"""
EVD-PDF Comparison Utility

Compares extracted EVD data with PDF invoice data to find matches and discrepancies.
This module provides functions to match invoices based on document numbers and amounts.

Author: EVD Extraction Team
"""

import json
from pathlib import Path
import re


class EVDPDFComparator:
    """
    Compares EVD data with PDF extraction data.

    Matching logic:
    1. Primary: Invoice number (normalized)
    2. Secondary: Amount (with tolerance)
    3. Tertiary: Vendor name (fuzzy match)
    """

    def __init__(self, amount_tolerance=0.01):
        """
        Initialize comparator.

        Args:
            amount_tolerance (float): Maximum difference in amounts to consider a match
        """
        self.amount_tolerance = amount_tolerance

    def normalize_invoice_number(self, invoice_num):
        """
        Normalize invoice number for comparison.

        Args:
            invoice_num (str): Raw invoice number

        Returns:
            str: Normalized invoice number
        """
        if not invoice_num:
            return ""

        # Convert to string and uppercase
        invoice_num = str(invoice_num).upper().strip()

        # Remove common prefixes
        invoice_num = re.sub(
            r'^(INV|INVOICE|DOC|FAKTURA|№|NO\.?|#)\s*[-:]?\s*', '', invoice_num)

        # Remove spaces and special characters
        invoice_num = re.sub(r'[^\w\d]', '', invoice_num)

        return invoice_num

    def amounts_match(self, amount1, amount2):
        """
        Check if two amounts match within tolerance.

        Args:
            amount1 (float): First amount
            amount2 (float): Second amount

        Returns:
            bool: True if amounts match
        """
        try:
            diff = abs(float(amount1) - float(amount2))
            return diff <= self.amount_tolerance
        except (ValueError, TypeError):
            return False

    def fuzzy_vendor_match(self, vendor1, vendor2):
        """
        Check if two vendor names are similar enough.

        Args:
            vendor1 (str): First vendor name
            vendor2 (str): Second vendor name

        Returns:
            float: Similarity score (0-1)
        """
        if not vendor1 or not vendor2:
            return 0.0

        v1 = vendor1.upper()
        v2 = vendor2.upper()

        # Exact match
        if v1 == v2:
            return 1.0

        # Check if one contains the other
        if v1 in v2 or v2 in v1:
            return 0.8

        # Check word overlap
        words1 = set(v1.split())
        words2 = set(v2.split())

        if not words1 or not words2:
            return 0.0

        common = words1 & words2
        total = words1 | words2

        return len(common) / len(total) if total else 0.0

    def find_matching_pdf(self, evd_invoice, pdf_invoices):
        """
        Find matching PDF invoice for an EVD entry.

        Args:
            evd_invoice (dict): EVD invoice record
            pdf_invoices (list): List of PDF invoice records

        Returns:
            tuple: (best_match, confidence_score) or (None, 0)
        """
        evd_inv_num = self.normalize_invoice_number(
            evd_invoice['invoice_number'])
        evd_amount = evd_invoice['total_amount_eur']
        evd_vendor = evd_invoice['vendor_normalized']

        best_match = None
        best_score = 0

        for pdf_invoice in pdf_invoices:
            score = 0

            # Check invoice number (most important)
            pdf_inv_num = self.normalize_invoice_number(
                pdf_invoice.get('invoice_number', ''))
            if evd_inv_num and pdf_inv_num and evd_inv_num == pdf_inv_num:
                score += 50  # High score for invoice number match

            # Check amount
            pdf_amount = pdf_invoice.get('total_amount', 0)
            if self.amounts_match(evd_amount, pdf_amount):
                score += 30  # Good score for amount match

            # Check vendor
            pdf_vendor = pdf_invoice.get('vendor_normalized', '')
            vendor_similarity = self.fuzzy_vendor_match(evd_vendor, pdf_vendor)
            score += vendor_similarity * 20  # Up to 20 points for vendor match

            if score > best_score:
                best_score = score
                best_match = pdf_invoice

        # Require minimum score for a match
        if best_score < 50:  # At least invoice number or amount+vendor
            return None, 0

        return best_match, best_score

    def compare_datasets(self, evd_data, pdf_data):
        """
        Compare complete EVD and PDF datasets.

        Args:
            evd_data (dict): Extracted EVD data structure
            pdf_data (dict): Extracted PDF data structure (same format)

        Returns:
            dict: Comparison results with matches, mismatches, and missing items
        """
        results = {
            'summary': {
                'total_evd': len(evd_data['all_invoices']),
                'total_pdf': len(pdf_data['all_invoices']),
                'matches': 0,
                'mismatches': 0,
                'missing_in_pdf': 0,
                'missing_in_evd': 0
            },
            'matches': [],
            'mismatches': [],
            'missing_in_pdf': [],
            'missing_in_evd': [],
            'by_vendor': {}
        }

        matched_pdf_indices = set()

        # Process each EVD invoice
        for evd_invoice in evd_data['all_invoices']:
            vendor = evd_invoice['vendor_normalized']

            # Get PDF invoices for same vendor
            vendor_pdfs = pdf_data['by_vendor'].get(
                vendor, {}).get('invoices', [])

            # Try to find match
            match, confidence = self.find_matching_pdf(
                evd_invoice, vendor_pdfs)

            if match:
                # Found a match
                match_result = {
                    'evd': evd_invoice,
                    'pdf': match,
                    'confidence': confidence,
                    'discrepancies': []
                }

                # Check for discrepancies
                if not self.amounts_match(evd_invoice['total_amount_eur'], match['total_amount']):
                    match_result['discrepancies'].append({
                        'type': 'amount',
                        'evd_value': evd_invoice['total_amount_eur'],
                        'pdf_value': match['total_amount'],
                        'difference': abs(evd_invoice['total_amount_eur'] - match['total_amount'])
                    })

                if match_result['discrepancies']:
                    results['mismatches'].append(match_result)
                    results['summary']['mismatches'] += 1
                else:
                    results['matches'].append(match_result)
                    results['summary']['matches'] += 1

                # Mark PDF as matched
                matched_pdf_indices.add(id(match))
            else:
                # No match found
                results['missing_in_pdf'].append(evd_invoice)
                results['summary']['missing_in_pdf'] += 1

        # Find unmatched PDFs
        for pdf_invoice in pdf_data['all_invoices']:
            if id(pdf_invoice) not in matched_pdf_indices:
                results['missing_in_evd'].append(pdf_invoice)
                results['summary']['missing_in_evd'] += 1

        return results

    def save_comparison_report(self, results, output_path):
        """
        Save comparison results to JSON file.

        Args:
            results (dict): Comparison results
            output_path (str or Path): Output file path
        """
        output_path = Path(output_path)
        with open(output_path, 'w', encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Comparison report saved to: {output_path}")

    def print_comparison_summary(self, results):
        """Print summary of comparison results."""
        print("\n" + "="*80)
        print("COMPARISON SUMMARY")
        print("="*80)

        summary = results['summary']
        print(f"Total EVD invoices: {summary['total_evd']}")
        print(f"Total PDF invoices: {summary['total_pdf']}")
        print(f"\nPerfect matches: {summary['matches']}")
        print(f"Matches with discrepancies: {summary['mismatches']}")
        print(f"Missing in PDF: {summary['missing_in_pdf']}")
        print(f"Missing in EVD: {summary['missing_in_evd']}")

        # Calculate match rate
        if summary['total_evd'] > 0:
            match_rate = (summary['matches'] / summary['total_evd']) * 100
            print(f"\nMatch rate: {match_rate:.1f}%")

        # Show some details
        if results['mismatches']:
            print("\nSample mismatches:")
            for mismatch in results['mismatches'][:3]:
                evd = mismatch['evd']
                pdf = mismatch['pdf']
                print(
                    f"  {evd['invoice_number']}: EVD=€{evd['total_amount_eur']:.2f}, PDF=€{pdf['total_amount']:.2f}")

        if results['missing_in_pdf']:
            print("\nSample missing in PDF:")
            for missing in results['missing_in_pdf'][:3]:
                print(
                    f"  {missing['invoice_number']}: {missing['vendor_normalized']} - €{missing['total_amount_eur']:.2f}")


def main():
    """Example usage."""
    import sys
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    if len(sys.argv) < 3:
        print(
            "Usage: python pdf_evd_comparator.py <evd_data.json> <pdf_data.json> [output.json]")
        sys.exit(1)

    evd_file = sys.argv[1]
    pdf_file = sys.argv[2]
    output_file = sys.argv[3] if len(
        sys.argv) > 3 else 'comparison_results.json'

    # Load data
    with open(evd_file, 'r', encoding="utf-8") as f:
        evd_data = json.load(f)

    with open(pdf_file, 'r', encoding="utf-8") as f:
        pdf_data = json.load(f)

    # Compare
    comparator = EVDPDFComparator()
    results = comparator.compare_datasets(evd_data, pdf_data)

    # Output results
    comparator.print_comparison_summary(results)
    comparator.save_comparison_report(results, output_file)


if __name__ == "__main__":
    main()
