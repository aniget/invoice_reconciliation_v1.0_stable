# User Guide

## Getting Started

### Installation

1. **Install Python 3.7 or higher**
   - Download from [python.org](https://python.org)
   - Verify: `python --version`

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**
   ```bash
   python app.py
   ```

4. **Open Browser**
   - Navigate to: http://localhost:7860
   - The interface will open automatically

## Using the Web Interface

### Step 1: Upload Files

**EVD Files (Left Side):**
- Click "EVD Excel Files" to upload
- Select one or more `.xlsx`, `.xlsm`, or `.xls` files
- These are your expense verification documents

**PDF Files (Right Side):**
- Click "PDF Invoice Files" to upload
- Select one or more `.pdf` files
- These are the invoices you want to reconcile

### Step 2: Process

- Click the "🔄 Process & Reconcile" button
- Wait for processing (usually 30-60 seconds)
- Progress will be shown

### Step 3: Review Results

**Summary Section:**
- Shows total files processed
- Total invoices found
- Quick statistics

**Statistics Section:**
- Breakdown by vendor
- Invoice counts

### Step 4: Download Report

- Click the "Download" link under the report section
- Save the Excel file
- Open in Microsoft Excel or Google Sheets

## Understanding the Report

The downloaded Excel file contains 7 sheets:

### Sheet 1: Summary
- Overall statistics
- Match rate percentage
- Total invoices processed
- Breakdown by status

### Sheet 2: Matches (Green)
Perfect matches between EVD and PDF:
- Invoice number matches
- Amount matches (within tolerance)
- Same vendor
- **Action needed:** None, these are correct

### Sheet 3: Mismatches (Red)
Invoices found in both but with differences:
- Amount discrepancies
- Vendor mismatches
- **Action needed:** Investigate differences

### Sheet 4: Missing in PDF (Yellow)
Invoices in EVD but not found in PDF:
- May be missing invoices
- Could be naming differences
- **Action needed:** Check if PDFs are missing

### Sheet 5: Missing in EVD (Yellow)
Invoices in PDF but not in EVD:
- Extra invoices received
- May not be in current EVD batch
- **Action needed:** Verify if should be included

### Sheet 6: EVD Data
Complete list of all EVD invoices:
- Full details from Excel files
- All extracted fields

### Sheet 7: PDF Data
Complete list of all PDF invoices:
- Full details from PDFs
- Extraction confidence scores

## Supported Vendors

### High Accuracy (Template-based)

**Vivacom Bulgaria:**
- Accuracy: 100%
- Processing time: <1 second per invoice
- All fields extracted perfectly

**Yettel Bulgaria:**
- Accuracy: 100%
- Processing time: <1 second per invoice
- All fields extracted perfectly

### Moderate Accuracy (Pattern-based)

**Other Vendors:**
- Accuracy: 70-80%
- Processing time: <2 seconds per invoice
- May require manual verification

## Tips for Best Results

### Preparing Files

1. **EVD Files:**
   - Use standard Excel format
   - Don't modify column headers
   - Keep one invoice per row
   - Save as .xlsx (preferred)

2. **PDF Files:**
   - Use good quality PDFs (not scanned if possible)
   - Ensure PDFs are not password-protected
   - Use original PDFs from vendors
   - Avoid heavily modified/annotated PDFs

### File Organization

**Recommended structure:**
```
invoices_january_2026/
├── evd/
│   ├── EVD_January_Part1.xlsx
│   └── EVD_January_Part2.xlsx
└── pdf/
    ├── vivacom_invoice_001.pdf
    ├── vivacom_invoice_002.pdf
    ├── yettel_invoice_001.pdf
    └── other_vendor_invoice.pdf
```

### Batch Processing

For large volumes:
1. Group files by period (monthly, weekly)
2. Process in batches of 50-100 invoices
3. Review results before processing next batch
4. Keep backup of original files

## Troubleshooting

### Common Issues

**Issue: "Import Error"**
```bash
# Solution: Install all dependencies
pip install -r requirements.txt
```

**Issue: "PDF Processing Failed"**
- Check if PDF is password-protected
- Verify PDF is not corrupted
- Ensure PDF is readable (open in Acrobat Reader)

**Issue: "Low Confidence Extraction"**
- PDF might be scanned (image-based)
- Try with original digital PDF
- Consider OCR setup (see OCR_SETUP_GUIDE.md)

**Issue: "Port Already in Use"**
```python
# Edit app.py, line with server_port:
app.launch(server_port=7861)  # Change to different port
```

**Issue: "Files Not Found"**
- Check file paths are correct
- Ensure files aren't open in another program
- Verify file permissions

### Getting Help

1. Check this guide first
2. Review ROADMAP.md for planned features
3. Check .gitignore for excluded file types
4. Open an issue on GitHub

## Advanced Usage

### Command-Line Mode

If you prefer command-line operation:

1. **Create Input Directories**
   ```bash
   mkdir input_evd input_pdf
   ```

2. **Copy Files**
   - Place EVD Excel files in `input_evd/`
   - Place PDF invoices in `input_pdf/`

3. **Run Processing**
   ```bash
   python run_reconciliation.py
   ```

4. **Find Results**
   - Check `output/` directory
   - Files will have timestamps

### Batch Script (Windows)

Create `reconcile.bat`:
```batch
@echo off
python run_reconciliation.py
pause
```

### Bash Script (Linux/Mac)

Create `reconcile.sh`:
```bash
#!/bin/bash
python run_reconciliation.py
```

Make executable:
```bash
chmod +x reconcile.sh
./reconcile.sh
```

## Performance Tips

### For Faster Processing

1. **Close Unnecessary Programs**
   - Free up RAM
   - Better CPU availability

2. **Process in Smaller Batches**
   - 20-50 invoices per run
   - More manageable results

3. **Use SSD Storage**
   - Faster file access
   - Better overall performance

4. **Adequate RAM**
   - Minimum 4GB
   - Recommended 8GB+

### For Better Accuracy

1. **Use Original PDFs**
   - Not scans or photos
   - Digital PDFs preferred

2. **Consistent Naming**
   - Help with vendor detection
   - Include vendor in filename

3. **Quality Check**
   - Verify EVD data first
   - Ensure PDFs are readable

## Frequently Asked Questions

**Q: What file formats are supported?**
- EVD: `.xlsx`, `.xlsm`, `.xls`
- Invoices: `.pdf` only

**Q: How many files can I process at once?**
- Recommended: 20-100 files per batch
- System can handle more, but review becomes harder

**Q: Is my data secure?**
- Yes! Everything runs locally on your computer
- No data sent to external servers
- No internet connection required

**Q: Can I use scanned PDFs?**
- Basic support through pattern matching
- For better results, install OCR (see OCR_SETUP_GUIDE.md)

**Q: What if a vendor isn't recognized?**
- System uses generic pattern matching (70-80% accurate)
- You can add vendor templates (see DEVELOPER_GUIDE.md)
- Or wait for ML features (see ROADMAP.md)

**Q: How do I add new vendors?**
- See DEVELOPER_GUIDE.md for template creation
- Or request feature on GitHub

**Q: Can I export data in other formats?**
- Currently: Excel only
- Future: CSV, JSON (see ROADMAP.md)

**Q: Does this work offline?**
- Yes! 100% offline operation
- No internet required
- All processing local

**Q: What about data privacy?**
- All data stays on your computer
- No external API calls
- No telemetry or tracking

## Best Practices

### Monthly Reconciliation Workflow

1. **Collect Files** (Day 1)
   - Gather all EVD Excel files for the month
   - Collect all PDF invoices received
   - Organize in folders

2. **Initial Processing** (Day 2)
   - Upload and process first batch
   - Review for obvious errors
   - Note any issues

3. **Investigation** (Day 3-5)
   - Review mismatches
   - Check missing invoices
   - Contact vendors if needed

4. **Final Reconciliation** (Day 6)
   - Re-process with corrections
   - Generate final report
   - Archive all files

5. **Documentation** (Day 7)
   - Save final reports
   - Document any exceptions
   - Update records

### Quality Control

**Before Processing:**
- [ ] All EVD files present
- [ ] All PDF invoices collected
- [ ] Files not corrupted
- [ ] Backup created

**After Processing:**
- [ ] Review summary statistics
- [ ] Check match rate (target: >90%)
- [ ] Investigate all mismatches
- [ ] Verify missing invoices
- [ ] Save final report

**Monthly:**
- [ ] Archive processed files
- [ ] Update vendor templates if needed
- [ ] Review overall accuracy
- [ ] Note improvement areas

---

**Need more help? See DEVELOPER_GUIDE.md for technical details or ROADMAP.md for upcoming features.**
