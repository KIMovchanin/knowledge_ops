$ErrorActionPreference = "Stop"

docker compose -f infra/docker-compose.yml --profile mvp down -v
Write-Host "Removed MVP services and volumes."
