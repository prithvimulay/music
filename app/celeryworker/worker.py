import os
from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "puremusic",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
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

# Optional: Configure task routes for different queues
celery_app.conf.task_routes = {
    "app.celeryworker.tasks.stem_separation": {"queue": "stem_separation"},
    "app.celeryworker.tasks.feature_extraction": {"queue": "feature_extraction"},
    "app.celeryworker.tasks.generate_fusion": {"queue": "generate_fusion"},
    "app.celeryworker.tasks.enhance_audio": {"queue": "enhance_audio"},
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
