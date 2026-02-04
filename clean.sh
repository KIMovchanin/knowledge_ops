#!/usr/bin/env bash
set -euo pipefail

docker compose -f infra/docker-compose.yml --profile mvp down -v
echo "Removed MVP services and volumes."
