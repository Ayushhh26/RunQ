from psycopg2.extras import RealDictCursor

from db.connection import get_connection


def execute_write(query, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()


def fetch_one(query, params=None):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()


def fetch_all(query, params=None):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()


def insert_job(job_id, job_type, status, file_path):
    query = """
    INSERT INTO jobs (id, job_type, status, file_path)
    VALUES (%s, %s, %s, %s)
    """
    execute_write(query, (str(job_id), job_type, status, file_path))


def get_job_by_id(job_id):
    query = """
    SELECT
        id,
        job_type,
        status,
        retry_count,
        file_path,
        result,
        error_message,
        processing_ms,
        created_at,
        updated_at
    FROM jobs
    WHERE id = %s
    """
    return fetch_one(query, (str(job_id),))
