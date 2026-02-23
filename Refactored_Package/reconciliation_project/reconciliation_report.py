"""
EVD-PDF Reconciliation Report Generator

Main entry point for generating reconciliation reports.
Orchestrates the entire process using layered architecture:

1. Domain Layer (domain/*) - Business logic
2. Application Layer (application/*) - Use cases
3. Adapters Layer (adapters/*) - Data conversion
4. Presentation Layer (presentation/*) - Excel formatting

All business logic is in the domain layer.
This file only orchestrates the flow.
"""

import json
import logging
from pathlib import Path
from decimal import Decimal

from .domain.service import ReconciliationService
from .adapters.json_adapter import JSONToInvoiceAdapter
from .application.report_generator import ReportDataGenerator
from .presentation.excel_presenter import ReconciliationExcelPresenter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReconciliationReportGenerator:
    """
    Main reconciliation report generator.
    
    Orchestrates:
    - Loading data via adapters
    - Reconciliation via domain service
    - Report data generation via application layer
    - Excel generation via presentation layer
    
    No business logic here - just orchestration.
    """
    
    def __init__(self, amount_tolerance: float = 0.01):
        """
        Initialize generator with dependencies.
        
        Args:
            amount_tolerance: Tolerance for amount comparisons (EUR)
        """
        self.reconciliation_service = ReconciliationService(
            amount_tolerance=Decimal(str(amount_tolerance))
        )
        self.data_generator = ReportDataGenerator()
        self.excel_presenter = ReconciliationExcelPresenter()
    
    def generate_report(
        self,
        evd_data: dict,
        pdf_data: dict,
        output_path: Path
    ):
        """
        Generate complete reconciliation report.
        
        This is the main public API for report generation.
        
        Args:
            evd_data: EVD extraction data (JSON format)
            pdf_data: PDF extraction data (JSON format)
            output_path: Where to save the Excel report
        """
        logger.info("="*80)
        logger.info("Starting Reconciliation Report Generation")
        logger.info("="*80)
        
        # Step 1: Convert JSON to domain models (Adapters)
        logger.info("Converting JSON data to domain models...")
        evd_invoices = JSONToInvoiceAdapter.from_json_dataset(evd_data, 'evd')
        pdf_invoices = JSONToInvoiceAdapter.from_json_dataset(pdf_data, 'pdf')
        pdf_by_vendor = JSONToInvoiceAdapter.extract_vendor_grouping(pdf_data, 'pdf')
        
        logger.info(f"  EVD invoices: {len(evd_invoices)}")
        logger.info(f"  PDF invoices: {len(pdf_invoices)}")
        
        # Step 2: Perform reconciliation (Domain)
        logger.info("Performing reconciliation...")
        result = self.reconciliation_service.reconcile(
            evd_invoices=evd_invoices,
            pdf_invoices=pdf_invoices,
            pdf_by_vendor=pdf_by_vendor
        )
        
        logger.info(f"  Matches: {len(result.matches)}")
        logger.info(f"  Mismatches: {len(result.mismatches)}")
        logger.info(f"  Missing in PDF: {len(result.missing_in_pdf)}")
        logger.info(f"  Missing in EVD: {len(result.missing_in_evd)}")
        logger.info(f"  Match rate: {result.match_rate:.1f}%")
        
        # Step 3: Generate report data (Application)
        logger.info("Generating report data...")
        report_data = self.data_generator.generate_report_data(
            result=result,
            evd_metadata=evd_data.get('metadata', {}),
            pdf_metadata=pdf_data.get('metadata', {})
        )
        
        # Step 4: Create Excel report (Presentation)
        logger.info(f"Creating Excel report: {output_path}")
        self.excel_presenter.create_workbook(report_data, output_path)
        
        logger.info("="*80)
        logger.info("[SUCCESS] Reconciliation report generated successfully!")
        logger.info(f"Report saved to: {output_path}")
        logger.info("="*80)
    
    def generate_report_from_files(
        self,
        evd_file: Path,
        pdf_file: Path,
        output_file: Path
    ):
        """
        Convenience method to generate report from file paths.
        
        Args:
            evd_file: Path to EVD JSON file
            pdf_file: Path to PDF JSON file
            output_file: Path for output Excel file
        """
        logger.info(f"Loading EVD data from: {evd_file}")
        with open(evd_file, 'r', encoding='utf-8') as f:
            evd_data = json.load(f)
        
        logger.info(f"Loading PDF data from: {pdf_file}")
        with open(pdf_file, 'r', encoding='utf-8') as f:
            pdf_data = json.load(f)
        
        self.generate_report(evd_data, pdf_data, output_file)


# ==========================================
# Backward Compatibility Layer
# For existing code that uses the old API
# ==========================================

class ReconciliationReportGeneratorLegacy:
    """
    Legacy API wrapper for backward compatibility.
    
    Maintains the old interface while using new architecture internally.
    """
    
    def __init__(self, amount_tolerance: float = 0.01):
        self._generator = ReconciliationReportGenerator(amount_tolerance)
        
        # Keep old style attributes for compatibility
        # (These are not used anymore but kept for any code that checks them)
        from .presentation.excel_presenter import ExcelStyles
        self.header_fill = ExcelStyles.FILL_HEADER
        self.header_font = ExcelStyles.FONT_HEADER
        self.match_fill = ExcelStyles.FILL_MATCH
        self.mismatch_fill = ExcelStyles.FILL_MISMATCH
        self.missing_fill = ExcelStyles.FILL_MISSING
    
    def generate_report(
        self,
        evd_data: dict,
        pdf_data: dict,
        comparison_results: dict,
        output_path: Path
    ):
        """
        Legacy API: accepts pre-computed comparison_results.
        
        New API doesn't need comparison_results as input since it
        performs reconciliation internally.
        """
        # Just ignore comparison_results and use new flow
        self._generator.generate_report(evd_data, pdf_data, output_path)


# ==========================================
# CLI Entry Point
# ==========================================

def main():
    """Command-line interface."""
    import sys
    
    if len(sys.argv) < 4:
        print("\nUsage: python reconciliation_report.py <evd_data.json> <pdf_data.json> <output.xlsx>")
        print("\nExample:")
        print("  python reconciliation_report.py evd_extracted.json pdf_extracted.json reconciliation.xlsx")
        sys.exit(1)
    
    evd_file = Path(sys.argv[1])
    pdf_file = Path(sys.argv[2])
    output_file = Path(sys.argv[3])
    
    # Validate files
    if not evd_file.exists():
        logger.error(f"EVD file not found: {evd_file}")
        sys.exit(1)
    
    if not pdf_file.exists():
        logger.error(f"PDF file not found: {pdf_file}")
        sys.exit(1)
    
    # Generate report
    generator = ReconciliationReportGenerator()
    
    try:
        generator.generate_report_from_files(evd_file, pdf_file, output_file)
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
