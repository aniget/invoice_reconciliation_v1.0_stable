"""
app.py — Invoice Reconciliation System — Web UI

Pre-Phase 1 refactor.  Key changes from the original:

  1. TENANT BUG FIXED:  tenant_id is now correctly read from the Gradio
     dropdown and passed all the way through the pipeline.  Previously
     tenant_dropdown was defined but never wired to process_folder().

  2. SUBPROCESS CHAIN REMOVED:  The three subprocess.run() calls have been
     replaced by core.pipeline.run_pipeline(), which calls all three
     processing classes directly in the same Python process.

  3. CONFIG CENTRALISED:  No hardcoded paths, ports, or strings.
     Everything comes from config.settings (reads env vars with defaults).

  4. INPUT VALIDATION:  Files are validated (extension + size) before any
     processing begins.  Errors are shown to the user with a clear message.

  5. LOGGING CENTRALISED:  setup_logging() is called once here at startup.
     Sub-modules no longer call basicConfig() themselves.

  6. ERROR HANDLING:  Typed exceptions from core.exceptions map to
     user-friendly messages.  The raw traceback is logged but not shown
     in the UI.
"""

from pdf_extraction_project.ui.template_builder_ui import build_ui
from core.validation import validate_evd_files, validate_pdf_files
from core.pipeline import PipelineResult, run_pipeline
from core.exceptions import (
    EVDExtractionError,
    NoFilesError,
    PDFExtractionError,
    ReconciliationJobError,
    UploadValidationError,
)
import logging
import traceback
from pathlib import Path

import gradio as gr

# ── Bootstrap: config + logging first, before any app imports ─────────── #
from config import settings
from core.logging_config import setup_logging

setup_logging(log_file=settings.LOG_FILE, log_level=settings.LOG_LEVEL)

# ── Application imports (after logging is configured) ─────────────────── #

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# UI controller
# ─────────────────────────────────────────────────────────────────────────

class InvoiceReconciliationUI:
    """Gradio UI controller.  Stateless — all state lives in pipeline results."""

    # ── Main handler ───────────────────────────────────────────────────── #

    def process_files(
        self,
        evd_files,
        pdf_files,
        tenant_id: str,
        progress=gr.Progress(),
    ):
        """
        Gradio event handler wired to the Process button.

        Returns: (report_file_path | None, summary_markdown, stats_html)
        """
        # ── 1. Validate inputs ─────────────────────────────────────────
        progress(0.05, desc="Validating uploads…")
        try:
            evd_paths = validate_evd_files(evd_files)
            pdf_paths = validate_pdf_files(pdf_files)
        except NoFilesError as exc:
            return None, f"⚠️ **Missing files:** {exc}", ""
        except UploadValidationError as exc:
            return None, f"⚠️ **Upload error:** {exc}", ""

        if not tenant_id:
            tenant_id = settings.DEFAULT_TENANT_ID

        logger.info(
            "Job started — tenant=%s  evd=%d  pdf=%d",
            tenant_id, len(evd_paths), len(pdf_paths),
        )

        # ── 2. Run pipeline ────────────────────────────────────────────
        try:
            progress(0.15, desc="Processing EVD files…")
            result: PipelineResult = run_pipeline(
                evd_paths=evd_paths,
                pdf_paths=pdf_paths,
                tenant_id=tenant_id,
            )
        except EVDExtractionError as exc:
            logger.error("EVD extraction failed: %s", exc)
            return (
                None,
                f"❌ **EVD processing failed**\n\n{exc}\n\n"
                "Check that your Excel files are valid EVD format.",
                "",
            )
        except PDFExtractionError as exc:
            logger.error("PDF extraction failed: %s", exc)
            return (
                None,
                f"❌ **PDF processing failed**\n\n{exc}\n\n"
                "Ensure PDF files are not password-protected or corrupted.",
                "",
            )
        except ReconciliationJobError as exc:
            logger.error("Reconciliation failed: %s", exc)
            return None, f"❌ **Reconciliation failed**\n\n{exc}", ""
        except Exception:
            logger.exception("Unexpected error during job")
            return (
                None,
                "❌ **Unexpected error.** The details have been logged.\n\n"
                "Please check app.log for the full trace.",
                "",
            )

        # ── 3. Build UI output ─────────────────────────────────────────
        progress(0.95, desc="Preparing results…")
        summary = self._build_summary(result)
        stats_html = self._build_stats_html(result)
        progress(1.0, desc="Done!")

        logger.info(
            "Job complete — session=%s  match_rate=%.1f%%  duration=%.1fs",
            result.session_id, result.match_rate, result.duration_seconds,
        )

        return str(result.report_path), summary, stats_html

    # ── Output builders ────────────────────────────────────────────────── #

    def _build_summary(self, result: PipelineResult) -> str:
        match_emoji = "🟢" if result.match_rate >= 90 else "🟡" if result.match_rate >= 70 else "🔴"
        return f"""
✅ **Processing Complete** — {result.duration_seconds:.1f}s

**Invoices processed:**
- EVD: **{result.total_evd_invoices}** invoices
- PDF: **{result.total_pdf_invoices}** invoices

**Reconciliation results:**
- {match_emoji} Match rate: **{result.match_rate:.1f}%**
- ✅ Perfect matches: **{result.matches}**
- ⚠️ Mismatches: **{result.mismatches}**
- 🔴 Missing in PDF: **{result.missing_in_pdf}**
- 🔵 Missing in EVD: **{result.missing_in_evd}**

📥 Download the Excel report below for full details.
"""

    def _build_stats_html(self, result: PipelineResult) -> str:
        def vendor_rows(by_vendor: dict) -> str:
            if not by_vendor:
                return "<li><em>No data</em></li>"
            rows = ""
            for vendor, data in list(by_vendor.items())[:8]:
                count = data.get("invoice_count", 0)
                amount = data.get("total_amount", 0)
                rows += (
                    f"<li><b>{vendor}</b>: {count} invoice(s) "
                    f"— €{float(amount):,.2f}</li>"
                )
            if len(by_vendor) > 8:
                rows += f"<li><em>…and {len(by_vendor) - 8} more vendors</em></li>"
            return rows

        return f"""
<div style="padding:20px;background:#f8f9fa;border-radius:10px;font-family:Arial,sans-serif">
  <h3 style="margin-top:0">📊 Vendor Breakdown</h3>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
    <div>
      <h4 style="color:#1F4E79">EVD Files</h4>
      <ul style="padding-left:20px">{vendor_rows(result.evd_by_vendor)}</ul>
    </div>
    <div>
      <h4 style="color:#1F4E79">PDF Files</h4>
      <ul style="padding-left:20px">{vendor_rows(result.pdf_by_vendor)}</ul>
    </div>
  </div>
  <p style="color:#666;font-size:12px;margin-bottom:0">
    Session ID: {result.session_id} — Tenant: {result.tenant_id}
  </p>
</div>
"""

    # ── Interface definition ───────────────────────────────────────────── #

    def create_interface(self) -> gr.Blocks:
        with gr.Blocks(
            title="Invoice Reconciliation System",
            theme=gr.themes.Soft(),
        ) as app:
            with gr.Tabs():
                # ── Tab 1: Reconciliation ──────────────────────────────
                with gr.TabItem("📊 Reconciliation"):
                    gr.Markdown("""
# 🧾 Invoice Reconciliation System

Upload your EVD Excel files and PDF invoices to generate a detailed reconciliation report.

**How it works:**
1. Select your company (tenant)
2. Upload one or more EVD Excel files (`.xlsx`, `.xlsm`, `.xls`)
3. Upload one or more PDF invoice files (`.pdf`)
4. Click **Process & Reconcile**
5. Download the generated Excel report
""")
                    # ── Tenant selector ────────────────────────────────
                    # NOTE: In Phase 1 this will be replaced by a JWT claim.
                    # The dropdown is kept so the feature is visible and
                    # the tenant_id is now correctly wired to the handler.
                    tenant_dropdown = gr.Dropdown(
                        label="🏢 Company (Tenant)",
                        choices=[settings.DEFAULT_TENANT_ID],
                        value=settings.DEFAULT_TENANT_ID,
                        interactive=True,
                        info="Phase 1: will be replaced by authenticated identity",
                    )

                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 📁 EVD Files")
                            evd_upload = gr.File(
                                label="EVD Excel Files",
                                file_count="multiple",
                                file_types=[".xlsx", ".xlsm", ".xls"],
                            )

                        with gr.Column():
                            gr.Markdown("### 📄 PDF Invoices")
                            pdf_upload = gr.File(
                                label="PDF Invoice Files",
                                file_count="multiple",
                                file_types=[".pdf"],
                            )

                    process_btn = gr.Button(
                        "🔄 Process & Reconcile",
                        variant="primary",
                        size="lg",
                    )

                    gr.Markdown("---")

                    with gr.Row():
                        summary_output = gr.Markdown(label="Summary")
                        stats_output = gr.HTML(label="Statistics")

                    report_output = gr.File(
                        label="📥 Download Reconciliation Report"
                    )

                    # ── Wire the button ────────────────────────────────
                    # FIX: tenant_dropdown is now passed as an input so
                    # its value reaches process_files() and the pipeline.
                    process_btn.click(
                        fn=self.process_files,
                        inputs=[evd_upload, pdf_upload, tenant_dropdown],
                        outputs=[report_output, summary_output, stats_output],
                    )

                    gr.Markdown("""
---
### 📋 Report Contents
The Excel report contains 7 sheets:
- **Summary** — overall statistics and match rate
- **Matches** — perfectly matched invoices (green)
- **Mismatches** — invoices with discrepancies (red)
- **Missing in PDF** — EVD invoices without a matching PDF (yellow)
- **Missing in EVD** — PDF invoices without a matching EVD (yellow)
- **EVD Data** — complete EVD invoice list
- **PDF Data** — complete PDF invoice list

### 🎯 Supported Vendors
- ✅ **Vivacom Bulgaria** — template-based extraction
- ✅ **Yettel Bulgaria** — template-based extraction
- ✅ **Generic vendors** — pattern-based fallback extraction
""")

                # ── Tab 2: Template Builder ────────────────────────────
                with gr.TabItem("⚙️ Template Builder"):
                    build_ui()

            app.queue()

        return app


# ─────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────

def main():
    """Launch the web interface."""
    logger.info(
        "Starting Invoice Reconciliation System — host=%s  port=%d  debug=%s",
        settings.SERVER_HOST, settings.SERVER_PORT, settings.DEBUG,
    )

    ui = InvoiceReconciliationUI()
    app = ui.create_interface()

    app.launch(
        server_name=settings.SERVER_HOST,
        server_port=settings.SERVER_PORT,
        share=False,
        show_error=settings.DEBUG,
        debug=settings.DEBUG,
    )


if __name__ == "__main__":
    main()
