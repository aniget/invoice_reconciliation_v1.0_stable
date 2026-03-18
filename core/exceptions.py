"""
core/exceptions.py — Application-wide exception hierarchy.

Using typed exceptions instead of bare Exception / RuntimeError means:
  - callers can catch exactly what they handle
  - error messages carry structured context (not just a string)
  - logging can distinguish recoverable from fatal errors
  - Phase 1 API layer can map exception types → HTTP status codes cleanly

All application exceptions inherit from ReconciliationError so a single
broad except clause is always available when needed.
"""


class ReconciliationError(Exception):
    """Base class for all application exceptions."""


# ── Upload / input validation ──────────────────────────────────────────── #

class UploadValidationError(ReconciliationError):
    """
    Raised when an uploaded file fails pre-processing validation.

    Examples:
        - Wrong file extension
        - File exceeds size limit
        - File content does not match declared type (Phase 2: magic-byte check)
        - No files provided at all
    """
    def __init__(self, message: str, filename: str = ""):
        self.filename = filename
        super().__init__(message)


class NoFilesError(UploadValidationError):
    """Raised when the user submits a job with zero files on one side."""


# ── Extraction errors ──────────────────────────────────────────────────── #

class EVDExtractionError(ReconciliationError):
    """
    Raised when an EVD Excel file cannot be parsed.

    Wraps the underlying library exception so callers don't need to
    know whether it was openpyxl or something else that failed.
    """
    def __init__(self, message: str, filename: str = "", cause: Exception = None):
        self.filename = filename
        self.cause = cause
        super().__init__(message)


class PDFExtractionError(ReconciliationError):
    """
    Raised when a PDF invoice cannot be processed.

    Could mean: unreadable PDF, no matching vendor template,
    OCR failure on a scanned document, etc.
    """
    def __init__(self, message: str, filename: str = "", cause: Exception = None):
        self.filename = filename
        self.cause = cause
        super().__init__(message)


class NoTextExtractedError(PDFExtractionError):
    """
    Raised when pdfplumber returns empty text AND OCR is not available
    or also returns empty text.
    """


# ── Template errors ────────────────────────────────────────────────────── #

class TemplateNotFoundError(ReconciliationError):
    """
    Raised when no template (including the generic fallback) exists for a
    given vendor + tenant combination.
    """
    def __init__(self, vendor: str, tenant_id: str):
        self.vendor = vendor
        self.tenant_id = tenant_id
        super().__init__(
            f"No template found for vendor '{vendor}' under tenant '{tenant_id}'. "
            f"Create a template via the Template Builder tab."
        )


# ── Reconciliation errors ──────────────────────────────────────────────── #

class ReconciliationJobError(ReconciliationError):
    """
    Raised when the reconciliation step itself fails (as opposed to the
    extraction steps).  This should be rare given the robustness of the
    domain layer, but it is possible with malformed adapter output.
    """


# ── Report generation ──────────────────────────────────────────────────── #

class ReportGenerationError(ReconciliationError):
    """Raised when the Excel report cannot be written to disk."""
    def __init__(self, message: str, output_path: str = "", cause: Exception = None):
        self.output_path = output_path
        self.cause = cause
        super().__init__(message)
