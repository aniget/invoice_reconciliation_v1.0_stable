"""
Invoice Reconciliation System - Simple Web UI

A user-friendly interface for invoice processing and reconciliation.
Uses Gradio for simplicity (no database, no AI dependencies).

Core features:
- Upload EVD Excel files
- Upload PDF invoices
- Process and reconcile
- Download Excel report
"""

import traceback
import sys
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
import json
import shutil
import os
import gradio as gr
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[
                    logging.FileHandler("debug.log", encoding="utf-8"), logging.StreamHandler()], force=True)


class InvoiceReconciliationUI:
    """Simple web UI for invoice reconciliation."""

    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "invoice_reconciliation"
        self.temp_dir.mkdir(exist_ok=True)

    def process_files(self, evd_files, pdf_files, progress=gr.Progress()):
        """
        Process uploaded files and generate reconciliation report.

        Args:
            evd_files: List of uploaded EVD Excel files
            pdf_files: List of uploaded PDF invoice files
            progress: Gradio progress tracker

        Returns:
            tuple: (report_path, summary_text, stats_html)
        """

        if not evd_files or not pdf_files:
            return None, "[ERROR] Error: Please upload both EVD and PDF files", ""

        try:
            # Create session directory
            session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            session_dir = self.temp_dir / session_id
            session_dir.mkdir(exist_ok=True)

            evd_dir = session_dir / "evd"
            pdf_dir = session_dir / "pdf"
            output_dir = session_dir / "output"

            evd_dir.mkdir()
            pdf_dir.mkdir()
            output_dir.mkdir()

            progress(0.1, desc="Copying uploaded files...")

            # Copy EVD files
            for evd_file in evd_files:
                if evd_file is not None:
                    filename = Path(evd_file.name).name
                    shutil.copy2(evd_file.name, evd_dir / filename)

            # Copy PDF files
            for pdf_file in pdf_files:
                if pdf_file is not None:
                    filename = Path(pdf_file.name).name
                    shutil.copy2(pdf_file.name, pdf_dir / filename)

            progress(0.2, desc="Processing EVD files...")

            # Process EVD files
            evd_output = output_dir / "evd_data.json"
            result = subprocess.run([
                sys.executable,
                '-m',
                'evd_extraction_project.batch_evd_extractor',
                str(evd_dir),
                str(evd_output)
            ], capture_output=True, text=True)

            if result.returncode != 0:
                return None, f"[ERROR] EVD processing failed:\n{result.stderr}", ""

            progress(0.5, desc="Processing PDF files...")

            # Process PDF files
            pdf_output = output_dir / "pdf_data.json"
            result = subprocess.run([
                sys.executable,
                '-m',
                'pdf_extraction_project.pdf_processor',
                str(pdf_dir),
                str(pdf_output)
            ], capture_output=True, text=True)

            if result.returncode != 0:
                return None, f"[ERROR] PDF processing failed:\n{result.stderr}", ""

            progress(0.8, desc="Generating reconciliation report...")

            # Generate reconciliation report
            report_output = output_dir / "reconciliation_report.xlsx"
            result = subprocess.run([
                sys.executable,
                '-m',
                'reconciliation_project.reconciliation_report',
                str(evd_output),
                str(pdf_output),
                str(report_output)
            ], capture_output=True, text=True)

            if result.returncode != 0:
                return None, f"[ERROR] Reconciliation failed:\n{result.stderr}", ""

            progress(0.9, desc="Preparing results...")

            # Load results
            with open(evd_output, "r", encoding="utf-8") as f:
                evd_data = json.load(f)

            with open(pdf_output, "r", encoding="utf-8") as f:
                pdf_data = json.load(f)

            # Calculate summary
            summary = self._generate_summary(
                evd_data, pdf_data, len(evd_files), len(pdf_files))
            stats_html = self._generate_stats_html(evd_data, pdf_data)

            progress(1.0, desc="Complete!")

            return str(report_output), summary, stats_html

        except Exception as e:
            full_trace = traceback.format_exc()
            return None, f"[ERROR] {full_trace}", ""

    def _generate_summary(self, evd_data, pdf_data, evd_count, pdf_count):
        """Generate summary text."""

        total_evd = evd_data.get('metadata', {}).get('total_invoices', 0)
        total_pdf = pdf_data.get('metadata', {}).get('total_invoices', 0)

        summary = f"""
✅ **Processing Complete!**

 **Summary:**
- EVD Files Processed: {evd_count}
- PDF Files Processed: {pdf_count}
- Total EVD Invoices: {total_evd}
- Total PDF Invoices: {total_pdf}

📥 **Download the Excel report below to view detailed results:**
- Matches (green)
- Mismatches (red)
- Missing invoices (yellow)
- Full reconciliation details
"""
        return summary

    def _generate_stats_html(self, evd_data, pdf_data):
        """Generate statistics HTML."""

        evd_vendors = evd_data.get('by_vendor', {})
        pdf_vendors = pdf_data.get('by_vendor', {})

        html = "<div style='padding: 20px; background: #f5f5f5; border-radius: 10px;'>"
        html += "<h3> Vendor Breakdown</h3>"

        html += "<h4>EVD Files:</h4><ul>"
        for vendor, data in list(evd_vendors.items())[:5]:
            count = data.get('invoice_count', 0)
            html += f"<li><b>{vendor}</b>: {count} invoices</li>"
        html += "</ul>"

        html += "<h4>PDF Files:</h4><ul>"
        for vendor, data in list(pdf_vendors.items())[:5]:
            count = data.get('invoice_count', 0)
            html += f"<li><b>{vendor}</b>: {count} invoices</li>"
        html += "</ul>"

        html += "</div>"
        return html

    def create_interface(self):
        """Create Gradio interface."""

        with gr.Blocks(title="Invoice Reconciliation System", theme=gr.themes.Soft()) as app:
            gr.Markdown("""
            #  Invoice Reconciliation System
            
            **Upload your EVD Excel files and PDF invoices to generate a detailed reconciliation report.**
            
            ### How it works:
            1. Upload one or more EVD Excel files (.xlsx, .xlsm, .xls)
            2. Upload one or more PDF invoice files (.pdf)
            3. Click "Process & Reconcile"
            4. Download the generated Excel report
            """)

            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📁 Upload EVD Files")
                    evd_upload = gr.File(
                        label="EVD Excel Files",
                        file_count="multiple",
                        file_types=[".xlsx", ".xlsm", ".xls"]
                    )
                    evd_info = gr.Markdown(
                        "*Upload one or more EVD Excel files*")

                with gr.Column():
                    gr.Markdown("### 📄 Upload PDF Files")
                    pdf_upload = gr.File(
                        label="PDF Invoice Files",
                        file_count="multiple",
                        file_types=[".pdf"]
                    )
                    pdf_info = gr.Markdown(
                        "*Upload one or more PDF invoice files*")

            process_btn = gr.Button(
                "🔄 Process & Reconcile", variant="primary", size="lg")

            gr.Markdown("---")

            with gr.Row():
                summary_output = gr.Markdown(label="Summary")
                stats_output = gr.HTML(label="Statistics")

            report_output = gr.File(label="📥 Download Reconciliation Report")

            # Process button click
            process_btn.click(
                fn=self.process_files,
                inputs=[evd_upload, pdf_upload],
                outputs=[report_output, summary_output, stats_output]
            )

            gr.Markdown("""
            ---
            ### 📋 Report Contents:
            The Excel report contains 7 detailed sheets:
            - **Summary**: Overall statistics and match rates
            - **Matches**: Perfectly matched invoices (green)
            - **Mismatches**: Invoices with discrepancies (red)  
            - **Missing in PDF**: EVD invoices without matching PDF (yellow)
            - **Missing in EVD**: PDF invoices without matching EVD (yellow)
            - **EVD Data**: Complete EVD invoice list
            - **PDF Data**: Complete PDF invoice list
            
            ### 🎯 Supported Vendors:
            - ✅ **Vivacom Bulgaria** - 100% accuracy
            - ✅ **Yettel Bulgaria** - 100% accuracy  
            - ✅ **Generic vendors** - Pattern-based extraction
            
            ### ⚙️ System Information:
            - Version: 1.0 (Stable)
            - Core extraction only (no AI, no database)
            - Runs completely offline
            """)
        # ⭐ REQUIRED for Gradio 3.x if progress is used
        app.queue()

        return app


def main():
    """Launch the web interface."""

    ui = InvoiceReconciliationUI()
    app = ui.create_interface()

    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        debug=True
    )


if __name__ == "__main__":
    main()
