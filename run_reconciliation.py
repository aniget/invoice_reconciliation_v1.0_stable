"""
Complete EVD-PDF Reconciliation Workflow

End-to-end workflow that:
1. Processes all EVD files from input_evd/ folder
2. Processes all PDF files from input_pdf/ folder  
3. Compares and matches the data
4. Generates Excel reconciliation report

Author: Reconciliation Team
Date: 2026-01-29
"""

from datetime import datetime
import subprocess
from pathlib import Path
import sys
import logging


class ReconciliationWorkflow:
    """
    Complete reconciliation workflow orchestrator.

    Folder Structure:
    input_evd/          - Place EVD Excel files here
    input_pdf/          - Place PDF invoices here
    output/             - Results will be saved here
    """

    def __init__(self, base_dir: Path = None):
        """
        Initialize workflow.

        Args:
            base_dir (Path): Base directory (default: current directory)
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()

        # Define folder structure
        self.input_evd_folder = self.base_dir / 'input_evd'
        self.input_pdf_folder = self.base_dir / 'input_pdf'
        self.output_folder = self.base_dir / 'output'

        # Define output files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.evd_output = self.output_folder / f'evd_data_{timestamp}.json'
        self.pdf_output = self.output_folder / f'pdf_data_{timestamp}.json'
        self.report_output = self.output_folder / \
            f'reconciliation_report_{timestamp}.xlsx'

        # Script paths
        self.evd_script = Path('evd_extraction_project/batch_evd_extractor.py')
        self.pdf_script = Path('pdf_extraction_project/pdf_processor.py')
        self.reconcile_script = Path(
            'reconciliation_project/reconciliation_report.py')

    def setup_folders(self):
        """Create required folders if they don't exist."""
        print("Setting up folder structure...")

        folders = [
            (self.input_evd_folder, "EVD Excel files"),
            (self.input_pdf_folder, "PDF invoice files"),
            (self.output_folder, "output files")
        ]

        for folder, description in folders:
            if not folder.exists():
                folder.mkdir(parents=True, exist_ok=True)
                print(
                    f"  [SUCCESS] Created: {folder}/ (for {description})")
            else:
                print(f"  [SUCCESS] Exists: {folder}/")

        print("")

    def check_files(self):
        """Check if input files exist."""
        print("Checking for input files...")

        # Count EVD files
        evd_files = list(self.input_evd_folder.glob('*.xlsx')) + \
            list(self.input_evd_folder.glob('*.xlsm')) + \
            list(self.input_evd_folder.glob('*.xls'))

        # Count PDF files (*.pdf matches .pdf and .PDF on Windows)
        pdf_files = sorted(self.input_pdf_folder.glob('*.pdf'))

        print(f"  EVD files found: {len(evd_files)}")
        if evd_files:
            for f in evd_files:
                print(f"    - {f.name}")

        print(f"  PDF files found: {len(pdf_files)}")
        if pdf_files:
            for f in pdf_files[:5]:  # Show first 5
                print(f"    - {f.name}")
            if len(pdf_files) > 5:
                print(f"    ... and {len(pdf_files) - 5} more")

        print("")

        if not evd_files and not pdf_files:
            print("[ATTENTION] Warning: No input files found!")
            print(f"  Please add EVD files to: {self.input_evd_folder}")
            print(f"  Please add PDF files to: {self.input_pdf_folder}")
            return False

        if not evd_files:
            print("[ATTENTION] Warning: No EVD files found!")
            print(
                f"  Please add EVD Excel files to: {self.input_evd_folder}")
            return False

        if not pdf_files:
            print("[ATTENTION] Warning: No PDF files found!")
            print(
                f"  Please add PDF invoices to: {self.input_pdf_folder}")
            return False

        return True

    def run_step(self, step_name: str, command: list):
        """
        Run a processing step.

        Args:
            step_name (str): Name of the step
            command (list): Command to execute

        Returns:
            bool: True if successful
        """
        print("="*80)
        print(f"STEP: {step_name}")
        print("="*80)

        try:
            result = subprocess.run(
                command,
                capture_output=False,
                text=True,
                check=True
            )
            print(f"\n[SUCCESS] {step_name} completed successfully\n")
            return True

        except subprocess.CalledProcessError as e:
            print(
                f"\n[ERROR] {step_name} failed with error code {e.returncode}\n")
            return False
        except FileNotFoundError:
            print(f"\n[ERROR] Script not found: {command[1]}")
            print(
                f"  Make sure you're running from the correct directory\n")
            return False

    def run(self):
        """Execute complete workflow."""
        print("\n" + "="*80)
        print("COMPLETE EVD-PDF RECONCILIATION WORKFLOW")
        print("="*80)
        print(
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base directory: {self.base_dir}")
        print("="*80 + "\n")

        # Step 0: Setup
        self.setup_folders()

        # Step 0.5: Check for files
        if not self.check_files():
            print("\n[ATTENTION] Please add input files and run again")
            return False

        # Step 1: Extract EVD data
        step1_success = self.run_step(
            "Extract EVD Data",
            [
                sys.executable,
                str(self.evd_script),
                str(self.input_evd_folder),
                str(self.evd_output)
            ]
        )

        if not step1_success:
            print("Workflow stopped due to EVD extraction failure")
            return False

        # Step 2: Extract PDF data
        step2_success = self.run_step(
            "Extract PDF Data",
            [
                sys.executable,
                str(self.pdf_script),
                str(self.input_pdf_folder),
                str(self.pdf_output)
            ]
        )

        if not step2_success:
            print("Workflow stopped due to PDF extraction failure")
            return False

        # Step 3: Generate reconciliation report
        step3_success = self.run_step(
            "Generate Reconciliation Report",
            [
                sys.executable,
                str(self.reconcile_script),
                str(self.evd_output),
                str(self.pdf_output),
                str(self.report_output)
            ]
        )

        if not step3_success:
            print("Workflow stopped due to reconciliation failure")
            return False

        # Success!
        print("\n" + "="*80)
        print("[SUCCESS] WORKFLOW COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nGenerated Files:")
        print(f"  1. EVD Data: {self.evd_output}")
        print(f"  2. PDF Data: {self.pdf_output}")
        print(f"  3. Reconciliation Report: {self.report_output}")
        print("\n[SUCCESS] Open the Excel report to review results")
        print("="*80 + "\n")

        return True


def main():
    """Main entry point."""

    # Check if help requested
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("""
EVD-PDF Reconciliation Workflow

USAGE:
  python run_reconciliation.py [base_directory]

DESCRIPTION:
  Complete workflow that processes EVD and PDF files and generates
  a reconciliation report.

FOLDER STRUCTURE:
  base_directory/
    ├── input_evd/       - Place EVD Excel files here
    ├── input_pdf/       - Place PDF invoices here
    └── output/          - Results will be saved here

WORKFLOW STEPS:
  1. Extract data from all EVD Excel files
  2. Extract data from all PDF invoices
  3. Compare and match the data
  4. Generate Excel reconciliation report (7 sheets)

EXAMPLES:
  # Run from current directory
  python run_reconciliation.py

  # Run from specific directory
  python run_reconciliation.py /path/to/project

OUTPUT FILES:
  - evd_data_TIMESTAMP.json          # Extracted EVD data
  - pdf_data_TIMESTAMP.json          # Extracted PDF data
  - reconciliation_report_TIMESTAMP.xlsx  # Final report

REQUIREMENTS:
  - EVD files in input_evd/ folder
  - PDF files in input_pdf/ folder
  - All dependencies installed (openpyxl, pdfplumber, pypdf)

For more help, see MASTER_GUIDE.md
        """)
        return 0

    # Determine base directory
    if len(sys.argv) > 1:
        base_dir = Path(sys.argv[1])
    else:
        base_dir = Path.cwd()

    # Run workflow
    workflow = ReconciliationWorkflow(base_dir)
    success = workflow.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
