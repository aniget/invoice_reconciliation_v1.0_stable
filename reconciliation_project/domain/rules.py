"""
Business Rules for Invoice Reconciliation

Contains the core business logic for:
- Normalizing data
- Matching invoices
- Validating amounts
- Calculating confidence scores

No presentation concerns, no I/O - pure business logic.
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple


class InvoiceNormalizer:
    """
    Normalizes invoice data for comparison.
    
    Handles variations in format, capitalization, and special characters.
    """
    
    @staticmethod
    def normalize_invoice_number(invoice_num: Optional[str]) -> str:
        """
        Normalize invoice number for matching.
        
        Removes common prefixes, special characters, and standardizes format.
        
        Examples:
            "INV-12345" -> "12345"
            "FAKTURA: 12345" -> "12345"
            "No. 12345" -> "12345"
        """
        if not invoice_num:
            return ""
        
        s = str(invoice_num).upper().strip()
        
        # Remove common prefixes
        s = re.sub(r'^(INV|INVOICE|DOC|FAKTURA|№|NO\.?|#)\s*[-:]?\s*', '', s)
        
        # Remove all non-alphanumeric characters
        s = re.sub(r'[^\w\d]', '', s)
        
        return s
    
    @staticmethod
    def normalize_vendor(vendor: Optional[str]) -> str:
        """
        Normalize vendor name for comparison.
        
        Standardizes capitalization and removes variations.
        """
        if not vendor:
            return ""
        
        return vendor.upper().strip()


class AmountValidator:
    """
    Validates and compares monetary amounts.
    
    Handles different conventions (expense/credit) and tolerances.
    """
    
    def __init__(self, tolerance: Decimal = Decimal('0.01')):
        """
        Initialize with tolerance level.
        
        Args:
            tolerance: Maximum acceptable difference (default 0.01 EUR)
        """
        self.tolerance = tolerance
    
    def normalize_amount(self, value: any) -> Decimal:
        """
        Convert value to Decimal for precise calculation.
        
        Args:
            value: Amount as float, int, string, or Decimal
            
        Returns:
            Decimal representation, or 0 if invalid
        """
        try:
            return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (ValueError, TypeError, AttributeError):
            return Decimal('0.00')
    
    def amounts_match(self, a: Decimal, b: Decimal) -> bool:
        """
        Check if two amounts are equal within tolerance.
        
        Args:
            a, b: Amounts to compare
            
        Returns:
            True if difference is within tolerance
        """
        return abs(a - b) <= self.tolerance
    
    def amounts_consistent(self, evd_amt: any, pdf_amt: any) -> bool:
        """
        Check if amounts are consistent considering accounting conventions.
        
        EVD and PDF may use different sign conventions:
        - EVD: expenses as positive
        - PDF: expenses as negative (or vice versa)
        
        This method checks multiple scenarios:
        1. Exact match (both positive or both negative)
        2. Magnitude match (one positive, one negative)
        3. Absolute value match
        
        Args:
            evd_amt: EVD amount
            pdf_amt: PDF amount
            
        Returns:
            True if amounts are consistent under any valid convention
        """
        evd = self.normalize_amount(evd_amt)
        pdf = self.normalize_amount(pdf_amt)
        
        # Scenario 1: Exact match
        if self.amounts_match(evd, pdf):
            return True
        
        # Scenario 2: Sign flipped (expense/credit convention)
        if self.amounts_match(evd, -pdf):
            return True
        
        # Scenario 3: Absolute value match (handle any sign)
        if self.amounts_match(abs(evd), abs(pdf)):
            return True
        
        return False
    
    def calculate_difference(self, evd_amt: any, pdf_amt: any) -> Decimal:
        """
        Calculate difference handling sign conventions.
        
        Returns 0 if amounts are consistent under any convention.
        Otherwise returns absolute difference.
        
        Args:
            evd_amt: EVD amount
            pdf_amt: PDF amount
            
        Returns:
            Decimal difference, or 0 if consistent
        """
        evd = self.normalize_amount(evd_amt)
        pdf = self.normalize_amount(pdf_amt)
        
        # If they're consistent under any convention, difference is 0
        if self.amounts_consistent(evd_amt, pdf_amt):
            return Decimal('0.00')
        
        # Otherwise, return absolute difference
        return abs(evd - pdf)


class VendorMatcher:
    """
    Matches vendors using fuzzy logic.
    
    Handles variations in company names, abbreviations, and typos.
    """
    
    @staticmethod
    def calculate_similarity(vendor1: Optional[str], vendor2: Optional[str]) -> float:
        """
        Calculate similarity score between two vendor names.
        
        Uses word-based Jaccard similarity with special cases for
        exact matches and substring containment.
        
        Args:
            vendor1, vendor2: Vendor names to compare
            
        Returns:
            Similarity score from 0.0 (no match) to 1.0 (perfect match)
        """
        if not vendor1 or not vendor2:
            return 0.0
        
        v1 = vendor1.upper().strip()
        v2 = vendor2.upper().strip()
        
        # Exact match
        if v1 == v2:
            return 1.0
        
        # Substring match (one contains the other)
        if v1 in v2 or v2 in v1:
            return 0.8
        
        # Word-based Jaccard similarity
        words1 = set(v1.split())
        words2 = set(v2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


class ConfidenceCalculator:
    """
    Calculates confidence scores for invoice matches.
    
    Weights different matching criteria to produce an overall score.
    """
    
    # Weight distribution for confidence calculation
    WEIGHTS = {
        'invoice_number': 50,  # Exact match is very strong indicator
        'amount': 30,          # Amount consistency is important
        'vendor': 20           # Vendor match provides context
    }
    
    # Minimum score to consider a match valid
    MIN_MATCH_SCORE = 50
    
    def calculate_match_confidence(
        self,
        invoice_match: bool,
        amount_consistent: bool,
        vendor_similarity: float
    ) -> Tuple[float, bool]:
        """
        Calculate overall confidence score for a match.
        
        Args:
            invoice_match: True if invoice numbers match
            amount_consistent: True if amounts are consistent
            vendor_similarity: Vendor similarity (0.0 to 1.0)
            
        Returns:
            Tuple of (confidence_score, is_valid_match)
            - confidence_score: 0-100
            - is_valid_match: True if score >= MIN_MATCH_SCORE
        """
        score = 0.0
        
        if invoice_match:
            score += self.WEIGHTS['invoice_number']
        
        if amount_consistent:
            score += self.WEIGHTS['amount']
        
        # Vendor similarity is weighted
        score += vendor_similarity * self.WEIGHTS['vendor']
        
        # Ensure score is within bounds
        score = min(100, max(0, score))
        
        is_valid = score >= self.MIN_MATCH_SCORE
        
        return score, is_valid
