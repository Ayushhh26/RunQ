import os

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "runq")
POSTGRES_USER = os.getenv("POSTGRES_USER", "runq")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "runq")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Optional: when set to a job `file_path` value (e.g. documents/report_001.txt), the worker raises
# during processing so you can verify retries + DLQ locally. Leave unset in production.
RUNQ_FORCE_FAIL_PATH = os.getenv("RUNQ_FORCE_FAIL_PATH", "").strip()

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_SUCCESS = "success"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_DEAD = "dead"

VALID_JOB_STATUSES = {
    JOB_STATUS_PENDING,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCESS,
    JOB_STATUS_FAILED,
    JOB_STATUS_DEAD,
}

JOB_TYPE_EXTRACT_METADATA = "extract_metadata"
JOB_TYPE_CLASSIFY_DOCUMENT = "classify_document"
JOB_TYPE_SUMMARIZE_DOCUMENT = "summarize_document"

VALID_JOB_TYPES = {
    JOB_TYPE_EXTRACT_METADATA,
    JOB_TYPE_CLASSIFY_DOCUMENT,
    JOB_TYPE_SUMMARIZE_DOCUMENT,
}

# Step 8: failures with new_retry 1..MAX get backoff + re-queue; new_retry > MAX -> dead + DLQ.
MAX_JOB_RETRY_ATTEMPTS = 3
# Backoff before re-queue after failure attempts 1..MAX (seconds); length must match MAX.
RETRY_BACKOFF_SECONDS = (1, 2, 4)
assert len(RETRY_BACKOFF_SECONDS) == MAX_JOB_RETRY_ATTEMPTS

# Step 9: running jobs older than this threshold are considered stale and re-queued.
STALE_JOB_THRESHOLD_SECONDS = int(os.getenv("STALE_JOB_THRESHOLD_SECONDS", "300"))
