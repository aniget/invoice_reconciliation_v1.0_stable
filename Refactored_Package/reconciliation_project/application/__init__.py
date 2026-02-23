"""
Application Layer

Contains use cases and application services.
Orchestrates domain logic for specific business scenarios.
"""

from .report_generator import ReportDataGenerator

__all__ = ['ReportDataGenerator']
