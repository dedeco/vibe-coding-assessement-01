from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import os
from pathlib import Path
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Disable telemetry to prevent startup warnings
os.environ['ANONYMIZED_TELEMETRY'] = 'false'
os.environ['CHROMA_TELEMETRY'] = 'false'
os.environ['CHROMADB_ANALYTICS'] = 'false'
os.environ['POSTHOG_DISABLED'] = 'true'

# Fix tokenizers parallelism warning
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Add parent directories to path to import our modules
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from src.query import ExpenseRetriever
from src.query.claude_client import ClaudeExpenseAnalyst

# Global components
retriever = None
claude_client = None
conversation_history = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global retriever, claude_client
    
    try:
        # Initialize retriever
        retriever = ExpenseRetriever("src/web/data/chromadb")
        print("✅ ExpenseRetriever initialized")
        
        # Initialize Claude client
        claude_api_key = os.getenv('CLAUDE_API_KEY')
        if claude_api_key:
            try:
                claude_client = ClaudeExpenseAnalyst(claude_api_key)
                print("✅ Claude client initialized")
            except Exception as claude_error:
                print(f"⚠️  Claude client initialization failed: {claude_error}")
                print("⚠️  Claude functionality will be limited.")
                claude_client = None
        else:
            print("⚠️  CLAUDE_API_KEY not found. Claude functionality will be limited.")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
    
    yield
    
    # Shutdown
    print("Application shutdown.")

# Initialize FastAPI app
app = FastAPI(
    title="Condominium Analytics Agent",
    description="Conversational analytics for condominium trial balance reports",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = current_dir / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Request/Response models
class QueryRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    question: str
    conversation_id: str
    relevant_data: Dict[str, Any]
    suggestions: List[str]
    success: bool
    error_message: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    components: Dict[str, str]
    message: str

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system health and component status."""
    
    components = {}
    overall_status = "healthy"
    
    # Check ChromaDB connection
    try:
        if retriever:
            collection = retriever.get_collection()
            count = collection.count()
            components["chromadb"] = f"healthy ({count} documents)"
        else:
            components["chromadb"] = "not initialized"
            overall_status = "degraded"
    except Exception as e:
        components["chromadb"] = f"error: {str(e)}"
        overall_status = "unhealthy"
    
    # Check Claude API
    if claude_client:
        components["claude_api"] = "configured"
    else:
        components["claude_api"] = "not configured"
        overall_status = "degraded" if overall_status == "healthy" else overall_status
    
    # Check environment
    components["environment"] = "ok"
    
    message = {
        "healthy": "All systems operational",
        "degraded": "Some components unavailable but core functionality works",
        "unhealthy": "Critical components failing"
    }.get(overall_status, "Unknown status")
    
    return HealthResponse(
        status=overall_status,
        components=components,
        message=message
    )

# Main query endpoint
@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a natural language query about expenses."""
    
    global conversation_history
    
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    try:
        # Search for relevant information
        search_results = retriever.search_natural_language(request.question)
        
        # Generate response
        if claude_client:
            # Use Claude for intelligent response
            analysis = claude_client.analyze_expenses(request.question, search_results)
            answer = analysis['answer']
            relevant_data = analysis['relevant_data']
            suggestions = claude_client.suggest_follow_up_questions(request.question, analysis)
        else:
            # Fallback: Simple response based on search results
            answer = generate_simple_response(request.question, search_results)
            relevant_data = extract_relevant_data(search_results)
            suggestions = generate_simple_suggestions(search_results)
        
        # Update conversation history
        conversation_history.append({
            "role": "user",
            "content": request.question
        })
        conversation_history.append({
            "role": "assistant", 
            "content": answer
        })
        
        # Keep only last 10 exchanges
        conversation_history = conversation_history[-20:]
        
        return QueryResponse(
            answer=answer,
            question=request.question,
            conversation_id=request.conversation_id or "default",
            relevant_data=relevant_data,
            suggestions=suggestions,
            success=True
        )
        
    except Exception as e:
        return QueryResponse(
            answer=f"Sorry, I encountered an error processing your question: {str(e)}",
            question=request.question,
            conversation_id=request.conversation_id or "default",
            relevant_data={},
            suggestions=[],
            success=False,
            error_message=str(e)
        )

def generate_simple_response(question: str, search_results: Dict[str, Any]) -> str:
    """Generate simple response without Claude API."""
    
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
        
        return error_response
    
    if not search_results.get('results'):
        return "I couldn't find any information related to your question in the trial balance data."
    
    # Use progressive disclosure formatting
    return format_progressive_fallback_response(question, search_results)

def extract_relevant_data(search_results: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant data from search results."""
    
    amounts = []
    vendors = set()
    categories = set()
    months = set()
    
    for result in search_results.get('results', []):
        metadata = result.get('metadata', {})
        
        if metadata.get('amount'):
            amounts.append({
                'amount': metadata['amount'],
                'description': metadata.get('description', result.get('content', '')[:100]),
                'vendor': metadata.get('vendor', ''),
                'category': metadata.get('category', '')
            })
        
        if metadata.get('vendor'):
            vendors.add(metadata['vendor'])
        
        if metadata.get('category'):
            categories.add(metadata['category'])
        
        if metadata.get('month_year'):
            months.add(metadata['month_year'])
    
    return {
        'amounts': amounts,
        'vendors': list(vendors),
        'categories': list(categories),
        'months': list(months)
    }

def generate_simple_suggestions(search_results: Dict[str, Any]) -> List[str]:
    """Generate simple follow-up suggestions."""
    
    suggestions = []
    relevant_data = extract_relevant_data(search_results)
    
    if relevant_data['categories']:
        category = list(relevant_data['categories'])[0]
        suggestions.append(f"Show me other {category} expenses")
    
    if relevant_data['vendors']:
        vendor = list(relevant_data['vendors'])[0]
        suggestions.append(f"What else did we pay to {vendor}?")
    
    if relevant_data['months']:
        month = list(relevant_data['months'])[0]
        suggestions.append(f"What was the total spent in {month}?")
    
    # Default suggestions
    if not suggestions:
        suggestions = [
            "What are the highest expenses?",
            "Show me utility costs",
            "What maintenance expenses do we have?"
        ]
    
    return suggestions[:3]

def format_progressive_fallback_response(question: str, search_results: Dict[str, Any]) -> str:
    """Format fallback response using progressive disclosure."""
    
    results = search_results.get('results', [])
    if not results:
        return "I couldn't find any information related to your question in the trial balance data."
    
    # Extract expenses with amounts
    expenses = []
    total_amount = 0
    
    for result in results:
        metadata = result.get('metadata', {})
        content = result.get('content', '')
        amount = metadata.get('amount', 0)
        
        if amount and amount > 0:
            expenses.append({
                'amount': float(amount),
                'content': content,
                'description': extract_clean_description(content),
                'category': metadata.get('category', 'Other'),
                'month': metadata.get('month_year', '')
            })
            total_amount += float(amount)
        else:
            # Include non-monetary items (summaries, etc.)
            expenses.append({
                'amount': 0,
                'content': content,
                'description': content[:100] + ('...' if len(content) > 100 else ''),
                'category': metadata.get('category', 'Summary'),
                'month': metadata.get('month_year', '')
            })
    
    # Sort by amount (highest first)
    expenses.sort(key=lambda x: x['amount'], reverse=True)
    
    # Build progressive response
    lines = []
    total_items = len(expenses)
    
    # Header
    if total_amount > 0:
        lines.append(f"# Found {total_items} results - R$ {total_amount:,.2f} total")
    else:
        lines.append(f"# Found {total_items} results")
    
    lines.append("")
    
    # Show top 3 items
    show_initially = min(3, total_items)
    remaining = total_items - show_initially
    
    lines.append(f"## ⚡ Top {show_initially} Results")
    lines.append("")
    
    for i, expense in enumerate(expenses[:show_initially], 1):
        if expense['amount'] > 0:
            lines.append(f"{i}. **R$ {expense['amount']:,.2f}** — {expense['description']}")
        else:
            lines.append(f"{i}. {expense['description']}")
    
    # Progressive disclosure for remaining items
    if remaining > 0:
        lines.append("")
        lines.append("<details>")
        lines.append(f"<summary>📋 <strong>Show all {total_items} results</strong></summary>")
        lines.append("")
        
        for i, expense in enumerate(expenses, 1):
            if expense['amount'] > 0:
                lines.append(f"{i}. **R$ {expense['amount']:,.2f}** — {expense['description']}")
            else:
                lines.append(f"{i}. {expense['description']}")
        
        lines.append("")
        lines.append("</details>")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("💡 **Tip:** Try asking more specific questions about categories or time periods for better results.")
    
    return "\n".join(lines)

def extract_clean_description(content: str) -> str:
    """Extract clean description from content."""
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

# Get available filters
@app.get("/filters")
async def get_available_filters():
    """Get available filter options."""
    
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    try:
        filters = retriever.get_available_filters()
        return {
            "success": True,
            "filters": filters
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filters": {}
        }

# Search by category
@app.get("/category/{category}")
async def search_by_category(category: str, month_year: Optional[str] = None):
    """Search expenses by category."""
    
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    try:
        results = retriever.search_by_category(category, month_year)
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": {}
        }

# Get monthly summary
@app.get("/month/{month_year}")
async def get_monthly_summary(month_year: str):
    """Get comprehensive monthly summary."""
    
    if not retriever:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    
    try:
        summary = retriever.get_monthly_summary(month_year)
        return {
            "success": True,
            "summary": summary
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "summary": {}
        }

# Serve main page
@app.get("/", response_class=HTMLResponse)
async def serve_main_page():
    """Serve the main application page."""
    
    html_file = Path(__file__).parent / "static" / "index.html"
    
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Condominium Analytics Agent</title>
        </head>
        <body>
            <h1>Condominium Analytics Agent</h1>
            <p>Frontend files not found. Please create the static files.</p>
            <p>API is running at <a href="/docs">/docs</a></p>
        </body>
        </html>
        """)

# Run the application
if __name__ == "__main__":
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    print("Starting Condominium Analytics Agent...")
    print(f"Server will be available at: http://localhost:{port}")
    print(f"API documentation at: http://localhost:{port}/docs")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
        reload_dirs=["../../src"]
    )