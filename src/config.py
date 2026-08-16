import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    #Redis
    REDIS_URL: str = "redis://redis:6379/0"

    #PostgreSQL
    DATABASE_URL: str = "postgresql://jobuser:jobpass@postgres/jobdb"    


    # Celery
    CELERY_BROKER_URL: str = REDIS_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL
    CELERY_TASK_DEFAULT_QUEUE: str = "default"
    CELERY_TASK_ROUTES: dict = {
        "tasks.send_email.send_email": {"queue": "email"},
            }
    CELERY_TASK_MAX_RETRIES: int = 3
    CELERY_TASK_DEFAULT_RETRY_DELAY: int = 5  # seconds
    CELERY_TASK_RETRY_BACKOFF: bool = True
    CELERY_TASK_RETRY_BACKOFF_MAX: int = 600  # 10 minutes

    #Job type to task mapping

    TASK_MAP: dict ={
        "send_email": "tasks.send_email.send_email",
    }

    #Idempotency
    IDEMPOTENCY_TTL_SECONDS:int = 86400

    class Config:
        env_file= ".env"
        env_file_encoding = "utf-8"

setttings = Settings() 
