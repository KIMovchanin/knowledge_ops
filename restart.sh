#!/usr/bin/env bash
set -euo pipefail

docker compose -f infra/docker-compose.yml --profile mvp stop

docker compose -f infra/docker-compose.yml --profile mvp up -d --build
echo "Restarted MVP services."
