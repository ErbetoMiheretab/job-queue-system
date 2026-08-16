import uuid

from sqlalchemy import JSON, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), unique=True, nullable=False, index=True) #Celery task ID
    job_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    idempotency_key = Column(String(255), nullable=False, index=True)
    status = Column(String(20), nullable=False,default="PENDING")

    attempts = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_jobs_status_created','status', 'created_at')
    )

    # Relationship: one Job can have one DeadLetterJob
    dead_letter = relationship("DeadLetterJob", back_populates="original_job", uselist=False)

    # Relationship: one Job can have many ProcessedActions
    processed_actions = relationship("ProcessedAction", back_populates="job")
class DeadLetterJob(Base):
    __tablename__ = "dead_letter_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_task_id = Column(String(255), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    idempotency_key = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    replayed_at = Column(DateTime(timezone=True), nullable=True) 

    # Relationship back to Job
    original_job = relationship("Job", back_populates="dead_letter")



class ProcessedAction(Base):
    __tablename__ = "processed_actions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(255), unique=True, nullable=False)
    task_id = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True) 

    # Relationship back to Job
    job = relationship("Job", back_populates="processed_actions")