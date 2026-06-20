# Interdimensional Oracle

Kurzer MVP fuer die AI Full-Stack Aufgabe. Der Agent beantwortet Fragen zum Rick and Morty Universe auf Basis von Daten aus:
https://rickandmortyapi.com/api

## Stack

- Backend: FastAPI
- Wissensbasis: lokale ChromaDB
- Embeddings: Jina Embeddings API
- LLM: Groq
- Frontend: einfach html, css und js

## Quickstart (5 Minuten)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

`.env` im Projekt-Root anlegen:

```bash
JINA_API_KEY=
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
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
- LLM Antworten koennen in Grenzfaellen variieren.

## Naechste Schritte

- Hybrid Retrieval (Vektor + Keyword)
- Re Ranking
- Output Validator gegen Kontext
- Optional: Feedback Logging, Browse Modus
- Streaming-Antworten
- Stokastik in confidenz