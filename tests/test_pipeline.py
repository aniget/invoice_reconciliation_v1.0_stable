"""
tests/test_pipeline.py

Baseline test suite for the pre-Phase 1 refactor.
Covers the new modules without requiring real EVD/PDF files.

Run with:
    pytest tests/ -v
"""

import pytest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.exceptions import (
    EVDExtractionError,
    PDFExtractionError,
    ReconciliationJobError,
)


# ─────────────────────────────────────────────────────────────────────────
# config.py
# ─────────────────────────────────────────────────────────────────────────

class TestSettings:
    def test_defaults_are_sane(self):
        from config import settings
        assert settings.DEFAULT_TENANT_ID == "default_tenant"
        assert settings.AMOUNT_TOLERANCE_EUR == Decimal("0.01")
        assert settings.MAX_UPLOAD_SIZE_MB == 50
        assert settings.SERVER_PORT == 7860

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_TENANT_ID", "acme_corp")
        monkeypatch.setenv("SERVER_PORT", "8080")
        from config import Settings
        s = Settings()
        assert s.DEFAULT_TENANT_ID == "acme_corp"
        assert s.SERVER_PORT == 8080

    def test_templates_dir_is_path(self):
        from config import settings
        assert isinstance(settings.TEMPLATES_DIR, Path)

    def test_max_upload_size_bytes(self):
        from config import settings
        assert settings.MAX_UPLOAD_SIZE_BYTES == settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ─────────────────────────────────────────────────────────────────────────
# core/exceptions.py
# ─────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_all_inherit_from_base(self):
        from core.exceptions import (
            ReconciliationError,
            UploadValidationError,
            NoFilesError,
            EVDExtractionError,
            PDFExtractionError,
            TemplateNotFoundError,
            ReconciliationJobError,
            ReportGenerationError,
        )
        for exc_class in [
            UploadValidationError, NoFilesError, EVDExtractionError,
            PDFExtractionError, TemplateNotFoundError,
            ReconciliationJobError, ReportGenerationError,
        ]:
            assert issubclass(exc_class, ReconciliationError)

    def test_upload_validation_error_carries_filename(self):
        from core.exceptions import UploadValidationError
        exc = UploadValidationError("bad file", filename="invoice.txt")
        assert exc.filename == "invoice.txt"

    def test_template_not_found_message(self):
        from core.exceptions import TemplateNotFoundError
        exc = TemplateNotFoundError(vendor="acme", tenant_id="t1")
        assert "acme" in str(exc)
        assert "t1" in str(exc)

    def test_evd_extraction_error_wraps_cause(self):
        from core.exceptions import EVDExtractionError
        cause = ValueError("openpyxl error")
        exc = EVDExtractionError("failed", filename="evd.xlsx", cause=cause)
        assert exc.cause is cause
        assert exc.filename == "evd.xlsx"


# ─────────────────────────────────────────────────────────────────────────
# core/validation.py
# ─────────────────────────────────────────────────────────────────────────

class TestValidation:
    """Validation tests use mock Gradio file objects (just need a .name attr)."""

    def _make_file(self, name: str, size_bytes: int = 1024, tmp_path=None):
        """Create a real temp file so stat() works."""
        path = tmp_path / name if tmp_path else Path(f"/tmp/{name}")
        path.write_bytes(b"x" * size_bytes)
        mock = MagicMock()
        mock.name = str(path)
        return mock

    def test_valid_evd_files_accepted(self, tmp_path):
        from core.validation import validate_evd_files
        files = [self._make_file("data.xlsx", tmp_path=tmp_path)]
        result = validate_evd_files(files)
        assert len(result) == 1
        assert result[0].suffix == ".xlsx"

    def test_valid_pdf_files_accepted(self, tmp_path):
        from core.validation import validate_pdf_files
        files = [self._make_file("invoice.pdf", tmp_path=tmp_path)]
        result = validate_pdf_files(files)
        assert len(result) == 1

    def test_no_evd_files_raises(self):
        from core.exceptions import NoFilesError
        from core.validation import validate_evd_files
        with pytest.raises(NoFilesError):
            validate_evd_files([])

    def test_no_pdf_files_raises(self):
        from core.exceptions import NoFilesError
        from core.validation import validate_pdf_files
        with pytest.raises(NoFilesError):
            validate_pdf_files(None)

    def test_wrong_extension_evd_raises(self, tmp_path):
        from core.exceptions import UploadValidationError
        from core.validation import validate_evd_files
        f = self._make_file("data.csv", tmp_path=tmp_path)
        with pytest.raises(UploadValidationError) as exc_info:
            validate_evd_files([f])
        assert "data.csv" in str(exc_info.value)

    def test_wrong_extension_pdf_raises(self, tmp_path):
        from core.exceptions import UploadValidationError
        from core.validation import validate_pdf_files
        f = self._make_file("invoice.docx", tmp_path=tmp_path)
        with pytest.raises(UploadValidationError):
            validate_pdf_files([f])

    def test_oversized_file_raises(self, tmp_path, monkeypatch):
        from core.exceptions import UploadValidationError
        from core.validation import validate_evd_files
        import config
        monkeypatch.setattr(config.settings.__class__, "MAX_UPLOAD_SIZE_BYTES",
                            property(lambda self: 10))  # 10 bytes limit
        f = self._make_file("big.xlsx", size_bytes=100, tmp_path=tmp_path)
        with pytest.raises(UploadValidationError) as exc_info:
            validate_evd_files([f])
        assert "exceeds" in str(exc_info.value)

    def test_none_entries_filtered(self, tmp_path):
        """Gradio sometimes injects None into the file list."""
        from core.validation import validate_evd_files
        real_file = self._make_file("data.xlsx", tmp_path=tmp_path)
        result = validate_evd_files([None, real_file, None])
        assert len(result) == 1

    def test_xlsm_accepted_as_evd(self, tmp_path):
        from core.validation import validate_evd_files
        f = self._make_file("macro_file.xlsm", tmp_path=tmp_path)
        result = validate_evd_files([f])
        assert len(result) == 1


# ─────────────────────────────────────────────────────────────────────────
# pdf_extraction_project/template_registry.py
# ─────────────────────────────────────────────────────────────────────────

class TestTemplateRegistry:
    def test_list_templates_and_get_all_templates_are_equivalent(self, tmp_path):
        from pdf_extraction_project.template_registry import TemplateRegistry
        reg = TemplateRegistry(tmp_path)
        # Save a template
        reg.save({"vendor": "TestVendor", "fields": []}, tenant_id="t1")
        via_list = reg.list_templates("t1")
        via_get_all = reg.get_all_templates("t1")
        assert via_list == via_get_all

    def test_save_and_get_roundtrip(self, tmp_path):
        from pdf_extraction_project.template_registry import TemplateRegistry
        reg = TemplateRegistry(tmp_path)
        template = {"vendor": "acme", "fields": [{"name": "invoice_number"}]}
        reg.save(template, tenant_id="t1")
        loaded = reg.get("acme", tenant_id="t1")
        assert loaded == template

    def test_get_missing_returns_none(self, tmp_path):
        from pdf_extraction_project.template_registry import TemplateRegistry
        reg = TemplateRegistry(tmp_path)
        assert reg.get("nonexistent", tenant_id="t1") is None

    def test_tenant_isolation(self, tmp_path):
        """Templates saved for one tenant must not appear for another."""
        from pdf_extraction_project.template_registry import TemplateRegistry
        reg = TemplateRegistry(tmp_path)
        reg.save({"vendor": "acme"}, tenant_id="tenant_a")
        assert reg.get("acme", tenant_id="tenant_b") is None
        assert reg.get("acme", tenant_id="tenant_a") is not None

    def test_delete_template(self, tmp_path):
        from pdf_extraction_project.template_registry import TemplateRegistry
        reg = TemplateRegistry(tmp_path)
        reg.save({"vendor": "acme"}, tenant_id="t1")
        assert reg.delete("acme", "t1") is True
        assert reg.get("acme", "t1") is None
        assert reg.delete("acme", "t1") is False  # already gone

    def test_list_template_files_returns_paths(self, tmp_path):
        from pdf_extraction_project.template_registry import TemplateRegistry
        reg = TemplateRegistry(tmp_path)
        reg.save({"vendor": "acme"}, tenant_id="t1")
        files = reg.list_template_files("t1")
        assert len(files) == 1
        assert files[0].suffix == ".json"


# ─────────────────────────────────────────────────────────────────────────
# core/pipeline.py — unit tests (mocked extractors)
# ─────────────────────────────────────────────────────────────────────────

MOCK_EVD_DATA = {
    "metadata": {"total_invoices": 2, "total_amount_eur": 500.0,
                 "files_processed": 1, "files_failed": 0,
                 "total_vendors": 1, "files": {}},
    "by_vendor": {
        "VIVACOM": {"vendor_name": "VIVACOM", "invoice_count": 2,
                    "total_amount": 500.0, "invoices": [
                        {"invoice_number": "INV-001", "vendor_normalized": "VIVACOM",
                         "vendor": "Vivacom", "total_amount_eur": 250.0,
                         "currency": "EUR", "invoice_date": "2024-01-01",
                         "net_amount_eur": 208.33, "vat_amount_eur": 41.67},
                        {"invoice_number": "INV-002", "vendor_normalized": "VIVACOM",
                         "vendor": "Vivacom", "total_amount_eur": 250.0,
                         "currency": "EUR", "invoice_date": "2024-01-02",
                         "net_amount_eur": 208.33, "vat_amount_eur": 41.67},
                    ]}
    },
    "by_invoice_number": {},
    "all_invoices": [
        {"invoice_number": "INV-001", "vendor_normalized": "VIVACOM",
         "vendor": "Vivacom", "total_amount_eur": 250.0,
         "currency": "EUR", "invoice_date": "2024-01-01",
         "net_amount_eur": 208.33, "vat_amount_eur": 41.67},
        {"invoice_number": "INV-002", "vendor_normalized": "VIVACOM",
         "vendor": "Vivacom", "total_amount_eur": 250.0,
         "currency": "EUR", "invoice_date": "2024-01-02",
         "net_amount_eur": 208.33, "vat_amount_eur": 41.67},
    ],
}

MOCK_PDF_DATA = {
    "metadata": {"total_invoices": 2, "successful": 2, "failed": 0,
                 "tenant_id": "default_tenant"},
    "by_vendor": {
        "VIVACOM": {"vendor_name": "VIVACOM", "invoice_count": 2,
                    "total_amount": 500.0, "invoices": [
                        {"invoice_number": "INV-001", "vendor_normalized": "VIVACOM",
                         "vendor": "Vivacom", "total_amount_eur": 250.0,
                         "currency": "EUR", "invoice_date": "2024-01-01",
                         "filename": "inv001.pdf", "status": "success"},
                        {"invoice_number": "INV-002", "vendor_normalized": "VIVACOM",
                         "vendor": "Vivacom", "total_amount_eur": 250.0,
                         "currency": "EUR", "invoice_date": "2024-01-02",
                         "filename": "inv002.pdf", "status": "success"},
                    ]}
    },
    "by_invoice_number": {},
    "all_invoices": [
        {"invoice_number": "INV-001", "vendor_normalized": "VIVACOM",
         "vendor": "Vivacom", "total_amount_eur": 250.0,
         "currency": "EUR", "filename": "inv001.pdf", "status": "success"},
        {"invoice_number": "INV-002", "vendor_normalized": "VIVACOM",
         "vendor": "Vivacom", "total_amount_eur": 250.0,
         "currency": "EUR", "filename": "inv002.pdf", "status": "success"},
    ],
}


class TestPipeline:
    """
    Pipeline tests mock the three heavy lifting components so we test
    the orchestration logic without needing real files.
    """

    def _make_dummy_file(self, tmp_path: Path, name: str) -> Path:
        p = tmp_path / name
        p.write_bytes(b"dummy content")
        return p

    @patch("core.pipeline._run_evd_extraction", return_value=MOCK_EVD_DATA)
    @patch("core.pipeline._run_pdf_extraction", return_value=MOCK_PDF_DATA)
    @patch("core.pipeline._run_reconciliation")
    def test_successful_run_returns_result(
        self, mock_recon, mock_pdf, mock_evd, tmp_path
    ):
        from core.pipeline import run_pipeline, PipelineResult

        # _run_reconciliation writes report_path — create a dummy file
        def fake_reconciliation(evd_data, pdf_data, report_path, session_id):
            report_path.write_bytes(b"fake excel")
        mock_recon.side_effect = fake_reconciliation

        evd_files = [self._make_dummy_file(tmp_path, "evd.xlsx")]
        pdf_files = [self._make_dummy_file(tmp_path, "inv.pdf")]

        result = run_pipeline(evd_files, pdf_files, "default_tenant")

        assert isinstance(result, PipelineResult)
        assert result.tenant_id == "default_tenant"
        assert result.total_evd_invoices == 2
        assert result.total_pdf_invoices == 2
        assert result.duration_seconds >= 0
        mock_evd.assert_called_once()
        mock_pdf.assert_called_once()
        mock_recon.assert_called_once()

    @patch("core.pipeline._run_evd_extraction",
           side_effect=EVDExtractionError(
               "EVD extraction failed: openpyxl: corrupt workbook"
           ))
    def test_evd_failure_raises_typed_exception(self, mock_evd, tmp_path):
        from core.pipeline import run_pipeline

        evd_files = [self._make_dummy_file(tmp_path, "bad.xlsx")]
        pdf_files = [self._make_dummy_file(tmp_path, "inv.pdf")]

        with pytest.raises(EVDExtractionError):
            run_pipeline(evd_files, pdf_files, "t1")

    @patch("core.pipeline._run_evd_extraction", return_value=MOCK_EVD_DATA)
    @patch("core.pipeline._run_pdf_extraction",
           side_effect=PDFExtractionError(
               "PDF extraction failed: pdfplumber: encrypted PDF"
           ))
    def test_pdf_failure_raises_typed_exception(
        self, mock_pdf, mock_evd, tmp_path
    ):
        from core.pipeline import run_pipeline

        evd_files = [self._make_dummy_file(tmp_path, "evd.xlsx")]
        pdf_files = [self._make_dummy_file(tmp_path, "locked.pdf")]

        with pytest.raises(PDFExtractionError):
            run_pipeline(evd_files, pdf_files, "t1")

    @patch("core.pipeline._run_evd_extraction", return_value=MOCK_EVD_DATA)
    @patch("core.pipeline._run_pdf_extraction", return_value=MOCK_PDF_DATA)
    @patch("core.pipeline._run_reconciliation",
           side_effect=ReconciliationJobError(
               "Reconciliation/report step failed: openpyxl write error"
           ))
    def test_reconciliation_failure_raises_typed_exception(
        self, mock_recon, mock_pdf, mock_evd, tmp_path
    ):
        from core.pipeline import run_pipeline

        evd_files = [self._make_dummy_file(tmp_path, "evd.xlsx")]
        pdf_files = [self._make_dummy_file(tmp_path, "inv.pdf")]

        with pytest.raises(ReconciliationJobError):
            run_pipeline(evd_files, pdf_files, "t1")

    @patch("core.pipeline._run_evd_extraction", return_value=MOCK_EVD_DATA)
    @patch("core.pipeline._run_pdf_extraction", return_value=MOCK_PDF_DATA)
    @patch("core.pipeline._run_reconciliation")
    def test_tenant_id_propagated(
        self, mock_recon, mock_pdf, mock_evd, tmp_path
    ):
        from core.pipeline import run_pipeline

        def fake_reconciliation(evd_data, pdf_data, report_path, session_id):
            report_path.write_bytes(b"x")
        mock_recon.side_effect = fake_reconciliation

        evd_files = [self._make_dummy_file(tmp_path, "evd.xlsx")]
        pdf_files = [self._make_dummy_file(tmp_path, "inv.pdf")]

        result = run_pipeline(evd_files, pdf_files, "acme_corp")
        assert result.tenant_id == "acme_corp"

        # PDF extractor should have received the tenant_id
        _, kwargs = mock_pdf.call_args
        assert kwargs.get(
            "tenant_id") == "acme_corp" or mock_pdf.call_args[0][1] == "acme_corp"
