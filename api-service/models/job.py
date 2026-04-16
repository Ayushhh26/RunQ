from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from config import VALID_JOB_TYPES


class CreateJobRequest(BaseModel):
    job_type: str
    file_path: str


class CreateJobResponse(BaseModel):
    job_id: UUID
    status: str


class JobResponse(BaseModel):
    id: UUID
    job_type: str
    status: str
    retry_count: int
    file_path: str
    result: dict[str, Any] | None = None
    error_message: str | None = None
    processing_ms: int | None = None
    created_at: datetime
    updated_at: datetime


def is_valid_job_type(job_type: str) -> bool:
    return job_type in VALID_JOB_TYPES
