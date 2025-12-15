"""Celery application configuration.

This module configures the Celery application for background task processing,
including worker settings, task scheduling, and beat configuration.
"""

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Celery app
celery_app = Celery(
    "mail_agent",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=False,  # Reduce memory usage from task tracking
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,  # Process 1 task at a time to prevent OOM (workflows load ~300MB each)
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        "poll-all-users": {
            "task": "app.tasks.email_tasks.poll_all_users",
            "schedule": timedelta(seconds=int(os.getenv("POLLING_INTERVAL_SECONDS", "120"))),  # Every 2 minutes by default
        },
        "send-batch-notifications-daily": {
            "task": "app.tasks.notification_tasks.send_batch_notifications",
            "schedule": crontab(hour=18, minute=0),  # Daily at 6 PM UTC
        },
        "send-daily-digest": {
            "task": "app.tasks.notification_tasks.send_daily_digest",
            "schedule": crontab(hour=18, minute=30),  # Daily at 6:30 PM UTC (Story 2.3)
        },
        "cleanup-old-vector-embeddings": {
            "task": "app.tasks.cleanup_tasks.cleanup_old_vector_embeddings",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM UTC (90-day retention)
        },
        "auto-resume-interrupted-indexing": {
            "task": "app.tasks.indexing_tasks.check_and_resume_interrupted_indexing",
            "schedule": timedelta(seconds=120),  # Every 2 minutes - auto-resume interrupted indexing jobs
        },
    },
)

# Autodiscover tasks
celery_app.autodiscover_tasks(["app.tasks"])


if __name__ == "__main__":
    celery_app.start()
