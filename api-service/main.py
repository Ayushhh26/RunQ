from fastapi import FastAPI
import os
import psycopg2
import redis

app = FastAPI()


@app.get("/")
def root():
    return {"status": "api alive"}


@app.get("/health")
def health():
    postgres_status = "disconnected"
    redis_status = "disconnected"

    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            dbname=os.getenv("POSTGRES_DB", "runq"),
            user=os.getenv("POSTGRES_USER", "runq"),
            password=os.getenv("POSTGRES_PASSWORD", "runq"),
        )
        conn.close()
        postgres_status = "connected"
    except Exception:
        pass

    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=6379,
            decode_responses=True,
        )
        r.ping()
        redis_status = "connected"
    except Exception:
        pass

    return {
        "api": "healthy",
        "postgres": postgres_status,
        "redis": redis_status,
    }
