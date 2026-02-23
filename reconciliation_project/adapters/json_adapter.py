"""
Data Adapters

Convert between external JSON format and internal domain models.
Handles the impedance mismatch between file format and business logic.
"""

from typing import List, Dict
from decimal import Decimal

from ..domain.models import Invoice


class JSONToInvoiceAdapter:
    """
    Converts JSON invoice data to domain Invoice objects.
    
    Handles variations in field names and data types from different sources.
    """
    
    @staticmethod
    def from_evd_json(evd_data: dict) -> Invoice:
        """
        Convert EVD JSON format to Invoice.
        
        Args:
            evd_data: Dictionary from EVD extraction
            
        Returns:
            Invoice domain object
        """
        return Invoice(
            invoice_number=evd_data.get('invoice_number', ''),
            vendor_normalized=evd_data.get('vendor_normalized', ''),
            vendor=evd_data.get('vendor', ''),
            total_amount_eur=Decimal(str(evd_data.get('total_amount_eur', 0))),
            currency=evd_data.get('currency', 'EUR'),
            invoice_date=evd_data.get('invoice_date'),
            source_type='evd',
            source_file=evd_data.get('source_file'),
            net_amount_eur=Decimal(str(evd_data['net_amount_eur'])) if evd_data.get('net_amount_eur') else None,
            vat_amount_eur=Decimal(str(evd_data['vat_amount_eur'])) if evd_data.get('vat_amount_eur') else None,
            customer=evd_data.get('customer')
        )
    
    @staticmethod
    def from_pdf_json(pdf_data: dict) -> Invoice:
        """
        Convert PDF JSON format to Invoice.
        
        Args:
            pdf_data: Dictionary from PDF extraction
            
        Returns:
            Invoice domain object
        """
        return Invoice(
            invoice_number=pdf_data.get('invoice_number', ''),
            vendor_normalized=pdf_data.get('vendor_normalized', ''),
            vendor=pdf_data.get('vendor', ''),
            total_amount_eur=Decimal(str(pdf_data.get('total_amount_eur', 0))),
            currency=pdf_data.get('currency', 'EUR'),
            invoice_date=pdf_data.get('invoice_date'),
            source_type='pdf',
            source_file=pdf_data.get('filename') or pdf_data.get('source_file'),
            net_amount_eur=Decimal(str(pdf_data['net_amount_eur'])) if pdf_data.get('net_amount_eur') else None,
            vat_amount_eur=Decimal(str(pdf_data['vat_amount_eur'])) if pdf_data.get('vat_amount_eur') else None,
            customer=pdf_data.get('customer'),
            confidence=pdf_data.get('confidence')
        )
    
    @staticmethod
    def from_json_dataset(data: dict, source_type: str) -> List[Invoice]:
        """
        Convert complete JSON dataset to list of Invoices.
        
        Args:
            data: Complete EVD or PDF JSON dataset
            source_type: 'evd' or 'pdf'
            
        Returns:
            List of Invoice domain objects
        """
        invoices = []
        invoice_list = data.get('all_invoices', [])
        
        for inv_data in invoice_list:
            if source_type == 'evd':
                invoice = JSONToInvoiceAdapter.from_evd_json(inv_data)
            else:
                invoice = JSONToInvoiceAdapter.from_pdf_json(inv_data)
            
            invoices.append(invoice)
        
        return invoices
    
    @staticmethod
    def extract_vendor_grouping(data: dict, source_type: str) -> Dict[str, List[Invoice]]:
        """
        Extract pre-grouped vendor data from JSON.
        
        Args:
            data: Complete EVD or PDF JSON dataset
            source_type: 'evd' or 'pdf'
            
        Returns:
            Dictionary mapping vendor to list of invoices
        """
        vendor_groups = {}
        by_vendor = data.get('by_vendor', {})
        
        for vendor, vendor_data in by_vendor.items():
            invoices = []
            for inv_data in vendor_data.get('invoices', []):
                if source_type == 'evd':
                    invoice = JSONToInvoiceAdapter.from_evd_json(inv_data)
                else:
                    invoice = JSONToInvoiceAdapter.from_pdf_json(inv_data)
                invoices.append(invoice)
            
            vendor_groups[vendor] = invoices
        
        return vendor_groups


class InvoiceToJSONAdapter:
    """
    Converts domain Invoice objects back to JSON format.
    
    For backward compatibility and serialization.
    """
    
    @staticmethod
    def to_json(invoice: Invoice) -> dict:
        """
        Convert Invoice to JSON-serializable dictionary.
        
        Args:
            invoice: Invoice domain object
            
        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            'invoice_number': invoice.invoice_number,
            'vendor_normalized': invoice.vendor_normalized,
            'vendor': invoice.vendor,
            'total_amount_eur': float(invoice.total_amount_eur),
            'currency': invoice.currency,
            'invoice_date': invoice.invoice_date,
            'source_type': invoice.source_type,
            'source_file': invoice.source_file,
            'net_amount_eur': float(invoice.net_amount_eur) if invoice.net_amount_eur else None,
            'vat_amount_eur': float(invoice.vat_amount_eur) if invoice.vat_amount_eur else None,
            'customer': invoice.customer,
            'confidence': invoice.confidence
        }
