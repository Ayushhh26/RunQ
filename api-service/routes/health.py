from fastapi import APIRouter

from config import ACTIVE_WORKERS
from db.connection import get_connection
from redis_client import get_queue_depth, get_redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    postgres_status = "disconnected"
    redis_status = "disconnected"
    queue_depth = 0

    try:
        conn = get_connection()
        conn.close()
        postgres_status = "connected"
    except Exception:
        pass

    try:
        r = get_redis_client()
        r.ping()
        redis_status = "connected"
        queue_depth = get_queue_depth()
    except Exception:
        pass

    return {
        "status": "healthy",
        "postgres": postgres_status,
        "redis": redis_status,
        "active_workers": ACTIVE_WORKERS,
        "queue_depth": queue_depth,
    }
