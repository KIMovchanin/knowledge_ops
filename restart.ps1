$ErrorActionPreference = "Stop"

docker compose -f infra/docker-compose.yml --profile mvp stop

docker compose -f infra/docker-compose.yml --profile mvp up -d --build
Write-Host "Restarted MVP services."
