"""Approval history tracking service.

This service records and retrieves user approval decisions for email sorting proposals,
enabling accuracy monitoring and future ML training. Tracks three types of decisions:
- approve: User accepts AI suggestion (approved=True, user_selected = ai_suggested)
- reject: User rejects email sorting (approved=False)
- change_folder: User selects different folder (approved=True, user_selected != ai_suggested)

Statistics Calculations:
- total_decisions: Count of all approval decisions
- approved_count: Count of "approve" actions
- rejected_count: Count of "reject" actions
- changed_count: Count of "change_folder" actions
- approval_rate: (approved + changed) / total_decisions (AI acceptance rate)
- top_folders: Most frequently selected folders by user

Usage:
    service = ApprovalHistoryService(db_session)

    # Record a decision
    record = await service.record_decision(
        user_id=1,
        email_queue_id=123,
        action_type="approve",
        ai_suggested_folder_id=5,
        user_selected_folder_id=5
    )

    # Get user history
    history = await service.get_user_history(
        user_id=1,
        from_date=datetime(2025, 11, 1),
        to_date=datetime(2025, 11, 30)
    )

    # Get approval statistics
    stats = await service.get_approval_statistics(user_id=1)
    # Returns: {"total_decisions": 150, "approved": 120, "rejected": 20, "changed": 10, "approval_rate": 0.867}
"""

from datetime import datetime, UTC
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from typing import Dict, List, Optional, Any

from app.models.approval_history import ApprovalHistory
from app.models.folder_category import FolderCategory


logger = structlog.get_logger(__name__)


class ApprovalHistoryService:
    """Service for tracking and analyzing user approval decisions.

    This service implements approval history recording and retrieval for monitoring
    AI classification accuracy and user preference patterns.

    Attributes:
        db: SQLAlchemy async session for database operations
    """

    def __init__(self, db: AsyncSession):
        """Initialize approval history service.

        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    async def record_decision(
        self,
        user_id: int,
        email_queue_id: int,
        action_type: str,
        ai_suggested_folder_id: Optional[int],
        user_selected_folder_id: Optional[int],
    ) -> ApprovalHistory:
        """Record user approval decision for email sorting proposal.

        Creates ApprovalHistory record with approval flag derived from action_type.
        For "approve" action, user_selected_folder_id is set to ai_suggested_folder_id.

        Decision Logic:
        - approve: approved=True, user_selected_folder_id = ai_suggested_folder_id
        - change_folder: approved=True, user_selected_folder_id != ai_suggested_folder_id
        - reject: approved=False, user_selected_folder_id can be None

        Args:
            user_id: Foreign key to users.id (authenticated user)
            email_queue_id: Foreign key to email_processing_queue.id (email being sorted)
            action_type: User decision type: "approve", "reject", or "change_folder"
            ai_suggested_folder_id: Foreign key to folder_categories.id (AI's suggestion)
            user_selected_folder_id: Foreign key to folder_categories.id (user's final choice)

        Returns:
            ApprovalHistory: Created approval history record

        Raises:
            Exception: If database commit fails (logged and re-raised)

        Example:
            >>> service = ApprovalHistoryService(db)
            >>> record = await service.record_decision(
            ...     user_id=1,
            ...     email_queue_id=123,
            ...     action_type="approve",
            ...     ai_suggested_folder_id=5,
            ...     user_selected_folder_id=5
            ... )
            >>> record.approved  # True
            >>> record.action_type  # "approve"
        """
        try:
            # Derive approved flag from action_type
            # approve and change_folder are considered "approved" (user accepts sorting)
            # reject is considered "not approved" (user rejects sorting)
            approved = action_type in ("approve", "change_folder")

            # For "approve" action, user_selected_folder_id should equal ai_suggested_folder_id
            if action_type == "approve" and ai_suggested_folder_id is not None:
                user_selected_folder_id = ai_suggested_folder_id

            # Create approval history record
            approval_record = ApprovalHistory(
                user_id=user_id,
                email_queue_id=email_queue_id,
                action_type=action_type,
                ai_suggested_folder_id=ai_suggested_folder_id,
                user_selected_folder_id=user_selected_folder_id,
                approved=approved,
                timestamp=datetime.now(UTC),
            )

            self.db.add(approval_record)
            await self.db.commit()
            await self.db.refresh(approval_record)

            # Log successful recording
            logger.info(
                "approval_decision_recorded",
                user_id=user_id,
                email_queue_id=email_queue_id,
                action_type=action_type,
                approved=approved,
                approval_history_id=approval_record.id,
            )

            return approval_record

        except Exception as e:
            logger.error(
                "error_recording_approval_decision",
                user_id=user_id,
                email_queue_id=email_queue_id,
                action_type=action_type,
                error=str(e),
            )
            await self.db.rollback()
            raise

    async def get_user_history(
        self,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        action_type: Optional[str] = None,
    ) -> List[ApprovalHistory]:
        """Query user's approval history with optional filters.

        Retrieves approval history records for specified user with optional filtering
        by date range and action type. Results ordered by timestamp descending (newest first).

        Args:
            user_id: Foreign key to users.id (filter by user)
            from_date: Optional start date for history query (inclusive, timezone-aware UTC)
            to_date: Optional end date for history query (inclusive, timezone-aware UTC)
            action_type: Optional action type filter: "approve", "reject", or "change_folder"

        Returns:
            List[ApprovalHistory]: List of approval history records, ordered by timestamp desc

        Example:
            >>> service = ApprovalHistoryService(db)
            >>> history = await service.get_user_history(
            ...     user_id=1,
            ...     from_date=datetime(2025, 11, 1, tzinfo=UTC),
            ...     to_date=datetime(2025, 11, 30, tzinfo=UTC),
            ...     action_type="approve"
            ... )
            >>> len(history)  # 120
            >>> history[0].timestamp  # Most recent decision
        """
        try:
            # Build query with user_id filter
            stmt = select(ApprovalHistory).where(ApprovalHistory.user_id == user_id)

            # Add date range filter if specified
            if from_date is not None:
                stmt = stmt.where(ApprovalHistory.timestamp >= from_date)

            if to_date is not None:
                stmt = stmt.where(ApprovalHistory.timestamp <= to_date)

            # Add action_type filter if specified
            if action_type is not None:
                stmt = stmt.where(ApprovalHistory.action_type == action_type)

            # Order by timestamp descending (newest first)
            stmt = stmt.order_by(ApprovalHistory.timestamp.desc())

            # Execute query
            result = await self.db.execute(stmt)
            history_records = result.scalars().all()

            logger.info(
                "approval_history_retrieved",
                user_id=user_id,
                record_count=len(history_records),
                from_date=from_date.isoformat() if from_date else None,
                to_date=to_date.isoformat() if to_date else None,
                action_type=action_type,
            )

            return list(history_records)

        except Exception as e:
            logger.error(
                "error_retrieving_approval_history",
                user_id=user_id,
                from_date=from_date.isoformat() if from_date else None,
                to_date=to_date.isoformat() if to_date else None,
                action_type=action_type,
                error=str(e),
            )
            raise

    async def get_approval_statistics(
        self,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculate approval decision statistics for user.

        Computes aggregate statistics from user's approval history:
        - total_decisions: Total number of approval decisions
        - approved: Count of "approve" actions
        - rejected: Count of "reject" actions
        - folder_changed: Count of "change_folder" actions
        - approval_rate: (approved + folder_changed) / total_decisions (0-1)
        - top_folders: Top 5 most frequently selected folders with counts

        Approval rate represents AI acceptance rate (how often user accepts sorting,
        with or without folder change).

        Args:
            user_id: Foreign key to users.id (filter by user)
            from_date: Optional start date for statistics calculation (inclusive)
            to_date: Optional end date for statistics calculation (inclusive)

        Returns:
            Dict with keys:
                - total_decisions (int): Total number of decisions
                - approved (int): Count of "approve" actions
                - rejected (int): Count of "reject" actions
                - folder_changed (int): Count of "change_folder" actions
                - approval_rate (float): AI acceptance rate (0.0-1.0)
                - top_folders (List[Dict]): [{"name": str, "count": int}, ...]

        Example:
            >>> service = ApprovalHistoryService(db)
            >>> stats = await service.get_approval_statistics(user_id=1)
            >>> stats
            {
                "total_decisions": 150,
                "approved": 120,
                "rejected": 20,
                "folder_changed": 10,
                "approval_rate": 0.867,  # (120 + 10) / 150
                "top_folders": [
                    {"name": "Government", "count": 45},
                    {"name": "Clients", "count": 35},
                    ...
                ]
            }
        """
        try:
            # Get user history with date filters
            history_records = await self.get_user_history(
                user_id=user_id,
                from_date=from_date,
                to_date=to_date,
            )

            # Calculate total decisions
            total_decisions = len(history_records)

            # Count decisions by action_type
            approved_count = sum(1 for r in history_records if r.action_type == "approve")
            rejected_count = sum(1 for r in history_records if r.action_type == "reject")
            changed_count = sum(1 for r in history_records if r.action_type == "change_folder")

            # Calculate approval rate (how often user accepts AI suggestion, with or without change)
            # approval_rate = (approved + changed) / total
            approval_rate = 0.0
            if total_decisions > 0:
                approval_rate = (approved_count + changed_count) / total_decisions

            # Get top 5 folders by user selection count (aggregation query)
            # Query user_selected_folder_id counts, join with folder_categories for names
            top_folders_stmt = (
                select(
                    FolderCategory.name,
                    func.count(ApprovalHistory.id).label("count")
                )
                .join(
                    ApprovalHistory,
                    FolderCategory.id == ApprovalHistory.user_selected_folder_id
                )
                .where(ApprovalHistory.user_id == user_id)
            )

            # Add date range filters for top_folders query
            if from_date is not None:
                top_folders_stmt = top_folders_stmt.where(ApprovalHistory.timestamp >= from_date)
            if to_date is not None:
                top_folders_stmt = top_folders_stmt.where(ApprovalHistory.timestamp <= to_date)

            # Group by folder name, order by count descending, limit to top 5
            top_folders_stmt = (
                top_folders_stmt
                .group_by(FolderCategory.name)
                .order_by(func.count(ApprovalHistory.id).desc())
                .limit(5)
            )

            # Execute top_folders aggregation query
            top_folders_result = await self.db.execute(top_folders_stmt)
            top_folders_rows = top_folders_result.all()

            # Format top_folders as list of dicts
            top_folders = [
                {"name": row.name, "count": row.count}
                for row in top_folders_rows
            ]

            # Build statistics dictionary
            statistics = {
                "total_decisions": total_decisions,
                "approved": approved_count,
                "rejected": rejected_count,
                "folder_changed": changed_count,
                "approval_rate": round(approval_rate, 3),  # Round to 3 decimal places
                "top_folders": top_folders,
            }

            logger.info(
                "approval_statistics_calculated",
                user_id=user_id,
                total_decisions=total_decisions,
                approval_rate=approval_rate,
                from_date=from_date.isoformat() if from_date else None,
                to_date=to_date.isoformat() if to_date else None,
            )

            return statistics

        except Exception as e:
            logger.error(
                "error_calculating_approval_statistics",
                user_id=user_id,
                from_date=from_date.isoformat() if from_date else None,
                to_date=to_date.isoformat() if to_date else None,
                error=str(e),
            )
            raise
