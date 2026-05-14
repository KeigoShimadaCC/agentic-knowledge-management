import logging
import os

from redis import Redis
from rq import Queue, Worker

logging.basicConfig(level=logging.INFO)


def main():
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    conn = Redis.from_url(redis_url)
    queues = [Queue("kos-ingest", connection=conn)]
    worker = Worker(queues, connection=conn)
    worker.work()


if __name__ == "__main__":
    main()
