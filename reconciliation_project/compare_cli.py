import json
import sys
from pdf_evd_comparator import EVDPDFComparator


def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_cli.py <evd.json> <pdf.json>")
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding="utf-8") as f:
        evd_data = json.load(f)

    with open(sys.argv[2], 'r', encoding="utf-8") as f:
        pdf_data = json.load(f)

    comparator = EVDPDFComparator()
    results = comparator.compare_datasets(evd_data, pdf_data)

    print(results["summary"])


if __name__ == "__main__":
    main()
