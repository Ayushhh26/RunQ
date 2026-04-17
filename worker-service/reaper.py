import logging

from config import STALE_JOB_THRESHOLD_SECONDS
from db import get_stale_running_job_ids, mark_job_pending_from_stale
from logging_config import log_event
from redis_client import enqueue_job

logger = logging.getLogger("runq-worker")


def requeue_stale_running_jobs():
    stale_ids = get_stale_running_job_ids(STALE_JOB_THRESHOLD_SECONDS)
    if not stale_ids:
        log_event(logger, "info", "reaper_no_stale_jobs")
        return

    for job_id in stale_ids:
        mark_job_pending_from_stale(job_id)
        enqueue_job(job_id)
        log_event(logger, "warning", "reaper_requeued_job", job_id=job_id)

    log_event(logger, "info", "reaper_recovered_jobs", count=len(stale_ids))
