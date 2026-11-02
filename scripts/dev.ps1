<#
.SYNOPSIS
  Starts the backend (FastAPI, port 8000) and the frontend (Next.js dev server) in two new windows.

.EXAMPLE
  powershell -File scripts\dev.ps1              # frontend on http://localhost:3004
  powershell -File scripts\dev.ps1 -WebPort 3005
#>
param([int]$WebPort = 3004, [int]$ApiPort = 8000)
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port $ApiPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontend'; `$env:BACKEND_URL='http://localhost:$ApiPort'; npx next dev -p $WebPort"

Write-Host "Backend:  http://localhost:$ApiPort/docs"
Write-Host "Frontend: http://localhost:$WebPort"
