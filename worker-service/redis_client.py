import redis

from config import REDIS_HOST, REDIS_PORT

QUEUE_NAME = "runq:queue"


def get_redis_client():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def pop_job_id(timeout=5):
    client = get_redis_client()
    item = client.brpop(QUEUE_NAME, timeout=timeout)
    if item is None:
        return None
    _, job_id = item
    return job_id
