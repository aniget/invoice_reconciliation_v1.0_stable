# Reconciliation Project - Refactored Architecture

## Overview

This document explains the refactored architecture of the invoice reconciliation system, which follows clean architecture principles with clear separation of concerns.

## Architecture Principles

### 1. Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Entry Points                          │
│  (CLI, API, Web Interface - orchestration only)         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Presentation Layer                          │
│  (Excel formatting, styling - NO business logic)        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│             Application Layer                            │
│  (Use cases, data transformation for presentation)      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│               Domain Layer                               │
│  (Business logic, rules, entities - core of system)     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Adapters Layer                              │
│  (Convert external data ↔ domain models)                │
└─────────────────────────────────────────────────────────┘
```

### 2. Dependency Rule

**Inner layers never depend on outer layers.**

- Domain layer has NO dependencies
- Application layer depends only on Domain
- Presentation depends on Application (through data contracts)
- Adapters convert between external and Domain

### 3. Single Responsibility

Each module has ONE clear purpose:

| Module | Responsibility | Does NOT Do |
|--------|---------------|-------------|
| `domain/models.py` | Define business entities | I/O, formatting, validation logic |
| `domain/rules.py` | Business rules (normalizing, matching, validating) | Data conversion, presentation |
| `domain/service.py` | Orchestrate business logic | I/O, formatting, external dependencies |
| `adapters/json_adapter.py` | Convert JSON ↔ Domain models | Business logic, presentation |
| `application/report_generator.py` | Transform domain → presentation data | Business decisions, Excel formatting |
| `presentation/excel_presenter.py` | Excel styling and formatting | Business logic, calculations |

## Project Structure

```
reconciliation_project/
│
├── domain/                          # Business Logic (Core)
│   ├── __init__.py
│   ├── models.py                    # Entities: Invoice, InvoiceMatch, etc.
│   ├── rules.py                     # Business Rules: validators, matchers
│   └── service.py                   # ReconciliationService (orchestrates rules)
│
├── adapters/                        # Data Conversion
│   ├── __init__.py
│   └── json_adapter.py              # JSON ↔ Domain models
│
├── application/                     # Use Cases
│   ├── __init__.py
│   └── report_generator.py          # Transform domain → presentation
│
├── presentation/                    # UI/Formatting
│   ├── __init__.py
│   └── excel_presenter.py           # Excel generation (styling only)
│
├── pdf_evd_comparator.py           # Facade (backward compatibility)
└── reconciliation_report.py        # Main entry point (orchestration)
```

## Layer Details

### Domain Layer (Core Business Logic)

**Location:** `domain/`

**Purpose:** Contains ALL business logic. No dependencies on external systems.

#### `domain/models.py`

Business entities with behavior:

```python
@dataclass
class Invoice:
    """Represents an invoice (from EVD or PDF)."""
    invoice_number: str
    vendor_normalized: str
    total_amount_eur: Decimal
    # ... more fields
    
    # Uses Decimal for monetary precision
    # Source-agnostic (works for EVD or PDF)

@dataclass  
class InvoiceMatch:
    """Represents a matched pair of invoices."""
    evd_invoice: Invoice
    pdf_invoice: Optional[Invoice]
    confidence: float
    discrepancies: List[Discrepancy]
    
    @property
    def is_perfect_match(self) -> bool:
        return len(self.discrepancies) == 0

@dataclass
class ReconciliationResult:
    """Complete reconciliation results."""
    matches: List[InvoiceMatch]
    mismatches: List[InvoiceMatch]
    missing_in_pdf: List[Invoice]
    missing_in_evd: List[Invoice]
    
    @property
    def match_rate(self) -> float:
        # Business calculation
```

#### `domain/rules.py`

Pure business rules - no I/O, no formatting:

```python
class InvoiceNormalizer:
    """Normalize invoice data for matching."""
    
    @staticmethod
    def normalize_invoice_number(invoice_num: str) -> str:
        # Remove prefixes, special chars
        # "INV-12345" → "12345"

class AmountValidator:
    """Validate and compare amounts."""
    
    def amounts_consistent(self, evd_amt, pdf_amt) -> bool:
        # Handle expense/credit conventions
        # Sign flipped? Absolute value match?
        
    def calculate_difference(self, evd_amt, pdf_amt) -> Decimal:
        # Returns 0 if consistent under any convention
        # This solves the TODO from original code!

class VendorMatcher:
    """Match vendors using fuzzy logic."""
    
    def calculate_similarity(self, v1, v2) -> float:
        # Jaccard similarity, substring matching
        # Returns 0.0 to 1.0

class ConfidenceCalculator:
    """Calculate match confidence scores."""
    
    def calculate_match_confidence(...) -> Tuple[float, bool]:
        # Weights: invoice# (50), amount (30), vendor (20)
        # Returns (score, is_valid_match)
```

#### `domain/service.py`

Orchestrates domain logic:

```python
class ReconciliationService:
    """Core reconciliation business logic."""
    
    def __init__(self, amount_tolerance: Decimal):
        self.normalizer = InvoiceNormalizer()
        self.amount_validator = AmountValidator(tolerance)
        self.vendor_matcher = VendorMatcher()
        self.confidence_calc = ConfidenceCalculator()
    
    def reconcile(
        self,
        evd_invoices: List[Invoice],
        pdf_invoices: List[Invoice],
        pdf_by_vendor: Dict[str, List[Invoice]]
    ) -> ReconciliationResult:
        # 1. Match each EVD invoice
        # 2. Find discrepancies
        # 3. Identify unmatched invoices
        # 4. Return result
        
        # ALL BUSINESS LOGIC HERE
        # No I/O, no formatting
```

**Key Point:** Domain layer can be tested in isolation. No dependencies!

### Adapters Layer (Data Conversion)

**Location:** `adapters/`

**Purpose:** Convert between external formats (JSON) and domain models.

```python
class JSONToInvoiceAdapter:
    """Converts JSON → Domain models."""
    
    @staticmethod
    def from_evd_json(evd_data: dict) -> Invoice:
        # Extract fields from EVD JSON structure
        # Convert to Invoice domain object
        # Handle missing fields gracefully
    
    @staticmethod
    def from_pdf_json(pdf_data: dict) -> Invoice:
        # Extract fields from PDF JSON structure
        # Different field names than EVD!
        
    @staticmethod
    def from_json_dataset(data: dict, source_type: str) -> List[Invoice]:
        # Convert complete dataset
```

**Why separate?**
- Domain doesn't know about JSON
- Easy to add XML, CSV, or database adapters later
- JSON structure can change without affecting domain

### Application Layer (Use Cases)

**Location:** `application/`

**Purpose:** Implement use cases, prepare data for presentation.

```python
class ReportDataGenerator:
    """Transforms domain results → presentation-ready data."""
    
    def generate_report_data(
        self,
        result: ReconciliationResult,
        evd_metadata: Dict,
        pdf_metadata: Dict
    ) -> Dict[str, Any]:
        return {
            'summary': self._generate_summary_data(...),
            'matches': self._generate_matches_data(...),
            'mismatches': self._generate_mismatches_data(...),
            # ... etc
        }
    
    def _generate_summary_data(self, result) -> Dict:
        # Calculate display percentages
        # Format status text
        # Determine colors based on match rate
        # Returns: data ready for Excel
    
    def _generate_matches_data(self, matches) -> List[Dict]:
        # Convert InvoiceMatch objects to row dictionaries
        # Add amount notes (sign convention explanations)
        # Format for display
```

**This is where the TODO was fixed:**

```python
def _create_comparison_row(self, ...) -> Dict:
    evd_amt = float(evd.total_amount_eur) if evd else None
    pdf_amt = float(pdf.total_amount_eur) if pdf else None
    
    # Fixed logic for difference calculation
    difference = None
    if evd_amt is not None and pdf_amt is not None:
        # If amounts are equal under expense/credit convention
        if abs(evd_amt + pdf_amt) < 0.01:
            difference = 0.0  # Consistent under sign flip
        else:
            difference = abs(evd_amt - pdf_amt)  # Real difference
```

### Presentation Layer (Excel Formatting)

**Location:** `presentation/`

**Purpose:** Pure visual presentation. NO business logic.

```python
class ExcelStyles:
    """Centralized styling definitions."""
    COLOR_MATCH = "C6EFCE"
    COLOR_MISMATCH = "FFC7CE"
    FONT_HEADER = Font(color="FFFFFF", bold=True)
    # ... all visual constants

class ExcelWorkbookBuilder:
    """Fluent API for building workbooks."""
    
    def create_sheet(self, title) -> SheetBuilder:
        # Returns builder for method chaining
    
class SheetBuilder:
    """Fluent API for building sheets."""
    
    def set_title(...) -> 'SheetBuilder':
        # Method chaining
    
    def set_header_row(...) -> 'SheetBuilder':
        # Method chaining
    
    def set_data_row(...) -> 'SheetBuilder':
        # Method chaining

class ReconciliationExcelPresenter:
    """Presents data in Excel."""
    
    def create_workbook(self, report_data: Dict, output: Path):
        # Receives PRE-FORMATTED data
        # Only handles Excel API calls
        # NO calculations, NO business decisions
```

**Key Point:** Presenter receives data already formatted for display. It just puts it into Excel cells with styling.

## Data Flow

### Generating a Report

```
1. User calls: reconciliation_report.py
   ↓
2. Load JSON files
   ↓
3. Adapters: JSON → Domain Models (Invoice objects)
   ↓
4. Domain Service: Reconcile invoices
   ├─ Apply business rules
   ├─ Match invoices
   ├─ Find discrepancies
   └─ Return: ReconciliationResult
   ↓
5. Application: Transform for presentation
   ├─ Calculate display percentages
   ├─ Format amounts for display
   ├─ Generate status texts
   └─ Return: presentation-ready Dict
   ↓
6. Presentation: Create Excel
   ├─ Apply styles
   ├─ Format cells
   └─ Save workbook
   ↓
7. Done!
```

## Benefits of This Architecture

### 1. Testability

Each layer can be tested independently:

```python
# Test domain logic (no I/O needed)
def test_amount_consistency():
    validator = AmountValidator(tolerance=Decimal('0.01'))
    assert validator.amounts_consistent(100.0, -100.0)  # Sign flip
    assert validator.amounts_consistent(100.0, 100.0)   # Exact match
    assert not validator.amounts_consistent(100.0, 200.0)  # Different

# Test service (no I/O needed)
def test_reconciliation():
    service = ReconciliationService()
    evd = [Invoice(...)]
    pdf = [Invoice(...)]
    result = service.reconcile(evd, pdf)
    assert result.match_rate > 90

# Test presentation (no business logic needed)
def test_excel_styling():
    presenter = ReconciliationExcelPresenter()
    # Test that colors are applied correctly
```

### 2. Maintainability

- **Change business rules?** Edit `domain/rules.py`
- **Change Excel colors?** Edit `presentation/excel_presenter.py`
- **Add database storage?** Create `adapters/database_adapter.py`
- **Change JSON format?** Edit `adapters/json_adapter.py`

Changes are localized!

### 3. Reusability

Domain logic can be reused:

```python
# Use in web API
from reconciliation_project.domain import ReconciliationService

@app.post("/api/reconcile")
def reconcile_api(evd_data, pdf_data):
    service = ReconciliationService()
    result = service.reconcile(...)
    return result.to_summary_dict()

# Use in batch processing
from reconciliation_project.domain import ReconciliationService

def batch_reconcile(folder):
    service = ReconciliationService()
    for evd_file, pdf_file in get_file_pairs(folder):
        result = service.reconcile(...)
        # Different output format!
```

### 4. Clear Boundaries

- Developers know exactly where to put new code
- No "God classes" with mixed responsibilities
- Easy to onboard new team members

### 5. Evolution

Easy to add new features:

**Add PDF output:**
```python
# Create presentation/pdf_presenter.py
class ReconciliationPDFPresenter:
    def create_pdf(self, report_data: Dict, output: Path):
        # Reuse same report_data from ReportDataGenerator!
```

**Add database storage:**
```python
# Create adapters/database_adapter.py
class DatabaseAdapter:
    def save_result(self, result: ReconciliationResult):
        # Convert domain models to database records
```

**Add new matching algorithm:**
```python
# Edit domain/rules.py
class MLVendorMatcher(VendorMatcher):
    def calculate_similarity(self, v1, v2) -> float:
        # Use ML model instead of Jaccard
```

## Migration Guide

### For Existing Code Using Old API

The old API still works through compatibility facades:

```python
# Old code (still works)
from reconciliation_project.pdf_evd_comparator import EVDPDFComparator

comparator = EVDPDFComparator()
results = comparator.compare_datasets(evd_data, pdf_data)
# Returns same JSON structure as before

# New code (recommended)
from reconciliation_project.domain import ReconciliationService
from reconciliation_project.adapters import JSONToInvoiceAdapter

service = ReconciliationService()
evd_invoices = JSONToInvoiceAdapter.from_json_dataset(evd_data, 'evd')
pdf_invoices = JSONToInvoiceAdapter.from_json_dataset(pdf_data, 'pdf')
result = service.reconcile(evd_invoices, pdf_invoices)
```

### Deprecated Methods

These methods still work but delegate to new architecture:

```python
class EVDPDFComparator:
    def normalize_invoice_number(self, num):
        # [DEPRECATED] Use domain.rules.InvoiceNormalizer
        return self.service.normalizer.normalize_invoice_number(num)
```

## Common Patterns

### Adding a New Business Rule

1. Define rule in `domain/rules.py`
2. Use rule in `domain/service.py`
3. Add tests for rule
4. Done! (No changes to presentation needed)

### Changing Display Format

1. Edit `application/report_generator.py` (data formatting)
2. Edit `presentation/excel_presenter.py` (styling)
3. Done! (No changes to business logic needed)

### Adding New Data Source

1. Create new adapter in `adapters/`
2. Implement conversion to `Invoice` domain model
3. Done! (Everything else works automatically)

## Conclusion

This refactored architecture:

✅ **Separates concerns** - Business logic ≠ Presentation  
✅ **Follows SOLID** - Single responsibility, dependency inversion  
✅ **Testable** - Each layer independently testable  
✅ **Maintainable** - Changes are localized  
✅ **Extensible** - Easy to add features  
✅ **Backward compatible** - Old API still works  

The TODO on line 533 was fixed by properly handling sign conventions in `application/report_generator.py`.

All errors were addressed through proper structure, not by hiding them.
