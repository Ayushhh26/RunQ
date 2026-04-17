import os
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from config import JOB_STATUS_PENDING
from db.queries import get_job_by_id, insert_job, list_jobs
from models.job import (
    CreateJobRequest,
    CreateJobResponse,
    JobResponse,
    ListJobsResponse,
    is_valid_job_status,
    is_valid_job_type,
)
from redis_client import enqueue_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=CreateJobResponse)
def create_job(payload: CreateJobRequest):
    if not is_valid_job_type(payload.job_type):
        raise HTTPException(status_code=400, detail="Invalid job_type")

    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=400, detail="file_path does not exist")

    job_id = uuid4()
    insert_job(
        job_id=job_id,
        job_type=payload.job_type,
        status=JOB_STATUS_PENDING,
        file_path=payload.file_path,
    )
    enqueue_job(str(job_id))

    return CreateJobResponse(job_id=job_id, status=JOB_STATUS_PENDING)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID):
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(**job)


@router.get("", response_model=ListJobsResponse)
def get_jobs(
    status: str | None = None,
    job_type: str | None = None,
    page: int = 1,
    per_page: int = 20,
):
    if status and not is_valid_job_status(status):
        raise HTTPException(status_code=400, detail="Invalid status")
    if job_type and not is_valid_job_type(job_type):
        raise HTTPException(status_code=400, detail="Invalid job_type")
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    if per_page < 1 or per_page > 100:
        raise HTTPException(status_code=400, detail="per_page must be between 1 and 100")

    rows, total = list_jobs(status=status, job_type=job_type, page=page, per_page=per_page)
    items = [JobResponse(**row) for row in rows]
    return ListJobsResponse(items=items, page=page, per_page=per_page, total=total)
