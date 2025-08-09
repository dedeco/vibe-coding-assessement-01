#!/bin/bash

# Condominium Analytics Agent - Setup Script
echo "🏢 Condominium Analytics Agent - Setup Script"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_info() {
    echo -e "${BLUE}📋${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "README.md" ] || ! grep -q "Condominium Analytics Agent" README.md; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
if [ $? -ne 0 ]; then
    print_error "Python 3 is required but not found"
    exit 1
fi

print_status "Python $python_version detected"

# Check if virtual environment should be created
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        print_status "Virtual environment created"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_info "Installing Python dependencies..."
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    print_status "Dependencies installed successfully"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Check if data already exists
if [ -d "data/chromadb" ] && [ "$(ls -A data/chromadb 2>/dev/null)" ]; then
    print_status "Data already processed. Skipping data pipeline."
    print_warning "To reprocess data, delete the 'data/' folder and run setup again."
else
    # Run data pipeline
    echo ""
    print_info "Running data ingestion pipeline..."
    
    # Step 1: Process PDFs
    print_info "Processing PDF documents..."
    python src/ingestion/pdf_processor.py
    if [ $? -eq 0 ]; then
        print_status "PDF processing completed"
    else
        print_error "PDF processing failed"
        exit 1
    fi
    
    # Step 2: Create semantic chunks
    print_info "Creating semantic chunks..."
    python src/ingestion/semantic_chunker.py
    if [ $? -eq 0 ]; then
        print_status "Semantic chunking completed"
    else
        print_error "Semantic chunking failed"
        exit 1
    fi
    
    # Step 3: Index in ChromaDB
    print_info "Indexing chunks in ChromaDB..."
    python src/ingestion/indexer.py
    if [ $? -eq 0 ]; then
        print_status "ChromaDB indexing completed"
    else
        print_error "ChromaDB indexing failed"
        exit 1
    fi
    
    print_status "Data pipeline completed successfully!"
fi

# Environment setup reminder
echo ""
echo "=================================================="
print_warning "IMPORTANT: Set your Claude API key for full functionality!"
echo "export CLAUDE_API_KEY='your-api-key-here'"
echo ""
echo "Or copy .env.example to .env and edit it:"
echo "cp .env.example .env"
echo ""

# Start the web application
echo "🚀 Starting web application..."
echo "📱 Application will be available at: http://localhost:8000"
echo "📖 API documentation at: http://localhost:8000/docs"
echo ""
print_warning "Press Ctrl+C to stop the server"
echo ""

# Change to web directory and start server
cd src/web
python app.py