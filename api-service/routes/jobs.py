import os
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from config import JOB_STATUS_PENDING
from db.queries import get_job_by_id, insert_job
from models.job import CreateJobRequest, CreateJobResponse, JobResponse, is_valid_job_type
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
