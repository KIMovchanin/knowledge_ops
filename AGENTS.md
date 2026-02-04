# KnowledgeOps — AGENTS.md

## What we are building
Self-hosted (local-first) LLM/RAG platform:
- ingest docs -> chunk -> embeddings -> Qdrant index
- chat endpoint returns answer + citations (sources)
- Airflow orchestrates ingestion/eval pipelines
- Spark job produces Parquet from raw docs (stored in MinIO)
- Optional: API LLM provider adapter, but primary is Ollama local

## Key decisions
- Local LLM runtime: Ollama (user runs it locally)
- Vector DB: Qdrant
- Primary mode: local-first self-hosted (no paid server)
- Frontend: local web UI (clean/original)
- Compose profiles:
  - mvp: minimal stack
  - full: adds kafka, mongo, minio, airflow, spark, prometheus, grafana

## Architecture
- services/gateway-go: JWT dev auth, rate limit, proxy to inference, audit logs
- services/inference-python: FastAPI RAG, retrieval, rerank (later), streaming (later), /docs and /redoc
- services/ingestion-worker: parse docs, chunk, embed via Ollama embeddings, upsert to Qdrant, write metadata to Postgres/Mongo/MinIO
- services/frontend-web: chat UI calling gateway
- pipelines/airflow: DAGs for ingestion and ETL/eval

## Repo structure (must follow)
- services/gateway-go
- services/inference-python
- services/ingestion-worker
- services/frontend-web
- pipelines/airflow/dags
- infra/docker-compose.yml
- observability/prometheus + grafana dashboards
- docs (architecture.md, api.md, DECISIONS.md)

## Working rules
- Small diffs; one task = one PR-sized chunk.
- Always include verification steps: commands + expected outputs.
- No secrets committed; use .env + .env.example.
- Add tests for critical logic (happy path + one failure path).
- Add /health and /metrics endpoints for services.
- Record defaults in docs/DECISIONS.md.

## Quality gates (Definition of Done)
- lint + tests pass for touched components
- docker build works for touched services
- docker-compose up works in "mvp" profile
- docs updated if API changes
