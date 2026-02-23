"""
EVD-PDF Comparator

Facade over the reconciliation domain service.
Maintains backward compatibility with existing JSON-based API.

This is now a thin adapter - business logic lives in domain.service.
"""

from reconciliation_project.adapters.json_adapter import JSONToInvoiceAdapter
from reconciliation_project.domain.service import ReconciliationService
import json
import sys
from pathlib import Path
from decimal import Decimal
from typing import Optional


class EVDPDFComparator:
    """
    Backward-compatible facade for invoice reconciliation.

    Delegates to ReconciliationService for business logic.
    Handles JSON conversion via adapters.
    """

    def __init__(self, amount_tolerance: float = 0.01):
        """
        Initialize comparator.

        Args:
            amount_tolerance: Tolerance for amount comparisons (in EUR)
        """
        # Delegate to domain service
        self.service = ReconciliationService(
            amount_tolerance=Decimal(str(amount_tolerance))
        )

        # Keep these for backward compatibility (deprecated)
        self.amount_tolerance = amount_tolerance

    def compare_datasets(self, evd_data: dict, pdf_data: dict) -> dict:
        """
        Compare EVD and PDF datasets.

        This method maintains backward compatibility with existing code
        that expects JSON dictionaries as input/output.

        Args:
            evd_data: EVD extraction data (JSON format)
            pdf_data: PDF extraction data (JSON format)

        Returns:
            Comparison results in JSON-compatible format
        """
        # Convert JSON to domain models
        evd_invoices = JSONToInvoiceAdapter.from_json_dataset(evd_data, 'evd')
        pdf_invoices = JSONToInvoiceAdapter.from_json_dataset(pdf_data, 'pdf')
        pdf_by_vendor = JSONToInvoiceAdapter.extract_vendor_grouping(
            pdf_data, 'pdf')

        # Perform reconciliation using domain service
        result = self.service.reconcile(
            evd_invoices=evd_invoices,
            pdf_invoices=pdf_invoices,
            pdf_by_vendor=pdf_by_vendor
        )

        # Convert back to JSON format for backward compatibility
        return result.to_summary_dict()

    # ==========================================
    # Deprecated methods - kept for compatibility
    # These delegate to domain.rules now
    # ==========================================

    def normalize_invoice_number(self, invoice_num: str) -> str:
        """[DEPRECATED] Use domain.rules.InvoiceNormalizer instead."""
        return self.service.normalizer.normalize_invoice_number(invoice_num)

    def normalize_amount(self, value) -> float:
        """[DEPRECATED] Use domain.rules.AmountValidator instead."""
        return float(self.service.amount_validator.normalize_amount(value))

    def amounts_match(self, a, b) -> bool:
        """[DEPRECATED] Use domain.rules.AmountValidator instead."""
        a_dec = self.service.amount_validator.normalize_amount(a)
        b_dec = self.service.amount_validator.normalize_amount(b)
        return self.service.amount_validator.amounts_match(a_dec, b_dec)

    def amounts_consistent(self, evd_amt, pdf_amt) -> bool:
        """[DEPRECATED] Use domain.rules.AmountValidator instead."""
        return self.service.amount_validator.amounts_consistent(evd_amt, pdf_amt)

    def fuzzy_vendor_match(self, v1, v2) -> float:
        """[DEPRECATED] Use domain.rules.VendorMatcher instead."""
        return self.service.vendor_matcher.calculate_similarity(v1, v2)


# ==========================================
# CLI entrypoint (unchanged from original)
# ==========================================
def main():
    """Command-line interface for comparison."""
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python pdf_evd_comparator.py <evd.json> <pdf.json> [output.json]")
        sys.exit(1)

    evd_file = Path(sys.argv[1])
    pdf_file = Path(sys.argv[2])
    output_file = Path(sys.argv[3]) if len(
        sys.argv) > 3 else Path("comparison_results.json")

    # Load data
    with open(evd_file, "r", encoding="utf-8") as f:
        evd_data = json.load(f)

    with open(pdf_file, "r", encoding="utf-8") as f:
        pdf_data = json.load(f)

    # Compare
    comparator = EVDPDFComparator()
    results = comparator.compare_datasets(evd_data, pdf_data)

    # Print summary
    print(json.dumps(results["summary"], indent=2))

    # Save results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved comparison results to: {output_file}")


if __name__ == "__main__":
    main()
