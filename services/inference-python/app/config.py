from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    ollama_base_url: str
    ollama_chat_model: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
        ollama_chat_model=os.getenv("OLLAMA_CHAT_MODEL", "llama3.2:3b"),
    )
