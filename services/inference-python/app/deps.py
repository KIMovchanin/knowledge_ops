from __future__ import annotations

from functools import lru_cache

from .config import get_settings
from .llm import APIClient, LLMClient, OllamaClient


@lru_cache
def get_llm_client() -> LLMClient:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "ollama":
        return OllamaClient(settings.ollama_base_url, settings.ollama_chat_model)
    if provider == "api":
        return APIClient(settings.ollama_chat_model)
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
