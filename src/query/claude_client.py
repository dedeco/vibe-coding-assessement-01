import os
import anthropic
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

class ClaudeExpenseAnalyst:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude client for expense analysis."""
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        if not self.api_key:
            raise ValueError("Claude API key not found. Set CLAUDE_API_KEY environment variable.")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-sonnet-20240229"
        
    def create_system_prompt(self) -> str:
        """Create system prompt for the expense analysis assistant."""
        return """You are an intelligent assistant helping condominium associates analyze their monthly trial balance reports. 

You have access to processed financial data from trial balance documents, including:
- Individual expense items with amounts, vendors, categories, and dates
- Monthly summaries and category breakdowns
- Vendor payment histories
- Expense categorizations (utilities, maintenance, services, supplies)

Your role is to:
1. Answer questions about expenses clearly and accurately
2. Provide specific amounts when asked
3. Explain expense categories and patterns
4. Compare expenses across months when relevant
5. Highlight important financial insights

Guidelines:
- Always provide specific amounts in Brazilian Reais (R$) when available
- Be precise with dates and vendor names
- Explain technical terms in simple language
- If data is missing or unclear, acknowledge this
- Suggest follow-up questions that might be helpful
- Keep responses concise but informative
- Use Portuguese or English based on the user's question language

Remember: You're helping condominium associates understand their financial contributions and verify expense allocations."""

    def format_context_from_results(self, results: Dict[str, Any]) -> str:
        """Format search results into context for Claude."""
        
        context_parts = []
        
        # Add query information
        context_parts.append(f"User Query: {results.get('query', 'N/A')}")
        context_parts.append(f"Found {results.get('total_results', 0)} relevant results:")
        context_parts.append("")
        
        # Process each result
        for i, result in enumerate(results.get('results', []), 1):
            context_parts.append(f"Result {i} (Score: {result.get('similarity_score', 0):.3f}):")
            context_parts.append(f"Content: {result.get('content', '')}")
            
            # Add structured metadata
            metadata = result.get('metadata', {})
            if metadata:
                context_parts.append("Metadata:")
                for key, value in metadata.items():
                    if value is not None and value != '':
                        context_parts.append(f"  - {key}: {value}")
            
            context_parts.append("")  # Empty line between results
        
        return "\n".join(context_parts)
    
    def generate_response(self, 
                         user_question: str, 
                         search_results: Dict[str, Any],
                         conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate response using Claude based on search results."""
        
        # Format context from search results
        context = self.format_context_from_results(search_results)
        
        # Build conversation messages
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-4:]:  # Keep last 4 exchanges
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add current query with context
        user_message = f"""Based on the following financial data from the condominium trial balance, please answer my question:

FINANCIAL DATA:
{context}

QUESTION: {user_question}

Please provide a clear, specific answer based on the data above. Include relevant amounts, dates, and vendor information when available."""

        messages.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,
                system=self.create_system_prompt(),
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"Sorry, I encountered an error while processing your request: {str(e)}"
    
    def analyze_expenses(self, 
                        user_question: str, 
                        search_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze expenses and return structured response."""
        
        # Generate natural language response
        response_text = self.generate_response(user_question, search_results)
        
        # Extract key information from search results for structured data
        relevant_amounts = []
        relevant_vendors = set()
        relevant_categories = set()
        relevant_months = set()
        
        for result in search_results.get('results', []):
            metadata = result.get('metadata', {})
            
            if metadata.get('amount'):
                relevant_amounts.append({
                    'amount': metadata['amount'],
                    'description': metadata.get('description', ''),
                    'vendor': metadata.get('vendor', ''),
                    'category': metadata.get('category', '')
                })
            
            if metadata.get('vendor'):
                relevant_vendors.add(metadata['vendor'])
            
            if metadata.get('category'):
                relevant_categories.add(metadata['category'])
            
            if metadata.get('month_year'):
                relevant_months.add(metadata['month_year'])
        
        return {
            'answer': response_text,
            'query': user_question,
            'total_results_found': search_results.get('total_results', 0),
            'relevant_data': {
                'amounts': relevant_amounts,
                'vendors': list(relevant_vendors),
                'categories': list(relevant_categories),
                'months': list(relevant_months)
            },
            'raw_results': search_results.get('results', [])[:5]  # Top 5 for reference
        }
    
    def suggest_follow_up_questions(self, 
                                   user_question: str, 
                                   analysis_result: Dict[str, Any]) -> List[str]:
        """Suggest follow-up questions based on the analysis."""
        
        suggestions = []
        relevant_data = analysis_result.get('relevant_data', {})
        
        # Suggest based on categories found
        categories = relevant_data.get('categories', [])
        if categories:
            for category in categories[:2]:  # Top 2 categories
                suggestions.append(f"What other {category} expenses do we have?")
        
        # Suggest based on vendors found
        vendors = relevant_data.get('vendors', [])
        if vendors:
            for vendor in vendors[:2]:  # Top 2 vendors
                suggestions.append(f"Show me all payments to {vendor}")
        
        # Suggest based on months found
        months = relevant_data.get('months', [])
        if months:
            for month in months[:2]:  # Top 2 months
                suggestions.append(f"What was the total spent in {month}?")
        
        # Generic suggestions
        if not suggestions:
            suggestions = [
                "What are the highest expenses this month?",
                "Show me all utility costs",
                "What maintenance expenses do we have?"
            ]
        
        return suggestions[:3]  # Return max 3 suggestions
    
    def create_expense_summary(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured summary of expenses from search results."""
        
        total_amount = 0
        expenses_by_category = {}
        expenses_by_month = {}
        expenses_by_vendor = {}
        
        for result in search_results.get('results', []):
            metadata = result.get('metadata', {})
            
            amount = metadata.get('amount', 0)
            if amount:
                total_amount += amount
                
                # By category
                category = metadata.get('category', 'other')
                if category not in expenses_by_category:
                    expenses_by_category[category] = {'count': 0, 'total': 0}
                expenses_by_category[category]['count'] += 1
                expenses_by_category[category]['total'] += amount
                
                # By month
                month = metadata.get('month_year', 'unknown')
                if month not in expenses_by_month:
                    expenses_by_month[month] = {'count': 0, 'total': 0}
                expenses_by_month[month]['count'] += 1
                expenses_by_month[month]['total'] += amount
                
                # By vendor
                vendor = metadata.get('vendor', 'unknown')
                if vendor and vendor != 'unknown':
                    if vendor not in expenses_by_vendor:
                        expenses_by_vendor[vendor] = {'count': 0, 'total': 0}
                    expenses_by_vendor[vendor]['count'] += 1
                    expenses_by_vendor[vendor]['total'] += amount
        
        return {
            'total_amount': total_amount,
            'total_items': len(search_results.get('results', [])),
            'by_category': expenses_by_category,
            'by_month': expenses_by_month,
            'by_vendor': expenses_by_vendor
        }

def main():
    """Test the Claude client functionality."""
    
    print("Claude client test requires:")
    print("1. CLAUDE_API_KEY environment variable to be set")
    print("2. Test data in ChromaDB")
    print("3. Use the main API endpoints for testing instead")
    print("\nRun the test suite with: python scripts/test_api_responses.py")

if __name__ == "__main__":
    main()