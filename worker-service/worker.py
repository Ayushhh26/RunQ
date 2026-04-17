import json
import logging
import signal
import time

from config import (
    MAX_JOB_RETRY_ATTEMPTS,
    RETRY_BACKOFF_SECONDS,
    RUNQ_FORCE_FAIL_PATH,
)
from db import (
    get_job_for_processing,
    mark_job_dead,
    mark_job_running,
    mark_job_success,
    schedule_job_retry,
)
from logging_config import configure_logging, log_event
from processors.classify import classify_document as run_classify_document, preload_classifier
from processors.extract import extract_metadata as run_extract_metadata, preload_model
from processors.summarize import summarize_document as run_summarize_document
from reaper import requeue_stale_running_jobs
from redis_client import enqueue_job, get_redis_client, pop_job_id, push_dlq

logger = logging.getLogger("runq-worker")
_shutdown_requested = False


def _request_shutdown(signum, _frame):
    global _shutdown_requested
    _shutdown_requested = True
    log_event(logger, "warning", "worker_shutdown_signal", signal=signum)


def install_signal_handlers():
    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)


def wait_for_redis():
    while True:
        try:
            client = get_redis_client()
            client.ping()
            log_event(logger, "info", "worker_redis_connected")
            return
        except Exception as exc:
            log_event(logger, "warning", "worker_redis_wait", error=str(exc))
            time.sleep(2)


def process_job(job_type, file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    if RUNQ_FORCE_FAIL_PATH and file_path == RUNQ_FORCE_FAIL_PATH:
        raise RuntimeError(
            f"Forced failure for Step 8 testing (RUNQ_FORCE_FAIL_PATH={RUNQ_FORCE_FAIL_PATH!r})"
        )

    if job_type == "extract_metadata":
        result = run_extract_metadata(content)
    elif job_type == "classify_document":
        result = run_classify_document(content)
    elif job_type == "summarize_document":
        result = run_summarize_document(content)
    else:
        raise ValueError(f"Unsupported job_type: {job_type}")

    return result


def run_worker_loop():
    while not _shutdown_requested:
        job_id = pop_job_id(timeout=5)
        if not job_id:
            continue

        started_at = time.time()
        log_event(logger, "info", "job_started", job_id=job_id)
        try:
            job = get_job_for_processing(job_id)
            if not job:
                log_event(logger, "warning", "job_not_found", job_id=job_id)
                continue

            _, job_type, file_path, retry_count = job
            mark_job_running(job_id)
            result = process_job(job_type, file_path)
            processing_ms = int((time.time() - started_at) * 1000)
            mark_job_success(job_id, json.dumps(result), processing_ms)
            log_event(
                logger,
                "info",
                "job_success",
                job_id=job_id,
                status="success",
                processing_ms=processing_ms,
            )
        except Exception as exc:
            processing_ms = int((time.time() - started_at) * 1000)
            err_msg = str(exc)
            log_event(
                logger,
                "error",
                "job_failure",
                job_id=job_id,
                status="failed",
                error=err_msg,
            )
            logger.exception("worker stacktrace")
            job = get_job_for_processing(job_id)
            if not job:
                log_event(logger, "warning", "job_missing_during_failure", job_id=job_id)
                continue
            _, _, _, retry_count = job
            new_retry = retry_count + 1
            if new_retry <= MAX_JOB_RETRY_ATTEMPTS:
                backoff = RETRY_BACKOFF_SECONDS[new_retry - 1]
                log_event(
                    logger,
                    "warning",
                    "job_retry_scheduled",
                    job_id=job_id,
                    retry_count=new_retry,
                    max_retries=MAX_JOB_RETRY_ATTEMPTS,
                    backoff_seconds=backoff,
                )
                time.sleep(backoff)
                schedule_job_retry(job_id, new_retry, err_msg)
                enqueue_job(job_id)
            else:
                log_event(
                    logger,
                    "error",
                    "job_moved_to_dlq",
                    job_id=job_id,
                    status="dead",
                    retry_count=new_retry - 1,
                    max_retries=MAX_JOB_RETRY_ATTEMPTS,
                )
                mark_job_dead(job_id, err_msg, processing_ms)
                push_dlq(job_id)
    log_event(logger, "info", "worker_loop_exited")


if __name__ == "__main__":
    configure_logging()
    install_signal_handlers()
    if RUNQ_FORCE_FAIL_PATH:
        log_event(logger, "warning", "worker_force_fail_enabled")
    wait_for_redis()
    log_event(logger, "info", "worker_model_loading", model="en_core_web_sm")
    preload_model()
    log_event(logger, "info", "worker_model_ready", model="en_core_web_sm")
    log_event(logger, "info", "worker_model_loading", model="classifier")
    preload_classifier()
    log_event(logger, "info", "worker_model_ready", model="classifier")
    requeue_stale_running_jobs()
    run_worker_loop()
