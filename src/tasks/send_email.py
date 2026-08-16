from celery import Task
from sqlalchemy.orm import func

from src.config import settings
from src.db.models import DeadLetterJob, Job, ProcessedAction
from src.db.session import SessionLocal
from src.tasks.celery_app import app
from src.utils.logger import logger


def _simulate_send_email(payload: dict) -> None:
    """Helper function to simulate (or execute) actual email delivery."""
    to = payload.get("to")
    subject = payload.get("subject")
    body = payload.get("body")

    if not to:
        raise ValueError("Missing 'to' field")

    # Simulate potential failure for demo
    if payload.get("fail"):
        raise RuntimeError("Simulated email failure")

    logger.info("sending_email", to=to, subject=subject)
    # Actual send logic (SMTP, SendGrid, Amazon SES, etc.) goes here


class BaseTaskWithDLQ(Task):
    """Base task that moves failed jobs to dead-letter queue after max retries."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Only move to DLQ if retries exhausted
        if self.request.retries >= self.max_retries:
            db = SessionLocal()
            try:
                # Update job status to dl
                job = db.query(Job).filter_by(task_id=task_id).first()
                if job:
                    job.status = "DEAD_LETTERED"
                    job.error = str(exc)
                    db.commit()
                # Create DeadLetterJob record
                dl = DeadLetterJob(
                    original_task_id=task_id,
                    job_type=kwargs.get("job_type") or self.name,
                    payload=args[0] if args else {},
                    idempotency_key=kwargs.get("idempotency_key"),
                    error=str(exc),
                    attempts=self.request.retries + 1,
                )
                db.add(dl)
                db.commit()
                logger.error(
                    "task_moved_to_dlq",
                    task_id=task_id,
                    error=str(exc),
                    retries=self.request.retries,
                )
            finally:
                db.close()


@app.task(
    bind=True,
    base=BaseTaskWithDLQ,
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
    autoretry_for=(Exception,),
    retry_backoff=settings.CELERY_TASK_RETRY_BACKOFF,
    retry_backoff_max=settings.CELERY_TASK_RETRY_BACKOFF_MAX,
)
def send_email(
    self,
    payload: dict,
    idempotency_key: str | None = None,
    job_type: str = "send_email",
):
    """
    Send an email. Idempotent via idempotency_key.
    """
    db = SessionLocal()
    try:
        # Idempotency check
        if idempotency_key:
            existing = (
                db.query(ProcessedAction)
                .filter_by(idempotency_key=idempotency_key)
                .first()
            )
            if existing:
                logger.info(
                    "email_already_sent_skipping", idempotency_key=idempotency_key
                )
                # Update job status to SUCCESS (already done)
                job = db.query(Job).filter_by(task_id=self.request.id).first()
                if job:
                    job.status = "SUCCESS"
                    job.result = {
                        "status": "already_processed",
                        "previous_task": existing.task_id,
                    }
                    db.commit()
                return {"status": "already_processed"}

        # Call the extracted email sending function
        _simulate_send_email(payload)

        # Record idempotency
        if idempotency_key:
            pa = ProcessedAction(
                idempotency_key=idempotency_key,
                task_id=self.request.id,
                expires_at=None,  # or now + TTL
            )
            db.add(pa)
            
        # Also update job status
        job = db.query(Job).filter_by(task_id=self.request.id).first()
        if job:
            job.status = "SUCCESS"
            job.result = {"status": "sent"}
            job.completed_at = func.now()
        
        db.commit()
        return {"status": "sent"}

    except Exception as exc:
        # Log and retry (autoretry_for will handle)
        logger.error(
            "email_task_failed",
            error=str(exc),
            task_id=self.request.id,
            retries=self.request.retries,
        )
        # Update job attempt count in DB
        job = db.query(Job).filter_by(task_id=self.request.id).first()
        if job:
            job.attempts = self.request.retries + 1
            job.status = (
                "RETRY" if self.request.retries < self.max_retries else "FAILED"
            )
            job.error = str(exc)
            db.commit()
        # Re-raise to trigger retry
        raise
    finally:
        db.close()