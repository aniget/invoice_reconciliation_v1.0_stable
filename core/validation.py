"""
core/validation.py — Upload and input validation.

Centralises all "is this input safe to process?" logic.
The UI calls these functions before touching any file.
The Phase 1 API layer will call the same functions from request handlers.

Raises typed exceptions from core.exceptions so callers always know
exactly what went wrong without inspecting string messages.
"""

import logging
from pathlib import Path
from typing import List

from core.exceptions import (
    NoFilesError,
    UploadValidationError,
)
from config import settings

logger = logging.getLogger(__name__)


def validate_evd_files(files: List) -> List[Path]:
    """
    Validate a batch of EVD file objects from the Gradio upload widget.

    Checks:
      1. At least one file provided
      2. File count does not exceed MAX_EVD_FILES
      3. Each file has an allowed extension
      4. Each file does not exceed MAX_UPLOAD_SIZE_BYTES

    Args:
        files: List of Gradio file objects (each has a .name attribute).

    Returns:
        List of validated Path objects, ready for processing.

    Raises:
        NoFilesError:           No files provided.
        UploadValidationError:  A file fails extension or size check.
    """
    if not files:
        raise NoFilesError("No EVD files were uploaded.")

    # Filter out any None entries Gradio sometimes injects
    files = [f for f in files if f is not None]

    if not files:
        raise NoFilesError("No EVD files were uploaded.")

    if len(files) > settings.MAX_EVD_FILES:
        raise UploadValidationError(
            f"Too many EVD files: {len(files)} uploaded, maximum is {settings.MAX_EVD_FILES}."
        )

    validated: List[Path] = []
    for f in files:
        path = Path(f.name)
        _check_extension(path, settings.ALLOWED_EVD_EXTENSIONS)
        _check_size(path, settings.MAX_UPLOAD_SIZE_BYTES)
        validated.append(path)

    logger.info("EVD validation passed — %d file(s) accepted.", len(validated))
    return validated


def validate_pdf_files(files: List) -> List[Path]:
    """
    Validate a batch of PDF file objects from the Gradio upload widget.

    Same logic as validate_evd_files but uses PDF-specific limits.

    Args:
        files: List of Gradio file objects.

    Returns:
        List of validated Path objects.

    Raises:
        NoFilesError:           No files provided.
        UploadValidationError:  A file fails extension or size check.
    """
    if not files:
        raise NoFilesError("No PDF files were uploaded.")

    files = [f for f in files if f is not None]

    if not files:
        raise NoFilesError("No PDF files were uploaded.")

    if len(files) > settings.MAX_PDF_FILES:
        raise UploadValidationError(
            f"Too many PDF files: {len(files)} uploaded, maximum is {settings.MAX_PDF_FILES}."
        )

    validated: List[Path] = []
    for f in files:
        path = Path(f.name)
        _check_extension(path, settings.ALLOWED_PDF_EXTENSIONS)
        _check_size(path, settings.MAX_UPLOAD_SIZE_BYTES)
        validated.append(path)

    logger.info("PDF validation passed — %d file(s) accepted.", len(validated))
    return validated


# ── Private helpers ────────────────────────────────────────────────────── #

def _check_extension(path: Path, allowed: tuple) -> None:
    """Raise UploadValidationError if the file extension is not in `allowed`."""
    if path.suffix.lower() not in allowed:
        raise UploadValidationError(
            f"File '{path.name}' has extension '{path.suffix}' which is not allowed. "
            f"Accepted extensions: {', '.join(allowed)}",
            filename=path.name,
        )


def _check_size(path: Path, max_bytes: int) -> None:
    """Raise UploadValidationError if the file exceeds the size limit."""
    try:
        size = path.stat().st_size
    except OSError:
        # If we cannot stat it, let the processor handle the failure
        return

    if size > max_bytes:
        mb = size / (1024 * 1024)
        limit_mb = max_bytes / (1024 * 1024)
        raise UploadValidationError(
            f"File '{path.name}' is {mb:.1f} MB, which exceeds the {limit_mb:.0f} MB limit.",
            filename=path.name,
        )
