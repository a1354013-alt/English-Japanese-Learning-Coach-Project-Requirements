#!/bin/bash

echo "===================================="
echo "Language Coach - Starting Frontend"
echo "===================================="

cd frontend

# Check if node_modules exists
if [ ! -d node_modules ]; then
    echo "Installing Node.js dependencies..."
    pnpm install
fi

echo ""
echo "Starting Vite development server..."
echo "Frontend will be available at http://localhost:5173"
echo "Press Ctrl+C to stop"
echo ""

pnpm dev
