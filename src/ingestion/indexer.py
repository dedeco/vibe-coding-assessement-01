import json
import chromadb
from pathlib import Path
from typing import List, Dict, Any
import uuid

class ChromaDBIndexer:
    def __init__(self, chunks_file: str = "data/chunks/semantic_chunks.json",
                 db_path: str = "data/chromadb"):
        self.chunks_file = Path(chunks_file)
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.collection_name = "condominium_expenses"
        
    def create_collection(self) -> chromadb.Collection:
        """Create or get ChromaDB collection."""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=self.collection_name)
            print(f"Using existing collection: {self.collection_name}")
        except ValueError:
            # Create new collection if it doesn't exist
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Condominium trial balance expenses and summaries"}
            )
            print(f"Created new collection: {self.collection_name}")
        
        return collection
    
    def reset_collection(self) -> chromadb.Collection:
        """Delete and recreate the collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"Deleted existing collection: {self.collection_name}")
        except ValueError:
            pass  # Collection didn't exist
        
        collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"description": "Condominium trial balance expenses and summaries"}
        )
        print(f"Created fresh collection: {self.collection_name}")
        return collection
    
    def prepare_chunk_for_indexing(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a chunk for ChromaDB indexing."""
        
        # Extract the content text
        content = chunk.get('content', '')
        
        # Prepare metadata for ChromaDB (must be flat and serializable)
        metadata = {
            'chunk_id': chunk.get('chunk_id', ''),
            'chunk_type': chunk.get('chunk_type', ''),
        }
        
        # Add specific metadata based on chunk type
        chunk_metadata = chunk.get('metadata', {})
        
        # Add common metadata fields
        if 'month_year' in chunk_metadata:
            metadata['month_year'] = str(chunk_metadata['month_year'])
        
        if 'category' in chunk_metadata:
            metadata['category'] = str(chunk_metadata['category'])
            
        if 'subcategory' in chunk_metadata:
            metadata['subcategory'] = str(chunk_metadata['subcategory'])
        
        if 'vendor' in chunk_metadata:
            metadata['vendor'] = str(chunk_metadata['vendor'])
        
        if 'amount' in chunk_metadata:
            metadata['amount'] = float(chunk_metadata['amount'])
        
        if 'currency' in chunk_metadata:
            metadata['currency'] = str(chunk_metadata['currency'])
        
        if 'document' in chunk_metadata:
            metadata['document'] = str(chunk_metadata['document'])
        
        # Add type-specific metadata
        if chunk['chunk_type'] == 'individual_expense':
            if 'description' in chunk_metadata:
                metadata['description'] = str(chunk_metadata['description'])[:500]  # Limit length
        
        elif chunk['chunk_type'] == 'category_summary':
            if 'expense_count' in chunk_metadata:
                metadata['expense_count'] = int(chunk_metadata['expense_count'])
                
        elif chunk['chunk_type'] == 'monthly_summary':
            if 'expense_count' in chunk_metadata:
                metadata['expense_count'] = int(chunk_metadata['expense_count'])
            if 'total_amount' in chunk_metadata:
                metadata['total_amount'] = float(chunk_metadata['total_amount'])
        
        elif chunk['chunk_type'] == 'vendor_summary':
            if 'transaction_count' in chunk_metadata:
                metadata['transaction_count'] = int(chunk_metadata['transaction_count'])
            if 'total_amount' in chunk_metadata:
                metadata['total_amount'] = float(chunk_metadata['total_amount'])
        
        return {
            'id': chunk.get('chunk_id', str(uuid.uuid4())),
            'content': content,
            'metadata': metadata
        }
    
    def index_chunks(self, chunks: List[Dict[str, Any]], reset: bool = False) -> None:
        """Index semantic chunks in ChromaDB."""
        
        if not chunks:
            print("No chunks to index")
            return
        
        # Create or reset collection
        if reset:
            collection = self.reset_collection()
        else:
            collection = self.create_collection()
        
        # Prepare chunks for indexing
        prepared_chunks = []
        for chunk in chunks:
            try:
                prepared_chunk = self.prepare_chunk_for_indexing(chunk)
                prepared_chunks.append(prepared_chunk)
            except Exception as e:
                print(f"Error preparing chunk {chunk.get('chunk_id', 'unknown')}: {e}")
                continue
        
        if not prepared_chunks:
            print("No valid chunks to index")
            return
        
        # Extract data for ChromaDB
        ids = [chunk['id'] for chunk in prepared_chunks]
        documents = [chunk['content'] for chunk in prepared_chunks]
        metadatas = [chunk['metadata'] for chunk in prepared_chunks]
        
        # Add chunks to collection in batches
        batch_size = 100
        total_batches = (len(prepared_chunks) + batch_size - 1) // batch_size
        
        for i in range(0, len(prepared_chunks), batch_size):
            batch_end = min(i + batch_size, len(prepared_chunks))
            batch_ids = ids[i:batch_end]
            batch_documents = documents[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            
            try:
                collection.add(
                    ids=batch_ids,
                    documents=batch_documents,
                    metadatas=batch_metadatas
                )
                batch_num = (i // batch_size) + 1
                print(f"Indexed batch {batch_num}/{total_batches} ({len(batch_ids)} chunks)")
                
            except Exception as e:
                print(f"Error indexing batch {batch_num}: {e}")
                continue
        
        # Verify indexing
        total_count = collection.count()
        print(f"Successfully indexed {total_count} chunks in ChromaDB")
        
        # Show collection stats
        self.show_collection_stats(collection)
    
    def show_collection_stats(self, collection: chromadb.Collection) -> None:
        """Display statistics about the indexed collection."""
        
        # Get sample of documents to analyze
        try:
            sample_results = collection.get(limit=1000)
            
            if not sample_results['metadatas']:
                print("No documents found in collection")
                return
            
            # Analyze chunk types
            chunk_types = {}
            categories = {}
            months = {}
            
            for metadata in sample_results['metadatas']:
                # Chunk types
                chunk_type = metadata.get('chunk_type', 'unknown')
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
                
                # Categories
                category = metadata.get('category')
                if category:
                    categories[category] = categories.get(category, 0) + 1
                
                # Months
                month_year = metadata.get('month_year')
                if month_year:
                    months[month_year] = months.get(month_year, 0) + 1
            
            print("\nCollection Statistics:")
            print(f"Total documents: {collection.count()}")
            
            print("\nChunk Types:")
            for chunk_type, count in sorted(chunk_types.items()):
                print(f"  {chunk_type}: {count}")
            
            if categories:
                print("\nTop Categories:")
                for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  {category}: {count}")
            
            if months:
                print("\nMonths Covered:")
                for month in sorted(months.keys()):
                    print(f"  {month}: {months[month]} chunks")
                    
        except Exception as e:
            print(f"Error getting collection stats: {e}")
    
    def index_from_file(self, reset: bool = False) -> None:
        """Index chunks from the JSON file."""
        
        if not self.chunks_file.exists():
            raise FileNotFoundError(f"Chunks file {self.chunks_file} does not exist")
        
        print(f"Loading chunks from {self.chunks_file}")
        with open(self.chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        print(f"Loaded {len(chunks)} chunks")
        self.index_chunks(chunks, reset=reset)
    
    def test_search(self, query: str, n_results: int = 5) -> None:
        """Test search functionality with a sample query."""
        
        try:
            collection = self.client.get_collection(name=self.collection_name)
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            print(f"\nTest search for: '{query}'")
            print(f"Found {len(results['documents'][0])} results:")
            
            for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
                print(f"\n{i+1}. {doc[:200]}...")
                print(f"   Type: {metadata.get('chunk_type', 'unknown')}")
                print(f"   Category: {metadata.get('category', 'N/A')}")
                print(f"   Month: {metadata.get('month_year', 'N/A')}")
                if 'amount' in metadata:
                    print(f"   Amount: R$ {metadata['amount']:,.2f}")
                    
        except Exception as e:
            print(f"Error testing search: {e}")

class ExpenseIndexer(ChromaDBIndexer):
    """Expense-specific indexer for testing."""
    
    def __init__(self, db_path: str = "data/chromadb"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.collection_name = "condominium_expenses"
    
    def get_collection(self) -> chromadb.Collection:
        """Get the ChromaDB collection."""
        try:
            return self.client.get_collection(name=self.collection_name)
        except ValueError:
            raise ValueError(f"Collection '{self.collection_name}' not found. Run indexer first.")
    
    def add_chunk(self, content: str, metadata: Dict[str, Any]) -> None:
        """Add a single chunk to the collection."""
        collection = self.create_collection()
        
        # Generate unique ID
        chunk_id = str(uuid.uuid4())
        
        try:
            collection.add(
                ids=[chunk_id],
                documents=[content],
                metadatas=[metadata]
            )
        except Exception as e:
            print(f"Error adding chunk: {e}")

def main():
    """Main function to run the indexer."""
    indexer = ChromaDBIndexer()
    
    # Index chunks from file (reset=True for fresh start)
    indexer.index_from_file(reset=True)
    
    # Test with sample queries
    test_queries = [
        "power supply expenses",
        "elevator maintenance",
        "total expenses March",
        "CEMIG payments"
    ]
    
    for query in test_queries:
        indexer.test_search(query)

if __name__ == "__main__":
    main()