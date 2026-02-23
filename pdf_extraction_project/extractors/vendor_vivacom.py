"""
Vivacom Invoice Extractor

Specialized extractor for Vivacom Bulgaria EAD invoices.
Based on analysis of Vivacom invoice format.

Author: PDF Extraction Team
Date: 2026-01-29
"""

import re
from datetime import datetime
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VivacomExtractor:
    """
    Extracts data from Vivacom Bulgaria invoices.

    Vivacom Invoice Format Characteristics:
    - Header: "INVOICE / ФАКТУРА №:"
    - Invoice number: 10-digit format (e.g., 0063266046)
    - Date format: DD.MM.YYYY
    - Amount in EUR and BGN
    - Structured layout with clear labels
    - Bilingual (English/Bulgarian)
    """

    VENDOR_NAME = "VIVACOM"
    VENDOR_NAME_CYRILLIC = "ВИВАКОМ"

    def __init__(self):
        """Initialize Vivacom extractor with patterns."""
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for extraction."""

        # Invoice number patterns
        self.invoice_patterns = [
            r'INVOICE\s+/\s+ФАКТУРА\s+№:\s*(\d{10})',
            r'ФАКТУРА\s+№:\s*(\d{10})',
            r'Invoice.*?№:\s*(\d{10})',
        ]

        # Date patterns
        self.date_patterns = [
            r'Invoice\s+date\s+/\s+Дата\s+на\s+фактура\s+(\d{2}\.\d{2}\.\d{4})',
            r'Дата\s+на\s+фактура\s+(\d{2}\.\d{2}\.\d{4})',
        ]

        # Amount patterns (EUR)
        self.amount_eur_patterns = [
            r'Total\s+amount\s+to\s+be\s+paid\s+EUR[\s\r\n]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
            r'Обща\s+сума\s+за\s+плащане\s+EUR[\s\r\n]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        ]

        # Amount patterns (BGN)
        self.amount_bgn_patterns = [
            r'Total\s+amount\s+to\s+be\s+paid\s+BGN[\s\r\n]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
            r'Обща\s+сума\s+за\s+плащане\s+BGN[\s\r\n]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        ]

        # Net amount (before VAT)
        self.net_amount_patterns = [
            r'Total\s+amount\s+before\s+VAT[\s\r\n]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
            r'Обща\s+стойност\s+без\s+ДДС[\s\r\n]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        ]

        # VAT amount
        self.vat_patterns = [
            r'VAT.*?20%\s+(\d+(?:[.,]\d{3})*[.,]\d{2})',
            r'ДДС.*?20%\s+(\d+(?:[.,]\d{3})*[.,]\d{2})',
        ]

        # Customer patterns (invoice recipient)
        self.customer_patterns = [
            r'Customer\s+/\s+Клиент\s+([А-ЯA-Z][^\n]+)',
            r'Клиент\s+([А-ЯA-Z][^\n]+)',
        ]

        # Contract number
        self.contract_patterns = [
            r'Contract\s+No.*?(\d+\s+/\s+\d{2}\.\d{1,2}\.\d{4})',
            r'Договор\s+No\s+(\d+\s+/\s+\d{2}\.\d{1,2}\.\d{4})',
        ]

    def detect(self, text: str) -> bool:
        """
        Detect if this is a Vivacom invoice.

        Args:
            text (str): Extracted PDF text

        Returns:
            bool: True if Vivacom invoice detected
        """
        text_upper = text.upper()

        # Check for Vivacom company name
        vivacom_indicators = [
            'VIVACOM BULGARIA',
            'ВИВАКОМ БЪЛГАРИЯ',
            'VIVACOM BULGARIA EAD',
            'ВИВАКОМ БЪЛГАРИЯ ЕАД'
        ]

        has_vendor = any(
            indicator in text_upper for indicator in vivacom_indicators)

        # Check for invoice header format
        has_invoice_header = 'INVOICE / ФАКТУРА' in text or 'INVOICE/ФАКТУРА' in text

        return has_vendor and has_invoice_header

    def extract(self, text: str, pdf_path: str = None) -> Dict:
        """
        Extract invoice data from Vivacom invoice.

        Args:
            text (str): Extracted PDF text
            pdf_path (str, optional): Path to PDF file

        Returns:
            dict: Extracted invoice data
        """
        data = {
            'vendor': 'VIVACOM BULGARIA',
            'vendor_normalized': 'ВИВАКОМ БЪЛГАРИЯ',
            'invoice_number': self._extract_invoice_number(text),
            'invoice_date': self._extract_invoice_date(text),
            'customer': self._extract_customer(text),
            'contract_number': self._extract_contract_number(text),
            'net_amount_eur': self._extract_net_amount(text),
            'vat_amount_eur': self._extract_vat_amount(text),
            'total_amount_eur': self._extract_total_amount_eur(text),
            'total_amount_bgn': self._extract_total_amount_bgn(text),
            'currency': 'EUR',
            'confidence': 0,
            'extraction_method': 'vivacom_template'
        }

        # Calculate confidence
        data['confidence'] = self._calculate_confidence(data)

        logger.info(
            f"WWWWWWWWWWWWWWWWWW Extracted total amount in EUR: {data['total_amount_eur']}")

        return data

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number."""
        for pattern in self.invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
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
        """Extract customer name."""
        for pattern in self.customer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                customer = match.group(1).strip()
                # Clean up (remove extra info)
                customer = customer.split('\n')[0].strip()
                return customer
        return None

    def _extract_contract_number(self, text: str) -> Optional[str]:
        """Extract contract number."""
        for pattern in self.contract_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_total_amount_eur(self, text: str) -> Optional[float]:
        """Extract total amount in EUR."""
        for pattern in self.amount_eur_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1)

                # Handle European format: 1.829,36 -> 1829.36
                if '.' in amount_str and ',' in amount_str:
                    # Remove thousands separator (dot)
                    amount_str = amount_str.replace('.', '')

                # Replace decimal separator (comma) with dot
                amount_str = amount_str.replace(',', '.')

                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None

    def _extract_total_amount_bgn(self, text: str) -> Optional[float]:
        """Extract total amount in BGN."""
        for pattern in self.amount_bgn_patterns:
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
    INVOICE / ФАКТУРА №: 0063266046
    Invoice date / Дата на фактура 16.01.2026
    Customer / Клиент
    ЙЕТТЕЛ БЪЛГАРИЯ ЕАД
    Contract No/Договор No 5689 / 10.5.2007
    Total amount before VAT / Обща стойност без ДДС 752,85
    VAT rate and amount / ДДС ставка и сума 20% 150,57
    Total amount to be paid EUR / Обща сума за плащане EUR 903,42
    Total amount to be paid BGN / Обща сума за плащане BGN 1.766,94
    Vivacom Bulgaria EAD
    """

    extractor = VivacomExtractor()

    logger.info("Detection test:")
    logger.info(f"  Is Vivacom invoice: {extractor.detect(sample_text)}")

    logger.info("\nExtraction test:")
    data = extractor.extract(sample_text)

    for key, value in data.items():
        logger.info(f"  {key}: {value}")

    logger.info(f"\nValidation: {extractor.validate(data)}")
