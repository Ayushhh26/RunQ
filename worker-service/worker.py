import os
import time
import redis


def wait_for_redis():
    while True:
        try:
            client = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=6379,
                decode_responses=True,
            )
            client.ping()
            print("Connected to Redis")
            return
        except Exception as exc:
            print(f"Waiting for Redis... {exc}")
            time.sleep(2)


if __name__ == "__main__":
    wait_for_redis()
    while True:
        print("Worker alive")
        time.sleep(5)
