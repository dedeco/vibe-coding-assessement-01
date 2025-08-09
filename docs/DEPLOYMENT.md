# Data Ingestion & Deployment Guide

This document explains how to populate the vector database for different deployment scenarios.

## 🎯 TL;DR - For POC Deployment

**Fastest approach for demonstration:**

```bash
# Build database with test data and start API
python scripts/build_database.py --source test --reset
cd src/web && python app.py
```

## 📊 Data Ingestion Options

### Option 1: Test Data (Recommended for POC)

**Best for:** Demonstrations, development, POC deployments

```bash
# Generate diverse test data and populate ChromaDB
python scripts/build_database.py --source test --reset
```

**Advantages:**
- ✅ No external dependencies
- ✅ Diverse, realistic data (547 documents)
- ✅ Fast build time (~30 seconds)
- ✅ Predictable, testable responses
- ✅ No sensitive data concerns

### Option 2: PDF Files (Production)

**Best for:** Real deployments with actual trial balance PDFs

```bash
# Process PDFs and populate ChromaDB
python scripts/build_database.py --source pdf --pdf-path pdfs --reset
```

**Requirements:**
- PDF files in the specified folder
- Files should follow naming pattern: `PACTO_BALANCETE_0913_YYMM.pdf`
- PDFs contain structured trial balance data

## 🚀 Deployment Strategies

### 1. Build-Time Population (Recommended for POC)

Populate database during application build/startup:

```bash
# Method A: Using build script
./scripts/build_and_run.sh

# Method B: Manual steps  
python scripts/build_database.py --source test --reset
cd src/web
python app.py
```

### 2. Docker Build-Time

Add to your `Dockerfile`:

```dockerfile
# Copy build files
COPY scripts/build_database.py /app/
COPY scripts/populate_test_data.py /app/
COPY src/ /app/src/

# Build database during image creation
RUN python scripts/build_database.py --source test --reset

# Database ready when container starts
CMD ["python", "src/web/app.py"]
```

### 3. Init Container (Kubernetes)

```yaml
apiVersion: v1
kind: Pod
spec:
  initContainers:
  - name: database-builder
    image: your-app:latest
    command: ['python', 'build_database.py', '--source', 'test', '--reset']
    volumeMounts:
    - name: database-volume
      mountPath: /app/src/web/data
  
  containers:
  - name: api-server
    image: your-app:latest
    volumeMounts:
    - name: database-volume  
      mountPath: /app/src/web/data
```

### 4. Runtime Population

For dynamic data loading:

```python
# In your app startup
from build_database import DatabaseBuilder

@app.on_event("startup")
async def populate_database():
    if not database_exists():
        builder = DatabaseBuilder()
        builder.build_from_test_data(reset=True)
```

## 🗂️ Data Pipeline Architecture

```
PDF Files OR Test Data
         ↓
   PDF Processor / Generator
         ↓  
   Structured Expenses
         ↓
   Semantic Chunker
         ↓
   Document Chunks
         ↓
   ChromaDB Indexer
         ↓
   Vector Database
         ↓
   API Ready! 🎉
```

## 📁 File Structure

```
project/
├── scripts/
│   ├── build_database.py          # Main build script
│   ├── populate_test_data.py       # Test data generator  
├── pdfs/                       # PDF source files
│   ├── PACTO_BALANCETE_*.pdf
├── src/
│   ├── ingestion/
│   │   ├── pdf_processor.py    # PDF → structured data
│   │   ├── semantic_chunker.py # Structure → chunks
│   │   └── indexer.py          # Chunks → vector DB
│   └── web/
│       ├── data/chromadb/      # Vector database
│       └── app.py              # API server
└── data/
    ├── processed/              # Intermediate files
    └── chunks/                 # Semantic chunks
```

## ⚙️ Configuration Options

### Environment Variables

```bash
# Optional: Claude API for enhanced responses
export CLAUDE_API_KEY="your-api-key"

# Database path (default: src/web/data/chromadb)
export DB_PATH="custom/path"

# API port (default: 8000)  
export PORT=8080
```

### Build Script Options

```bash
# Reset database (clear existing data)
python scripts/build_database.py --reset

# Choose data source
python scripts/build_database.py --source pdf    # Use PDF files
python scripts/build_database.py --source test   # Use test data

# Custom PDF path
python scripts/build_database.py --source pdf --pdf-path /custom/path

# Create deployment scripts
python scripts/build_database.py --create-scripts
```

## 🧪 Testing & Verification

After building the database:

```bash
# Verify database population
python scripts/build_database.py --source test  # Will verify at the end

# Test API responses
python scripts/test_api_responses.py

# Manual API test
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How much was spent on electricity?"}'
```

## 📈 Performance & Scale

### POC/Demo (Test Data)
- **Size:** 547 documents, ~2MB
- **Build time:** 30 seconds
- **Memory:** ~100MB
- **Response time:** <200ms

### Production (PDF Data)
- **Size:** Depends on PDF count
- **Build time:** ~1-5 minutes for 50 PDFs
- **Memory:** ~500MB-2GB
- **Response time:** <500ms

## 🔧 Troubleshooting

### Common Issues

**Database empty after build:**
```bash
# Check database location
ls -la src/web/data/chromadb/

# Verify with explicit path
python -c "
from src.query.retriever import ExpenseRetriever
r = ExpenseRetriever('src/web/data/chromadb')
print(f'Documents: {r.get_collection().count()}')
"
```

**Import errors:**
```bash
# Ensure Python path includes src/
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or use absolute imports
python -c "import sys; sys.path.append('src'); from build_database import DatabaseBuilder"
```

**ChromaDB permission errors:**
```bash
# Fix permissions
chmod -R 755 src/web/data/chromadb/
```

## 💡 Best Practices

### For POC/Demo:
1. ✅ Use test data (`--source test`)
2. ✅ Build at container build time
3. ✅ Include verification step
4. ✅ Add health check endpoints

### For Production:
1. ✅ Use actual PDF files (`--source pdf`)
2. ✅ Implement incremental updates
3. ✅ Add data validation
4. ✅ Monitor database size/performance
5. ✅ Backup vector database regularly

### General:
1. ✅ Always verify after build
2. ✅ Test with diverse queries
3. ✅ Monitor response times
4. ✅ Log build process for debugging