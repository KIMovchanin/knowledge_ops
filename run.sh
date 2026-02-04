#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "==> $*"
}

log "Checking Docker"
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker and try again."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker Engine is not running. Start Docker and retry."
  exit 1
fi

if [ ! -f .env ]; then
  log "Creating .env from .env.example"
  cp .env.example .env
fi

log "Checking Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found. Install Ollama from https://ollama.com and try again."
  exit 1
fi

check_ollama() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- http://localhost:11434/api/tags >/dev/null 2>&1
  else
    return 2
  fi
}

start_ollama() {
  if pgrep -f "ollama serve" >/dev/null 2>&1; then
    return 0
  fi
  if command -v nohup >/dev/null 2>&1; then
    nohup ollama serve >/tmp/ollama.log 2>&1 &
  else
    ollama serve >/tmp/ollama.log 2>&1 &
  fi
}

if ! check_ollama; then
  log "Starting Ollama"
  if ! start_ollama; then
    echo "Warning: failed to start Ollama automatically."
  fi

  for _ in 1 2 3 4 5; do
    sleep 1
    if check_ollama; then
      break
    fi
  done
fi

if check_ollama; then
  if command -v curl >/dev/null 2>&1; then
    tags=$(curl -fsS http://localhost:11434/api/tags || true)
  else
    tags=$(wget -qO- http://localhost:11434/api/tags || true)
  fi
  if ! echo "$tags" | grep -q "llama3.2:3b"; then
    log "Pulling llama3.2:3b"
    if ! ollama pull llama3.2:3b; then
      echo "Warning: failed to pull llama3.2:3b. Run: ollama pull llama3.2:3b"
    fi
  fi
  if ! echo "$tags" | grep -q "nomic-embed-text"; then
    log "Pulling nomic-embed-text"
    if ! ollama pull nomic-embed-text; then
      echo "Warning: failed to pull nomic-embed-text. Run: ollama pull nomic-embed-text"
    fi
  fi
else
  echo "Warning: Ollama is not reachable at http://localhost:11434."
  echo "Start it manually in another terminal: ollama serve"
fi

log "Starting KnowledgeOps MVP"
docker compose -f infra/docker-compose.yml --profile mvp up -d --build

log "Done"
ui_url="http://localhost:3000"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$ui_url" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  open "$ui_url" >/dev/null 2>&1 &
fi
echo "Open UI: $ui_url"
echo "Gateway: http://localhost:8080/health"
