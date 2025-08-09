#!/usr/bin/env python3
"""
Setup script for Condominium Analytics Agent
This script sets up the complete data pipeline and starts the web application.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a shell command with error handling."""
    print(f"📋 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return None

def check_requirements():
    """Check if required files exist."""
    required_files = [
        "pdfs/",
        "requirements.txt",
        "src/ingestion/pdf_processor.py",
        "src/ingestion/semantic_chunker.py", 
        "src/ingestion/indexer.py",
        "src/web/app.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    return True

def setup_environment():
    """Set up Python environment and install dependencies."""
    print("🔧 Setting up environment...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    
    print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro} detected")
    
    # Install dependencies
    if run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return True
    else:
        print("❌ Failed to install dependencies. Try: pip install -r requirements.txt")
        return False

def run_data_pipeline():
    """Run the complete data ingestion pipeline."""
    print("\n🔄 Running data ingestion pipeline...")
    
    # Step 1: Process PDFs
    if not run_command("python src/ingestion/pdf_processor.py", "Processing PDF documents"):
        return False
    
    # Step 2: Create semantic chunks  
    if not run_command("python src/ingestion/semantic_chunker.py", "Creating semantic chunks"):
        return False
    
    # Step 3: Index in ChromaDB
    if not run_command("python src/ingestion/indexer.py", "Indexing chunks in ChromaDB"):
        return False
    
    print("✅ Data pipeline completed successfully!")
    return True

def start_web_app():
    """Start the web application."""
    print("\n🚀 Starting web application...")
    print("📱 The application will be available at: http://localhost:8000")
    print("📖 API documentation at: http://localhost:8000/docs")
    print("\n⚠️  Remember to set your CLAUDE_API_KEY environment variable for full functionality!")
    print("   Example: export CLAUDE_API_KEY='your-api-key-here'")
    print("\n🛑 Press Ctrl+C to stop the server\n")
    
    # Change to web directory and start server
    os.chdir("src/web")
    os.system("python app.py")

def main():
    """Main setup function."""
    print("🏢 Condominium Analytics Agent - Setup Script")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("README.md").exists() or "Condominium Analytics Agent" not in Path("README.md").read_text():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Check requirements
    if not check_requirements():
        print("❌ Setup cannot continue due to missing files")
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        print("❌ Environment setup failed")
        sys.exit(1)
    
    # Check if data already exists
    if Path("data/chromadb").exists() and any(Path("data/chromadb").iterdir()):
        print("\n📊 Data already processed. Skipping data pipeline.")
        print("   To reprocess data, delete the 'data/' folder and run setup again.")
        skip_pipeline = True
    else:
        skip_pipeline = False
    
    # Run data pipeline if needed
    if not skip_pipeline:
        if not run_data_pipeline():
            print("❌ Data pipeline failed")
            sys.exit(1)
    
    # Start web application
    print("\n" + "=" * 50)
    start_web_app()

if __name__ == "__main__":
    main()