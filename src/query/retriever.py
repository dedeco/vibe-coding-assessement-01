import chromadb
from pathlib import Path
from typing import List, Dict, Any, Optional

class ExpenseRetriever:
    def __init__(self, db_path: str = "data/chromadb"):
        self.db_path = Path(db_path)
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.collection_name = "condominium_expenses"
        
    def get_collection(self) -> chromadb.Collection:
        """Get the ChromaDB collection."""
        try:
            return self.client.get_collection(name=self.collection_name)
        except ValueError:
            raise ValueError(f"Collection '{self.collection_name}' not found. Run indexer first.")
    
    def search_expenses(self, 
                       query: str, 
                       n_results: int = 10,
                       filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search for expenses using semantic similarity."""
        
        collection = self.get_collection()
        
        # Build where clause for filtering
        where_clause = {}
        if filters:
            for key, value in filters.items():
                if value is not None:
                    where_clause[key] = value
        
        # Perform semantic search
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        
        # Format results
        formatted_results = {
            'query': query,
            'total_results': len(results['documents'][0]),
            'results': []
        }
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0], 
            results['distances'][0] if results['distances'] else [0] * len(results['documents'][0])
        )):
            result = {
                'rank': i + 1,
                'content': doc,
                'metadata': metadata,
                'similarity_score': 1.0 - distance if distance else 1.0,
                'chunk_type': metadata.get('chunk_type', 'unknown')
            }
            formatted_results['results'].append(result)
        
        return formatted_results
    
    def search_by_category(self, 
                          category: str, 
                          month_year: Optional[str] = None,
                          n_results: int = 20) -> Dict[str, Any]:
        """Search expenses by category."""
        
        filters = {'category': category}
        if month_year:
            filters['month_year'] = month_year
        
        query = f"{category} expenses"
        if month_year:
            query += f" {month_year}"
            
        return self.search_expenses(query, n_results, filters)
    
    def search_by_vendor(self, 
                        vendor: str, 
                        n_results: int = 20) -> Dict[str, Any]:
        """Search expenses by vendor."""
        
        filters = {'vendor': vendor}
        query = f"{vendor} payments expenses"
        
        return self.search_expenses(query, n_results, filters)
    
    def search_by_month(self, 
                       month_year: str, 
                       n_results: int = 30) -> Dict[str, Any]:
        """Search all expenses for a specific month."""
        
        filters = {'month_year': month_year}
        query = f"expenses {month_year} monthly summary"
        
        return self.search_expenses(query, n_results, filters)
    
    def search_by_amount_range(self, 
                              min_amount: Optional[float] = None,
                              max_amount: Optional[float] = None,
                              query: str = "expenses",
                              n_results: int = 20) -> Dict[str, Any]:
        """Search expenses within amount range."""
        
        # Note: ChromaDB filtering with ranges requires specific syntax
        filters = {}
        
        # For now, we'll do post-filtering since ChromaDB range queries 
        # can be complex. In production, you might want to use more 
        # sophisticated filtering
        
        results = self.search_expenses(query, n_results * 2)  # Get more to filter
        
        # Post-filter by amount
        filtered_results = []
        for result in results['results']:
            amount = result['metadata'].get('amount')
            if amount is not None:
                if min_amount is not None and amount < min_amount:
                    continue
                if max_amount is not None and amount > max_amount:
                    continue
            filtered_results.append(result)
        
        # Limit to requested number
        filtered_results = filtered_results[:n_results]
        
        return {
            'query': f"{query} (amount: {min_amount or 0} - {max_amount or 'max'})",
            'total_results': len(filtered_results),
            'results': filtered_results
        }
    
    def get_monthly_summary(self, month_year: str) -> Dict[str, Any]:
        """Get comprehensive summary for a specific month."""
        
        # Search for monthly summary chunk first
        monthly_results = self.search_expenses(
            f"monthly summary {month_year}", 
            n_results=5,
            filters={'chunk_type': 'monthly_summary', 'month_year': month_year}
        )
        
        # Get category summaries for the month
        category_results = self.search_expenses(
            f"category expenses {month_year}",
            n_results=10,
            filters={'chunk_type': 'category_summary', 'month_year': month_year}
        )
        
        # Get top individual expenses
        individual_results = self.search_expenses(
            f"expenses {month_year}",
            n_results=15,
            filters={'chunk_type': 'individual_expense', 'month_year': month_year}
        )
        
        return {
            'month_year': month_year,
            'monthly_summary': monthly_results['results'],
            'category_summaries': category_results['results'],
            'top_expenses': individual_results['results']
        }
    
    def get_vendor_analysis(self, vendor: str) -> Dict[str, Any]:
        """Get comprehensive analysis for a specific vendor."""
        
        # Get vendor summary
        vendor_summary = self.search_expenses(
            f"{vendor} vendor summary",
            n_results=5,
            filters={'chunk_type': 'vendor_summary', 'vendor': vendor}
        )
        
        # Get all individual transactions
        transactions = self.search_expenses(
            f"{vendor} payments",
            n_results=20,
            filters={'chunk_type': 'individual_expense', 'vendor': vendor}
        )
        
        return {
            'vendor': vendor,
            'summary': vendor_summary['results'],
            'transactions': transactions['results']
        }
    
    def get_category_analysis(self, category: str) -> Dict[str, Any]:
        """Get comprehensive analysis for a specific category."""
        
        # Get category summaries across months
        summaries = self.search_expenses(
            f"{category} category summary",
            n_results=10,
            filters={'chunk_type': 'category_summary', 'category': category}
        )
        
        # Get individual expenses in this category
        expenses = self.search_expenses(
            f"{category} expenses",
            n_results=20,
            filters={'chunk_type': 'individual_expense', 'category': category}
        )
        
        return {
            'category': category,
            'monthly_summaries': summaries['results'],
            'individual_expenses': expenses['results']
        }
    
    def search_natural_language(self, query: str) -> Dict[str, Any]:
        """Handle natural language queries with intelligent routing."""
        
        query_lower = query.lower()
        
        # Detect query type and route accordingly
        if 'month' in query_lower or any(month in query_lower for month in 
            ['january', 'february', 'march', 'april', 'may', 'june',
             'july', 'august', 'september', 'october', 'november', 'december']):
            # Month-based query
            return self.search_expenses(query, n_results=15)
        
        elif any(vendor_keyword in query_lower for vendor_keyword in 
                ['cemig', 'vendor', 'paid to', 'supplier']):
            # Vendor-based query
            return self.search_expenses(query, n_results=15)
        
        elif any(category in query_lower for category in 
                ['power', 'electricity', 'water', 'gas', 'elevator', 'maintenance', 
                 'cleaning', 'security', 'utilities']):
            # Category-based query
            return self.search_expenses(query, n_results=15)
        
        elif 'total' in query_lower or 'summary' in query_lower:
            # Summary query - prioritize summary chunks
            return self.search_expenses(query, n_results=10)
        
        else:
            # General search
            return self.search_expenses(query, n_results=12)
    
    def get_available_filters(self) -> Dict[str, List[str]]:
        """Get available filter values from the collection."""
        
        collection = self.get_collection()
        
        # Get sample of all documents to analyze available filters
        sample_results = collection.get(limit=1000)
        
        filters = {
            'categories': set(),
            'subcategories': set(),
            'vendors': set(),
            'months': set(),
            'chunk_types': set()
        }
        
        for metadata in sample_results['metadatas']:
            if metadata.get('category'):
                filters['categories'].add(metadata['category'])
            if metadata.get('subcategory'):
                filters['subcategories'].add(metadata['subcategory'])
            if metadata.get('vendor'):
                filters['vendors'].add(metadata['vendor'])
            if metadata.get('month_year'):
                filters['months'].add(metadata['month_year'])
            if metadata.get('chunk_type'):
                filters['chunk_types'].add(metadata['chunk_type'])
        
        # Convert sets to sorted lists
        return {
            'categories': sorted(list(filters['categories'])),
            'subcategories': sorted(list(filters['subcategories'])),
            'vendors': sorted(list(filters['vendors'])),
            'months': sorted(list(filters['months'])),
            'chunk_types': sorted(list(filters['chunk_types']))
        }

def main():
    """Test the retriever functionality."""
    retriever = ExpenseRetriever()
    
    # Test queries
    test_queries = [
        "How much was spent on power supply?",
        "elevator maintenance costs",
        "total expenses March 2025",
        "CEMIG payments",
        "cleaning services expenses"
    ]
    
    print("Testing ExpenseRetriever...")
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print('='*50)
        
        results = retriever.search_natural_language(query)
        
        print(f"Found {results['total_results']} results:")
        for result in results['results'][:3]:  # Show top 3
            print(f"\n- {result['content'][:150]}...")
            print(f"  Type: {result['chunk_type']}")
            print(f"  Score: {result['similarity_score']:.3f}")
    
    # Test available filters
    print(f"\n{'='*50}")
    print("Available Filters:")
    print('='*50)
    filters = retriever.get_available_filters()
    for filter_type, values in filters.items():
        print(f"{filter_type}: {values[:5]}...")  # Show first 5

if __name__ == "__main__":
    main()