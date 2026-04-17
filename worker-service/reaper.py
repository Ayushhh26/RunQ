import logging

from config import STALE_JOB_THRESHOLD_SECONDS
from db import get_stale_running_job_ids, mark_job_pending_from_stale
from redis_client import enqueue_job

logger = logging.getLogger("runq-worker")


def requeue_stale_running_jobs():
    stale_ids = get_stale_running_job_ids(STALE_JOB_THRESHOLD_SECONDS)
    if not stale_ids:
        logger.info("Reaper found no stale running jobs")
        return

    for job_id in stale_ids:
        mark_job_pending_from_stale(job_id)
        enqueue_job(job_id)
        logger.warning("Reaper re-queued stale job %s", job_id)

    logger.info("Reaper recovered %s stale running jobs", len(stale_ids))
