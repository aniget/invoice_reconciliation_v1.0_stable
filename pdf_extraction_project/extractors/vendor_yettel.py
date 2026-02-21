"""
Yettel Invoice Extractor

Specialized extractor for Yettel Bulgaria EAD (formerly Telenor) invoices.
Based on analysis of Yettel invoice format.

Author: PDF Extraction Team
Date: 2026-01-29
"""

import re
from datetime import datetime
from typing import Dict, Optional


class YettelExtractor:
    """
    Extracts data from Yettel Bulgaria invoices.
    
    Yettel Invoice Format Characteristics:
    - Header: "ФАКТУРА" or "FAKTURA"
    - Invoice number format: 10-digit (e.g., 4500127511)
    - Date format: DD.MM.YYYY
    - Amount in EUR and BGN
    - Table structure with line items
    - Bilingual (Bulgarian/English mixed)
    - Supplier: Yettel (sender) → Customer: Receiver
    """
    
    VENDOR_NAME = "YETTEL"
    VENDOR_NAME_CYRILLIC = "ЙЕТТЕЛ"
    
    def __init__(self):
        """Initialize Yettel extractor with patterns."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for extraction."""
        
        # Invoice number patterns
        self.invoice_patterns = [
            r'ФАКТУРА.*?No[.:\s]*(\d{10})',
            r'FAKTURA.*?No[.:\s]*(\d{10})',
            r'No[.:\s]*(\d{10})',
            r'№[.:\s]*(\d{10})',
        ]
        
        # Date patterns
        self.date_patterns = [
            r'Дата:\s*(\d{2}\.\d{2}\.\d{4})',
            r'Date:\s*(\d{2}\.\d{2}\.\d{4})',
        ]
        
        # Total amount patterns (EUR)
        self.total_eur_patterns = [
            r'Обща\s+стойност:\s*(\d+[.,]\d{2})\s*евро',
            r'Total.*?:\s*(\d+[.,]\d{2})\s*евро',
            r'Обща\s+стойност:\s*(\d+[.,]\d{2})\s*euro',
        ]
        
        # Total amount patterns (BGN)
        self.total_bgn_patterns = [
            r'Обща\s+стойност:\s*(\d+[.,]\d{2})\s*лева',
            r'Total.*?:\s*(\d+[.,]\d{2})\s*лева',
        ]
        
        # Net amount (before VAT)
        self.net_amount_patterns = [
            r'Стойност\s+на\s+сделката:\s*(\d+[.,]\d{2})',
            r'Net\s+amount:\s*(\d+[.,]\d{2})',
        ]
        
        # VAT amount
        self.vat_patterns = [
            r'Начислен\s+ДДС:.*?(\d+[.,]\d{2})',
            r'VAT.*?20%\s*(\d+[.,]\d{2})',
            r'ДДС.*?20%\s*(\d+[.,]\d{2})',
        ]
        
        # Customer patterns (ПОЛУЧАТЕЛ = Receiver)
        self.customer_patterns = [
            r'ПОЛУЧАТЕЛ:.*?Име:\s*([^\n]+)',
            r'Receiver:.*?Name:\s*([^\n]+)',
        ]
        
        # Supplier patterns (ДОСТАВЧИК = Supplier)
        self.supplier_patterns = [
            r'ДОСТАВЧИК:.*?Име:\s*([^\n]+)',
            r'Supplier:.*?Name:\s*([^\n]+)',
        ]
        
        # Delivery/Contract number
        self.delivery_patterns = [
            r'Доставка\s+номер:\s*(\d+)',
            r'Delivery\s+number:\s*(\d+)',
        ]
    
    def detect(self, text: str) -> bool:
        """
        Detect if this is a Yettel invoice.
        
        Args:
            text (str): Extracted PDF text
            
        Returns:
            bool: True if Yettel invoice detected
        """
        text_upper = text.upper()
        
        # Check for Yettel company name (as SUPPLIER/DOSTAVCHIK)
        yettel_indicators = [
            'YETTEL',
            'ЙЕТТЕЛ',
            'YETTEL BULGARIA',
            'ЙЕТТЕЛ БЪЛГАРИЯ',
            'TELENOR'  # Old name
        ]
        
        has_vendor = any(indicator in text_upper for indicator in yettel_indicators)
        
        # Check for invoice header format
        has_invoice_header = 'ФАКТУРА' in text or 'FAKTURA' in text
        
        # Check for ДОСТАВЧИК (supplier) section
        has_supplier = 'ДОСТАВЧИК' in text or 'SUPPLIER' in text
        
        return has_vendor and (has_invoice_header or has_supplier)
    
    def extract(self, text: str, pdf_path: str = None) -> Dict:
        """
        Extract invoice data from Yettel invoice.
        
        Args:
            text (str): Extracted PDF text
            pdf_path (str, optional): Path to PDF file
            
        Returns:
            dict: Extracted invoice data
        """
        data = {
            'vendor': 'YETTEL BULGARIA',
            'vendor_normalized': 'ЙЕТТЕЛ БЪЛГАРИЯ',
            'invoice_number': self._extract_invoice_number(text),
            'invoice_date': self._extract_invoice_date(text),
            'customer': self._extract_customer(text),
            'supplier': self._extract_supplier(text),
            'delivery_number': self._extract_delivery_number(text),
            'net_amount_eur': self._extract_net_amount(text),
            'vat_amount_eur': self._extract_vat_amount(text),
            'total_amount_eur': self._extract_total_amount_eur(text),
            'total_amount_bgn': self._extract_total_amount_bgn(text),
            'currency': 'EUR',
            'confidence': 0,
            'extraction_method': 'yettel_template'
        }
        
        # Calculate confidence
        data['confidence'] = self._calculate_confidence(data)
        
        return data
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number."""
        for pattern in self.invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
        return None
    
    def _extract_invoice_date(self, text: str) -> Optional[str]:
        """Extract and format invoice date."""
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Convert DD.MM.YYYY to YYYY-MM-DD
                try:
                    date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    return date_str
        return None
    
    def _extract_customer(self, text: str) -> Optional[str]:
        """Extract customer name (ПОЛУЧАТЕЛ)."""
        for pattern in self.customer_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                customer = match.group(1).strip()
                # Clean up (remove extra info)
                customer = customer.split('\n')[0].strip()
                return customer
        return None
    
    def _extract_supplier(self, text: str) -> Optional[str]:
        """Extract supplier name (ДОСТАВЧИК - should be Yettel)."""
        for pattern in self.supplier_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                supplier = match.group(1).strip()
                supplier = supplier.split('\n')[0].strip()
                return supplier
        return None
    
    def _extract_delivery_number(self, text: str) -> Optional[str]:
        """Extract delivery/contract number."""
        for pattern in self.delivery_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_total_amount_eur(self, text: str) -> Optional[float]:
        """Extract total amount in EUR."""
        for pattern in self.total_eur_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '.')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    def _extract_total_amount_bgn(self, text: str) -> Optional[float]:
        """Extract total amount in BGN."""
        for pattern in self.total_bgn_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '.').replace(' ', '')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    def _extract_net_amount(self, text: str) -> Optional[float]:
        """Extract net amount (before VAT)."""
        for pattern in self.net_amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '.')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    def _extract_vat_amount(self, text: str) -> Optional[float]:
        """Extract VAT amount."""
        for pattern in self.vat_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '.')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    def _calculate_confidence(self, data: Dict) -> int:
        """
        Calculate extraction confidence score (0-100).
        
        Args:
            data (dict): Extracted data
            
        Returns:
            int: Confidence score
        """
        score = 0
        
        # Required fields
        if data.get('invoice_number'):
            score += 30
            # Validate format (10 digits)
            if len(data['invoice_number']) == 10 and data['invoice_number'].isdigit():
                score += 10
        
        if data.get('total_amount_eur'):
            score += 30
            # Validate reasonable amount
            if 0 < data['total_amount_eur'] < 1000000:
                score += 10
        
        if data.get('invoice_date'):
            score += 20
        
        # Optional fields
        if data.get('customer'):
            score += 5
        
        if data.get('net_amount_eur') and data.get('vat_amount_eur'):
            # Validate VAT calculation (should be ~20%)
            net = data['net_amount_eur']
            vat = data['vat_amount_eur']
            expected_vat = net * 0.20
            if abs(vat - expected_vat) < 0.1:
                score += 5
        
        return min(score, 100)
    
    def validate(self, data: Dict) -> bool:
        """
        Validate extracted data.
        
        Args:
            data (dict): Extracted data
            
        Returns:
            bool: True if data is valid
        """
        # Must have invoice number and amount
        if not data.get('invoice_number'):
            return False
        
        if not data.get('total_amount_eur'):
            return False
        
        # Invoice number should be 10 digits
        if not (len(data['invoice_number']) == 10 and data['invoice_number'].isdigit()):
            return False
        
        # Amount should be reasonable
        amount = data['total_amount_eur']
        if amount <= 0 or amount > 1000000:
            return False
        
        return True


# Test with sample text
if __name__ == "__main__":
    sample_text = """
    ФАКТУРА ОРИГИНAЛ
    No. 4500127511
    Дата: 16.01.2026
    
    ДОСТАВЧИК: ИН по ЗДДС: BG130460283
    Име: Йеттел България ЕАД
    
    ПОЛУЧАТЕЛ: ИН по ЗДДС: BG831642181
    Име: Виваком България ЕАД
    
    Доставка номер: 1700815832
    
    Стойност на сделката: 663,63 евро
    Начислен ДДС: 20% 132,73 евро
    Обща стойност: 796,36 евро
    Обща стойност: 1.557,55 лева
    """
    
    extractor = YettelExtractor()
    
    print("Detection test:")
    print(f"  Is Yettel invoice: {extractor.detect(sample_text)}")
    
    print("\nExtraction test:")
    data = extractor.extract(sample_text)
    
    for key, value in data.items():
        print(f"  {key}: {value}")
    
    print(f"\nValidation: {extractor.validate(data)}")
