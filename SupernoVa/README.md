# SupernoVa

A document-first study assistant built with Streamlit and Gemini.

## Features

- Black/red custom interface
- Gmail-based account login
- Separate conversations
- New conversation clears previous documents
- PDF and TXT upload
- Document-grounded Q&A
- Conversation history
- Conversation deletion without logging out
- Each saved conversation keeps its documents, chunks and chat history
- Gemini API key loaded from `.env`

## Run locally

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and put your Gemini API key in `GEMINI_API_KEY`.

Then:

```powershell
python -m streamlit run app.py
```

## Important

Never commit `.env`, your real API key, `supernova.db`, or your virtual environment.
