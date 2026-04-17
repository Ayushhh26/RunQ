from fastapi import FastAPI

from logging_config import configure_logging
from routes.jobs import router as jobs_router
from routes.health import router as health_router
from routes.metrics import router as metrics_router

configure_logging()
app = FastAPI()
app.include_router(jobs_router)
app.include_router(health_router)
app.include_router(metrics_router)


@app.get("/")
def root():
    return {"status": "api alive"}
