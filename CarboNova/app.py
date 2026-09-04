import os
import sqlite3
from functools import wraps
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from services.calculator import calculate_impact
from services.optimizer import optimize
from services.gemini_service import get_gemini_recommendation

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
DB_PATH = os.path.join(os.path.dirname(__file__), "carbanova.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        electricity_kwh REAL NOT NULL,
        water_liters REAL NOT NULL,
        fuel_liters REAL NOT NULL,
        waste_kg REAL NOT NULL,
        solar_kwh REAL NOT NULL,
        occupancy INTEGER NOT NULL,
        energy_cost REAL NOT NULL,
        temperature REAL,
        daylight REAL,
        air_quality REAL,
        carbon_intensity REAL,
        operating_hours REAL,
        operating_condition TEXT,
        total_carbon REAL NOT NULL,
        predicted_reduction REAL NOT NULL DEFAULT 0,
        actual_reduction REAL,
        status TEXT NOT NULL DEFAULT 'Recommended',
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        action TEXT NOT NULL,
        reason TEXT NOT NULL,
        estimated_reduction REAL NOT NULL,
        cost_level TEXT NOT NULL,
        implementation TEXT NOT NULL,
        current_condition TEXT,
        expected_impact TEXT,
        cost_benefit_score REAL DEFAULT 0,
        FOREIGN KEY(assessment_id) REFERENCES assessments(id)
    );
    """)
    # Lightweight migrations keep an existing local SQLite database compatible.
    existing_assessment = {row["name"] for row in conn.execute("PRAGMA table_info(assessments)").fetchall()}
    for column, definition in {
        "temperature": "REAL",
        "daylight": "REAL",
        "air_quality": "REAL",
        "carbon_intensity": "REAL",
        "operating_hours": "REAL",
        "operating_condition": "TEXT"
    }.items():
        if column not in existing_assessment:
            conn.execute(f"ALTER TABLE assessments ADD COLUMN {column} {definition}")

    existing_recommendation = {row["name"] for row in conn.execute("PRAGMA table_info(recommendations)").fetchall()}
    for column, definition in {
        "current_condition": "TEXT",
        "expected_impact": "TEXT",
        "cost_benefit_score": "REAL DEFAULT 0"
    }.items():
        if column not in existing_recommendation:
            conn.execute(f"ALTER TABLE recommendations ADD COLUMN {column} {definition}")

    conn.commit()
    conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    user = conn.execute(
        "SELECT id,name,email,created_at FROM users WHERE id=?",
        (session["user_id"],)
    ).fetchone()
    conn.close()
    return user

@app.context_processor
def inject_user():
    return {"current_user": current_user()}

@app.route("/")
def index():
    return redirect(url_for("dashboard")) if "user_id" in session else render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 6:
            flash("Enter your name, email and a password of at least 6 characters.", "error")
            return render_template("auth.html", mode="signup")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
                (name, email, generate_password_hash(password), datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
            user = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
            return render_template("auth.html", mode="signup")
        finally:
            conn.close()
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    latest = conn.execute(
        "SELECT * FROM assessments WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (session["user_id"],)
    ).fetchone()
    history = conn.execute(
        "SELECT created_at,total_carbon FROM assessments WHERE user_id=? ORDER BY id ASC LIMIT 12",
        (session["user_id"],)
    ).fetchall()
    recommendations = []
    if latest:
        recommendations = conn.execute(
            "SELECT * FROM recommendations WHERE assessment_id=? ORDER BY estimated_reduction DESC",
            (latest["id"],)
        ).fetchall()
    conn.close()
    return render_template("dashboard.html", latest=latest, history=history, recommendations=recommendations)

@app.route("/history")
@login_required
def history():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM assessments WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("history.html", rows=rows)

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

@app.post("/api/analyze")
@login_required
def analyze():
    data = request.get_json(force=True)

    numeric_defaults = {
        "electricity_kwh": 0, "water_liters": 0, "fuel_liters": 0,
        "waste_kg": 0, "solar_kwh": 0, "occupancy": 0, "energy_cost": 0,
        "temperature": 23, "daylight": 85, "air_quality": 90,
        "carbon_intensity": 150, "operating_hours": 8
    }
    for key, default in numeric_defaults.items():
        try:
            data[key] = float(data.get(key, default))
        except (TypeError, ValueError):
            data[key] = float(default)

    data["occupancy"] = max(0, int(data["occupancy"]))
    data["operating_condition"] = str(data.get("operating_condition", "Normal")).strip() or "Normal"
    data["daylight"] = max(0, min(data["daylight"], 100))
    data["air_quality"] = max(0, min(data["air_quality"], 100))
    data["carbon_intensity"] = max(0, data["carbon_intensity"])
    data["temperature"] = max(-50, min(data["temperature"], 60))
    data["operating_hours"] = max(0, min(data["operating_hours"], 24))

    impact = calculate_impact(data)
    recommendations = optimize(data, impact)
    gemini_text = get_gemini_recommendation(impact, recommendations)
    predicted = round(min(sum(r["estimated_reduction"] for r in recommendations), impact["total_carbon"]), 2)
    gemini_text = get_gemini_recommendation(impact, recommendations)
    predicted = round(min(sum(r["estimated_reduction"] for r in recommendations), impact["total_carbon"]), 2)

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO assessments(
            user_id,created_at,electricity_kwh,water_liters,fuel_liters,waste_kg,
            solar_kwh,occupancy,energy_cost,temperature,daylight,air_quality,
            carbon_intensity,operating_hours,operating_condition,total_carbon,predicted_reduction
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        session["user_id"], datetime.now(timezone.utc).isoformat(),
        impact["electricity_kwh"], impact["water_liters"], impact["fuel_liters"],
        impact["waste_kg"], impact["solar_kwh"], impact["occupancy"],
        impact["energy_cost"], data["temperature"], data["daylight"],
        data["air_quality"], data["carbon_intensity"], data["operating_hours"],
        data["operating_condition"], impact["total_carbon"], predicted
    ))
    assessment_id = cur.lastrowid

    for r in recommendations:
        conn.execute("""
            INSERT INTO recommendations(
                assessment_id,title,category,priority,action,reason,
                estimated_reduction,cost_level,implementation,current_condition,
                expected_impact,cost_benefit_score
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            assessment_id, r["title"], r["category"], r["priority"], r["action"],
            r["reason"], r["estimated_reduction"], r["cost_level"], r["implementation"],
            r.get("current_condition", ""), r.get("expected_impact", ""),
            r.get("cost_benefit_score", 0)
        ))
    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "assessment_id": assessment_id,
        "impact": impact,
        "recommendations": recommendations,
        "gemini": gemini_text,
        "predicted_reduction": predicted
    })

@app.post("/api/what-if")
@login_required
def what_if():
    data = request.get_json(force=True)
    baseline = calculate_impact(data)
    scenario = dict(data)

    er = max(0, min(float(data.get("electricity_reduction_pct", 0)), 100))
    wr = max(0, min(float(data.get("water_reduction_pct", 0)), 100))
    solar_add = max(float(data.get("solar_addition_kwh", 0)), 0)

    scenario["electricity_kwh"] = float(data.get("electricity_kwh", 0)) * (1 - er / 100)
    scenario["water_liters"] = float(data.get("water_liters", 0)) * (1 - wr / 100)
    scenario["solar_kwh"] = float(data.get("solar_kwh", 0)) + solar_add

    result = calculate_impact(scenario)
    saved = max(baseline["total_carbon"] - result["total_carbon"], 0)

    return jsonify({
        "baseline": baseline["total_carbon"],
        "scenario": result["total_carbon"],
        "saved": round(saved, 2)
    })

@app.post("/api/verify/<int:assessment_id>")
@login_required
def verify(assessment_id):
    data = request.get_json(force=True)
    actual = max(float(data.get("actual_reduction", 0)), 0)

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM assessments WHERE id=? AND user_id=?",
        (assessment_id, session["user_id"])
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Assessment not found"}), 404

    conn.execute(
        "UPDATE assessments SET actual_reduction=?,status='Verified' WHERE id=?",
        (actual, assessment_id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "predicted": row["predicted_reduction"],
        "actual": actual,
        "variance": round(actual - row["predicted_reduction"], 2)
    })

init_db()

if __name__ == "__main__":
    app.run(debug=True)
