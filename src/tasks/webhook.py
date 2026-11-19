from src.config import settings
from src.tasks.base import BaseTaskWithDLQ
from src.tasks.celery_app import app
from src.utils.logger import logger


@app.task(
    bind=True,
    base=BaseTaskWithDLQ,
    name="src.tasks.webhook.send_webhook",
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
    autoretry_for=(Exception,),
    retry_backoff=settings.CELERY_TASK_RETRY_BACKOFF,
    retry_backoff_max=settings.CELERY_TASK_RETRY_BACKOFF_MAX,
)
def send_webhook(
    self,
    payload: dict,
    idempotency_key: str | None = None,
    job_type: str = "send_webhook",
):
    """
    Simulated outgoing webhook delivery task.
    Demonstrates handling transient external API failures with exponential backoff.
    """
    url = payload.get("url")
    event = payload.get("event", "generic_event")
    data = payload.get("data", {})

    if not url:
        raise ValueError("Missing 'url' destination for webhook delivery")

    # Simulate intermittent failures that succeed on later retry
    fail_attempts = payload.get("fail_attempts", 0)
    if fail_attempts > 0 and self.request.retries < fail_attempts:
        logger.warning(
            "webhook_delivery_transient_failure",
            url=url,
            retry=self.request.retries + 1,
            target_attempts=fail_attempts,
        )
        raise RuntimeError(
            f"Webhook destination {url} returned HTTP 503 (Retry {self.request.retries + 1}/{fail_attempts})"
        )

    # Simulate permanent failure
    if payload.get("fail"):
        raise RuntimeError(f"Webhook destination {url} permanently rejected delivery")

    logger.info("webhook_delivery_succeeded", url=url, event=event)
    return {
        "status": "delivered",
        "url": url,
        "event": event,
        "response_code": 200,
    }
