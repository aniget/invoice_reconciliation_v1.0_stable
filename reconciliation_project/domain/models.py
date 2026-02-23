"""
Domain Models for Invoice Reconciliation

Pure business entities with no external dependencies.
Represents the core concepts of the reconciliation domain.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from decimal import Decimal


@dataclass
class Invoice:
    """
    Core invoice entity.
    
    Represents an invoice from either EVD or PDF source.
    Uses Decimal for precise monetary calculations.
    """
    invoice_number: str
    vendor_normalized: str
    total_amount_eur: Decimal
    currency: str = "EUR"
    invoice_date: Optional[str] = None
    source_type: Optional[str] = None  # 'evd' or 'pdf'
    source_file: Optional[str] = None
    
    # Additional fields (flexible)
    net_amount_eur: Optional[Decimal] = None
    vat_amount_eur: Optional[Decimal] = None
    customer: Optional[str] = None
    vendor: Optional[str] = None
    confidence: Optional[int] = None
    
    def __post_init__(self):
        """Ensure amounts are Decimal for precision."""
        if not isinstance(self.total_amount_eur, Decimal):
            self.total_amount_eur = Decimal(str(self.total_amount_eur))
        
        if self.net_amount_eur and not isinstance(self.net_amount_eur, Decimal):
            self.net_amount_eur = Decimal(str(self.net_amount_eur))
        
        if self.vat_amount_eur and not isinstance(self.vat_amount_eur, Decimal):
            self.vat_amount_eur = Decimal(str(self.vat_amount_eur))


@dataclass
class Discrepancy:
    """Represents a mismatch between EVD and PDF invoice data."""
    type: str  # 'amount', 'date', 'vendor', etc.
    evd_value: any
    pdf_value: any
    difference: Optional[any] = None
    
    def __str__(self):
        if self.difference is not None:
            return f"{self.type}: EVD={self.evd_value}, PDF={self.pdf_value}, diff={self.difference}"
        return f"{self.type}: EVD={self.evd_value}, PDF={self.pdf_value}"


@dataclass
class InvoiceMatch:
    """
    Represents a matched pair of EVD and PDF invoices.
    
    Can be a perfect match or have discrepancies.
    """
    evd_invoice: Invoice
    pdf_invoice: Optional[Invoice]
    confidence: float = 0.0
    discrepancies: List[Discrepancy] = field(default_factory=list)
    
    @property
    def is_perfect_match(self) -> bool:
        """True if no discrepancies exist."""
        return len(self.discrepancies) == 0
    
    @property
    def has_pdf(self) -> bool:
        """True if PDF invoice was found."""
        return self.pdf_invoice is not None


@dataclass
class ReconciliationResult:
    """
    Complete reconciliation results.
    
    Contains all matches, mismatches, and unmatched invoices.
    """
    matches: List[InvoiceMatch] = field(default_factory=list)
    mismatches: List[InvoiceMatch] = field(default_factory=list)
    missing_in_pdf: List[Invoice] = field(default_factory=list)
    missing_in_evd: List[Invoice] = field(default_factory=list)
    
    @property
    def total_evd(self) -> int:
        """Total EVD invoices processed."""
        return len(self.matches) + len(self.mismatches) + len(self.missing_in_pdf)
    
    @property
    def total_pdf(self) -> int:
        """Total unique PDF invoices processed."""
        pdf_count = len(self.matches) + len(self.mismatches) + len(self.missing_in_evd)
        return pdf_count
    
    @property
    def match_rate(self) -> float:
        """Percentage of perfect matches."""
        if self.total_evd == 0:
            return 0.0
        return (len(self.matches) / self.total_evd) * 100
    
    def to_summary_dict(self) -> dict:
        """Convert to summary dictionary for backward compatibility."""
        return {
            'summary': {
                'total_evd': self.total_evd,
                'total_pdf': self.total_pdf,
                'matches': len(self.matches),
                'mismatches': len(self.mismatches),
                'missing_in_pdf': len(self.missing_in_pdf),
                'missing_in_evd': len(self.missing_in_evd),
                'match_rate': self.match_rate
            },
            'matches': [self._match_to_dict(m) for m in self.matches],
            'mismatches': [self._match_to_dict(m) for m in self.mismatches],
            'missing_in_pdf': [self._invoice_to_dict(inv) for inv in self.missing_in_pdf],
            'missing_in_evd': [self._invoice_to_dict(inv) for inv in self.missing_in_evd]
        }
    
    def _match_to_dict(self, match: InvoiceMatch) -> dict:
        """Convert match to dictionary."""
        return {
            'evd': self._invoice_to_dict(match.evd_invoice),
            'pdf': self._invoice_to_dict(match.pdf_invoice) if match.pdf_invoice else None,
            'confidence': match.confidence,
            'discrepancies': [
                {
                    'type': d.type,
                    'evd_value': float(d.evd_value) if isinstance(d.evd_value, Decimal) else d.evd_value,
                    'pdf_value': float(d.pdf_value) if isinstance(d.pdf_value, Decimal) else d.pdf_value,
                    'difference': float(d.difference) if isinstance(d.difference, Decimal) else d.difference
                }
                for d in match.discrepancies
            ]
        }
    
    def _invoice_to_dict(self, invoice: Optional[Invoice]) -> Optional[dict]:
        """Convert invoice to dictionary."""
        if not invoice:
            return None
        
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
