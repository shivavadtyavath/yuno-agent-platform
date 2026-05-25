@echo off
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║     Yuno AI Agent Orchestration Platform             ║
echo ╚══════════════════════════════════════════════════════╝
echo.

echo Starting backend on http://localhost:8000 ...
start "Yuno Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak > nul

echo Starting frontend on http://localhost:5173 ...
start "Yuno Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║  Platform is starting!                               ║
echo ║  Frontend: http://localhost:5173                     ║
echo ║  Backend:  http://localhost:8000                     ║
echo ║  API Docs: http://localhost:8000/docs                ║
echo ╚══════════════════════════════════════════════════════╝
echo.
pause
