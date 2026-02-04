from __future__ import annotations

import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .config import get_settings
from .deps import resolve_llm_client
from .llm import LLMClient, LLMClientError, LLMResult

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
    retrieval = RetrievalInfo(top_k=request.top_k, provider=retrieval_provider, hybrid=False)

    settings = get_settings()
    provider = (request.provider or settings.llm_provider).lower()
    api_key = request.api_key or None
    try:
        llm_client: LLMClient = resolve_llm_client(provider, request.model, api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    start = time.time()
    try:
        result: LLMResult = llm_client.chat(request.query, request.session_id)
    except LLMClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    latency_ms = int((time.time() - start) * 1000)

    return ChatResponse(
        answer=result.answer,
        citations=[],
        latency_ms=latency_ms,
        model=result.model,
        retrieval=retrieval,
    )
