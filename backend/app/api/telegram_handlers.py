"""Telegram bot command and callback handlers.

This module contains handlers for:
- Bot commands: /start, /help, /test
- Callback queries: Inline button interactions for email approval workflow
"""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from functools import partial
import os

from app.api.deps import AsyncSessionLocal, engine
from app.core.gmail_client import GmailClient
from app.core.llm_client import LLMClient
from app.core.telegram_bot import TelegramBotClient
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User
from app.models.workflow_mapping import WorkflowMapping
from app.services.telegram_linking import link_telegram_account, link_telegram_account_async
from app.workflows import nodes
from app.workflows.email_workflow import create_email_workflow

logger = structlog.get_logger(__name__)


from contextlib import asynccontextmanager

@asynccontextmanager
async def create_workflow_for_resumption(db: AsyncSession, gmail_client: GmailClient, telegram_bot: TelegramBotClient):
    """Async context manager for creating workflow with checkpointer for callback resumption.

    This helper builds a workflow instance with proper dependency injection and
    AsyncPostgresSaver checkpointer within an async context manager.

    Args:
        db: AsyncSession database session
        gmail_client: Gmail API client for the user
        telegram_bot: Telegram bot client

    Yields:
        Compiled workflow ready for resumption via ainvoke()
    """
    # Get database URL for checkpointer
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgresql+psycopg://"):
        checkpoint_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    else:
        checkpoint_url = database_url

    async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
        # Setup checkpoint tables if not exists (idempotent)
        await checkpointer.setup()

        # Create db_factory context manager that yields the existing session
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def db_factory():
            """Context manager factory that yields the existing session."""
            yield db

        # Use create_email_workflow to ensure consistent workflow structure
        # This ensures all routing logic (including Story 3.9 draft approval) is applied
        llm_client = LLMClient()

        # Create workflow using centralized factory function
        # This ensures we use the same workflow graph for both initial creation and resumption
        workflow_app = create_email_workflow(
            checkpointer=checkpointer,
            db_session_factory=db_factory,
            gmail_client=gmail_client,
            llm_client=llm_client,
            telegram_client=telegram_bot,
        )

        yield workflow_app


async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command.

    Sends welcome message with account linking instructions.
    If a linking code is provided (e.g., /start A3B7X9), notes it for future implementation.

    Args:
        update: Telegram Update object containing message and user info
        context: Bot context with args and bot instance
    """
    telegram_id = update.effective_user.id
    username = update.effective_user.username or "User"

    logger.info(
        "telegram_command_received",
        command="/start",
        telegram_id=telegram_id,
        username=username,
    )

    # Check if linking code was provided (e.g., /start A3B7X9)
    if context.args and len(context.args) > 0:
        code = context.args[0].upper()  # Case-insensitive
        telegram_id_str = str(telegram_id)
        telegram_username = update.effective_user.username

        logger.info(
            "telegram_linking_attempt",
            telegram_id=telegram_id_str,
            code=code,
            username=telegram_username,
        )

        # Validate and link account using async database session (Story 5-2)
        async with AsyncSessionLocal() as db:
            result = await link_telegram_account_async(
                telegram_id=telegram_id_str,
                telegram_username=telegram_username,
                code=code,
                db=db
            )

        # Send result message to user
        if result["success"]:
            await update.message.reply_text(result["message"])
        else:
            await update.message.reply_text(f"❌ {result['error']}")

        return

    # Send welcome message
    welcome_message = (
        f"Welcome to *Mail Agent Bot!* 👋\n\n"
        f"Hi {username}, I'm here to help you manage your emails with AI-powered sorting.\n\n"
        "📱 *To link your account:*\n"
        "1. Log in to the Mail Agent web app\n"
        "2. Go to Settings → Telegram Connection\n"
        "3. Generate a linking code\n"
        "4. Send: `/start [your-code]`\n\n"
        "❓ Need help? Send /help"
    )

    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def handle_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command.

    Displays list of available commands and usage instructions.

    Args:
        update: Telegram Update object containing message and user info
        context: Bot context with args and bot instance
    """
    telegram_id = update.effective_user.id

    logger.info(
        "telegram_command_received",
        command="/help",
        telegram_id=telegram_id,
    )

    help_message = (
        "📚 *Mail Agent Bot - Commands*\n\n"
        "*Available Commands:*\n"
        "/start - Link your Telegram account\n"
        "/help - Show this help message\n"
        "/test - Send a test message (for testing only)\n\n"
        "*What I can do:*\n"
        "• Send you email sorting proposals\n"
        "• Let you approve or reject AI suggestions\n"
        "• Help you organize your inbox efficiently\n\n"
        "🔗 *Need more help?*\n"
        "Visit the documentation or contact support through the web app."
    )

    await update.message.reply_text(help_message, parse_mode="Markdown")


async def handle_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /test command.

    Sends test confirmation message with user's Telegram ID.
    Useful for verifying bot connectivity and getting Telegram ID.

    Args:
        update: Telegram Update object containing message and user info
        context: Bot context with args and bot instance
    """
    telegram_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"

    logger.info(
        "telegram_command_received",
        command="/test",
        telegram_id=telegram_id,
    )

    test_message = (
        "✅ *Test successful!*\n\n"
        f"*Your Telegram ID:* `{telegram_id}`\n"
        f"*Username:* @{username}\n\n"
        "The bot is working correctly. You can receive messages from Mail Agent."
    )

    await update.message.reply_text(test_message, parse_mode="Markdown")


async def handle_retry_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /retry command for manual email retry (Story 2.11 - AC #6).

    Command format: /retry {email_id}

    Allows users to manually retry failed emails that are in "error" status.
    Validates ownership, resets status to pending, and re-triggers workflow.

    Args:
        update: Telegram Update object containing message and user info
        context: Bot context with args containing email_id

    Example:
        /retry 123  # Retry email with ID 123
    """
    telegram_id = str(update.effective_user.id)

    logger.info(
        "telegram_command_received",
        command="/retry",
        telegram_id=telegram_id,
        args=context.args,
    )

    # Validate command format
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Usage: `/retry {email_id}`\n\n"
            "Example: `/retry 123`\n\n"
            "You can find email IDs in error notifications.",
            parse_mode="Markdown"
        )
        return

    # Parse email_id
    try:
        email_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            f"❌ Invalid email ID: '{context.args[0]}'\n\n"
            "Email ID must be a number.",
            parse_mode="Markdown"
        )
        return

    # Process retry in database session
    async with AsyncSessionLocal() as db:
        try:
            # Find user by telegram_id
            result = await db.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()

            if not user:
                await update.message.reply_text(
                    "❌ Your Telegram account is not linked.\n\n"
                    "Use /start to link your account first.",
                    parse_mode="Markdown"
                )
                return

            # Load email from database
            result = await db.execute(select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id))
            email = result.scalar_one_or_none()

            if not email:
                await update.message.reply_text(
                    f"❌ Email #{email_id} not found.",
                    parse_mode="Markdown"
                )
                logger.warning(
                    "retry_command_email_not_found",
                    email_id=email_id,
                    telegram_id=telegram_id,
                    user_id=user.id,
                )
                return

            # Security check: User owns the email
            if email.user_id != user.id:
                await update.message.reply_text(
                    f"❌ You don't have permission to retry email #{email_id}.",
                    parse_mode="Markdown"
                )
                logger.warning(
                    "retry_command_unauthorized",
                    email_id=email_id,
                    telegram_id=telegram_id,
                    user_id=user.id,
                    email_owner_id=email.user_id,
                )
                return

            # Validate email is in error status
            if email.status != "error":
                await update.message.reply_text(
                    f"❌ Email #{email_id} is not in error state.\n\n"
                    f"Current status: {email.status}\n\n"
                    "Only failed emails can be retried.",
                    parse_mode="Markdown"
                )
                logger.info(
                    "retry_command_invalid_status",
                    email_id=email_id,
                    current_status=email.status,
                    user_id=user.id,
                )
                return

            # Reset email to pending status (Story 2.11 - AC #6, Task 8)
            previous_error_type = email.error_type
            email.status = "pending"
            email.error_type = None
            email.error_message = None
            email.error_timestamp = None
            email.retry_count = 0
            email.dlq_reason = None  # Clear DLQ reason on manual retry (Task 8)

            await db.commit()

            logger.info(
                "manual_retry_triggered",
                user_id=user.id,
                email_id=email_id,
                previous_error_type=previous_error_type,
                retry_timestamp=str(update.message.date),
            )

            # Re-trigger workflow
            try:
                from app.workflows.email_workflow import create_email_workflow

                # Create Gmail client for user
                gmail_client = GmailClient(user_id=user.id)

                # Create Telegram bot client
                telegram_bot = TelegramBotClient()
                await telegram_bot.initialize()

                # Create workflow
                workflow = create_email_workflow(
                    db=db,
                    gmail_client=gmail_client,
                    telegram_bot_client=telegram_bot,
                )

                # Generate new thread_id for workflow
                import uuid
                thread_id = str(uuid.uuid4())

                # Trigger workflow from beginning
                await workflow.ainvoke(
                    {"email_id": str(email_id)},
                    config={"configurable": {"thread_id": thread_id}}
                )

                logger.info(
                    "workflow_retriggered",
                    email_id=email_id,
                    user_id=user.id,
                    thread_id=thread_id,
                )

            except Exception as workflow_error:
                logger.error(
                    "workflow_retrigger_failed",
                    email_id=email_id,
                    user_id=user.id,
                    error=str(workflow_error),
                    error_type=type(workflow_error).__name__,
                    exc_info=True,
                )
                # Don't fail - status already reset, workflow will be picked up by polling

            # Send confirmation
            await update.message.reply_text(
                f"✅ Retrying email from *{email.sender}*\n\n"
                f"Subject: {email.subject or '(no subject)'}\n\n"
                "You'll receive a new proposal shortly.",
                parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(
                "retry_command_failed",
                email_id=email_id,
                telegram_id=telegram_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            await update.message.reply_text(
                "❌ Failed to retry email. Please try again later.",
                parse_mode="Markdown"
            )


# ============================================================================
# Callback Query Handlers (Story 2.7: Approval Button Handling)
# ============================================================================


def parse_callback_data(callback_data: str) -> tuple[str, int | None, int | None]:
    """Parse callback data from Telegram inline button.

    Callback data format:
    - Primary actions: {action}_{email_id} (e.g., "approve_123")
    - Folder selection: folder_{folder_id}_{email_id} (e.g., "folder_5_123")
    - Response actions: {action}_response_{email_id} (e.g., "send_response_123") - Story 3.9

    Args:
        callback_data: Raw callback data string from Telegram button

    Returns:
        Tuple of (action, email_id, folder_id):
        - action: "approve", "reject", "change", "folder", "send_response", "edit_response", "reject_response"
        - email_id: Email ID from callback data (int)
        - folder_id: Folder ID for folder selection, None otherwise

    Raises:
        ValueError: If callback_data format is invalid
    """
    parts = callback_data.split("_")

    if len(parts) < 2:
        raise ValueError(f"Invalid callback data format: '{callback_data}' (expected at least 2 parts)")

    # Handle response actions: send_response_{email_id}, edit_response_{email_id}, reject_response_{email_id} (Story 3.9)
    if len(parts) == 3 and parts[1] == "response":
        action = f"{parts[0]}_response"  # send_response, edit_response, reject_response
        try:
            email_id = int(parts[2])
            return action, email_id, None
        except ValueError as e:
            raise ValueError(f"Invalid email_id in response callback: '{callback_data}'") from e

    action = parts[0]

    # Handle folder selection: folder_{folder_id}_{email_id}
    if action == "folder":
        if len(parts) != 3:
            raise ValueError(f"Invalid folder callback format: '{callback_data}' (expected 3 parts)")
        try:
            folder_id = int(parts[1])
            email_id = int(parts[2])
            return action, email_id, folder_id
        except ValueError as e:
            raise ValueError(f"Invalid folder callback IDs: '{callback_data}'") from e

    # Handle primary actions: {action}_{email_id}
    if action in ("approve", "reject", "change"):
        try:
            email_id = int(parts[1])
            return action, email_id, None
        except ValueError as e:
            raise ValueError(f"Invalid email_id in callback: '{callback_data}'") from e

    raise ValueError(f"Unknown action in callback data: '{action}'")


async def validate_user_owns_email(telegram_user_id: int, email_id: int, db: AsyncSession) -> bool:
    """Verify that telegram_user_id owns the email being processed.

    Security validation to prevent unauthorized users from processing
    emails that don't belong to them.

    Args:
        telegram_user_id: Telegram user ID from callback query
        email_id: Email ID from callback data
        db: Async database session

    Returns:
        True if user owns the email, False otherwise
    """
    # Get user by telegram_id
    result = await db.execute(
        select(User).where(User.telegram_id == str(telegram_user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(
            "callback_validation_user_not_found",
            telegram_user_id=telegram_user_id,
        )
        return False

    # Get email and check ownership
    result = await db.execute(
        select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
    )
    email = result.scalar_one_or_none()

    if not email:
        logger.warning(
            "callback_validation_email_not_found",
            email_id=email_id,
            telegram_user_id=telegram_user_id,
        )
        return False

    if email.user_id != user.id:
        logger.warning(
            "callback_validation_ownership_mismatch",
            email_id=email_id,
            telegram_user_id=telegram_user_id,
            email_user_id=email.user_id,
            telegram_user_id_db=user.id,
        )
        return False

    return True


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callback queries from Telegram.

    Routes callback queries to appropriate handlers based on action:
    - approve_{email_id}: Resume workflow with approval
    - reject_{email_id}: Resume workflow with rejection
    - change_{email_id}: Show folder selection menu
    - folder_{folder_id}_{email_id}: Apply selected folder

    Args:
        update: Telegram Update object containing callback query
        context: Bot context

    Security:
        - Validates user owns the email before processing (AC #8)
        - Logs all callback interactions for audit trail
    """
    query = update.callback_query
    telegram_user_id = query.from_user.id
    callback_data = query.data

    logger.info(
        "callback_query_received",
        telegram_user_id=telegram_user_id,
        callback_data=callback_data,
    )

    # Parse callback data
    try:
        action, email_id, folder_id = parse_callback_data(callback_data)
    except ValueError as e:
        logger.error(
            "callback_data_parse_failed",
            callback_data=callback_data,
            error=str(e),
        )
        await query.answer("❌ Invalid button data", show_alert=True)
        return

    # Validate user owns the email (AC #8)
    async with AsyncSessionLocal() as db:
        if not await validate_user_owns_email(telegram_user_id, email_id, db):
            logger.warning(
                "callback_unauthorized",
                telegram_user_id=telegram_user_id,
                email_id=email_id,
                action=action,
            )
            await query.answer("❌ Unauthorized", show_alert=True)
            return

        # Route to appropriate handler
        if action == "approve":
            await handle_approve(query, email_id, db)
        elif action == "reject":
            await handle_reject(query, email_id, db)
        elif action == "change":
            await handle_change_folder(query, email_id, db)
        elif action == "folder":
            await handle_folder_selection(query, email_id, folder_id, db)
        # Story 3.9: Response editing and sending handlers
        elif action == "send_response":
            await handle_send_response(update, context, email_id, db)
        elif action == "edit_response":
            await handle_edit_response(update, context, email_id, db)
        elif action == "reject_response":
            await handle_reject_response(update, context, email_id, db)


async def handle_approve(query, email_id: int, db: AsyncSession):
    """Handle Approve button click (AC #2, #6, #9).

    Resumes LangGraph workflow with user_decision="approve", which triggers:
    - execute_action node: Apply proposed folder label to Gmail
    - send_confirmation node: Edit original message with confirmation

    Args:
        query: Telegram CallbackQuery object
        email_id: Email ID from callback data
        db: AsyncSession database session
    """
    await query.answer()

    logger.info(
        "callback_approve_processing",
        email_id=email_id,
        telegram_user_id=query.from_user.id,
    )

    # Get WorkflowMapping and Email to find thread_id and user
    result = await db.execute(
        select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
    )
    workflow_mapping = result.scalars().first()

    if not workflow_mapping:
        logger.error(
            "callback_workflow_mapping_not_found",
            email_id=email_id,
        )
        await query.answer("❌ Workflow not found", show_alert=True)
        return

    # Get email to get user for Gmail client
    result = await db.execute(
        select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
    )
    email = result.scalar_one_or_none()
    if not email:
        logger.error("callback_email_not_found", email_id=email_id)
        await query.answer("❌ Email not found", show_alert=True)
        return

    # Get user for Gmail and Telegram clients
    result = await db.execute(
        select(User).where(User.id == email.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.error("callback_user_not_found", user_id=email.user_id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Initialize services for workflow resumption
    gmail_client = GmailClient(user_id=user.id)
    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    # Create workflow with dependency injection using async context manager
    async with create_workflow_for_resumption(db, gmail_client, telegram_bot) as workflow:
        config = {"configurable": {"thread_id": workflow_mapping.thread_id}}

        try:
            # Update state with user decision using update_state
            # This updates only the specific fields without restarting workflow
            await workflow.aupdate_state(
                config,
                {"user_decision": "approve"},
                as_node="await_approval"
            )

            logger.info(
                "callback_resuming_workflow",
                email_id=email_id,
                thread_id=workflow_mapping.thread_id,
                user_decision="approve",
            )

            # Resume workflow from interrupt point (execute_action node)
            # ainvoke(None) continues from where workflow was interrupted
            # Workflow will execute: execute_action → send_confirmation → END
            await workflow.ainvoke(None, config=config)

            logger.info(
                "callback_workflow_resumed",
                email_id=email_id,
                action="approve",
            )

        except Exception as e:
            logger.error(
                "callback_workflow_resume_failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await query.answer("❌ Error processing approval", show_alert=True)


async def handle_reject(query, email_id: int, db: AsyncSession):
    """Handle Reject button click (AC #3, #6).

    Resumes LangGraph workflow with user_decision="reject", which triggers:
    - execute_action node: Update status to "rejected", no Gmail API call
    - send_confirmation node: Edit original message with confirmation

    Args:
        query: Telegram CallbackQuery object
        email_id: Email ID from callback data
        db: AsyncSession database session
    """
    await query.answer()

    logger.info(
        "callback_reject_processing",
        email_id=email_id,
        telegram_user_id=query.from_user.id,
    )

    # Get WorkflowMapping and Email
    result = await db.execute(
        select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
    )
    workflow_mapping = result.scalars().first()

    if not workflow_mapping:
        logger.error(
            "callback_workflow_mapping_not_found",
            email_id=email_id,
        )
        await query.answer("❌ Workflow not found", show_alert=True)
        return

    # Get email to get user
    result = await db.execute(
        select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
    )
    email = result.scalar_one_or_none()
    if not email:
        logger.error("callback_email_not_found", email_id=email_id)
        await query.answer("❌ Email not found", show_alert=True)
        return

    # Get user for services
    result = await db.execute(
        select(User).where(User.id == email.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.error("callback_user_not_found", user_id=email.user_id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Initialize services
    gmail_client = GmailClient(user_id=user.id)
    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    # Create workflow with dependency injection using async context manager
    async with create_workflow_for_resumption(db, gmail_client, telegram_bot) as workflow:
        config = {"configurable": {"thread_id": workflow_mapping.thread_id}}

        try:
            # Update state with user decision using update_state
            await workflow.aupdate_state(
                config,
                {"user_decision": "reject"},
                as_node="await_approval"
            )

            logger.info(
                "callback_resuming_workflow",
                email_id=email_id,
                thread_id=workflow_mapping.thread_id,
                user_decision="reject",
            )

            # Resume workflow from interrupt point
            await workflow.ainvoke(None, config=config)

            logger.info(
                "callback_workflow_resumed",
                email_id=email_id,
                action="reject",
            )

        except Exception as e:
            logger.error(
                "callback_workflow_resume_failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await query.answer("❌ Error processing rejection", show_alert=True)


async def handle_change_folder(query, email_id: int, db: AsyncSession):
    """Handle Change Folder button click (AC #4).

    Displays folder selection menu with user's folder categories.

    Args:
        query: Telegram CallbackQuery object
        email_id: Email ID from callback data
        db: AsyncSession database session
    """
    await query.answer()

    logger.info(
        "callback_change_folder_processing",
        email_id=email_id,
        telegram_user_id=query.from_user.id,
    )

    # Get user by telegram_id
    result = await db.execute(
        select(User).where(User.telegram_id == str(query.from_user.id))
    )
    user = result.scalars().first()

    if not user:
        logger.error("callback_user_not_found", telegram_user_id=query.from_user.id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Get user's folder categories
    result = await db.execute(
        select(FolderCategory).where(FolderCategory.user_id == user.id)
    )
    folders = result.scalars().all()

    if not folders:
        logger.warning("callback_no_folders_found", user_id=user.id)
        await query.answer("❌ No folders configured", show_alert=True)
        return

    # Create inline keyboard with folder options
    keyboard = []
    for folder in folders:
        button = InlineKeyboardButton(
            text=folder.name,
            callback_data=f"folder_{folder.id}_{email_id}"
        )
        keyboard.append([button])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Edit message to show folder selection
    try:
        # Don't use parse_mode to avoid Markdown entity conflicts
        await query.edit_message_text(
            text=query.message.text + "\n\n📁 Select a folder:",
            reply_markup=reply_markup,
        )

        logger.info(
            "callback_folder_menu_displayed",
            email_id=email_id,
            folder_count=len(folders),
        )

    except Exception as e:
        logger.error(
            "callback_edit_message_failed",
            email_id=email_id,
            error=str(e),
        )
        await query.answer("❌ Error displaying folders", show_alert=True)


async def handle_folder_selection(query, email_id: int, folder_id: int, db: AsyncSession):
    """Handle folder selection from change folder menu (AC #5, #6).

    Resumes LangGraph workflow with user_decision="change_folder" and selected_folder_id.

    Args:
        query: Telegram CallbackQuery object
        email_id: Email ID from callback data
        folder_id: Selected folder ID from callback data
        db: AsyncSession database session
    """
    await query.answer()

    logger.info(
        "callback_folder_selection_processing",
        email_id=email_id,
        folder_id=folder_id,
        telegram_user_id=query.from_user.id,
    )

    # Get WorkflowMapping and Email
    result = await db.execute(
        select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
    )
    workflow_mapping = result.scalars().first()

    if not workflow_mapping:
        logger.error(
            "callback_workflow_mapping_not_found",
            email_id=email_id,
        )
        await query.answer("❌ Workflow not found", show_alert=True)
        return

    # Verify folder exists and belongs to user
    result = await db.execute(
        select(FolderCategory).where(FolderCategory.id == folder_id)
    )
    folder = result.scalar_one_or_none()
    if not folder:
        logger.error(
            "callback_folder_not_found",
            folder_id=folder_id,
            email_id=email_id,
        )
        await query.answer("❌ Folder not found", show_alert=True)
        return

    # Get email to get user
    result = await db.execute(
        select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
    )
    email = result.scalar_one_or_none()
    if not email:
        logger.error("callback_email_not_found", email_id=email_id)
        await query.answer("❌ Email not found", show_alert=True)
        return

    # Get user for services
    result = await db.execute(
        select(User).where(User.id == email.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.error("callback_user_not_found", user_id=email.user_id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Initialize services
    gmail_client = GmailClient(user_id=user.id)
    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    # Create workflow with dependency injection using async context manager
    async with create_workflow_for_resumption(db, gmail_client, telegram_bot) as workflow:
        config = {"configurable": {"thread_id": workflow_mapping.thread_id}}

        try:
            # Update state with user decision and selected folder using update_state
            await workflow.aupdate_state(
                config,
                {
                    "user_decision": "change_folder",
                    "selected_folder_id": folder_id,
                    "selected_folder": folder.name
                },
                as_node="await_approval"
            )

            logger.info(
                "callback_resuming_workflow",
                email_id=email_id,
                thread_id=workflow_mapping.thread_id,
                user_decision="change_folder",
                selected_folder_id=folder_id,
            )

            # Resume workflow from interrupt point
            await workflow.ainvoke(None, config=config)

            logger.info(
                "callback_workflow_resumed",
                email_id=email_id,
                action="change_folder",
                folder_id=folder_id,
            )

        except Exception as e:
            logger.error(
                "callback_workflow_resume_failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await query.answer("❌ Error processing folder selection", show_alert=True)


# ============================================================================
# Response Editing and Sending Handlers (Story 3.9)
# ============================================================================


async def handle_send_response(update: Update, context: ContextTypes.DEFAULT_TYPE, email_id: int, db: AsyncSession):
    """Handle Send button click for response drafts (Story 3.9 - AC #4-9).

    Resumes LangGraph workflow with draft_decision="send_response", which triggers:
    - send_email_response node: Send email via Gmail API
    - execute_action node: Update EmailProcessingQueue status, apply folder
    - send_confirmation node: Delete intermediate messages, send clean summary

    Args:
        update: Telegram Update object with callback_query
        context: Bot context
        email_id: Email ID from callback data
        db: Database session
    """
    query = update.callback_query
    await query.answer()

    logger.info(
        "callback_send_response_processing",
        email_id=email_id,
        telegram_user_id=query.from_user.id,
    )

    # Get WorkflowMapping to find thread_id
    result = await db.execute(
        select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
    )
    workflow_mapping = result.scalars().first()

    if not workflow_mapping:
        logger.error(
            "callback_workflow_mapping_not_found",
            email_id=email_id,
        )
        await query.answer("❌ Workflow not found", show_alert=True)
        return

    # Get email to get user for Gmail client
    result = await db.execute(
        select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
    )
    email = result.scalar_one_or_none()
    if not email:
        logger.error("callback_email_not_found", email_id=email_id)
        await query.answer("❌ Email not found", show_alert=True)
        return

    # Get user for Gmail and Telegram clients
    result = await db.execute(
        select(User).where(User.id == email.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.error("callback_user_not_found", user_id=email.user_id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Initialize services for workflow resumption
    gmail_client = GmailClient(user_id=user.id)
    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    # Create workflow with dependency injection using async context manager
    async with create_workflow_for_resumption(db, gmail_client, telegram_bot) as workflow:
        config = {"configurable": {"thread_id": workflow_mapping.thread_id}}

        try:
            # Import Command from langgraph.types for proper interrupt resumption
            from langgraph.types import Command

            # CRITICAL FIX: Use Command(resume=...) to properly resume after interrupt()
            # This is the CORRECT way per LangGraph documentation to continue execution
            # after send_response_draft_notification's interrupt() call
            logger.info(
                "callback_resuming_workflow",
                email_id=email_id,
                thread_id=workflow_mapping.thread_id,
                draft_decision="send_response",
                note="Using Command(resume=...) to properly resume from interrupt"
            )

            # Resume workflow with Command - this passes "send_response" value to the interrupt() return
            # Workflow will continue: route_draft_decision → send_email_response → execute_action → send_confirmation → END
            await workflow.ainvoke(Command(resume="send_response"), config=config)

            logger.info(
                "callback_workflow_resumed",
                email_id=email_id,
                action="send_response",
            )

        except Exception as e:
            logger.error(
                "callback_workflow_resume_failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await query.answer("❌ Error sending response", show_alert=True)


async def handle_edit_response(update: Update, context: ContextTypes.DEFAULT_TYPE, email_id: int, db: AsyncSession):
    """Handle Edit button click for response drafts (Story 3.9 - AC #1-3).

    Prompts user to reply with edited text, captures reply,
    updates draft in database, and re-sends draft message.

    Args:
        update: Telegram Update object with callback_query
        context: Bot context
        email_id: Email ID from callback data
        db: Database session
    """
    query = update.callback_query
    telegram_user_id = query.from_user.id

    # Get user by telegram_id
    result = await db.execute(
        select(User).where(User.telegram_id == str(telegram_user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        logger.error("edit_response_user_not_found", telegram_user_id=telegram_user_id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Initialize services
    from app.services.response_editing_service import ResponseEditingService
    from app.services.telegram_response_draft import TelegramResponseDraftService

    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    draft_service = TelegramResponseDraftService(telegram_bot=telegram_bot)

    editing_service = ResponseEditingService(
        telegram_bot=telegram_bot,
        draft_service=draft_service
    )

    # Handle edit via service
    await editing_service.handle_edit_response_callback(
        update=update,
        context=context,
        email_id=email_id,
        user_id=user.id
    )


async def handle_reject_response(update: Update, context: ContextTypes.DEFAULT_TYPE, email_id: int, db: AsyncSession):
    """Handle Reject button click for response drafts (Story 3.9).

    Resumes LangGraph workflow with draft_decision="reject_response", which triggers:
    - execute_action node: Update EmailProcessingQueue status to "rejected", apply folder
    - send_confirmation node: Delete intermediate messages, send clean summary

    Args:
        update: Telegram Update object with callback_query
        context: Bot context
        email_id: Email ID from callback data
        db: Database session
    """
    query = update.callback_query
    await query.answer()

    logger.info(
        "callback_reject_response_processing",
        email_id=email_id,
        telegram_user_id=query.from_user.id,
    )

    # Get WorkflowMapping to find thread_id
    result = await db.execute(
        select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
    )
    workflow_mapping = result.scalars().first()

    if not workflow_mapping:
        logger.error(
            "callback_workflow_mapping_not_found",
            email_id=email_id,
        )
        await query.answer("❌ Workflow not found", show_alert=True)
        return

    # Get email to get user for Gmail client
    result = await db.execute(
        select(EmailProcessingQueue).where(EmailProcessingQueue.id == email_id)
    )
    email = result.scalar_one_or_none()
    if not email:
        logger.error("callback_email_not_found", email_id=email_id)
        await query.answer("❌ Email not found", show_alert=True)
        return

    # Get user for Gmail and Telegram clients
    result = await db.execute(
        select(User).where(User.id == email.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        logger.error("callback_user_not_found", user_id=email.user_id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Initialize services for workflow resumption
    gmail_client = GmailClient(user_id=user.id)
    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    # Create workflow with dependency injection using async context manager
    async with create_workflow_for_resumption(db, gmail_client, telegram_bot) as workflow:
        config = {"configurable": {"thread_id": workflow_mapping.thread_id}}

        try:
            # Import Command from langgraph.types for proper interrupt resumption
            from langgraph.types import Command

            # CRITICAL FIX: Use Command(resume=...) to properly resume after interrupt()
            # This is the CORRECT way per LangGraph documentation to continue execution
            # after send_response_draft_notification's interrupt() call
            logger.info(
                "callback_resuming_workflow",
                email_id=email_id,
                thread_id=workflow_mapping.thread_id,
                draft_decision="reject_response",
                note="Using Command(resume=...) to properly resume from interrupt"
            )

            # Resume workflow with Command - this passes "reject_response" value to the interrupt() return
            # Workflow will continue: route_draft_decision → execute_action → send_confirmation → END
            await workflow.ainvoke(Command(resume="reject_response"), config=config)

            logger.info(
                "callback_workflow_resumed",
                email_id=email_id,
                action="reject_response",
            )

        except Exception as e:
            logger.error(
                "callback_workflow_resume_failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await query.answer("❌ Error rejecting response", show_alert=True)


# ============================================================================
# Message Handler for Edit Workflow (Story 3.9)
# ============================================================================


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages for edit workflow reply capture (Story 3.9).

    This handler captures user replies during the response editing workflow.
    When a user clicks [Edit] on a response draft, they enter an editing session.
    Their next message is captured here and processed by ResponseEditingService.

    The handler checks if the user has an active editing session and routes
    the message to ResponseEditingService.handle_message_reply() if so.

    Args:
        update: Telegram Update object containing message
        context: Bot context with conversation state

    Note:
        This handler is registered for all TEXT messages that are NOT commands.
        It only processes messages from users with active edit sessions.
    """
    # Check if message exists and has text
    if not update.message or not update.message.text:
        return

    # Initialize services for edit workflow
    from app.services.response_editing_service import ResponseEditingService
    from app.services.telegram_response_draft import TelegramResponseDraftService

    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    draft_service = TelegramResponseDraftService(telegram_bot=telegram_bot)

    editing_service = ResponseEditingService(
        telegram_bot=telegram_bot,
        draft_service=draft_service
    )

    # Route to editing service's message handler
    await editing_service.handle_message_reply(
        update=update,
        context=context
    )
