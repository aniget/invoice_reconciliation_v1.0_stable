# Technical Notes - EVD Data Extraction

## EVD File Format Analysis

### File Structure

The Zaiavka za plashtane (EVD) Excel files follow a standardized format:

```
Rows 1-11:  Headers and metadata
Row 12:     "Информация за фактура / Invoice information"
Row 13:     Column headers
Row 14+:    Invoice data
Row 30+:    Signature section (to be ignored)
```

### Column Mapping (Excel → Python 1-based index)

| Excel Column | Index | Field | Description |
|--------------|-------|-------|-------------|
| B | 2 | Row Number | Sequential numbering |
| D | 4 | Vendor | Supplier/vendor name |
| O | 15 | Invoice Number | Invoice/document number |
| AC | 29 | Invoice Date | Invoice date |
| AJ | 36 | Currency | Currency code (EUR, BGN, etc.) |
| AN | 40 | Currency Amount | Amount in original currency |
| AU | 47 | Net Amount EUR | Net amount in EUR |
| BB | 54 | VAT Amount EUR | VAT/tax amount in EUR |
| BI | 61 | Total Amount EUR | Total amount in EUR |

### Data Validation Rules

**Required Fields:**
- Vendor name (column D)
- Invoice number (column O)

**Optional Fields:**
- All other fields

**Skip Conditions:**
- Empty vendor field
- Vendor name contains keywords: "Name", "Title", "Function", "Date", "Signature"
- Vendor field has < 3 characters

### Vendor Name Normalization

**Process:**
1. Convert to uppercase
2. Remove company suffixes: ЕАД, ЕООД, AD, LTD, LLC
3. Remove extra whitespace
4. Trim leading/trailing spaces

**Examples:**
```
"Йеттел България ЕАД"        → "ЙЕТТЕЛ БЪЛГАРИЯ"
"Виваком България EAД"       → "ВИВАКОМ БЪЛГАРИЯ"
"ABC Company Ltd."           → "ABC COMPANY"
"Test  Supplier   ЕООД"      → "TEST SUPPLIER"
```

### Invoice Number Normalization

**Process:**
1. Convert to uppercase
2. Remove common prefixes: INV, INVOICE, DOC, FAKTURA, №, #
3. Remove all non-alphanumeric characters
4. Trim spaces

**Examples:**
```
"INV-2024-001"     → "20240001"
"#4500127510"      → "4500127510"
"FAKTURA №12345"   → "12345"
```

## Output Data Structure

### JSON Format

```json
{
  "metadata": {
    "source_file": "filename.xlsx",
    "extraction_date": "2026-01-28 14:30:00",
    "total_invoices": 14,
    "total_vendors": 2,
    "total_amount_eur": 160.00
  },
  "by_vendor": {
    "VENDOR_NAME": {
      "vendor_name": "VENDOR_NAME",
      "invoice_count": 5,
      "total_amount": 16.00,
      "invoices": [...]
    }
  },
  "by_invoice_number": {
    "INVOICE_NUM": [...]
  },
  "all_invoices": [
    {
      "evd_row": 14,
      "row_number": 1,
      "vendor_original": "Original Name",
      "vendor_normalized": "NORMALIZED NAME",
      "invoice_number": "4500127510",
      "invoice_date": "2026-01-16",
      "currency": "EUR",
      "currency_amount": 0.0,
      "net_amount_eur": 0.0,
      "vat_amount_eur": 0.0,
      "total_amount_eur": 6.0
    }
  ]
}
```

### Data Structure Purpose

**1. by_vendor**
- Quick vendor-based lookups
- Aggregate statistics per vendor
- Useful for reconciliation by supplier

**2. by_invoice_number**
- O(1) lookup by invoice number
- Handles duplicate invoice numbers across vendors
- Fast matching with PDF data

**3. all_invoices**
- Complete dataset for iteration
- Preserves original row order
- Useful for sequential processing

## Comparison Algorithm

### Matching Logic

**Step 1: Invoice Number Match** (Priority: High)
- Normalize both invoice numbers
- Compare: `evd_num == pdf_num`
- Score: +50 points

**Step 2: Amount Match** (Priority: Medium)
- Compare with tolerance: `abs(evd_amt - pdf_amt) <= tolerance`
- Default tolerance: €0.01
- Score: +30 points

**Step 3: Vendor Match** (Priority: Low)
- Fuzzy string matching
- Word overlap calculation
- Score: 0-20 points

**Minimum Match Score:** 50 points (requires invoice number OR amount+vendor)

### Confidence Scoring

| Score Range | Confidence | Interpretation |
|-------------|-----------|----------------|
| 80-100 | Very High | All fields match |
| 60-79 | High | Invoice + amount match |
| 50-59 | Medium | Invoice match only |
| <50 | No Match | Insufficient similarity |

### Fuzzy Vendor Matching

**Algorithm:**
1. Exact match → 1.0
2. Substring match → 0.8
3. Word overlap → `common_words / total_words`

**Example:**
```
"ЙЕТТЕЛ БЪЛГАРИЯ"  vs  "YETTEL BULGARIA"
→ No exact match
→ No substring match
→ Word overlap: 0/4 = 0.0

"ABC COMPANY"  vs  "ABC COMPANY LIMITED"
→ Substring match: "ABC COMPANY" in "ABC COMPANY LIMITED"
→ Score: 0.8
```

## Error Handling

### Extraction Errors

**1. Missing Required Fields**
- Skip row silently
- Continue processing other rows
- Log in summary

**2. Invalid Data Types**
- Convert to appropriate type
- Use default value if conversion fails
- Amounts: default to 0.0
- Dates: default to None

**3. Malformed Excel File**
- Attempt to open with `data_only=True`
- If fails, raise FileNotFoundError
- Provide clear error message

### Comparison Errors

**1. Vendor Not Found**
- Search all PDF invoices
- Perform cross-vendor matching
- Report as "Missing in PDF"

**2. Amount Discrepancy**
- Flag as mismatch
- Record difference amount
- Keep in results for review

**3. No Matches Found**
- List all unmatched items
- Separate by source (EVD/PDF)
- Provide details for investigation

## Performance Optimization

### Memory Usage

**For small files (<1000 invoices):**
- Load entire file into memory
- Process all at once
- Memory: ~10MB

**For large files (>1000 invoices):**
- Current implementation handles up to 10,000 invoices
- Memory: ~100MB
- Consider batch processing for larger files

### Processing Speed

**Bottlenecks:**
1. Excel file loading (0.1-1s)
2. Data extraction (0.01s per row)
3. Normalization (0.001s per item)

**Optimization opportunities:**
- Compile regex patterns once
- Cache normalized values
- Use set lookups for matching

## Testing Recommendations

### Unit Tests

**Test Cases:**
1. Vendor normalization
   - Test various company suffixes
   - Test special characters
   - Test unicode/cyrillic

2. Invoice number normalization
   - Test different prefixes
   - Test numeric-only
   - Test alphanumeric

3. Amount conversion
   - Test None values
   - Test zero
   - Test negative amounts
   - Test large amounts

4. Date formatting
   - Test datetime objects
   - Test string dates
   - Test None

### Integration Tests

**Test Scenarios:**
1. Complete extraction workflow
2. Comparison with perfect matches
3. Comparison with discrepancies
4. Comparison with missing items

### Sample Data

**Create test EVD files with:**
- Valid invoices (5-10)
- Duplicate invoice numbers
- Missing amounts
- Special characters in vendor names
- Edge case dates

## Column Identification Troubleshooting

### If Columns Change

**Steps to identify new columns:**

1. **Open EVD file in Excel**
2. **Find header row** (look for "Invoice information")
3. **Note column letters** for each field
4. **Convert to index**:
   ```
   A=1, B=2, C=3, ..., Z=26, AA=27, AB=28, AC=29, ...
   ```
5. **Update COLUMNS dictionary** in code

### Quick Column Reference

```python
# Excel column letter to index conversion
from openpyxl.utils import column_index_from_string

# Example
column_index_from_string('AC')  # Returns: 29
column_index_from_string('BI')  # Returns: 61
```

### Visual Column Finder

Add this code to find columns interactively:

```python
# Print all columns in header row
for col_idx in range(1, 70):
    val = ws.cell(row=12, column=col_idx).value
    if val:
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        logging.info(f"{col_letter} ({col_idx}): {val}")
```

## Integration Points

### With PDF Processors

**Expected PDF output format:**
```json
{
  "by_vendor": {
    "VENDOR": {
      "invoices": [
        {
          "invoice_number": "...",
          "total_amount": 0.0,
          "vendor_normalized": "...",
          "invoice_date": "..."
        }
      ]
    }
  },
  "all_invoices": [...]
}
```

**Matching requirements:**
- Same vendor normalization algorithm
- Same invoice number normalization
- Amount field names must match

### With Database Systems

**SQL Import:**
```sql
CREATE TABLE evd_invoices (
    id SERIAL PRIMARY KEY,
    evd_row INT,
    vendor_normalized VARCHAR(255),
    invoice_number VARCHAR(100),
    invoice_date DATE,
    currency VARCHAR(3),
    total_amount_eur DECIMAL(10,2)
);

-- Import from JSON using your database's JSON functions
```

### With Reporting Systems

**Excel Report Generation:**
- Use `pandas` to convert JSON to DataFrame
- Export to Excel with formatting
- Add charts and summaries

**PDF Report Generation:**
- Use `reportlab` or similar
- Include comparison tables
- Highlight discrepancies

## Future Enhancements

### Possible Improvements

1. **Multi-sheet Support**
   - Handle EVD files with multiple sheets
   - Process each sheet separately

2. **Batch Processing**
   - Process multiple EVD files at once
   - Combine results into single output

3. **Web Interface**
   - Upload EVD files via browser
   - View results in dashboard
   - Download reports

4. **Machine Learning**
   - Learn vendor name variations
   - Predict matching likelihood
   - Auto-correct common errors

5. **Configurable Column Mapping**
   - JSON configuration file
   - Support different EVD formats
   - Runtime column detection

## Appendix: Sample Test Data

### Minimal EVD Structure for Testing

```
Row 12: Информация за фактура
Row 13: №    Vendor    Invoice Number    Date    Amount
Row 14: 1    TEST Ltd  INV001           2026-01-01  100.00
Row 15: 2    TEST Ltd  INV002           2026-01-02  200.00
```

### Expected Output

```json
{
  "metadata": {
    "total_invoices": 2,
    "total_amount_eur": 300.00
  },
  "by_vendor": {
    "TEST": {
      "invoice_count": 2,
      "total_amount": 300.00
    }
  }
}
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-28  
**Maintained by:** EVD Extraction Team
