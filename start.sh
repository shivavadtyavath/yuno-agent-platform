#!/bin/bash
# ─── Start both backend and frontend ─────────────────────────────────────────
set -e

echo "🚀 Starting Yuno AI Agent Platform..."

# Start backend
echo "Starting backend on http://localhost:8000 ..."
cd backend
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || true
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Wait for backend
sleep 3

# Start frontend
echo "Starting frontend on http://localhost:5173 ..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  🎉 Platform is running!                             ║"
echo "║  Frontend: http://localhost:5173                     ║"
echo "║  Backend:  http://localhost:8000                     ║"
echo "║  API Docs: http://localhost:8000/docs                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT
wait
