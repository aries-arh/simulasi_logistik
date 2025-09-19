@echo off
echo ========================================
echo   Production & Logistics Simulator
echo ========================================
echo.

echo [1/3] Starting Backend Server...
start "Backend Server" cmd /k "cd /d D:\APLIKASI PYTHON\production_simulator14\backend && echo Backend starting... && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo [2/3] Waiting for backend to initialize...
timeout /t 8 /nobreak > nul

echo [3/3] Starting Frontend Server...
start "Frontend Server" cmd /k "cd /d D:\APLIKASI PYTHON\production_simulator14\frontend && echo Frontend starting... && npm start"

echo.
echo ========================================
echo   Servers are starting...
echo ========================================
echo Backend API:  http://localhost:8000
echo Frontend UI:  http://localhost:3001 (or 3000)
echo API Docs:     http://localhost:8000/docs
echo Debug Tool:   file:///D:/APLIKASI%20PYTHON/production_simulator14/debug_api.html
echo ========================================
echo.
echo Note: Frontend may take 1-2 minutes to compile
echo       Check the terminal windows for any errors
echo.
echo Press any key to open debug tool...
pause > nul

echo Opening debug tool...
start "" "file:///D:/APLIKASI%20PYTHON/production_simulator14/debug_api.html"
