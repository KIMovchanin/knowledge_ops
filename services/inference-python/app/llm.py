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

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMClientError(502, "Invalid JSON response from Ollama.") from exc
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


class OpenAIClient(LLMClient):
    def __init__(self, base_url: str, model: str, api_key: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key.strip()
        self.timeout = httpx.Timeout(timeout_seconds, connect=5.0)

    def chat(self, query: str, session_id: Optional[str] = None) -> LLMResult:
        if not self.api_key:
            raise LLMClientError(401, "OpenAI API key is required for provider openai.")

        payload = {"model": self.model, "messages": [{"role": "user", "content": query}]}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.post("/v1/chat/completions", json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise LLMClientError(502, f"OpenAI is unreachable at {self.base_url}.") from exc

        if response.status_code != 200:
            raise LLMClientError(502, f"OpenAI error {response.status_code}: {response.text}")

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMClientError(502, "Invalid JSON response from OpenAI.") from exc

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
        if not content:
            raise LLMClientError(502, "OpenAI response missing message content.")

        return LLMResult(answer=content, model=f"openai:{self.model}")


class GeminiClient(LLMClient):
    def __init__(self, base_url: str, model: str, api_key: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key.strip()
        self.timeout = httpx.Timeout(timeout_seconds, connect=5.0)

    def chat(self, query: str, session_id: Optional[str] = None) -> LLMResult:
        if not self.api_key:
            raise LLMClientError(401, "Gemini API key is required for provider gemini.")

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": query}],
                }
            ]
        }
        headers = {"x-goog-api-key": self.api_key}
        path = f"/v1beta/models/{self.model}:generateContent"

        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.post(path, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise LLMClientError(502, f"Gemini is unreachable at {self.base_url}.") from exc

        if response.status_code != 200:
            raise LLMClientError(502, f"Gemini error {response.status_code}: {response.text}")

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMClientError(502, "Invalid JSON response from Gemini.") from exc

        candidates = data.get("candidates", [])
        if not candidates:
            raise LLMClientError(502, "Gemini response missing candidates.")
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [part.get("text", "") for part in parts if part.get("text")]
        content = "\n".join(text_parts).strip()
        if not content:
            raise LLMClientError(502, "Gemini response missing text content.")

        return LLMResult(answer=content, model=f"gemini:{self.model}")
