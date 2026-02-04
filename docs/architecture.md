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
3. If `use_rag=true`, Inference embeds the query, retrieves top K chunks from Qdrant, and builds context.
4. Inference calls Ollama (or selected provider) with the context.
5. Inference returns answer + citations + retrieval metadata to Gateway.
6. Gateway returns the response to the Frontend.

## /v1/files/upload sequence

1. Browser uploads a folder of files to Gateway.
2. Gateway proxies files to Inference.
3. Inference saves files to the upload volume.
4. Inference chunks text, embeds it, and upserts vectors into Qdrant.
