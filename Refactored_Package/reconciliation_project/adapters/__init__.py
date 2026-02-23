"""
Adapters Layer

Handles conversion between external formats and internal domain models.
Isolates the domain from external data structures.
"""

from .json_adapter import JSONToInvoiceAdapter, InvoiceToJSONAdapter

__all__ = ['JSONToInvoiceAdapter', 'InvoiceToJSONAdapter']
