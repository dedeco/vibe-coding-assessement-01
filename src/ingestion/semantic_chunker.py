import json
import uuid
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class SemanticChunker:
    def __init__(self, input_file: str = "data/processed/processed_expenses.json", 
                 output_folder: str = "data/chunks"):
        self.input_file = Path(input_file)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
    def create_expense_chunk(self, expense: Dict[str, Any]) -> Dict[str, Any]:
        """Create a semantic chunk for an individual expense."""
        
        # Format amount for natural language
        amount_formatted = f"R$ {expense['amount']:,.2f}"
        
        # Create natural language content
        content_parts = []
        
        # Basic expense information
        if expense['vendor']:
            content_parts.append(f"{expense['description']} - {amount_formatted} paid to {expense['vendor']}")
        else:
            content_parts.append(f"{expense['description']} - {amount_formatted}")
        
        # Add category context
        if expense['category'] != 'other':
            content_parts.append(f"Category: {expense['category'].title()}")
            if expense['subcategory'] != 'miscellaneous':
                content_parts.append(f"Subcategory: {expense['subcategory'].replace('_', ' ').title()}")
        
        # Add temporal context
        month_year_parts = expense['month_year'].split('-')
        if len(month_year_parts) == 2:
            year, month = month_year_parts
            month_names = {
                '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                '09': 'September', '10': 'October', '11': 'November', '12': 'December'
            }
            month_name = month_names.get(month, month)
            content_parts.append(f"Period: {month_name} {year}")
        
        content = ". ".join(content_parts) + "."
        
        chunk = {
            'chunk_id': f"expense_{expense['id']}_{uuid.uuid4().hex[:8]}",
            'content': content,
            'chunk_type': 'individual_expense',
            'metadata': {
                'expense_id': expense['id'],
                'description': expense['description'],
                'amount': expense['amount'],
                'amount_formatted': amount_formatted,
                'vendor': expense['vendor'],
                'category': expense['category'],
                'subcategory': expense['subcategory'],
                'month_year': expense['month_year'],
                'document': expense['document'],
                'currency': expense['currency']
            }
        }
        
        return chunk
    
    def create_category_summary_chunk(self, category: str, expenses: List[Dict[str, Any]], 
                                    month_year: str) -> Dict[str, Any]:
        """Create a summary chunk for a category in a specific month."""
        
        total_amount = sum(exp['amount'] for exp in expenses)
        count = len(expenses)
        
        # Get subcategory breakdown
        subcategories = {}
        vendors = set()
        
        for expense in expenses:
            subcat = expense['subcategory']
            if subcat not in subcategories:
                subcategories[subcat] = {'count': 0, 'total': 0.0}
            subcategories[subcat]['count'] += 1
            subcategories[subcat]['total'] += expense['amount']
            
            if expense['vendor']:
                vendors.add(expense['vendor'])
        
        # Format month/year
        month_year_parts = month_year.split('-')
        if len(month_year_parts) == 2:
            year, month = month_year_parts
            month_names = {
                '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                '09': 'September', '10': 'October', '11': 'November', '12': 'December'
            }
            month_name = month_names.get(month, month)
            period = f"{month_name} {year}"
        else:
            period = month_year
        
        # Create natural language content
        content_parts = [
            f"{category.title()} expenses for {period}: R$ {total_amount:,.2f} total across {count} items"
        ]
        
        if len(subcategories) > 1:
            subcat_details = []
            for subcat, info in subcategories.items():
                subcat_name = subcat.replace('_', ' ').title()
                subcat_details.append(f"{subcat_name}: R$ {info['total']:,.2f}")
            content_parts.append(f"Breakdown: {', '.join(subcat_details)}")
        
        if vendors:
            vendor_list = list(vendors)[:5]  # Show top 5 vendors
            if len(vendor_list) < len(vendors):
                vendor_text = f"Main vendors: {', '.join(vendor_list)} and {len(vendors) - len(vendor_list)} others"
            else:
                vendor_text = f"Vendors: {', '.join(vendor_list)}"
            content_parts.append(vendor_text)
        
        content = ". ".join(content_parts) + "."
        
        chunk = {
            'chunk_id': f"category_{category}_{month_year}_{uuid.uuid4().hex[:8]}",
            'content': content,
            'chunk_type': 'category_summary',
            'metadata': {
                'category': category,
                'month_year': month_year,
                'period': period,
                'total_amount': total_amount,
                'expense_count': count,
                'subcategories': subcategories,
                'vendors': list(vendors),
                'currency': 'BRL'
            }
        }
        
        return chunk
    
    def create_monthly_summary_chunk(self, month_year: str, 
                                   expenses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary chunk for all expenses in a specific month."""
        
        total_amount = sum(exp['amount'] for exp in expenses)
        count = len(expenses)
        
        # Category breakdown
        categories = {}
        all_vendors = set()
        
        for expense in expenses:
            category = expense['category']
            if category not in categories:
                categories[category] = {'count': 0, 'total': 0.0}
            categories[category]['count'] += 1
            categories[category]['total'] += expense['amount']
            
            if expense['vendor']:
                all_vendors.add(expense['vendor'])
        
        # Format month/year
        month_year_parts = month_year.split('-')
        if len(month_year_parts) == 2:
            year, month = month_year_parts
            month_names = {
                '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                '09': 'September', '10': 'October', '11': 'November', '12': 'December'
            }
            month_name = month_names.get(month, month)
            period = f"{month_name} {year}"
        else:
            period = month_year
        
        # Create natural language content
        content_parts = [
            f"Monthly summary for {period}: R$ {total_amount:,.2f} total expenses across {count} items"
        ]
        
        # Top categories
        sorted_categories = sorted(categories.items(), key=lambda x: x[1]['total'], reverse=True)
        top_categories = []
        for cat_name, cat_info in sorted_categories[:3]:
            cat_display = cat_name.replace('_', ' ').title()
            top_categories.append(f"{cat_display}: R$ {cat_info['total']:,.2f}")
        
        if top_categories:
            content_parts.append(f"Top categories: {', '.join(top_categories)}")
        
        # Vendor count
        if all_vendors:
            content_parts.append(f"Total vendors: {len(all_vendors)}")
        
        content = ". ".join(content_parts) + "."
        
        chunk = {
            'chunk_id': f"monthly_{month_year}_{uuid.uuid4().hex[:8]}",
            'content': content,
            'chunk_type': 'monthly_summary',
            'metadata': {
                'month_year': month_year,
                'period': period,
                'total_amount': total_amount,
                'expense_count': count,
                'categories': categories,
                'vendor_count': len(all_vendors),
                'currency': 'BRL'
            }
        }
        
        return chunk
    
    def create_vendor_chunks(self, expenses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create chunks for vendor-specific information."""
        vendor_data = {}
        
        # Group expenses by vendor
        for expense in expenses:
            vendor = expense['vendor']
            if not vendor:
                continue
                
            if vendor not in vendor_data:
                vendor_data[vendor] = []
            vendor_data[vendor].append(expense)
        
        chunks = []
        
        for vendor, vendor_expenses in vendor_data.items():
            if len(vendor_expenses) < 2:  # Skip vendors with only one expense
                continue
                
            total_amount = sum(exp['amount'] for exp in vendor_expenses)
            
            # Group by month
            monthly_data = {}
            categories = set()
            
            for expense in vendor_expenses:
                month = expense['month_year']
                if month not in monthly_data:
                    monthly_data[month] = {'count': 0, 'total': 0.0}
                monthly_data[month]['count'] += 1
                monthly_data[month]['total'] += expense['amount']
                categories.add(expense['category'])
            
            # Create content
            content_parts = [
                f"{vendor}: R$ {total_amount:,.2f} total across {len(vendor_expenses)} transactions"
            ]
            
            if len(monthly_data) > 1:
                months = sorted(monthly_data.keys())
                month_details = []
                for month in months:
                    month_info = monthly_data[month]
                    month_details.append(f"{month}: R$ {month_info['total']:,.2f}")
                content_parts.append(f"Monthly breakdown: {', '.join(month_details)}")
            
            if len(categories) > 1:
                cat_names = [cat.replace('_', ' ').title() for cat in categories]
                content_parts.append(f"Categories: {', '.join(cat_names)}")
            
            content = ". ".join(content_parts) + "."
            
            chunk = {
                'chunk_id': f"vendor_{vendor.replace(' ', '_')}_{uuid.uuid4().hex[:8]}",
                'content': content,
                'chunk_type': 'vendor_summary',
                'metadata': {
                    'vendor': vendor,
                    'total_amount': total_amount,
                    'transaction_count': len(vendor_expenses),
                    'monthly_data': monthly_data,
                    'categories': list(categories),
                    'currency': 'BRL'
                }
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def process_expenses_to_chunks(self) -> List[Dict[str, Any]]:
        """Process all expenses into semantic chunks."""
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file {self.input_file} does not exist")
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_expenses = data.get('all_expenses', [])
        if not all_expenses:
            print("No expenses found in input file")
            return []
        
        chunks = []
        
        # Create individual expense chunks
        print("Creating individual expense chunks...")
        for expense in all_expenses:
            chunk = self.create_expense_chunk(expense)
            chunks.append(chunk)
        
        # Group expenses by month for summary chunks
        monthly_expenses = {}
        for expense in all_expenses:
            month = expense['month_year']
            if month not in monthly_expenses:
                monthly_expenses[month] = []
            monthly_expenses[month].append(expense)
        
        # Create monthly summary chunks
        print("Creating monthly summary chunks...")
        for month_year, expenses in monthly_expenses.items():
            chunk = self.create_monthly_summary_chunk(month_year, expenses)
            chunks.append(chunk)
            
            # Create category summary chunks for this month
            category_expenses = {}
            for expense in expenses:
                category = expense['category']
                if category not in category_expenses:
                    category_expenses[category] = []
                category_expenses[category].append(expense)
            
            for category, cat_expenses in category_expenses.items():
                if len(cat_expenses) >= 2:  # Only create summaries for categories with multiple items
                    chunk = self.create_category_summary_chunk(category, cat_expenses, month_year)
                    chunks.append(chunk)
        
        # Create vendor chunks
        print("Creating vendor summary chunks...")
        vendor_chunks = self.create_vendor_chunks(all_expenses)
        chunks.extend(vendor_chunks)
        
        # Save chunks
        output_file = self.output_folder / "semantic_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        print(f"Created {len(chunks)} semantic chunks")
        print(f"Chunk types breakdown:")
        chunk_types = {}
        for chunk in chunks:
            chunk_type = chunk['chunk_type']
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        for chunk_type, count in chunk_types.items():
            print(f"  {chunk_type}: {count}")
        
        print(f"Chunks saved to {output_file}")
        
        return chunks

def main():
    """Main function to run the semantic chunker."""
    chunker = SemanticChunker()
    chunks = chunker.process_expenses_to_chunks()
    return chunks

if __name__ == "__main__":
    main()