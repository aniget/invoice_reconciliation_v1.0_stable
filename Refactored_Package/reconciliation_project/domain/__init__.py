"""
Domain Layer

Contains core business logic and rules.
No external dependencies, no I/O, no presentation concerns.

This is the heart of the application - all business rules live here.
"""

from .models import Invoice, Discrepancy, InvoiceMatch, ReconciliationResult
from .service import ReconciliationService
from .rules import (
    InvoiceNormalizer,
    AmountValidator,
    VendorMatcher,
    ConfidenceCalculator
)

__all__ = [
    'Invoice',
    'Discrepancy',
    'InvoiceMatch',
    'ReconciliationResult',
    'ReconciliationService',
    'InvoiceNormalizer',
    'AmountValidator',
    'VendorMatcher',
    'ConfidenceCalculator',
]
