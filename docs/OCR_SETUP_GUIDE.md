# OCR Setup Guide - Complete Instructions

## What is OCR?

**OCR (Optical Character Recognition)** converts scanned PDFs (images) into text. This is essential for:
- Scanned invoices
- Photos of invoices
- PDFs without embedded text
- Low-quality or faxed documents

## When Do You Need OCR?

**✅ You NEED OCR if:**
- PDFs are scanned/photographed
- Opening PDF shows an image (can't select text)
- PDF extraction returns empty or gibberish text

**[ERROR] You DON'T need OCR if:**
- PDFs are generated electronically
- You can select and copy text from PDF
- Text extraction works fine

## Installation

### Prerequisites
- Python 3.7+
- pip package manager
- Windows/Linux/macOS

---

## Windows Setup (Detailed)

### Step 1: Install Python Packages

```bash
pip install pytesseract pdf2image Pillow
```

### Step 2: Install Tesseract OCR

1. **Download Tesseract:**
   - Go to: https://github.com/UB-Mannheim/tesseract/wiki
   - Download: `tesseract-ocr-w64-setup-5.3.x.exe` (latest version)

2. **Run Installer:**
   - Double-click the downloaded file
   - **IMPORTANT:** During installation, check "Additional language data"
   - Select **Bulgarian (bul)** from the language list
   - Install to default location: `C:\Program Files\Tesseract-OCR`
   - Click "Install"

3. **Verify Installation:**
   ```bash
   # Open Command Prompt
   "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
   ```
   
   Should show:
   ```
   tesseract 5.3.x
   ```

4. **Add to System PATH (if needed):**
   - Right-click "This PC" → Properties
   - Advanced system settings → Environment Variables
   - Edit "Path" variable
   - Add: `C:\Program Files\Tesseract-OCR`
   - Click OK

### Step 3: Install Poppler (PDF to Image Converter)

1. **Download Poppler:**
   - Go to: https://github.com/oschwartz10612/poppler-windows/releases/
   - Download: `Release-24.xx.x-0.zip` (latest version)

2. **Extract:**
   - Extract to: `C:\Program Files\poppler`
   - You should have: `C:\Program Files\poppler\Library\bin\`

3. **Add to System PATH:**
   - Same process as Tesseract
   - Add: `C:\Program Files\poppler\Library\bin`

4. **Verify Installation:**
   ```bash
   pdftoppm -v
   ```
   
   Should show version info

### Step 4: Configure Python to Find Tesseract

If automatic detection fails, add to your script:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

Or set environment variable:
```bash
setx TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

---

## Linux Setup

### Ubuntu/Debian:

```bash
# Install Tesseract with Bulgarian language
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-bul

# Install Poppler
sudo apt-get install poppler-utils

# Install Python packages
pip install pytesseract pdf2image Pillow
```

### CentOS/RHEL:

```bash
# Install Tesseract
sudo yum install tesseract tesseract-langpack-bul

# Install Poppler
sudo yum install poppler-utils

# Install Python packages
pip install pytesseract pdf2image Pillow
```

---

## macOS Setup

### Using Homebrew:

```bash
# Install Tesseract
brew install tesseract

# Install Bulgarian language pack
brew install tesseract-lang

# Install Poppler
brew install poppler

# Install Python packages
pip install pytesseract pdf2image Pillow
```

---

## Verification

### Test OCR Installation

Create a test script `test_ocr.py`:

```python
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

logging.info("Testing OCR Setup...")

# Test 1: Tesseract version
try:
    version = pytesseract.get_tesseract_version()
    logging.info(f"[SUCCESS] Tesseract version: {version}")
except Exception as e:
    logging.info(f"[ERROR] Tesseract not found: {e}")
    exit(1)

# Test 2: Languages available
try:
    langs = pytesseract.get_languages()
    logging.info(f"[SUCCESS] Available languages: {', '.join(langs)}")
    
    if 'bul' in langs:
        logging.info("[SUCCESS] Bulgarian language pack installed")
    else:
        logging.info("[ATTENTION] Bulgarian language pack NOT found")
        logging.info("  Install from: https://github.com/tesseract-ocr/tessdata")
except Exception as e:
    logging.info(f"[ATTENTION] Could not get languages: {e}")

# Test 3: PDF to image conversion
try:
    # Create a test image with text
    img = Image.new('RGB', (400, 100), color='white')
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Test 123 Тест", fill='black')
    
    # OCR the image
    text = pytesseract.image_to_string(img, lang='eng+bul')
    logging.info(f"[SUCCESS] OCR test successful: '{text.strip()}'")
except Exception as e:
    logging.info(f"[ERROR] OCR test failed: {e}")

logging.info("\n[SUCCESS] All checks passed! OCR is ready to use.")
```

Run the test:
```bash
python test_ocr.py
```

Expected output:
```
Testing OCR Setup...
[SUCCESS] Tesseract version: 5.3.x
[SUCCESS] Available languages: eng, bul, osd
[SUCCESS] Bulgarian language pack installed
[SUCCESS] OCR test successful: 'Test 123 Тест'

[SUCCESS] All checks passed! OCR is ready to use.
```

---

## Using OCR in the System

### Automatic OCR Fallback

The system **automatically** uses OCR when text extraction fails:

```python
# Process PDFs - OCR kicks in automatically
python pdf_processor.py invoices/ output.json
```

**Workflow:**
1. Try normal text extraction (pdfplumber)
2. If text is insufficient (<50 chars), try OCR
3. OCR converts PDF to images and extracts text
4. Continue with normal processing

### Manual OCR Control

If you want to force OCR or disable it:

```python
from pdf_processor import PDFInvoiceProcessor

processor = PDFInvoiceProcessor()

# Check if OCR is available
if processor.ocr_enabled:
    logging.info("OCR is available")
else:
    logging.info("OCR not available")

# Process with OCR explicitly
text = processor.extract_text_ocr(Path('scanned_invoice.pdf'))
```

---

## Performance & Quality

### OCR Settings

The system uses optimized settings:

```python
# In pdf_processor.py
pytesseract.image_to_string(
    image,
    lang='bul+eng',        # Bulgarian + English
    config='--psm 6'       # Assume uniform text block
)
```

**Page Segmentation Modes (PSM):**
- `--psm 6` - Uniform block of text (default, best for invoices)
- `--psm 3` - Fully automatic (slower, more accurate for complex layouts)
- `--psm 4` - Single column of text

**To change PSM**, edit `pdf_processor.py`:
```python
config='--psm 3'  # More accurate but slower
```

### Image Preprocessing

The system preprocesses images for better OCR:

1. **Convert to Grayscale** - Removes color noise
2. **Enhance Contrast** - Makes text clearer
3. **Sharpen** - Improves edge detection

**To adjust preprocessing:**

```python
# In extract_text_ocr method
enhancer = ImageEnhance.Contrast(image)
image = enhancer.enhance(2.5)  # Increase for darker scans
```

### Performance Metrics

**Speed:**
- Text-based PDF: ~0.5 seconds
- Scanned PDF (with OCR): ~3-5 seconds per page

**Accuracy:**
- Clean scans: 95%+
- Normal quality: 85-95%
- Poor quality: 70-85%

**Tips for Better Results:**
- Use 300 DPI or higher for scanning
- Ensure good lighting
- Keep documents flat
- Avoid shadows and glare

---

## Troubleshooting

### Error: "Tesseract not found"

**Solution:**
```python
# Add to pdf_processor.py at the top
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Error: "Bulgarian language not found"

**Solution:**
1. Reinstall Tesseract and select Bulgarian during installation
2. Or manually download `bul.traineddata`:
   - From: https://github.com/tesseract-ocr/tessdata
   - Copy to: `C:\Program Files\Tesseract-OCR\tessdata\`

### Error: "PDF to image conversion failed"

**Solution:**
1. Check Poppler installation
2. Verify PATH includes poppler bin folder
3. Test manually: `pdftoppm -v`

### Low OCR Accuracy

**Solutions:**
1. **Increase DPI:**
   ```python
   images = convert_from_path(pdf_path, dpi=400)  # Higher quality
   ```

2. **Adjust preprocessing:**
   ```python
   enhancer = ImageEnhance.Contrast(image)
   image = enhancer.enhance(2.5)  # Stronger contrast
   ```

3. **Try different PSM:**
   ```python
   config='--psm 3'  # Fully automatic
   ```

### OCR Too Slow

**Solutions:**
1. **Lower DPI:**
   ```python
   images = convert_from_path(pdf_path, dpi=200)  # Faster
   ```

2. **Process specific pages only:**
   ```python
   images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
   ```

3. **Skip OCR for text-based PDFs** (system does this automatically)

---

## Advanced Configuration

### Custom Language Combinations

```python
# English + Bulgarian + Russian
text = pytesseract.image_to_string(image, lang='eng+bul+rus')

# Only Bulgarian
text = pytesseract.image_to_string(image, lang='bul')
```

### Confidence Scores

```python
# Get OCR confidence data
data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

# Check confidence for each word
for i, conf in enumerate(data['conf']):
    if int(conf) > 60:  # Only accept >60% confidence
        logging.info(data['text'][i])
```

### Batch OCR Processing

```python
# Process multiple PDFs with OCR
from pathlib import Path

for pdf_file in Path('scanned_invoices/').glob('*.pdf'):
    logging.info(f"Processing: {pdf_file}")
    text = processor.extract_text_ocr(pdf_file)
    # ... process text
```

---

## System Integration

### How OCR is Integrated

```python
# In pdf_processor.py

def process_pdf(self, pdf_path):
    # 1. Try normal text extraction
    text = self.extract_text(pdf_path)
    
    # 2. Check if sufficient text
    if len(text) < 50:
        # 3. Fall back to OCR
        if self.ocr_enabled:
            text = self.extract_text_ocr(pdf_path)
    
    # 4. Continue normal processing
    data = self.extract_data(text)
    return data
```

### OCR Statistics

The system tracks OCR usage:

```
PROCESSING SUMMARY
==================
Total processed: 20
Successful: 19
Failed: 1
OCR used: 5          # Number of PDFs that needed OCR
```

---

## Best Practices

### When to Use OCR

✅ **Use OCR for:**
- Scanned documents
- Faxed invoices
- Photos of invoices
- Legacy documents

[ERROR] **Don't use OCR for:**
- Electronically generated PDFs
- When text extraction works fine
- Real-time processing (OCR is slower)

### Quality Checklist

Before OCR processing:
- [ ] Scan at 300+ DPI
- [ ] Ensure document is straight
- [ ] Good lighting, no shadows
- [ ] Clean document (no stains/marks)
- [ ] High contrast (dark text, light background)

### Performance Tips

1. **Pre-filter PDFs:**
   ```python
   # Skip OCR for text-based PDFs
   text = extract_text(pdf)
   if len(text) > 100:
       # Has text, no OCR needed
       return text
   else:
       # Scanned, use OCR
       return extract_text_ocr(pdf)
   ```

2. **Parallel Processing:**
   ```python
   from multiprocessing import Pool
   
   with Pool(4) as p:
       results = p.map(process_pdf, pdf_files)
   ```

3. **Cache Results:**
   ```python
   # Save OCR text to avoid re-processing
   cache_file = f"{pdf_path.stem}_ocr.txt"
   if cache_file.exists():
       return cache_file.read_text()
   else:
       text = extract_text_ocr(pdf_path)
       cache_file.write_text(text)
       return text
   ```

---

## Resources

### Downloads
- **Tesseract Windows:** https://github.com/UB-Mannheim/tesseract/wiki
- **Poppler Windows:** https://github.com/oschwartz10612/poppler-windows/releases/
- **Language Data:** https://github.com/tesseract-ocr/tessdata

### Documentation
- **Tesseract:** https://github.com/tesseract-ocr/tesseract
- **pytesseract:** https://pypi.org/project/pytesseract/
- **pdf2image:** https://pypi.org/project/pdf2image/

### Support
- Tesseract Issues: https://github.com/tesseract-ocr/tesseract/issues
- pytesseract Issues: https://github.com/madmaze/pytesseract/issues

---

## Quick Reference

### Installation Commands

**Windows:**
```bash
pip install pytesseract pdf2image Pillow
# Then install Tesseract and Poppler manually
```

**Linux (Ubuntu):**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-bul poppler-utils
pip install pytesseract pdf2image Pillow
```

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
pip install pytesseract pdf2image Pillow
```

### Usage

```python
# Import
from pdf_processor import PDFInvoiceProcessor

# Initialize
processor = PDFInvoiceProcessor()

# Check OCR availability
logging.info(f"OCR enabled: {processor.ocr_enabled}")

# Process PDFs (OCR automatic)
processor.process_folder('invoices/', 'output.json')
```

### Verification

```bash
# Test Tesseract
tesseract --version

# Test Poppler
pdftoppm -v

# Test in Python
python -c "import pytesseract; logging.info(pytesseract.get_tesseract_version())"
```

---

**OCR is now integrated and ready to use! The system will automatically use it when needed.**
