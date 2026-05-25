#!/bin/bash
# ─── Yuno AI Agent Platform — One-Command Setup ──────────────────────────────
set -e

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     Yuno AI Agent Orchestration Platform Setup       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.10+ is required. Please install it first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PYTHON_VERSION found"

# Check Node
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 18+ is required. Please install it first."
    exit 1
fi
echo "✅ Node.js $(node --version) found"

# Setup .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 Created .env from .env.example"
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY before running the platform."
    echo ""
fi

# Backend setup
echo "📦 Installing backend dependencies..."
cd backend
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || true
pip install -q -r requirements.txt
echo "✅ Backend dependencies installed"
cd ..

# Frontend setup
echo "📦 Installing frontend dependencies..."
cd frontend
npm install --silent
echo "✅ Frontend dependencies installed"
cd ..

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║                   Setup Complete!                    ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  1. Edit .env and set OPENAI_API_KEY                 ║"
echo "║  2. (Optional) Set TELEGRAM_BOT_TOKEN in .env        ║"
echo "║  3. Run: ./start.sh                                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
