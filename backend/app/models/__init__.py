"""Models package for the application."""

from app.models.base import BaseModel
from app.models.user import User
from app.models.session import Session
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.context_models import EmailMessage, RAGContext
from app.models.prompt_versions import PromptVersion
from app.models.manual_notification import ManualNotification
from app.models.dead_letter_queue import DeadLetterQueue
from app.models.batch_notification_queue import BatchNotificationQueue
from app.models.approval_history import ApprovalHistory
from app.models.indexing_progress import IndexingProgress
from app.models.workflow_mapping import WorkflowMapping
from app.models.notification_preferences import NotificationPreferences

__all__ = [
    "BaseModel",
    "User",
    "Session",
    "EmailProcessingQueue",
    "FolderCategory",
    "EmailMessage",
    "RAGContext",
    "PromptVersion",
    "ManualNotification",
    "DeadLetterQueue",
    "BatchNotificationQueue",
    "ApprovalHistory",
    "IndexingProgress",
    "WorkflowMapping",
    "NotificationPreferences",
]
