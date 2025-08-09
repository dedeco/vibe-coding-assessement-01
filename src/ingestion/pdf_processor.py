import os
import json
import pandas as pd
import pdfplumber
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

class TrialBalanceProcessor:
    def __init__(self, pdf_folder: str = "pdfs", output_folder: str = "data/processed"):
        self.pdf_folder = Path(pdf_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text content from PDF file."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_content = ""
                for page in pdf.pages:
                    text_content += page.extract_text() + "\n"
                return text_content
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def extract_tables_from_pdf(self, pdf_path: Path) -> List[List[List[str]]]:
        """Extract tables from PDF file."""
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
        except Exception as e:
            print(f"Error extracting tables from {pdf_path}: {e}")
        return tables
    
    def parse_amount(self, amount_str: str) -> float:
        """Parse Brazilian currency amount string to float."""
        if not amount_str or amount_str in ['', '-', 'N/A']:
            return 0.0
        
        # Remove currency symbols and clean the string
        cleaned = re.sub(r'[R$\s]', '', str(amount_str))
        
        # Handle negative amounts in parentheses
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        
        # Convert comma decimal separator to dot
        cleaned = cleaned.replace('.', '').replace(',', '.')
        
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    
    def categorize_expense(self, description: str) -> Dict[str, str]:
        """Categorize expense based on description."""
        description_lower = description.lower()
        
        # Define category mappings
        categories = {
            'utilities': {
                'power_supply': ['energia', 'eletric', 'cemig', 'light', 'copel'],
                'water': ['agua', 'water', 'saneamento', 'sabesp'],
                'gas': ['gas', 'ultragaz', 'liquigás'],
                'internet': ['internet', 'telefon', 'vivo', 'tim', 'oi']
            },
            'maintenance': {
                'elevator': ['elevador', 'elevator', 'otis', 'schindler'],
                'cleaning': ['limpeza', 'cleaning', 'faxina'],
                'gardening': ['jardim', 'garden', 'paisagismo'],
                'repairs': ['reparo', 'repair', 'conserto', 'manutencao']
            },
            'services': {
                'security': ['seguranca', 'security', 'portaria'],
                'administration': ['administracao', 'admin', 'gestao'],
                'legal': ['juridico', 'legal', 'advogado'],
                'accounting': ['contabil', 'accounting', 'contador']
            },
            'supplies': {
                'office': ['escritorio', 'office', 'papelaria'],
                'cleaning_supplies': ['material limpeza', 'detergente', 'sabao'],
                'maintenance_supplies': ['ferramenta', 'material manutencao']
            }
        }
        
        for main_category, subcategories in categories.items():
            for subcategory, keywords in subcategories.items():
                if any(keyword in description_lower for keyword in keywords):
                    return {'category': main_category, 'subcategory': subcategory}
        
        return {'category': 'other', 'subcategory': 'miscellaneous'}
    
    def extract_date_from_filename(self, filename: str) -> str:
        """Extract date from filename pattern PACTO_BALANCETE_0913_YYMM.pdf."""
        match = re.search(r'(\d{2})(\d{2})\.pdf$', filename)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            # Assume years 00-30 are 2000s, 31-99 are 1900s
            full_year = 2000 + year if year <= 30 else 1900 + year
            return f"{full_year}-{month:02d}"
        return "unknown"
    
    def process_tables_to_expenses(self, tables: List[List[List[str]]], 
                                 document_name: str, 
                                 month_year: str) -> List[Dict[str, Any]]:
        """Process extracted tables into structured expense data."""
        expenses = []
        
        for table in tables:
            if not table or len(table) < 2:
                continue
                
            # Try to identify expense table structure
            headers = [str(cell).lower().strip() if cell else '' for cell in table[0]]
            
            # Look for common column patterns
            desc_col = None
            amount_col = None
            vendor_col = None
            
            for i, header in enumerate(headers):
                if any(keyword in header for keyword in ['descri', 'conta', 'item']):
                    desc_col = i
                elif any(keyword in header for keyword in ['valor', 'debito', 'credito']):
                    amount_col = i
                elif any(keyword in header for keyword in ['fornecedor', 'vendor', 'credor']):
                    vendor_col = i
            
            # Process table rows
            for row_idx, row in enumerate(table[1:], 1):
                if not row or len(row) < 2:
                    continue
                
                # Extract description and amount
                description = ""
                amount = 0.0
                vendor = ""
                
                if desc_col is not None and desc_col < len(row):
                    description = str(row[desc_col]).strip() if row[desc_col] else ""
                
                if amount_col is not None and amount_col < len(row):
                    amount = self.parse_amount(row[amount_col])
                
                if vendor_col is not None and vendor_col < len(row):
                    vendor = str(row[vendor_col]).strip() if row[vendor_col] else ""
                
                # Skip empty or header-like rows
                if not description or amount == 0.0 or len(description) < 3:
                    continue
                
                # Categorize the expense
                category_info = self.categorize_expense(description)
                
                expense = {
                    'id': f"{document_name}_{row_idx}",
                    'description': description,
                    'amount': amount,
                    'vendor': vendor,
                    'category': category_info['category'],
                    'subcategory': category_info['subcategory'],
                    'month_year': month_year,
                    'document': document_name,
                    'currency': 'BRL'
                }
                
                expenses.append(expense)
        
        return expenses
    
    def process_single_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Process a single PDF file and extract expense data."""
        print(f"Processing {pdf_path.name}...")
        
        # Extract month/year from filename
        month_year = self.extract_date_from_filename(pdf_path.name)
        
        # Extract text and tables
        text_content = self.extract_text_from_pdf(pdf_path)
        tables = self.extract_tables_from_pdf(pdf_path)
        
        # Process tables into structured expense data
        expenses = self.process_tables_to_expenses(tables, pdf_path.stem, month_year)
        
        result = {
            'document': pdf_path.name,
            'month_year': month_year,
            'text_content': text_content,
            'expenses': expenses,
            'total_expenses': len(expenses),
            'total_amount': sum(exp['amount'] for exp in expenses),
            'processed_at': datetime.now().isoformat()
        }
        
        return result
    
    def process_all_pdfs(self) -> Dict[str, Any]:
        """Process all PDFs in the folder."""
        if not self.pdf_folder.exists():
            raise FileNotFoundError(f"PDF folder {self.pdf_folder} does not exist")
        
        pdf_files = list(self.pdf_folder.glob("*.pdf"))
        if not pdf_files:
            print("No PDF files found in the folder")
            return {}
        
        all_results = {}
        all_expenses = []
        
        for pdf_file in pdf_files:
            result = self.process_single_pdf(pdf_file)
            all_results[pdf_file.stem] = result
            all_expenses.extend(result['expenses'])
        
        # Create summary
        summary = {
            'total_documents': len(pdf_files),
            'total_expenses': len(all_expenses),
            'total_amount': sum(exp['amount'] for exp in all_expenses),
            'date_range': {
                'earliest': min((exp['month_year'] for exp in all_expenses), default='unknown'),
                'latest': max((exp['month_year'] for exp in all_expenses), default='unknown')
            },
            'categories': {}
        }
        
        # Category breakdown
        for expense in all_expenses:
            category = expense['category']
            if category not in summary['categories']:
                summary['categories'][category] = {'count': 0, 'total': 0.0}
            summary['categories'][category]['count'] += 1
            summary['categories'][category]['total'] += expense['amount']
        
        # Save processed data
        output_file = self.output_folder / "processed_expenses.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': summary,
                'documents': all_results,
                'all_expenses': all_expenses
            }, f, ensure_ascii=False, indent=2)
        
        # Save as CSV for easy inspection
        if all_expenses:
            df = pd.DataFrame(all_expenses)
            csv_file = self.output_folder / "expenses.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8')
        
        print(f"Processed {len(pdf_files)} documents")
        print(f"Extracted {len(all_expenses)} expense records")
        print(f"Total amount: R$ {summary['total_amount']:,.2f}")
        print(f"Results saved to {output_file}")
        
        return {
            'summary': summary,
            'documents': all_results,
            'all_expenses': all_expenses
        }

def main():
    """Main function to run the PDF processor."""
    processor = TrialBalanceProcessor()
    results = processor.process_all_pdfs()
    return results

if __name__ == "__main__":
    main()