#!/bin/bash

# Development setup script

set -e

echo "🚀 Setting up AI Chatbot development environment..."

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "📍 Python version: $python_version"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -e ".[dev]"

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Check if PostgreSQL is running
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        echo "✅ PostgreSQL is running"
    else
        echo "⚠️  PostgreSQL is not running. Start it manually or use Docker Compose"
    fi
else
    echo "⚠️  PostgreSQL not found. Use Docker Compose or install manually"
fi

# Set up pre-commit hooks
if command -v pre-commit &> /dev/null; then
    echo "🔧 Setting up pre-commit hooks..."
    pre-commit install
else
    echo "⚠️  pre-commit not found. Install with: pip install pre-commit"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your OpenAI API key and database settings"
echo "2. Initialize database: chat-manage init-database"
echo "3. Create admin user: chat-manage create-admin --username admin --email admin@example.com"
echo "4. Start development server: python -m uvicorn chat.main:app --reload"
echo "5. Open http://localhost:8000/docs to see API documentation"
echo ""
echo "Or use Docker Compose:"
echo "  docker-compose up -d"
echo ""