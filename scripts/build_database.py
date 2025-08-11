#!/usr/bin/env python3
"""
Build-time database population script for POC deployment.

This script handles the complete data ingestion pipeline:
1. Process PDFs -> Extract structured data
2. Create semantic chunks -> Prepare for vector search  
3. Index in ChromaDB -> Ready for API consumption

Usage:
    python build_database.py [--reset] [--source pdf|test] [--pdf-path PATH]
"""

import argparse

# Import from src package
import sys
from pathlib import Path

# Add project root to Python path for package imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ingestion import TrialBalanceProcessor, SemanticChunker, ChromaDBIndexer

class DatabaseBuilder:
    """Build and populate the vector database for POC deployment."""
    
    def __init__(self, db_path: str = "src/web/data/chromadb"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
    def build_from_pdfs(self, pdf_path: str = "pdfs", reset: bool = False) -> bool:
        """Build database from PDF files (production approach)."""
        
        print("🔄 Building database from PDF files...")
        print("=" * 60)
        
        try:
            # Step 1: Process PDFs
            print("📄 Step 1: Processing PDF files...")
            processor = TrialBalanceProcessor(pdf_folder=pdf_path)
            
            if not Path(pdf_path).exists():
                print(f"❌ PDF folder '{pdf_path}' not found")
                return False
                
            pdf_files = list(Path(pdf_path).glob("*.pdf"))
            if not pdf_files:
                print(f"❌ No PDF files found in '{pdf_path}'")
                return False
                
            print(f"Found {len(pdf_files)} PDF files")
            results = processor.process_all_pdfs()
            print(f"✅ Extracted {results['summary']['total_expenses']} expense records")
            
            # Step 2: Create semantic chunks
            print("\n🔍 Step 2: Creating semantic chunks...")
            chunker = SemanticChunker()
            
            # Use the processed expenses data
            expenses_file = Path("data/processed/processed_expenses.json")
            if not expenses_file.exists():
                print(f"❌ Processed expenses file not found at {expenses_file}")
                return False
                
            chunker = SemanticChunker(input_file=str(expenses_file))
            chunks = chunker.process_expenses_to_chunks()
            print(f"✅ Created {len(chunks)} semantic chunks")
            
            # Step 3: Index in ChromaDB
            print(f"\n🗂️  Step 3: Indexing in ChromaDB...")
            indexer = ChromaDBIndexer(db_path=str(self.db_path))
            indexer.index_chunks(chunks, reset=reset)
            
            print("\n✅ Database built successfully from PDFs!")
            return True
            
        except Exception as e:
            print(f"❌ Error building from PDFs: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def build_from_test_data(self, reset: bool = False) -> bool:
        """Build database with test data (POC/demo approach)."""
        
        print("🔄 Building database with test data...")
        print("=" * 60)
        
        try:
            # Import and run test data generator
            from populate_test_data import generate_test_expenses, create_document_chunks
            from src.ingestion.indexer import ExpenseIndexer
            
            # Generate test data
            print("🎲 Step 1: Generating diverse test data...")
            expenses = generate_test_expenses()
            print(f"Generated {len(expenses)} expense records")
            
            # Create document chunks
            print("\n🔍 Step 2: Creating document chunks...")
            chunks = create_document_chunks(expenses)
            print(f"Created {len(chunks)} document chunks")
            
            # Index in ChromaDB
            print(f"\n🗂️  Step 3: Indexing in ChromaDB...")
            indexer = ExpenseIndexer(db_path=str(self.db_path))
            
            # Clear existing data if reset requested
            if reset:
                try:
                    collection = indexer.get_collection()
                    indexer.client.delete_collection(indexer.collection_name)
                    print("🗑️  Cleared existing data")
                except:
                    pass  # Collection didn't exist
            
            # Index chunks
            for chunk in chunks:
                indexer.add_chunk(
                    content=chunk['content'],
                    metadata=chunk['metadata']
                )
            
            # Verify indexing
            collection = indexer.get_collection()
            count = collection.count()
            print(f"✅ Indexed {count} documents")
            
            print("\n✅ Database built successfully with test data!")
            return True
            
        except Exception as e:
            print(f"❌ Error building test data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_database(self) -> bool:
        """Verify the database is properly populated and accessible."""
        
        print("\n🔍 Verifying database...")
        
        try:
            from src.query.retriever import ExpenseRetriever
            
            retriever = ExpenseRetriever(db_path=str(self.db_path))
            collection = retriever.get_collection()
            count = collection.count()
            
            if count == 0:
                print("❌ Database is empty")
                return False
            
            print(f"✅ Database contains {count} documents")
            
            # Test search functionality
            print("🔍 Testing search functionality...")
            test_queries = [
                "electricity expenses",
                "maintenance costs", 
                "monthly summary"
            ]
            
            for query in test_queries:
                results = retriever.search_natural_language(query)
                if results['total_results'] > 0:
                    print(f"  ✅ '{query}': {results['total_results']} results")
                else:
                    print(f"  ⚠️  '{query}': No results")
            
            # Get available filters
            filters = retriever.get_available_filters()
            print(f"\n📊 Available data:")
            print(f"  Categories: {len(filters['categories'])}")
            print(f"  Vendors: {len(filters['vendors'])}")
            print(f"  Months: {len(filters['months'])}")
            
            return True
            
        except Exception as e:
            print(f"❌ Database verification failed: {e}")
            return False

def create_build_script():
    """Create a simple build script for deployment."""
    
    build_script = '''#!/bin/bash
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
'''
    
    with open('build_and_run.sh', 'w') as f:
        f.write(build_script)
    
    Path('build_and_run.sh').chmod(0o755)
    print("✅ Created build_and_run.sh script")

def create_dockerfile_instructions():
    """Create Dockerfile instructions for containerized deployment."""
    
    dockerfile_addition = '''
# Add these lines to your Dockerfile for build-time database population

# Copy build script and data
COPY scripts/build_database.py /app/
COPY scripts/populate_test_data.py /app/

# Build database during image build
RUN python build_database.py --source test --reset

# The database will be ready when the container starts
'''
    
    print("\n📝 Dockerfile instructions:")
    print(dockerfile_addition)
    
    return dockerfile_addition

def main():
    parser = argparse.ArgumentParser(description='Build vector database for POC')
    parser.add_argument('--reset', action='store_true', 
                       help='Reset/clear existing database')
    parser.add_argument('--source', choices=['pdf', 'test'], default='test',
                       help='Data source: pdf files or test data')
    parser.add_argument('--pdf-path', default='pdfs',
                       help='Path to PDF files (for --source pdf)')
    parser.add_argument('--create-scripts', action='store_true',
                       help='Create build scripts for deployment')
    parser.add_argument('--skip-verify', action='store_true',
                       help='Skip database verification (useful for Docker builds)')
    
    args = parser.parse_args()
    
    print("🏗️  Database Builder for Condominium Analytics POC")
    print("=" * 60)
    
    # Create deployment scripts if requested
    if args.create_scripts:
        create_build_script()
        create_dockerfile_instructions()
        return
    
    builder = DatabaseBuilder()
    
    # Build database based on source
    success = False
    if args.source == 'pdf':
        success = builder.build_from_pdfs(args.pdf_path, args.reset)
    else:
        success = builder.build_from_test_data(args.reset)
    
    if not success:
        print("❌ Database build failed!")
        sys.exit(1)
    
    # Verify the build (skip if requested)
    if not args.skip_verify:
        if not builder.verify_database():
            print("❌ Database verification failed!")
            sys.exit(1)
    else:
        print("⏭️  Skipping database verification")
    
    print("\n🎉 Build completed successfully!")
    print("\nNext steps:")
    print("1. Start the API: cd src/web && python app.py")
    print("2. Test the API: python scripts/test_api_responses.py")
    print("3. Access docs: http://localhost:8000/docs")

if __name__ == "__main__":
    main()