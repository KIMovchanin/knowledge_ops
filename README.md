# KnowledgeOps

KnowledgeOps is a self-hosted, local-first LLM/RAG platform for chatting with your own documents. The project is designed as an educational playground for learning Docker, Ollama, FastAPI, Go services, vector search, and local AI application architecture.

The core idea is simple:
- ingest documents
- split them into chunks
- generate embeddings
- store them in Qdrant
- ask questions and receive answers with citations

The default setup runs locally and does not depend on a paid cloud service.

## What this project includes

- A local web UI for chatting with uploaded documents
- A Go-based gateway service for auth, rate limiting, proxying, and health checks
- A Python/FastAPI inference service for retrieval-augmented generation (RAG)
- Docker Compose profiles for an MVP stack and a fuller experimental stack
- Optional support for OpenAI or Gemini providers, while Ollama remains the primary local runtime

## Architecture overview

The repository is organized around a small set of services:

- `services/frontend-web` — simple web client for interacting with the system
- `services/gateway-go` — API gateway with JWT/dev auth, rate limiting, health, and metrics
- `services/inference-python` — FastAPI service for chat, document upload, embedding, retrieval, and response generation
- `services/ingestion-worker` — ingestion pipeline component for the fuller stack
- `infra/docker-compose.yml` — Docker Compose setup for the MVP and full profiles
- `pipelines/airflow` — orchestration for ingestion and evaluation workflows
- `docs/` — architecture, API, and design decision documents

The current MVP flow is:

1. The frontend sends a chat request to the gateway.
2. The gateway forwards the request to the inference service.
3. The inference service retrieves relevant chunks from Qdrant.
4. The response is generated using Ollama (or another configured provider).
5. The answer is returned to the user with relevant citations.

## Tech stack

- Docker / Docker Compose
- Ollama (local LLM and embeddings)
- Qdrant (vector database)
- PostgreSQL
- FastAPI (Python)
- Go (gateway service)
- React + Vite (frontend)

## Prerequisites

Before running the project locally, make sure you have:

- Docker installed and running
- Docker Compose available
- Ollama installed locally

## Quick start

### 1) Install and prepare Ollama

```bash
ollama serve
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### 2) Prepare environment variables

```bash
cp .env.example .env
```

### 3) Start the MVP stack

On Linux/macOS:

```bash
./run.sh
```

On Windows PowerShell:

```powershell
./run.ps1
```

### 4) Open the app

Once the stack is running, you can access:

- UI: http://localhost:3000
- Gateway health: http://localhost:8080/health
- Inference API docs: http://localhost:8000/docs

## Example API usage

### Health check

```bash
curl http://localhost:8080/health
```

Expected result: an HTTP 200 response from the gateway.

### Chat request

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"hello","use_rag":true,"top_k":5}'
```

### Upload files for RAG

```bash
curl -X POST http://localhost:8080/v1/files/upload \
  -F "files=@./notes/example.txt"
```

## Development commands

Useful commands for local development:

```bash
make up
make down
make logs
make lint
make test
make fmt
```

## Repository structure

```text
.
├── docs/                  # architecture, API, and design documentation
├── infra/                 # Docker Compose configuration
├── observability/         # monitoring-related files
├── pipelines/             # Airflow DAGs and workflow definitions
├── services/
│   ├── frontend-web/      # web UI
│   ├── gateway-go/        # Go gateway service
│   ├── inference-python/  # FastAPI inference service
│   └── ingestion-worker/  # ingestion worker (planned/full profile)
├── .env.example           # example environment configuration
├── Makefile               # common development tasks
├── run.sh / run.ps1       # startup scripts
```

## Documentation

The project already contains a set of design documents:

- `docs/architecture.md` — overall architecture and request flow
- `docs/api.md` — API examples and endpoints
- `docs/DECISIONS.md` — key project decisions and defaults

## Roadmap

Current focus:

- stabilize the MVP stack
- improve RAG quality and retrieval behavior
- add ingestion pipeline support in the full profile
- add Airflow/Spark/MinIO-based data workflows
- expand observability and evaluation tooling

## Notes

This project is still evolving and is primarily meant as a learning project. The current implementation focuses on local-first deployment, modular service boundaries, and a practical path from raw documents to conversational AI.
