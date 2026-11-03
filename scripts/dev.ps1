<#
.SYNOPSIS
  Starts everything for local development: the PostgreSQL container, the backend (FastAPI) and the frontend
  (Next.js dev server), the last two in their own windows. Settings come from backend\.env and frontend\.env.local.

.EXAMPLE
  powershell -File scripts\dev.ps1              # frontend on http://localhost:3004, API on http://localhost:8000
  powershell -File scripts\dev.ps1 -WebPort 3005
#>
param([int]$WebPort = 3004, [int]$ApiPort = 8000)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

foreach ($required in @((Join-Path $backend ".venv\Scripts\python.exe"), (Join-Path $backend ".env"), (Join-Path $frontend "node_modules"))) {
    if (-not (Test-Path $required)) { throw "Missing $required - run scripts\setup.ps1 first." }
}

Write-Host "==> PostgreSQL container" -ForegroundColor Cyan
Push-Location $root
docker compose up -d db
Pop-Location
for ($i = 0; $i -lt 60; $i++) {
    if ((docker inspect -f "{{.State.Health.Status}}" hospital_ai_db) -eq "healthy") { break }
    Start-Sleep -Seconds 2
}

# The backend applies pending migrations on start. The frontend proxies /api/* to the backend and opens
# WebSockets on the backend's port directly, so both are told where it is.
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port $ApiPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontend'; `$env:BACKEND_URL='http://127.0.0.1:$ApiPort'; `$env:NEXT_PUBLIC_BACKEND_PORT='$ApiPort'; npx next dev -p $WebPort"

Write-Host "Backend:  http://localhost:$ApiPort/docs"
Write-Host "Frontend: http://localhost:$WebPort"
