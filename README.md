# Invoice Reconciliation System

A simple, user-friendly tool for reconciling EVD (Expense Verification Documents) Excel files with PDF invoices.

## Features

✅ **Simple Web Interface** - User-friendly Gradio UI  
✅ **Batch Processing** - Handle multiple files at once  
✅ **Vendor Templates** - 100% accuracy for Vivacom & Yettel  
✅ **Pattern Matching** - Generic extraction for other vendors  
✅ **Excel Reports** - Professional 7-sheet reconciliation reports  
✅ **Offline Operation** - No external dependencies or APIs  

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

### 3. Open Browser

Navigate to: **http://localhost:7860**

### 4. Use the Interface

1. Upload EVD Excel files
2. Upload PDF invoices
3. Click "Process & Reconcile"
4. Download the generated report

## System Requirements

- Python 3.7+
- Windows, macOS, or Linux
- 4GB RAM minimum
- No GPU required

## Supported File Formats

**Input:**
- EVD: `.xlsx`, `.xlsm`, `.xls`
- Invoices: `.pdf`

**Output:**
- Reconciliation Report: `.xlsx` (7 sheets)

## Supported Vendors

| Vendor | Accuracy | Method |
|--------|----------|--------|
| **Vivacom Bulgaria** | 100% | Template-based |
| **Yettel Bulgaria** | 100% | Template-based |
| **Other Vendors** | 70-80% | Pattern matching |

## Project Structure

```
invoice_reconciliation/
├── app.py                          # Web UI (Gradio)
├── evd_extraction_project/         # EVD Excel extraction
│   ├── evd_extractor.py
│   └── batch_evd_extractor.py
├── pdf_extraction_system/          # PDF invoice extraction
│   ├── pdf_processor.py
│   └── extractors/
│       ├── vendor_vivacom.py       # Vivacom template
│       ├── vendor_yettel.py        # Yettel template
│       └── generic_extractor.py    # Generic patterns
├── reconciliation_system/          # Comparison & reporting
│   └── reconciliation_report.py
└── docs/                           # Documentation
```

## Documentation

- **README.md** - This file (quick start)
- **USER_GUIDE.md** - Detailed user instructions
- **DEVELOPER_GUIDE.md** - Technical documentation
- **ROADMAP.md** - Future development plans

## Troubleshooting

**Issue: Import errors**
```bash
pip install -r requirements.txt
```

**Issue: PDF processing fails**
```bash
# Check if files are valid PDFs
# Ensure files are not password-protected
```

**Issue: Port 7860 already in use**
```bash
# Edit app.py and change server_port to another port (e.g., 7861)
```

## Command Line Usage

If you prefer command-line operation:

```bash
# Process files
python run_reconciliation.py

# Files go in:
# - input_evd/    (EVD Excel files)
# - input_pdf/    (PDF invoices)
# - output/       (Reports generated here)
```

## Version

**Version 1.0 (Stable)**
- Core functionality only
- No database
- No AI dependencies
- No external APIs
- Simple and reliable

## License

MIT License - See LICENSE file

## Support

For issues or questions, please:
1. Check the USER_GUIDE.md
2. Review the troubleshooting section
3. Open an issue on GitHub

---

**Ready to reconcile! 🚀**
