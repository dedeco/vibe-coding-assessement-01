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
        
        try:
            # Initialize client with minimal configuration
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.model = "claude-3-5-sonnet-20241022"
        except Exception as e:
            raise ValueError(f"Failed to initialize Claude client: {str(e)}")
        
    def create_system_prompt(self) -> str:
        """Create system prompt for the expense analysis assistant."""
        return """You are an expert financial analyst specialized in condominium expense analysis. You provide confident, assertive answers based on trial balance data.

AVAILABLE DATA:
- Individual expense items with precise amounts, vendors, categories, and dates
- Monthly summaries and category breakdowns
- Vendor payment histories
- Expense categorizations (utilities, maintenance, services, supplies)

YOUR EXPERTISE:
1. Provide confident, definitive answers when data is available
2. Give specific amounts in Brazilian Reais (R$) with precise formatting
3. Explain expense patterns and identify trends
4. Make direct comparisons and provide context
5. Highlight important financial insights proactively

RESPONSE STYLE:
- Be assertive and confident: "The expenses were R$ X" not "It appears the expenses might be"
- START WITH THE TOTAL AMOUNT ONLY - be concise and direct
- For utility/expense questions, provide just the final total amount
- Use strong, definitive language when data supports it
- Present the main number prominently and clearly
- Avoid lengthy explanations unless specifically asked for details

FORMATTING:
- Lead with just the key total: "R$ 2,865.00" or "R$ 2,865.00 total utilities in January 2025"
- Keep responses to 1-2 sentences maximum for simple total questions  
- Only provide breakdowns if explicitly requested
- Bold the main amount

LANGUAGE:
- Use Portuguese or English based on the user's question
- Be direct and professional
- Avoid hedging language ("seems", "appears", "might be")
- State facts confidently based on the provided data

Remember: You're the expert. The associates trust your analysis to make informed financial decisions."""

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
        user_message = f"""CONDOMINIUM FINANCIAL ANALYSIS REQUEST

QUESTION: {user_question}

AVAILABLE FINANCIAL DATA:
{context}

INSTRUCTIONS:
- Provide a confident, definitive answer based on the data
- START WITH THE TOTAL AMOUNT IMMEDIATELY - lead with the main number
- For simple cost questions, provide just the total amount in R$ format
- Keep responses concise (1-2 sentences) unless breakdown is specifically requested
- Only provide detailed breakdowns if user asks for "details", "breakdown", or "show me all"
- Be direct and assertive - give the number first, context second"""

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
        
        # Check if search returned an error
        if 'error' in search_results and search_results['total_results'] == 0:
            error_response = f"I couldn't find any data matching your query. {search_results['error']}"
            
            # Add intelligent suggestions if available
            if 'suggestions' in search_results and search_results['suggestions']:
                error_response += "\n\nHere are some questions you could ask instead:"
                for i, suggestion in enumerate(search_results['suggestions'], 1):
                    error_response += f"\n{i}. {suggestion}"
            
            # Add reformulated queries if available
            if 'reformulated_queries' in search_results and search_results['reformulated_queries']:
                error_response += "\n\nTry these similar questions with available data:"
                for i, reformulated in enumerate(search_results['reformulated_queries'], 1):
                    error_response += f"\n• {reformulated}"
            
            return {
                'answer': error_response,
                'query': user_question,
                'total_results_found': 0,
                'relevant_data': {
                    'amounts': [],
                    'vendors': [],
                    'categories': [],
                    'months': []
                },
                'raw_results': [],
                'suggestions': search_results.get('suggestions', []),
                'reformulated_queries': search_results.get('reformulated_queries', [])
            }
        
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
        
        # Check if user wants detailed breakdown
        wants_details = any(keyword in user_question.lower() for keyword in ['breakdown', 'details', 'show me all', 'list all', 'show all'])
        
        # Format response - simple for totals, detailed for breakdowns
        if wants_details:
            formatted_answer = self._format_progressive_response(user_question, search_results, response_text)
        else:
            # Return concise response for simple total questions
            formatted_answer = response_text
        
        return {
            'answer': formatted_answer,
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
    
    def _format_progressive_response(self, user_question: str, search_results: Dict[str, Any], claude_response: str) -> str:
        """Format response using progressive disclosure pattern."""
        
        results = search_results.get('results', [])
        if not results:
            return claude_response
        
        # Extract expenses with amounts
        expenses = []
        summary_info = None
        
        for result in results:
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            
            # Check if this is a summary
            if 'monthly summary' in content.lower() or 'total expenses' in content.lower():
                summary_info = {
                    'content': content,
                    'metadata': metadata
                }
                continue
            
            # Extract individual expenses
            amount = metadata.get('amount')
            if amount and amount > 0:
                expenses.append({
                    'amount': float(amount),
                    'content': content,
                    'metadata': metadata,
                    'description': self._extract_description(content),
                    'category': metadata.get('category', 'Other'),
                    'vendor': metadata.get('vendor', ''),
                    'month': metadata.get('month_year', '')
                })
        
        # Sort expenses by amount (highest first)
        expenses.sort(key=lambda x: x['amount'], reverse=True)
        
        if not expenses and not summary_info:
            return claude_response
        
        return self._build_progressive_markdown(user_question, expenses, summary_info, claude_response)
    
    def _extract_description(self, content: str) -> str:
        """Extract clean description from content."""
        # Remove amount and period info for cleaner display
        import re
        
        # Remove "R$ X.XX" patterns
        content = re.sub(r'R\$\s*[\d,]+\.?\d*', '', content)
        # Remove "Period: YYYY-MM" patterns with more variations
        content = re.sub(r'Period:\s*\d{4}-\d{2}', '', content)
        content = re.sub(r'\.\s*Period:\s*[^.]*', '', content)
        # Remove extra dots and dashes
        content = re.sub(r'[.\-\s]+$', '', content)
        content = re.sub(r'^[.\-\s]+', '', content)
        # Clean up multiple spaces
        content = re.sub(r'\s+', ' ', content)
        
        # Limit length
        if len(content) > 70:
            content = content[:67] + '...'
        
        return content.strip()
    
    def _build_progressive_markdown(self, question: str, expenses: List[Dict], summary_info: Dict, claude_response: str) -> str:
        """Build progressive disclosure markdown response."""
        
        if not expenses:
            return claude_response
        
        # Determine how many to show initially (top 3 or top 5 based on total)
        total_items = len(expenses)
        if total_items <= 3:
            show_initially = total_items
            show_more = 0
        elif total_items <= 6:
            show_initially = 3
            show_more = total_items - 3
        else:
            show_initially = 4
            show_more = total_items - 4
        
        # Extract month/period info
        period_info = ""
        if expenses and expenses[0].get('month'):
            month_code = expenses[0]['month']
            try:
                year, month = month_code.split('-')
                month_names = {
                    '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                    '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                    '09': 'September', '10': 'October', '11': 'November', '12': 'December'
                }
                period_info = f"{month_names.get(month, month)} {year}"
            except:
                period_info = month_code
        
        # Calculate totals
        total_amount = sum(expense['amount'] for expense in expenses)
        shown_amount = sum(expense['amount'] for expense in expenses[:show_initially])
        hidden_amount = total_amount - shown_amount
        
        # Build response
        lines = []
        
        # Header with key info
        if period_info:
            lines.append(f"# {period_info}: R$ {total_amount:,.2f} Total Expenses")
        else:
            lines.append(f"# Expenses: R$ {total_amount:,.2f} Total")
        
        lines.append("")
        
        # Quick summary
        if total_items > 1:
            avg_amount = total_amount / total_items
            lines.append(f"## ⚡ Quick View (Top {show_initially})")
            lines.append(f"**{total_items} items** • **Average:** R$ {avg_amount:,.2f}")
            lines.append("")
        else:
            lines.append("## 💰 Expense Details")
            lines.append("")
        
        # Show top items
        for i, expense in enumerate(expenses[:show_initially], 1):
            amount_str = f"R$ {expense['amount']:,.2f}"
            description = expense['description']
            
            # Add emphasis for high-value items (top 2)
            if i <= 2 and total_items > 2:
                lines.append(f"{i}. **{amount_str}** — {description}")
            else:
                lines.append(f"{i}. **{amount_str}** — {description}")
        
        # Progressive disclosure section
        if show_more > 0:
            lines.append("")
            lines.append("<details>")
            lines.append(f"<summary>📋 <strong>Show all {total_items} items</strong> (+ R$ {hidden_amount:,.2f} more)</summary>")
            lines.append("")
            lines.append("### Complete List")
            
            # Show all items
            for i, expense in enumerate(expenses, 1):
                amount_str = f"R$ {expense['amount']:,.2f}"
                description = expense['description']
                lines.append(f"{i}. **{amount_str}** — {description}")
            
            # Add breakdown by category if multiple categories
            categories = {}
            for expense in expenses:
                cat = expense.get('category', 'Other')
                if cat not in categories:
                    categories[cat] = {'count': 0, 'total': 0}
                categories[cat]['count'] += 1
                categories[cat]['total'] += expense['amount']
            
            if len(categories) > 1:
                lines.append("")
                lines.append("### 📊 By Category")
                for cat, data in sorted(categories.items(), key=lambda x: x[1]['total'], reverse=True):
                    lines.append(f"- **{cat}:** {data['count']} items — R$ {data['total']:,.2f}")
            
            # Add value breakdown
            if total_items > 3:
                high_value = [e for e in expenses if e['amount'] > 500]
                low_value = [e for e in expenses if e['amount'] <= 500]
                
                if high_value and low_value:
                    lines.append("")
                    lines.append("### 💰 By Value Range")
                    lines.append(f"- **High (>R$ 500):** {len(high_value)} items — R$ {sum(e['amount'] for e in high_value):,.2f}")
                    lines.append(f"- **Standard (≤R$ 500):** {len(low_value)} items — R$ {sum(e['amount'] for e in low_value):,.2f}")
            
            lines.append("")
            lines.append("</details>")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Add related questions based on data
        lines.append("## 🎯 Related Questions")
        if period_info:
            lines.append(f"- [Compare with other months](#)")
            lines.append(f"- [Show {period_info.split()[0]} trends](#)")
        
        if len(set(e.get('category') for e in expenses)) == 1:
            cat = expenses[0].get('category', 'Other')
            lines.append(f"- [Other {cat.lower()} expenses](#)")
        
        lines.append("- [Highest expenses across all months](#)")
        
        return "\n".join(lines)
    
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