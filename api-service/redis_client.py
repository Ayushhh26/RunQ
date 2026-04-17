import redis

from config import REDIS_HOST, REDIS_PORT

QUEUE_NAME = "runq:queue"
DLQ_NAME = "runq:dlq"


def get_redis_client():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def enqueue_job(job_id: str):
    client = get_redis_client()
    client.lpush(QUEUE_NAME, job_id)


def get_queue_depth() -> int:
    client = get_redis_client()
    return int(client.llen(QUEUE_NAME))
