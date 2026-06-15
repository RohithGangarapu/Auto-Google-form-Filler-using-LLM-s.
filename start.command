#!/bin/bash
# Automated Form Filler - One-Click Launcher for macOS
# Move to the directory where this script is located
cd "$(dirname "$0")"

# Clean up background jobs on exit
trap "kill 0" EXIT

echo "======================================================"
echo "🚀 Starting LLM Form Automation Assistant..."
echo "======================================================"

# 1. Start Backend Server
echo "🐍 Booting backend..."
cd backend
# Use system python or virtual environment python
if [ -d "venv" ]; then
    source venv/bin/activate
    python3 -m uvicorn main:app --port 8000 &
else
    python3 -m pip install -r requirements.txt
    python3 -m uvicorn main:app --port 8000 &
fi
BACKEND_PID=$!
cd ..

# 2. Start Frontend Server
echo "⚛️  Booting frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "📦 First time setup: Installing npm packages..."
    npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

# 3. Open UI in Default Browser
echo "⏳ Waiting for servers to initialize..."
sleep 4
open http://localhost:5173

echo "======================================================"
echo "✨ Web App is open at http://localhost:5173"
echo "⚠️  Keep this terminal window open."
echo "❌ Press Ctrl+C or close this window to shut down."
echo "======================================================"

# Wait for background servers
wait
