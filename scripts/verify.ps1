[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\scripts\setup.ps1 first."
}

Set-Location $ProjectRoot
Write-Host "Running backend tests..." -ForegroundColor Cyan
& $Python -m pytest .\backend\tests -v
if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }

Write-Host "Running frontend tests and production build..." -ForegroundColor Cyan
Push-Location .\frontend
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
    npm test
    if ($LASTEXITCODE -ne 0) { throw "Frontend tests failed." }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
}
finally {
    Pop-Location
}

Write-Host "All Phase 8.1 verification checks passed." -ForegroundColor Green
