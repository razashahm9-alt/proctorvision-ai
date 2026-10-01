[CmdletBinding()]
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$FrontendIndex = Join-Path $ProjectRoot "frontend\dist\index.html"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\scripts\setup.ps1 first."
}
if (-not (Test-Path $FrontendIndex)) {
    throw "Production frontend not found. Run .\scripts\setup.ps1 first."
}

Set-Location $ProjectRoot
$env:PROCTORVISION_SERVE_FRONTEND = "true"

Write-Host "Starting ProctorVision AI 0.8.1..." -ForegroundColor Cyan
Write-Host "Open http://${HostAddress}:$Port in the browser."
Write-Host "Press Ctrl+C to stop the application."

& $Python -m uvicorn app.main:app --app-dir backend --host $HostAddress --port $Port
