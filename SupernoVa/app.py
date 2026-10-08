import json
import os
import re
import sqlite3
import hashlib
import hmac
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# IMPORTANT:
# Load .env BEFORE importing rag.py because rag.py reads
# GENERATION_MODEL when it is imported.
load_dotenv(ENV_FILE, override=True)

# Safe default if GENERATION_MODEL is missing from .env.
os.environ.setdefault("GENERATION_MODEL", "gemini-3.5-flash-lite")


# ============================================================
# PROJECT IMPORTS
# ============================================================

from document_processor import process_files
from rag import answer_question, build_index


# ============================================================
# DATABASE
# ============================================================

DB_PATH = BASE_DIR / "supernova.db"


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="SupernoVa",
    page_icon="V",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STYLING
# ============================================================

st.markdown(
    """
    <style>

    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: #000 !important;
        color: #eee !important;
    }

    [data-testid="stHeader"] {
        background: #000 !important;
    }

    [data-testid="stSidebar"] {
        background: #000 !important;
        border-right: 1px solid #1b1b1b;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 20px 14px;
    }

    .block-container {
        max-width: 1320px;
        padding: 72px 44px 70px;
    }

    .brand {
        font-size: 25px;
        font-weight: 800;
        letter-spacing: -1.4px;
    }

    .brand-v {
        color: #ef3030;
        font-size: 31px;
    }

    .muted {
        color: #666;
    }

    .micro {
        color: #555;
        font-size: 9px;
        letter-spacing: 1.7px;
        text-transform: uppercase;
    }

    .profile-name {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-align: center;
    }

    .hero {
        max-width: 900px;
        padding: 80px 0 45px;
    }

    .hero h1 {
        font-size: clamp(48px, 7vw, 88px);
        line-height: .94;
        letter-spacing: -5px;
        margin: 14px 0 24px;
    }

    .hero h1 span {
        color: #ef3030;
    }

    .hero-copy {
        max-width: 650px;
        color: #858585;
        font-size: 15px;
        line-height: 1.75;
    }

    .steps {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-top: 40px;
    }

    .step {
        border-top: 1px solid #252525;
        padding: 16px 4px;
    }

    .step-no {
        color: #ef3030;
        font-size: 10px;
        letter-spacing: 1px;
    }

    .step-title {
        margin-top: 10px;
        font-size: 14px;
        font-weight: 650;
    }

    .step-copy {
        color: #666;
        font-size: 11px;
        line-height: 1.6;
        margin-top: 5px;
    }

    .page-title {
        font-size: 38px;
        font-weight: 800;
        letter-spacing: -2.3px;
        margin-top: 10px;
    }

    .page-sub {
        color: #666;
        font-size: 11px;
        margin-top: 5px;
    }

    .panel {
        background: #060606;
        border: 1px solid #202020;
        border-radius: 10px;
        padding: 22px;
        margin-top: 24px;
    }

    .chip {
        display: inline-block;
        border: 1px solid #282828;
        background: #070707;
        color: #999;
        border-radius: 6px;
        padding: 6px 9px;
        margin: 5px 5px 0 0;
        font-size: 10px;
    }

    .empty {
        border: 1px dashed #2b2b2b;
        border-radius: 10px;
        padding: 42px;
        text-align: center;
        color: #555;
        margin-top: 22px;
    }

    .source {
        border-left: 2px solid #ef3030;
        background: #080808;
        padding: 9px 11px;
        margin: 7px 0;
    }

    .source-meta {
        color: #d95757;
        font-size: 9px;
    }

    .source-text {
        color: #777;
        font-size: 10px;
        line-height: 1.55;
        margin-top: 4px;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background: #070707 !important;
        color: #fff !important;
        border: 1px solid #292929 !important;
    }

    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
        border-color: #ef3030 !important;
        box-shadow: none !important;
    }

    [data-testid="stFileUploader"] {
        background: #050505 !important;
        border: 1px solid #202020 !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: #000 !important;
        border: 1px dashed #303030 !important;
    }

    .stButton > button {
        background: #080808 !important;
        color: #ddd !important;
        border: 1px solid #252525 !important;
        border-radius: 8px !important;
    }

    .stButton > button:hover {
        border-color: #555 !important;
        color: #fff !important;
    }

    .stButton > button[kind="primary"] {
        background: #ef3030 !important;
        border-color: #ef3030 !important;
        color: #fff !important;
    }

    @media(max-width: 800px) {
        .block-container {
            padding: 24px 16px 60px;
        }

        .steps {
            grid-template-columns: 1fr;
        }

        .hero h1 {
            letter-spacing: -3px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            documents_json TEXT NOT NULL DEFAULT '[]',
            chunks_json TEXT NOT NULL DEFAULT '[]',
            messages_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()

    # --------------------------------------------------------
    # Safe migration
    # --------------------------------------------------------

    user_cols = {
        r[1]
        for r in conn.execute("PRAGMA table_info(users)").fetchall()
    }

    if "name" not in user_cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN name TEXT NOT NULL DEFAULT ''"
        )

    chat_cols = {
        r[1]
        for r in conn.execute("PRAGMA table_info(chats)").fetchall()
    }

    if "documents_json" not in chat_cols:
        conn.execute(
            "ALTER TABLE chats ADD COLUMN documents_json TEXT NOT NULL DEFAULT '[]'"
        )

    if "chunks_json" not in chat_cols:
        conn.execute(
            "ALTER TABLE chats ADD COLUMN chunks_json TEXT NOT NULL DEFAULT '[]'"
        )

    if "messages_json" not in chat_cols:
        conn.execute(
            "ALTER TABLE chats ADD COLUMN messages_json TEXT NOT NULL DEFAULT '[]'"
        )

    if "updated_at" not in chat_cols:
        conn.execute(
            "ALTER TABLE chats ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
        )

    conn.commit()
    conn.close()


init_db()


# ============================================================
# AUTHENTICATION
# ============================================================

def password_hash(password: str) -> str:
    salt = os.urandom(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        120000,
    )

    return f"{salt.hex()}:{digest.hex()}"


def password_ok(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            bytes.fromhex(salt_hex),
            120000,
        )

        return hmac.compare_digest(
            actual,
            bytes.fromhex(digest_hex),
        )

    except Exception:
        return False


def create_user(name, email, password):
    conn = db()

    try:
        cur = conn.execute(
            """
            INSERT INTO users(name, email, password_hash)
            VALUES(?,?,?)
            """,
            (
                name.strip(),
                email.strip().lower(),
                password_hash(password),
            ),
        )

        conn.commit()

        return {
            "id": cur.lastrowid,
            "name": name.strip(),
            "email": email.strip().lower(),
        }, None

    except sqlite3.IntegrityError:
        return None, "An account with this Gmail already exists."

    finally:
        conn.close()


def login_user(email, password):
    conn = db()

    row = conn.execute(
        """
        SELECT id, name, email, password_hash
        FROM users
        WHERE email=?
        """,
        (email.strip().lower(),),
    ).fetchone()

    conn.close()

    if row and password_ok(password, row[3]):
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
        }

    return None


# ============================================================
# CHAT PERSISTENCE
# ============================================================

def save_chat(
    user_id,
    title,
    documents,
    chunks,
    messages,
    chat_id=None,
):
    conn = db()

    now = datetime.now().isoformat(timespec="seconds")

    docs = json.dumps(
        documents,
        ensure_ascii=False,
    )

    chunk_data = json.dumps(
        chunks,
        ensure_ascii=False,
    )

    msg_data = json.dumps(
        messages,
        ensure_ascii=False,
    )

    if chat_id:

        conn.execute(
            """
            UPDATE chats
            SET
                title=?,
                documents_json=?,
                chunks_json=?,
                messages_json=?,
                updated_at=?
            WHERE id=? AND user_id=?
            """,
            (
                title,
                docs,
                chunk_data,
                msg_data,
                now,
                chat_id,
                user_id,
            ),
        )

    else:

        cur = conn.execute(
            """
            INSERT INTO chats(
                user_id,
                title,
                documents_json,
                chunks_json,
                messages_json,
                updated_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                user_id,
                title,
                docs,
                chunk_data,
                msg_data,
                now,
            ),
        )

        chat_id = cur.lastrowid

    conn.commit()
    conn.close()

    return chat_id


def list_chats(user_id):
    conn = db()

    rows = conn.execute(
        """
        SELECT id, title, updated_at
        FROM chats
        WHERE user_id=?
        ORDER BY updated_at DESC
        """,
        (user_id,),
    ).fetchall()

    conn.close()

    return rows


def load_chat(user_id, chat_id):
    conn = db()

    row = conn.execute(
        """
        SELECT *
        FROM chats
        WHERE id=? AND user_id=?
        """,
        (chat_id, user_id),
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "title": row["title"],
        "documents": json.loads(
            row["documents_json"] or "[]"
        ),
        "chunks": json.loads(
            row["chunks_json"] or "[]"
        ),
        "messages": json.loads(
            row["messages_json"] or "[]"
        ),
    }


def delete_chat(user_id, chat_id):
    conn = db()

    conn.execute(
        """
        DELETE FROM chats
        WHERE id=? AND user_id=?
        """,
        (chat_id, user_id),
    )

    conn.commit()
    conn.close()


# ============================================================
# SESSION
# ============================================================

def reset_conversation():
    st.session_state.chat_id = None
    st.session_state.chat_title = "New conversation"
    st.session_state.documents = []
    st.session_state.chunks = []
    st.session_state.index = None
    st.session_state.messages = []
    st.session_state.upload_key += 1


for key, value in {
    "user": None,
    "page": "landing",
    "auth_mode": "signin",
    "chat_id": None,
    "chat_title": "New conversation",
    "documents": [],
    "chunks": [],
    "index": None,
    "messages": [],
    "upload_key": 0,
    "profile_open": False,
    "delete_target": None,
}.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# UI HELPERS
# ============================================================

def brand_html():
    return (
        '<div class="brand">'
        'Superno<span class="brand-v">V</span>a'
        '</div>'
    )


def logout():
    st.session_state.user = None
    st.session_state.page = "landing"
    st.session_state.auth_mode = "signin"
    st.session_state.profile_open = False

    reset_conversation()

    st.rerun()


def top_bar():

    left, right = st.columns(
        [7, 1.5],
        vertical_alignment="center",
    )

    with left:
        st.markdown(
            brand_html(),
            unsafe_allow_html=True,
        )

    with right:

        if st.session_state.user:

            label = (
                st.session_state.user.get("name")
                or "Profile"
            )

            if st.button(
                label,
                key="profile_button",
                use_container_width=True,
            ):
                st.session_state.profile_open = (
                    not st.session_state.profile_open
                )
                st.rerun()

        else:

            if st.button(
                "Sign in",
                key="signin_top",
                use_container_width=True,
            ):
                st.session_state.page = "auth"
                st.rerun()

    if (
        st.session_state.user
        and st.session_state.profile_open
    ):

        user_name = st.session_state.user.get("name") or "User"
        user_email = st.session_state.user.get("email") or ""

        st.html(
            f"""
            <div style="
                width:260px;
                margin-left:auto;
                margin-top:10px;
                border:1px solid #242424;
                background:#080808;
                border-radius:10px;
                padding:16px;
                text-align:center;
                box-sizing:border-box;
            ">
                <div style="
                    color:#eee;
                    font-size:14px;
                    font-weight:700;
                    margin-bottom:6px;
                    overflow:hidden;
                    text-overflow:ellipsis;
                    white-space:nowrap;
                ">
                    {user_name}
                </div>
                <div style="
                    color:#777;
                    font-size:11px;
                    overflow-wrap:anywhere;
                ">
                    {user_email}
                </div>
            </div>
            """
        )

        if st.button(
            "Log out",
            key="top_logout",
            use_container_width=False,
        ):
            logout()


def sidebar():

    user = st.session_state.user

    with st.sidebar:

        st.markdown(
            brand_html(),
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="micro" style="margin-top:5px">'
            'document study assistant'
            '</div>',
            unsafe_allow_html=True,
        )

        st.divider()

        if st.button(
            "＋  New conversation",
            key="new_chat",
            use_container_width=True,
        ):
            reset_conversation()
            st.session_state.page = "workspace"
            st.rerun()

        st.markdown(
            '<div class="micro" style="margin:18px 4px 8px">'
            'conversation history'
            '</div>',
            unsafe_allow_html=True,
        )

        chats = list_chats(user["id"])

        if not chats:
            st.caption("No conversations yet.")

        for row in chats:

            chat_id = row["id"]
            title = row["title"] or "Untitled conversation"

            if len(title) > 26:
                title = title[:26] + "…"

            c1, c2 = st.columns(
                [5, 1],
                gap="small",
            )

            with c1:

                if st.button(
                    title,
                    key=f"open_{chat_id}",
                    use_container_width=True,
                ):

                    data = load_chat(
                        user["id"],
                        chat_id,
                    )

                    if data:

                        st.session_state.chat_id = data["id"]
                        st.session_state.chat_title = data["title"]
                        st.session_state.documents = data["documents"]
                        st.session_state.chunks = data["chunks"]
                        st.session_state.messages = data["messages"]

                        st.session_state.index = (
                            build_index(data["chunks"])
                            if data["chunks"]
                            else None
                        )

                        st.session_state.page = "workspace"

                        st.rerun()

            with c2:

                if st.button(
                    "⋯",
                    key=f"menu_{chat_id}",
                    help="Delete conversation",
                ):

                    st.session_state.delete_target = (
                        chat_id
                        if st.session_state.delete_target != chat_id
                        else None
                    )

                    st.rerun()

            if st.session_state.delete_target == chat_id:

                d1, d2 = st.columns(
                    2,
                    gap="small",
                )

                with d1:

                    if st.button(
                        "Delete",
                        key=f"confirm_delete_{chat_id}",
                        use_container_width=True,
                    ):

                        delete_chat(
                            user["id"],
                            chat_id,
                        )

                        if st.session_state.chat_id == chat_id:
                            reset_conversation()

                        st.session_state.delete_target = None

                        st.rerun()

                with d2:

                    if st.button(
                        "Cancel",
                        key=f"cancel_delete_{chat_id}",
                        use_container_width=True,
                    ):

                        st.session_state.delete_target = None
                        st.rerun()

        st.markdown(
            '<div style="height:80px"></div>',
            unsafe_allow_html=True,
        )

        st.divider()

        st.caption(
            user.get("name") or "User"
        )

        st.caption(
            user["email"]
        )

        if st.button(
            "Log out",
            key="side_logout",
            use_container_width=True,
        ):
            logout()


# ============================================================
# LANDING PAGE
# ============================================================

def landing_page():

    top_bar()

    st.html(
        """
        <div class="hero">

            <div class="micro">
                A document-first study assistant
            </div>

            <h1>
                Study from what<br>
                you <span>already have.</span>
            </h1>

            <div class="hero-copy">
                SupernoVa turns your own notes and PDFs
                into a focused study conversation.
                Upload material, ask doubts in plain language,
                and keep each study session separate.
            </div>

            <div class="steps">

                <div class="step">
                    <div class="step-no">01</div>
                    <div class="step-title">
                        Bring your material
                    </div>
                    <div class="step-copy">
                        Upload the notes or documents
                        you actually want to study.
                    </div>
                </div>

                <div class="step">
                    <div class="step-no">02</div>
                    <div class="step-title">
                        Ask naturally
                    </div>
                    <div class="step-copy">
                        Ask questions, request explanations,
                        and continue with follow-ups.
                    </div>
                </div>

                <div class="step">
                    <div class="step-no">03</div>
                    <div class="step-title">
                        Keep sessions apart
                    </div>
                    <div class="step-copy">
                        Every conversation keeps its own
                        documents and complete chat history.
                    </div>
                </div>

            </div>

        </div>
        """
    )


# ============================================================
# AUTH PAGE
# ============================================================

def auth_page():

    top_bar()

    st.markdown(
        '<div style="max-width:520px;margin:60px auto 0">',
        unsafe_allow_html=True,
    )

    mode = st.radio(
        "Mode",
        ["Sign in", "Create account"],
        horizontal=True,
        label_visibility="collapsed",
        index=(
            0
            if st.session_state.auth_mode == "signin"
            else 1
        ),
    )

    st.session_state.auth_mode = (
        "signin"
        if mode == "Sign in"
        else "register"
    )

    st.markdown(
        '<div class="micro" style="margin-top:35px">'
        'SupernoVa account'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="page-title">{mode}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-sub">'
        'Use a Gmail address to keep your conversations '
        'private to your account.'
        '</div>',
        unsafe_allow_html=True,
    )

    name = ""

    if mode == "Create account":
        name = st.text_input(
            "Name",
            placeholder="Your name",
        )

    email = st.text_input(
        "Gmail",
        placeholder="you@gmail.com",
    )

    password = st.text_input(
        "Password",
        type="password",
    )

    confirm = ""

    if mode == "Create account":
        confirm = st.text_input(
            "Confirm password",
            type="password",
        )

    if st.button(
        mode,
        type="primary",
        use_container_width=True,
        key="auth_submit",
    ):

        email = email.strip().lower()

        if not re.fullmatch(
            r"[^@\s]+@gmail\.com",
            email,
        ):

            st.error(
                "Please enter a valid Gmail address."
            )

        elif len(password) < 6:

            st.error(
                "Password must contain at least 6 characters."
            )

        elif (
            mode == "Create account"
            and not name.strip()
        ):

            st.error(
                "Please enter your name."
            )

        elif (
            mode == "Create account"
            and password != confirm
        ):

            st.error(
                "Passwords do not match."
            )

        elif mode == "Create account":

            user, error = create_user(
                name,
                email,
                password,
            )

            if error:

                st.error(error)

            else:

                st.session_state.user = user

                reset_conversation()

                st.session_state.page = "workspace"

                st.rerun()

        else:

            user = login_user(
                email,
                password,
            )

            if not user:

                st.error(
                    "Incorrect Gmail or password."
                )

            else:

                st.session_state.user = user

                reset_conversation()

                st.session_state.page = "workspace"

                st.rerun()

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# UPLOAD PAGE
# ============================================================

def upload_page():

    st.markdown(
        '<div class="page-title">'
        'Start a study session'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="page-sub">'
        'This is a fresh conversation. Nothing from an older '
        'conversation is carried into it.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="panel">
            <b>Add your study material</b>
            <br>
            <span class="muted">
                PDF and TXT files are supported.
                Your documents stay attached to this conversation.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    files = st.file_uploader(
        "Documents",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key=f"files_{st.session_state.upload_key}",
    )

    if files:

        st.caption(
            f"{len(files)} file(s) selected"
        )

        for f in files:
            st.write(
                f"• {f.name}"
            )

        if st.button(
            "Process documents",
            type="primary",
            use_container_width=True,
            key="process_files",
        ):

            try:

                with st.spinner(
                    "Reading your documents…"
                ):

                    chunks = process_files(files)

                    index = build_index(chunks)

                if not chunks:

                    st.error(
                        "No readable text was found "
                        "in the uploaded files."
                    )

                    return

                st.session_state.documents = [
                    f.name
                    for f in files
                ]

                st.session_state.chunks = chunks

                st.session_state.index = index

                st.session_state.messages = []

                st.session_state.chat_id = None

                st.session_state.chat_title = (
                    "New conversation"
                )

                st.session_state.page = "workspace"

                st.rerun()

            except Exception as exc:

                st.error(
                    "Could not process the document."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.code(
                        str(exc)
                    )


# ============================================================
# SOURCES
# ============================================================

def render_sources(sources):

    if not sources:
        return

    with st.expander(
        "Referenced snippets"
    ):

        for source in sources:

            file_name = source.get(
                "file",
                "Document",
            )

            page = source.get(
                "page",
                "?",
            )

            text = source.get(
                "text",
                "",
            )

            st.markdown(
                f"""
                <div class="source">

                    <div class="source-meta">
                        {file_name} · Page {page}
                    </div>

                    <div class="source-text">
                        {text}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# CHAT PAGE
# ============================================================

def chat_page():

    docs = st.session_state.documents

    st.markdown(
        f'<div class="page-title">'
        f'{st.session_state.chat_title}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="page-sub">'
        f'{len(docs)} document(s) in this conversation'
        f'</div>',
        unsafe_allow_html=True,
    )

    if docs:

        st.markdown(
            "".join(
                f'<span class="chip">{d}</span>'
                for d in docs
            ),
            unsafe_allow_html=True,
        )

    if not st.session_state.messages:

        st.markdown(
            """
            <div class="empty">
                <b>Ready when you are.</b>
                <br>
                <span style="font-size:11px">
                    Ask a question about the uploaded material below.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for msg in st.session_state.messages:

        role = msg.get(
            "role",
            "assistant",
        )

        with st.chat_message(role):

            st.markdown(
                msg.get(
                    "content",
                    "",
                )
            )

            if role == "assistant":

                render_sources(
                    msg.get(
                        "sources",
                        [],
                    )
                )

    question = st.chat_input(
        "Ask a doubt about your documents…"
    )

    if not question:
        return

    if (
        not st.session_state.chunks
        or not st.session_state.index
    ):

        st.error(
            "This conversation has no active document index. "
            "Please start a new conversation and upload "
            "the documents again."
        )

        return

    previous_history = list(
        st.session_state.messages
    )

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    answer = ""
    sources = []

    with st.chat_message("assistant"):

        try:

            with st.spinner(
                "Thinking from your documents…"
            ):

                result = answer_question(
                    question,
                    st.session_state.chunks,
                    st.session_state.index,
                    previous_history,
                )

            answer = result.get(
                "answer",
                "No answer was generated.",
            )

            sources = result.get(
                "sources",
                [],
            )

            st.markdown(answer)

            render_sources(sources)

        except Exception as exc:

            error_text = str(exc)

            lower_error = error_text.lower()

            # ------------------------------------------------
            # Identify the actual Gemini problem
            # ------------------------------------------------

            if (
                "404" in lower_error
                and "model" in lower_error
            ):

                answer = (
                    "SupernoVa reached Gemini, but the "
                    "configured Gemini model is not available "
                    "for this API project. Check "
                    "GENERATION_MODEL in your .env file."
                )

            elif (
                "429" in lower_error
                or "resource_exhausted" in lower_error
            ):

                answer = (
                    "SupernoVa reached Gemini, but the API "
                    "request was rate-limited or the project's "
                    "Gemini quota was exhausted."
                )

            elif (
                "401" in lower_error
                or "403" in lower_error
                or "permission" in lower_error
            ):

                answer = (
                    "SupernoVa reached Gemini, but the API key "
                    "or project does not have permission to use "
                    "the configured model."
                )

            elif (
                "api key" in lower_error
                or "api_key" in lower_error
            ):

                answer = (
                    "SupernoVa could not authenticate with "
                    "the Gemini API. Check GEMINI_API_KEY "
                    "in your .env file."
                )

            else:

                answer = (
                    "SupernoVa could not generate the answer. "
                    "Open Technical details below to see "
                    "the actual error."
                )

            st.markdown(answer)

            with st.expander(
                "Technical details"
            ):

                st.code(
                    "Model loaded by app: "
                    + os.getenv(
                        "GENERATION_MODEL",
                        "(not set)",
                    )
                    + "\n\nError:\n"
                    + error_text
                )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
        }
    )

    title = re.sub(
        r"\s+",
        " ",
        question,
    ).strip()[:50] or "New conversation"

    st.session_state.chat_title = title

    st.session_state.chat_id = save_chat(
        st.session_state.user["id"],
        title,
        st.session_state.documents,
        st.session_state.chunks,
        st.session_state.messages,
        st.session_state.chat_id,
    )

    st.rerun()


# ============================================================
# WORKSPACE
# ============================================================

def workspace():

    sidebar()

    top_bar()

    if (
        not st.session_state.documents
        and not st.session_state.messages
    ):

        upload_page()

    else:

        chat_page()


# ============================================================
# ROUTE
# ============================================================

if st.session_state.user is None:

    if st.session_state.page == "auth":

        auth_page()

    else:

        landing_page()

else:

    workspace()