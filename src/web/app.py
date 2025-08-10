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
        retriever = ExpenseRetriever()
        print("✅ ExpenseRetriever initialized")
        
        # Initialize Claude client
        claude_api_key = os.getenv('CLAUDE_API_KEY')
        if claude_api_key:
            claude_client = ClaudeExpenseAnalyst(claude_api_key)
            print("✅ Claude client initialized")
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
    
    if not search_results.get('results'):
        return "I couldn't find any information related to your question in the trial balance data."
    
    # Extract key information
    total_amount = 0
    items = []
    
    for result in search_results['results'][:5]:
        content = result.get('content', '')
        metadata = result.get('metadata', {})
        
        amount = metadata.get('amount', 0)
        if amount:
            total_amount += amount
        
        # Extract key details for response
        items.append({
            'content': content,
            'amount': amount,
            'category': metadata.get('category', ''),
            'vendor': metadata.get('vendor', ''),
            'month': metadata.get('month_year', '')
        })
    
    # Build response
    response_parts = []
    
    if question.lower().find('how much') != -1 or question.lower().find('total') != -1:
        if total_amount > 0:
            response_parts.append(f"Based on the trial balance data, I found expenses totaling R$ {total_amount:,.2f}.")
        
    response_parts.append(f"Here are the relevant details I found:")
    
    for i, item in enumerate(items[:3], 1):
        response_parts.append(f"{i}. {item['content'][:200]}...")
    
    if len(search_results['results']) > 3:
        response_parts.append(f"... and {len(search_results['results']) - 3} more items.")
    
    return "\n\n".join(response_parts)

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
        reload_dirs=["src"]
    )