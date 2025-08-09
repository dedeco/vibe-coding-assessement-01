# Quick Start Guide

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Claude API key (optional, but recommended for full functionality)

### Option 1: Automated Setup (Recommended)
```bash
# Run the setup script
./scripts/setup.sh
```

This will:
1. Create a virtual environment
2. Install all dependencies
3. Process the PDF documents
4. Create semantic chunks
5. Index data in ChromaDB
6. Start the web application

### Option 2: Manual Setup
```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run data pipeline
python src/ingestion/pdf_processor.py
python src/ingestion/semantic_chunker.py
python src/ingestion/indexer.py

# 4. Set Claude API key (optional)
export CLAUDE_API_KEY="your-api-key-here"

# 5. Start web application
cd src/web
python app.py
```

## 🔑 Claude API Setup (Optional but Recommended)

1. Get your API key from [Claude Console](https://console.anthropic.com/)
2. Set the environment variable:
   ```bash
   export CLAUDE_API_KEY="your-api-key-here"
   ```
   Or copy `.env.example` to `.env` and edit it.

**Note:** The application works without Claude API (with limited responses), but Claude provides much better natural language understanding and responses.

## 🌐 Using the Application

1. Open your browser to `http://localhost:8000`
2. Ask questions about the trial balance data:
   - "How much was spent on power supply?"
   - "What are the elevator maintenance costs?"
   - "Show me total expenses for March 2025"
   - "What did we pay to CEMIG?"

## 🛠️ API Endpoints

- `GET /` - Web interface
- `POST /query` - Submit questions
- `GET /health` - System health check
- `GET /docs` - API documentation
- `GET /filters` - Available filter options

## 📊 Sample Data

The project includes 6 trial balance PDFs from January-June 2025 for the PACTO condominium property, located in the `pdfs/` folder.

## 🔧 Troubleshooting

### Common Issues

**"Collection not found" error:**
- Run the data pipeline: `python src/ingestion/indexer.py`

**"Claude API key not found" warning:**
- Set your `CLAUDE_API_KEY` environment variable
- The app still works with basic responses without Claude

**Port already in use:**
- Change the port: `PORT=8001 python src/web/app.py`

**PDF processing fails:**
- Ensure PDF files are in the `pdfs/` folder
- Check file permissions

### Reset Data
```bash
# Delete processed data to start fresh
rm -rf data/
./scripts/setup.sh
```

## 📁 Project Structure

```
├── README.md                    # Main documentation
├── docs/QUICKSTART.md          # This file
├── requirements.txt            # Python dependencies
├── scripts/
│   └── setup.sh                   # Automated setup script
├── .env.example              # Environment variables template
├── pdfs/                     # Trial balance PDF documents
├── data/                     # Processed data (created by pipeline)
│   ├── processed/           # Extracted PDF data
│   ├── chunks/             # Semantic chunks
│   └── chromadb/          # Vector database
├── src/
│   ├── ingestion/          # Data processing pipeline
│   │   ├── pdf_processor.py
│   │   ├── semantic_chunker.py
│   │   └── indexer.py
│   ├── query/              # Query processing
│   │   ├── retriever.py
│   │   └── claude_client.py
│   └── web/                # Web application
│       ├── app.py          # FastAPI backend
│       └── static/         # Frontend files
│           ├── index.html
│           ├── style.css
│           └── app.js
```