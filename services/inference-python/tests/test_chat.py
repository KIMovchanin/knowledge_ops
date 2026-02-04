from fastapi.testclient import TestClient

import app.main as main
from app.llm import LLMClient, LLMClientError, LLMResult
from app.main import app


class StubClient(LLMClient):
    def chat(self, query: str, session_id=None, context=None) -> LLMResult:
        return LLMResult(answer=f"echo:{query}", model="ollama:stub")


ORIGINAL_RESOLVER = main.resolve_llm_client


def test_chat_contract():
    main.resolve_llm_client = lambda *_args, **_kwargs: StubClient()
    client = TestClient(app)
    response = client.post(
        "/v1/chat",
        json={"query": "hello", "top_k": 3, "use_rag": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "echo:hello"
    assert data["citations"] == []
    assert data["model"] == "ollama:stub"
    assert data["retrieval"] == {"top_k": 3, "provider": "none", "hybrid": False}
    assert isinstance(data["latency_ms"], int)
    main.resolve_llm_client = ORIGINAL_RESOLVER


def test_chat_llm_error():
    class ErrorClient(LLMClient):
        def chat(self, query: str, session_id=None, context=None) -> LLMResult:
            raise LLMClientError(502, "Ollama unreachable")

    main.resolve_llm_client = lambda *_args, **_kwargs: ErrorClient()
    client = TestClient(app)
    response = client.post("/v1/chat", json={"query": "hello", "use_rag": False})
    assert response.status_code == 502
    assert response.json()["detail"] == "Ollama unreachable"
    main.resolve_llm_client = ORIGINAL_RESOLVER
