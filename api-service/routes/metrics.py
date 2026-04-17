from fastapi import APIRouter

from db.queries import get_average_processing_ms, get_jobs_per_minute, get_status_counts
from redis_client import get_queue_depth

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics():
    counts = get_status_counts()
    total_jobs = sum(counts.values())
    success = counts.get("success", 0)
    failed = counts.get("failed", 0)
    dead = counts.get("dead", 0)
    success_rate = (success / total_jobs * 100) if total_jobs else 0.0

    try:
        queue_depth = get_queue_depth()
    except Exception:
        queue_depth = 0

    return {
        "total_jobs": total_jobs,
        "success": success,
        "failed": failed,
        "dead": dead,
        "success_rate": f"{success_rate:.1f}%",
        "avg_processing_time_ms": round(get_average_processing_ms(), 2),
        "queue_depth": queue_depth,
        "jobs_per_minute": round(get_jobs_per_minute(), 2),
    }
