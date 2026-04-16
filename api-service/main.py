from fastapi import FastAPI

from db.connection import get_connection
from redis_client import get_redis_client
from routes.jobs import router as jobs_router

app = FastAPI()
app.include_router(jobs_router)


@app.get("/")
def root():
    return {"status": "api alive"}


@app.get("/health")
def health():
    postgres_status = "disconnected"
    redis_status = "disconnected"

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
    except Exception:
        pass

    return {
        "api": "healthy",
        "postgres": postgres_status,
        "redis": redis_status,
    }
