#!/usr/bin/env python3

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import random

# Import from src package
from pathlib import Path

# Add project root to Python path for package imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ingestion import ExpenseIndexer

def generate_test_expenses():
    """Generate diverse test expense data to avoid hardcoded responses."""
    
    # Diverse categories and subcategories
    categories = {
        'utilities': ['electricity', 'water', 'gas', 'internet', 'phone'],
        'maintenance': ['elevator', 'plumbing', 'electrical', 'hvac', 'general'],
        'services': ['cleaning', 'security', 'landscaping', 'waste_management'],
        'supplies': ['office_supplies', 'cleaning_supplies', 'maintenance_supplies'],
        'insurance': ['property_insurance', 'liability_insurance'],
        'administration': ['accounting', 'legal', 'management_fees']
    }
    
    # Diverse vendor names (avoiding hardcoded CEMIG)
    vendors = {
        'utilities': ['PowerCorp Brazil', 'AquaServ Ltda', 'GasDistrib SA', 'NetConnect', 'TeleBrasil'],
        'maintenance': ['TechFix Solutions', 'ElevatorPro', 'PlumbingExperts', 'ElectricWorks', 'HVAC Masters'],
        'services': ['CleanPro Services', 'SecurityPlus', 'GreenLandscape', 'WasteAway'],
        'supplies': ['OfficeSupply Co', 'CleanSupplies Inc', 'ToolsRUs'],
        'insurance': ['InsuranceCorp', 'SafeGuard Insurance'],
        'administration': ['AccountPro', 'LegalAdvice Ltd', 'PropertyManage']
    }
    
    # Generate expenses for different months (avoiding hardcoded March 2025)
    months = ['2024-01', '2024-02', '2024-04', '2024-05', '2024-06', '2024-07', '2024-08', '2024-09', '2024-10', '2024-11', '2024-12']
    
    expenses = []
    expense_id = 1
    
    for month in months:
        month_expenses = []
        
        for category, subcategories in categories.items():
            for subcategory in subcategories:
                # Generate 1-3 expenses per subcategory per month
                num_expenses = random.randint(1, 3)
                
                for _ in range(num_expenses):
                    vendor = random.choice(vendors.get(category, ['Generic Vendor']))
                    
                    # Generate realistic amounts (avoiding hardcoded R$ 2,450.30)
                    base_amount = {
                        'utilities': (500, 3000),
                        'maintenance': (200, 2000),
                        'services': (300, 1500),
                        'supplies': (50, 500),
                        'insurance': (1000, 5000),
                        'administration': (800, 2500)
                    }
                    
                    min_amt, max_amt = base_amount.get(category, (100, 1000))
                    amount = round(random.uniform(min_amt, max_amt), 2)
                    
                    # Random day in month
                    day = random.randint(1, 28)
                    date = f"{month}-{day:02d}"
                    
                    expense = {
                        'id': expense_id,
                        'description': f'{subcategory.replace("_", " ").title()} expense for {month}',
                        'amount': amount,
                        'vendor': vendor,
                        'category': category,
                        'subcategory': subcategory,
                        'date': date,
                        'month_year': month,
                        'payment_method': random.choice(['bank_transfer', 'check', 'credit_card']),
                        'status': 'paid'
                    }
                    
                    expenses.append(expense)
                    month_expenses.append(expense)
                    expense_id += 1
        
        # Create monthly summary
        total_amount = sum(e['amount'] for e in month_expenses)
        category_totals = {}
        for expense in month_expenses:
            cat = expense['category']
            category_totals[cat] = category_totals.get(cat, 0) + expense['amount']
        
        monthly_summary = {
            'type': 'monthly_summary',
            'month_year': month,
            'total_amount': total_amount,
            'total_items': len(month_expenses),
            'category_breakdown': category_totals,
            'description': f'Monthly summary for {month}: {len(month_expenses)} expenses totaling R$ {total_amount:,.2f}'
        }
        expenses.append(monthly_summary)
    
    return expenses

def create_document_chunks(expenses):
    """Create document chunks for indexing, similar to PDF processing."""
    
    chunks = []
    
    for expense in expenses:
        if expense.get('type') == 'monthly_summary':
            # Monthly summary chunk
            content = expense['description']
            for category, amount in expense['category_breakdown'].items():
                content += f"\n{category.title()}: R$ {amount:,.2f}"
            
            chunk = {
                'content': content,
                'metadata': {
                    'chunk_type': 'monthly_summary',
                    'month_year': expense['month_year'],
                    'total_amount': expense['total_amount'],
                    'expense_count': expense['total_items']
                }
            }
            chunks.append(chunk)
            
        else:
            # Individual expense chunk
            content = f"{expense['description']}: R$ {expense['amount']:,.2f} paid to {expense['vendor']} on {expense['date']}. Category: {expense['category'].title()}. Subcategory: {expense['subcategory'].replace('_', ' ').title()}. Period: {expense['month_year']}."
            
            chunk = {
                'content': content,
                'metadata': {
                    'chunk_type': 'individual_expense',
                    'category': expense['category'],
                    'subcategory': expense['subcategory'],
                    'amount': expense['amount'],
                    'vendor': expense['vendor'],
                    'month_year': expense['month_year'],
                    'date': expense['date']
                }
            }
            chunks.append(chunk)
    
    # Create category summaries
    category_data = {}
    for expense in expenses:
        if expense.get('type') != 'monthly_summary':
            cat = expense['category']
            month = expense['month_year']
            
            if cat not in category_data:
                category_data[cat] = {}
            if month not in category_data[cat]:
                category_data[cat][month] = {'items': [], 'total': 0}
            
            category_data[cat][month]['items'].append(expense)
            category_data[cat][month]['total'] += expense['amount']
    
    # Add category summary chunks
    for category, months in category_data.items():
        for month, data in months.items():
            content = f"{category.title()} expenses for {month}: R$ {data['total']:,.2f} total across {len(data['items'])} items."
            
            vendors = list(set(item['vendor'] for item in data['items']))
            if vendors:
                content += f" Main vendors: {', '.join(vendors[:3])}."
            
            chunk = {
                'content': content,
                'metadata': {
                    'chunk_type': 'category_summary',
                    'category': category,
                    'month_year': month,
                    'total_amount': data['total'],
                    'expense_count': len(data['items'])
                }
            }
            chunks.append(chunk)
    
    return chunks

def main():
    print("🗂️  Populating ChromaDB with Test Data")
    print("=" * 60)
    
    try:
        # Generate test data
        print("Generating diverse test expenses...")
        expenses = generate_test_expenses()
        print(f"Generated {len(expenses)} expense records")
        
        # Create document chunks
        print("Creating document chunks...")
        chunks = create_document_chunks(expenses)
        print(f"Created {len(chunks)} document chunks")
        
        # Initialize indexer
        print("Initializing indexer...")
        # Set up database path
        db_path = "../src/web/data/chromadb"
        indexer = ExpenseIndexer(db_path=db_path)
        
        # Index the chunks
        print("Indexing chunks into ChromaDB...")
        for chunk in chunks:
            indexer.add_chunk(
                content=chunk['content'],
                metadata=chunk['metadata']
            )
        
        # Verify indexing
        collection = indexer.get_collection()
        count = collection.count()
        print(f"✅ Successfully indexed {count} documents")
        
        # Save raw data for reference
        output_data = {
            'expenses': expenses,
            'chunks': chunks,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_expenses': len([e for e in expenses if e.get('type') != 'monthly_summary']),
                'total_chunks': len(chunks),
                'months_covered': len(set(e['month_year'] for e in expenses if 'month_year' in e)),
                'categories': list(set(e['category'] for e in expenses if 'category' in e))
            }
        }
        
        with open('test_data_generated.json', 'w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ Test data saved to test_data_generated.json")
        
        # Show sample queries to test
        print("\n📋 Sample queries to test:")
        sample_queries = [
            "How much was spent on electricity?",
            "What are the water costs in 2024-01?",
            "Show me elevator maintenance expenses",
            "What did we pay to PowerCorp Brazil?",
            "Total expenses for 2024-05",
        ]
        
        for i, query in enumerate(sample_queries, 1):
            print(f"  {i}. {query}")
        
        print(f"\n✅ ChromaDB populated successfully!")
        print(f"   Database location: {db_path}")
        print(f"   Total documents: {count}")
        
    except Exception as e:
        print(f"❌ Error populating test data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()