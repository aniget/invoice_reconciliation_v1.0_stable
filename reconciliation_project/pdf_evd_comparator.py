"""
EVD-PDF Comparison Utility (Refactored & Clean Architecture)

Responsibilities:
- Normalize data
- Compare datasets
- Return structured comparison results
- No formatting / no Excel logic

Author: EVD Extraction Team
"""

import json
from pathlib import Path
import re
import logging


class EVDPDFComparator:

    def __init__(self, amount_tolerance=0.01):
        self.amount_tolerance = amount_tolerance

    # -------------------------
    # NORMALIZATION UTILITIES
    # -------------------------

    def normalize_invoice_number(self, invoice_num):
        if not invoice_num:
            return ""

        invoice_num = str(invoice_num).upper().strip()
        invoice_num = re.sub(
            r'^(INV|INVOICE|DOC|FAKTURA|№|NO\.?|#)\s*[-:]?\s*', '', invoice_num)
        invoice_num = re.sub(r'[^\w\d]', '', invoice_num)
        return invoice_num

    def normalize_amount(self, value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    # -------------------------
    # MATCHING RULES
    # -------------------------

    def amounts_match(self, amount1, amount2):
        return abs(amount1 - amount2) <= self.amount_tolerance

    def amounts_consistent_with_evd_sign_rules(self, evd_amount, pdf_amount):
        evd = self.normalize_amount(evd_amount)
        pdf = self.normalize_amount(pdf_amount)

        if self.amounts_match(evd, pdf):
            return True
        if self.amounts_match(abs(evd), pdf):
            return True
        if self.amounts_match(evd, -pdf):
            return True
        return False

    def fuzzy_vendor_match(self, vendor1, vendor2):
        if not vendor1 or not vendor2:
            return 0.0

        v1 = vendor1.upper()
        v2 = vendor2.upper()

        if v1 == v2:
            return 1.0

        if v1 in v2 or v2 in v1:
            return 0.8

        words1 = set(v1.split())
        words2 = set(v2.split())
        if not words1 or not words2:
            return 0.0

        return len(words1 & words2) / len(words1 | words2)

    # -------------------------
    # CORE MATCHING
    # -------------------------

    def find_matching_pdf(self, evd_invoice, pdf_candidates):

        evd_inv = self.normalize_invoice_number(
            evd_invoice.get("invoice_number"))
        evd_amt = self.normalize_amount(
            evd_invoice.get("total_amount_eur"))
        evd_vendor = evd_invoice.get("vendor_normalized", "")

        best_match = None
        best_score = 0

        for pdf in pdf_candidates:
            score = 0

            pdf_inv = self.normalize_invoice_number(
                pdf.get("invoice_number"))
            pdf_amt = self.normalize_amount(
                pdf.get("total_amount_eur"))
            pdf_vendor = pdf.get("vendor_normalized", "")

            if evd_inv and pdf_inv and evd_inv == pdf_inv:
                score += 50

            if self.amounts_consistent_with_evd_sign_rules(evd_amt, pdf_amt):
                score += 30

            score += self.fuzzy_vendor_match(evd_vendor, pdf_vendor) * 20

            if score > best_score:
                best_score = score
                best_match = pdf

        if best_score < 50:
            return None, 0

        return best_match, best_score

    # -------------------------
    # MAIN COMPARISON
    # -------------------------

    def compare_datasets(self, evd_data, pdf_data):

        evd_list = evd_data.get("all_invoices", [])
        pdf_list = pdf_data.get("all_invoices", [])

        results = {
            "summary": {
                "total_evd": len(evd_list),
                "total_pdf": len({(
                    p.get("vendor_normalized"),
                    self.normalize_invoice_number(p.get("invoice_number"))
                ) for p in pdf_list}),  # UNIQUE COUNT
                "matches": 0,
                "mismatches": 0,
                "missing_in_pdf": 0,
                "missing_in_evd": 0
            },
            "matches": [],
            "mismatches": [],
            "missing_in_pdf": [],
            "missing_in_evd": []
        }

        matched_pdf_keys = set()

        for evd in evd_list:
            vendor = evd.get("vendor_normalized", "")
            vendor_pdfs = pdf_data.get("by_vendor", {}).get(
                vendor, {}).get("invoices", [])

            match, confidence = self.find_matching_pdf(
                evd, vendor_pdfs)

            if match:
                key = (
                    match.get("vendor_normalized"),
                    self.normalize_invoice_number(
                        match.get("invoice_number"))
                )
                matched_pdf_keys.add(key)

                pdf_amt = self.normalize_amount(
                    match.get("total_amount_eur"))
                evd_amt = self.normalize_amount(
                    evd.get("total_amount_eur"))

                discrepancies = []

                if not self.amounts_consistent_with_evd_sign_rules(evd_amt, pdf_amt):
                    discrepancies.append({
                        "type": "amount",
                        "evd_value": evd_amt,
                        "pdf_value": pdf_amt,
                        "difference": abs(evd_amt - pdf_amt)
                    })

                result_obj = {
                    "evd": evd,
                    "pdf": match,
                    "confidence": confidence,
                    "discrepancies": discrepancies
                }

                if discrepancies:
                    results["mismatches"].append(result_obj)
                    results["summary"]["mismatches"] += 1
                else:
                    results["matches"].append(result_obj)
                    results["summary"]["matches"] += 1

            else:
                results["missing_in_pdf"].append(evd)
                results["summary"]["missing_in_pdf"] += 1

        # Missing in EVD
        for pdf in pdf_list:
            key = (
                pdf.get("vendor_normalized"),
                self.normalize_invoice_number(
                    pdf.get("invoice_number"))
            )
            if key not in matched_pdf_keys:
                results["missing_in_evd"].append(pdf)
                results["summary"]["missing_in_evd"] += 1

        return results
