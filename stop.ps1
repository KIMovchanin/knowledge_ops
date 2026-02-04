$ErrorActionPreference = "Stop"

docker compose -f infra/docker-compose.yml --profile mvp stop
Write-Host "Stopped MVP services (data preserved)."
