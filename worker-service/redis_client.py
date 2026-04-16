import redis

from config import REDIS_HOST, REDIS_PORT

QUEUE_NAME = "runq:queue"
DLQ_NAME = "runq:dlq"


def get_redis_client():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def enqueue_job(job_id: str):
    client = get_redis_client()
    client.lpush(QUEUE_NAME, job_id)


def push_dlq(job_id: str):
    client = get_redis_client()
    client.lpush(DLQ_NAME, job_id)


def pop_job_id(timeout=5):
    client = get_redis_client()
    item = client.brpop(QUEUE_NAME, timeout=timeout)
    if item is None:
        return None
    _, job_id = item
    return job_id
