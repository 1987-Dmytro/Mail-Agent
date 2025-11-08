"""LangGraph workflow nodes for email classification and approval.

This module defines the individual nodes (steps) in the email processing workflow.
Each node function receives the current workflow state, performs its specific action,
and returns an updated state for the next node.

Workflow Flow:
    extract_context → classify → send_telegram → await_approval → execute_action → send_confirmation

Node Implementation Status:
    - extract_context: ✅ Full implementation (Story 2.3)
    - classify: ✅ Full implementation (Story 2.3)
    - send_telegram: 🚧 Stub (Full implementation in Story 2.6)
    - await_approval: ✅ Full implementation (Story 2.3) - Pauses workflow
    - execute_action: 🚧 Stub (Full implementation in Story 2.7)
    - send_confirmation: 🚧 Stub (Full implementation in Story 2.6)
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlmodel import Session

from app.workflows.states import EmailWorkflowState
from app.services.classification import EmailClassificationService
from app.services.approval_history import ApprovalHistoryService
from app.core.gmail_client import GmailClient
from app.core.llm_client import LLMClient
from app.core.telegram_bot import TelegramBotClient
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User


logger = structlog.get_logger(__name__)


def format_dlq_reason(
    action: str,
    retry_count: int,
    error_type: str,
    error_msg: str,
    email_id: int,
    gmail_message_id: str,
    folder_name: str,
    label_id: str,
) -> str:
    """Format Dead Letter Queue (DLQ) reason for failed email processing.

    Creates a standardized DLQ reason string with all relevant context
    for debugging and manual investigation of failed emails.

    Args:
        action: Description of the action that failed (e.g., "apply Gmail label")
        retry_count: Number of retry attempts made before failure
        error_type: Type of error (e.g., "gmail_api_failure")
        error_msg: Detailed error message from the exception
        email_id: Email processing queue ID
        gmail_message_id: Gmail message ID
        folder_name: Target folder name
        label_id: Gmail label ID

    Returns:
        Formatted DLQ reason string with all context

    Example:
        >>> format_dlq_reason(
        ...     action="apply Gmail label",
        ...     retry_count=3,
        ...     error_type="gmail_api_failure",
        ...     error_msg="503 Service Unavailable",
        ...     email_id=123,
        ...     gmail_message_id="msg_456",
        ...     folder_name="Work",
        ...     label_id="Label_789"
        ... )
        'Failed to apply Gmail label after 3 retries. Error: gmail_api_failure - 503 Service Unavailable. Email ID: 123, Gmail Message ID: msg_456, Target Folder: Work (Label ID: Label_789)'
    """
    return (
        f"Failed to {action} after {retry_count} retries. "
        f"Error: {error_type} - {error_msg}. "
        f"Email ID: {email_id}, Gmail Message ID: {gmail_message_id}, "
        f"Target Folder: {folder_name} (Label ID: {label_id})"
    )


async def extract_context(
    state: EmailWorkflowState,
    db: AsyncSession,
    gmail_client: GmailClient,
) -> EmailWorkflowState:
    """Node 1: Extract email content and user folder context.

    This node loads the full email content from Gmail and prepares context
    for classification. It populates the state with email metadata.

    Actions:
        1. Load email from Gmail using state["email_id"]
        2. Extract sender, subject, body from Gmail API response
        3. Load user's folder categories from database
        4. Update state with email content and metadata

    Args:
        state: Current workflow state containing email_id and user_id
        db: Database session for loading folder categories
        gmail_client: Gmail API client for email retrieval

    Returns:
        Updated state with populated email_content, sender, subject fields

    Raises:
        Exception: Any errors are captured in state["error_message"]
    """
    logger.info("node_extract_context_started", email_id=state["email_id"])

    try:
        # Load EmailProcessingQueue entry to get gmail_message_id
        result = await db.execute(
            select(EmailProcessingQueue).where(
                EmailProcessingQueue.id == int(state["email_id"]),
                EmailProcessingQueue.user_id == int(state["user_id"]),
            )
        )
        email = result.scalar_one_or_none()

        if not email:
            raise ValueError(
                f"Email {state['email_id']} not found for user {state['user_id']}"
            )

        # Load full email content from Gmail
        email_detail = await gmail_client.get_message_detail(
            message_id=email.gmail_message_id
        )

        # Update state with email content
        state["email_content"] = email_detail["body"]
        state["sender"] = email_detail["sender"]
        state["subject"] = email_detail["subject"]

        logger.info(
            "node_extract_context_completed",
            email_id=state["email_id"],
            sender=state["sender"],
            subject=state["subject"],
        )

    except Exception as e:
        logger.error(
            "node_extract_context_failed",
            email_id=state["email_id"],
            error=str(e),
        )
        state["error_message"] = f"Failed to extract email context: {str(e)}"

    return state


async def classify(
    state: EmailWorkflowState,
    db: AsyncSession,
    gmail_client: GmailClient,
    llm_client: LLMClient,
) -> EmailWorkflowState:
    """Node 2: Classify email using Gemini LLM.

    This node calls the EmailClassificationService to analyze the email
    and determine the appropriate folder for sorting.

    Actions:
        1. Initialize EmailClassificationService with dependencies
        2. Call classify_email() with email_id and user_id
        3. Parse ClassificationResponse from service
        4. Update state with classification results:
           - classification: "sort_only" (Epic 2 only handles sorting)
           - proposed_folder: AI-suggested folder name
           - classification_reasoning: AI reasoning (max 300 chars)
           - priority_score: 0-100 priority score
        5. Log classification completion

    Args:
        state: Current workflow state with email content from extract_context
        db: Database session for loading user folders
        gmail_client: Gmail API client (passed to classification service)
        llm_client: Gemini LLM client for AI classification

    Returns:
        Updated state with classification, proposed_folder, reasoning, priority_score

    Raises:
        Exception: Errors captured in state["error_message"], workflow continues
    """
    logger.info("node_classify_started", email_id=state["email_id"])

    try:
        # Initialize classification service with dependencies
        classification_service = EmailClassificationService(
            db=db,
            gmail_client=gmail_client,
            llm_client=llm_client,
        )

        # Call classification service
        classification_result = await classification_service.classify_email(
            email_id=int(state["email_id"]),
            user_id=int(state["user_id"]),
        )

        # Update state with classification results
        # Epic 2 only handles sorting (not response generation)
        state["classification"] = "sort_only"
        state["proposed_folder"] = classification_result.suggested_folder
        state["classification_reasoning"] = classification_result.reasoning
        state["priority_score"] = classification_result.priority_score

        # Look up proposed_folder_id for database FK
        if classification_result.suggested_folder:
            folder_result = await db.execute(
                select(FolderCategory).where(
                    FolderCategory.user_id == int(state["user_id"]),
                    FolderCategory.name == classification_result.suggested_folder,
                )
            )
            folder = folder_result.scalar_one_or_none()
            if folder:
                state["proposed_folder_id"] = folder.id
            else:
                logger.warning(
                    "proposed_folder_not_found",
                    email_id=state["email_id"],
                    proposed_folder=classification_result.suggested_folder,
                )

        # Persist classification results to EmailProcessingQueue for test verification
        from sqlalchemy import update

        stmt = (
            update(EmailProcessingQueue)
            .where(EmailProcessingQueue.id == int(state["email_id"]))
            .values(
                classification=state["classification"],
                proposed_folder_id=state.get("proposed_folder_id"),
                classification_reasoning=state["classification_reasoning"],
            )
        )
        await db.execute(stmt)
        await db.commit()

        logger.info(
            "node_classify_completed",
            email_id=state["email_id"],
            proposed_folder=state["proposed_folder"],
            proposed_folder_id=state.get("proposed_folder_id"),
            priority_score=state["priority_score"],
        )

    except Exception as e:
        logger.error(
            "node_classify_failed",
            email_id=state["email_id"],
            error=str(e),
        )
        state["error_message"] = f"Classification failed: {str(e)}"
        # Set fallback classification to allow workflow to continue
        state["classification"] = "sort_only"
        state["proposed_folder"] = "Unclassified"
        state["classification_reasoning"] = f"Classification failed: {str(e)}"
        state["priority_score"] = 50

    return state


async def detect_priority(
    state: EmailWorkflowState,
    db: AsyncSession,
) -> EmailWorkflowState:
    """Node 2.5: Detect if email is high-priority based on sender, keywords, user config.

    This node implements rule-based priority detection (Story 2.9):
    - Government domain senders: +50 points
    - Urgency keywords (multilingual): +30 points
    - User-configured priority senders: +40 points
    - Threshold: >= 70 triggers immediate notification

    Priority emails bypass batch processing and are sent to Telegram immediately.

    Actions:
        1. Run PriorityDetectionService.detect_priority()
        2. Update state with priority_score, is_priority, detection_reasons
        3. Update EmailProcessingQueue with priority flags for persistence

    Args:
        state: Current workflow state with email metadata (sender, subject, email_content)
        db: Database session for loading user config and updating EmailProcessingQueue

    Returns:
        Updated state with priority_score, is_priority, and detection_reasons populated

    Raises:
        Exception: Errors captured in state["error_message"], workflow continues with priority_score=0
    """
    logger.info("node_detect_priority_started", email_id=state["email_id"])

    try:
        # Import here to avoid circular imports
        from app.services.priority_detection import PriorityDetectionService
        from app.models.email import EmailProcessingQueue
        from sqlalchemy import update

        # Initialize service
        service = PriorityDetectionService(db)

        # Run priority detection (convert email_id to int for database query)
        result = await service.detect_priority(
            email_id=int(state["email_id"]),
            sender=state["sender"],
            subject=state["subject"],
            body_preview=state.get("email_content", "")[:200],
        )

        # Update state
        state["priority_score"] = result["priority_score"]
        state["is_priority"] = result["is_priority"]
        state["detection_reasons"] = result["detection_reasons"]

        # Persist priority flags to EmailProcessingQueue (AC #5)
        stmt = (
            update(EmailProcessingQueue)
            .where(EmailProcessingQueue.id == int(state["email_id"]))
            .values(
                priority_score=result["priority_score"],
                is_priority=result["is_priority"],
            )
        )
        await db.execute(stmt)
        await db.commit()

        logger.info(
            "node_detect_priority_completed",
            email_id=state["email_id"],
            priority_score=result["priority_score"],
            is_priority=result["is_priority"],
            detection_reasons=result["detection_reasons"],
        )

    except Exception as e:
        logger.error(
            "node_detect_priority_failed",
            email_id=state["email_id"],
            error=str(e),
        )
        state["error_message"] = f"Priority detection failed: {str(e)}"
        # Set fallback priority to allow workflow to continue
        state["priority_score"] = 0
        state["is_priority"] = False
        state["detection_reasons"] = []

    return state


async def send_telegram(
    state: EmailWorkflowState,
    db: AsyncSession,
    telegram_bot_client,
) -> EmailWorkflowState:
    """Node 3: Send Telegram approval request (with priority bypass for Story 2.8).

    This node implements priority email bypass logic (Story 2.8 AC #6):
    - Priority emails (priority_score >= 70): Send immediately via Telegram
    - Non-priority emails: Mark as awaiting_approval, skip Telegram send (sent in batch)

    Actions for priority emails:
        1. Load user's telegram_id from database
        2. Format email body preview (first 100 characters)
        3. Format Telegram message with ⚠️ priority indicator
        4. Create inline keyboard with approval buttons
        5. Send message via TelegramBotClient
        6. Update WorkflowMapping with telegram_message_id
        7. Store telegram_message_id in state for tracking

    Actions for non-priority emails:
        1. Update EmailProcessingQueue status to "awaiting_approval"
        2. Skip Telegram message sending (will be sent in batch via Story 2.8)

    Args:
        state: Current workflow state with classification results
        db: Database session for loading user and updating WorkflowMapping
        telegram_bot_client: TelegramBotClient instance for message sending

    Returns:
        Updated state with telegram_message_id (priority only) and body_preview populated

    Raises:
        Exception: Errors captured in state["error_message"], workflow continues
    """
    logger.info("node_send_telegram_started", email_id=state["email_id"])

    try:
        # Import here to avoid circular imports
        from app.models.user import User
        from app.models.workflow_mapping import WorkflowMapping
        from app.services.telegram_message_formatter import (
            format_sorting_proposal_message,
            create_inline_keyboard,
        )

        # Check if email is priority (Story 2.8 AC #6)
        is_priority = state.get("priority_score", 0) >= 70
        state["is_priority"] = is_priority

        if is_priority:
            # PRIORITY EMAIL: Send immediately (bypass batch)
            logger.info("priority_email_detected", email_id=state["email_id"], priority_score=state.get("priority_score"))

            # Step 1: Load user to get telegram_id
            result = await db.execute(
                select(User).where(User.id == int(state["user_id"]))
            )
            user = result.scalar_one_or_none()

            if not user or not user.telegram_id:
                raise ValueError(f"User {state['user_id']} has no Telegram account linked")

            # Step 2: Create body preview (first 100 characters)
            body_preview = state["email_content"][:100] if state.get("email_content") else ""
            state["body_preview"] = body_preview

            # Step 3: Format Telegram message with priority indicator
            message_text = format_sorting_proposal_message(
                sender=state["sender"],
                subject=state["subject"],
                body_preview=body_preview,
                proposed_folder=state.get("proposed_folder", "Unclassified"),
                reasoning=state.get("classification_reasoning", "No reasoning provided"),
                is_priority=True,  # Include ⚠️ priority indicator
            )

            # Step 4: Create inline keyboard buttons
            buttons = create_inline_keyboard(email_id=int(state["email_id"]))

            # Step 5: Send message via TelegramBotClient
            telegram_message_id = await telegram_bot_client.send_message_with_buttons(
                telegram_id=user.telegram_id,
                text=message_text,
                buttons=buttons,
            )

            # Step 6: Update WorkflowMapping with telegram_message_id
            result = await db.execute(
                select(WorkflowMapping).where(
                    WorkflowMapping.thread_id == state["thread_id"]
                )
            )
            workflow_mapping = result.scalar_one_or_none()

            if workflow_mapping:
                workflow_mapping.telegram_message_id = telegram_message_id
                workflow_mapping.workflow_state = "awaiting_approval"
                await db.commit()
                logger.debug(
                    "workflow_mapping_updated",
                    thread_id=state["thread_id"],
                    telegram_message_id=telegram_message_id,
                )
            else:
                logger.warning(
                    "workflow_mapping_not_found",
                    thread_id=state["thread_id"],
                    note="WorkflowMapping should have been created during workflow initialization",
                )

            # Step 7: Store telegram_message_id in state
            state["telegram_message_id"] = telegram_message_id

            # Step 8: Update EmailProcessingQueue status to awaiting_approval
            result = await db.execute(
                select(EmailProcessingQueue).where(
                    EmailProcessingQueue.id == int(state["email_id"])
                )
            )
            email = result.scalar_one_or_none()

            if email:
                email.status = "awaiting_approval"
                await db.commit()

            logger.info(
                "priority_email_sent_immediate",
                email_id=state["email_id"],
                telegram_message_id=telegram_message_id,
                priority_score=state.get("priority_score", 0),
            )

        else:
            # NON-PRIORITY EMAIL: Mark for batch, skip Telegram send (Story 2.8 AC #6)
            logger.info("non_priority_email_detected", email_id=state["email_id"], priority_score=state.get("priority_score"))

            # Update EmailProcessingQueue status to awaiting_approval
            result = await db.execute(
                select(EmailProcessingQueue).where(
                    EmailProcessingQueue.id == int(state["email_id"])
                )
            )
            email = result.scalar_one_or_none()

            if email:
                email.status = "awaiting_approval"
                email.is_priority = False
                await db.commit()

                logger.info(
                    "email_marked_for_batch",
                    email_id=state["email_id"],
                    priority_score=state.get("priority_score", 0),
                    note="Email will be sent in batch notification (Story 2.8)"
                )
            else:
                logger.warning(
                    "email_not_found_for_batch_marking",
                    email_id=state["email_id"]
                )

            # Create body preview for consistency
            body_preview = state["email_content"][:100] if state.get("email_content") else ""
            state["body_preview"] = body_preview

    except Exception as e:
        logger.error(
            "node_send_telegram_failed",
            email_id=state["email_id"],
            error=str(e),
            error_type=type(e).__name__,
        )
        state["error_message"] = f"Failed to send Telegram message: {str(e)}"

    return state


async def await_approval(state: EmailWorkflowState) -> EmailWorkflowState:
    """Node 4: Pause workflow for user approval.

    This node is the critical pause point in the workflow. It returns the state
    unchanged, allowing LangGraph's checkpointer to save the current state to
    PostgreSQL. The workflow will remain paused until Story 2.7 implements the
    Telegram callback handler to resume execution.

    Workflow Pause Mechanism:
        1. This node returns state without adding edges to next nodes
        2. LangGraph checkpointer automatically saves state to PostgreSQL
        3. Workflow instance becomes "awaiting approval" status
        4. User receives Telegram message (Story 2.6)
        5. User clicks button hours/days later
        6. Telegram callback handler resumes workflow from thread_id (Story 2.7)

    Args:
        state: Current workflow state with classification and Telegram message sent

    Returns:
        State unchanged - workflow pauses at this point

    Note:
        This node does NOT add edges to subsequent nodes. The workflow will
        resume from this checkpoint when Story 2.7's callback handler invokes
        workflow.ainvoke() with the saved thread_id.
    """
    logger.info(
        "node_await_approval_pause",
        email_id=state["email_id"],
        thread_id=state["thread_id"],
        note="Workflow paused - awaiting user decision from Telegram",
    )

    # Workflow pauses here - no further nodes executed
    # State persisted to PostgreSQL via checkpointer
    # Resumption handled in Story 2.7 via Telegram callback

    return state


async def execute_action(
    state: EmailWorkflowState,
    db: Session,
    gmail_client: GmailClient,
) -> EmailWorkflowState:
    """Node 5: Execute approved action (Story 2.7).

    This node applies the user's decision after approval:
    - If approved: Apply proposed folder label to email in Gmail
    - If change_folder: Apply selected_folder label to email in Gmail
    - If rejected: Update status to "rejected", no Gmail API call

    Args:
        state: Current workflow state with user_decision from Telegram callback
        db: Database session for querying folders and updating email status
        gmail_client: Gmail API client for applying labels

    Returns:
        State with final_action populated
    """
    email_id = state["email_id"]
    user_decision = state.get("user_decision")

    logger.info(
        "node_execute_action_start",
        email_id=email_id,
        user_decision=user_decision,
    )

    # Get email from database
    email = await db.get(EmailProcessingQueue, int(email_id))
    if not email:
        error_msg = f"Email {email_id} not found in database"
        logger.error("execute_action_email_not_found", email_id=email_id)
        state["error_message"] = error_msg
        return state

    # Handle user decision
    if user_decision == "approve":
        # Apply proposed folder label (AC #2)
        folder_id = state.get("proposed_folder_id")
        if not folder_id:
            error_msg = "No proposed_folder_id in state for approve action"
            logger.error("execute_action_no_proposed_folder", email_id=email_id)
            state["error_message"] = error_msg
            return state

        folder = await db.get(FolderCategory, folder_id)
        if not folder:
            error_msg = f"Folder {folder_id} not found"
            logger.error("execute_action_folder_not_found", folder_id=folder_id)
            state["error_message"] = error_msg
            return state

        # Apply Gmail label with comprehensive error handling (Story 2.11 - AC #4, #5)
        try:
            success = await gmail_client.apply_label(
                message_id=email.gmail_message_id,
                label_id=folder.gmail_label_id,
            )

            if not success:
                error_msg = "Gmail API returned False for label application"
                logger.error(
                    "execute_action_gmail_apply_failed",
                    email_id=email_id,
                    message_id=email.gmail_message_id,
                    label_id=folder.gmail_label_id,
                )
                state["error_message"] = error_msg
                return state

            # Update email status to completed (AC #2)
            email.status = "completed"
            db.add(email)

            # Record approval decision to history (Story 2.10)
            try:
                approval_service = ApprovalHistoryService(db)
                await approval_service.record_decision(
                    user_id=email.user_id,
                    email_queue_id=email.id,
                    action_type="approve",
                    ai_suggested_folder_id=folder_id,
                    user_selected_folder_id=folder_id,
                )
                logger.info(
                    "approval_history_recorded",
                    email_id=email_id,
                    action_type="approve",
                )
            except Exception as history_error:
                # Log error but don't block workflow
                logger.error(
                    "approval_history_recording_failed",
                    email_id=email_id,
                    action_type="approve",
                    error=str(history_error),
                    error_type=type(history_error).__name__,
                )

            await db.commit()

            state["final_action"] = "approved"

            logger.info(
                "execute_action_approved",
                email_id=email_id,
                folder_name=folder.name,
                gmail_message_id=email.gmail_message_id,
            )

        except Exception as e:
            # Persistent failure after all retries exhausted (Story 2.11 - AC #4, #5, Task 8, Task 9)
            from datetime import datetime, UTC
            from app.core.metrics import (
                email_processing_errors_total,
                email_dlq_total,
                email_retry_count_histogram,
                emails_in_error_state,
            )

            error_type = "gmail_api_failure"
            error_msg = str(e)

            # Update email status to "error" (AC #4)
            email.status = "error"
            email.error_type = error_type
            email.error_message = error_msg
            email.error_timestamp = datetime.now(UTC)
            email.retry_count = 3  # MAX_RETRIES from RetryConfig

            # Populate DLQ reason for Dead Letter Queue tracking (Task 8)
            email.dlq_reason = format_dlq_reason(
                action="apply Gmail label",
                retry_count=email.retry_count,
                error_type=error_type,
                error_msg=error_msg,
                email_id=email.id,
                gmail_message_id=email.gmail_message_id,
                folder_name=folder.name,
                label_id=folder.gmail_label_id,
            )

            db.add(email)
            await db.commit()

            # Record Prometheus metrics (Task 9)
            email_processing_errors_total.labels(
                error_type=error_type,
                user_id=str(email.user_id)
            ).inc()

            email_dlq_total.labels(
                error_type=error_type,
                user_id=str(email.user_id)
            ).inc()

            email_retry_count_histogram.observe(email.retry_count)

            emails_in_error_state.labels(error_type=error_type).inc()

            # Log structured error (AC #1)
            logger.error(
                "workflow_node_error",
                email_id=email_id,
                user_id=email.user_id,
                node="execute_action",
                error_type=error_type,
                error_message=error_msg,
                retry_count=3,
                exc_info=True,
            )

            # Send error notification to user via Telegram (AC #5)
            try:
                from app.core.telegram_bot import TelegramBotClient

                # Get user's telegram_id from database
                from app.models.user import User
                user = await db.get(User, email.user_id)

                if user and user.telegram_id:
                    telegram_bot = TelegramBotClient()
                    await telegram_bot.initialize()

                    # Format error notification message
                    notification_text = f"""⚠️ Email Processing Error

Email from: {email.sender}
Subject: {email.subject or '(no subject)'}

Error: {error_type}

This email could not be processed automatically. Use /retry {email.id} to try again manually."""

                    await telegram_bot.send_message(
                        telegram_id=user.telegram_id,
                        text=notification_text,
                        user_id=user.id,
                    )

                    logger.info(
                        "error_notification_sent",
                        email_id=email_id,
                        user_id=email.user_id,
                        telegram_id=user.telegram_id,
                    )
            except Exception as notification_error:
                # Log but don't fail workflow if notification fails
                logger.error(
                    "error_notification_failed",
                    email_id=email_id,
                    user_id=email.user_id,
                    error=str(notification_error),
                    error_type=type(notification_error).__name__,
                )

            state["error_message"] = error_msg
            state["final_action"] = "error"
            return state

    elif user_decision == "reject":
        # Update status to rejected, no Gmail API call (AC #3)
        email.status = "rejected"
        db.add(email)

        # Record rejection decision to history (Story 2.10)
        try:
            approval_service = ApprovalHistoryService(db)
            await approval_service.record_decision(
                user_id=email.user_id,
                email_queue_id=email.id,
                action_type="reject",
                ai_suggested_folder_id=state.get("proposed_folder_id"),
                user_selected_folder_id=None,
            )
            logger.info(
                "approval_history_recorded",
                email_id=email_id,
                action_type="reject",
            )
        except Exception as history_error:
            # Log error but don't block workflow
            logger.error(
                "approval_history_recording_failed",
                email_id=email_id,
                action_type="reject",
                error=str(history_error),
                error_type=type(history_error).__name__,
            )

        await db.commit()

        state["final_action"] = "rejected"

        logger.info(
            "execute_action_rejected",
            email_id=email_id,
        )

    elif user_decision == "change_folder":
        # Apply selected folder label instead of proposed (AC #5)
        folder_id = state.get("selected_folder_id")
        if not folder_id:
            error_msg = "No selected_folder_id in state for change_folder action"
            logger.error("execute_action_no_selected_folder", email_id=email_id)
            state["error_message"] = error_msg
            return state

        folder = await db.get(FolderCategory, folder_id)
        if not folder:
            error_msg = f"Selected folder {folder_id} not found"
            logger.error("execute_action_selected_folder_not_found", folder_id=folder_id)
            state["error_message"] = error_msg
            return state

        # Apply Gmail label (AC #9 - Error handling)
        try:
            success = await gmail_client.apply_label(
                message_id=email.gmail_message_id,
                label_id=folder.gmail_label_id,
            )

            if not success:
                error_msg = "Gmail API returned False for label application"
                logger.error(
                    "execute_action_gmail_apply_failed",
                    email_id=email_id,
                    message_id=email.gmail_message_id,
                    label_id=folder.gmail_label_id,
                )
                state["error_message"] = error_msg
                return state

            # Update email status to completed with selected folder
            email.status = "completed"
            db.add(email)

            # Record folder change decision to history (Story 2.10)
            try:
                approval_service = ApprovalHistoryService(db)
                await approval_service.record_decision(
                    user_id=email.user_id,
                    email_queue_id=email.id,
                    action_type="change_folder",
                    ai_suggested_folder_id=state.get("proposed_folder_id"),
                    user_selected_folder_id=folder_id,
                )
                logger.info(
                    "approval_history_recorded",
                    email_id=email_id,
                    action_type="change_folder",
                )
            except Exception as history_error:
                # Log error but don't block workflow
                logger.error(
                    "approval_history_recording_failed",
                    email_id=email_id,
                    action_type="change_folder",
                    error=str(history_error),
                    error_type=type(history_error).__name__,
                )

            await db.commit()

            state["final_action"] = "changed"

            logger.info(
                "execute_action_folder_changed",
                email_id=email_id,
                selected_folder_name=folder.name,
                gmail_message_id=email.gmail_message_id,
            )

        except Exception as e:
            # Persistent failure after all retries exhausted (Story 2.11 - Task 8, Task 9)
            from datetime import datetime, UTC
            from app.core.metrics import (
                email_processing_errors_total,
                email_dlq_total,
                email_retry_count_histogram,
                emails_in_error_state,
            )

            error_type = "gmail_api_failure"
            error_msg = str(e)

            # Update email status to "error" with DLQ tracking
            email.status = "error"
            email.error_type = error_type
            email.error_message = error_msg
            email.error_timestamp = datetime.now(UTC)
            email.retry_count = 3  # MAX_RETRIES from RetryConfig

            # Populate DLQ reason for Dead Letter Queue tracking (Task 8)
            email.dlq_reason = format_dlq_reason(
                action="apply Gmail label (change_folder action)",
                retry_count=email.retry_count,
                error_type=error_type,
                error_msg=error_msg,
                email_id=email.id,
                gmail_message_id=email.gmail_message_id,
                folder_name=folder.name,
                label_id=folder.gmail_label_id,
            )

            db.add(email)
            await db.commit()

            # Record Prometheus metrics (Task 9)
            email_processing_errors_total.labels(
                error_type=error_type,
                user_id=str(email.user_id)
            ).inc()

            email_dlq_total.labels(
                error_type=error_type,
                user_id=str(email.user_id)
            ).inc()

            email_retry_count_histogram.observe(email.retry_count)

            emails_in_error_state.labels(error_type=error_type).inc()

            logger.error(
                "execute_action_gmail_error",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
                dlq_reason=email.dlq_reason,
                exc_info=True,
            )

            # Send error notification to user
            try:
                from app.core.telegram_bot import TelegramBotClient
                from app.models.user import User

                user = await db.get(User, email.user_id)
                if user and user.telegram_id:
                    telegram_bot = TelegramBotClient()
                    await telegram_bot.initialize()

                    notification_text = f"""⚠️ Email Processing Error

Email from: {email.sender}
Subject: {email.subject or '(no subject)'}

Error: {error_type}

This email could not be processed automatically. Use /retry {email.id} to try again manually."""

                    await telegram_bot.send_message(
                        telegram_id=user.telegram_id,
                        text=notification_text,
                        user_id=user.id,
                    )

                    logger.info(
                        "error_notification_sent",
                        email_id=email_id,
                        user_id=email.user_id,
                        telegram_id=user.telegram_id,
                    )
            except Exception as notification_error:
                logger.error(
                    "error_notification_failed",
                    email_id=email_id,
                    user_id=email.user_id,
                    error=str(notification_error),
                    error_type=type(notification_error).__name__,
                )

            state["error_message"] = error_msg
            state["final_action"] = "error"
            return state

    else:
        error_msg = f"Unknown user_decision: {user_decision}"
        logger.error("execute_action_unknown_decision", user_decision=user_decision)
        state["error_message"] = error_msg
        return state

    return state


async def send_confirmation(
    state: EmailWorkflowState,
    db: Session,
    telegram_bot_client: TelegramBotClient,
) -> EmailWorkflowState:
    """Node 6: Send Telegram confirmation (Story 2.7).

    This node sends a confirmation message to the user after action execution:
    - Edits original Telegram message with confirmation result
    - Confirms email was sorted to the selected folder
    - Shows rejection confirmation if user rejected the suggestion

    Args:
        state: Current workflow state with final_action from execute_action
        db: Database session for querying user and folder information
        telegram_bot_client: Telegram bot for editing messages

    Returns:
        State unchanged
    """
    email_id = state["email_id"]
    final_action = state.get("final_action")
    error_message = state.get("error_message")

    logger.info(
        "node_send_confirmation_start",
        email_id=email_id,
        final_action=final_action,
        has_error=bool(error_message),
    )

    # Get user for Telegram ID
    user_id = state.get("user_id")
    if not user_id:
        logger.error("send_confirmation_no_user_id", email_id=email_id)
        return state

    user = await db.get(User, int(user_id))
    if not user or not user.telegram_id:
        logger.error(
            "send_confirmation_user_not_found",
            user_id=user_id,
            email_id=email_id,
        )
        return state

    # Get original telegram_message_id for editing
    telegram_message_id = state.get("telegram_message_id")
    if not telegram_message_id:
        logger.error(
            "send_confirmation_no_message_id",
            email_id=email_id,
            user_id=user_id,
        )
        return state

    # Get original message text to append confirmation to
    # (We'll reconstruct a summary since we don't have full original text in state)
    subject = state.get("subject", "Email")
    sender = state.get("sender", "Unknown sender")

    # Format confirmation message based on final_action (AC #6)
    if error_message:
        # Error occurred during execution
        confirmation_text = f"⚠️ *Error:* {error_message}"
        logger.warning(
            "send_confirmation_with_error",
            email_id=email_id,
            error_message=error_message,
        )

    elif final_action == "approved":
        # User approved the proposed folder (AC #2, #6)
        folder_id = state.get("proposed_folder_id")
        if folder_id:
            folder = await db.get(FolderCategory, folder_id)
            folder_name = folder.name if folder else "Unknown Folder"
        else:
            folder_name = state.get("proposed_folder", "Unknown Folder")

        confirmation_text = f"✅ *Email sorted to \"{folder_name}\"*"

        logger.info(
            "send_confirmation_approved",
            email_id=email_id,
            folder_name=folder_name,
        )

    elif final_action == "rejected":
        # User rejected the suggestion (AC #3, #6)
        confirmation_text = "❌ *Email sorting rejected.* Email remains in inbox."

        logger.info(
            "send_confirmation_rejected",
            email_id=email_id,
        )

    elif final_action == "changed":
        # User selected a different folder (AC #5, #6)
        folder_id = state.get("selected_folder_id")
        if folder_id:
            folder = await db.get(FolderCategory, folder_id)
            folder_name = folder.name if folder else "Unknown Folder"
        else:
            folder_name = state.get("selected_folder", "Unknown Folder")

        confirmation_text = f"✅ *Email sorted to \"{folder_name}\"*"

        logger.info(
            "send_confirmation_folder_changed",
            email_id=email_id,
            folder_name=folder_name,
        )

    else:
        # Unknown final_action
        confirmation_text = "✅ *Action completed*"
        logger.warning(
            "send_confirmation_unknown_action",
            email_id=email_id,
            final_action=final_action,
        )

    # Build full message with original proposal info + confirmation
    full_message = (
        f"📧 *New Email*\n\n"
        f"*From:* {sender}\n"
        f"*Subject:* {subject}\n\n"
        f"{confirmation_text}"
    )

    # Edit original message with confirmation
    try:
        await telegram_bot_client.edit_message_text(
            telegram_id=user.telegram_id,
            message_id=telegram_message_id,
            text=full_message,
        )

        logger.info(
            "send_confirmation_message_edited",
            email_id=email_id,
            telegram_id=user.telegram_id,
            telegram_message_id=telegram_message_id,
        )

    except Exception as e:
        logger.error(
            "send_confirmation_edit_failed",
            email_id=email_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Don't set error_message in state - confirmation failure is not critical

    return state
