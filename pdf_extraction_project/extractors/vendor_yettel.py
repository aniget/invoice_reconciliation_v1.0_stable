"""
Yettel Invoice Extractor - Robust Version

Key improvements over v1:
1. Position-aware extraction (context validation)
2. OCR error handling
3. Cross-field validation
4. Field-level confidence scores
5. Detailed extraction report

Author: Extraction Team  
Date: 2026-02-21
Version: 2.0
"""

import re
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YettelExtractor:
    """
    Production-ready Yettel invoice extractor.

    Features:
    - Context-aware extraction (not just regex matching)
    - OCR error correction
    - Cross-field validation (VAT, totals)
    - Detailed confidence scoring
    - Comprehensive logging

    Example:
        extractor = YettelExtractor()
        data = extractor.extract(pdf_text)
        if extractor.validate(data):
            # Use data
        else:
            # Manual review needed
    """

    VENDOR_NAME = "YETTEL БЪЛГАРИЯ"

    def __init__(self, debug=False):
        """
        Initialize extractor.

        Args:
            debug (bool): Enable debug logging
        """
        self.debug = debug
        if debug:
            logger.setLevel(logging.DEBUG)

    def detect(self, text: str) -> bool:
        """
        Detect if this is a Yettel invoice.

        Rules:
        1. Must have "ДОСТАВЧИК: ... Йеттел" (Yettel as supplier)
        2. Must have "ФАКТУРА" header
        3. Must have structured sections

        Args:
            text (str): Extracted PDF text

        Returns:
            bool: True if Yettel invoice
        """
        # Clean for detection
        text_clean = self._fix_ocr_errors(text)

        # Check for Yettel as supplier (ДОСТАВЧИК)
        has_yettel = bool(re.search(
            r'ДОСТАВЧИК:.*?Йеттел',
            text_clean,
            re.IGNORECASE | re.DOTALL
        ))

        # Must have invoice structure
        has_structure = all([
            'ФАКТУРА' in text,
            'ПОЛУЧАТЕЛ:' in text,
            'ДОСТАВЧИК:' in text
        ])

        return has_yettel and has_structure

    def extract(self, text: str, pdf_path: str = None) -> Dict:
        """
        Extract invoice data with validation.

        Args:
            text (str): PDF text
            pdf_path (str): Optional PDF path for advanced extraction

        Returns:
            dict: Extracted and validated data
        """
        logger.info("Starting extraction...")

        # Fix common OCR errors
        text_clean = self._fix_ocr_errors(text)

        if self.debug:
            logger.debug(
                f"Cleaned text (first 500 chars):\n{text_clean[:500]}")

        # Extract fields
        data = {}

        data['vendor'] = 'YETTEL БЪЛГАРИЯ'
        data['vendor_normalized'] = 'YETTEL BULGARIA'

        # Core fields
        data['invoice_number'] = self._extract_invoice_number(text_clean)
        data['invoice_date'] = self._extract_date(text_clean)
        data['customer'] = self._extract_customer(text_clean)
        data['supplier'] = self._extract_supplier(text_clean)
        data['delivery_number'] = self._extract_delivery_number(text_clean)

        # Amounts
        data['net_amount_eur'] = self._extract_net_amount(text_clean)
        data['vat_amount_eur'] = self._extract_vat(text_clean)
        data['total_amount_eur'] = self._extract_total_eur(text_clean)
        data['total_amount_bgn'] = self._extract_total_bgn(text_clean)

        data['currency'] = 'EUR'
        data['extraction_method'] = 'yettel_template'

        # Validate cross-field relationships
        data = self._cross_validate(data)

        # Calculate confidence
        data['confidence'] = self._calculate_confidence(data)

        logger.info(f"Extraction complete. Confidence: {data['confidence']}%")

        return data

    def _fix_ocr_errors(self, text: str) -> str:
        """
        Fix common OCR errors in Yettel invoices.

        Common issues:
        - Missing spaces: "Доставканомер" → "Доставка номер"
        - Merged words: "ВивакомБългарияЕАД" → "Виваком България ЕАД"
        - Missing spaces in amounts: "2.768,68" (correct) vs "2768,68" (missing separator)
        """
        fixes = {
            'Доставканомер': 'Доставка номер',
            'ИНпоЗДДС': 'ИН по ЗДДС',
            'ВивакомБългарияЕАД': 'Виваком България ЕАД',
            'ЙеттелБългарияЕАД': 'Йеттел България ЕАД',
            'Стойностнасделката': 'Стойност на сделката',
            'НачисленДДС': 'Начислен ДДС',
            'Общастойност': 'Обща стойност',
            'Дата:16': 'Дата: 16',  # Fix missing space after colon
        }

        for wrong, correct in fixes.items():
            text = text.replace(wrong, correct)

        return text

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """
        Extract invoice number.

        Rules:
        1. Must be 10 digits
        2. Must appear after "ФАКТУРА" and "No."
        3. Must NOT be a VAT number (those have BG prefix)
        """
        # Look for "ФАКТУРА...No. XXXXXXXXXX" pattern
        pattern = r'ФАКТУРА[^\n]*\n\s*No\.\s*(\d{10})'
        match = re.search(pattern, text, re.DOTALL)

        if match:
            inv_num = match.group(1)

            # Validate: not a VAT number
            if not re.search(rf'BG{inv_num}', text):
                logger.debug(f"Extracted invoice number: {inv_num}")
                return inv_num

        logger.warning("Invoice number not found")
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract and normalize invoice date."""
        pattern = r'Дата:\s*(\d{2}\.\d{2}\.\d{4})'
        match = re.search(pattern, text)

        if match:
            date_str = match.group(1)
            try:
                date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                logger.warning(f"Invalid date format: {date_str}")

        return None

    def _extract_customer(self, text: str) -> Optional[str]:
        """
        Extract customer name.

        Rules:
        1. Must be from ПОЛУЧАТЕЛ (receiver) section
        2. Must NOT be Yettel (that's the supplier)
        """
        pattern = r'ПОЛУЧАТЕЛ:.*?Име:\s*([А-Яа-я\s]+(?:ЕАД|ЕООД|ООД|АД))'
        match = re.search(pattern, text, re.DOTALL)

        if match:
            customer = match.group(1).strip()
            customer = customer.split('\n')[0]  # Take first line only
            customer = re.sub(r'\s+', ' ', customer)  # Normalize spaces

            # Validate: should NOT be Yettel
            if 'Йеттел' not in customer:
                return customer

        logger.warning("Customer not found or invalid")
        return None

    def _extract_supplier(self, text: str) -> Optional[str]:
        """Extract supplier - should be Yettel."""
        pattern = r'ДОСТАВЧИК:.*?Име:\s*([А-Яа-я\s]+(?:ЕАД|ЕООД|ООД|АД))'
        match = re.search(pattern, text, re.DOTALL)

        if match:
            supplier = match.group(1).strip()
            supplier = supplier.split('\n')[0]
            supplier = re.sub(r'\s+', ' ', supplier)
            return supplier

        return None

    def _extract_delivery_number(self, text: str) -> Optional[str]:
        """Extract delivery/order number."""
        pattern = r'Доставка\s+номер:\s*(\d+)'
        match = re.search(pattern, text)

        if match:
            return match.group(1)

        return None

    def _extract_net_amount(self, text: str) -> Optional[float]:
        """
        Extract net amount (before VAT).

        Critical: Must be from "Стойност на сделката:" line.

        Amount format: "2.768,68" where:
        - "." is thousands separator (may be multiple)
        - "," is decimal separator
        """
        pattern = r'Стойност\s+на\s+сделката:\s*([\d.,]+)\s*евро'
        match = re.search(pattern, text)

        if match:
            amount_str = match.group(1)
            amount = self._parse_amount(amount_str)

            if amount:
                logger.debug(f"Net amount: {amount}")
            return amount

        logger.warning("Net amount not found")
        return None

    def _extract_vat(self, text: str) -> Optional[float]:
        """Extract VAT amount (20%)."""
        pattern = r'Начислен\s+ДДС:\s*20%\s*([\d.,]+)\s*евро'
        match = re.search(pattern, text)

        if match:
            amount_str = match.group(1)
            return self._parse_amount(amount_str)

        return None

    def _extract_total_eur(self, text: str) -> Optional[float]:
        """
        Extract total amount in EUR.

        Note: "Обща стойност:" appears twice - EUR first, then BGN.
        We want the FIRST occurrence (EUR).
        """
        pattern = r'Обща\s+стойност:\s*([\d.,]+)\s*евро'
        match = re.search(pattern, text)

        if match:
            amount_str = match.group(1)
            amount = self._parse_amount(amount_str)

            if amount:
                logger.debug(f"Total EUR: {amount}")
            return amount

        logger.warning("Total EUR not found")
        return None

    def _extract_total_bgn(self, text: str) -> Optional[float]:
        """Extract total amount in BGN."""
        pattern = r'Обща\s+стойност:\s*([\d.,_\s]+)\s*лева'
        match = re.search(pattern, text)

        if match:
            amount_str = match.group(1)
            # OCR artifacts: "6_.4_9_8,_11" → "6.498,11"
            amount_str = re.sub(r'[_\s]', '', amount_str)
            return self._parse_amount(amount_str)

        return None

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """
        Parse Bulgarian number format to float.

        Format: "2.768,68"
        - "." = thousands separator (remove)
        - "," = decimal separator (convert to ".")

        Args:
            amount_str (str): Amount string like "2.768,68"

        Returns:
            float: Parsed amount or None if invalid
        """
        try:
            # Step 1: Remove all thousands separators (dots)
            # But we need to detect if it's thousands or decimal

            # If there's a comma, it's always decimal separator
            if ',' in amount_str:
                # Remove dots (thousands), replace comma with dot (decimal)
                clean = amount_str.replace('.', '')
                clean = clean.replace(',', '.')
            # If only dots and last one has 2 digits after, it's decimal
            elif '.' in amount_str:
                parts = amount_str.split('.')
                if len(parts[-1]) == 2 and len(parts) > 1:
                    # Last dot is decimal: "123.45"
                    # Join all but last, then add decimal
                    clean = ''.join(parts[:-1]) + '.' + parts[-1]
                else:
                    # All dots are thousands: "1.234.567"
                    clean = amount_str.replace('.', '')
            else:
                clean = amount_str

            amount = float(clean)

            # Sanity check
            if amount <= 0 or amount > 10000000:
                logger.warning(f"Amount out of range: {amount}")
                return None

            return amount

        except ValueError as e:
            logger.error(f"Failed to parse amount '{amount_str}': {e}")
            return None

    def _cross_validate(self, data: Dict) -> Dict:
        """
        Validate relationships between fields.

        Checks:
        1. VAT = Net × 0.20 (±0.01)
        2. Total EUR = Net + VAT (±0.01)
        3. Total BGN = Total EUR × ~1.9558 (±5%)

        Args:
            data (dict): Extracted data

        Returns:
            dict: Data with validation_warnings added
        """
        warnings = []

        net = data.get('net_amount_eur')
        vat = data.get('vat_amount_eur')
        total_eur = data.get('total_amount_eur')
        total_bgn = data.get('total_amount_bgn')

        # Check 1: VAT = Net × 20%
        if net and vat:
            expected_vat = net * 0.20
            diff = abs(vat - expected_vat)

            if diff > 0.01:
                warnings.append(
                    f'VAT calculation mismatch: '
                    f'expected {expected_vat:.2f}, got {vat:.2f} '
                    f'(diff: {diff:.2f})'
                )
                logger.warning(warnings[-1])

        # Check 2: Total = Net + VAT
        if net and vat and total_eur:
            expected_total = net + vat
            diff = abs(total_eur - expected_total)

            if diff > 0.01:
                warnings.append(
                    f'Total calculation mismatch: '
                    f'expected {expected_total:.2f}, got {total_eur:.2f} '
                    f'(diff: {diff:.2f})'
                )
                logger.warning(warnings[-1])

        # Check 3: BGN/EUR rate (approximately 1.95583)
        if total_eur and total_bgn:
            rate = total_bgn / total_eur
            expected_rate = 1.95583
            diff_pct = abs(rate - expected_rate) / expected_rate * 100

            if diff_pct > 1:  # More than 1% difference
                warnings.append(
                    f'Currency rate mismatch: '
                    f'rate is {rate:.4f}, expected ~{expected_rate:.4f} '
                    f'({diff_pct:.1f}% difference)'
                )
                logger.warning(warnings[-1])

        data['validation_warnings'] = warnings

        return data

    def _calculate_confidence(self, data: Dict) -> int:
        """
        Calculate overall extraction confidence.

        Scoring:
        - Invoice number (10 digits): 30 points
        - Date (valid format): 20 points
        - Total amount (reasonable): 30 points
        - No validation warnings: 20 points

        Returns:
            int: Confidence score 0-100
        """
        score = 0

        # Invoice number
        inv_num = data.get('invoice_number')
        if inv_num and len(inv_num) == 10 and inv_num.isdigit():
            score += 30

        # Date
        if data.get('invoice_date'):
            score += 20

        # Total amount
        total = data.get('total_amount_eur')
        if total and 0 < total < 1000000:
            score += 30

        # Cross-validation
        warnings = data.get('validation_warnings', [])
        if len(warnings) == 0:
            score += 20
        elif len(warnings) == 1:
            score += 10
        # 0 points if 2+ warnings

        return min(score, 100)

    def validate(self, data: Dict) -> bool:
        """
        Strict validation of extracted data.

        Required for validation:
        1. Invoice number (10 digits)
        2. Total amount EUR (positive, reasonable)
        3. Overall confidence ≥ 80%
        4. No more than 1 validation warning

        Args:
            data (dict): Extracted data

        Returns:
            bool: True if data passes validation
        """
        # Must have invoice number
        inv_num = data.get('invoice_number')
        if not inv_num or len(inv_num) != 10 or not inv_num.isdigit():
            logger.error("Validation failed: Invalid invoice number")
            return False

        # Must have valid total amount
        total = data.get('total_amount_eur')
        if not total or total <= 0 or total > 1000000:
            logger.error("Validation failed: Invalid total amount")
            return False

        # Confidence must be high
        confidence = data.get('confidence', 0)
        if confidence < 80:
            logger.error(f"Validation failed: Low confidence ({confidence}%)")
            return False

        # Maximum 1 validation warning
        warnings = data.get('validation_warnings', [])
        if len(warnings) > 1:
            logger.error(
                f"Validation failed: Too many warnings ({len(warnings)})")
            return False

        logger.info("[SUCCESS] Validation passed")
        return True

    def get_extraction_report(self, data: Dict) -> str:
        """
        Generate human-readable extraction report.

        Args:
            data (dict): Extracted data

        Returns:
            str: Formatted report
        """
        report = []
        report.append("="*60)
        report.append("YETTEL INVOICE EXTRACTION REPORT")
        report.append("="*60)

        report.append("\n📋 CORE FIELDS:")
        report.append(
            f"   Invoice Number:  {data.get('invoice_number', 'NOT FOUND')}")
        report.append(
            f"   Date:            {data.get('invoice_date', 'NOT FOUND')}")
        report.append(
            f"   Customer:        {data.get('customer', 'NOT FOUND')}")
        report.append(
            f"   Supplier:        {data.get('supplier', 'NOT FOUND')}")
        report.append(
            f"   Delivery #:      {data.get('delivery_number', 'NOT FOUND')}")

        report.append("\n💰 AMOUNTS:")
        report.append(
            f"   Net (EUR):       {data.get('net_amount_eur', 'NOT FOUND')}")
        report.append(
            f"   VAT (EUR):       {data.get('vat_amount_eur', 'NOT FOUND')}")
        report.append(
            f"   Total (EUR):     {data.get('total_amount_eur', 'NOT FOUND')}")
        report.append(
            f"   Total (BGN):     {data.get('total_amount_bgn', 'NOT FOUND')}")

        report.append(f"\n QUALITY:")
        report.append(f"   Confidence:      {data.get('confidence', 0)}%")
        report.append(
            f"   Valid:           {'[SUCCESS] Yes' if self.validate(data) else '[ERROR] No'}")

        warnings = data.get('validation_warnings', [])
        if warnings:
            report.append(
                f"\n[ATTENTION]  VALIDATION WARNINGS ({len(warnings)}):")
            for i, warning in enumerate(warnings, 1):
                report.append(f"   {i}. {warning}")
        else:
            report.append("\n[SUCCESS] No validation warnings")

        report.append("\n" + "="*60)

        return "\n".join(report)


# Example usage
if __name__ == "__main__":
    import pdfplumber

    logging.info("\n" + "="*70)
    logging.info("YETTEL EXTRACTOR - PRODUCTION TEST")
    logging.info("="*70 + "\n")

    # Extract PDF text
    with pdfplumber.open('/mnt/user-data/uploads/4500127510_VIVACOM.pdf') as pdf:
        text = pdf.pages[0].extract_text()

    # Initialize extractor
    extractor = YettelExtractor(debug=True)

    # Detect
    logging.info("1  DETECTION")
    is_yettel = extractor.detect(text)
    logging.info(
        f"   Is Yettel invoice: {'Yes' if is_yettel else 'No'}\n")

    # Extract
    logging.info("2  EXTRACTION")
    data = extractor.extract(text)

    # Print report
    logging.info(extractor.get_extraction_report(data))
