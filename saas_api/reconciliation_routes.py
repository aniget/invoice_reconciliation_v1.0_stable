"""
Reconciliation API Routes

Endpoints for creating and managing reconciliation jobs.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import uuid
import shutil

from saas_config import get_db, settings, tenant_context
from saas_models import User, Tenant, ReconciliationJob, JobStatus, AuditLog
from .auth_dependencies import get_current_user, get_current_active_tenant


router = APIRouter(prefix="/reconciliations", tags=["reconciliations"])


# Request/Response Models
class JobResponse(BaseModel):
    """Job response model."""
    id: str
    status: str
    created_at: datetime
    evd_invoice_count: Optional[int]
    pdf_invoice_count: Optional[int]
    matches_count: Optional[int]
    mismatches_count: Optional[int]
    match_rate: Optional[float]
    report_file_path: Optional[str]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Paginated job list response."""
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobStatsResponse(BaseModel):
    """Job statistics response."""
    total_jobs: int
    pending: int
    processing: int
    completed: int
    failed: int
    jobs_this_month: int
    monthly_limit: int


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_reconciliation(
    evd_file: UploadFile = File(..., description="EVD Excel file"),
    pdf_file: UploadFile = File(..., description="PDF invoice file"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: Session = Depends(get_db)
):
    """
    Create a new reconciliation job.
    
    Uploads files and queues job for background processing.
    """
    # Check monthly limit
    if tenant.jobs_this_month >= tenant.jobs_per_month:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly job limit reached ({tenant.jobs_per_month}). Upgrade your plan."
        )
    
    # Validate file types
    if not evd_file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EVD file must be Excel format (.xlsx or .xls)"
        )
    
    if not pdf_file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF file must be PDF format (.pdf)"
        )
    
    # Validate file sizes
    max_size = settings.max_upload_size_mb * 1024 * 1024  # Convert MB to bytes
    
    # Create job
    job = ReconciliationJob(
        tenant_id=tenant.id,
        user_id=user.id,
        status=JobStatus.PENDING
    )
    db.add(job)
    db.flush()  # Get job ID
    
    # Create tenant-specific upload directory
    upload_dir = settings.upload_dir / str(tenant.id) / str(job.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded files
    evd_path = upload_dir / f"evd_{evd_file.filename}"
    pdf_path = upload_dir / f"pdf_{pdf_file.filename}"
    
    with open(evd_path, "wb") as f:
        shutil.copyfileobj(evd_file.file, f)
    
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(pdf_file.file, f)
    
    # Update job with file paths
    job.evd_file_path = str(evd_path)
    job.pdf_file_path = str(pdf_path)
    
    # Increment tenant job count
    tenant.jobs_this_month += 1
    
    # Audit log
    audit = AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        action="job.created",
        resource_type="job",
        resource_id=job.id,
        details={
            "evd_file": evd_file.filename,
            "pdf_file": pdf_file.filename
        }
    )
    db.add(audit)
    
    db.commit()
    db.refresh(job)
    
    # Queue job for background processing
    # TODO: Replace with Celery task
    # process_reconciliation_task.delay(str(job.id), str(tenant.id))
    
    # For now, add to background tasks (runs in same process)
    from .job_processor import process_reconciliation_sync
    background_tasks.add_task(process_reconciliation_sync, str(job.id), str(tenant.id))
    
    return JobResponse(
        id=str(job.id),
        status=job.status.value,
        created_at=job.created_at,
        evd_invoice_count=job.evd_invoice_count,
        pdf_invoice_count=job.pdf_invoice_count,
        matches_count=job.matches_count,
        mismatches_count=job.mismatches_count,
        match_rate=float(job.match_rate) if job.match_rate else None,
        report_file_path=job.report_file_path,
        error_message=job.error_message
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get status and details of a specific job.
    
    Includes tenant isolation - users can only see their own tenant's jobs.
    """
    job = db.query(ReconciliationJob).filter(
        ReconciliationJob.id == job_id,
        ReconciliationJob.tenant_id == user.tenant_id  # Tenant isolation
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponse(
        id=str(job.id),
        status=job.status.value,
        created_at=job.created_at,
        evd_invoice_count=job.evd_invoice_count,
        pdf_invoice_count=job.pdf_invoice_count,
        matches_count=job.matches_count,
        mismatches_count=job.mismatches_count,
        match_rate=float(job.match_rate) if job.match_rate else None,
        report_file_path=job.report_file_path,
        error_message=job.error_message
    )


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all jobs for the current tenant.
    
    Supports pagination and filtering by status.
    """
    # Base query with tenant isolation
    query = db.query(ReconciliationJob).filter(
        ReconciliationJob.tenant_id == user.tenant_id
    )
    
    # Apply status filter if provided
    if status_filter:
        try:
            status_enum = JobStatus(status_filter)
            query = query.filter(ReconciliationJob.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    query = query.order_by(ReconciliationJob.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    jobs = query.all()
    
    return JobListResponse(
        items=[
            JobResponse(
                id=str(job.id),
                status=job.status.value,
                created_at=job.created_at,
                evd_invoice_count=job.evd_invoice_count,
                pdf_invoice_count=job.pdf_invoice_count,
                matches_count=job.matches_count,
                mismatches_count=job.mismatches_count,
                match_rate=float(job.match_rate) if job.match_rate else None,
                report_file_path=job.report_file_path,
                error_message=job.error_message
            )
            for job in jobs
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/stats/summary", response_model=JobStatsResponse)
async def get_job_stats(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_active_tenant),
    db: Session = Depends(get_db)
):
    """
    Get job statistics for the current tenant.
    """
    # Count jobs by status
    total_jobs = db.query(ReconciliationJob).filter(
        ReconciliationJob.tenant_id == user.tenant_id
    ).count()
    
    pending = db.query(ReconciliationJob).filter(
        ReconciliationJob.tenant_id == user.tenant_id,
        ReconciliationJob.status == JobStatus.PENDING
    ).count()
    
    processing = db.query(ReconciliationJob).filter(
        ReconciliationJob.tenant_id == user.tenant_id,
        ReconciliationJob.status == JobStatus.PROCESSING
    ).count()
    
    completed = db.query(ReconciliationJob).filter(
        ReconciliationJob.tenant_id == user.tenant_id,
        ReconciliationJob.status == JobStatus.COMPLETED
    ).count()
    
    failed = db.query(ReconciliationJob).filter(
        ReconciliationJob.tenant_id == user.tenant_id,
        ReconciliationJob.status == JobStatus.FAILED
    ).count()
    
    return JobStatsResponse(
        total_jobs=total_jobs,
        pending=pending,
        processing=processing,
        completed=completed,
        failed=failed,
        jobs_this_month=tenant.jobs_this_month,
        monthly_limit=tenant.jobs_per_month
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a job and its associated files.
    
    Only admins can delete jobs.
    """
    # Check admin permission
    if user.role.value not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can delete jobs"
        )
    
    job = db.query(ReconciliationJob).filter(
        ReconciliationJob.id == job_id,
        ReconciliationJob.tenant_id == user.tenant_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Delete files
    if job.evd_file_path:
        Path(job.evd_file_path).unlink(missing_ok=True)
    if job.pdf_file_path:
        Path(job.pdf_file_path).unlink(missing_ok=True)
    if job.report_file_path:
        Path(job.report_file_path).unlink(missing_ok=True)
    
    # Audit log
    audit = AuditLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="job.deleted",
        resource_type="job",
        resource_id=job.id
    )
    db.add(audit)
    
    # Delete job
    db.delete(job)
    db.commit()
