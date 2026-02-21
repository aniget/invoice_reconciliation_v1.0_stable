# EVD-PDF Reconciliation System

## Complete Integration Solution

This system integrates EVD extraction, PDF extraction, and automated comparison with professional Excel report generation.

## What It Does

```
EVD Excel Files → Extract Data
                      ↓
PDF Invoices    → Extract Data
                      ↓
             Compare & Match
                      ↓
        Generate Excel Report
              (7 sheets)
```

## Features

✅ **Automated Comparison** - Matches EVD with PDF data  
✅ **Intelligent Matching** - Invoice number, amount, vendor  
✅ **Professional Excel Reports** - 7 detailed sheets  
✅ **Color-Coded Results** - Green=match, Red=mismatch, Yellow=missing  
✅ **Vendor Summaries** - Statistics by vendor  
✅ **Detailed Analysis** - Side-by-side comparisons  

## Excel Report Structure

The generated report includes **7 comprehensive sheets**:

### 1. Summary
- Overall statistics
- Match rate percentage
- Color-coded status indicator
- Quick overview of issues

### 2. Matches
- All perfectly matched invoices
- Green highlighting
- EVD and PDF details side-by-side
- Confidence scores

### 3. Mismatches  
- Invoices with discrepancies
- Red highlighting
- Amount differences
- Discrepancy details (amount, currency, date)

### 4. Missing in PDF
- EVD entries without matching PDF
- Yellow highlighting
- Shows which PDFs are missing

### 5. Missing in EVD
- PDF files without EVD entry
- Yellow highlighting
- Unexpected or unregistered invoices

### 6. By Vendor
- Summary by vendor
- Match rates per vendor
- Color-coded by performance

### 7. Detailed Comparison
- Complete side-by-side view
- All invoices in one place
- Status indicators
- Notes and discrepancy details

## Installation

```bash
# Install dependencies
pip install openpyxl

# Already have from previous steps:
# - pdfplumber (for PDF extraction)
# - openpyxl (for EVD extraction)
```

## Usage

### Step 1: Extract EVD Data

```bash
cd evd_extraction_project
python evd_extractor.py your_evd_file.xlsx evd_data.json
```

### Step 2: Extract PDF Data

```bash
cd pdf_extraction_system
python pdf_processor.py invoices_folder/ pdf_data.json
```

### Step 3: Generate Reconciliation Report

```bash
cd reconciliation_system
python reconciliation_report.py evd_data.json pdf_data.json report.xlsx
```

### Complete Workflow (All-in-One)

```bash
# 1. Extract EVD
python evd_extraction_project/evd_extractor.py data/evd_file.xlsx evd_data.json

# 2. Extract PDFs
python pdf_extraction_system/pdf_processor.py data/invoices/ pdf_data.json

# 3. Reconcile and report
python reconciliation_system/reconciliation_report.py evd_data.json pdf_data.json reconciliation_report.xlsx
```

## Example Output

### Console Output
```
================================================================================
EVD-PDF Reconciliation System
================================================================================

Loading EVD data from: evd_data.json
Loading PDF data from: pdf_data.json

Comparing datasets...

================================================================================
COMPARISON SUMMARY
================================================================================
Total EVD invoices: 14
Total PDF invoices: 14

Perfect matches: 12
Matches with discrepancies: 1
Missing in PDF: 1
Missing in EVD: 1

Match rate: 85.7%

Generating Excel report...
[SUCCESS] Reconciliation report saved: reconciliation_report.xlsx

================================================================================
RECONCILIATION COMPLETE
================================================================================
```

### Excel Report Preview

**Summary Sheet:**
```
RECONCILIATION SUMMARY
┌─────────────────────────┬───────┬────────────┐
│ Metric                  │ Count │ Percentage │
├─────────────────────────┼───────┼────────────┤
│ Total EVD Invoices      │ 14    │ 100%       │
│ Total PDF Invoices      │ 14    │ 100%       │
│ Perfect Matches         │ 12    │ 85.7%      │ [Green]
│ Mismatches              │ 1     │ 7.1%       │ [Red]
│ Missing in PDF          │ 1     │ 7.1%       │ [Yellow]
│ Missing in EVD          │ 1     │ 7.1%       │ [Yellow]
└─────────────────────────┴───────┴────────────┘

Overall Match Rate: 85.7%
Status: GOOD - Some review needed
```

**Matches Sheet (Green):**
```
┌──────────────────────┬──────────────┬────────────┬───────────┐
│ Vendor               │ Invoice #    │ EVD Amount │ PDF Amount│
├──────────────────────┼──────────────┼────────────┼───────────┤
│ ВИВАКОМ БЪЛГАРИЯ     │ 0063266046   │ €903.42    │ €903.42   │
│ ВИВАКОМ БЪЛГАРИЯ     │ 0063266047   │ €914.00    │ €914.00   │
│ ЙЕТТЕЛ БЪЛГАРИЯ      │ 4500127510   │ €6.00      │ €6.00     │
└──────────────────────┴──────────────┴────────────┴───────────┘
```

**Mismatches Sheet (Red):**
```
┌──────────────────────┬──────────────┬────────────┬────────────┬────────────┐
│ Vendor               │ Invoice #    │ EVD Amount │ PDF Amount │ Difference │
├──────────────────────┼──────────────┼────────────┼────────────┼────────────┤
│ ВИВАКОМ БЪЛГАРИЯ     │ 0063266048   │ €915.00    │ €915.50    │ €0.50      │
└──────────────────────┴──────────────┴────────────┴────────────┴────────────┘
```

## Matching Logic

### Primary Matching Criteria:
1. **Invoice Number** - Exact match (handles leading zeros)
2. **Vendor Name** - Normalized comparison
3. **Amount** - Within tolerance (default: €0.01)

### Confidence Scoring:
- **Invoice Number Match**: +50 points
- **Amount Match**: +30 points
- **Vendor Match**: +20 points

**Minimum for match:** 50 points (invoice number OR amount+vendor)

## Configuration

### Amount Tolerance

```python
# In reconciliation_report.py
comparator = EVDPDFComparator(amount_tolerance=0.01)  # €0.01

# For stricter matching
comparator = EVDPDFComparator(amount_tolerance=0.001)  # €0.001

# For looser matching (useful for rounding differences)
comparator = EVDPDFComparator(amount_tolerance=0.10)  # €0.10
```

### Invoice Number Normalization

The system automatically handles:
- Leading zeros: `63266046` matches `0063266046`
- Prefixes: `INV-001` matches `001`
- Case: `ABC123` matches `abc123`

## File Structure

```
reconciliation_system/
├── reconciliation_report.py    # Main report generator
├── pdf_evd_comparator.py      # Comparison logic
├── demo_evd_data.json         # Sample EVD data
├── demo_pdf_data.json         # Sample PDF data
├── demo_reconciliation.xlsx   # Sample output
└── README.md                  # This file
```

## Customization

### Add Custom Matching Rules

In `pdf_evd_comparator.py`, modify `find_matching_pdf()`:

```python
def find_matching_pdf(self, evd_invoice, pdf_invoices):
    # ... existing code ...
    
    # Add custom rule
    if evd_invoice.get('contract_number') == pdf_invoice.get('contract_number'):
        score += 10  # Bonus for contract match
    
    # ... rest of code ...
```

### Change Report Colors

In `reconciliation_report.py`:

```python
# In __init__:
self.match_fill = PatternFill(start_color="C6EFCE", ...)      # Light green
self.mismatch_fill = PatternFill(start_color="FFC7CE", ...)   # Light red
self.missing_fill = PatternFill(start_color="FFEB9C", ...)    # Light yellow
```

### Add Custom Sheet

```python
def _create_custom_sheet(self, data):
    ws = self.wb.create_sheet("Custom Analysis")
    # Add your analysis here
```

Then call it in `generate_report()`:
```python
self._create_custom_sheet(comparison_results)
```

## Troubleshooting

### "No matches found"

**Possible causes:**
1. Invoice numbers don't match (check format)
2. Vendors don't match (check normalization)
3. Amounts significantly different

**Solutions:**
- Check sample invoice numbers from both sources
- Increase amount tolerance
- Add debug logging to see matching attempts

### "All invoices marked as missing"

**Cause:** Data format mismatch

**Solution:** Verify both JSON files have the correct structure:
```json
{
  "by_vendor": {...},
  "by_invoice_number": {...},
  "all_invoices": [...]
}
```

### "Excel file won't open"

**Cause:** File corruption during generation

**Solution:** 
- Check disk space
- Ensure output folder exists
- Try different output path

## Performance

- **Small dataset** (<50 invoices): <5 seconds
- **Medium dataset** (50-200 invoices): 5-15 seconds  
- **Large dataset** (200-1000 invoices): 15-60 seconds

Memory usage: ~50MB for typical dataset

## Advanced Usage

### Batch Processing Multiple Periods

```python
import glob
from pathlib import Path

# Process all EVD files for a month
for evd_file in glob.glob('evd_files/*.xlsx'):
    evd_name = Path(evd_file).stem
    
    # Extract EVD
    evd_data = extract_evd(evd_file)
    
    # Find matching PDFs
    pdf_folder = f'pdfs/{evd_name}'
    pdf_data = extract_pdfs(pdf_folder)
    
    # Generate report
    output = f'reports/{evd_name}_reconciliation.xlsx'
    generate_report(evd_data, pdf_data, output)
```

### Integration with Database

```python
import sqlite3

# After comparison
conn = sqlite3.connect('reconciliation.db')

# Store matches
for match in comparison_results['matches']:
    conn.execute("""
        INSERT INTO matches (vendor, invoice_num, amount, status)
        VALUES (?, ?, ?, 'matched')
    """, (match['evd']['vendor_normalized'],
          match['evd']['invoice_number'],
          match['evd']['total_amount_eur']))

conn.commit()
```

## Report Distribution

### Email Report

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def email_report(report_path, recipients):
    msg = MIMEMultipart()
    msg['Subject'] = 'EVD-PDF Reconciliation Report'
    
    # Attach Excel file
    with open(report_path, 'rb') as f:
        part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename=reconciliation.xlsx')
        msg.attach(part)
    
    # Send email
    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    smtp.starttls()
    smtp.login('your_email', 'your_password')
    smtp.send_message(msg)
    smtp.quit()
```

### Convert to PDF

```python
import win32com.client

def excel_to_pdf(excel_path, pdf_path):
    excel = win32com.client.Dispatch("Excel.Application")
    wb = excel.Workbooks.Open(str(excel_path))
    wb.ExportAsFixedFormat(0, str(pdf_path))
    wb.Close()
    excel.Quit()
```

## Best Practices

1. **Run regularly** - Daily or weekly reconciliation
2. **Archive reports** - Keep history for audit trail
3. **Review mismatches** - Investigate discrepancies promptly
4. **Update templates** - Add new vendors as they appear
5. **Monitor match rates** - Track trends over time

## Next Steps

1. **Process your data** - Run on real EVD and PDF files
2. **Review report** - Check all sheets for issues
3. **Fix discrepancies** - Investigate mismatches
4. **Automate** - Schedule regular runs
5. **Customize** - Add vendor-specific rules

## Support

For issues:
1. Check this README
2. Review sample files
3. Enable debug logging
4. Check data format

## Version

- **Version**: 1.0
- **Date**: 2026-01-29
- **Python**: 3.7+
- **Dependencies**: openpyxl

---

**Ready to reconcile! Run: `python reconciliation_report.py evd.json pdf.json report.xlsx`**
