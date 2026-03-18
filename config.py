"""
config.py — Centralised application configuration.

All tuneable values live here.  Nothing in the codebase should contain a
magic string or number that might need to change between environments.

Reads from environment variables so that the same code runs on a developer
laptop, a staging VM, or a production container without any file edits.

Usage:
    from config import settings
    print(settings.TEMPLATES_DIR)
    print(settings.DEFAULT_TENANT_ID)
"""

import os
from pathlib import Path
from decimal import Decimal


class Settings:
    """
    Application settings resolved from environment variables.

    Every attribute has a safe default so the app starts out-of-the-box
    with no configuration required — and can be overridden for production
    by setting the corresponding environment variable.
    """

    # ------------------------------------------------------------------ #
    # Paths                                                                #
    # ------------------------------------------------------------------ #

    @property
    def BASE_DIR(self) -> Path:
        """Root directory of the project (where app.py lives)."""
        return Path(os.environ.get("APP_BASE_DIR", Path(__file__).parent))

    @property
    def TEMPLATES_DIR(self) -> Path:
        """
        Directory that holds per-tenant template JSON files.
        Structure: <TEMPLATES_DIR>/<tenant_id>/<vendor>.json
        """
        default = self.BASE_DIR / "pdf_extraction_project" / "templates"
        return Path(os.environ.get("TEMPLATES_DIR", default))

    @property
    def TEMP_DIR(self) -> Path:
        """
        Root for per-session working directories.
        Each job gets its own sub-folder: <TEMP_DIR>/<session_id>/
        """
        default = Path("/tmp") / "invoice_reconciliation"
        return Path(os.environ.get("TEMP_DIR", default))

    @property
    def LOG_FILE(self) -> Path:
        """Path for the application log file."""
        default = self.BASE_DIR / "app.log"
        return Path(os.environ.get("LOG_FILE", default))

    # ------------------------------------------------------------------ #
    # Tenancy                                                              #
    # ------------------------------------------------------------------ #

    @property
    def DEFAULT_TENANT_ID(self) -> str:
        """
        Tenant used when no tenant is specified.
        In Phase 1 this will be replaced by the value from the auth JWT.
        """
        return os.environ.get("DEFAULT_TENANT_ID", "default_tenant")

    # ------------------------------------------------------------------ #
    # Reconciliation rules                                                 #
    # ------------------------------------------------------------------ #

    @property
    def AMOUNT_TOLERANCE_EUR(self) -> Decimal:
        """
        Maximum acceptable difference (€) between EVD and PDF amounts
        before a match is flagged as a mismatch.
        """
        raw = os.environ.get("AMOUNT_TOLERANCE_EUR", "0.01")
        return Decimal(raw)

    # ------------------------------------------------------------------ #
    # Upload validation                                                    #
    # ------------------------------------------------------------------ #

    @property
    def MAX_UPLOAD_SIZE_MB(self) -> int:
        """Maximum size (MB) for a single uploaded file."""
        return int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50"))

    @property
    def MAX_UPLOAD_SIZE_BYTES(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def ALLOWED_EVD_EXTENSIONS(self) -> tuple:
        return (".xlsx", ".xlsm", ".xls")

    @property
    def ALLOWED_PDF_EXTENSIONS(self) -> tuple:
        return (".pdf",)

    @property
    def MAX_EVD_FILES(self) -> int:
        """Maximum number of EVD files per job."""
        return int(os.environ.get("MAX_EVD_FILES", "20"))

    @property
    def MAX_PDF_FILES(self) -> int:
        """Maximum number of PDF files per job."""
        return int(os.environ.get("MAX_PDF_FILES", "100"))

    # ------------------------------------------------------------------ #
    # Web server                                                           #
    # ------------------------------------------------------------------ #

    @property
    def SERVER_HOST(self) -> str:
        return os.environ.get("SERVER_HOST", "0.0.0.0")

    @property
    def SERVER_PORT(self) -> int:
        return int(os.environ.get("SERVER_PORT", "7860"))

    @property
    def DEBUG(self) -> bool:
        return os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes")

    # ------------------------------------------------------------------ #
    # Logging                                                              #
    # ------------------------------------------------------------------ #

    @property
    def LOG_LEVEL(self) -> str:
        return os.environ.get("LOG_LEVEL", "INFO").upper()


# Module-level singleton — import this everywhere.
settings = Settings()
