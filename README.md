# Interdimensional Oracle

Kurzer MVP für die AI Full-Stack Aufgabe. Der Agent beantwortet Fragen zum Rick and Morty Universe auf Basis von Daten aus:
https://rickandmortyapi.com/api

## Stack

- Backend: FastAPI
- Wissensbasis: lokale ChromaDB
- Embeddings: Jina Embeddings API
- LLM: Groq
- Frontend: einfach html, css und js

## Quickstart (5 Minuten)

```bash
git clone <repo-url>
cd Rick-und-Morty
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Wichtiger Hinweis zu Secrets:

- Die Datei `.env` ist im Repository enthalten, aber nur mit Platzhaltern.
- Für den lokalen Start brauchst du einen API-Key von Groq und einen API-Key von Jina.

API-Keys erstellen:

- Groq: Account anlegen und API-Key erzeugen unter https://console.groq.com/
- Jina AI: Account anlegen und API-Key erzeugen unter https://jina.ai/

Dann `.env` im Projekt-Root mit deinen Keys befüllen:

```bash
JINA_API_KEY=
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
JINA_EMBEDDING_MODEL=jina-embeddings-v5-text-small
MIN_RELEVANCE_CONFIDENCE=60
```

Starten:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
curl -X POST http://127.0.0.1:8000/api/ingest
curl -X POST http://127.0.0.1:8000/api/chat -H "Content-Type: application/json" -d '{"message":"Wer ist Rick Sanchez?"}'
```

## MVP Status

- Datenpipeline: done
- RAG Pipeline mit Quellen: done
- Chat Interface mit Verlauf: done
- Prompt Engineering: done
- Guardrails:
  - Code Ebene: done (low relevance block)
  - Prompt Ebene: done (no guess rule)

## API Endpunkte

- GET /api/health
- POST /api/ingest
- POST /api/chat

## Bekannte Limitierungen

- Rein vektorbasierte Suche, kein Hybrid Retrieval.
- Kein Re Ranking.
- Episode Dokumente enthalten aktuell nur Character count, nicht die volle Charakterliste.
- LLM Antworten können in Grenzfällen variieren.

## Nächste Schritte

- Hybrid Retrieval (Vektor + Keyword)
- Re Ranking
- Output Validator gegen Kontext
- Optional: Feedback Logging, Browse Modus
- Streaming-Antworten
- Stochastik in Konfidenz
