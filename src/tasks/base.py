import traceback
from celery import Task
from sqlalchemy.sql import func

from src.db.models import DeadLetterJob, Job
from src.db.session import get_db_context
from src.utils.logger import logger


class BaseTaskWithDLQ(Task):
    """
    Production base task providing automated status tracking, failure recovery,
    exponential retry tracking, and Dead-Letter Queue (DLQ) capture.
    """

    def before_start(self, task_id, args, kwargs):
        """Invoked immediately before the task begins executing."""
        try:
            with get_db_context() as db:
                job = db.query(Job).filter_by(task_id=task_id).first()
                if job:
                    job.status = "STARTED"
                    db.commit()
            logger.info("task_execution_started", task_id=task_id, task_name=self.name)
        except Exception as e:
            logger.warning("before_start_update_failed", task_id=task_id, error=str(e))
        super().before_start(task_id, args, kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        """Invoked when the task finishes successfully."""
        try:
            with get_db_context() as db:
                job = db.query(Job).filter_by(task_id=task_id).first()
                if job:
                    job.status = "SUCCESS"
                    job.result = retval if isinstance(retval, (dict, list, str, int, float, bool)) else {"output": str(retval)}
                    job.completed_at = func.now()
                    db.commit()
            logger.info("task_execution_succeeded", task_id=task_id, task_name=self.name)
        except Exception as e:
            logger.error("on_success_update_failed", task_id=task_id, error=str(e))
        super().on_success(retval, task_id, args, kwargs)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Invoked whenever the task triggers a retry."""
        try:
            with get_db_context() as db:
                job = db.query(Job).filter_by(task_id=task_id).first()
                if job:
                    job.status = "RETRY"
                    job.attempts = self.request.retries + 1
                    job.error = str(exc)
                    db.commit()
            logger.warning(
                "task_execution_retrying",
                task_id=task_id,
                task_name=self.name,
                retries=self.request.retries,
                max_retries=self.max_retries,
                error=str(exc),
            )
        except Exception as e:
            logger.error("on_retry_update_failed", task_id=task_id, error=str(e))
        super().on_retry(exc, task_id, args, kwargs, einfo)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Invoked on task failure. If retries are exhausted, the task is automatically
        transitioned to DEAD_LETTERED and logged in the dead_letter_jobs table.
        """
        try:
            with get_db_context() as db:
                job = db.query(Job).filter_by(task_id=task_id).first()
                is_exhausted = self.request.retries >= (self.max_retries or 0)

                payload = args[0] if (args and isinstance(args[0], dict)) else kwargs.get("payload", {})
                job_type = kwargs.get("job_type", self.name)
                idempotency_key = kwargs.get("idempotency_key")
                stack_trace = str(einfo) if einfo else traceback.format_exc()

                if is_exhausted:
                    if job:
                        job.status = "DEAD_LETTERED"
                        job.error = str(exc)
                        job.attempts = self.request.retries + 1

                    # Create DLQ record if not already present
                    existing_dl = db.query(DeadLetterJob).filter_by(original_task_id=task_id).first()
                    if not existing_dl:
                        dl = DeadLetterJob(
                            original_task_id=task_id,
                            job_type=job_type,
                            payload=payload,
                            idempotency_key=idempotency_key,
                            error=str(exc),
                            stack_trace=stack_trace,
                            exception_class=exc.__class__.__name__,
                            attempts=self.request.retries + 1,
                        )
                        db.add(dl)

                    db.commit()
                    logger.error(
                        "task_moved_to_dlq",
                        task_id=task_id,
                        task_name=self.name,
                        retries=self.request.retries,
                        error=str(exc),
                    )
                else:
                    if job:
                        job.status = "FAILED"
                        job.error = str(exc)
                        job.attempts = self.request.retries + 1
                        db.commit()
                    logger.error(
                        "task_execution_failed",
                        task_id=task_id,
                        task_name=self.name,
                        error=str(exc),
                    )
        except Exception as e:
            logger.error("on_failure_update_failed", task_id=task_id, error=str(e))
        super().on_failure(exc, task_id, args, kwargs, einfo)
