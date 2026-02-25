"""
Job Processor

Background processing for reconciliation jobs.
This will be replaced with Celery for production scalability.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import subprocess
import logging

from saas_config.database import SessionLocal
from saas_models import ReconciliationJob, JobStatus, Invoice, SourceType

logger = logging.getLogger(__name__)


def process_reconciliation_sync(job_id: str, tenant_id: str):
    """
    Process a reconciliation job synchronously.
    
    This is a simplified version for initial deployment.
    TODO: Replace with Celery task for production.
    
    Args:
        job_id: UUID of the job to process
        tenant_id: UUID of the tenant (for isolation)
    """
    db = SessionLocal()
    
    try:
        # Get job
        job = db.query(ReconciliationJob).filter(
            ReconciliationJob.id == job_id,
            ReconciliationJob.tenant_id == tenant_id
        ).first()
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        # Update status
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Processing job {job_id}")
        
        # Process EVD file
        evd_output = Path(job.evd_file_path).parent / "evd_data.json"
        result = subprocess.run([
            sys.executable,
            '-m',
            'evd_extraction_project.evd_extractor',
            job.evd_file_path,
            str(evd_output)
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            raise Exception(f"EVD processing failed: {result.stderr}")
        
        # Load EVD data
        with open(evd_output, 'r', encoding='utf-8') as f:
            evd_data = json.load(f)
        
        # Process PDF file
        pdf_output = Path(job.pdf_file_path).parent / "pdf_data.json"
        result = subprocess.run([
            sys.executable,
            '-m',
            'pdf_extraction_project.pdf_processor',
            job.pdf_file_path,
            str(pdf_output)
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            raise Exception(f"PDF processing failed: {result.stderr}")
        
        # Load PDF data
        with open(pdf_output, 'r', encoding='utf-8') as f:
            pdf_data = json.load(f)
        
        # Run reconciliation
        from reconciliation_project.reconciliation_report import ReconciliationReportGenerator
        
        report_output = Path(job.evd_file_path).parent / f"report_{job_id}.xlsx"
        generator = ReconciliationReportGenerator()
        generator.generate_report(evd_data, pdf_data, report_output)
        
        # Store results in job
        job.evd_data = evd_data
        job.pdf_data = pdf_data
        job.report_file_path = str(report_output)
        
        # Extract summary statistics
        evd_invoices = evd_data.get('invoices', [])
        pdf_invoices = pdf_data.get('invoices', [])
        
        job.evd_invoice_count = len(evd_invoices)
        job.pdf_invoice_count = len(pdf_invoices)
        
        # Store invoices in database for searching
        _store_invoices(db, job, evd_invoices, pdf_invoices)
        
        # Calculate match statistics
        # TODO: Extract from reconciliation result
        job.matches_count = 0
        job.mismatches_count = 0
        job.match_rate = 0.0
        
        # Update status
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
        
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        
    finally:
        db.close()


def _store_invoices(db, job, evd_invoices: list, pdf_invoices: list):
    """Store invoices in database for searching."""
    
    # Store EVD invoices
    for evd in evd_invoices:
        invoice = Invoice(
            tenant_id=job.tenant_id,
            job_id=job.id,
            invoice_number=evd.get('invoice_number', ''),
            vendor_name=evd.get('vendor', ''),
            vendor_normalized=evd.get('vendor_normalized', ''),
            total_amount_eur=evd.get('total_amount_eur'),
            total_amount_bgn=evd.get('total_amount_bgn'),
            source_type=SourceType.EVD,
            source_file=job.evd_file_path,
            metadata=evd
        )
        db.add(invoice)
    
    # Store PDF invoices
    for pdf in pdf_invoices:
        invoice = Invoice(
            tenant_id=job.tenant_id,
            job_id=job.id,
            invoice_number=pdf.get('invoice_number', ''),
            vendor_name=pdf.get('vendor', ''),
            vendor_normalized=pdf.get('vendor_normalized', ''),
            total_amount_eur=pdf.get('total_amount_eur'),
            net_amount_eur=pdf.get('net_amount_eur'),
            vat_amount_eur=pdf.get('vat_amount_eur'),
            source_type=SourceType.PDF,
            source_file=job.pdf_file_path,
            extraction_method=pdf.get('extraction_method'),
            confidence=pdf.get('confidence'),
            metadata=pdf
        )
        db.add(invoice)
