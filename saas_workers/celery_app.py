"""
Celery Configuration for Background Job Processing

Production-ready async job processing with Celery and Redis.
This replaces BackgroundTasks for scalable production deployment.
"""

from celery import Celery
from saas_config import settings

# Create Celery app
celery_app = Celery(
    'invoice_reconciliation',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'saas_workers.tasks.process_reconciliation': {'queue': 'reconciliation'},
        'saas_workers.tasks.cleanup_old_files': {'queue': 'maintenance'},
    },
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=settings.job_timeout_seconds * 2,
    task_soft_time_limit=settings.job_timeout_seconds,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Result backend
    result_expires=3600,  # 1 hour
    result_extended=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['saas_workers'])
