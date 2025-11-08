"""Workflow instance tracking and lifecycle management.

This service manages the lifecycle of email classification workflows, including:
- Workflow initialization with dependency injection
- Thread ID generation for checkpoint tracking
- State persistence to EmailProcessingQueue
- Workflow invocation with proper configuration

The service solves the dependency injection challenge for LangGraph nodes by using
functools.partial to bind database sessions and API clients to node functions before
workflow compilation.
"""

import uuid
from functools import partial
from typing import Dict

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from app.workflows.states import EmailWorkflowState
from app.workflows import nodes
from app.core.gmail_client import GmailClient
from app.core.llm_client import LLMClient
from app.core.telegram_bot import TelegramBotClient
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.workflow_mapping import WorkflowMapping


logger = structlog.get_logger(__name__)


class WorkflowInstanceTracker:
    """Service for managing email classification workflow instances.

    This service handles workflow lifecycle management with proper dependency injection
    for LangGraph nodes. It solves the challenge that LangGraph nodes typically only
    receive state parameters, but our nodes need database sessions and API clients.

    Solution: Use functools.partial to bind dependencies to node functions before
    adding them to the StateGraph. This allows nodes to access db, gmail_client,
    and llm_client while maintaining LangGraph's state-based execution model.

    Attributes:
        db: SQLAlchemy async session for database operations
        gmail_client: Gmail API client for email retrieval
        llm_client: Gemini LLM client for classification
        telegram_bot_client: Telegram Bot client for message sending
        checkpointer: PostgreSQL checkpointer for workflow state persistence
    """

    def __init__(
        self,
        db: AsyncSession,
        gmail_client: GmailClient,
        llm_client: LLMClient,
        telegram_bot_client: TelegramBotClient,
        database_url: str,
    ):
        """Initialize workflow tracker with required dependencies.

        Args:
            db: SQLAlchemy async session
            gmail_client: Gmail API client instance
            llm_client: Gemini LLM client instance
            telegram_bot_client: Telegram Bot client instance
            database_url: PostgreSQL connection string for checkpointing
        """
        self.db = db
        self.gmail_client = gmail_client
        self.llm_client = llm_client
        self.telegram_bot_client = telegram_bot_client

        # Initialize PostgreSQL checkpointer for workflow state persistence
        # Convert psycopg:// to postgresql:// for PostgresSaver compatibility
        if database_url.startswith("postgresql+psycopg://"):
            checkpoint_url = database_url.replace("postgresql+psycopg://", "postgresql://")
        else:
            checkpoint_url = database_url

        self.checkpointer = PostgresSaver.from_conn_string(
            conn_string=checkpoint_url,
            sync=False,  # Async mode for FastAPI
        )

        logger.debug("workflow_tracker_initialized", checkpointer="PostgreSQL")

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow with dependency-injected nodes.

        This method creates a StateGraph with nodes that have dependencies bound
        using functools.partial. This allows nodes to access db, gmail_client,
        and llm_client without violating LangGraph's state-only parameter model.

        Returns:
            Compiled StateGraph ready for execution with checkpointing

        Example:
            >>> tracker = WorkflowInstanceTracker(db, gmail, llm, db_url)
            >>> workflow = tracker._build_workflow()
            >>> result = await workflow.ainvoke(initial_state, config)
        """
        logger.debug("building_workflow_with_injected_dependencies")

        # Create workflow graph
        workflow = StateGraph(EmailWorkflowState)

        # Bind dependencies to node functions using functools.partial
        # This creates new functions with db, gmail_client, llm_client pre-filled
        extract_context_with_deps = partial(
            nodes.extract_context,
            db=self.db,
            gmail_client=self.gmail_client,
        )

        classify_with_deps = partial(
            nodes.classify,
            db=self.db,
            gmail_client=self.gmail_client,
            llm_client=self.llm_client,
        )

        # Bind dependencies for send_telegram node (Story 2.6)
        send_telegram_with_deps = partial(
            nodes.send_telegram,
            db=self.db,
            telegram_bot_client=self.telegram_bot_client,
        )

        # Bind dependencies for execute_action node (Story 2.7)
        execute_action_with_deps = partial(
            nodes.execute_action,
            db=self.db,
            gmail_client=self.gmail_client,
        )

        # Bind dependencies for send_confirmation node (Story 2.7)
        send_confirmation_with_deps = partial(
            nodes.send_confirmation,
            db=self.db,
            telegram_bot_client=self.telegram_bot_client,
        )

        # Stub node without dependencies
        await_approval_node = nodes.await_approval

        # Add nodes to workflow with dependency-injected functions
        workflow.add_node("extract_context", extract_context_with_deps)
        workflow.add_node("classify", classify_with_deps)
        workflow.add_node("send_telegram", send_telegram_with_deps)
        workflow.add_node("await_approval", await_approval_node)
        workflow.add_node("execute_action", execute_action_with_deps)
        workflow.add_node("send_confirmation", send_confirmation_with_deps)

        # Define workflow edges (sequential flow)
        workflow.set_entry_point("extract_context")
        workflow.add_edge("extract_context", "classify")
        workflow.add_edge("classify", "send_telegram")
        workflow.add_edge("send_telegram", "await_approval")
        # await_approval → execute_action (Story 2.7: Resume after user decision)
        workflow.add_edge("await_approval", "execute_action")
        workflow.add_edge("execute_action", "send_confirmation")
        workflow.add_edge("send_confirmation", END)

        # Compile workflow with PostgreSQL checkpointer
        app = workflow.compile(checkpointer=self.checkpointer)

        logger.debug("workflow_compiled_with_dependencies")

        return app

    async def start_workflow(self, email_id: int, user_id: int) -> str:
        """Start a new email classification workflow.

        This method orchestrates the complete workflow initialization process:
        1. Generate unique thread_id for checkpoint tracking
        2. Initialize EmailWorkflowState with email and user IDs
        3. Build workflow with dependency-injected nodes
        4. Invoke workflow asynchronously (runs until await_approval pause)
        5. Update EmailProcessingQueue with classification results
        6. Return thread_id for later resumption (Story 2.7)

        The workflow will execute: extract_context → classify → send_telegram → await_approval
        and then PAUSE with state saved to PostgreSQL.

        Args:
            email_id: EmailProcessingQueue.id of the email to classify
            user_id: User ID who owns the email

        Returns:
            str: Thread ID for workflow tracking (format: email_{email_id}_{uuid})
                Use this thread_id to resume workflow later via Telegram callback

        Raises:
            ValueError: If email_id not found or doesn't belong to user_id
            Exception: Any workflow execution errors

        Example:
            >>> tracker = WorkflowInstanceTracker(db, gmail, llm, db_url)
            >>> thread_id = await tracker.start_workflow(email_id=123, user_id=456)
            >>> print(thread_id)  # "email_123_abc-def-123-456"
            >>> # Workflow paused at await_approval, state in PostgreSQL
        """
        logger.info("workflow_start_requested", email_id=email_id, user_id=user_id)

        # Step 1: Generate unique thread_id for checkpoint tracking
        thread_id = f"email_{email_id}_{uuid.uuid4()}"

        logger.debug("thread_id_generated", thread_id=thread_id)

        # Step 1.5: Create WorkflowMapping entry for callback reconnection
        await self._create_workflow_mapping(email_id, user_id, thread_id)

        # Step 2: Initialize EmailWorkflowState
        # Note: Most fields will be populated by workflow nodes
        initial_state: EmailWorkflowState = {
            "email_id": str(email_id),
            "user_id": str(user_id),
            "thread_id": thread_id,
            # Fields populated by extract_context node:
            "email_content": "",
            "sender": "",
            "subject": "",
            "body_preview": "",  # Populated by send_telegram node (Story 2.6)
            # Fields populated by classify node:
            "classification": None,
            "proposed_folder": None,
            "proposed_folder_id": None,  # Story 2.6
            "classification_reasoning": None,
            "priority_score": 0,
            # Fields populated by send_telegram node (Story 2.6):
            "telegram_message_id": None,
            # Fields populated by user approval (Story 2.7):
            "user_decision": None,
            "selected_folder": None,
            "selected_folder_id": None,  # Story 2.6
            # Fields populated by execute_action (Story 2.7):
            "final_action": None,
            # Error handling:
            "error_message": None,
        }

        # Step 3: Build workflow with dependency injection
        workflow = self._build_workflow()

        # Step 4: Invoke workflow asynchronously
        # Config specifies thread_id for checkpoint tracking
        config = {"configurable": {"thread_id": thread_id}}

        logger.info(
            "workflow_invoking",
            email_id=email_id,
            thread_id=thread_id,
            note="Workflow will pause at await_approval node",
        )

        try:
            # Invoke workflow - runs until await_approval pauses execution
            result_state = await workflow.ainvoke(initial_state, config=config)

            logger.info(
                "workflow_paused_at_await_approval",
                email_id=email_id,
                thread_id=thread_id,
                proposed_folder=result_state.get("proposed_folder"),
                priority_score=result_state.get("priority_score"),
            )

        except Exception as e:
            logger.error(
                "workflow_execution_failed",
                email_id=email_id,
                thread_id=thread_id,
                error=str(e),
            )
            # Update EmailProcessingQueue status to "error"
            await self._update_email_status(email_id, "error", error_message=str(e))
            raise

        # Step 5: Update EmailProcessingQueue with classification results
        await self._save_classification_results(email_id, result_state)

        # Step 6: Update status to "awaiting_approval"
        await self._update_email_status(email_id, "awaiting_approval")

        logger.info(
            "workflow_started_successfully",
            email_id=email_id,
            thread_id=thread_id,
            status="awaiting_approval",
        )

        return thread_id

    async def _save_classification_results(
        self, email_id: int, state: EmailWorkflowState
    ) -> None:
        """Save classification results to EmailProcessingQueue.

        Updates the database with AI classification results:
        - proposed_folder_id (lookup FolderCategory by name)
        - classification_reasoning
        - priority_score
        - is_priority (True if priority_score >= 70)

        Args:
            email_id: EmailProcessingQueue.id to update
            state: Workflow state containing classification results
        """
        logger.debug("saving_classification_results", email_id=email_id)

        # Load EmailProcessingQueue entry
        result = await self.db.execute(
            select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
        )
        email = result.scalar_one_or_none()

        if not email:
            logger.error("email_not_found_for_update", email_id=email_id)
            return

        # Lookup proposed_folder_id by folder name
        proposed_folder_name = state.get("proposed_folder")
        if proposed_folder_name:
            folder_result = await self.db.execute(
                select(FolderCategory).where(
                    FolderCategory.user_id == int(state["user_id"]),
                    FolderCategory.name == proposed_folder_name,
                )
            )
            folder = folder_result.scalar_one_or_none()
            if folder:
                email.proposed_folder_id = folder.id

        # Update classification fields
        email.classification = state.get("classification")
        email.classification_reasoning = state.get("classification_reasoning")
        email.priority_score = state.get("priority_score", 0)
        email.is_priority = email.priority_score >= 70

        await self.db.commit()

        logger.debug(
            "classification_results_saved",
            email_id=email_id,
            proposed_folder=proposed_folder_name,
            priority_score=email.priority_score,
            is_priority=email.is_priority,
        )

    async def _update_email_status(
        self, email_id: int, status: str, error_message: str = None
    ) -> None:
        """Update EmailProcessingQueue status.

        Args:
            email_id: EmailProcessingQueue.id to update
            status: New status value (e.g., "awaiting_approval", "error")
            error_message: Optional error message if status is "error"
        """
        result = await self.db.execute(
            select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
        )
        email = result.scalar_one_or_none()

        if email:
            email.status = status
            if error_message:
                # Store error in classification_reasoning for debugging
                email.classification_reasoning = f"Error: {error_message}"
            await self.db.commit()
            logger.debug("email_status_updated", email_id=email_id, status=status)

    async def _create_workflow_mapping(
        self, email_id: int, user_id: int, thread_id: str
    ) -> None:
        """Create WorkflowMapping entry for callback reconnection.

        This mapping enables Telegram callback handlers to reconnect to the correct
        workflow instance when the user clicks approval buttons hours/days later.

        Args:
            email_id: EmailProcessingQueue.id
            user_id: User ID who owns the email
            thread_id: LangGraph thread ID for checkpoint tracking
        """
        from datetime import datetime, UTC

        workflow_mapping = WorkflowMapping(
            email_id=email_id,
            user_id=user_id,
            thread_id=thread_id,
            telegram_message_id=None,  # Will be set by send_telegram node
            workflow_state="initialized",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        self.db.add(workflow_mapping)
        await self.db.commit()

        logger.debug(
            "workflow_mapping_created",
            email_id=email_id,
            thread_id=thread_id,
        )
