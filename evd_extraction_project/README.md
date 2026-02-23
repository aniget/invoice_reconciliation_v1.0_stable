# EVD Data Extraction & Comparison Project

## Overview

This standalone project extracts invoice data from **Zaiavka za plashtane** (EVD - Expense Verification Document) Excel files and provides tools to structure the data for easy comparison with PDF invoices.

## What This Project Does

### 1. **EVD Data Extraction** (`evd_extractor.py`)
- Reads standardized EVD Excel files
- Extracts invoice information: vendor, invoice number, date, amounts
- Normalizes vendor names for consistent matching
- Structures data by vendor and invoice number
- Outputs clean JSON format

### 2. **PDF-EVD Comparison** (`pdf_evd_comparator.py`)
- Compares EVD data with PDF extraction data
- Matches invoices by number, amount, and vendor
- Identifies perfect matches, discrepancies, and missing documents
- Generates comparison reports

## EVD File Structure

The tool expects EVD Excel files with this structure:

```
Row 12: Invoice Information section header
Row 13: Column headers (№, Vendor, Invoice Number, Date, etc.)
Row 14+: Invoice data rows

Key Columns:
- Column B (2): Row number
- Column D (4): Vendor/Supplier name
- Column O (15): Invoice number
- Column AC (29): Invoice date
- Column AJ (36): Currency
- Column BI (61): Total amount EUR
```

## Installation

### Requirements
```bash
pip install openpyxl
```

That's it! Only one dependency needed.

### Quick Start
```bash
# 1. Install dependency
pip install openpyxl

# 2. Extract data from EVD
python evd_extractor.py your_evd_file.xlsx

# Output: your_evd_file_extracted.json
```

## Usage

### Extract EVD Data

```bash
python evd_extractor.py <evd_file.xlsx> [output.json]
```

**Examples:**
```bash
# Basic extraction (auto-generates output filename)
python evd_extractor.py Zaiavka_za_plashtane_012026.xlsx

# Specify output filename
python evd_extractor.py Zaiavka_za_plashtane_012026.xlsx invoices_jan2026.json
```

**Output:**
```json
{
  "metadata": {
    "source_file": "Zaiavka_za_plashtane_012026.xlsx",
    "extraction_date": "2026-01-28 14:30:00",
    "total_invoices": 14,
    "total_vendors": 2,
    "total_amount_eur": 160.00
  },
  "by_vendor": {
    "ВИВАКОМ БЪЛГАРИЯ": {
      "vendor_name": "ВИВАКОМ БЪЛГАРИЯ",
      "invoice_count": 9,
      "total_amount": 144.00,
      "invoices": [...]
    }
  },
  "by_invoice_number": {
    "63266045": [...]
  },
  "all_invoices": [...]
}
```

### Compare EVD with PDF Data

```bash
python pdf_evd_comparator.py <evd_data.json> <pdf_data.json> [output.json]
```

**Example:**
```bash
python pdf_evd_comparator.py evd_extracted.json pdf_extracted.json comparison_report.json
```

**Output:**
- Matched invoices (perfect matches)
- Mismatched invoices (different amounts)
- Missing in PDF (EVD entries without PDF)
- Missing in EVD (PDFs without EVD entry)

## Data Structure

### Extracted Invoice Record
```json
{
  "evd_row": 14,
  "row_number": 1,
  "vendor_original": "Йеттел България ЕАД",
  "vendor_normalized": "ЙЕТТЕЛ БЪЛГАРИЯ",
  "invoice_number": "4500127510",
  "invoice_date": "2026-01-16",
  "currency": "EUR",
  "currency_amount": 0.0,
  "net_amount_eur": 0.0,
  "vat_amount_eur": 0.0,
  "total_amount_eur": 6.0
}
```

### Structured Output
The extractor creates three lookup structures:

1. **by_vendor**: Group invoices by normalized vendor name
2. **by_invoice_number**: Lookup invoices by number
3. **all_invoices**: Complete list of all invoices

This makes it easy to:
- Find all invoices from a specific vendor
- Look up an invoice by number
- Process all invoices sequentially

## Features

### Smart Vendor Normalization
```python
"Йеттел България ЕАД" → "ЙЕТТЕЛ БЪЛГАРИЯ"
"Виваком България EAД" → "ВИВАКОМ БЪЛГАРИЯ"
```

Removes:
- Company suffixes (ЕАД, ЕООД, LTD, etc.)
- Extra whitespace
- Standardizes to uppercase

### Flexible Invoice Number Matching
```python
"INV-2024-001" → "20240001"
"4500127510"   → "4500127510"
"#63266045"    → "63266045"
```

Normalizes different invoice number formats for consistent matching.

### Automatic Data Section Detection
The extractor automatically finds where invoice data starts by looking for "Invoice information" header.

## Integration with PDF Processing

This tool outputs data in a format that's ready to compare with PDF extraction results. The expected PDF data structure should match:

```json
{
  "by_vendor": {
    "VENDOR_NAME": {
      "invoices": [
        {
          "invoice_number": "...",
          "total_amount": 0.0,
          "vendor_normalized": "...",
          ...
        }
      ]
    }
  },
  "all_invoices": [...]
}
```

## Example Workflow

### Complete Invoice Verification Workflow

1. **Extract EVD Data**
```bash
python evd_extractor.py Zaiavka_za_plashtane.xlsx evd_data.json
```

2. **Extract PDF Data** (using your PDF processor)
```bash
python pdf_processor.py invoices_folder/ pdf_data.json
```

3. **Compare Datasets**
```bash
python pdf_evd_comparator.py evd_data.json pdf_data.json report.json
```

4. **Review Results**
- Check `report.json` for detailed comparison
- Review matches, mismatches, and missing documents
- Investigate discrepancies

## Sample Output

### Extraction Output
```
================================================================================
EVD Data Extractor
================================================================================
Loading file: Zaiavka_za_plashtane_Yettel_012026_Vivacom_BG_sample.xlsx
  Sheet: EVD
  Dimensions: A1:BP60
Found data start row: 14

Extracting invoice data from rows 14 to 60...
  Row 14: ЙЕТТЕЛ БЪЛГАРИЯ - 4500127510 - €6.0
  Row 15: ЙЕТТЕЛ БЪЛГАРИЯ - 4500127511 - €1.0
  ...

Extracted 14 invoice records

================================================================================
EXTRACTION SUMMARY
================================================================================
Source file: Zaiavka_za_plashtane_Yettel_012026_Vivacom_BG_sample.xlsx
Extraction date: 2026-01-28 14:30:00
Total invoices: 14
Total vendors: 2
Total amount (EUR): €160.00

By Vendor:
  ЙЕТТЕЛ БЪЛГАРИЯ: 5 invoices, €16.00
  ВИВАКОМ БЪЛГАРИЯ: 9 invoices, €144.00

Saved to: sample_output.json

[SUCCESS] Extraction completed successfully!
```

## Customization

### Adjusting Column Mapping

If your EVD format uses different columns, edit the `COLUMNS` dictionary in `evd_extractor.py`:

```python
COLUMNS = {
    'row_num': 2,        # Column B
    'vendor': 4,         # Column D
    'invoice_num': 15,   # Column O
    'invoice_date': 29,  # Column AC
    'currency': 36,      # Column AJ
    # ... adjust as needed
}
```

### Changing Amount Tolerance

For comparison, adjust the tolerance for amount matching:

```python
comparator = EVDPDFComparator(amount_tolerance=0.05)  # €0.05 tolerance
```

### Adding Custom Vendor Normalization

Add your own normalization rules:

```python
def normalize_vendor_name(self, vendor):
    vendor = super().normalize_vendor_name(vendor)
    # Add custom rules
    vendor = vendor.replace('СТАРО_ИМЕ', 'НОВО_ИМЕ')
    return vendor
```

## Troubleshooting

### "No invoices extracted"
**Check:**
- EVD file structure matches expected format
- Data starts around row 14
- Vendor column (D) has data

**Solution:** Adjust `data_start_row` or column mapping

### "Wrong amounts extracted"
**Check:**
- Total amount is in column BI (61)
- Values are numeric, not formulas

**Solution:** Open file with `data_only=True` to get calculated values

### "Vendor names not matching"
**Check:**
- Vendor normalization is working
- Compare normalized names in output

**Solution:** Add custom normalization rules for specific vendors

## Technical Details

### Column Index Reference
Excel columns → Python indices (1-based):
```
A=1, B=2, C=3, D=4, ...
O=15, AC=29, AJ=36, BI=61
```

### Data Types
- **Dates**: Converted to YYYY-MM-DD format
- **Amounts**: Converted to float (0.0 if missing)
- **Strings**: Stripped and normalized

### Performance
- **Small files** (<100 invoices): <1 second
- **Medium files** (100-500 invoices): 1-3 seconds
- **Large files** (500+ invoices): 3-10 seconds

## Files Included

```
evd_extraction_project/
├── evd_extractor.py           # Main extraction tool
├── pdf_evd_comparator.py      # Comparison utility
├── README.md                  # This file
├── TECHNICAL_NOTES.md         # Detailed technical information
├── requirements.txt           # Python dependencies
└── sample_output.json         # Example output
```

## Requirements

- Python 3.7+
- openpyxl library

No other dependencies required!

## License

This tool is provided for internal use. Modify as needed for your requirements.

## Support

For issues or questions:
1. Check TECHNICAL_NOTES.md for detailed information
2. Review sample_output.json for expected format
3. Examine the code comments in evd_extractor.py

## Version

- **Version**: 1.0
- **Date**: 2026-01-28
- **Python**: 3.7+

---

**Ready to extract! Just run `python evd_extractor.py your_file.xlsx`**
