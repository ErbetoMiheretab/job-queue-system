import time
from src.config import settings
from src.tasks.base import BaseTaskWithDLQ
from src.tasks.celery_app import app
from src.utils.logger import logger


@app.task(
    bind=True,
    base=BaseTaskWithDLQ,
    name="src.tasks.compute.compute_data",
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
    autoretry_for=(Exception,),
    retry_backoff=settings.CELERY_TASK_RETRY_BACKOFF,
    retry_backoff_max=settings.CELERY_TASK_RETRY_BACKOFF_MAX,
)
def compute_data(
    self,
    payload: dict,
    idempotency_key: str | None = None,
    job_type: str = "compute_data",
):
    """
    Simulated computational / batch data transformation job.
    Demonstrates incremental progress updates via self.update_state().
    """
    steps = payload.get("steps", 5)
    records_per_step = payload.get("records_per_step", 1000)
    delay_per_step = payload.get("delay", 0.2)

    total_records = 0
    start_time = time.time()

    logger.info("compute_job_started", task_id=self.request.id, steps=steps)

    for i in range(1, steps + 1):
        if payload.get("fail_at_step") == i:
            raise RuntimeError(f"Simulated compute failure at step {i}")

        time.sleep(delay_per_step)
        total_records += records_per_step
        percent = int((i / steps) * 100)

        # Emit task progress state
        self.update_state(
            state="PROGRESS",
            meta={
                "current_step": i,
                "total_steps": steps,
                "percent": percent,
                "records_processed": total_records,
            },
        )

    duration = round(time.time() - start_time, 3)
    logger.info(
        "compute_job_finished",
        task_id=self.request.id,
        total_records=total_records,
        duration_seconds=duration,
    )

    return {
        "status": "completed",
        "steps_completed": steps,
        "total_records_processed": total_records,
        "duration_seconds": duration,
    }
