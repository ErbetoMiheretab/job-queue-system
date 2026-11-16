from typing import Dict, List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General App Config
    PROJECT_NAME: str = "Distributed Job Processing Platform"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Redis Connection
    REDIS_URL: str = "redis://redis:6379/0"

    # PostgreSQL Connection
    DATABASE_URL: str = "postgresql://jobuser:jobpass@postgres/jobdb"

    # Celery Core Configuration
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_DEFAULT_QUEUE: str = "default"
    
    # Priority Queue Definitions
    # Celery supports priorities 0 (lowest) to 9 (highest)
    QUEUES: List[str] = ["high_priority", "default", "low_priority", "email"]
    
    CELERY_TASK_ROUTES: Dict[str, dict] = {
        "src.tasks.send_email.send_email": {"queue": "email"},
        "src.tasks.compute.compute_data": {"queue": "default"},
        "src.tasks.webhook.send_webhook": {"queue": "default"},
        "src.tasks.send_email.failing_demo_task": {"queue": "default"},
    }

    # Celery Retries & Fault Tolerance
    CELERY_TASK_MAX_RETRIES: int = 3
    CELERY_TASK_DEFAULT_RETRY_DELAY: int = 5  # seconds
    CELERY_TASK_RETRY_BACKOFF: bool = True
    CELERY_TASK_RETRY_BACKOFF_MAX: int = 600  # 10 minutes
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1

    # Task mapping for dynamic dispatch by job_type string
    TASK_MAP: Dict[str, str] = {
        "send_email": "src.tasks.send_email.send_email",
        "compute_data": "src.tasks.compute.compute_data",
        "send_webhook": "src.tasks.webhook.send_webhook",
        "failing_demo_task": "src.tasks.send_email.failing_demo_task",
    }

    # Idempotency Engine
    IDEMPOTENCY_TTL_SECONDS: int = 86400  # 24 hours
    IDEMPOTENCY_LOCK_TIMEOUT_SECONDS: int = 30  # Lock during job creation

    # Real-time WebSocket Event Bus
    CELERY_EVENT_CHANNEL: str = "job_events"

    # Security & CORS
    CORS_ORIGINS: List[str] = ["*"]

    def __init__(self, **values):
        super().__init__(**values)
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL


settings = Settings()
