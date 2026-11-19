from celery import Celery
from kombu import Exchange, Queue

from src.config import settings

# Initialize Celery Application
app = Celery(
    "job_queue",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "src.tasks.send_email",
        "src.tasks.compute",
        "src.tasks.webhook",
    ],
)

# Kombu Exchange & Queue Definitions with Priority Routing
default_exchange = Exchange("default", type="direct")

task_queues = [
    Queue(
        "high_priority",
        default_exchange,
        routing_key="high_priority",
        queue_arguments={"x-max-priority": 9},
    ),
    Queue(
        "default",
        default_exchange,
        routing_key="default",
        queue_arguments={"x-max-priority": 5},
    ),
    Queue(
        "low_priority",
        default_exchange,
        routing_key="low_priority",
        queue_arguments={"x-max-priority": 1},
    ),
    Queue(
        "email",
        default_exchange,
        routing_key="email",
    ),
]

app.conf.update(
    task_queues=task_queues,
    task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,
    task_default_exchange="default",
    task_default_routing_key="default",
    task_default_priority=5,
    task_routes=settings.CELERY_TASK_ROUTES,
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Concurrency & Reliability
    task_track_started=True,
    task_acks_late=settings.CELERY_TASK_ACKS_LATE,
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    result_expires=86400,
    # Execution Time Limits
    task_time_limit=1800,       # Hard limit (30 minutes)
    task_soft_time_limit=1200,  # Soft limit (20 minutes)
    # Redis Broker Transport Options for Priorities
    broker_transport_options={
        "queue_order_strategy": "priority",
        "priority_steps": list(range(10)),
        "sep": ":",
    },
    # Retry Defaults
    task_default_retry_delay=settings.CELERY_TASK_DEFAULT_RETRY_DELAY,
    task_max_retries=settings.CELERY_TASK_MAX_RETRIES,
    task_retry_backoff=settings.CELERY_TASK_RETRY_BACKOFF,
    task_retry_backoff_max=settings.CELERY_TASK_RETRY_BACKOFF_MAX,
)

if __name__ == "__main__":
    app.start()
