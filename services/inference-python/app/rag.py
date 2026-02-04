from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import httpx


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source: str
    chunk_index: int
    score: float


class RAGError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(words):
            break
        start = max(end - overlap, 0)
    return chunks


def extract_text(path: Path) -> str:
    data = path.read_bytes()
    return data.decode("utf-8", errors="ignore").strip()


def embed_text(
    base_url: str, model: str, text: str, timeout_seconds: float = 30.0
) -> List[float]:
    payload = {"model": model, "prompt": text}
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/api/embeddings",
            json=payload,
            timeout=httpx.Timeout(timeout_seconds, connect=5.0),
        )
    except httpx.RequestError as exc:
        raise RAGError(
            502,
            (
                "Ollama embeddings are unreachable at "
                f"{base_url}. Start it with `ollama serve` on the host."
            ),
        ) from exc

    if response.status_code != 200:
        raise RAGError(
            502, f"Ollama embeddings error {response.status_code}: {response.text}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise RAGError(502, "Invalid JSON response from Ollama embeddings.") from exc

    embedding = data.get("embedding")
    if not embedding:
        raise RAGError(502, "Ollama embeddings response missing embedding.")
    return embedding


def ensure_collection(
    qdrant_url: str,
    collection: str,
    vector_size: int,
    distance: str = "Cosine",
) -> None:
    url = qdrant_url.rstrip("/")
    try:
        response = httpx.get(f"{url}/collections/{collection}", timeout=10.0)
    except httpx.RequestError as exc:
        raise RAGError(502, f"Qdrant is unreachable at {qdrant_url}.") from exc

    if response.status_code == 200:
        existing = response.json()
        existing_size = (
            existing.get("result", {})
            .get("config", {})
            .get("params", {})
            .get("vectors", {})
            .get("size")
        )
        if existing_size and existing_size != vector_size:
            raise RAGError(
                500,
                (
                    f"Qdrant collection '{collection}' has size {existing_size} "
                    f"but embeddings are {vector_size}."
                ),
            )
        return

    if response.status_code not in (404, 400):
        raise RAGError(502, f"Qdrant error {response.status_code}: {response.text}")

    payload = {"vectors": {"size": vector_size, "distance": distance}}
    try:
        create_response = httpx.put(
            f"{url}/collections/{collection}", json=payload, timeout=10.0
        )
    except httpx.RequestError as exc:
        raise RAGError(502, f"Qdrant is unreachable at {qdrant_url}.") from exc

    if create_response.status_code not in (200, 201):
        raise RAGError(
            502, f"Qdrant create error {create_response.status_code}: {create_response.text}"
        )


def upsert_chunks(
    qdrant_url: str,
    collection: str,
    vectors: Iterable[List[float]],
    payloads: Iterable[dict],
) -> int:
    url = qdrant_url.rstrip("/")
    ids = []
    vector_list = []
    payload_list = []
    for vector, payload in zip(vectors, payloads):
        ids.append(str(uuid.uuid4()))
        vector_list.append(vector)
        payload_list.append(payload)
    if not ids:
        return 0

    body = {"batch": {"ids": ids, "vectors": vector_list, "payloads": payload_list}}
    try:
        response = httpx.put(
            f"{url}/collections/{collection}/points?wait=true",
            json=body,
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        raise RAGError(502, f"Qdrant is unreachable at {qdrant_url}.") from exc

    if response.status_code not in (200, 201):
        raise RAGError(
            502, f"Qdrant upsert error {response.status_code}: {response.text}"
        )

    return len(ids)


def search_chunks(
    qdrant_url: str,
    collection: str,
    query_vector: List[float],
    top_k: int,
) -> List[RetrievedChunk]:
    url = qdrant_url.rstrip("/")
    body = {"vector": query_vector, "limit": top_k, "with_payload": True}
    try:
        response = httpx.post(
            f"{url}/collections/{collection}/points/search",
            json=body,
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        raise RAGError(502, f"Qdrant is unreachable at {qdrant_url}.") from exc

    if response.status_code != 200:
        raise RAGError(
            502, f"Qdrant search error {response.status_code}: {response.text}"
        )

    data = response.json()
    results = []
    for item in data.get("result", []):
        payload = item.get("payload", {})
        results.append(
            RetrievedChunk(
                text=payload.get("text", ""),
                source=payload.get("source", ""),
                chunk_index=int(payload.get("chunk_index", 0)),
                score=float(item.get("score", 0.0)),
            )
        )
    return results


def build_context(chunks: Iterable[RetrievedChunk]) -> str:
    parts = []
    for chunk in chunks:
        header = f"Source: {chunk.source} (chunk {chunk.chunk_index})"
        parts.append(f"{header}\n{chunk.text}")
    return "\n\n---\n\n".join(parts)
