import os
import json
import pandas as pd
import pdfplumber
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import pytesseract
from PIL import Image
import pdf2image
import cv2
import numpy as np
import gc
import signal
import sys

class TrialBalanceProcessor:
    def __init__(self, pdf_folder: str = "pdfs", output_folder: str = "data/processed"):
        self.pdf_folder = Path(pdf_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print(f"\nReceived signal {signum}. Cleaning up...")
        gc.collect()
        sys.exit(0)
        
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
    
    def convert_pdf_to_images(self, pdf_path: Path, dpi: int = 150) -> List[Image.Image]:
        """Convert PDF pages to images for OCR processing."""
        try:
            images = pdf2image.convert_from_path(pdf_path, dpi=dpi)
            return images
        except Exception as e:
            print(f"Error converting PDF to images {pdf_path}: {e}")
            return []
    
    def extract_red_numbers(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Extract red numbers from image using color detection and OCR."""
        try:
            # Convert PIL image to OpenCV format
            img_array = np.array(image)
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            
            # Define range for red color in HSV
            # Red can be in two ranges due to HSV wraparound
            lower_red1 = np.array([0, 50, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 50, 50])
            upper_red2 = np.array([180, 255, 255])
            
            # Create masks for red color
            mask1 = cv2.inRange(img_hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(img_hsv, lower_red2, upper_red2)
            red_mask = mask1 + mask2
            
            # Find contours of red regions
            contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            red_numbers = []
            for contour in contours:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size (adjust thresholds as needed)
                if w > 5 and h > 5 and w < 300 and h < 150:
                    # Extract region of interest
                    roi = img_array[y:y+h, x:x+w]
                    roi_pil = Image.fromarray(roi)
                    
                    # Apply OCR to extracted region
                    text = pytesseract.image_to_string(roi_pil, config='--psm 8 -c tessedit_char_whitelist=0123456789')
                    text = text.strip()
                    
                    if text and text.isdigit():
                        red_numbers.append({
                            'number': text,
                            'position': {'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)},
                            'confidence': 'extracted'
                        })
            
            return red_numbers
        except Exception as e:
            print(f"Error extracting red numbers: {e}")
            return []
    
    def extract_first_page_metadata(self, image: Image.Image) -> Dict[str, Any]:
        """Extract metadata from first page using OCR."""
        try:
            # Apply OCR to entire first page (try Portuguese first, fallback to English)
            try:
                text = pytesseract.image_to_string(image, lang='por')
            except:
                text = pytesseract.image_to_string(image, lang='eng')
            
            metadata = {
                'full_text': text,
                'invoice_details': {},
                'dates': [],
                'amounts': [],
                'vendor_info': {}
            }
            
            # Extract dates (various Brazilian formats)
            date_patterns = [
                r'\d{2}/\d{2}/\d{4}',
                r'\d{2}-\d{2}-\d{4}',
                r'\d{2}\.\d{2}\.\d{4}'
            ]
            for pattern in date_patterns:
                dates = re.findall(pattern, text)
                metadata['dates'].extend(dates)
            
            # Extract amounts (Brazilian currency format)
            amount_pattern = r'R\$\s*[\d.,]+(?:,\d{2})?'
            amounts = re.findall(amount_pattern, text)
            metadata['amounts'] = amounts
            
            # Look for common invoice fields
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if any(keyword in line.lower() for keyword in ['cnpj', 'cpf']):
                    metadata['vendor_info']['tax_id'] = line
                elif any(keyword in line.lower() for keyword in ['fornecedor', 'empresa', 'razão social']):
                    metadata['vendor_info']['name'] = line
                elif any(keyword in line.lower() for keyword in ['nota fiscal', 'nf', 'número']):
                    metadata['invoice_details']['number'] = line
            
            return metadata
        except Exception as e:
            print(f"Error extracting first page metadata: {e}")
            return {'error': str(e)}
    
    def extract_images_from_pdf_with_ocr(self, pdf_path: Path, max_pages: int = 3) -> Dict[str, Any]:
        """Extract and process images from PDF using OCR."""
        try:
            # Get total page count efficiently
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
            
            pages_to_process = min(total_pages, max_pages)
            print(f"Processing {pages_to_process} of {total_pages} pages to conserve memory")
            
            result = {
                'total_pages': total_pages,
                'processed_pages': pages_to_process,
                'first_page_metadata': {},
                'red_numbers_by_page': [],
                'ocr_text_by_page': []
            }
            
            for page_num in range(pages_to_process):
                print(f"Processing page {page_num + 1}...")
                try:
                    # Convert one page at a time with lower DPI
                    images = pdf2image.convert_from_path(
                        pdf_path, 
                        first_page=page_num + 1, 
                        last_page=page_num + 1,
                        dpi=100,  # Further reduced DPI
                        fmt='JPEG',  # Use JPEG for less memory
                        jpegopt={'quality': 85}  # Compress JPEG
                    )
                    if not images:
                        continue
                    
                    image = images[0]
                    
                    # Only process first page for metadata and red numbers to save time/memory
                    if page_num == 0:
                        # Extract detailed metadata from first page
                        result['first_page_metadata'] = self.extract_first_page_metadata(image)
                        
                        # Extract red numbers from first page
                        red_numbers = self.extract_red_numbers(image)
                        result['red_numbers_by_page'].append({
                            'page': page_num + 1,
                            'red_numbers': red_numbers
                        })
                    
                    # Extract OCR text (limited to prevent memory issues)
                    try:
                        page_text = pytesseract.image_to_string(image, lang='por', config='--psm 6')[:5000]  # Limit text length
                        result['ocr_text_by_page'].append({
                            'page': page_num + 1,
                            'text': page_text
                        })
                    except Exception as e:
                        print(f"Error extracting text from page {page_num + 1}: {e}")
                    
                    # Explicitly clean up
                    image.close() if hasattr(image, 'close') else None
                    del image, images
                    gc.collect()
                    
                except Exception as e:
                    print(f"Error processing page {page_num + 1}: {e}")
                    gc.collect()
                    continue
            
            return result
            
        except Exception as e:
            print(f"Error in extract_images_from_pdf_with_ocr: {e}")
            gc.collect()
            return {'error': str(e)}
    
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
        
        # Define category mappings for Brazilian expenses
        categories = {
            'utilities': {
                'power_supply': ['cemig', 'energia', 'eletric', 'light', 'copel', 'eletropaulo', 'enel'],
                'water': ['copasa', 'agua', 'water', 'saneamento', 'sabesp', 'cedae'],
                'gas': ['gas', 'ultragaz', 'liquigás', 'comgas'],
                'telecom': ['telefonia', 'internet', 'vivo', 'tim', 'oi', 'claro', 'algar', 'fibra']
            },
            'maintenance': {
                'elevator': ['elevador', 'elevator', 'otis', 'schindler', 'atlas'],
                'cleaning': ['limpeza', 'cleaning', 'faxina', 'banho quimico', 'material limpeza'],
                'gardening': ['jardim', 'garden', 'paisagismo', 'jardinagem'],
                'repairs': ['reparo', 'repair', 'conserto', 'manutencao', 'manut', 'pintura'],
                'vehicles': ['combustivel', 'locacao veic', 'veiculo', 'moto', 'gasolina']
            },
            'services': {
                'security': ['seguranca', 'seg', 'portaria', 'vigilancia', 'patrulhamento'],
                'administration': ['administracao', 'admin', 'gestao', 'pacto administradora'],
                'legal': ['juridico', 'legal', 'advogado', 'honorarios', 'custas'],
                'accounting': ['contabil', 'accounting', 'contador', 'honor contabeis'],
                'transport': ['transporte', 'micro onibus', 'vale transporte', 'complemento vt']
            },
            'personnel': {
                'salaries': ['salarios', 'salary', 'ferias', '13 sal', 'rescisao'],
                'benefits': ['plano saude', 'cartao aliment', 'cesta basica', 'vale'],
                'social_charges': ['fgts', 'encargos', 'tributos federais', 'inss']
            },
            'supplies': {
                'office': ['escritorio', 'office', 'papelaria', 'material escritorio'],
                'cleaning_supplies': ['material limpeza', 'detergente', 'sabao', 'saco lixo'],
                'maintenance_supplies': ['ferramenta', 'material construcao', 'material eletrico', 'material hidraulico']
            },
            'taxes_and_fees': {
                'municipal_taxes': ['iss', 'iptu', 'taxa municipal'],
                'federal_taxes': ['tributos federais', 'cofins', 'pis'],
                'fees': ['taxa', 'licenca', 'alvara', 'renovacao']
            }
        }
        
        for main_category, subcategories in categories.items():
            for subcategory, keywords in subcategories.items():
                if any(keyword in description_lower for keyword in keywords):
                    return {'category': main_category, 'subcategory': subcategory}
        
        return {'category': 'other', 'subcategory': 'miscellaneous'}
    
    def extract_date_from_filename(self, filename: str) -> str:
        """Extract date from filename patterns like JANUARY_2025_PACTO_BALANCETE_0913_2501.pdf."""
        # First try the new format: JANUARY_2025_PACTO_BALANCETE_0913_2501.pdf
        month_names = {
            'JANUARY': '01', 'FEBRUARY': '02', 'MARCH': '03', 'APRIL': '04',
            'MAY': '05', 'JUNE': '06', 'JULY': '07', 'AUGUST': '08',
            'SEPTEMBER': '09', 'OCTOBER': '10', 'NOVEMBER': '11', 'DECEMBER': '12'
        }
        
        # Try month name + year format
        for month_name, month_num in month_names.items():
            if month_name in filename.upper():
                year_match = re.search(r'(\d{4})', filename)
                if year_match:
                    year = year_match.group(1)
                    return f"{year}-{month_num}"
        
        # Fallback to old format: PACTO_BALANCETE_0913_YYMM.pdf
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
                                 month_year: str,
                                 image_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
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
                    'currency': 'BRL',
                    'image_metadata': image_metadata or {}
                }
                
                expenses.append(expense)
        
        return expenses
    
    def process_text_to_expenses(self, text_content: str, 
                               document_name: str, 
                               month_year: str,
                               image_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Process text content to extract Brazilian trial balance expenses."""
        expenses = []
        
        if not text_content:
            return expenses
        
        lines = text_content.split('\n')
        
        # Process "OUTRAS DESPESAS" (Other Expenses) section
        expenses.extend(self._extract_outras_despesas(lines, document_name, month_year, image_metadata))
        
        # Process "EXTRATO DE CONTA" (Account Statement) section  
        expenses.extend(self._extract_extrato_conta(lines, document_name, month_year, image_metadata))
        
        # Process main balance sheet items (Credits/Debits)
        expenses.extend(self._extract_balance_items(lines, document_name, month_year, image_metadata))
        
        return expenses
    
    def _extract_outras_despesas(self, lines: List[str], document_name: str, month_year: str, image_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract expenses from OUTRAS DESPESAS section."""
        expenses = []
        in_outras_section = False
        expense_id = 1
        
        for line in lines:
            line = line.strip()
            
            # Detect start of OUTRAS DESPESAS section
            if 'OUTRAS DESPESAS' in line.upper():
                in_outras_section = True
                continue
            
            # Detect end of section
            if in_outras_section and ('TOTAL OUTRAS DESPESAS' in line.upper() or '=' in line):
                break
                
            # Parse expense lines in format: "1 - MANUT MOTOS SEG 950,00"
            if in_outras_section:
                match = re.match(r'^\s*(\d+)\s*-\s*(.+?)\s+([\d.,]+)\s*$', line)
                if match:
                    seq_num, description, amount_str = match.groups()
                    amount = self.parse_amount(amount_str)
                    
                    if amount > 0:
                        category_info = self.categorize_expense(description)
                        
                        expense = {
                            'id': f"{document_name}_outras_{expense_id}",
                            'description': description.strip(),
                            'amount': amount,
                            'vendor': self._extract_vendor_from_description(description),
                            'category': category_info['category'],
                            'subcategory': category_info['subcategory'],
                            'month_year': month_year,
                            'document': document_name,
                            'source_section': 'outras_despesas',
                            'currency': 'BRL',
                            'sequence_number': int(seq_num),
                            'image_metadata': image_metadata or {}
                        }
                        expenses.append(expense)
                        expense_id += 1
        
        return expenses
    
    def _extract_extrato_conta(self, lines: List[str], document_name: str, month_year: str, image_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract expenses from EXTRATO DE CONTA section."""
        expenses = []
        in_extrato_section = False
        expense_id = 1
        
        for line in lines:
            line = line.strip()
            
            # Detect start of EXTRATO section
            if 'EXTRATO DE CONTA' in line.upper():
                in_extrato_section = True
                continue
            
            # Skip header lines
            if in_extrato_section and ('Data Lanc.' in line or '------' in line or 'SALDO MES ANTERIOR' in line):
                continue
                
            # Detect end of section
            if in_extrato_section and ('Continua' in line or line == ''):
                continue
                
            # Parse transaction lines: "02/01/25 17814990 DESPESAS POSTAIS \ MALOTE 133,81 75.092,54"
            if in_extrato_section:
                # Pattern: date, doc_num, description, debit, credit, balance
                match = re.match(r'^(\d{2}/\d{2}/\d{2})\s+(\d+)\s+(.+?)\s+([\d.,]+)(?:\s+([\d.,]+))?\s+([\d.,-]+)\s*$', line)
                if match:
                    date, doc_num, description, amount1, amount2, balance = match.groups()
                    
                    # Use the first amount as the expense amount (usually debit)
                    amount = self.parse_amount(amount1)
                    
                    if amount > 0:
                        # Parse date to full date format
                        try:
                            day, month, year = date.split('/')
                            full_year = 2000 + int(year) if int(year) < 50 else 1900 + int(year)
                            expense_date = f"{full_year}-{month}-{day}"
                        except:
                            expense_date = f"{month_year}-01"
                        
                        category_info = self.categorize_expense(description)
                        
                        expense = {
                            'id': f"{document_name}_extrato_{expense_id}",
                            'description': description.strip(),
                            'amount': amount,
                            'vendor': self._extract_vendor_from_description(description),
                            'category': category_info['category'],
                            'subcategory': category_info['subcategory'],
                            'month_year': month_year,
                            'date': expense_date,
                            'document_number': doc_num,
                            'document': document_name,
                            'source_section': 'extrato_conta',
                            'currency': 'BRL',
                            'image_metadata': image_metadata or {}
                        }
                        expenses.append(expense)
                        expense_id += 1
        
        return expenses
    
    def _extract_balance_items(self, lines: List[str], document_name: str, month_year: str, image_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract expenses from main balance sheet (CREDITOS/DEBITOS) section."""
        expenses = []
        in_balance_section = False
        expense_id = 1
        
        for line in lines:
            line = line.strip()
            
            # Detect balance section (look for numbered items with amounts)
            if re.match(r'^\d+\s*-\s*.+\s+[\d.,]+$', line) and not any(section in line.upper() for section in ['OUTRAS DESPESAS', 'EXTRATO']):
                in_balance_section = True
            
            # Parse balance items: "1 - SALARIOS 159.531,22"
            if in_balance_section:
                match = re.match(r'^(\d+)\s*-\s*(.+?)\s+([\d.,]+)\s*$', line)
                if match:
                    seq_num, description, amount_str = match.groups()
                    amount = self.parse_amount(amount_str)
                    
                    if amount > 0:
                        category_info = self.categorize_expense(description)
                        
                        expense = {
                            'id': f"{document_name}_balance_{expense_id}",
                            'description': description.strip(),
                            'amount': amount,
                            'vendor': self._extract_vendor_from_description(description),
                            'category': category_info['category'],
                            'subcategory': category_info['subcategory'],
                            'month_year': month_year,
                            'document': document_name,
                            'source_section': 'balance_sheet',
                            'currency': 'BRL',
                            'sequence_number': int(seq_num),
                            'image_metadata': image_metadata or {}
                        }
                        expenses.append(expense)
                        expense_id += 1
            
            # Stop processing if we hit totals
            if 'TOTAL' in line.upper() and '==' in line:
                in_balance_section = False
        
        return expenses
    
    def _extract_vendor_from_description(self, description: str) -> str:
        """Extract vendor name from expense description."""
        description = description.strip()
        
        # Common vendor patterns in Brazilian expenses
        vendor_patterns = [
            r'(CEMIG|COPASA|SABESP|LIGHT)',  # Utilities
            r'(TIM|VIVO|OI|CLARO)',          # Telecom
            r'(ULTRA|LIQUI)GAZ',             # Gas companies
            r'paid to (.+)',                  # "paid to" pattern
            r'PAGO A (.+)',                   # "pago a" pattern
        ]
        
        for pattern in vendor_patterns:
            match = re.search(pattern, description.upper())
            if match:
                return match.group(1).strip()
        
        # Try to extract capitalized words that might be vendor names
        words = description.split()
        capitalized_words = [word for word in words if word.isupper() and len(word) > 3]
        if capitalized_words:
            return capitalized_words[0]
        
        return ""
    
    def process_single_pdf(self, pdf_path: Path, skip_ocr: bool = True) -> Dict[str, Any]:
        """Process a single PDF file and extract expense data."""
        print(f"Processing {pdf_path.name}...")
        
        # Extract month/year from filename
        month_year = self.extract_date_from_filename(pdf_path.name)
        
        # Check PDF properties first
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"PDF has {total_pages} pages")
            
            # For large PDFs, process only first few pages for text/tables
            max_pages_for_text = min(10, total_pages)
            
            # Extract text and tables from limited pages
            text_content = ""
            tables = []
            
            for page_num in range(max_pages_for_text):
                try:
                    page = pdf.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
                    
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
                        
                except Exception as e:
                    print(f"Error processing page {page_num + 1}: {e}")
                    continue
        
        print(f"Extracted text from {max_pages_for_text} pages, found {len(tables)} tables")
        
        # Skip OCR processing for large image-based PDFs
        image_metadata = {}
        if not skip_ocr and total_pages < 50:  # Only do OCR for smaller PDFs
            try:
                print(f"Extracting image metadata from {pdf_path.name}...")
                image_metadata = self.extract_images_from_pdf_with_ocr(pdf_path)
            except Exception as e:
                print(f"OCR processing failed, skipping: {e}")
                image_metadata = {'error': 'OCR processing failed'}
        else:
            reason = "large PDF" if total_pages >= 50 else "OCR disabled"
            print(f"Skipping OCR processing ({reason})")
            image_metadata = {
                'skipped': f'OCR processing skipped for {reason}',
                'total_pages': total_pages,
                'processed_pages': max_pages_for_text
            }
        
        # Process both tables and text into structured expense data
        table_expenses = self.process_tables_to_expenses(tables, pdf_path.stem, month_year, image_metadata)
        text_expenses = self.process_text_to_expenses(text_content, pdf_path.stem, month_year, image_metadata)
        
        # Combine and deduplicate expenses
        expenses = table_expenses + text_expenses
        
        result = {
            'document': pdf_path.name,
            'month_year': month_year,
            'text_content': text_content[:10000],  # Limit text content size
            'image_metadata': image_metadata,
            'expenses': expenses,
            'total_expenses': len(expenses),
            'total_amount': sum(exp['amount'] for exp in expenses),
            'processed_at': datetime.now().isoformat(),
            'pdf_info': {
                'total_pages': total_pages,
                'processed_pages': max_pages_for_text
            }
        }
        
        # Clean up
        gc.collect()
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
            result = self.process_single_pdf(pdf_file, skip_ocr=True)  # Skip OCR by default
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