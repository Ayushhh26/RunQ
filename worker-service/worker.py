import json
import logging
import time

from db import (
    get_job_for_processing,
    mark_job_failed,
    mark_job_running,
    mark_job_success,
)
from logging_config import configure_logging
from processors.classify import classify_document as run_classify_document, preload_classifier
from processors.extract import extract_metadata as run_extract_metadata, preload_model
from redis_client import get_redis_client, pop_job_id

logger = logging.getLogger("runq-worker")


def wait_for_redis():
    while True:
        try:
            client = get_redis_client()
            client.ping()
            logger.info("Connected to Redis")
            return
        except Exception as exc:
            logger.warning("Waiting for Redis... %s", exc)
            time.sleep(2)


def process_job(job_type, file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    if job_type == "extract_metadata":
        result = run_extract_metadata(content)
    elif job_type == "classify_document":
        result = run_classify_document(content)
    elif job_type == "summarize_document":
        result = {
            "processor": "placeholder_summarize",
            "preview": content[:200],
            "original_length": len(content),
        }
    else:
        raise ValueError(f"Unsupported job_type: {job_type}")

    return result


def run_worker_loop():
    while True:
        job_id = pop_job_id(timeout=5)
        if not job_id:
            continue

        started_at = time.time()
        logger.info("Starting job %s", job_id)
        try:
            job = get_job_for_processing(job_id)
            if not job:
                logger.warning("Job %s not found in database", job_id)
                continue

            _, job_type, file_path, _ = job
            mark_job_running(job_id)
            result = process_job(job_type, file_path)
            processing_ms = int((time.time() - started_at) * 1000)
            mark_job_success(job_id, json.dumps(result), processing_ms)
            logger.info("Finished job %s successfully", job_id)
        except Exception as exc:
            processing_ms = int((time.time() - started_at) * 1000)
            mark_job_failed(job_id, str(exc), processing_ms)
            logger.exception("Job %s failed", job_id)


if __name__ == "__main__":
    configure_logging()
    wait_for_redis()
    logger.info("Loading spaCy model en_core_web_sm...")
    preload_model()
    logger.info("spaCy model ready")
    logger.info("Loading document classifier...")
    preload_classifier()
    logger.info("Classifier ready")
    run_worker_loop()
