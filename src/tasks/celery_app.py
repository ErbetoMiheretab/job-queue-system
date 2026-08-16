from celery import Celery

from src.config import settings

app =Celery(
    "job_queue", 
    broker = settings.CELERY_BROKER_URL, 
    backend=settings.CELERY_RESULT_BACKEND, 
    include=[
        "src.tasks.send_email"
    ]
)


app.conf.update(
    task_serializer="json", 
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,
    task_soft_time_limit=1200,
    task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,
    task_routes=settings.CELERY_TASK_ROUTES,
    task_default_rate_limit="100/m",  
    task_acks_late=True,             # acknowledge after completion
    worker_prefetch_multiplier=1,    # fair distribution
)


# Optional: configure retry defaults
app.conf.task_default_retry_delay = settings.CELERY_TASK_DEFAULT_RETRY_DELAY
app.conf.task_max_retries = settings.CELERY_TASK_MAX_RETRIES
app.conf.task_retry_backoff = settings.CELERY_TASK_RETRY_BACKOFF
app.conf.task_retry_backoff_max = settings.CELERY_TASK_RETRY_BACKOFF_MAX

if __name__ == "__main__":
    app.start()