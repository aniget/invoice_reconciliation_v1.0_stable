"""
Reconciliation Service

Core business logic for matching EVD and PDF invoices.
Uses domain models and business rules.
No presentation logic, no file I/O.
"""

from typing import List, Dict, Optional, Set, Tuple
from decimal import Decimal

from .models import Invoice, InvoiceMatch, Discrepancy, ReconciliationResult
from .rules import (
    InvoiceNormalizer,
    AmountValidator,
    VendorMatcher,
    ConfidenceCalculator
)


class ReconciliationService:
    """
    Service for reconciling EVD and PDF invoices.
    
    Pure business logic - orchestrates matching process using domain rules.
    """
    
    def __init__(self, amount_tolerance: Decimal = Decimal('0.01')):
        """
        Initialize service with business rule components.
        
        Args:
            amount_tolerance: Tolerance for amount comparisons
        """
        self.normalizer = InvoiceNormalizer()
        self.amount_validator = AmountValidator(tolerance=amount_tolerance)
        self.vendor_matcher = VendorMatcher()
        self.confidence_calc = ConfidenceCalculator()
    
    def reconcile(
        self,
        evd_invoices: List[Invoice],
        pdf_invoices: List[Invoice],
        pdf_by_vendor: Optional[Dict[str, List[Invoice]]] = None
    ) -> ReconciliationResult:
        """
        Perform complete reconciliation of EVD and PDF invoices.
        
        Args:
            evd_invoices: List of EVD invoices
            pdf_invoices: List of PDF invoices
            pdf_by_vendor: Optional pre-grouped PDF invoices by vendor
            
        Returns:
            ReconciliationResult with matches, mismatches, and unmatched invoices
        """
        result = ReconciliationResult()
        
        # Track which PDF invoices have been matched
        matched_pdf_keys: Set[Tuple[str, str]] = set()
        
        # Group PDFs by vendor if not provided
        if pdf_by_vendor is None:
            pdf_by_vendor = self._group_by_vendor(pdf_invoices)
        
        # Match each EVD invoice
        for evd_invoice in evd_invoices:
            match_result = self._match_evd_invoice(
                evd_invoice,
                pdf_by_vendor,
                matched_pdf_keys
            )
            
            if match_result is None:
                # No PDF found
                result.missing_in_pdf.append(evd_invoice)
            elif match_result.is_perfect_match:
                result.matches.append(match_result)
            else:
                result.mismatches.append(match_result)
        
        # Find unmatched PDF invoices
        for pdf_invoice in pdf_invoices:
            pdf_key = self._get_invoice_key(pdf_invoice)
            if pdf_key not in matched_pdf_keys:
                result.missing_in_evd.append(pdf_invoice)
        
        return result
    
    def _match_evd_invoice(
        self,
        evd_invoice: Invoice,
        pdf_by_vendor: Dict[str, List[Invoice]],
        matched_keys: Set[Tuple[str, str]]
    ) -> Optional[InvoiceMatch]:
        """
        Find best matching PDF invoice for an EVD invoice.
        
        Args:
            evd_invoice: EVD invoice to match
            pdf_by_vendor: PDF invoices grouped by vendor
            matched_keys: Set of already matched PDF keys
            
        Returns:
            InvoiceMatch if found, None if no match
        """
        # Get candidate PDFs from same vendor
        vendor = evd_invoice.vendor_normalized
        candidate_pdfs = pdf_by_vendor.get(vendor, [])
        
        # Find best match
        best_match = None
        best_score = 0.0
        
        for pdf_invoice in candidate_pdfs:
            # Skip if already matched
            pdf_key = self._get_invoice_key(pdf_invoice)
            if pdf_key in matched_keys:
                continue
            
            # Calculate match score
            score, is_valid = self._calculate_match_score(evd_invoice, pdf_invoice)
            
            if is_valid and score > best_score:
                best_score = score
                best_match = pdf_invoice
        
        if best_match is None:
            return None
        
        # Mark as matched
        matched_keys.add(self._get_invoice_key(best_match))
        
        # Create match result with discrepancies
        discrepancies = self._find_discrepancies(evd_invoice, best_match)
        
        return InvoiceMatch(
            evd_invoice=evd_invoice,
            pdf_invoice=best_match,
            confidence=best_score,
            discrepancies=discrepancies
        )
    
    def _calculate_match_score(
        self,
        evd_invoice: Invoice,
        pdf_invoice: Invoice
    ) -> Tuple[float, bool]:
        """
        Calculate match score between two invoices.
        
        Args:
            evd_invoice: EVD invoice
            pdf_invoice: PDF invoice
            
        Returns:
            Tuple of (score, is_valid_match)
        """
        # Normalize invoice numbers
        evd_num = self.normalizer.normalize_invoice_number(evd_invoice.invoice_number)
        pdf_num = self.normalizer.normalize_invoice_number(pdf_invoice.invoice_number)
        
        # Check criteria
        invoice_match = (evd_num == pdf_num) if evd_num and pdf_num else False
        
        amount_consistent = self.amount_validator.amounts_consistent(
            evd_invoice.total_amount_eur,
            pdf_invoice.total_amount_eur
        )
        
        vendor_similarity = self.vendor_matcher.calculate_similarity(
            evd_invoice.vendor_normalized,
            pdf_invoice.vendor_normalized
        )
        
        # Calculate confidence
        return self.confidence_calc.calculate_match_confidence(
            invoice_match,
            amount_consistent,
            vendor_similarity
        )
    
    def _find_discrepancies(
        self,
        evd_invoice: Invoice,
        pdf_invoice: Invoice
    ) -> List[Discrepancy]:
        """
        Identify discrepancies between matched invoices.
        
        Args:
            evd_invoice: EVD invoice
            pdf_invoice: PDF invoice
            
        Returns:
            List of discrepancies found
        """
        discrepancies = []
        
        # Check amount discrepancy
        if not self.amount_validator.amounts_consistent(
            evd_invoice.total_amount_eur,
            pdf_invoice.total_amount_eur
        ):
            difference = self.amount_validator.calculate_difference(
                evd_invoice.total_amount_eur,
                pdf_invoice.total_amount_eur
            )
            
            discrepancies.append(Discrepancy(
                type='amount',
                evd_value=evd_invoice.total_amount_eur,
                pdf_value=pdf_invoice.total_amount_eur,
                difference=difference
            ))
        
        # Could add more discrepancy checks here:
        # - Date discrepancies
        # - Currency discrepancies
        # - etc.
        
        return discrepancies
    
    def _group_by_vendor(
        self,
        invoices: List[Invoice]
    ) -> Dict[str, List[Invoice]]:
        """
        Group invoices by normalized vendor name.
        
        Args:
            invoices: List of invoices to group
            
        Returns:
            Dictionary mapping vendor to list of invoices
        """
        grouped: Dict[str, List[Invoice]] = {}
        
        for invoice in invoices:
            vendor = invoice.vendor_normalized
            if vendor not in grouped:
                grouped[vendor] = []
            grouped[vendor].append(invoice)
        
        return grouped
    
    def _get_invoice_key(self, invoice: Invoice) -> Tuple[str, str]:
        """
        Get unique key for invoice (vendor + normalized number).
        
        Args:
            invoice: Invoice to get key for
            
        Returns:
            Tuple of (vendor, normalized_invoice_number)
        """
        normalized_num = self.normalizer.normalize_invoice_number(
            invoice.invoice_number
        )
        return (invoice.vendor_normalized, normalized_num)
