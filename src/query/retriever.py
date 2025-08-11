import os
import chromadb
from pathlib import Path
from typing import List, Dict, Any, Optional

# Disable ChromaDB telemetry
os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ['CHROMA_TELEMETRY'] = 'false'

class ExpenseRetriever:
    def __init__(self, db_path: str = "data/chromadb"):
        self.db_path = Path(db_path)
        
        # Monkey patch to fix telemetry capture error
        try:
            import chromadb.telemetry.posthog as posthog_module
            original_capture = posthog_module.Posthog.capture
            def fixed_capture(self, event, properties=None):
                try:
                    if properties is None:
                        properties = {}
                    return original_capture(event, properties)
                except Exception:
                    pass  # Silently ignore telemetry errors
            posthog_module.Posthog.capture = fixed_capture
        except Exception:
            pass  # If monkey patching fails, continue anyway
        
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
        
        # Get available data to validate query against existing content
        available_filters = self.get_available_filters()
        
        # Extract potential month references
        month_mapping = {
            'january': '2024-01', 'february': '2024-02', 'march': '2024-03',
            'april': '2024-04', 'may': '2024-05', 'june': '2024-06',
            'july': '2024-07', 'august': '2024-08', 'september': '2024-09',
            'october': '2024-10', 'november': '2024-11', 'december': '2024-12'
        }
        
        requested_month = None
        for month_name, month_code in month_mapping.items():
            if month_name in query_lower:
                requested_month = month_code
                break
        
        # Check if requested month exists in data
        if requested_month and requested_month not in available_filters.get('months', []):
            available_months = available_filters.get('months', [])
            suggestions = self._generate_month_suggestions(query, available_months)
            
            return {
                'query': query,
                'total_results': 0,
                'results': [],
                'error': f"No data available for {requested_month.split('-')[1]}/{requested_month.split('-')[0]}. Available months: {', '.join(available_months)}",
                'suggestions': suggestions,
                'reformulated_queries': [
                    f"What were the expenses for {self._format_month_name(month)}?" 
                    for month in available_months[:2]
                ]
            }
        
        # Check for salary/personnel keywords that might not exist in categories
        salary_keywords = ['salary', 'personnel', 'payroll', 'staff', 'employee', 'wages']
        if any(keyword in query_lower for keyword in salary_keywords):
            # Check if we have any personnel-related categories
            personnel_categories = [cat for cat in available_filters.get('categories', []) 
                                  if any(word in cat.lower() for word in ['personnel', 'salary', 'payroll', 'staff', 'employee'])]
            
            if not personnel_categories:
                available_categories = available_filters.get('categories', [])
                suggestions = self._generate_category_suggestions(query, available_categories)
                
                return {
                    'query': query,
                    'total_results': 0,
                    'results': [],
                    'error': f"No salary/personnel expenses found in data. Available categories: {', '.join(available_categories)}",
                    'suggestions': suggestions,
                    'reformulated_queries': [
                        query.replace(keyword, category) 
                        for keyword in salary_keywords if keyword in query_lower
                        for category in available_categories[:2]
                    ][:3]
                }
        
        # Perform search based on query type
        if requested_month:
            # Month-based query with month filter
            return self.search_by_month(requested_month, n_results=15)
        
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
            # General search - but check if we get good results
            results = self.search_expenses(query, n_results=12)
            
            # If no results or very low similarity scores, provide better feedback
            if (not results['results'] or 
                all(result.get('similarity_score', 0) < 0.3 for result in results['results'][:3])):
                suggestions = self._generate_general_suggestions(available_filters)
                
                return {
                    'query': query,
                    'total_results': 0,
                    'results': [],
                    'error': f"No relevant results found. Try searching for: {', '.join(available_filters.get('categories', []))} or months: {', '.join(available_filters.get('months', []))}",
                    'suggestions': suggestions,
                    'reformulated_queries': self._suggest_better_queries(query, available_filters)
                }
            
            return results
    
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
    
    def _generate_month_suggestions(self, original_query: str, available_months: List[str]) -> List[str]:
        """Generate intelligent follow-up suggestions for month-based queries."""
        suggestions = []
        
        # Extract the intent from the original query
        query_lower = original_query.lower()
        if 'salary' in query_lower or 'personnel' in query_lower:
            intent = "expenses by category"
        elif 'total' in query_lower or 'summary' in query_lower:
            intent = "monthly summary"
        else:
            intent = "expenses"
        
        for month in available_months[:2]:
            month_name = self._format_month_name(month)
            suggestions.append(f"What were the {intent} for {month_name}?")
        
        suggestions.append("What categories of expenses do we track?")
        return suggestions
    
    def _generate_category_suggestions(self, original_query: str, available_categories: List[str]) -> List[str]:
        """Generate intelligent follow-up suggestions for category-based queries."""
        suggestions = []
        
        # Extract month context if present
        query_lower = original_query.lower()
        month_context = ""
        month_mapping = {
            'january': '2024-01', 'february': '2024-02', 'march': '2024-03',
            'april': '2024-04', 'may': '2024-05', 'june': '2024-06',
            'july': '2024-07', 'august': '2024-08', 'september': '2024-09',
            'october': '2024-10', 'november': '2024-11', 'december': '2024-12'
        }
        
        for month_name, month_code in month_mapping.items():
            if month_name in query_lower:
                month_context = f" in {self._format_month_name(month_code)}"
                break
        
        for category in available_categories:
            suggestions.append(f"What were the {category} expenses{month_context}?")
        
        if month_context:
            suggestions.append(f"What was the total spent{month_context}?")
        else:
            suggestions.append("What was the total spent across all months?")
        
        return suggestions[:3]
    
    def _generate_general_suggestions(self, available_filters: Dict[str, List[str]]) -> List[str]:
        """Generate general follow-up suggestions based on available data."""
        suggestions = []
        
        categories = available_filters.get('categories', [])
        months = available_filters.get('months', [])
        
        if categories:
            suggestions.append(f"Show me {categories[0]} expenses")
        
        if months:
            latest_month = max(months)
            suggestions.append(f"What was spent in {self._format_month_name(latest_month)}?")
        
        if len(months) > 1:
            suggestions.append("Compare expenses across all months")
        
        suggestions.append("What are the highest individual expenses?")
        
        return suggestions[:3]
    
    def _suggest_better_queries(self, original_query: str, available_filters: Dict[str, List[str]]) -> List[str]:
        """Suggest better reformulated queries based on available data."""
        suggestions = []
        
        categories = available_filters.get('categories', [])
        months = available_filters.get('months', [])
        
        # If query mentions unavailable terms, suggest replacements
        query_lower = original_query.lower()
        
        if categories and months:
            # Create combinations of available data
            for category in categories[:2]:
                for month in months[:2]:
                    month_name = self._format_month_name(month)
                    suggestions.append(f"How much was spent on {category} in {month_name}?")
        
        # Add general queries based on available data
        if months:
            latest_month = max(months)
            suggestions.append(f"What was the total spent in {self._format_month_name(latest_month)}?")
        
        return suggestions[:3]
    
    def _format_month_name(self, month_code: str) -> str:
        """Convert month code (2025-03) to readable format (March 2025)."""
        try:
            year, month_num = month_code.split('-')
            month_names = {
                '01': 'January', '02': 'February', '03': 'March',
                '04': 'April', '05': 'May', '06': 'June',
                '07': 'July', '08': 'August', '09': 'September',
                '10': 'October', '11': 'November', '12': 'December'
            }
            return f"{month_names.get(month_num, month_num)} {year}"
        except:
            return month_code

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