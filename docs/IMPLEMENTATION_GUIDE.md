# Implementation Guide

## How to Integrate the Refactored Code

This guide shows you how to replace the old code with the refactored version.

## Step 1: Backup Current Code

```bash
# Backup your current reconciliation_project
cp -r reconciliation_project reconciliation_project_backup
```

## Step 2: Extract Refactored Code

```bash
# Extract the refactored version
unzip reconciliation_refactored.zip -d reconciliation_project_new

# The structure:
reconciliation_project_new/
├── reconciliation_project/     # New layered structure
│   ├── domain/                 # ← Business logic
│   ├── adapters/               # ← Data conversion
│   ├── application/            # ← Use cases
│   ├── presentation/           # ← Excel formatting
│   ├── pdf_evd_comparator.py  # ← Backward compatible facade
│   └── reconciliation_report.py # ← Main entry point
├── ARCHITECTURE.md             # ← Read this!
└── REFACTORING_SUMMARY.md      # ← Changes explained
```

## Step 3: Verify Dependencies

```bash
# Check requirements (should already be installed)
pip list | grep -E "openpyxl|pathlib"

# If missing:
pip install openpyxl
```

## Step 4: Test Compatibility

### Option A: Drop-in Replacement (Safest)

```bash
# Replace old files with new ones
mv reconciliation_project reconciliation_project_old
mv reconciliation_project_new/reconciliation_project .

# Run your existing scripts - they should still work!
python reconciliation_project/reconciliation_report.py evd.json pdf.json output.xlsx
```

### Option B: Gradual Migration

```bash
# Keep both versions temporarily
mv reconciliation_project reconciliation_project_old
mv reconciliation_project_new/reconciliation_project reconciliation_project_refactored

# Update imports in your code:
# OLD: from reconciliation_project.pdf_evd_comparator import EVDPDFComparator
# NEW: from reconciliation_project_refactored.pdf_evd_comparator import EVDPDFComparator
```

## Step 5: Update Calling Code (Recommended)

### Old Way (Still Works)

```python
# This continues to work - backward compatible
from reconciliation_project.pdf_evd_comparator import EVDPDFComparator

comparator = EVDPDFComparator()
results = comparator.compare_datasets(evd_data, pdf_data)

# Old report generation
from reconciliation_project.reconciliation_report import ReconciliationReportGenerator

generator = ReconciliationReportGenerator()
generator.generate_report(evd_data, pdf_data, comparison_results, output_path)
```

### New Way (Recommended)

```python
# New simplified API - comparison_results not needed!
from reconciliation_project.reconciliation_report import ReconciliationReportGenerator

generator = ReconciliationReportGenerator()
generator.generate_report(evd_data, pdf_data, output_path)
# That's it! Simpler!
```

## Step 6: Verify Everything Works

### Test 1: CLI

```bash
# Should work exactly as before
python reconciliation_project/reconciliation_report.py \
    path/to/evd.json \
    path/to/pdf.json \
    path/to/output.xlsx

# Check the Excel file - should be identical to before
```

### Test 2: Programmatic

```python
import json
from pathlib import Path
from reconciliation_project.reconciliation_report import ReconciliationReportGenerator

# Load data
with open('evd.json') as f:
    evd_data = json.load(f)

with open('pdf.json') as f:
    pdf_data = json.load(f)

# Generate report
generator = ReconciliationReportGenerator()
generator.generate_report(evd_data, pdf_data, Path('output.xlsx'))

print("✓ Report generated successfully!")
```

### Test 3: Comparison API

```python
from reconciliation_project.pdf_evd_comparator import EVDPDFComparator

comparator = EVDPDFComparator()
results = comparator.compare_datasets(evd_data, pdf_data)

# Same output format as before
print(f"Matches: {results['summary']['matches']}")
print(f"Match rate: {results['summary'].get('match_rate', 'N/A')}%")
```

## Common Migration Scenarios

### Scenario 1: Using in Web App

```python
# Before (still works)
from reconciliation_project.pdf_evd_comparator import EVDPDFComparator

@app.post("/api/reconcile")
def reconcile(evd_data: dict, pdf_data: dict):
    comparator = EVDPDFComparator()
    results = comparator.compare_datasets(evd_data, pdf_data)
    return results['summary']

# After (recommended - cleaner)
from reconciliation_project.domain import ReconciliationService
from reconciliation_project.adapters import JSONToInvoiceAdapter

@app.post("/api/reconcile")
def reconcile(evd_data: dict, pdf_data: dict):
    service = ReconciliationService()
    
    evd_invoices = JSONToInvoiceAdapter.from_json_dataset(evd_data, 'evd')
    pdf_invoices = JSONToInvoiceAdapter.from_json_dataset(pdf_data, 'pdf')
    
    result = service.reconcile(evd_invoices, pdf_invoices)
    
    return {
        'match_rate': result.match_rate,
        'matches': len(result.matches),
        'mismatches': len(result.mismatches),
    }
```

### Scenario 2: Batch Processing

```python
# Before
from reconciliation_project.pdf_evd_comparator import EVDPDFComparator
from reconciliation_project.reconciliation_report import ReconciliationReportGenerator

comparator = EVDPDFComparator()
generator = ReconciliationReportGenerator()

for evd_file, pdf_file in file_pairs:
    evd_data = load_json(evd_file)
    pdf_data = load_json(pdf_file)
    
    comparison = comparator.compare_datasets(evd_data, pdf_data)
    
    output = f"report_{evd_file.stem}.xlsx"
    generator.generate_report(evd_data, pdf_data, comparison, output)

# After (simpler!)
from reconciliation_project.reconciliation_report import ReconciliationReportGenerator

generator = ReconciliationReportGenerator()

for evd_file, pdf_file in file_pairs:
    evd_data = load_json(evd_file)
    pdf_data = load_json(pdf_file)
    
    output = f"report_{evd_file.stem}.xlsx"
    generator.generate_report(evd_data, pdf_data, output)
    # No need for separate comparison step!
```

### Scenario 3: Custom Business Logic

```python
# New architecture makes this easy!
from reconciliation_project.domain import ReconciliationService
from reconciliation_project.domain.rules import AmountValidator
from decimal import Decimal

# Create service with custom tolerance
service = ReconciliationService(amount_tolerance=Decimal('0.05'))

# Or customize a rule
class StrictAmountValidator(AmountValidator):
    def amounts_consistent(self, evd_amt, pdf_amt) -> bool:
        # Custom logic - must match exactly
        evd = self.normalize_amount(evd_amt)
        pdf = self.normalize_amount(pdf_amt)
        return self.amounts_match(evd, pdf)

# Easy to plug in custom rules!
```

## Troubleshooting

### Issue: Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'reconciliation_project.domain'

# Solution: Make sure you're importing from the new structure
python -c "from reconciliation_project.domain import ReconciliationService; print('✓ Imports work')"
```

### Issue: Different Results

```bash
# The refactored code should produce identical results

# Debug: Compare outputs
python reconciliation_project_old/reconciliation_report.py evd.json pdf.json old_output.xlsx
python reconciliation_project/reconciliation_report.py evd.json pdf.json new_output.xlsx

# Check both Excel files - they should be identical
```

### Issue: Performance Concerns

```python
# The refactored code should be SAME or FASTER

import time
from reconciliation_project.reconciliation_report import ReconciliationReportGenerator

start = time.time()
generator = ReconciliationReportGenerator()
generator.generate_report(evd_data, pdf_data, output_path)
print(f"Time: {time.time() - start:.2f}s")

# Should be similar to old version
```

## Rollback Plan

If anything goes wrong:

```bash
# Step 1: Stop using new code
# Step 2: Restore backup
mv reconciliation_project reconciliation_project_failed
mv reconciliation_project_backup reconciliation_project

# Step 3: Report issue with details:
# - What operation failed?
# - Error message?
# - Sample data (if possible)?
```

## Next Steps After Integration

1. **Read ARCHITECTURE.md** - Understand the new structure
2. **Read REFACTORING_SUMMARY.md** - See what changed and why
3. **Update internal docs** - Document the new architecture
4. **Train team** - Explain the layers to developers
5. **Add tests** - Take advantage of testable architecture

## Benefits You'll See

✅ **Easier to test** - Each layer independently testable  
✅ **Easier to extend** - Clear where new code goes  
✅ **Easier to maintain** - Find and fix bugs faster  
✅ **Better code organization** - No more God classes  
✅ **Fixed TODO bug** - Proper difference calculation  

## Getting Help

### Documentation

1. **ARCHITECTURE.md** - Complete architecture explanation
2. **REFACTORING_SUMMARY.md** - All changes documented
3. **This file** - Implementation steps

### Code Examples

All files include:
- Comprehensive docstrings
- Type hints
- Usage examples
- Clear responsibilities

### Questions?

Check:
1. Does the old API still work? YES - backward compatible
2. Do I need to rewrite my code? NO - but recommended for new code
3. Will this break production? NO - drop-in replacement
4. Is it faster/slower? SAME speed, better structure

## Success Checklist

Before considering integration complete:

- [ ] Backup created
- [ ] Refactored code extracted
- [ ] Dependencies verified
- [ ] CLI tested
- [ ] Programmatic API tested
- [ ] Comparison results identical
- [ ] Excel output identical
- [ ] Team trained on new structure
- [ ] Documentation updated
- [ ] Tests passing

**Once all checked - you're ready to go! 🚀**

## Contact

For issues or questions about the refactored code:
- Review ARCHITECTURE.md
- Check REFACTORING_SUMMARY.md
- Examine the code (it's well-documented)

---

**The refactored code is production-ready and backward compatible!**
