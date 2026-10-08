import math
import os
import re
from collections import Counter

from google import genai

MODEL = os.getenv("GENERATION_MODEL", "gemini-2.5-flash")


def tokens(text):
    return re.findall(r"[a-zA-Z0-9_]+", str(text).lower())


def build_index(chunks):
    docs = [Counter(tokens(item.get("text", ""))) for item in chunks]
    df = Counter()
    for doc in docs:
        for word in doc:
            df[word] += 1
    return {"docs": docs, "df": df, "n": len(docs)}


def retrieve(query, chunks, index, k=5):
    if not chunks or not index or not index.get("docs"):
        return []

    query_words = set(tokens(query))
    scores = []
    n = index.get("n", len(chunks))
    df = index.get("df", {})

    for i, doc in enumerate(index["docs"]):
        score = 0.0
        for word in query_words:
            if word in doc:
                tf = 1 + math.log(doc[word])
                idf = math.log((n + 1) / (df.get(word, 0) + 1))
                score += tf * idf
        scores.append((score, i))

    scores.sort(reverse=True)
    selected = [chunks[i] for score, i in scores[:k] if score > 0]
    return selected or chunks[:k]


def answer_question(question, chunks, index, history=None):
    sources = retrieve(question, chunks, index, k=5)
    context = "\n\n".join(
        f"[{item.get('file', 'Document')} | page {item.get('page', '?')}]\n{item.get('text', '')}"
        for item in sources
    )

    history = history or []
    recent = "\n".join(
        f"{item.get('role', 'user')}: {item.get('content', '')}"
        for item in history[-6:]
    )

    prompt = f"""You are SupernoVa, a document-based study assistant.

Answer the student's question using the supplied document excerpts as the main source.
Do not invent facts that are absent from the excerpts.
If the documents do not contain enough information, say that clearly.
Explain at a student-friendly level.
Preserve important terminology, formulas, dates, names, and definitions from the material.

DOCUMENT EXCERPTS:
{context}

RECENT CONVERSATION:
{recent}

QUESTION:
{question}
"""

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Put it in your .env file.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response. Try again.")

    return {"answer": text.strip(), "sources": sources}
