$ErrorActionPreference = "Stop"

docker compose -f infra/docker-compose.yml --profile mvp stop

docker compose -f infra/docker-compose.yml --profile mvp up -d --build
Write-Host "Restarted MVP services."

try {
    Start-Process "http://localhost:3000" | Out-Null
} catch {
    Write-Host "Could not open browser automatically. Open manually: http://localhost:3000"
}
