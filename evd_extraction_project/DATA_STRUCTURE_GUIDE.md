# EVD Data Structure - Visual Guide

##  Complete Data Flow

```
EVD Excel File
    ↓
evd_extractor.py
    ↓
Structured JSON
    ↓
├─ Lookup by Vendor
├─ Lookup by Invoice Number
└─ Complete List
    ↓
Ready for Comparison with PDF Data
```

---

## 📁 Output JSON Structure

### Top Level

```
{
  metadata: {...},           // Summary information
  by_vendor: {...},          // Grouped by vendor
  by_invoice_number: {...},  // Indexed by invoice number
  all_invoices: [...]        // Complete list
}
```

### 1. Metadata Section

```json
{
  "metadata": {
    "source_file": "Zaiavka_za_plashtane_Yettel_012026_Vivacom_BG_sample.xlsx",
    "extraction_date": "2026-01-28 20:32:22",
    "total_invoices": 14,
    "total_vendors": 2,
    "total_amount_eur": 160.0
  }
}
```

**Purpose:** Quick overview and statistics

**Usage:**
```python
logging.info(f"Extracted {data['metadata']['total_invoices']} invoices")
logging.info(f"Total: €{data['metadata']['total_amount_eur']:,.2f}")
```

---

### 2. By Vendor Section

```json
{
  "by_vendor": {
    "ЙЕТТЕЛ БЪЛГАРИЯ": {
      "vendor_name": "ЙЕТТЕЛ БЪЛГАРИЯ",
      "invoice_count": 5,
      "total_amount": 16.0,
      "invoices": [
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
        },
        // ... more invoices from this vendor
      ]
    },
    "ВИВАКОМ БЪЛГАРИЯ": {
      // ... similar structure
    }
  }
}
```

**Purpose:** Fast vendor-based operations

**Usage:**
```python
# Get all invoices from a vendor
vendor_invoices = data['by_vendor']['ЙЕТТЕЛ БЪЛГАРИЯ']['invoices']

# Calculate vendor total
vendor_total = data['by_vendor']['ЙЕТТЕЛ БЪЛГАРИЯ']['total_amount']

# List all vendors
for vendor_name in data['by_vendor'].keys():
    logging.info(vendor_name)
```

---

### 3. By Invoice Number Section

```json
{
  "by_invoice_number": {
    "4500127510": [
      {
        "evd_row": 14,
        "vendor_normalized": "ЙЕТТЕЛ БЪЛГАРИЯ",
        "invoice_number": "4500127510",
        "total_amount_eur": 6.0,
        // ... full invoice data
      }
    ],
    "63266045": [
      {
        "evd_row": 20,
        "vendor_normalized": "ВИВАКОМ БЪЛГАРИЯ",
        "invoice_number": "63266045",
        "total_amount_eur": 12.0,
        // ... full invoice data
      }
    ]
    // ... more invoice numbers
  }
}
```

**Purpose:** O(1) lookup by invoice number

**Usage:**
```python
# Find invoice by number
invoice_num = "4500127510"
if invoice_num in data['by_invoice_number']:
    invoice = data['by_invoice_number'][invoice_num][0]
    logging.info(f"Amount: €{invoice['total_amount_eur']}")
else:
    logging.info("Invoice not found")

# Check for duplicates
invoice_num = "4500127510"
count = len(data['by_invoice_number'][invoice_num])
if count > 1:
    logging.info(f"Warning: {count} invoices with same number!")
```

---

### 4. All Invoices Section

```json
{
  "all_invoices": [
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
    },
    // ... all other invoices in order
  ]
}
```

**Purpose:** Complete dataset, preserves order

**Usage:**
```python
# Process all invoices
for invoice in data['all_invoices']:
    logging.info(f"{invoice['invoice_number']}: €{invoice['total_amount_eur']}")

# Convert to DataFrame
import pandas as pd
df = pd.DataFrame(data['all_invoices'])

# Filter invoices
high_value = [inv for inv in data['all_invoices'] 
              if inv['total_amount_eur'] > 10]
```

---

## 🔍 Invoice Record Fields

### Complete Invoice Record Structure

```json
{
  "evd_row": 14,                              // Excel row number
  "row_number": 1,                            // Sequential number in EVD
  "vendor_original": "Йеттел България ЕАД",   // Original vendor name
  "vendor_normalized": "ЙЕТТЕЛ БЪЛГАРИЯ",     // Normalized for matching
  "invoice_number": "4500127510",             // Invoice/document number
  "invoice_date": "2026-01-16",              // Invoice date (YYYY-MM-DD)
  "currency": "EUR",                          // Currency code
  "currency_amount": 0.0,                     // Amount in original currency
  "net_amount_eur": 0.0,                      // Net amount in EUR
  "vat_amount_eur": 0.0,                      // VAT amount in EUR
  "total_amount_eur": 6.0                     // Total amount in EUR
}
```

### Field Descriptions

| Field | Type | Description | Usage |
|-------|------|-------------|-------|
| `evd_row` | int | Original Excel row | Debugging, tracing |
| `row_number` | int | Sequential number | Reference |
| `vendor_original` | str | Original vendor name | Display |
| `vendor_normalized` | str | Normalized vendor | Matching, grouping |
| `invoice_number` | str | Invoice number | Primary key for matching |
| `invoice_date` | str | Invoice date | Date filtering, sorting |
| `currency` | str | Currency code | Currency conversion |
| `currency_amount` | float | Original currency amount | Multi-currency tracking |
| `net_amount_eur` | float | Net amount EUR | Subtotals |
| `vat_amount_eur` | float | VAT amount EUR | Tax calculations |
| `total_amount_eur` | float | Total EUR | **Primary amount for matching** |

---

## 🔄 Usage Patterns

### Pattern 1: Find All Invoices for Vendor

```python
# Method 1: Using by_vendor
vendor_name = "ЙЕТТЕЛ БЪЛГАРИЯ"
if vendor_name in data['by_vendor']:
    invoices = data['by_vendor'][vendor_name]['invoices']
    total = data['by_vendor'][vendor_name]['total_amount']
    logging.info(f"{vendor_name}: {len(invoices)} invoices, €{total:,.2f}")

# Method 2: Filtering all_invoices
invoices = [inv for inv in data['all_invoices'] 
            if inv['vendor_normalized'] == vendor_name]
```

### Pattern 2: Lookup Specific Invoice

```python
# Fast O(1) lookup
invoice_num = "4500127510"
if invoice_num in data['by_invoice_number']:
    invoice = data['by_invoice_number'][invoice_num][0]
    logging.info(f"Vendor: {invoice['vendor_normalized']}")
    logging.info(f"Amount: €{invoice['total_amount_eur']}")
else:
    logging.info(f"Invoice {invoice_num} not found")
```

### Pattern 3: Generate Report

```python
# Summary by vendor
logging.info("Vendor Summary:")
logging.info("-" * 50)
for vendor, info in data['by_vendor'].items():
    logging.info(f"{vendor:30} {info['invoice_count']:3} invoices  €{info['total_amount']:>10,.2f}")

logging.info("-" * 50)
logging.info(f"{'TOTAL':30} {data['metadata']['total_invoices']:3} invoices  €{data['metadata']['total_amount_eur']:>10,.2f}")
```

### Pattern 4: Export to Excel

```python
import pandas as pd

# Simple export
df = pd.DataFrame(data['all_invoices'])
df.to_excel('invoices.xlsx', index=False)

# Export with summary
with pd.ExcelWriter('invoices_report.xlsx') as writer:
    # All invoices
    df_all = pd.DataFrame(data['all_invoices'])
    df_all.to_excel(writer, sheet_name='All Invoices', index=False)
    
    # By vendor
    for vendor, info in data['by_vendor'].items():
        df_vendor = pd.DataFrame(info['invoices'])
        sheet_name = vendor[:31]  # Excel sheet name limit
        df_vendor.to_excel(writer, sheet_name=sheet_name, index=False)
```

### Pattern 5: Compare with PDF Data

```python
# Assuming pdf_data has same structure

# Find invoices only in EVD
evd_numbers = set(data['by_invoice_number'].keys())
pdf_numbers = set(pdf_data['by_invoice_number'].keys())

only_in_evd = evd_numbers - pdf_numbers
only_in_pdf = pdf_numbers - evd_numbers

logging.info(f"Only in EVD: {len(only_in_evd)}")
logging.info(f"Only in PDF: {len(only_in_pdf)}")
logging.info(f"In both: {len(evd_numbers & pdf_numbers)}")
```

---

## 📈 Data Statistics

### Quick Stats from Sample File

```
Total Invoices: 14
Total Vendors: 2
Total Amount: €160.00

Breakdown by Vendor:
├─ ЙЕТТЕЛ БЪЛГАРИЯ
│  ├─ Invoices: 5
│  ├─ Amount: €16.00
│  └─ Average: €3.20
│
└─ ВИВАКОМ БЪЛГАРИЯ
   ├─ Invoices: 9
   ├─ Amount: €144.00
   └─ Average: €16.00
```

---

## 💡 Pro Tips

### Tip 1: Always Use Normalized Names
```python
# ✅ Good
if 'ЙЕТТЕЛ БЪЛГАРИЯ' in data['by_vendor']:
    ...

# [ERROR] Bad - won't find it
if 'Йеттел България ЕАД' in data['by_vendor']:
    ...
```

### Tip 2: Handle Missing Data
```python
# ✅ Good - check existence first
if invoice_num in data['by_invoice_number']:
    invoice = data['by_invoice_number'][invoice_num][0]
else:
    logging.info("Not found")

# [ERROR] Bad - will crash
invoice = data['by_invoice_number'][invoice_num][0]
```

### Tip 3: Use Total Amount for Matching
```python
# ✅ Good - use total_amount_eur
amount = invoice['total_amount_eur']

# [ATTENTION]️ Less reliable - might be 0
amount = invoice['currency_amount']
```

---

## 🎯 Key Takeaways

1. **Three ways to access data:**
   - by_vendor → For vendor-based operations
   - by_invoice_number → For fast lookups
   - all_invoices → For complete iteration

2. **Always use normalized names:**
   - vendor_normalized (not vendor_original)
   - Consistent formatting for matching

3. **Primary matching field:**
   - invoice_number (unique identifier)
   - total_amount_eur (for verification)

4. **Safe data access:**
   - Check existence before accessing
   - Handle None values
   - Validate data types

---

**Ready to use your data? Load the JSON and start exploring!**

```python
import json
with open('your_file_extracted.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# You now have access to all three structures:
data['by_vendor']
data['by_invoice_number']
data['all_invoices']
```
