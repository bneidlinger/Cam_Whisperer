@echo off
setlocal EnableDelayedExpansion

echo.
echo  ============================================================
echo   CAMOPT AI v0.2 - STARTUP SEQUENCE
echo  ============================================================
echo.

REM Get the script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Change to backend directory
cd /d "%SCRIPT_DIR%"

echo  [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo        ERROR: Python not found in PATH
    echo        Please install Python 3.10+ and add to PATH
    pause
    exit /b 1
)
echo        OK - Python found

echo  [2/5] Checking virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo        Virtual environment not found. Creating...
    python -m venv venv
    if errorlevel 1 (
        echo        ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo        Created virtual environment
)
echo        OK - Virtual environment exists

REM Activate virtual environment
call venv\Scripts\activate.bat
if not defined VIRTUAL_ENV (
    echo        ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo        OK - Virtual environment activated

echo  [3/5] Checking dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo        Installing dependencies...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo        ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo        Dependencies installed
)
echo        OK - Dependencies ready

echo  [4/5] Checking configuration...
if not exist ".env" (
    if exist ".env.example" (
        echo        Creating .env from template...
        copy ".env.example" ".env" >nul
        echo        NOTE: Edit .env to add your ANTHROPIC_API_KEY
    ) else (
        echo        WARNING: No .env file found
    )
) else (
    echo        OK - Configuration file exists
)

REM Check for API key
findstr /C:"ANTHROPIC_API_KEY=sk-" ".env" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ============================================================
    echo   WARNING: No Anthropic API key configured!
    echo   The system will use heuristic fallback only.
    echo   Edit backend\.env to add: ANTHROPIC_API_KEY=sk-ant-...
    echo  ============================================================
    echo.
)

echo  [5/5] Launching services...
echo.

REM Start frontend server in background
echo        Starting frontend server on port 3000...
start "CamOpt Frontend" /min cmd /c "cd /d "%PROJECT_ROOT%" && python -m http.server 3000 2>nul"
timeout /t 1 /nobreak >nul

REM Open browser to frontend
echo        Opening browser...
timeout /t 1 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo  ============================================================
echo   CAMOPT AI SERVICES RUNNING
echo  ============================================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo   Press Ctrl+C to stop the backend server
echo   Close the "CamOpt Frontend" window to stop frontend
echo  ============================================================
echo.

REM Start backend (this blocks until Ctrl+C)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

REM Cleanup: Kill frontend server when backend stops
echo.
echo  Shutting down frontend server...
taskkill /FI "WINDOWTITLE eq CamOpt Frontend*" /F >nul 2>&1

echo  All services stopped.
pause
