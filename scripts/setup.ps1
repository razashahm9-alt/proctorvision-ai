[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VirtualEnvironment = Join-Path $ProjectRoot ".venv"
$Python = Join-Path $VirtualEnvironment "Scripts\python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path $Python)) {
    Write-Host "Creating the Python 3.12 virtual environment..." -ForegroundColor Cyan
    py -3.12 -m venv $VirtualEnvironment
    if ($LASTEXITCODE -ne 0) { throw "Python virtual-environment creation failed." }
}

Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $Python -m pip install -r (Join-Path $ProjectRoot "requirements-lock.txt")
if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }
& $Python -m pip install -r (Join-Path $ProjectRoot "backend\requirements-openvino.txt")
if ($LASTEXITCODE -ne 0) { throw "OpenVINO dependency installation failed." }

$PytorchModel = Join-Path $ProjectRoot "yolo11s.pt"
if (-not (Test-Path $PytorchModel)) {
    Write-Host "Downloading the official YOLO11s weights..." -ForegroundColor Cyan
    & $Python -c "from ultralytics import YOLO; YOLO('yolo11s.pt')"
    if ($LASTEXITCODE -ne 0) { throw "YOLO11s download failed." }
}

$OpenVinoDirectory = Join-Path $ProjectRoot "yolo11s_openvino_model"
$OpenVinoXml = Get-ChildItem $OpenVinoDirectory -Filter *.xml -ErrorAction SilentlyContinue
$OpenVinoBin = Get-ChildItem $OpenVinoDirectory -Filter *.bin -ErrorAction SilentlyContinue
if (-not $OpenVinoXml -or -not $OpenVinoBin) {
    Write-Host "Preparing the OpenVINO model..." -ForegroundColor Cyan
    & $Python (Join-Path $ProjectRoot "backend\scripts\prepare_openvino.py")
    if ($LASTEXITCODE -ne 0) { throw "OpenVINO model preparation failed." }
}

Write-Host "Installing and building the frontend..." -ForegroundColor Cyan
Push-Location (Join-Path $ProjectRoot "frontend")
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

Write-Host "Running backend verification..." -ForegroundColor Cyan
& $Python -m pytest (Join-Path $ProjectRoot "backend\tests") -q
if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }

Write-Host "Setup and verification completed successfully." -ForegroundColor Green
Write-Host "Start the application with: .\scripts\start.ps1"
