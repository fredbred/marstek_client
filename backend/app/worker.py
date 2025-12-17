"""RQ worker for background tasks."""

import os

from redis import Redis
from rq import Connection, Queue, Worker

from app.config import get_settings
from app.core.logger import configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


def main() -> None:
    """Start RQ worker."""
    redis_conn = Redis.from_url(settings.redis.url)
    queue_name = os.getenv("RQ_WORKER_QUEUE", "default")

    logger.info("starting_rq_worker", queue=queue_name)

    with Connection(redis_conn):
        worker = Worker([Queue(queue_name)])
        worker.work()


if __name__ == "__main__":
    main()

