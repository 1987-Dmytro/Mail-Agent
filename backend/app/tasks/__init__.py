"""Background tasks package.

This package contains Celery background tasks for email polling,
processing, and other asynchronous operations.
"""

# Import all tasks so Celery can discover them
from app.tasks.email_tasks import poll_user_emails, poll_all_users  # noqa: F401
from app.tasks.indexing_tasks import index_user_emails  # noqa: F401
from app.tasks.notification_tasks import send_batch_notifications, send_daily_digest  # noqa: F401

__all__ = [
    "poll_user_emails",
    "poll_all_users",
    "index_user_emails",
    "send_batch_notifications",
    "send_daily_digest",
]
