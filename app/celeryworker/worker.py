import os
import logging
from celery import Celery
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine Redis host based on environment
redis_host = "redis"  # Default to container name in Docker network
redis_port = os.getenv("REDIS_PORT", "6379")

# Log Redis connection details
broker_url = f"redis://{redis_host}:{redis_port}/0"
backend_url = f"redis://{redis_host}:{redis_port}/0"
logger.info(f"Connecting to Redis broker at: {broker_url}")
logger.info(f"Using Redis result backend at: {backend_url}")

# Create Celery instance
celery_app = Celery(
    "puremusic",
    broker=os.getenv("CELERY_BROKER_URL", broker_url),
    backend=os.getenv("CELERY_RESULT_BACKEND", backend_url),
    include=["app.celeryworker.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour time limit for tasks
    task_soft_time_limit=3300,  # 55 minutes soft time limit
)

# Configure task routes for different queues
celery_app.conf.task_routes = {
    "app.celeryworker.tasks.generate_music_with_stems": {"queue": "music_generation"},
    "app.celeryworker.tasks.mix_stems": {"queue": "audio_mixing"},
    "app.celeryworker.tasks.cleanup_temp_files": {"queue": "maintenance"},
}

# Optional: Configure task priority
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5

# Optional: Configure periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-temp-files": {
        "task": "app.celeryworker.tasks.cleanup_temp_files",
        "schedule": 3600.0,  # Run every hour
    },
}

if __name__ == "__main__":
    celery_app.start()
