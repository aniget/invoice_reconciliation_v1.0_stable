"""
pdf_extraction_project/pdf_processor.py

Changes from original:
  1. BUG FIX: detect_vendor() called self.registry.list_templates() which
     does not exist on TemplateRegistry.  The correct method is
     _get_tenant_dir() + glob.  Fixed to use registry._get_tenant_dir().

  2. NEW METHOD: process_folder_in_memory(input_dir) — returns the result
     dict directly without writing a JSON file.  Called by core.pipeline
     instead of the old subprocess approach.

  3. process_folder() kept for backward compatibility (CLI / run_reconciliation.py).

  4. Removed hardcoded default templates_dir string.  Now uses settings.TEMPLATES_DIR
     via the default parameter so it still works with zero config.

  5. Removed the module-level logging.basicConfig() call.
     Logging is configured once by core.logging_config.setup_logging().
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
import sys

import pdfplumber

from pdf_extraction_project.template_registry import TemplateRegistry
from pdf_extraction_project.template_engine import TemplateExtractor

logger = logging.getLogger(__name__)


class PDFInvoiceProcessor:
    """
    PDF invoice processor with multi-tenant template support and OCR fallback.

    Supports two output modes:
      - process_folder()            writes result to a JSON file (CLI / legacy)
      - process_folder_in_memory()  returns dict directly (pipeline / API)
    """

    def __init__(
        self,
        templates_dir: str = None,
        tenant_id: str = "default_tenant",
    ):
        # Defer the import so config is not required at module import time
        if templates_dir is None:
            from config import settings
            templates_dir = str(settings.TEMPLATES_DIR)

        self.tenant_id = tenant_id
        self.registry = TemplateRegistry(Path(templates_dir))
        self.ocr_enabled = self._check_ocr_availability()

        logger.debug(
            "PDFInvoiceProcessor ready — tenant=%s  templates=%s  ocr=%s",
            tenant_id, templates_dir, self.ocr_enabled,
        )

    # ── Text extraction ────────────────────────────────────────────────── #

    def _check_ocr_availability(self) -> bool:
        """Return True if Tesseract OCR is installed and accessible."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from a PDF.  Falls back to OCR for scanned documents.
        Returns empty string on failure (caller decides what to do).
        """
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text(x_tolerance=1.0)
                    if extracted:
                        text += extracted + "\n"
        except Exception as exc:
            logger.error("Failed to read %s: %s", pdf_path.name, exc)

        if len(text.strip()) < 50 and self.ocr_enabled:
            logger.info(
                "Insufficient text in %s — attempting OCR.", pdf_path.name
            )
            text = self._extract_text_ocr(pdf_path)

        return text

    def _extract_text_ocr(self, pdf_path: Path) -> str:
        """OCR extraction for scanned invoices."""
        import pytesseract
        from pdf2image import convert_from_path

        text = ""
        try:
            images = convert_from_path(pdf_path, dpi=300)
            for image in images:
                text += pytesseract.image_to_string(
                    image, lang="bul+eng", config="--psm 6"
                ) + "\n"
        except Exception as exc:
            logger.error("OCR failed for %s: %s", pdf_path.name, exc)
        return text

    # ── Vendor detection ───────────────────────────────────────────────── #

    def detect_vendor(self, text: str) -> dict:
        """
        Scan all templates for the current tenant and find a match.

        BUG FIX: original code called self.registry.list_templates() which
        does not exist.  Corrected to use registry._get_tenant_dir() + glob
        (same pattern the registry uses internally).

        Falls back to the 'generic' template if no specific vendor matches.
        Returns None only if even the generic template is missing.
        """
        tenant_dir = self.registry._get_tenant_dir(self.tenant_id)

        for template_file in sorted(tenant_dir.glob("*.json")):
            if template_file.stem.lower() == "generic":
                continue  # Reserve generic as fallback

            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    template = json.load(f)
            except Exception as exc:
                logger.warning(
                    "Could not load template %s: %s", template_file.name, exc
                )
                continue

            patterns = template.get(
                "detection_patterns", [template.get("vendor")]
            )
            for pattern in patterns:
                if pattern and re.search(pattern, text, re.IGNORECASE):
                    logger.debug(
                        "Vendor matched: %s (template: %s)",
                        template.get("vendor"), template_file.name,
                    )
                    return template

        # Fallback
        generic = self.registry.get("generic", self.tenant_id)
        if generic is None:
            logger.warning(
                "No vendor-specific template matched and no generic template "
                "exists for tenant '%s'.", self.tenant_id
            )
        else:
            logger.debug(
                "Using generic template for tenant '%s'.", self.tenant_id)
        return generic

    # ── Single-file processing ─────────────────────────────────────────── #

    def process_pdf(self, pdf_path: Path) -> dict:
        """
        Process a single PDF invoice: extract text → detect vendor → extract fields.

        Returns a dict with at minimum 'filename' and 'status' keys.
        status == 'success' means all required fields were extracted.
        status == 'failed'  means something went wrong (error key has details).
        """
        text = self.extract_text(pdf_path)

        if not text.strip():
            logger.error("No text extracted from %s.", pdf_path.name)
            return {
                "filename": pdf_path.name,
                "status": "failed",
                "error": "No text could be extracted (scanned PDF with no OCR?)",
            }

        template = self.detect_vendor(text)
        if not template:
            logger.error(
                "No template found for %s (tenant: %s).",
                pdf_path.name, self.tenant_id,
            )
            return {
                "filename": pdf_path.name,
                "status": "failed",
                "error": f"No matching template for tenant '{self.tenant_id}'",
            }

        extractor = TemplateExtractor(template)
        data = extractor.extract(text)
        data["filename"] = pdf_path.name
        data["status"] = "success"
        return data

    # ── Batch processing ───────────────────────────────────────────────── #

    def _collect_pdf_files(self, input_dir: Path) -> list:
        """Return all PDF files in input_dir (case-insensitive extension)."""
        return sorted(
            p for p in input_dir.iterdir()
            if p.suffix.lower() == ".pdf"
        )

    def _build_output_structure(
        self, input_dir: Path, all_invoices: list, successful: int, total: int
    ) -> dict:
        """Assemble the canonical output dict from processed invoices."""
        by_vendor: dict = {}
        by_invoice_number: dict = {}

        for data in all_invoices:
            vendor = data.get("vendor_normalized", "UNKNOWN")
            if vendor not in by_vendor:
                by_vendor[vendor] = {
                    "vendor_name": vendor,
                    "invoice_count": 0,
                    "total_amount": 0.0,
                    "invoices": [],
                }
            by_vendor[vendor]["invoices"].append(data)
            by_vendor[vendor]["invoice_count"] += 1
            by_vendor[vendor]["total_amount"] += float(
                data.get("total_amount_eur") or 0.0
            )

            inv_num = data.get("invoice_number")
            if inv_num:
                by_invoice_number.setdefault(inv_num, []).append(data)

        return {
            "metadata": {
                "tenant_id": self.tenant_id,
                "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_folder": str(input_dir),
                "total_invoices": total,
                "successful": successful,
                "failed": total - successful,
            },
            "by_vendor": by_vendor,
            "by_invoice_number": by_invoice_number,
            "all_invoices": all_invoices,
        }

    def process_folder_in_memory(self, input_dir: Path) -> dict:
        """
        Process all PDFs in input_dir and return the result dict directly.

        NEW METHOD — used by core.pipeline to avoid writing JSON to disk.
        No file I/O beyond reading the PDFs themselves.
        """
        input_dir = Path(input_dir)
        pdf_files = self._collect_pdf_files(input_dir)

        logger.info(
            "Processing %d PDF file(s) from %s (tenant=%s).",
            len(pdf_files), input_dir, self.tenant_id,
        )

        all_invoices = []
        successful = 0

        for pdf_file in pdf_files:
            logger.info("  Processing: %s", pdf_file.name)
            data = self.process_pdf(pdf_file)
            if data.get("status") == "success":
                successful += 1
                all_invoices.append(data)
            else:
                logger.warning(
                    "  Failed: %s — %s", pdf_file.name, data.get("error", "")
                )

        return self._build_output_structure(
            input_dir, all_invoices, successful, len(pdf_files)
        )

    def process_folder(self, input_dir: str, output_file: str) -> dict:
        """
        Batch-process all PDFs and write results to a JSON file.

        Kept for CLI / run_reconciliation.py backward compatibility.
        Internally calls process_folder_in_memory() so the logic is not
        duplicated.
        """
        output_data = self.process_folder_in_memory(Path(input_dir))

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)

        logger.info("PDF results written to %s", output_path)
        return output_data


# ── CLI entry point (unchanged behaviour) ─────────────────────────────── #

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m pdf_extraction_project.pdf_processor "
            "<input_pdf_dir> <output.json> [tenant_id]"
        )
        sys.exit(1)

    input_dir = sys.argv[1]
    output_file = sys.argv[2]
    tenant_id = sys.argv[3] if len(sys.argv) > 3 else "default_tenant"

    processor = PDFInvoiceProcessor(tenant_id=tenant_id)
    processor.process_folder(input_dir, output_file)
