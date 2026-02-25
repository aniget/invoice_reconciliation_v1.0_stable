"""
SaaS Configuration Settings

Environment-based configuration for multi-tenant SaaS deployment.
Uses environment variables with sensible defaults for development.
"""

import os
from typing import Optional
from pathlib import Path
from pydantic import BaseSettings, Field, PostgresDsn, validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application Info
    app_name: str = "Invoice Reconciliation SaaS"
    app_version: str = "2.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # API Configuration
    api_prefix: str = "/api/v1"
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # Database Configuration
    database_url: PostgresDsn = Field(
        default="postgresql://localhost:5432/invoice_reconciliation",
        env="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis/Queue Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    # Security Configuration
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    jwt_secret_key: str = Field(
        default="jwt-secret-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = Field(default=1440, env="JWT_EXPIRATION_MINUTES")  # 24 hours
    
    # CORS Configuration
    cors_origins: list = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    # Storage Configuration
    upload_dir: Path = Field(default=Path("./uploads"), env="UPLOAD_DIR")
    reports_dir: Path = Field(default=Path("./reports"), env="REPORTS_DIR")
    temp_dir: Path = Field(default=Path("./temp"), env="TEMP_DIR")
    max_upload_size_mb: int = Field(default=50, env="MAX_UPLOAD_SIZE_MB")
    
    # Processing Configuration
    max_concurrent_jobs: int = Field(default=5, env="MAX_CONCURRENT_JOBS")
    job_timeout_seconds: int = Field(default=300, env="JOB_TIMEOUT_SECONDS")  # 5 minutes
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = "json"  # json or text
    log_file: Optional[str] = Field(default="logs/app.log", env="LOG_FILE")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Feature Flags
    enable_ocr: bool = Field(default=False, env="ENABLE_OCR")
    enable_ml_extraction: bool = Field(default=False, env="ENABLE_ML_EXTRACTION")
    enable_webhooks: bool = Field(default=False, env="ENABLE_WEBHOOKS")
    
    # Subscription Tiers
    free_tier_jobs_per_month: int = Field(default=100, env="FREE_TIER_JOBS_PER_MONTH")
    pro_tier_jobs_per_month: int = Field(default=1000, env="PRO_TIER_JOBS_PER_MONTH")
    
    @validator('upload_dir', 'reports_dir', 'temp_dir', pre=True)
    def create_directories(cls, v):
        """Ensure directories exist."""
        if isinstance(v, str):
            v = Path(v)
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
