#!/bin/bash
set -e

# Kill background jobs on exit
trap 'kill $(jobs -p) 2>/dev/null' EXIT

echo "▶ Starting backend..."
cd "$(dirname "$0")/backend"

if [ ! -d ".venv" ]; then
  echo "  Creating Python virtual environment..."
  PYTHON=$(command -v python3.12 || command -v python3.11 || command -v python3)
  "$PYTHON" -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt -q
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

echo "▶ Starting frontend..."
cd ../frontend
npm install -q
npm run dev &

echo ""
echo "✓ Backend:  http://localhost:8000"
echo "✓ Frontend: http://localhost:3000"
echo "✓ Preview:  http://localhost:3000/preview (no auth needed)"
echo ""
echo "Press Ctrl+C to stop both servers."
wait
