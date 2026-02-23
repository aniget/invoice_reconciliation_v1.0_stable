"""
Batch EVD Extractor - Process Multiple EVD Files

Processes all EVD Excel files in a folder and combines results.
Designed for monthly reconciliation workflows.

Author: EVD Extraction Team
Date: 2026-01-29
"""

from datetime import datetime
import json
from pathlib import Path
import sys
import logging

from .evd_extractor import EVDExtractor


class BatchEVDProcessor:
    """
    Processes multiple EVD files from a folder.

    Features:
    - Processes all Excel files in input folder
    - Combines results from all files
    - Tracks which file each invoice came from
    - Generates combined summary statistics
    """

    def __init__(self, input_folder: Path):
        """
        Initialize batch processor.

        Args:
            input_folder (Path): Folder containing EVD Excel files
        """
        self.input_folder = Path(input_folder)
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'total_invoices': 0,
            'by_vendor': {},
            'by_file': {}
        }

    def find_evd_files(self):
        """
        Find all Excel files in input folder.

        Returns:
            list: List of Path objects for Excel files
        """
        excel_extensions = ['*.xlsx', '*.xlsm', '*.xls']
        files = []

        for ext in excel_extensions:
            files.extend(self.input_folder.glob(ext))

        return sorted(files)

    def process_folder(self, output_path: Path = None):
        """
        Process all EVD files in the folder.

        Args:
            output_path (Path, optional): Output JSON file path

        Returns:
            dict: Combined structured data from all files
        """
        logging.info("="*80)
        logging.info("BATCH EVD EXTRACTOR")
        logging.info("="*80)
        logging.info(f"Input folder: {self.input_folder}")
        logging.info("")

        # Find all EVD files
        evd_files = self.find_evd_files()

        if not evd_files:
            logging.info("No Excel files found in input folder")
            return {
                'metadata': {'total_invoices': 0},
                'by_vendor': {},
                'by_invoice_number': {},
                'all_invoices': []
            }

        logging.info(f"Found {len(evd_files)} Excel file(s):\n")
        for f in evd_files:
            logging.info(f"  - {f.name}")
        logging.info("")

        # Process each file
        all_invoices = []

        for evd_file in evd_files:
            try:
                logging.info(f"Processing: {evd_file.name}")

                extractor = EVDExtractor(evd_file)
                file_data = extractor.extract_and_structure()

                # Add source file to each invoice
                for invoice in file_data['all_invoices']:
                    invoice['source_file'] = evd_file.name
                    invoice['source_path'] = str(evd_file)
                    all_invoices.append(invoice)

                # Update statistics
                self.stats['files_processed'] += 1
                self.stats['by_file'][evd_file.name] = {
                    'invoice_count': file_data['metadata']['total_invoices'],
                    'total_amount': file_data['metadata']['total_amount_eur']
                }

                logging.info(
                    f"  [SUCCESS] Extracted {file_data['metadata']['total_invoices']} invoices")
                logging.info(
                    f"    Total: €{file_data['metadata']['total_amount_eur']:,.2f}")
                logging.info("")

            except Exception as e:
                logging.info(
                    f"  [ERROR] Error processing {evd_file.name}: {str(e)}")
                self.stats['files_failed'] += 1
                logging.info("")

        # Combine all results
        combined_data = self._combine_results(all_invoices)

        # Print summary
        self._print_summary(combined_data)

        # Save to file if requested
        if output_path:
            self._save_results(combined_data, output_path)

        return combined_data

    def _combine_results(self, all_invoices: list) -> dict:
        """
        Combine invoices from all files into single structure.

        Args:
            all_invoices (list): Combined list of all invoices

        Returns:
            dict: Structured combined data
        """
        # Calculate totals
        total_amount = sum(inv['total_amount_eur'] for inv in all_invoices)

        # Group by vendor
        by_vendor = {}
        for invoice in all_invoices:
            vendor = invoice['vendor_normalized']
            if vendor not in by_vendor:
                by_vendor[vendor] = {
                    'vendor_name': vendor,
                    'invoice_count': 0,
                    'total_amount': 0,
                    'invoices': []
                }

            by_vendor[vendor]['invoices'].append(invoice)
            by_vendor[vendor]['invoice_count'] += 1
            by_vendor[vendor]['total_amount'] += invoice['total_amount_eur']

        # Index by invoice number
        by_invoice_number = {}
        for invoice in all_invoices:
            inv_num = invoice['invoice_number']
            if inv_num:
                if inv_num not in by_invoice_number:
                    by_invoice_number[inv_num] = []
                by_invoice_number[inv_num].append(invoice)

        # Create combined structure
        combined = {
            'metadata': {
                'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source_folder': str(self.input_folder),
                'files_processed': self.stats['files_processed'],
                'files_failed': self.stats['files_failed'],
                'total_invoices': len(all_invoices),
                'total_vendors': len(by_vendor),
                'total_amount_eur': total_amount,
                'files': self.stats['by_file']
            },
            'by_vendor': by_vendor,
            'by_invoice_number': by_invoice_number,
            'all_invoices': all_invoices
        }

        return combined

    def _print_summary(self, data: dict):
        """Print processing summary."""
        logging.info("="*80)
        logging.info("BATCH PROCESSING SUMMARY")
        logging.info("="*80)

        metadata = data['metadata']
        logging.info(f"Files processed: {metadata['files_processed']}")
        logging.info(f"Files failed: {metadata['files_failed']}")
        logging.info(f"Total invoices: {metadata['total_invoices']}")
        logging.info(f"Total vendors: {metadata['total_vendors']}")
        logging.info(f"Total amount: €{metadata['total_amount_eur']:,.2f}")

        logging.info("\nBy File:")
        for filename, file_info in metadata['files'].items():
            logging.info(
                f"  {filename}: {file_info['invoice_count']} invoices, €{file_info['total_amount']:,.2f}")

        logging.info("\nBy Vendor:")
        for vendor, vendor_data in data['by_vendor'].items():
            logging.info(
                f"  {vendor}: {vendor_data['invoice_count']} invoices, €{vendor_data['total_amount']:,.2f}")

    def _save_results(self, data: dict, output_path: Path):
        """Save combined results to JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logging.info(f"\n[SUCCESS] Results saved to: {output_path}")


def main():
    """Main entry point."""
    logging.info("\n")

    if len(sys.argv) < 2:
        logging.info(
            "Usage: python batch_evd_extractor.py <input_folder> [output.json]")
        logging.info("\nExample:")
        logging.info("  python batch_evd_extractor.py input_evd/")
        logging.info(
            "  python batch_evd_extractor.py input_evd/ combined_evd_data.json")
        logging.info(
            "\nThe script will process all Excel files in the input folder.")
        sys.exit(1)

    input_folder = Path(sys.argv[1])
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    # Auto-generate output filename if not provided
    if not output_file:
        output_file = Path('evd_combined.json')

    # Check if input folder exists
    if not input_folder.exists():
        logging.info(f"[ERROR] Error: Input folder not found: {input_folder}")
        logging.info(f"\nCreating folder: {input_folder}")
        input_folder.mkdir(parents=True, exist_ok=True)
        logging.info(
            f"[SUCCESS] Folder created. Please add EVD Excel files to: {input_folder}")
        sys.exit(1)

    if not input_folder.is_dir():
        logging.info(f"[ERROR] Error: {input_folder} is not a directory")
        sys.exit(1)

    try:
        # Process all files
        processor = BatchEVDProcessor(input_folder)
        results = processor.process_folder(output_file)

        logging.info("\n[SUCCESS] Batch processing completed successfully!")

        return 0

    except Exception as e:
        logging.info(f"\n[ERROR] Error during batch processing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
