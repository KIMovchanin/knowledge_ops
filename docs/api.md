# API

## Gateway health

```bash
curl http://localhost:8080/health
```

## Gateway chat

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"hello","use_rag":true,"top_k":5}'
```

### Using OpenAI or Gemini

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"hello","provider":"openai","model":"gpt-4o-mini","api_key":"YOUR_KEY"}'
```

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"hello","provider":"gemini","model":"gemini-2.5-flash","api_key":"YOUR_KEY"}'
```

## Inference docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
