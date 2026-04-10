#!/usr/bin/env bash
set -euo pipefail

echo "===================================="
echo "Language Coach - Start Frontend"
echo "===================================="

cd frontend

if [ ! -d node_modules ]; then
  echo "Installing frontend dependencies with npm..."
  npm install
fi

echo "Starting Vite dev server on http://localhost:5173"
npm run dev
