"""
Database Configuration and Session Management

Provides SQLAlchemy engine, session factory, and base models
for multi-tenant database access.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import logging

from .settings import settings

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine_kwargs = {
    "pool_pre_ping": True,  # Verify connections before using
    "pool_size": settings.database_pool_size,
    "max_overflow": settings.database_max_overflow,
    "echo": settings.database_echo,
}

# For SQLite (development), use different pool settings
if settings.database_url.startswith("sqlite"):
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    })
    engine_kwargs.pop("pool_size")
    engine_kwargs.pop("max_overflow")

engine = create_engine(str(settings.database_url), **engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


# Tenant context for row-level security
class TenantContext:
    """Thread-local storage for current tenant."""
    
    def __init__(self):
        self._tenant_id = None
    
    def set_tenant_id(self, tenant_id: str):
        """Set the current tenant ID."""
        self._tenant_id = tenant_id
        logger.debug(f"Tenant context set to: {tenant_id}")
    
    def get_tenant_id(self) -> str:
        """Get the current tenant ID."""
        if not self._tenant_id:
            raise ValueError("No tenant context set. Use set_tenant_id() first.")
        return self._tenant_id
    
    def clear(self):
        """Clear tenant context."""
        self._tenant_id = None


# Global tenant context
tenant_context = TenantContext()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database session.
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    Should be called on application startup.
    """
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def drop_db():
    """
    Drop all database tables.
    WARNING: Use only in development/testing!
    """
    if settings.environment == "production":
        raise ValueError("Cannot drop database in production!")
    
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("Database tables dropped")


# Database event listeners for logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log database connections."""
    logger.debug("Database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log connection checkouts from pool."""
    logger.debug("Database connection checked out from pool")
