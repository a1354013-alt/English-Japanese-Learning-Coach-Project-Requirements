#!/bin/bash

echo "==================================="
echo "Language Coach - Starting Backend"
echo "==================================="

cd backend

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Check if Python dependencies are installed
echo "Checking Python dependencies..."
python3.11 -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Python dependencies..."
    sudo pip3 install -r requirements.txt
fi

# Initialize database if not exists
if [ ! -f ../data/language_coach.db ]; then
    echo "Initializing database..."
    python3.11 -c "from database import db; db.init_database(); print('Database initialized!')"
fi

echo ""
echo "Starting FastAPI server..."
echo "API will be available at http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
