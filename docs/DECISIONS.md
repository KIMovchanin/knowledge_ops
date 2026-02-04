# Decisions

- Local-first (Option A): everything runs on the user laptop via Docker Compose.
- LLM runtime: Ollama on the host machine (not containerized).
- Optional cloud LLMs: OpenAI and Gemini via user-provided API keys.
- Vector DB: Qdrant for embeddings and retrieval.
- Inference service tooling: Poetry for dependency management; ruff + black for lint/format.
- Go service tooling: Go modules.
- Default ports and base URLs:
  - Frontend: http://localhost:3000
  - Gateway: http://localhost:8080
  - Inference: http://localhost:8000
  - Qdrant: http://localhost:6333
  - Postgres: localhost:5432
  - Ollama (host): http://host.docker.internal:11434
  - OpenAI API: https://api.openai.com (default model: gpt-4o-mini)
  - Gemini API: https://generativelanguage.googleapis.com (default model: gemini-2.5-flash)
  - Qdrant collection: knowledgeops_chunks
  - Embeddings model (Ollama): nomic-embed-text
  - Chunking defaults: size 200, overlap 40
