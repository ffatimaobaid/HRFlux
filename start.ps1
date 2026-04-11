# HRFlux - One-Command Startup Script
# Runs backend and frontend in separate terminals

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $RootDir "venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$PipExe = Join-Path $VenvPath "Scripts\pip.exe"
$RequirementsFile = Join-Path $RootDir "requirements.txt"
$FrontendDir = Join-Path $RootDir "frontend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   HRFlux Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check / Create virtualenv
if (-Not (Test-Path $PythonExe)) {
    Write-Host "[1/3] Virtual environment not found. Creating venv..." -ForegroundColor Yellow
    python -m venv "$VenvPath"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment. Make sure Python is installed and on PATH." -ForegroundColor Red
        exit 1
    }
    Write-Host "      venv created successfully." -ForegroundColor Green
}
else {
    Write-Host "[1/3] Virtual environment found." -ForegroundColor Green
}

# Step 2: Check / Install requirements
Write-Host "[2/3] Checking Python requirements..." -ForegroundColor Yellow
$MissingPackages = & "$PipExe" install -r "$RequirementsFile" --dry-run 2>&1 | Select-String "Would install"

if ($MissingPackages) {
    Write-Host "      Missing packages detected. Installing requirements..." -ForegroundColor Yellow
    & "$PipExe" install -r "$RequirementsFile"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install requirements." -ForegroundColor Red
        exit 1
    }
    Write-Host "      Requirements installed." -ForegroundColor Green
}
else {
    Write-Host "      Verifying installed packages..." -ForegroundColor DarkGray
    & "$PipExe" check 2>&1 | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray }
    Write-Host "      All requirements already satisfied." -ForegroundColor Green
}

# Step 3: Initialize Database
Write-Host "[3/4] Initializing Database and Seeding Data..." -ForegroundColor Yellow
& "$PythonExe" backend\seed_data.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Database initialization failed." -ForegroundColor Red
    exit 1
}
Write-Host "      Database initialized successfully." -ForegroundColor Green
Write-Host ""

# Step 4: Launch Backend and Frontend in separate terminals
Write-Host "[4/4] Starting Backend and Frontend..." -ForegroundColor Yellow
Write-Host ""

# Launch Backend in a new PowerShell terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    Set-Location '$RootDir'; 
    Write-Host '--- HRFlux Backend ---' -ForegroundColor Cyan;
    & '$PythonExe' backend\main.py
"

# Small delay so terminals don't spawn simultaneously
Start-Sleep -Seconds 2

# Launch Frontend in a new PowerShell terminal
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    Set-Location '$FrontendDir'; 
    Write-Host '--- HRFlux Frontend ---' -ForegroundColor Cyan;
    npm run dev
"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Servers starting in separate windows!" -ForegroundColor Green
Write-Host "  Backend  -> http://localhost:8000"     -ForegroundColor White
Write-Host "  Frontend -> http://localhost:3000"     -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
