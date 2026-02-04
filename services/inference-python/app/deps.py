from __future__ import annotations

from functools import lru_cache

from .config import get_settings
from .llm import APIClient, GeminiClient, LLMClient, OpenAIClient, OllamaClient


@lru_cache
def get_settings_cached():
    return get_settings()


def resolve_llm_client(provider: str, model: str | None, api_key: str | None) -> LLMClient:
    settings = get_settings_cached()
    normalized = provider.lower().strip()

    if normalized == "ollama":
        return OllamaClient(settings.ollama_base_url, model or settings.ollama_chat_model)
    if normalized == "openai":
        return OpenAIClient(
            settings.openai_base_url,
            model or settings.openai_model,
            api_key or settings.openai_api_key,
        )
    if normalized == "gemini":
        return GeminiClient(
            settings.gemini_base_url,
            model or settings.gemini_model,
            api_key or settings.gemini_api_key,
        )
    if normalized == "api":
        return APIClient(model or settings.ollama_chat_model)

    raise ValueError(f"Unsupported LLM_PROVIDER: {normalized}")
