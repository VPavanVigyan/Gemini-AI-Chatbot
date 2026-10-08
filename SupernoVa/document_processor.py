from io import BytesIO

from pypdf import PdfReader


def clean_text(text):
    text = text.replace("\x00", " ")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def chunk_text(text, size=1200, overlap=180):
    text = clean_text(text)
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def process_files(files):
    result = []
    for uploaded in files:
        name = uploaded.name
        data = uploaded.getvalue()
        lower = name.lower()

        if lower.endswith(".pdf"):
            reader = PdfReader(BytesIO(data))
            for page_no, page in enumerate(reader.pages, start=1):
                text = clean_text(page.extract_text() or "")
                for piece in chunk_text(text):
                    result.append({"file": name, "page": page_no, "text": piece})
        elif lower.endswith(".txt"):
            text = data.decode("utf-8", errors="ignore")
            for piece in chunk_text(text):
                result.append({"file": name, "page": 1, "text": piece})

    return result
