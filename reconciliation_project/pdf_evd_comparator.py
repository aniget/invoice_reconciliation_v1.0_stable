"""
EVD-PDF Comparison Utility

Compares extracted EVD data with PDF invoice data to find matches and discrepancies.
This module is both:
- a reusable comparison library
- a CLI entrypoint when run as a script
"""

import json
import logging
import re
from pathlib import Path


class EVDPDFComparator:
    def __init__(self, amount_tolerance=0.01):
        self.amount_tolerance = amount_tolerance

    def normalize_invoice_number(self, invoice_num):
        if not invoice_num:
            return ""
        s = str(invoice_num).upper().strip()
        s = re.sub(r'^(INV|INVOICE|DOC|FAKTURA|№|NO\.?|#)\s*[-:]?\s*', '', s)
        s = re.sub(r'[^\w\d]', '', s)
        return s

    def normalize_amount(self, value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def amounts_match(self, a, b):
        return abs(a - b) <= self.amount_tolerance

    def amounts_consistent(self, evd_amt, pdf_amt):
        # match absolute, match sign flipped, match magnitude differences
        evd = self.normalize_amount(evd_amt)
        pdf = self.normalize_amount(pdf_amt)
        if self.amounts_match(evd, pdf):
            return True
        if self.amounts_match(abs(evd), pdf):
            return True
        if self.amounts_match(evd, -pdf):
            return True
        return False

    def fuzzy_vendor_match(self, v1, v2):
        if not v1 or not v2:
            return 0.0
        w1, w2 = v1.upper(), v2.upper()
        if w1 == w2:
            return 1.0
        if w1 in w2 or w2 in w1:
            return 0.8
        s1, s2 = set(w1.split()), set(w2.split())
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / len(s1 | s2)

    def find_matching_pdf(self, evd, pdf_list):
        evd_inv = self.normalize_invoice_number(evd.get("invoice_number"))
        evd_amt = self.normalize_amount(evd.get("total_amount_eur"))
        evd_vendor = evd.get("vendor_normalized", "")
        best_match, best_score = None, 0

        for pdf in pdf_list:
            pdf_inv = self.normalize_invoice_number(pdf.get("invoice_number"))
            pdf_amt = self.normalize_amount(pdf.get("total_amount_eur", 0))
            vendor_score = self.fuzzy_vendor_match(
                evd_vendor, pdf.get("vendor_normalized", "")
            )
            score = 0
            if evd_inv and pdf_inv == evd_inv:
                score += 50
            if self.amounts_consistent(evd_amt, pdf_amt):
                score += 30
            score += vendor_score * 20

            if score > best_score:
                best_score, best_match = score, pdf

        if best_score < 50:
            return None, 0
        return best_match, best_score

    def compare_datasets(self, evd_data, pdf_data):
        evd_list = evd_data.get("all_invoices", [])
        pdf_list = pdf_data.get("all_invoices", [])

        results = {
            "summary": {
                "total_evd": len(evd_list),
                "total_pdf": len({(
                    p.get("vendor_normalized"),
                    self.normalize_invoice_number(p.get("invoice_number"))
                ) for p in pdf_list}),
                "matches": 0,
                "mismatches": 0,
                "missing_in_pdf": 0,
                "missing_in_evd": 0,
            },
            "matches": [],
            "mismatches": [],
            "missing_in_pdf": [],
            "missing_in_evd": []
        }

        matched_keys = set()

        for evd in evd_list:
            vendor = evd.get("vendor_normalized", "")
            candidate_pdfs = pdf_data.get("by_vendor", {}).get(
                vendor, {}).get("invoices", [])
            match, confidence = self.find_matching_pdf(evd, candidate_pdfs)
            if not match:
                results["missing_in_pdf"].append(evd)
                results["summary"]["missing_in_pdf"] += 1
                continue

            key = (match.get("vendor_normalized"), self.normalize_invoice_number(
                match.get("invoice_number")
            ))
            matched_keys.add(key)

            evd_amt = self.normalize_amount(evd.get("total_amount_eur"))
            pdf_amt = self.normalize_amount(match.get("total_amount_eur"))
            discrepancies = []

            if not self.amounts_consistent(evd_amt, pdf_amt):
                discrepancies.append({
                    "type": "amount",
                    "evd_value": evd_amt,
                    "pdf_value": pdf_amt,
                    "difference": abs(evd_amt - pdf_amt),
                })

            obj = {"evd": evd, "pdf": match, "confidence": confidence,
                   "discrepancies": discrepancies}

            if discrepancies:
                results["mismatches"].append(obj)
                results["summary"]["mismatches"] += 1
            else:
                results["matches"].append(obj)
                results["summary"]["matches"] += 1

        for pdf in pdf_list:
            key = (pdf.get("vendor_normalized"),
                   self.normalize_invoice_number(pdf.get("invoice_number")))
            if key not in matched_keys:
                results["missing_in_evd"].append(pdf)
                results["summary"]["missing_in_evd"] += 1

        return results


# --------------------------------------
# CLI entrypoint (optional)
# --------------------------------------
def main():
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python pdf_evd_comparator.py <evd.json> <pdf.json> [output.json]")
        sys.exit(1)

    evd_file, pdf_file = sys.argv[1], sys.argv[2]
    output_file = sys.argv[3] if len(
        sys.argv) > 3 else "comparison_results.json"

    with open(evd_file, "r", encoding="utf-8") as f:
        evd_data = json.load(f)
    with open(pdf_file, "r", encoding="utf-8") as f:
        pdf_data = json.load(f)

    cmptr = EVDPDFComparator()
    results = cmptr.compare_datasets(evd_data, pdf_data)

    print(json.dumps(results["summary"], indent=2))
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved comparison results to: {output_file}")


if __name__ == "__main__":
    main()
