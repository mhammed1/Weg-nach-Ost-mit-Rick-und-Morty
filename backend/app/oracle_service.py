from __future__ import annotations

import os
import time
from pathlib import Path

import chromadb
import requests
from chromadb.config import Settings
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE_DIR / "data" / "chroma"

API_BASE = "https://rickandmortyapi.com/api"
COLLECTION_NAME = "oracle_jina_v1"
JINA_API_URL = "https://api.jina.ai/v1/embeddings"
JINA_EMBEDDING_MODEL = "jina-embeddings-v5-text-small"
MIN_RELEVANCE_CONFIDENCE = 60.0

SYSTEM_PROMPT = """You are the Interdimensional Oracle, a Rick & Morty Universe analyst.
STRICT RULES:
1. Answer ONLY from the retrieved context. Do NOT use external knowledge or world facts.
2. If the context does NOT answer the question, respond ONLY with: "Ich habe keine Informationen dazu in der Rick & Morty Wissensdatenbank."
3. Do NOT guess, speculate, or provide information from your training data.
4. Do NOT answer questions unrelated to Rick & Morty (like geography, history, science, etc.).
5. Answer in German.
6. End with a section titled 'Sources' and list URLs.
"""

ENTITY_TYPES = ("character", "episode", "location")


def _chroma_client() -> chromadb.PersistentClient:
    """Erzeugt einen persistenten Chroma-Client für das lokale Oracle-Verzeichnis."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def collection() -> chromadb.Collection:
    """Gibt die persistente Chroma-Collection des Oracle zurück."""
    client = _chroma_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


def embed_texts(texts: list[str], task: str) -> list[list[float]]:
    """Erzeugt Jina-Embeddings und gibt Vektoren in Eingabereihenfolge zurück."""
    if not texts:
        return []

    payload = {
        "model": JINA_EMBEDDING_MODEL,
        "task": task,
        "normalized": True,
        "input": texts,
    }
    response = requests.post(
        JINA_API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('JINA_API_KEY', '').strip()}",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    data = sorted(body.get("data", []), key=lambda item: int(item.get("index", 0)))
    return [[float(v) for v in item.get("embedding", [])] for item in data]


def fetch_all(endpoint: str) -> list:
    """Lädt alle paginierten Ergebnisse für einen API-Endpunkt."""
    items: list = []
    url = f"{API_BASE}/{endpoint}"
    while url:
        for attempt in range(5):
            response = requests.get(url, timeout=30)
            if response.status_code != 429:
                break
            retry_after = response.headers.get("Retry-After")
            wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else min(2 + attempt * 2, 10)
            time.sleep(wait_seconds)

        response.raise_for_status()
        payload = response.json()
        items.extend(payload.get("results", []))
        url = payload.get("info", {}).get("next")
    return items


def to_doc(entity_type: str, obj: dict) -> tuple[str, str, dict]:
    """Wandelt eine API-Entity in Dokumenttext und Retrieval-Metadaten um."""
    if entity_type == "character":
        text = "\n".join(
            [
                f"Character: {obj.get('name', 'Unknown')}",
                f"Status: {obj.get('status', 'unknown')}",
                f"Species: {obj.get('species', 'unknown')}",
                f"Type: {obj.get('type') or 'n/a'}",
                f"Gender: {obj.get('gender', 'unknown')}",
                f"Origin: {obj.get('origin', {}).get('name', 'unknown')}",
                f"Last known location: {obj.get('location', {}).get('name', 'unknown')}",
                f"Episode appearances: {len(obj.get('episode', []))}",
            ]
        )
    elif entity_type == "episode":
        text = "\n".join(
            [
                f"Episode: {obj.get('name', 'Unknown')}",
                f"Code: {obj.get('episode', 'unknown')}",
                f"Air date: {obj.get('air_date', 'unknown')}",
                f"Character count: {len(obj.get('characters', []))}",
            ]
        )
    else:
        text = "\n".join(
            [
                f"Location: {obj.get('name', 'Unknown')}",
                f"Type: {obj.get('type', 'unknown')}",
                f"Dimension: {obj.get('dimension', 'unknown')}",
                f"Resident count: {len(obj.get('residents', []))}",
            ]
        )

    metadata = {
        "type": entity_type,
        "name": obj.get("name", "Unknown"),
        "url": obj.get("url", ""),
    }
    return f"{entity_type}-{obj.get('id')}", text, metadata


def confidence(distance_list: list, source_count: int) -> float:
    """Berechnet einen Confidence-Wert aus Distanzen und Quellanzahl."""
    if not distance_list:
        return 0.0
    best = min(distance_list)
    score_factor = max(0.0, min(1.0, 1.0 - (best / 2.0)))
    count_factor = min(source_count / 6.0, 1.0)
    return round((0.6 * score_factor + 0.4 * count_factor) * 100.0, 1)


def _build_sources(metas: list, distances: list) -> list:
    # Baut eine Liste von Quellen aus Metadaten und Distanzwerten.
    sources: list = []
    for idx, meta in enumerate(metas):
        sources.append(
            {
            "name": meta.get("name", "Unknown"),
            "type": meta.get("type", "unknown"),
            "url": meta.get("url", ""),
            "score": distances[idx] if idx < len(distances) else 0.0,
            }
        )
    return sources


def _query_docs(query: str) -> tuple:
    """Erzeugt Query-Embedding und holt passende Top-Dokumente aus Chroma."""
    query_embedding = embed_texts([query], task="retrieval.query")
    result = collection().query(
        query_embeddings=query_embedding,
        n_results=6,
        include=["documents", "metadatas", "distances"],
    )
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    return docs, metas, distances


def _build_context_block(docs: list, metas: list) -> str:
    context_lines = [
        f"[{i + 1}] {meta.get('name', 'Unknown')} ({meta.get('type', 'unknown')})\n{doc}\nURL: {meta.get('url', '')}"
        for i, (doc, meta) in enumerate(zip(docs, metas))
    ]
    return "\n\n".join(context_lines)


def _build_prompt(query: str, context_block: str) -> str:
    return (
        f"Retrieved context:\n{context_block}\n\n"
        f"User question:\n{query}"
    )


def ingest_data() -> dict:
    """Baut die lokale Wissensbasis aus Characters, Episodes und Locations neu auf."""
    entity_data = {entity_type: fetch_all(entity_type) for entity_type in ENTITY_TYPES}

    client = _chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    coll = client.get_or_create_collection(name=COLLECTION_NAME)

    ids: list[str] = []
    docs: list[str] = []
    metadatas: list[dict] = []

    for entity_type, items in entity_data.items():
        for item in items:
            doc_id, doc_text, meta = to_doc(entity_type, item)
            ids.append(doc_id)
            docs.append(doc_text)
            metadatas.append(meta)

    batch_size = 200
    for i in range(0, len(ids), batch_size):
        batch_docs = docs[i : i + batch_size]
        batch_embeddings = embed_texts(batch_docs, task="retrieval.passage")
        coll.add(
            ids=ids[i : i + batch_size],
            documents=batch_docs,
            metadatas=metadatas[i : i + batch_size],
            embeddings=batch_embeddings,
        )

    stats = {
        "characters": len(entity_data["character"]),
        "episodes": len(entity_data["episode"]),
        "locations": len(entity_data["location"]),
        "documents": len(ids),
    }
    return stats


def run_chat(payload: dict) -> dict:
    """Führt Retrieval und Guardrail-geschützte LLM-Antwort für Chat-Payload aus."""
    query = str(payload.get("message", "")).strip()
    if not query:
        raise ValueError("message must not be empty")

    docs, metas, distances = _query_docs(query)
    score = confidence([float(x) for x in distances], len(docs))

    if not docs or score < MIN_RELEVANCE_CONFIDENCE:
        return {
            "answer": "Ich habe keine Informationen dazu in der Rick & Morty Wissensdatenbank.",
            "sources": [],
            "confidence": score,
            "guardrail": "off_topic_low_relevance_guardrail",
        }

    sources = _build_sources(metas, distances)

    context_block = _build_context_block(docs, metas)

    prompt = _build_prompt(query, context_block)
    client = Groq(api_key=os.getenv("GROQ_API_KEY", "").strip())
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    answer = response.choices[0].message.content or "Ich konnte keine Antwort generieren."

    return {
        "answer": answer,
        "sources": sources,
        "confidence": score,
        "guardrail": None,
    }


