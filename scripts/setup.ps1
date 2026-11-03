<#
.SYNOPSIS
  One-time setup: PostgreSQL in Docker, Python virtual environment, npm packages, backend/.env, schema migrations
  and an admin account.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#>
param(
    [int]$PgPort = 5432,
    [string]$DbName = "hospital_ai",
    [string]$DbUser = "hospital_ai"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }

Step "PostgreSQL container (docker compose: databases '$DbName' and '${DbName}_test')"
$rootEnv = Join-Path $root ".env"
if (-not (Test-Path $rootEnv)) {
    # Credentials for the container; docker compose reads this file. Never committed.
    # Postgres only applies them when the data volume is created, so an existing volume keeps the compose defaults.
    docker volume inspect hospital_ai_pgdata *> $null
    if ($LASTEXITCODE -eq 0) {
        $dbPw = "hospital_ai"
    } else {
        $dbPw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    }
    Set-Content -Path $rootEnv -Encoding ascii -Value @("POSTGRES_USER=$DbUser", "POSTGRES_PASSWORD=$dbPw", "POSTGRES_DB=$DbName", "POSTGRES_PORT=$PgPort")
    Write-Host "Wrote .env with the container's database credentials."
}
$dbEnv = @{}
Get-Content $rootEnv | Where-Object { $_ -match "^\s*([A-Z_]+)=(.*)$" } | ForEach-Object { $dbEnv[$Matches[1]] = $Matches[2] }
Push-Location $root
docker compose up -d db
Pop-Location
Write-Host -NoNewline "Waiting for the database"
for ($i = 0; $i -lt 60; $i++) {
    if ((docker inspect -f "{{.State.Health.Status}}" hospital_ai_db) -eq "healthy") { break }
    Write-Host -NoNewline "."; Start-Sleep -Seconds 2
}
Write-Host ""

Step "Python virtual environment (backend\.venv)"
if (-not (Test-Path $python)) { py -3.12 -m venv (Join-Path $backend ".venv") }
& $python -m pip install --quiet --upgrade pip
& $python -m pip install --quiet -r (Join-Path $backend "requirements-dev.txt")   # pinned versions
& $python -m pip install --quiet --no-deps -e $backend

Step "Frontend packages (npm install)"
Push-Location $frontend
npm install --no-audit --no-fund
Pop-Location

Step "Backend settings (backend\.env)"
$envFile = Join-Path $backend ".env"
if (Test-Path $envFile) {
    Write-Host "backend\.env already exists; leaving it as it is."
} else {
    # 127.0.0.1, not localhost: on Windows "localhost" tries IPv6 first and the container listens on IPv4 only
    $url = "postgresql+psycopg://$($dbEnv.POSTGRES_USER):$($dbEnv.POSTGRES_PASSWORD)@127.0.0.1:$($dbEnv.POSTGRES_PORT)/$($dbEnv.POSTGRES_DB)"
    $secret = & $python -c "import secrets; print(secrets.token_urlsafe(48))"
    $template = Get-Content (Join-Path $backend ".env.example") -Raw
    $template = $template -replace "(?m)^DATABASE_URL=.*$", "DATABASE_URL=$url"
    $template = $template -replace "(?m)^SESSION_SECRET=.*$", "SESSION_SECRET=$secret"
    Set-Content -Path $envFile -Value $template -Encoding utf8
    Write-Host "Wrote backend\.env (set NOTE_PROVIDER and its key - ANTHROPIC_API_KEY or GROQ_API_KEY - plus DEEPGRAM_API_KEY and VAPI_SECRET)."
}

Step "Frontend settings (frontend\.env.local)"
$envLocal = Join-Path $frontend ".env.local"
if (-not (Test-Path $envLocal)) {
    Copy-Item (Join-Path $frontend ".env.example") $envLocal
    Write-Host "Created frontend\.env.local - add your VAPI public key and assistant id."
}

Step "Database schema (alembic upgrade head) and tests"
Push-Location $backend
& $python -m app migrate
& $python -m pytest -q
Pop-Location

Step "Admin account"
$create = Read-Host "Create an admin account now? (y/n)"
if ($create -eq "y") {
    $username = Read-Host "Username"
    $name = Read-Host "Display name (e.g. Dr. Rahman)"
    Push-Location $backend
    & $python -m app users add $username --name "$name" --role admin
    Pop-Location
}

Write-Host "`nSetup complete. Start everything with:  powershell -File scripts\dev.ps1" -ForegroundColor Green
