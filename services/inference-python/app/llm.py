from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass(frozen=True)
class LLMResult:
    answer: str
    model: str


class LLMClientError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class LLMClient:
    def chat(self, query: str, session_id: Optional[str] = None) -> LLMResult:
        raise NotImplementedError


class OllamaClient(LLMClient):
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_seconds, connect=5.0),
        )

    def chat(self, query: str, session_id: Optional[str] = None) -> LLMResult:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": query}],
            "stream": False,
        }
        try:
            response = self.client.post("/api/chat", json=payload)
        except httpx.RequestError as exc:
            raise LLMClientError(
                502,
                (
                    "Ollama is unreachable at "
                    f"{self.base_url}. Start it with `ollama serve` on the host."
                ),
            ) from exc

        if response.status_code != 200:
            raise LLMClientError(
                502,
                f"Ollama error {response.status_code}: {response.text}",
            )

        data = response.json()
        content = data.get("message", {}).get("content")
        if not content:
            raise LLMClientError(502, "Ollama response missing message content.")

        return LLMResult(answer=content, model=f"ollama:{self.model}")


class APIClient(LLMClient):
    def __init__(self, model: str = "unknown") -> None:
        self.model = model

    def chat(self, query: str, session_id: Optional[str] = None) -> LLMResult:
        raise NotImplementedError(
            "LLM_PROVIDER=api is not implemented in the MVP. "
            "Set LLM_PROVIDER=ollama to use the local Ollama runtime."
        )
