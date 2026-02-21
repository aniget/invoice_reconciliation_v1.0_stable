# Developer Guide

## Architecture Overview

The system consists of three main components:

```
┌─────────────────────────────────────────────┐
│           User Interface (app.py)            │
│              Gradio Web UI                   │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
┌───▼────────────┐      ┌────────▼─────────┐
│ EVD Extraction │      │ PDF Extraction   │
│   (batch)      │      │  (templates +    │
│                │      │   patterns)      │
└───┬────────────┘      └────────┬─────────┘
    │                             │
    │         ┌───────────────────┘
    │         │
┌───▼─────────▼────┐
│  Reconciliation   │
│   & Reporting     │
└───────────────────┘
```

## Project Structure

```
invoice_reconciliation/
├── app.py                          # Gradio web interface
├── run_reconciliation.py           # CLI workflow
├── requirements.txt                # Python dependencies
│
├── evd_extraction_project/
│   ├── evd_extractor.py           # Single file extraction
│   ├── batch_evd_extractor.py     # Batch processing
│   └── requirements.txt
│
├── pdf_extraction_project/
│   ├── pdf_processor.py           # Main PDF processor
│   ├── extractors/
│   │   ├── vendor_vivacom.py      # Vivacom template
│   │   ├── vendor_yettel.py       # Yettel template
│   │   └── generic_extractor.py   # Pattern-based fallback
│   └── requirements.txt
│
├── reconciliation_project/
│   ├── reconciliation_report.py   # Report generation
│   └── pdf_evd_comparator.py      # Comparison logic
│
└── docs/
    └── OCR_SETUP_GUIDE.md         # OCR setup (optional)
```

## Core Components

### 1. EVD Extraction (`evd_extraction_project/`)

**Purpose:** Extract invoice data from Excel files

**Main Functions:**
```python
# Single file
from evd_extractor import EVDExtractor
extractor = EVDExtractor()
data = extractor.extract_invoice_data("file.xlsx")

# Batch
from batch_evd_extractor import BatchEVDExtractor
extractor = BatchEVDExtractor()
data = extractor.process_folder("input_evd/")
```

**Output Format:**
```json
{
  "metadata": {
    "total_invoices": 42,
    "extraction_date": "2026-01-29T10:30:00"
  },
  "by_vendor": {
    "VIVACOM BULGARIA": {
      "invoice_count": 15,
      "total_amount_eur": 12345.67
    }
  },
  "all_invoices": [
    {
      "invoice_number": "0063266046",
      "vendor": "VIVACOM BULGARIA",
      "total_amount_eur": 903.42,
      ...
    }
  ]
}
```

### 2. PDF Extraction (`pdf_extraction_project/`)

**Purpose:** Extract invoice data from PDF files

**Extraction Chain:**
```python
1. Vendor Detection
   └─> Check for known vendor keywords

2. Template Extraction (if vendor known)
   └─> Use vendor-specific extractor
   └─> Return if confidence > 90%

3. Generic Extraction (fallback)
   └─> Pattern-based extraction
   └─> Return with confidence score
```

**Adding New Vendor Template:**

```python
# 1. Create extractors/vendor_newvendor.py

from typing import Dict

class NewVendorExtractor:
    """Template for New Vendor invoices."""
    
    def extract(self, text: str, pdf_path: str = None) -> Dict:
        """Extract invoice data."""
        
        import re
        data = {}
        
        # Invoice number pattern
        inv_match = re.search(r'Invoice No:\s*(\d+)', text)
        if inv_match:
            data['invoice_number'] = inv_match.group(1)
        
        # Add more patterns...
        
        data['extraction_method'] = 'newvendor_template'
        data['confidence'] = self._calculate_confidence(data)
        
        return data
    
    def _calculate_confidence(self, data):
        score = 0
        if data.get('invoice_number'): score += 30
        if data.get('total_amount'): score += 30
        # ...
        return min(score, 100)

# 2. Register in pdf_processor.py

from extractors.vendor_newvendor import NewVendorExtractor

class PDFInvoiceProcessor:
    def __init__(self):
        self.vendor_extractors = {
            'VIVACOM': VivacomExtractor(),
            'YETTEL': YettelExtractor(),
            'NEWVENDOR': NewVendorExtractor(),  # Add here
        }
```

### 3. Reconciliation (`reconciliation_project/`)

**Purpose:** Match EVD and PDF data, generate report

**Matching Logic:**
```python
def fuzzy_match(invoice1, invoice2):
    # 1. Invoice number similarity
    if similar(invoice1['number'], invoice2['number']) > 0.9:
        # 2. Amount within tolerance
        if abs(invoice1['amount'] - invoice2['amount']) < tolerance:
            # 3. Vendor match
            if invoice1['vendor'] == invoice2['vendor']:
                return 'MATCH'
    return 'NO_MATCH'
```

## Extension Points

### Adding Extraction Features

**1. New Field Extraction:**

```python
# In vendor template or generic extractor:

def extract(self, text: str, pdf_path: str = None) -> Dict:
    # ... existing fields ...
    
    # Add new field
    vat_match = re.search(r'VAT:\s*([\d.]+)', text)
    if vat_match:
        data['vat_number'] = vat_match.group(1)
    
    return data
```

**2. New Validation Rule:**

```python
# In reconciliation_report.py:

def validate_invoice(self, invoice):
    # Existing validations...
    
    # Add new validation
    if invoice.get('vat_number'):
        if not self._is_valid_vat(invoice['vat_number']):
            invoice['warnings'].append('Invalid VAT number')
```

### Adding Report Features

**Custom Report Sheet:**

```python
# In reconciliation_report.py, add new method:

def _create_custom_sheet(self, workbook, data):
    """Create custom analysis sheet."""
    ws = workbook.create_sheet('Custom Analysis')
    
    # Add your custom logic
    ws['A1'] = 'Custom Analysis'
    # ...
    
    return ws

# Call in _generate_report():
self._create_custom_sheet(workbook, comparison_data)
```

## Configuration

### EVD Extraction Config

```python
# evd_extraction_project/config.py

# Create this file for custom settings

EVD_CONFIG = {
    'currency_conversion': {
        'BGN_to_EUR': 0.511292,
    },
    'vendor_normalization': {
        'remove_suffixes': ['ЕАД', 'EAD', 'Ltd'],
    },
    'column_detection': {
        'invoice_number_keywords': ['№', 'No', 'Номер'],
    }
}
```

### PDF Extraction Config

```python
# pdf_extraction_project/config.py

PDF_CONFIG = {
    'confidence_threshold': 70,  # Minimum confidence to accept
    'ocr_enabled': False,         # Enable OCR by default
    'ocr_languages': 'bul+eng',   # OCR languages
}
```

### Reconciliation Config

```python
# reconciliation_project/config.py

RECONCILIATION_CONFIG = {
    'amount_tolerance_percent': 1.0,  # 1% tolerance
    'fuzzy_match_threshold': 0.9,     # 90% similarity
    'report_colors': {
        'match': '90EE90',      # Light green
        'mismatch': 'FFB6C1',   # Light red
        'missing': 'FFE4B5',    # Light yellow
    }
}
```

## Testing

### Unit Tests

```python
# tests/test_evd_extraction.py

import pytest
from evd_extraction_project.evd_extractor import EVDExtractor

def test_invoice_extraction():
    extractor = EVDExtractor()
    data = extractor.extract_invoice_data('test_data/sample.xlsx')
    
    assert data['metadata']['total_invoices'] > 0
    assert 'all_invoices' in data

def test_vendor_normalization():
    extractor = EVDExtractor()
    normalized = extractor._normalize_vendor('VIVACOM ЕАД')
    
    assert normalized == 'VIVACOM BULGARIA'
```

### Integration Tests

```python
# tests/test_integration.py

def test_full_workflow():
    """Test complete EVD + PDF + Reconciliation."""
    
    # 1. Extract EVD
    evd_data = extract_evd('test_data/evd/')
    
    # 2. Extract PDF
    pdf_data = extract_pdf('test_data/pdf/')
    
    # 3. Reconcile
    report = reconcile(evd_data, pdf_data)
    
    assert report.exists()
```

## Debugging

### Enable Detailed Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Now all modules will log details
```

### Common Issues

**Issue: Low extraction confidence**

```python
# Debug extraction:
data = extractor.extract(pdf_path)
print(f"Confidence: {data['confidence']}")
print(f"Method: {data['extraction_method']}")
print(f"Found fields: {data.keys()}")

# Check which fields are missing
required = ['invoice_number', 'total_amount', 'vendor']
missing = [f for f in required if not data.get(f)]
print(f"Missing: {missing}")
```

**Issue: No vendor match**

```python
# Debug vendor detection:
text = extract_text(pdf_path)
print("Text sample:", text[:500])

vendor = detect_vendor(text)
print(f"Detected vendor: {vendor}")

# Check vendor keywords
for keyword in vendor_keywords:
    if keyword in text:
        print(f"Found: {keyword}")
```

## Performance Optimization

### Batch Processing

```python
# Use multiprocessing for large batches:
from multiprocessing import Pool

def process_pdf(pdf_path):
    return extractor.extract(pdf_path)

with Pool(processes=4) as pool:
    results = pool.map(process_pdf, pdf_files)
```

### Caching

```python
# Cache extraction results:
import hashlib
import json

def hash_file(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

cache = {}

def extract_with_cache(pdf_path):
    file_hash = hash_file(pdf_path)
    
    if file_hash in cache:
        return cache[file_hash]
    
    data = extractor.extract(pdf_path)
    cache[file_hash] = data
    
    return data
```

## Deployment

### Local Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/invoice-reconciliation.git
cd invoice-reconciliation

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python app.py
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

EXPOSE 7860

CMD ["python", "app.py"]
```

```bash
# Build and run
docker build -t invoice-reconciliation .
docker run -p 7860:7860 invoice-reconciliation
```

## Contributing

### Code Style

```python
# Follow PEP 8
# Use Black formatter:
black app.py

# Use type hints:
def extract_invoice(pdf_path: str) -> Dict[str, Any]:
    ...

# Document functions:
def reconcile(evd_data: dict, pdf_data: dict) -> str:
    """
    Reconcile EVD and PDF data.
    
    Args:
        evd_data: Extracted EVD invoice data
        pdf_data: Extracted PDF invoice data
        
    Returns:
        Path to generated Excel report
    """
```

### Adding Features

1. Create feature branch: `git checkout -b feature/new-vendor`
2. Implement and test
3. Update documentation
4. Submit pull request

## API Reference

See inline code documentation for detailed API reference.

Key modules:
- `evd_extractor.EVDExtractor`
- `pdf_processor.PDFInvoiceProcessor`
- `reconciliation_report.ReconciliationReportGenerator`

---

For questions, see USER_GUIDE.md or open an issue on GitHub.
