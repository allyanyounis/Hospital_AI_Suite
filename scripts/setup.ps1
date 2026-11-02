<#
.SYNOPSIS
  One-time setup: Python virtual environment, npm packages, PostgreSQL role + database, backend/.env and an admin account.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#>
param(
    [string]$PgBin = "C:\Program Files\PostgreSQL\17\bin",
    [string]$PgHost = "localhost",
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

Step "Python virtual environment (backend\.venv)"
if (-not (Test-Path $python)) { py -3.12 -m venv (Join-Path $backend ".venv") }
& $python -m pip install --quiet --upgrade pip
& $python -m pip install --quiet -e "$backend[dev]"

Step "Frontend packages (npm install)"
Push-Location $frontend
npm install --no-audit --no-fund
Pop-Location

Step "PostgreSQL role '$DbUser' and databases '$DbName', '${DbName}_test'"
$envFile = Join-Path $backend ".env"
if (Test-Path $envFile) {
    Write-Host "backend\.env already exists; leaving the database settings as they are."
} else {
    $psql = Join-Path $PgBin "psql.exe"
    $superPw = Read-Host "Password for the PostgreSQL 'postgres' superuser" -AsSecureString
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($superPw))
    $appPw = & $python -c "import secrets; print(secrets.token_urlsafe(24))"
    $sql = @"
DO `$`$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DbUser') THEN CREATE ROLE $DbUser LOGIN PASSWORD '$appPw';
  ELSE ALTER ROLE $DbUser PASSWORD '$appPw'; END IF;
END `$`$;
"@
    $sql | & $psql -w -h $PgHost -p $PgPort -U postgres -v ON_ERROR_STOP=1 -q
    foreach ($db in @($DbName, "${DbName}_test")) {
        $exists = & $psql -w -h $PgHost -p $PgPort -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$db'"
        if (-not $exists) { & $psql -w -h $PgHost -p $PgPort -U postgres -q -c "CREATE DATABASE $db OWNER $DbUser ENCODING 'UTF8';" }
    }
    Remove-Item Env:PGPASSWORD

    $secret = & $python -c "import secrets; print(secrets.token_urlsafe(48))"
    $template = Get-Content (Join-Path $backend ".env.example") -Raw
    $template = $template -replace "(?m)^DATABASE_URL=.*$", "DATABASE_URL=postgresql+psycopg://${DbUser}:${appPw}@${PgHost}:${PgPort}/${DbName}"
    $template = $template -replace "(?m)^SESSION_SECRET=.*$", "SESSION_SECRET=$secret"
    Set-Content -Path $envFile -Value $template -Encoding utf8
    Write-Host "Wrote backend\.env (add your ANTHROPIC_API_KEY, DEEPGRAM_API_KEY and VAPI_SECRET there)."
}

Step "Frontend settings (frontend\.env.local)"
$envLocal = Join-Path $frontend ".env.local"
if (-not (Test-Path $envLocal)) {
    Copy-Item (Join-Path $frontend ".env.example") $envLocal
    Write-Host "Created frontend\.env.local - add your VAPI public key and assistant id."
}

Step "Database tables and tests"
Push-Location $backend
& $python -c "from app.database import init_db; init_db(); print('Tables ready')"
& $python -m pytest -q
Pop-Location

Step "Admin account"
$create = Read-Host "Create an admin account now? (y/n)"
if ($create -eq "y") {
    $username = Read-Host "Username"
    $name = Read-Host "Display name (e.g. Dr. Rahman)"
    Push-Location $backend
    & $python -m app.users add $username --name "$name" --role admin
    Pop-Location
}

Write-Host "`nSetup complete. Start everything with:  powershell -File scripts\dev.ps1" -ForegroundColor Green
