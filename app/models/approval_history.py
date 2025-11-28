"""ApprovalHistory model for tracking user approval decisions.

PRIVACY CONSIDERATIONS (AC #8 - GDPR Compliance):

Data Retention Policy:
- MVP: Approval history retained indefinitely for accuracy monitoring and future ML training
- Post-MVP: Planned 90-day auto-delete for GDPR compliance via Celery task
- Rationale: Small data volume (~5000 records/day * 100 users = 1.8M records/year = ~180MB)

User Rights (GDPR Articles 15-17, 20):
- Right to Access (Article 15): GET /api/v1/stats/approvals provides user's history summary
- Right to Deletion (Article 17): User account deletion triggers CASCADE delete of all ApprovalHistory records
- Right to Data Portability (Article 20): Statistics endpoint returns JSON (exportable format)

Data Minimization (GDPR Article 5):
- Only essential fields stored: action_type, folder_ids, timestamp
- NO email content, subject, or body stored in ApprovalHistory
- email_queue_id can be NULL (SET NULL on delete) - preserves statistics even if email deleted

Security Measures:
- Multi-tenant isolation: All queries filtered by authenticated user's user_id
- Foreign key constraints prevent cross-user data access
- No PII exposed in API responses (only folder names and counts)

Future Enhancements:
- Automated cleanup job: Delete records older than 90 days
- Data export API: Download user's complete approval history as JSON
- Anonymization for ML: Remove user_id before using historical data for model training
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlmodel import Column, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.email import EmailProcessingQueue
    from app.models.folder_category import FolderCategory
    from app.models.user import User


class ApprovalHistory(BaseModel, table=True):
    """Tracks user approval decisions for AI accuracy monitoring.

    This table records every user decision (approve/reject/change_folder) when users
    respond to email sorting proposals in Telegram. Used for:
    - Monitoring AI classification accuracy (approval_rate metric)
    - Learning user preferences (future ML training)
    - Providing statistics to users (GET /api/v1/stats/approvals)

    Workflow Integration:
    - Created in execute_action node after Gmail label application
    - Non-blocking: Errors logged but don't halt workflow
    - State fields required: user_id, email_id, user_decision, proposed_folder_id, selected_folder_id

    Database Growth Considerations:
    - Growth rate: ~5000 records/day (100 users * 50 decisions/day)
    - Indexes on (user_id, timestamp) and action_type ensure queries remain fast
    - PostgreSQL table size estimate: 180MB/year (manageable for MVP scale)
    - Monitor via Prometheus metric: approval_history_table_size_bytes

    Attributes:
        id: Primary key
        user_id: Foreign key to users.id (CASCADE delete when user account deleted)
        email_queue_id: Foreign key to email_processing_queue.id (SET NULL, nullable - preserves history if email deleted)
        action_type: User decision type: "approve", "reject", or "change_folder"
        ai_suggested_folder_id: Foreign key to folder_categories.id (AI's suggested folder, SET NULL)
        user_selected_folder_id: Foreign key to folder_categories.id (User's final choice, SET NULL)
        approved: Boolean derived from action_type (True for approve/change_folder, False for reject)
        timestamp: When decision was made (UTC, server_default=now(), indexed for date-range queries)
        created_at: Record creation timestamp (inherited from BaseModel)
        user: Relationship to User model
        email: Relationship to EmailProcessingQueue model
        ai_suggested_folder: Relationship to FolderCategory model (AI suggestion)
        user_selected_folder: Relationship to FolderCategory model (user's choice)
    """

    __tablename__ = "approval_history"

    id: int = Field(default=None, primary_key=True)

    user_id: int = Field(
        foreign_key="users.id",
        nullable=False,
        index=True,
        ondelete="CASCADE"
    )

    email_queue_id: Optional[int] = Field(
        default=None,
        foreign_key="email_processing_queue.id",
        nullable=True,
        ondelete="SET NULL"
    )

    action_type: str = Field(
        max_length=50,
        nullable=False
    )

    ai_suggested_folder_id: Optional[int] = Field(
        default=None,
        foreign_key="folder_categories.id",
        nullable=True,
        ondelete="SET NULL"
    )

    user_selected_folder_id: Optional[int] = Field(
        default=None,
        foreign_key="folder_categories.id",
        nullable=True,
        ondelete="SET NULL"
    )

    approved: bool = Field(
        sa_column=Column(Boolean, nullable=False)
    )

    timestamp: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            index=True
        )
    )

    # Compound index for efficient date-range queries on user history (AC #7)
    # Most common query pattern: "Get user's approval history for date range"
    # Single index on action_type for filtering by decision type
    __table_args__ = (
        Index('idx_approval_history_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_approval_history_action_type', 'action_type'),
    )

    # Relationships
    user: Optional["User"] = Relationship(back_populates="approval_history")
    email: Optional["EmailProcessingQueue"] = Relationship()
    ai_suggested_folder: Optional["FolderCategory"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ApprovalHistory.ai_suggested_folder_id]"}
    )
    user_selected_folder: Optional["FolderCategory"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ApprovalHistory.user_selected_folder_id]"}
    )


# Avoid circular imports
from app.models.email import EmailProcessingQueue  # noqa: E402, F401
from app.models.folder_category import FolderCategory  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
