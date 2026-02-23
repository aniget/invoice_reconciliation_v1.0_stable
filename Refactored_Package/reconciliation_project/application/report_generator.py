"""
Report Data Generator

Transforms domain reconciliation results into presentation-ready format.
This is the "glue" between business logic and Excel presentation.

Responsibilities:
- Format data for display
- Calculate display percentages
- Generate display strings
- Organize data by sheet requirements
"""

from typing import Dict, List, Any
from decimal import Decimal

from ..domain.models import ReconciliationResult, InvoiceMatch, Invoice, Discrepancy


class ReportDataGenerator:
    """
    Generates presentation-ready data from domain reconciliation results.
    
    Separates business logic (ReconciliationService) from presentation (ExcelPresenter).
    """
    
    def generate_report_data(
        self,
        result: ReconciliationResult,
        evd_metadata: Dict = None,
        pdf_metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        Generate complete report data structure.
        
        Args:
            result: Domain reconciliation result
            evd_metadata: Optional EVD dataset metadata
            pdf_metadata: Optional PDF dataset metadata
            
        Returns:
            Dictionary with all data needed for Excel presentation
        """
        return {
            'summary': self._generate_summary_data(result, evd_metadata, pdf_metadata),
            'matches': self._generate_matches_data(result.matches),
            'mismatches': self._generate_mismatches_data(result.mismatches),
            'missing_in_pdf': self._generate_missing_in_pdf_data(result.missing_in_pdf),
            'missing_in_evd': self._generate_missing_in_evd_data(result.missing_in_evd),
            'by_vendor': self._generate_by_vendor_data(result),
            'detailed': self._generate_detailed_comparison_data(result)
        }
    
    def _generate_summary_data(
        self,
        result: ReconciliationResult,
        evd_metadata: Dict,
        pdf_metadata: Dict
    ) -> Dict:
        """Generate summary sheet data."""
        match_rate = result.match_rate
        
        # Determine source information
        source = "Unknown"
        if pdf_metadata:
            if 'source_file' in pdf_metadata:
                source = pdf_metadata['source_file']
            elif 'source_folder' in pdf_metadata:
                source = pdf_metadata['source_folder']
        
        # Status determination
        if match_rate >= 95:
            status_text = "EXCELLENT - Minimal discrepancies"
        elif match_rate >= 85:
            status_text = "GOOD - Some review needed"
        else:
            status_text = "ATTENTION REQUIRED - Significant discrepancies"
        
        return {
            'source': source,
            'total_evd': result.total_evd,
            'total_pdf': result.total_pdf,
            'matches': len(result.matches),
            'mismatches': len(result.mismatches),
            'missing_in_pdf': len(result.missing_in_pdf),
            'missing_in_evd': len(result.missing_in_evd),
            'match_pct': self._format_percentage(len(result.matches), result.total_evd),
            'mismatch_pct': self._format_percentage(len(result.mismatches), result.total_evd),
            'missing_pdf_pct': self._format_percentage(len(result.missing_in_pdf), result.total_evd),
            'missing_evd_pct': self._format_percentage(len(result.missing_in_evd), result.total_pdf),
            'match_rate': match_rate,
            'match_rate_display': f"{match_rate:.1f}%",
            'status_text': status_text
        }
    
    def _generate_matches_data(self, matches: List[InvoiceMatch]) -> List[Dict]:
        """Generate matches sheet data."""
        rows = []
        
        for match in matches:
            evd = match.evd_invoice
            pdf = match.pdf_invoice
            
            # Determine amount note based on sign convention
            evd_amt = float(evd.total_amount_eur)
            pdf_amt = float(pdf.total_amount_eur) if pdf else 0
            
            if abs(evd_amt + pdf_amt) < 0.01:
                amount_note = "Sign convention: EVD expense = PDF credit"
            else:
                amount_note = "Amounts match"
            
            rows.append({
                'vendor': evd.vendor_normalized,
                'invoice_number': evd.invoice_number,
                'evd_date': evd.invoice_date or '',
                'pdf_date': pdf.invoice_date if pdf else '',
                'evd_amount': evd_amt,
                'pdf_amount': pdf_amt,
                'confidence': match.confidence,
                'amount_note': amount_note,
                'evd_file': evd.source_file or '',
                'pdf_file': pdf.source_file if pdf else ''
            })
        
        return rows
    
    def _generate_mismatches_data(self, mismatches: List[InvoiceMatch]) -> List[Dict]:
        """Generate mismatches sheet data."""
        rows = []
        
        for mismatch in mismatches:
            evd = mismatch.evd_invoice
            pdf = mismatch.pdf_invoice
            
            # Format discrepancies as readable text
            issues = []
            difference = Decimal('0.00')
            
            for disc in mismatch.discrepancies:
                if disc.type == 'amount':
                    issues.append(f"Amount: EVD={disc.evd_value:.2f} vs PDF={disc.pdf_value:.2f}")
                    difference = abs(Decimal(str(disc.difference)))
                else:
                    issues.append(f"{disc.type}: {disc}")
            
            issue_text = "; ".join(issues) if issues else "Unknown discrepancy"
            
            rows.append({
                'vendor': evd.vendor_normalized,
                'invoice_number': evd.invoice_number,
                'evd_amount': float(evd.total_amount_eur),
                'pdf_amount': float(pdf.total_amount_eur) if pdf else 0,
                'difference': float(difference),
                'issue': issue_text,
                'evd_file': evd.source_file or '',
                'pdf_file': pdf.source_file if pdf else ''
            })
        
        return rows
    
    def _generate_missing_in_pdf_data(self, missing: List[Invoice]) -> List[Dict]:
        """Generate missing in PDF sheet data."""
        rows = []
        
        for invoice in missing:
            rows.append({
                'vendor': invoice.vendor_normalized,
                'invoice_number': invoice.invoice_number,
                'amount': float(invoice.total_amount_eur),
                'date': invoice.invoice_date or '',
                'evd_file': invoice.source_file or ''
            })
        
        return rows
    
    def _generate_missing_in_evd_data(self, missing: List[Invoice]) -> List[Dict]:
        """Generate missing in EVD sheet data."""
        rows = []
        
        for invoice in missing:
            rows.append({
                'vendor': invoice.vendor_normalized,
                'invoice_number': invoice.invoice_number,
                'amount': float(invoice.total_amount_eur),
                'date': invoice.invoice_date or '',
                'pdf_file': invoice.source_file or '',
                'confidence': invoice.confidence or 0
            })
        
        return rows
    
    def _generate_by_vendor_data(self, result: ReconciliationResult) -> List[Dict]:
        """Generate by vendor summary data."""
        # Collect all vendors
        vendors = set()
        
        for match in result.matches:
            vendors.add(match.evd_invoice.vendor_normalized)
        for mismatch in result.mismatches:
            vendors.add(mismatch.evd_invoice.vendor_normalized)
        for invoice in result.missing_in_pdf:
            vendors.add(invoice.vendor_normalized)
        for invoice in result.missing_in_evd:
            vendors.add(invoice.vendor_normalized)
        
        rows = []
        
        for vendor in sorted(vendors):
            # Count by vendor
            evd_count = sum(
                1 for m in result.matches if m.evd_invoice.vendor_normalized == vendor
            ) + sum(
                1 for m in result.mismatches if m.evd_invoice.vendor_normalized == vendor
            ) + sum(
                1 for inv in result.missing_in_pdf if inv.vendor_normalized == vendor
            )
            
            pdf_count = sum(
                1 for m in result.matches if m.evd_invoice.vendor_normalized == vendor
            ) + sum(
                1 for m in result.mismatches if m.evd_invoice.vendor_normalized == vendor
            ) + sum(
                1 for inv in result.missing_in_evd if inv.vendor_normalized == vendor
            )
            
            matches = sum(
                1 for m in result.matches if m.evd_invoice.vendor_normalized == vendor
            )
            
            mismatches = sum(
                1 for m in result.mismatches if m.evd_invoice.vendor_normalized == vendor
            )
            
            missing_pdf = sum(
                1 for inv in result.missing_in_pdf if inv.vendor_normalized == vendor
            )
            
            missing_evd = sum(
                1 for inv in result.missing_in_evd if inv.vendor_normalized == vendor
            )
            
            match_rate = (matches / max(evd_count, 1)) * 100
            
            rows.append({
                'vendor': vendor,
                'evd_count': evd_count,
                'pdf_count': pdf_count,
                'matches': matches,
                'mismatches': mismatches,
                'missing_pdf': missing_pdf,
                'missing_evd': missing_evd,
                'match_rate': match_rate,
                'match_rate_display': f"{match_rate:.1f}%"
            })
        
        return rows
    
    def _generate_detailed_comparison_data(self, result: ReconciliationResult) -> List[Dict]:
        """Generate detailed comparison sheet data."""
        rows = []
        
        # Add matches
        for match in result.matches:
            rows.append(self._create_comparison_row(
                'MATCH',
                match.evd_invoice,
                match.pdf_invoice,
                ''
            ))
        
        # Add mismatches
        for mismatch in result.mismatches:
            notes = '; '.join([self._format_discrepancy(d) for d in mismatch.discrepancies])
            rows.append(self._create_comparison_row(
                'MISMATCH',
                mismatch.evd_invoice,
                mismatch.pdf_invoice,
                notes
            ))
        
        # Add missing in PDF
        for invoice in result.missing_in_pdf:
            rows.append(self._create_comparison_row(
                'NO PDF',
                invoice,
                None,
                'PDF not found'
            ))
        
        # Add missing in EVD
        for invoice in result.missing_in_evd:
            rows.append(self._create_comparison_row(
                'NO EVD',
                None,
                invoice,
                'Not in EVD'
            ))
        
        return rows
    
    def _create_comparison_row(
        self,
        status: str,
        evd: Invoice = None,
        pdf: Invoice = None,
        notes: str = ''
    ) -> Dict:
        """Create a single comparison row."""
        evd_amt = float(evd.total_amount_eur) if evd else None
        pdf_amt = float(pdf.total_amount_eur) if pdf else None
        
        # Calculate difference handling sign conventions
        # This fixes the TODO on line 533 of the original file
        difference = None
        if evd_amt is not None and pdf_amt is not None:
            # If amounts are equal under expense/credit convention (opposite signs)
            if abs(evd_amt + pdf_amt) < 0.01:
                difference = 0.0
            else:
                # Otherwise, absolute difference
                difference = abs(evd_amt - pdf_amt)
        
        return {
            'status': status,
            'vendor': (evd.vendor_normalized if evd else pdf.vendor_normalized if pdf else ''),
            'invoice_number': (evd.invoice_number if evd else pdf.invoice_number if pdf else ''),
            'evd_date': evd.invoice_date if evd else '',
            'pdf_date': pdf.invoice_date if pdf else '',
            'evd_amount': evd_amt,
            'pdf_amount': pdf_amt,
            'difference': difference,
            'evd_currency': evd.currency if evd else '',
            'pdf_currency': pdf.currency if pdf else '',
            'notes': notes
        }
    
    def _format_discrepancy(self, disc: Discrepancy) -> str:
        """Format discrepancy for display."""
        if disc.type == 'amount':
            return f"Amount: EVD={disc.evd_value:.2f} vs PDF={disc.pdf_value:.2f} (diff: {disc.difference:.2f})"
        return str(disc)
    
    def _format_percentage(self, count: int, total: int) -> str:
        """Format count as percentage of total."""
        if total == 0:
            return "0.0%"
        return f"{(count / total * 100):.1f}%"
