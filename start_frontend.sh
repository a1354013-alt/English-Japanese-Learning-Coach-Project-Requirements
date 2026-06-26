#!/usr/bin/env bash
set -euo pipefail

echo "===================================="
echo "Language Coach - Start Frontend"
echo "===================================="

cd frontend

if [ ! -d node_modules ]; then
  if [ -f package-lock.json ]; then
    echo "Installing frontend dependencies with npm ci..."
    npm ci
  else
    echo "Installing frontend dependencies with npm install..."
    npm install
  fi
fi

echo "Starting Vite dev server on http://localhost:5173"
npm run dev
