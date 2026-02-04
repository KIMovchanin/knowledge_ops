#!/usr/bin/env bash
set -euo pipefail

docker compose -f infra/docker-compose.yml --profile mvp stop

docker compose -f infra/docker-compose.yml --profile mvp up -d --build
echo "Restarted MVP services."

ui_url="http://localhost:3000"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$ui_url" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
  open "$ui_url" >/dev/null 2>&1 &
fi
echo "Open UI: $ui_url"
