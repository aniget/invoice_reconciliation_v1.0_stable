# Quick Start Guide - EVD Data Extractor

## 5-Minute Setup

### Step 1: Install (30 seconds)
```bash
pip install openpyxl
```

### Step 2: Extract Data (10 seconds)
```bash
python evd_extractor.py your_evd_file.xlsx
# or with a folder
python evd_extractor.py "../input_evd/evd.xlsx"
```

That's it! Your data is now in `your_evd_file_extracted.json`

---

## What You Get

The extracted JSON file contains:

✅ **All invoice data** from the EVD file  
✅ **Normalized vendor names** for easy matching  
✅ **Grouped by vendor** for quick lookups  
✅ **Indexed by invoice number** for fast searches  
✅ **Summary statistics** (totals, counts, etc.)

---

## Example Output

```bash
$ python evd_extractor.py Zaiavka_za_plashtane.xlsx

================================================================================
EVD Data Extractor
================================================================================
Loading file: Zaiavka_za_plashtane.xlsx
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
Source file: Zaiavka_za_plashtane.xlsx
Extraction date: 2026-01-28 14:30:00
Total invoices: 14
Total vendors: 2
Total amount (EUR): €160.00

By Vendor:
  ЙЕТТЕЛ БЪЛГАРИЯ: 5 invoices, €16.00
  ВИВАКОМ БЪЛГАРИЯ: 9 invoices, €144.00

Saved to: Zaiavka_za_plashtane_extracted.json

[SUCCESS] Extraction completed successfully!
```

---

## Using the Data

### In Python

```python
import json

# Load extracted data
with open('your_file_extracted.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Get summary
print(f"Total invoices: {data['metadata']['total_invoices']}")
print(f"Total amount: €{data['metadata']['total_amount_eur']}")

# Find all invoices from a vendor
vendor_data = data['by_vendor']['ЙЕТТЕЛ БЪЛГАРИЯ']
print(f"{vendor_data['vendor_name']}: {vendor_data['invoice_count']} invoices")

# Look up specific invoice
invoice = data['by_invoice_number']['4500127510'][0]
print(f"Invoice: {invoice['invoice_number']}, Amount: €{invoice['total_amount_eur']}")

# Process all invoices
for invoice in data['all_invoices']:
    print(f"{invoice['vendor_normalized']}: {invoice['invoice_number']}")
```

### Compare with PDF Data

```bash
# 1. Extract EVD data
python evd_extractor.py evd_file.xlsx evd_data.json

# 2. Extract PDF data (your own tool)
python your_pdf_extractor.py pdfs/ pdf_data.json

# 3. Compare
python pdf_evd_comparator.py evd_data.json pdf_data.json comparison.json
```

---

## Common Use Cases

### 1. Verify All Invoices Have PDFs
```python
data = json.load(open('evd_extracted.json'))
for invoice in data['all_invoices']:
    # Check if this invoice exists in your PDF collection
    check_pdf_exists(invoice['invoice_number'])
```

### 2. Calculate Vendor Totals
```python
for vendor, info in data['by_vendor'].items():
    print(f"{vendor}: €{info['total_amount']:,.2f}")
```

### 3. Export to Excel
```python
import pandas as pd

data = json.load(open('evd_extracted.json'))
df = pd.DataFrame(data['all_invoices'])
df.to_excel('invoices.xlsx', index=False)
```

### 4. Find Specific Invoice
```python
invoice_num = "4500127510"
if invoice_num in data['by_invoice_number']:
    invoice = data['by_invoice_number'][invoice_num][0]
    print(f"Found: {invoice['vendor_normalized']}, €{invoice['total_amount_eur']}")
```

---

## Troubleshooting

### "pip: command not found"
**Solution:** Install Python from python.org first

### "ModuleNotFoundError: No module named 'openpyxl'"
**Solution:** Run `pip install openpyxl`

### "No invoices extracted"
**Solution:** Your EVD file might use a different format. Contact support or check TECHNICAL_NOTES.md

### "Wrong amounts"
**Solution:** Make sure you're looking at the right column. Check column mapping in code.

---

## Next Steps

1. ✅ Extract your EVD data
2. 📄 Read README.md for complete documentation
3. 🔧 Check TECHNICAL_NOTES.md if you need to customize
4. 🔄 Use the comparison tool if you have PDF data

---

**Need help?** Check the README.md or TECHNICAL_NOTES.md files for detailed information.

**Ready to go?** Just run: `python evd_extractor.py your_file.xlsx`
