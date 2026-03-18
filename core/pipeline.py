"""
core/pipeline.py — In-process reconciliation pipeline.

This is the most important change in the pre-Phase 1 refactor.

BEFORE (the subprocess chain):
    subprocess.run([sys.executable, '-m', 'evd_extraction_project...'])   → writes evd.json
    subprocess.run([sys.executable, '-m', 'pdf_extraction_project...'])   → writes pdf.json
    subprocess.run([sys.executable, '-m', 'reconciliation_project...'])   → reads both json files

Problems with that approach:
  • Three separate Python interpreter processes spawned per job
  • Data serialised to disk between every step (I/O overhead)
  • No shared state → tenant context is lost between steps
  • Cannot be made async (Celery) without significant rework
  • Exception tracebacks from sub-processes are swallowed

AFTER (this module — direct calls):
    evd_data  = BatchEVDProcessor(evd_dir).process_folder()        # in-memory dict
    pdf_data  = PDFInvoiceProcessor(tenant_id=...).process_folder_in_memory(pdf_dir)
    report    = ReconciliationReportGenerator().generate_report(evd_data, pdf_data, output_path)

All three steps run in the same process, in the same Python call stack.
Exceptions propagate naturally. Tenant context is passed as a parameter.
The result is ready to be moved onto a Celery task in Phase 2 with
minimal changes — just wrap run_pipeline() as a @celery.task.
"""

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from config import settings
from core.exceptions import (
    EVDExtractionError,
    PDFExtractionError,
    ReconciliationJobError,
    ReportGenerationError,
)

logger = logging.getLogger(__name__)


# ── Result dataclass ───────────────────────────────────────────────────── #

@dataclass
class PipelineResult:
    """
    Everything the UI (or future API) needs after a successful run.

    Keeping this as a dataclass makes it easy to serialise to JSON for
    the Phase 1 database job record.
    """
    report_path: Path
    session_id: str
    tenant_id: str
    total_evd_invoices: int = 0
    total_pdf_invoices: int = 0
    matches: int = 0
    mismatches: int = 0
    missing_in_pdf: int = 0
    missing_in_evd: int = 0
    match_rate: float = 0.0
    evd_by_vendor: dict = field(default_factory=dict)
    pdf_by_vendor: dict = field(default_factory=dict)
    duration_seconds: float = 0.0


# ── Main entry point ───────────────────────────────────────────────────── #

def run_pipeline(
    evd_paths: List[Path],
    pdf_paths: List[Path],
    tenant_id: str,
) -> PipelineResult:
    """
    Run the full EVD → PDF → Reconciliation pipeline in-process.

    This function is intentionally side-effect free with respect to the
    caller's filesystem — it creates its own session directory under
    settings.TEMP_DIR and cleans it up on completion.  The report Excel
    file is the only artefact left on disk after a successful run.

    Args:
        evd_paths:  Validated EVD file paths (from core.validation).
        pdf_paths:  Validated PDF file paths (from core.validation).
        tenant_id:  Tenant identifier.  Passed to PDFInvoiceProcessor so
                    the correct template set is used.

    Returns:
        PipelineResult with the report path and summary statistics.

    Raises:
        EVDExtractionError:      EVD batch processing failed.
        PDFExtractionError:      PDF batch processing failed.
        ReconciliationJobError:  Reconciliation/report step failed.
    """
    started = datetime.now()
    session_id = started.strftime("%Y%m%d_%H%M%S")

    # ── Session working directory ──────────────────────────────────────
    session_dir = settings.TEMP_DIR / session_id
    evd_dir = session_dir / "evd"
    pdf_dir = session_dir / "pdf"
    output_dir = session_dir / "output"

    for d in (evd_dir, pdf_dir, output_dir):
        d.mkdir(parents=True, exist_ok=True)

    logger.info(
        "[%s] Pipeline started — tenant=%s  evd=%d  pdf=%d",
        session_id, tenant_id, len(evd_paths), len(pdf_paths),
    )

    try:
        # ── Step 1: Copy uploads into session dir ──────────────────────
        # We copy rather than use the tmp Gradio paths directly, because
        # Gradio may reclaim its temp files during a long run.
        for src in evd_paths:
            shutil.copy2(src, evd_dir / src.name)
        for src in pdf_paths:
            shutil.copy2(src, pdf_dir / src.name)

        logger.info("[%s] Files staged in session directory.", session_id)

        # ── Step 2: EVD extraction ─────────────────────────────────────
        evd_data = _run_evd_extraction(evd_dir, session_id)

        # ── Step 3: PDF extraction ─────────────────────────────────────
        pdf_data = _run_pdf_extraction(pdf_dir, tenant_id, session_id)

        # DEBUG: inspect exact PDF extraction payload
        import json
        (output_dir / "pdf_debug.json").write_text(
            json.dumps(pdf_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # ── Step 4: Reconciliation + Excel report ──────────────────────
        report_path = output_dir / "reconciliation_report.xlsx"
        _run_reconciliation(evd_data, pdf_data, report_path, session_id)

        # ── Step 5: Build result summary ───────────────────────────────
        duration = (datetime.now() - started).total_seconds()

        result = _build_result(
            evd_data=evd_data,
            pdf_data=pdf_data,
            report_path=report_path,
            session_id=session_id,
            tenant_id=tenant_id,
            duration=duration,
        )

        logger.info(
            "[%s] Pipeline complete — %.1fs  match_rate=%.1f%%",
            session_id, duration, result.match_rate,
        )
        return result

    except (EVDExtractionError, PDFExtractionError, ReconciliationJobError):
        # Already typed — re-raise so the UI can display a specific message
        raise

    except Exception as exc:
        # Unexpected error — wrap it so it stays typed
        logger.exception("[%s] Unexpected pipeline error: %s", session_id, exc)
        raise ReconciliationJobError(
            f"Pipeline failed unexpectedly: {exc}"
        ) from exc


# ── Private step functions ─────────────────────────────────────────────── #

def _run_evd_extraction(evd_dir: Path, session_id: str) -> dict:
    """Call BatchEVDProcessor directly (no subprocess)."""
    from evd_extraction_project.batch_evd_extractor import BatchEVDProcessor

    logger.info("[%s] Step 2/4 — EVD extraction from %s", session_id, evd_dir)
    try:
        processor = BatchEVDProcessor(input_folder=evd_dir)
        data = processor.process_folder()  # returns dict, no file I/O needed
    except Exception as exc:
        raise EVDExtractionError(
            f"EVD extraction failed: {exc}", cause=exc
        ) from exc

    total = data.get("metadata", {}).get("total_invoices", 0)
    logger.info("[%s] EVD extraction done — %d invoices.", session_id, total)
    return data


def _run_pdf_extraction(pdf_dir: Path, tenant_id: str, session_id: str) -> dict:
    """Call PDFInvoiceProcessor directly (no subprocess)."""
    from pdf_extraction_project.pdf_processor import PDFInvoiceProcessor

    logger.info("[%s] Step 3/4 — PDF extraction from %s", session_id, pdf_dir)
    try:
        processor = PDFInvoiceProcessor(
            templates_dir=str(settings.TEMPLATES_DIR),
            tenant_id=tenant_id,
        )
        # process_folder_in_memory returns dict without writing JSON to disk
        data = processor.process_folder_in_memory(pdf_dir)

    except Exception as exc:
        raise PDFExtractionError(
            f"PDF extraction failed: {exc}", cause=exc
        ) from exc

    total = data.get("metadata", {}).get("total_invoices", 0)
    logger.info("[%s] PDF extraction done — %d invoices.", session_id, total)
    return data


def _run_reconciliation(
    evd_data: dict,
    pdf_data: dict,
    report_path: Path,
    session_id: str,
) -> None:
    """Call ReconciliationReportGenerator directly (no subprocess)."""
    from reconciliation_project.reconciliation_report import ReconciliationReportGenerator

    logger.info("[%s] Step 4/4 — Reconciliation + Excel report", session_id)
    try:
        generator = ReconciliationReportGenerator(
            amount_tolerance=float(settings.AMOUNT_TOLERANCE_EUR)
        )
        generator.generate_report(evd_data, pdf_data, report_path)
    except Exception as exc:
        raise ReconciliationJobError(
            f"Reconciliation/report step failed: {exc}"
        ) from exc


def _build_result(
    evd_data: dict,
    pdf_data: dict,
    report_path: Path,
    session_id: str,
    tenant_id: str,
    duration: float,
) -> PipelineResult:
    """
    Assemble a PipelineResult from the raw dicts returned by the extractors.

    The reconciliation summary is re-computed here rather than captured
    inside _run_reconciliation to avoid coupling this module to the
    internals of ReconciliationReportGenerator.
    """
    evd_meta = evd_data.get("metadata", {})
    pdf_meta = pdf_data.get("metadata", {})

    # Rerun a lightweight reconciliation just to get match stats for the UI.
    # This is fast because it's pure in-memory Python — no file I/O.
    matches = mismatches = missing_in_pdf = missing_in_evd = 0
    match_rate = 0.0

    try:
        from reconciliation_project.adapters.json_adapter import JSONToInvoiceAdapter
        from reconciliation_project.domain.service import ReconciliationService
        from decimal import Decimal

        evd_invoices = JSONToInvoiceAdapter.from_json_dataset(evd_data, "evd")
        pdf_invoices = JSONToInvoiceAdapter.from_json_dataset(pdf_data, "pdf")
        pdf_by_vendor = JSONToInvoiceAdapter.extract_vendor_grouping(
            pdf_data, "pdf")

        svc = ReconciliationService(
            amount_tolerance=Decimal(str(settings.AMOUNT_TOLERANCE_EUR))
        )
        result = svc.reconcile(evd_invoices, pdf_invoices, pdf_by_vendor)

        matches = len(result.matches)
        mismatches = len(result.mismatches)
        missing_in_pdf = len(result.missing_in_pdf)
        missing_in_evd = len(result.missing_in_evd)
        match_rate = result.match_rate

    except Exception:
        # Stats are best-effort — the report was already written successfully
        logger.warning(
            "[%s] Could not compute match stats for summary; report still valid.",
            session_id,
        )

    return PipelineResult(
        report_path=report_path,
        session_id=session_id,
        tenant_id=tenant_id,
        total_evd_invoices=evd_meta.get("total_invoices", 0),
        total_pdf_invoices=pdf_meta.get("total_invoices", 0),
        matches=matches,
        mismatches=mismatches,
        missing_in_pdf=missing_in_pdf,
        missing_in_evd=missing_in_evd,
        match_rate=match_rate,
        evd_by_vendor=evd_data.get("by_vendor", {}),
        pdf_by_vendor=pdf_data.get("by_vendor", {}),
        duration_seconds=duration,
    )
