# Condominium Analytics Agent

## Overview

A conversational web application that enables condominium associates to query monthly trial balance data through natural language. The system uses a semantic layer with ChromaDB vector storage to process and index financial documents, allowing Claude AI to provide accurate, contextual answers about expenses and contributions.

## Problem Statement

Associates need quick access to financial information from monthly trial balance reports, but manually searching through PDF documents is inefficient. This agent provides instant answers through a simple chat interface backed by intelligently processed document data.

## Architecture

### Two-Phase Approach

#### Phase 1: Data Ingestion & Semantic Processing (Offline)
- **PDF Processing**: Extract financial data from trial balance documents
- **Semantic Chunking**: Break down data into meaningful pieces with rich metadata
- **Vector Storage**: Store chunks in ChromaDB for semantic similarity search
- **Knowledge Base**: Searchable index of financial information ready for queries

#### Phase 2: Query & Response (Real-time)
- **Web Interface**: Simple textbox for user questions
- **Semantic Search**: ChromaDB finds relevant chunks based on query similarity
- **Context Assembly**: Gather related chunks and metadata for LLM input
- **LLM Processing**: Claude AI generates answers using retrieved context
- **Response**: Natural language answer displayed instantly

## Key Features

### 🔍 Natural Language Querying
- Ask questions like: "How much was spent on power supply?"
- Supports contextual follow-ups and complex queries
- Bilingual support (Portuguese/English)

### 🧠 Semantic Understanding
- Intelligent chunking of financial data by categories, vendors, dates
- Vector embeddings for semantic similarity matching
- Metadata-rich knowledge base for precise filtering and retrieval

### 💬 Simple Web Interface
- Clean, responsive design
- Single textbox interaction
- Real-time responses
- Mobile-friendly

## Data Storage Strategy

### ChromaDB Vector Storage
```json
{
  "chunk_id": "expense_power_2025_03_001",
  "content": "Power supply expenses for March 2025: R$ 2,450.30 paid to CEMIG on 15/03/2025",
  "metadata": {
    "category": "utilities",
    "subcategory": "power_supply", 
    "amount": 2450.30,
    "currency": "BRL",
    "date": "2025-03-15",
    "vendor": "CEMIG",
    "month": "2025-03",
    "document": "PACTO_BALANCETE_0913_2503.pdf"
  },
  "embedding": [0.1, -0.3, 0.8, ...]
}
```

### Benefits of ChromaDB Approach
- **Local Storage**: No external dependencies, runs on SQLite
- **Built-in Embeddings**: Automatic vector generation
- **Metadata Filtering**: Combine semantic search with structured queries
- **Lightweight**: Perfect for single-property proof of concept
- **Easy Setup**: Simple installation and configuration

## Technical Components

### Semantic Layer Pipeline
```
PDF Documents → Data Extraction → Semantic Chunking → Vector Embeddings → ChromaDB Storage
```

#### 1. Data Extraction Module (`pdf_processor.py`)
- PDF parsing and table recognition
- Financial data normalization  
- Expense categorization

#### 2. Semantic Chunking Module (`semantic_chunker.py`)
- Create logical chunks (expense items, category summaries, totals)
- Add rich metadata (date, category, vendor, amount, document source)
- Structure for optimal retrieval

#### 3. Vector Storage Module (`indexer.py`)
- Generate embeddings using sentence-transformers
- Store chunks in ChromaDB with metadata
- Create searchable collections for efficient queries

#### 4. Query Processing Module (`retriever.py`, `claude_client.py`)
- Semantic search in ChromaDB to find relevant chunks
- Metadata filtering for precise results
- Context assembly and Claude API integration

## Data Flow

### Ingestion Pipeline (Offline)
1. **Input**: Trial balance PDFs from `pdfs/` folder
2. **Extract**: Parse tables, identify expense categories and amounts
3. **Chunk**: Create semantic chunks with metadata
4. **Embed**: Generate vector embeddings for each chunk
5. **Store**: Save to ChromaDB collection with searchable metadata

### Query Pipeline (Real-time)
1. **User Question**: "How much was spent on power supply?"
2. **Semantic Search**: ChromaDB finds chunks about power/electricity expenses
3. **Metadata Filter**: Narrow results by date, category, or amount if needed
4. **Context Assembly**: Gather relevant chunks and metadata
5. **LLM Query**: Claude processes question with retrieved context
6. **Response**: Natural language answer with specific amounts and details

## Sample Use Cases

### Financial Queries
- "How much was spent on power supply this month?"
- "What are all the maintenance expenses?"
- "Show me elevator service costs"
- "What did we pay for cleaning services?"

### Comparative Analysis
- "Compare utility costs across the months"
- "What are the highest expense categories?"

## Project Structure

```
├── README.md
├── pdfs/                          # Source trial balance documents
├── data/
│   ├── processed/                 # Extracted and cleaned data
│   ├── chromadb/                  # ChromaDB vector database files
│   └── chunks/                    # Processed semantic chunks (backup)
├── src/
│   ├── ingestion/
│   │   ├── pdf_processor.py       # PDF parsing and data extraction
│   │   ├── semantic_chunker.py    # Create chunks with metadata
│   │   └── indexer.py             # ChromaDB storage and indexing
│   ├── query/
│   │   ├── retriever.py           # ChromaDB semantic search
│   │   ├── claude_client.py       # Claude API integration
│   │   └── response_generator.py  # Answer formatting
│   └── web/
│       ├── app.py                 # FastAPI backend
│       └── static/
│           ├── index.html         # Web interface
│           ├── style.css          # Responsive styling
│           └── app.js             # Frontend logic
└── requirements.txt
```

## Getting Started

### Prerequisites
- Python 3.8+
- Claude API key

### Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CLAUDE_API_KEY="your-claude-api-key"

# Run ingestion pipeline (one-time setup)
python src/ingestion/pdf_processor.py      # Extract data from PDFs
python src/ingestion/semantic_chunker.py   # Create semantic chunks
python src/ingestion/indexer.py            # Store in ChromaDB

# Start web application
python src/web/app.py

# Access at http://localhost:8000
```

### Dependencies
```txt
fastapi
uvicorn
chromadb
sentence-transformers
anthropic
pypdf2
pdfplumber
pandas
python-multipart
```

## Sample Data
6 trial balance PDFs (PACTO property, Jan-Jun 2025) included for demonstration and testing.

## Future Enhancements

### Planned Features
- **Multi-property Support**: Handle multiple condominium properties in separate ChromaDB collections
- **Advanced Analytics**: Expense trends and budget variance analysis using aggregated chunk data
- **Export Capabilities**: Generate reports from retrieved chunks and analysis
- **Document Upload Interface**: Web-based PDF ingestion with real-time processing
- **Historical Comparisons**: Cross-month analysis using temporal metadata
- **Mobile Application**: Native mobile app with same backend API
- **Integration APIs**: Property management software connectivity
- **User Authentication**: Role-based access control for different user types
- **Real-time Notifications**: Alerts based on expense pattern analysis
- **Predictive Analytics**: Expense forecasting using historical chunk patterns

### Technical Enhancements
- **Vector Database Scaling**: Migration to Pinecone or Weaviate for production
- **Advanced Embeddings**: Fine-tuned models for financial document understanding
- **Hybrid Search**: Combine vector similarity with keyword and metadata filtering
- **Caching Layer**: Redis for frequently accessed chunks and query results

## Benefits

- **Instant Access**: Semantic search provides answers in seconds
- **Natural Language**: Ask questions as you would to a financial advisor  
- **Accurate Context**: Vector similarity ensures relevant, precise responses
- **Scalable Architecture**: ChromaDB handles growing document collections efficiently
- **User-Friendly**: Simple interface accessible to all associates
- **Offline Capable**: Local ChromaDB storage works without internet connectivity# vide-coding-assessement-01
