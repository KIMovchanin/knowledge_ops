$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message"
}

$ollamaModels = "D:\.ollama"

Write-Step "Checking Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker not found. Install Docker Desktop and try again."
    exit 1
}

try {
    docker info | Out-Null
} catch {
    Write-Host "Docker Engine is not running. Start Docker Desktop and retry."
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Step "Creating .env from .env.example"
    Copy-Item ".env.example" ".env"
}

Write-Step "Checking Ollama"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama not found. Install Ollama from https://ollama.com and try again."
    exit 1
}

$env:OLLAMA_MODELS = $ollamaModels
$env:OLLAMA_HOST = "0.0.0.0:11434"

function Get-OllamaTags {
    try {
        return Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2
    } catch {
        return $null
    }
}

$tags = Get-OllamaTags
if (-not $tags) {
    Write-Step "Starting Ollama"
    try {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden | Out-Null
    } catch {
        Write-Host "Warning: failed to start Ollama automatically."
    }

    Start-Sleep -Seconds 2
    $tags = Get-OllamaTags
}

if (-not $tags) {
    Write-Host "Warning: Ollama is not reachable at http://localhost:11434."
    Write-Host "Start it manually in another terminal with:"
    Write-Host "  `$env:OLLAMA_MODELS=\"$ollamaModels\"; `$env:OLLAMA_HOST=\"0.0.0.0:11434\"; ollama serve"
} else {
    $modelFound = $false
    $embedFound = $false
    if ($tags.models) {
        foreach ($model in $tags.models) {
            if ($model.name -eq "llama3.2:3b") {
                $modelFound = $true
            }
            if ($model.name -eq "nomic-embed-text:latest") {
                $embedFound = $true
            }
        }
    }

    if (-not $modelFound) {
        Write-Step "Pulling llama3.2:3b"
        try {
            ollama pull llama3.2:3b | Out-Null
        } catch {
            Write-Host "Warning: failed to pull llama3.2:3b. Run: ollama pull llama3.2:3b"
        }
    }

    if (-not $embedFound) {
        Write-Step "Pulling nomic-embed-text:latest"
        try {
            ollama pull nomic-embed-text:latest | Out-Null
        } catch {
            Write-Host "Warning: failed to pull nomic-embed-text:latest. Run: ollama pull nomic-embed-text:latest"
        }
    }
}

Write-Step "Starting KnowledgeOps MVP"
docker compose -f infra/docker-compose.yml --profile mvp up -d --build

Write-Step "Done"
Write-Host "Open UI: http://localhost:3000"
Write-Host "Gateway: http://localhost:8080/health"

try {
    Start-Process "http://localhost:3000" | Out-Null
} catch {
    Write-Host "Could not open browser automatically. Open manually: http://localhost:3000"
}
