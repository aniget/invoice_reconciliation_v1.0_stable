"""
PDF Invoice Processor - Main Module

Processes vendor-specific PDF invoices and extracts structured data.
Supports multiple vendors with template-based and generic extraction.

Author: PDF Extraction Team
Date: 2026-01-29
"""

from datetime import datetime
import pdfplumber
from typing import Dict, List, Optional
from pathlib import Path
import json
from .extractors.generic_extractor import GenericExtractor
from .extractors.vendor_yettel import YettelExtractor
from .extractors.vendor_vivacom import VivacomExtractor
import sys
import logging


class PDFInvoiceProcessor:
    """
    Main processor for PDF invoices.

    Workflow:
    1. Extract text from PDF
    2. Detect vendor
    3. Use vendor-specific extractor or generic
    4. Validate and return structured data
    """

    def __init__(self):
        """Initialize processor with all extractors."""
        # Register vendor extractors
        self.vendor_extractors = {
            'VIVACOM': VivacomExtractor(),
            'YETTEL': YettelExtractor(),
            # Add more vendors here:
            # 'A1': A1Extractor(),
        }

        # Generic extractor as fallback
        self.generic_extractor = GenericExtractor()

        # OCR configuration
        self.ocr_enabled = self._check_ocr_available()

        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'ocr_used': 0,
            'by_vendor': {}
        }

    def _check_ocr_available(self) -> bool:
        """Check if OCR libraries are available."""
        try:
            import pytesseract
            import pdf2image
            # Try to get tesseract version
            pytesseract.get_tesseract_version()
            return True
        except (ImportError, Exception):
            return False

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from PDF file.

        Args:
            pdf_path (Path): Path to PDF file

        Returns:
            str: Extracted text
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                return text
        except Exception as e:
            logging.info(
                f"Error extracting text from {pdf_path.name}: {str(e)}")
            return ""

    def extract_text_ocr(self, pdf_path: Path) -> str:
        """
        Extract text from PDF using OCR (for scanned documents).

        Args:
            pdf_path (Path): Path to PDF file

        Returns:
            str: Extracted text via OCR
        """
        if not self.ocr_enabled:
            logging.info(f"  OCR not available, skipping")
            return ""

        try:
            import pytesseract
            from pdf2image import convert_from_path
            from PIL import ImageEnhance, ImageFilter

            logging.info(f"  Using OCR for {pdf_path.name}...")

            # Convert PDF to images
            images = convert_from_path(str(pdf_path), dpi=300)

            text = ""
            for i, image in enumerate(images):
                # Preprocess image for better OCR
                # Convert to grayscale
                image = image.convert('L')

                # Enhance contrast
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(2.0)

                # Sharpen
                image = image.filter(ImageFilter.SHARPEN)

                # Run OCR with Bulgarian + English
                page_text = pytesseract.image_to_string(
                    image,
                    lang='bul+eng',
                    config='--psm 6'  # Assume uniform block of text
                )

                text += page_text + "\n\n"

            self.stats['ocr_used'] += 1
            logging.info(
                f"  [SUCCESS] OCR completed ({len(text)} characters extracted)")
            return text

        except Exception as e:
            logging.info(f"  [ERROR] OCR failed: {str(e)}")
            return ""

    def detect_vendor(self, text: str, filename: str) -> Optional[str]:
        """
        Detect vendor from PDF content or filename.

        Args:
            text (str): Extracted PDF text
            filename (str): PDF filename

        Returns:
            str: Vendor identifier or None
        """
        # Try each vendor's detection method
        for vendor_name, extractor in self.vendor_extractors.items():
            if hasattr(extractor, 'detect') and extractor.detect(text):
                return vendor_name

        # Try filename detection
        filename_lower = filename.lower()
        if 'vivacom' in filename_lower or 'виваком' in filename_lower:
            return 'VIVACOM'
        if 'yettel' in filename_lower or 'йеттел' in filename_lower:
            return 'YETTEL'
        if 'a1' in filename_lower:
            return 'A1'

        return None

    def process_pdf(self, pdf_path: Path) -> Dict:
        """
        Process a single PDF invoice.

        Args:
            pdf_path (Path): Path to PDF file

        Returns:
            dict: Extracted invoice data
        """
        self.stats['total_processed'] += 1

        logging.info(f"Processing: {pdf_path.name}")

        # Extract text
        text = self.extract_text(pdf_path)
        if not text or len(text) < 50:
            logging.info(
                f"  [ATTENTION] Insufficient text extracted ({len(text)} chars)")

            # Try OCR if available
            if self.ocr_enabled:
                text = self.extract_text_ocr(pdf_path)

            if not text or len(text) < 50:
                logging.info(f"  [ERROR] Failed: Insufficient text extracted")
                self.stats['failed'] += 1
                return {
                    'filename': pdf_path.name,
                    'status': 'failed',
                    'error': 'Insufficient text extracted',
                    'confidence': 0
                }

        # Detect vendor
        vendor = self.detect_vendor(text, pdf_path.name)
        logging.info(f"  Detected vendor: {vendor or 'UNKNOWN'}")

        # Extract data
        if vendor and vendor in self.vendor_extractors:
            # Use vendor-specific extractor
            extractor = self.vendor_extractors[vendor]
            data = extractor.extract(text, str(pdf_path))
            data['detected_vendor'] = vendor

            # Validate
            if hasattr(extractor, 'validate') and not extractor.validate(data):
                logging.info(
                    f"  [ATTENTION] Vendor template validation failed, using generic")
                data = self.generic_extractor.extract(text, str(pdf_path))
                data['extraction_method'] = 'generic_fallback'
        else:
            # Use generic extractor
            data = self.generic_extractor.extract(text, str(pdf_path))
            data['detected_vendor'] = 'UNKNOWN'

        # Add metadata
        data['filename'] = pdf_path.name
        data['filepath'] = str(pdf_path)
        data['processed_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['status'] = 'success' if data.get(
            'confidence', 0) >= 50 else 'low_confidence'

        # Update stats
        if data['status'] == 'success':
            self.stats['successful'] += 1

        vendor_key = data.get('detected_vendor', 'UNKNOWN')
        self.stats['by_vendor'][vendor_key] = self.stats['by_vendor'].get(
            vendor_key, 0) + 1

        # Print results
        conf = data.get('confidence', 0)
        inv_num = data.get('invoice_number', 'N/A')
        amount = data.get('total_amount_eur', 0)

        if conf >= 80:
            logging.info(
                f"  [SUCCESS] Success: {inv_num} - €{amount} (confidence: {conf}%)")
        elif conf >= 50:
            logging.info(
                f"  [ATTENTION] Extracted: {inv_num} - €{amount} (confidence: {conf}%) - Review recommended")
        else:
            logging.info(
                f"  [ERROR] Low confidence: {conf}% - Manual review required")

        return data

    def process_folder(self, folder_path: Path, output_path: Optional[Path] = None) -> Dict:
        """
        Process all PDF files in a folder.

        Args:
            folder_path (Path): Path to folder containing PDFs
            output_path (Path, optional): Path for output JSON

        Returns:
            dict: Structured extraction results
        """
        folder_path = Path(folder_path)

        logging.info("="*80)
        logging.info("PDF Invoice Processor")
        logging.info("="*80)
        logging.info(f"Input folder: {folder_path}")
        logging.info("")

        # Find all PDF files (*.pdf matches .pdf and .PDF on case-insensitive filesystems)
        pdf_files = sorted(folder_path.glob('*.pdf'))

        if not pdf_files:
            logging.info("No PDF files found")
            return {'invoices': [], 'summary': {}}

        logging.info(f"Found {len(pdf_files)} PDF file(s)\n")

        # Process each PDF
        results = []
        for pdf_file in pdf_files:
            try:
                data = self.process_pdf(pdf_file)
                results.append(data)
            except Exception as e:
                logging.info(f"  [ERROR] Error: {str(e)}")
                self.stats['failed'] += 1
                results.append({
                    'filename': pdf_file.name,
                    'status': 'error',
                    'error': str(e),
                    'confidence': 0
                })
            logging.info("")

        # Structure results
        structured_results = self._structure_results(results)

        # Print summary
        self._print_summary()

        # Save to file if requested
        if output_path:
            self._save_results(structured_results, output_path)

        return structured_results

    def _structure_results(self, results: List[Dict]) -> Dict:
        """Structure results by vendor and invoice number."""
        structured = {
            'metadata': {
                'processed_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_invoices': len(results),
                'successful': sum(1 for r in results if r.get('status') == 'success'),
                'failed': sum(1 for r in results if r.get('status') in ['failed', 'error']),
                'low_confidence': sum(1 for r in results if r.get('status') == 'low_confidence')
            },
            'by_vendor': {},
            'by_invoice_number': {},
            'all_invoices': results
        }

        # Group by vendor
        for result in results:
            vendor = result.get('vendor_normalized', 'UNKNOWN')
            if vendor not in structured['by_vendor']:
                structured['by_vendor'][vendor] = {
                    'vendor_name': vendor,
                    'invoice_count': 0,
                    'total_amount': 0,
                    'invoices': []
                }

            structured['by_vendor'][vendor]['invoices'].append(result)
            structured['by_vendor'][vendor]['invoice_count'] += 1

            amount = result.get('total_amount_eur', 0)
            if amount:
                structured['by_vendor'][vendor]['total_amount'] += amount

        # Index by invoice number
        for result in results:
            inv_num = result.get('invoice_number')
            if inv_num:
                if inv_num not in structured['by_invoice_number']:
                    structured['by_invoice_number'][inv_num] = []
                structured['by_invoice_number'][inv_num].append(result)

        return structured

    def _print_summary(self):
        """Print processing summary."""
        logging.info("="*80)
        logging.info("PROCESSING SUMMARY")
        logging.info("="*80)
        logging.info(f"Total processed: {self.stats['total_processed']}")
        logging.info(f"Successful: {self.stats['successful']}")
        logging.info(f"Failed: {self.stats['failed']}")

        if self.ocr_enabled and self.stats['ocr_used'] > 0:
            logging.info(f"OCR used: {self.stats['ocr_used']}")
        elif not self.ocr_enabled:
            logging.info(
                "OCR: Not available (install pytesseract and pdf2image)")

        if self.stats['by_vendor']:
            logging.info("\nBy Vendor:")
            for vendor, count in self.stats['by_vendor'].items():
                logging.info(f"  {vendor}: {count}")

    def _save_results(self, results: Dict, output_path: Path):
        """Save results to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logging.info(f"\n[SUCCESS] Results saved to: {output_path}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        logging.info(
            "Usage: python pdf_processor.py <pdf_folder> [output.json]")
        logging.info("\nExample:")
        logging.info("  python pdf_processor.py invoices/ extracted_data.json")
        sys.exit(1)

    input_folder = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'pdf_extracted.json'

    processor = PDFInvoiceProcessor()
    results = processor.process_folder(Path(input_folder), Path(output_file))

    return 0 if results['metadata']['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
