#!/bin/bash
# Build script for POC deployment
# Populates the vector database before starting the API

set -e

# Change to project root if running from scripts directory
if [ "$(basename "$PWD")" = "scripts" ]; then
    cd ..
fi

echo "🚀 Building Condominium Analytics POC..."

# Create required directories
mkdir -p src/web/data/chromadb
mkdir -p data/processed
mkdir -p data/chunks

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Build database
echo "🗂️  Populating vector database..."
python scripts/build_database.py --source test --reset

# Verify build
echo "✅ Build complete! Starting API..."
cd src/web
python app.py
