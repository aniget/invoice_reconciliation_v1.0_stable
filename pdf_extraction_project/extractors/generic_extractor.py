"""
Generic Invoice Extractor

Uses pattern matching to extract data from any invoice format.
Fallback extractor when vendor-specific template is not available.

Author: PDF Extraction Team
"""

import re
from datetime import datetime
from typing import Dict, Optional, List, Tuple


class GenericExtractor:
    """
    Generic extractor using multiple patterns.
    Works across different invoice formats.
    """
    
    def __init__(self):
        """Initialize with common patterns."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for various fields."""
        
        # Invoice number patterns (most common formats)
        self.invoice_patterns = [
            # English formats
            r'Invoice\s+(?:No|Number|#)[.:]?\s*([A-Z0-9\-/]+)',
            r'Invoice[:\s]+([A-Z0-9\-/]{5,})',
            r'Document\s+(?:No|Number)[.:]?\s*([A-Z0-9\-/]+)',
            r'Reference[:]?\s*([A-Z0-9\-/]+)',
            
            # Cyrillic formats
            r'Фактура\s+№\s*[:]?\s*([A-Z0-9\-/]+)',
            r'Документ\s+№\s*[:]?\s*([A-Z0-9\-/]+)',
            
            # Symbolic
            r'№[\s]*([A-Z0-9\-/]+)',
            r'#[\s]*([A-Z0-9\-/]{5,})',
            
            # Generic alphanumeric (10+ chars)
            r'\b([A-Z]{2,}\d{6,})\b',
            r'\b(\d{10,})\b',
        ]
        
        # Date patterns
        self.date_patterns = [
            # DD.MM.YYYY or DD/MM/YYYY or DD-MM-YYYY
            r'(\d{1,2}[\./-]\d{1,2}[\./-]\d{4})',
            # YYYY-MM-DD or YYYY/MM/DD
            r'(\d{4}[\./-]\d{1,2}[\./-]\d{1,2})',
            # With labels
            r'(?:Date|Data|Invoice\s+date)[:\s]+(\d{1,2}[\./-]\d{1,2}[\./-]\d{4})',
            r'(?:Дата)[:\s]+(\d{1,2}[\./-]\d{1,2}[\./-]\d{4})',
        ]
        
        # Amount patterns
        self.amount_patterns = [
            # With currency before amount
            r'(?:EUR|BGN|USD|€|лв)[\s]*(\d+[\s,]*\d*[.,]\d{2})',
            # With currency after amount
            r'(\d+[\s,]*\d*[.,]\d{2})[\s]*(?:EUR|BGN|USD|€|лв)',
            # With labels
            r'(?:Total|TOTAL|Sum|Amount|Общо|Сума)[:\s]+(\d+[\s,]*\d*[.,]\d{2})',
            # Stand-alone amounts (2 decimal places)
            r'\b(\d{1,6}[.,]\d{2})\b',
        ]
        
        # Currency patterns
        self.currency_patterns = [
            r'\b(EUR|BGN|USD)\b',
            r'(€|лв)',
        ]
        
        # Vendor patterns
        self.vendor_patterns = [
            # Look for company names in header (all caps, with EAD/LTD)
            r'([А-ЯA-Z][А-ЯA-Z\s&\.]{10,50}(?:ЕАД|EAD|ЕООД|EOOD|LTD|LLC))',
            # Labeled
            r'(?:Vendor|Supplier|From|Доставчик|От)[:\s]+([А-ЯA-Z][^\n]{5,50})',
        ]
    
    def extract(self, text: str, pdf_path: str = None) -> Dict:
        """
        Extract data using generic patterns.
        
        Args:
            text (str): Extracted PDF text
            pdf_path (str, optional): Path to PDF file
            
        Returns:
            dict: Extracted data with confidence scores
        """
        data = {
            'vendor': self._extract_vendor(text),
            'vendor_normalized': self._normalize_vendor(self._extract_vendor(text)),
            'invoice_number': self._extract_invoice_number(text),
            'invoice_date': self._extract_date(text),
            'total_amount_eur': self._extract_amount(text),
            'currency': self._extract_currency(text),
            'confidence': 0,
            'extraction_method': 'generic_patterns'
        }
        
        # Calculate confidence
        data['confidence'] = self._calculate_confidence(data, text)
        
        return data
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number with scoring."""
        candidates = []
        
        for pattern in self.invoice_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                inv_num = match.group(1).strip()
                # Score this candidate
                score = self._score_invoice_number(inv_num, text, match.start())
                candidates.append((inv_num, score))
        
        if not candidates:
            return None
        
        # Return highest scoring candidate
        best = max(candidates, key=lambda x: x[1])
        return best[0] if best[1] > 0 else None
    
    def _score_invoice_number(self, inv_num: str, text: str, position: int) -> int:
        """Score invoice number candidate by quality."""
        score = 0
        
        # Length check (typical: 6-15 characters)
        if 6 <= len(inv_num) <= 15:
            score += 10
        elif 4 <= len(inv_num) <= 20:
            score += 5
        
        # Position (earlier = better)
        if position < 500:
            score += 5
        elif position < 1000:
            score += 3
        
        # Contains both letters and numbers
        has_letters = any(c.isalpha() for c in inv_num)
        has_numbers = any(c.isdigit() for c in inv_num)
        if has_letters and has_numbers:
            score += 5
        elif has_numbers:
            score += 3
        
        # Not too many special characters
        special_count = sum(1 for c in inv_num if not c.isalnum())
        if special_count <= 2:
            score += 3
        
        return score
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract and normalize date."""
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Try to parse and normalize
                return self._normalize_date(date_str)
        return None
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date to YYYY-MM-DD format."""
        # Try different formats
        formats = [
            '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y',
            '%Y.%m.%d', '%Y/%m/%d', '%Y-%m-%d',
            '%d.%m.%y', '%d/%m/%y', '%d-%m-%y'
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return date_str  # Return as-is if can't parse
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract amount (typically the largest amount found)."""
        amounts = []
        
        for pattern in self.amount_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1)
                amount = self._parse_amount(amount_str)
                if amount and 0 < amount < 1000000:
                    amounts.append(amount)
        
        if not amounts:
            return None
        
        # Return largest amount (usually the total)
        return max(amounts)
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float."""
        try:
            # Remove spaces and convert comma to dot
            amount_str = amount_str.replace(' ', '').replace(',', '.')
            return float(amount_str)
        except (ValueError, AttributeError):
            return None
    
    def _extract_currency(self, text: str) -> str:
        """Extract currency code."""
        for pattern in self.currency_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                currency = match.group(1).upper()
                # Map symbols to codes
                if currency == '€':
                    return 'EUR'
                elif currency == 'ЛВ':
                    return 'BGN'
                return currency
        return 'EUR'  # Default
    
    def _extract_vendor(self, text: str) -> Optional[str]:
        """Extract vendor name."""
        # Check first 1000 characters (header area)
        header = text[:1000]
        
        for pattern in self.vendor_patterns:
            match = re.search(pattern, header, re.IGNORECASE)
            if match:
                vendor = match.group(1).strip()
                # Clean up
                vendor = vendor.split('\n')[0].strip()
                if len(vendor) > 5:
                    return vendor
        
        return 'UNKNOWN'
    
    def _normalize_vendor(self, vendor: str) -> str:
        """Normalize vendor name."""
        if not vendor or vendor == 'UNKNOWN':
            return 'UNKNOWN'
        
        vendor = vendor.upper().strip()
        
        # Remove common suffixes
        suffixes = ['ЕАД', 'EAD', 'ЕООД', 'EOOD', 'АД', 'AD', 'ООД', 'OOD', 
                   'LTD', 'LIMITED', 'LLC', 'INC', 'CORP']
        for suffix in suffixes:
            vendor = re.sub(rf'\s+{suffix}\.?\s*$', '', vendor, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        vendor = re.sub(r'\s+', ' ', vendor).strip()
        
        return vendor
    
    def _calculate_confidence(self, data: Dict, text: str) -> int:
        """Calculate confidence score (0-100)."""
        score = 0
        
        # Required fields
        if data.get('invoice_number'):
            score += 30
        
        if data.get('total_amount_eur'):
            score += 30
        
        # Optional fields
        if data.get('invoice_date'):
            score += 15
        
        if data.get('vendor') and data['vendor'] != 'UNKNOWN':
            score += 15
        
        if data.get('currency'):
            score += 10
        
        return min(score, 100)


# Test
if __name__ == "__main__":
    sample = """
    Invoice Number: INV-2024-12345
    Date: 15.01.2026
    Vendor: TEST COMPANY EAD
    Total Amount: 1,234.56 EUR
    """
    
    extractor = GenericExtractor()
    data = extractor.extract(sample)
    
    print("Generic Extraction Test:")
    for key, value in data.items():
        print(f"  {key}: {value}")
