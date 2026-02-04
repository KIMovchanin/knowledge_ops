from fastapi.testclient import TestClient

from app.deps import get_llm_client
from app.llm import LLMClient, LLMResult
from app.main import app


class StubClient(LLMClient):
    def chat(self, query: str, session_id=None) -> LLMResult:
        return LLMResult(answer=f"echo:{query}", model="ollama:stub")


def test_chat_contract():
    app.dependency_overrides[get_llm_client] = lambda: StubClient()
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
    app.dependency_overrides.clear()


def test_chat_streaming_not_supported():
    client = TestClient(app)
    response = client.post("/v1/chat", json={"query": "hello", "stream": True})
    assert response.status_code == 400
