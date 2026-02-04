# Architecture

```
Browser
  |
  v
Frontend Web (Vite + React)
  |
  v
Gateway (Go)  ----->  /metrics
  |
  v
Inference (FastAPI)  ----->  /docs /redoc /metrics
  |
  v
Ollama (host)

Inference also connects to:
- Qdrant
- Postgres
```

## /v1/chat sequence

1. Browser sends a chat request to the Gateway.
2. Gateway validates JWT (if configured), rate limits, and proxies to Inference.
3. Inference calls Ollama for the response.
4. Inference returns answer + retrieval metadata to Gateway.
5. Gateway returns the response to the Frontend.
