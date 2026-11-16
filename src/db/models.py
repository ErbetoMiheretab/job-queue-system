import uuid
from sqlalchemy import JSON, Column, DateTime, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import declarative_base, foreign, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), unique=True, nullable=False, index=True)  # Celery task ID
    job_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    idempotency_key = Column(String(255), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="PENDING", index=True)

    priority = Column(Integer, default=5, index=True)  # 1=Low, 5=Default, 9=High
    queue = Column(String(50), nullable=False, default="default")
    scheduled_for = Column(DateTime(timezone=True), nullable=True)

    attempts = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_jobs_status_created", "status", "created_at"),
    )

    # Relationships
    dead_letter = relationship(
        "DeadLetterJob",
        back_populates="original_job",
        uselist=False,
        primaryjoin="Job.task_id == foreign(DeadLetterJob.original_task_id)",
    )
    processed_actions = relationship(
        "ProcessedAction",
        back_populates="job",
        primaryjoin="Job.task_id == foreign(ProcessedAction.task_id)",
    )


class DeadLetterJob(Base):
    __tablename__ = "dead_letter_jobs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_task_id = Column(String(255), nullable=False, index=True)
    job_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    idempotency_key = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    exception_class = Column(String(255), nullable=True)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    replayed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship back to Job
    original_job = relationship(
        "Job",
        back_populates="dead_letter",
        primaryjoin="Job.task_id == foreign(DeadLetterJob.original_task_id)",
    )


class ProcessedAction(Base):
    __tablename__ = "processed_actions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(255), unique=True, nullable=False, index=True)
    task_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship back to Job
    job = relationship(
        "Job",
        back_populates="processed_actions",
        primaryjoin="Job.task_id == foreign(ProcessedAction.task_id)",
    )
