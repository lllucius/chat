#!/bin/bash

# Development server script

set -e

echo "🚀 Starting AI Chatbot development server..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Run scripts/setup.sh first"
    exit 1
fi

# Check if database is accessible
echo "🔍 Checking database connection..."
if python -c "
import asyncio
from chat.core import init_db, close_db

async def check_db():
    try:
        await init_db()
        print('✅ Database connection successful')
        await close_db()
        return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

if not asyncio.run(check_db()):
    exit(1)
"; then
    echo "Database check passed"
else
    echo "❌ Database check failed. Make sure PostgreSQL is running and configured correctly"
    exit 1
fi

# Start the development server
echo "🌟 Starting FastAPI development server..."
python -m uvicorn chat.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir src \
    --log-level info