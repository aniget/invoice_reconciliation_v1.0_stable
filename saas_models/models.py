"""
Database Models for Multi-Tenant SaaS

Core models for tenants, users, jobs, and invoices with tenant isolation.
All models include tenant_id for row-level security.
"""

from sqlalchemy import (
    Column, String, DateTime, Enum, Integer, Numeric, ForeignKey,
    Boolean, Text, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
import enum

from saas_config.database import Base


class SubscriptionTier(str, enum.Enum):
    """Subscription tiers for tenants."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserRole(str, enum.Enum):
    """User roles for access control."""
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"


class JobStatus(str, enum.Enum):
    """Status of reconciliation jobs."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SourceType(str, enum.Enum):
    """Source type for invoices."""
    EVD = "evd"
    PDF = "pdf"


class Tenant(Base):
    """
    Tenant (Organization) model.
    
    Each tenant represents a customer organization with isolated data.
    """
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    subscription_tier = Column(
        Enum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False
    )
    
    # Subscription limits
    jobs_per_month = Column(Integer, default=100)
    jobs_this_month = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    jobs = relationship("ReconciliationJob", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tenant {self.name} ({self.subscription_tier})>"


class User(Base):
    """
    User model.
    
    Users belong to a tenant and have role-based access control.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    first_name = Column(String(100))
    last_name = Column(String(100))
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    
    # API access
    api_key = Column(String(255), unique=True, index=True)
    api_key_created_at = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    jobs = relationship("ReconciliationJob", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class ReconciliationJob(Base):
    """
    Reconciliation Job model.
    
    Represents a single reconciliation task with EVD and PDF data.
    """
    __tablename__ = "reconciliation_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Job details
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    priority = Column(Integer, default=0)  # Higher = more priority
    
    # File references
    evd_file_path = Column(String(500))
    pdf_file_path = Column(String(500))
    report_file_path = Column(String(500))
    
    # Processing metadata
    evd_invoice_count = Column(Integer)
    pdf_invoice_count = Column(Integer)
    matches_count = Column(Integer)
    mismatches_count = Column(Integer)
    match_rate = Column(Numeric(5, 2))  # Percentage
    
    # Results (stored as JSON)
    evd_data = Column(JSONB)
    pdf_data = Column(JSONB)
    result_data = Column(JSONB)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="jobs")
    user = relationship("User", back_populates="jobs")
    invoices = relationship("Invoice", back_populates="job", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_tenant_status_created', 'tenant_id', 'status', 'created_at'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Job {self.id} ({self.status})>"


class Invoice(Base):
    """
    Invoice model.
    
    Stores extracted invoice data from both EVD and PDF sources.
    """
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("reconciliation_jobs.id"), nullable=False, index=True)
    
    # Invoice data
    invoice_number = Column(String(100), nullable=False, index=True)
    vendor_name = Column(String(255), index=True)
    vendor_normalized = Column(String(255), index=True)
    
    # Amounts
    total_amount_eur = Column(Numeric(15, 2))
    total_amount_bgn = Column(Numeric(15, 2))
    net_amount_eur = Column(Numeric(15, 2))
    vat_amount_eur = Column(Numeric(15, 2))
    
    # Dates
    invoice_date = Column(DateTime)
    
    # Source information
    source_type = Column(Enum(SourceType), nullable=False, index=True)
    source_file = Column(String(500))
    extraction_method = Column(String(50))  # template, generic, ocr
    confidence = Column(Numeric(3, 2))  # 0.00 to 1.00
    
    # Additional data (flexible storage)
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    job = relationship("ReconciliationJob", back_populates="invoices")
    
    # Indexes
    __table_args__ = (
        Index('idx_tenant_invoice_number', 'tenant_id', 'invoice_number'),
        Index('idx_tenant_vendor', 'tenant_id', 'vendor_normalized'),
        Index('idx_job_source', 'job_id', 'source_type'),
    )
    
    def __repr__(self):
        return f"<Invoice {self.invoice_number} ({self.source_type})>"


class AuditLog(Base):
    """
    Audit log for tracking all system actions.
    
    Records who did what and when for compliance and debugging.
    """
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), index=True)
    user_id = Column(UUID(as_uuid=True), index=True)
    
    # Action details
    action = Column(String(100), nullable=False, index=True)  # e.g., "job.created", "user.login"
    resource_type = Column(String(50), index=True)  # e.g., "job", "user", "tenant"
    resource_id = Column(UUID(as_uuid=True), index=True)
    
    # Context
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(String(500))
    
    # Details (flexible storage)
    details = Column(JSONB)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_tenant_action_created', 'tenant_id', 'action', 'created_at'),
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_resource_type_id', 'resource_type', 'resource_id'),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id}>"
