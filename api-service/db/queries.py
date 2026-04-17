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


def list_jobs(status=None, job_type=None, page=1, per_page=20):
    where_clauses = []
    params = []

    if status:
        where_clauses.append("status = %s")
        params.append(status)
    if job_type:
        where_clauses.append("job_type = %s")
        params.append(job_type)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    count_query = f"""
    SELECT COUNT(*) AS total
    FROM jobs
    {where_sql}
    """
    count_row = fetch_one(count_query, tuple(params) if params else None)
    total = int(count_row["total"])

    offset = (page - 1) * per_page
    query = f"""
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
    {where_sql}
    ORDER BY created_at DESC, id DESC
    LIMIT %s OFFSET %s
    """
    query_params = [*params, per_page, offset]
    rows = fetch_all(query, tuple(query_params))
    return rows, total


def get_status_counts():
    query = """
    SELECT status, COUNT(*) AS count
    FROM jobs
    GROUP BY status
    """
    rows = fetch_all(query)
    return {row["status"]: int(row["count"]) for row in rows}


def get_average_processing_ms():
    query = """
    SELECT AVG(processing_ms) AS avg_processing_ms
    FROM jobs
    WHERE processing_ms IS NOT NULL
    """
    row = fetch_one(query)
    value = row["avg_processing_ms"]
    return float(value) if value is not None else 0.0


def get_jobs_per_minute():
    query = """
    SELECT COUNT(*) AS count
    FROM jobs
    WHERE updated_at >= NOW() - INTERVAL '1 minute'
      AND status IN ('success', 'failed', 'dead')
    """
    row = fetch_one(query)
    return float(row["count"])
