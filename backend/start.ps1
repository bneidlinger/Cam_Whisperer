# PlatoniCam - Startup Script (PowerShell)

$ErrorActionPreference = "Stop"

# Get paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Change to backend directory
Set-Location $ScriptDir

Write-Host ""
Write-Host " ============================================================" -ForegroundColor Cyan
Write-Host "  PlatoniCam - STARTUP SEQUENCE" -ForegroundColor Cyan
Write-Host " ============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python
Write-Host " [1/5] Checking Python installation..." -ForegroundColor White
try {
    $pythonVersion = python --version 2>&1
    Write-Host "       OK - $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "       ERROR: Python not found in PATH" -ForegroundColor Red
    Write-Host "       Please install Python 3.10+ and add to PATH" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2: Check/Create virtual environment
Write-Host " [2/5] Checking virtual environment..." -ForegroundColor White
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "       Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "       ERROR: Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "       Created virtual environment" -ForegroundColor Green
}
Write-Host "       OK - Virtual environment exists" -ForegroundColor Green

# Activate virtual environment
try {
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "       OK - Virtual environment activated" -ForegroundColor Green
} catch {
    Write-Host "       ERROR: Failed to activate virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 3: Check dependencies
Write-Host " [3/5] Checking dependencies..." -ForegroundColor White
$fastapi = pip show fastapi 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "       Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "       ERROR: Failed to install dependencies" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "       Dependencies installed" -ForegroundColor Green
}
Write-Host "       OK - Dependencies ready" -ForegroundColor Green

# Step 4: Check configuration
Write-Host " [4/5] Checking configuration..." -ForegroundColor White
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "       Creating .env from template..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "       NOTE: Edit .env to add your ANTHROPIC_API_KEY" -ForegroundColor Yellow
    } else {
        Write-Host "       WARNING: No .env file found" -ForegroundColor Yellow
    }
} else {
    Write-Host "       OK - Configuration file exists" -ForegroundColor Green
}

# Check for API key
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    if ($envContent -notmatch "ANTHROPIC_API_KEY=sk-") {
        Write-Host ""
        Write-Host " ============================================================" -ForegroundColor Yellow
        Write-Host "  WARNING: No Anthropic API key configured!" -ForegroundColor Yellow
        Write-Host "  The system will use heuristic fallback only." -ForegroundColor Yellow
        Write-Host "  Edit backend\.env to add: ANTHROPIC_API_KEY=sk-ant-..." -ForegroundColor Yellow
        Write-Host " ============================================================" -ForegroundColor Yellow
        Write-Host ""
    }
}

# Step 5: Launch services
Write-Host " [5/5] Launching services..." -ForegroundColor White
Write-Host ""

# Start frontend server in background
Write-Host "       Starting frontend server on port 3000..." -ForegroundColor White
$frontendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    python -m http.server 3000 2>&1
} -ArgumentList $ProjectRoot

Start-Sleep -Seconds 1

# Open browser
Write-Host "       Opening browser..." -ForegroundColor White
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host " ============================================================" -ForegroundColor Cyan
Write-Host "  PlatoniCam SERVICES RUNNING" -ForegroundColor Cyan
Write-Host " ============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend:  " -NoNewline; Write-Host "http://localhost:3000" -ForegroundColor Green
Write-Host "  Backend:   " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Green
Write-Host "  API Docs:  " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "  Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host " ============================================================" -ForegroundColor Cyan
Write-Host ""

# Start backend (blocks until Ctrl+C)
try {
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
} finally {
    # Cleanup: Stop frontend job
    Write-Host ""
    Write-Host " Shutting down frontend server..." -ForegroundColor Yellow
    Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $frontendJob -Force -ErrorAction SilentlyContinue
    Write-Host " All services stopped." -ForegroundColor Green
}
