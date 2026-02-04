from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .config import get_settings
from .deps import resolve_llm_client
from .llm import LLMClient, LLMClientError, LLMResult
from .rag import (
    RAGError,
    build_context,
    chunk_text,
    embed_text,
    ensure_collection,
    extract_text,
    search_chunks,
    upsert_chunks,
)
from .storage import safe_upload_path

APP_VERSION = "0.1.0"

REQUEST_COUNT = Counter(
    "inference_requests_total",
    "Total inference requests",
    ["path", "method", "status"],
)
REQUEST_LATENCY = Histogram(
    "inference_request_latency_seconds",
    "Inference request latency in seconds",
    ["path"],
)

app = FastAPI(title="KnowledgeOps Inference", version=APP_VERSION)


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=100)
    use_rag: bool = True
    stream: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


class RetrievalInfo(BaseModel):
    top_k: int
    provider: str
    hybrid: bool = False


class ChatResponse(BaseModel):
    answer: str
    citations: list
    latency_ms: int
    model: str
    retrieval: RetrievalInfo


class UploadResponse(BaseModel):
    count: int
    total_bytes: int
    files: list[str]
    indexed_chunks: int


@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        duration = time.time() - start
        REQUEST_LATENCY.labels(request.url.path).observe(duration)
        REQUEST_COUNT.labels(request.url.path, request.method, str(status)).inc()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "inference", "version": APP_VERSION}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    retrieval_provider = "qdrant" if request.use_rag else "none"
    retrieval = RetrievalInfo(
        top_k=request.top_k, provider=retrieval_provider, hybrid=False
    )

    settings = get_settings()
    provider = (request.provider or settings.llm_provider).lower()
    api_key = request.api_key or None
    try:
        llm_client: LLMClient = resolve_llm_client(provider, request.model, api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    context = None
    citations: list = []
    if request.use_rag:
        try:
            query_vector = embed_text(
                settings.ollama_base_url, settings.embedding_model, request.query
            )
            ensure_collection(
                settings.qdrant_url, settings.qdrant_collection, len(query_vector)
            )
            results = search_chunks(
                settings.qdrant_url,
                settings.qdrant_collection,
                query_vector,
                request.top_k,
            )
            citations = [
                {
                    "source": chunk.source,
                    "chunk": chunk.chunk_index,
                    "score": chunk.score,
                    "text": chunk.text,
                }
                for chunk in results
            ]
            context = build_context(results)
        except RAGError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    start = time.time()
    try:
        result: LLMResult = llm_client.chat(
            request.query, request.session_id, context=context
        )
    except LLMClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    latency_ms = int((time.time() - start) * 1000)

    return ChatResponse(
        answer=result.answer,
        citations=citations,
        latency_ms=latency_ms,
        model=result.model,
        retrieval=retrieval,
    )


@app.post("/v1/files/upload", response_model=UploadResponse)
async def upload_files(files: list[UploadFile] = File(...)):
    settings = get_settings()
    base_dir = Path(settings.upload_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    total_bytes = 0
    indexed_chunks = 0

    for upload in files:
        if not upload.filename:
            continue
        try:
            target = safe_upload_path(base_dir, upload.filename)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid filename.") from None

        target.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with target.open("wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                size += len(chunk)
        await upload.close()

        total_bytes += size
        saved_files.append(str(target.relative_to(base_dir)))

        text = extract_text(target)
        if not text:
            continue

        chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            continue

        vectors = []
        payloads = []
        for idx, chunk in enumerate(chunks):
            try:
                vector = embed_text(
                    settings.ollama_base_url, settings.embedding_model, chunk
                )
            except RAGError as exc:
                raise HTTPException(
                    status_code=exc.status_code, detail=exc.message
                ) from exc
            vectors.append(vector)
            payloads.append(
                {
                    "text": chunk,
                    "source": str(target.relative_to(base_dir)),
                    "chunk_index": idx,
                }
            )

        if vectors:
            try:
                ensure_collection(
                    settings.qdrant_url, settings.qdrant_collection, len(vectors[0])
                )
                indexed_chunks += upsert_chunks(
                    settings.qdrant_url, settings.qdrant_collection, vectors, payloads
                )
            except RAGError as exc:
                raise HTTPException(
                    status_code=exc.status_code, detail=exc.message
                ) from exc

    return UploadResponse(
        count=len(saved_files),
        total_bytes=total_bytes,
        files=saved_files,
        indexed_chunks=indexed_chunks,
    )
