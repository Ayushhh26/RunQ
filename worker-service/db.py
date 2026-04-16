import psycopg2

from config import (
    JOB_STATUS_FAILED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCESS,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)


def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        port=POSTGRES_PORT,
    )


def execute_write(query, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()


def fetch_one(query, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()


def fetch_all(query, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def get_job_for_processing(job_id):
    query = """
    SELECT id, job_type, file_path, retry_count
    FROM jobs
    WHERE id = %s
    """
    return fetch_one(query, (job_id,))


def mark_job_running(job_id):
    query = """
    UPDATE jobs
    SET status = %s, updated_at = NOW()
    WHERE id = %s
    """
    execute_write(query, (JOB_STATUS_RUNNING, job_id))


def mark_job_success(job_id, result, processing_ms):
    query = """
    UPDATE jobs
    SET status = %s,
        result = %s::jsonb,
        error_message = NULL,
        processing_ms = %s,
        updated_at = NOW()
    WHERE id = %s
    """
    execute_write(query, (JOB_STATUS_SUCCESS, result, processing_ms, job_id))


def mark_job_failed(job_id, error_message, processing_ms):
    query = """
    UPDATE jobs
    SET status = %s,
        error_message = %s,
        processing_ms = %s,
        updated_at = NOW()
    WHERE id = %s
    """
    execute_write(query, (JOB_STATUS_FAILED, error_message, processing_ms, job_id))
