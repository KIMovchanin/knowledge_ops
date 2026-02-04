#!/usr/bin/env bash
set -euo pipefail

docker compose -f infra/docker-compose.yml --profile mvp stop
echo "Stopped MVP services (data preserved)."
