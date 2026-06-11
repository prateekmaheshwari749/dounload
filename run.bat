@echo off
echo ====================================================================
echo Starting Techphotons Audio Dataset Downloader & Processor Pipeline...
echo ====================================================================
echo.

:: Start Python FastAPI server in a new cmd window
echo [STEP 1] Launching FastAPI Backend on http://localhost:8000...
start "Techphotons Backend" cmd /k "title Backend Server && .venv\Scripts\python -m uvicorn server:app --host 0.0.0.0 --port 8000"

:: Start Vite React dev server in a new cmd window
echo [STEP 2] Launching Vite React Frontend on http://localhost:5173...
start "Techphotons Frontend" cmd /k "title Frontend Server && cd frontend && npm run dev -- --host"

:: Wait for servers to initialize
echo.
echo Waiting for servers to initialize (3 seconds)...
timeout /t 3 /nobreak >nul

:: Open browser
echo [STEP 3] Opening Web Interface in your default browser...
start http://localhost:5173

echo.
echo ====================================================================
echo System Running! Keep the backend and frontend command windows open.
echo ====================================================================
echo.
pause
