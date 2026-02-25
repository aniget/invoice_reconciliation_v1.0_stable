# Template Builder UI

## Purpose

Allow users to create JSON extraction templates
without writing code.

## Flow

1. Upload PDF
2. Extract raw text
3. Copy relevant line
4. Select field name
5. Add field
6. Save template

## Storage Location

pdf_extraction_project/templates/

## Template Format

{
  "vendor": "Vendor Name",
  "fields": {
      "invoice_number": {
          "type": "regex",
          "pattern": "..."
      }
  }
}

## Validation

Required fields:
- invoice_number
- invoice_date
- total_amount