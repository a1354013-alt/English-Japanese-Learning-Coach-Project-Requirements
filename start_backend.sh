#!/usr/bin/env bash
set -euo pipefail

echo "==================================="
echo "Language Coach - Start Backend"
echo "==================================="

cd backend

if [ ! -f .env ]; then
  echo "Creating backend/.env from .env.example"
  cp .env.example .env
fi

echo "Use a virtual environment before installing dependencies:"
echo "  python -m venv .venv"
echo "  source .venv/bin/activate  # Windows: .venv\\Scripts\\activate"

echo "Installing backend dependencies in current Python environment..."
python -m pip install -r requirements.txt

echo "Starting FastAPI server on http://localhost:8000"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
