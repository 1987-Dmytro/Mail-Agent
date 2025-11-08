"""Telegram bot command and callback handlers.

This module contains handlers for:
- Bot commands: /start, /help, /test
- Callback queries: Inline button interactions for email approval workflow
"""

import structlog
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession

from functools import partial

from app.api.deps import AsyncSessionLocal, engine
from app.core.gmail_client import GmailClient
from app.core.telegram_bot import TelegramBotClient
from app.models.email import EmailProcessingQueue
from app.models.folder_category import FolderCategory
from app.models.user import User
from app.models.workflow_mapping import WorkflowMapping
from app.services.telegram_linking import link_telegram_account
from app.workflows import nodes
from app.workflows.email_workflow import create_email_workflow

logger = structlog.get_logger(__name__)


def _create_workflow_for_resumption(db: Session, gmail_client: GmailClient, telegram_bot: TelegramBotClient):
    """Create workflow with dependency injection for callback resumption.

    This helper builds a workflow instance with proper dependency injection,
    allowing callback handlers to resume workflows with access to required services.

    Args:
        db: Database session
        gmail_client: Gmail API client for the user
        telegram_bot: Telegram bot client

    Returns:
        Compiled workflow ready for resumption via ainvoke()
    """
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.postgres import PostgresSaver
    from app.workflows.states import EmailWorkflowState
    import os

    # Get database URL for checkpointer
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.startswith("postgresql+psycopg://"):
        checkpoint_url = database_url.replace("postgresql+psycopg://", "postgresql://")
    else:
        checkpoint_url = database_url

    checkpointer = PostgresSaver.from_conn_string(
        conn_string=checkpoint_url,
        sync=False,
    )

    # Build workflow with dependency-injected nodes
    workflow = StateGraph(EmailWorkflowState)

    # Bind dependencies to node functions
    extract_context_with_deps = partial(nodes.extract_context, db=db, gmail_client=gmail_client)
    classify_with_deps = partial(nodes.classify, db=db, gmail_client=gmail_client, llm_client=None)  # llm not needed for resumption
    send_telegram_with_deps = partial(nodes.send_telegram, db=db, telegram_bot_client=telegram_bot)
    execute_action_with_deps = partial(nodes.execute_action, db=db, gmail_client=gmail_client)
    send_confirmation_with_deps = partial(nodes.send_confirmation, db=db, telegram_bot_client=telegram_bot)

    # Add nodes
    workflow.add_node("extract_context", extract_context_with_deps)
    workflow.add_node("classify", classify_with_deps)
    workflow.add_node("send_telegram", send_telegram_with_deps)
    workflow.add_node("await_approval", nodes.await_approval)
    workflow.add_node("execute_action", execute_action_with_deps)
    workflow.add_node("send_confirmation", send_confirmation_with_deps)

    # Define edges
    workflow.set_entry_point("extract_context")
    workflow.add_edge("extract_context", "classify")
    workflow.add_edge("classify", "send_telegram")
    workflow.add_edge("send_telegram", "await_approval")
    workflow.add_edge("await_approval", "execute_action")
    workflow.add_edge("execute_action", "send_confirmation")
    workflow.add_edge("send_confirmation", END)

    # Compile with checkpointer
    return workflow.compile(checkpointer=checkpointer)


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

        # Validate and link account using database session
        with Session(engine) as db:
            result = link_telegram_account(
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

    Args:
        callback_data: Raw callback data string from Telegram button

    Returns:
        Tuple of (action, email_id, folder_id):
        - action: "approve", "reject", "change", or "folder"
        - email_id: Email ID from callback data (int)
        - folder_id: Folder ID for folder selection, None otherwise

    Raises:
        ValueError: If callback_data format is invalid
    """
    parts = callback_data.split("_")

    if len(parts) < 2:
        raise ValueError(f"Invalid callback data format: '{callback_data}' (expected at least 2 parts)")

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


async def handle_approve(query, email_id: int, db: Session):
    """Handle Approve button click (AC #2, #6, #9).

    Resumes LangGraph workflow with user_decision="approve", which triggers:
    - execute_action node: Apply proposed folder label to Gmail
    - send_confirmation node: Edit original message with confirmation

    Args:
        query: Telegram CallbackQuery object
        email_id: Email ID from callback data
        db: Database session
    """
    await query.answer()

    logger.info(
        "callback_approve_processing",
        email_id=email_id,
        telegram_user_id=query.from_user.id,
    )

    # Get WorkflowMapping and Email to find thread_id and user
    workflow_mapping = db.exec(
        select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
    ).first()

    if not workflow_mapping:
        logger.error(
            "callback_workflow_mapping_not_found",
            email_id=email_id,
        )
        await query.answer("❌ Workflow not found", show_alert=True)
        return

    # Get email to get user for Gmail client
    email = db.get(EmailProcessingQueue, email_id)
    if not email:
        logger.error("callback_email_not_found", email_id=email_id)
        await query.answer("❌ Email not found", show_alert=True)
        return

    # Get user for Gmail and Telegram clients
    user = db.get(User, email.user_id)
    if not user:
        logger.error("callback_user_not_found", user_id=email.user_id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Initialize services for workflow resumption
    gmail_client = GmailClient(user_id=user.id, db_session=db)
    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    # Create workflow with dependency injection
    workflow = _create_workflow_for_resumption(db, gmail_client, telegram_bot)
    config = {"configurable": {"thread_id": workflow_mapping.thread_id}}

    try:
        # Get current state from PostgreSQL checkpoint
        state_snapshot = await workflow.aget_state(config)
        state = dict(state_snapshot.values)

        # Update state with user decision
        state["user_decision"] = "approve"

        logger.info(
            "callback_resuming_workflow",
            email_id=email_id,
            thread_id=workflow_mapping.thread_id,
            user_decision="approve",
        )

        # Resume workflow from await_approval node
        # Workflow will execute: await_approval → execute_action → send_confirmation → END
        await workflow.ainvoke(state, config=config)

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


async def handle_reject(query, email_id: int, db: Session):
    """Handle Reject button click (AC #3, #6).

    Resumes LangGraph workflow with user_decision="reject", which triggers:
    - execute_action node: Update status to "rejected", no Gmail API call
    - send_confirmation node: Edit original message with confirmation

    Args:
        query: Telegram CallbackQuery object
        email_id: Email ID from callback data
        db: Database session
    """
    await query.answer()

    logger.info(
        "callback_reject_processing",
        email_id=email_id,
        telegram_user_id=query.from_user.id,
    )

    # Get WorkflowMapping and Email
    workflow_mapping = db.exec(
        select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
    ).first()

    if not workflow_mapping:
        logger.error(
            "callback_workflow_mapping_not_found",
            email_id=email_id,
        )
        await query.answer("❌ Workflow not found", show_alert=True)
        return

    # Get email to get user
    email = db.get(EmailProcessingQueue, email_id)
    if not email:
        logger.error("callback_email_not_found", email_id=email_id)
        await query.answer("❌ Email not found", show_alert=True)
        return

    # Get user for services
    user = db.get(User, email.user_id)
    if not user:
        logger.error("callback_user_not_found", user_id=email.user_id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Initialize services
    gmail_client = GmailClient(user_id=user.id, db_session=db)
    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    # Create workflow with dependency injection
    workflow = _create_workflow_for_resumption(db, gmail_client, telegram_bot)
    config = {"configurable": {"thread_id": workflow_mapping.thread_id}}

    try:
        # Get current state from PostgreSQL checkpoint
        state_snapshot = await workflow.aget_state(config)
        state = dict(state_snapshot.values)

        # Update state with user decision
        state["user_decision"] = "reject"

        logger.info(
            "callback_resuming_workflow",
            email_id=email_id,
            thread_id=workflow_mapping.thread_id,
            user_decision="reject",
        )

        # Resume workflow
        await workflow.ainvoke(state, config=config)

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


async def handle_change_folder(query, email_id: int, db: Session):
    """Handle Change Folder button click (AC #4).

    Displays folder selection menu with user's folder categories.

    Args:
        query: Telegram CallbackQuery object
        email_id: Email ID from callback data
        db: Database session
    """
    await query.answer()

    logger.info(
        "callback_change_folder_processing",
        email_id=email_id,
        telegram_user_id=query.from_user.id,
    )

    # Get user by telegram_id
    user = db.exec(
        select(User).where(User.telegram_id == str(query.from_user.id))
    ).first()

    if not user:
        logger.error("callback_user_not_found", telegram_user_id=query.from_user.id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Get user's folder categories
    folders = db.exec(
        select(FolderCategory).where(FolderCategory.user_id == user.id)
    ).all()

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
        await query.edit_message_text(
            text=query.message.text + "\n\n📁 *Select a folder:*",
            reply_markup=reply_markup,
            parse_mode="Markdown",
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


async def handle_folder_selection(query, email_id: int, folder_id: int, db: Session):
    """Handle folder selection from change folder menu (AC #5, #6).

    Resumes LangGraph workflow with user_decision="change_folder" and selected_folder_id.

    Args:
        query: Telegram CallbackQuery object
        email_id: Email ID from callback data
        folder_id: Selected folder ID from callback data
        db: Database session
    """
    await query.answer()

    logger.info(
        "callback_folder_selection_processing",
        email_id=email_id,
        folder_id=folder_id,
        telegram_user_id=query.from_user.id,
    )

    # Get WorkflowMapping and Email
    workflow_mapping = db.exec(
        select(WorkflowMapping).where(WorkflowMapping.email_id == email_id)
    ).first()

    if not workflow_mapping:
        logger.error(
            "callback_workflow_mapping_not_found",
            email_id=email_id,
        )
        await query.answer("❌ Workflow not found", show_alert=True)
        return

    # Verify folder exists and belongs to user
    folder = db.get(FolderCategory, folder_id)
    if not folder:
        logger.error(
            "callback_folder_not_found",
            folder_id=folder_id,
            email_id=email_id,
        )
        await query.answer("❌ Folder not found", show_alert=True)
        return

    # Get email to get user
    email = db.get(EmailProcessingQueue, email_id)
    if not email:
        logger.error("callback_email_not_found", email_id=email_id)
        await query.answer("❌ Email not found", show_alert=True)
        return

    # Get user for services
    user = db.get(User, email.user_id)
    if not user:
        logger.error("callback_user_not_found", user_id=email.user_id)
        await query.answer("❌ User not found", show_alert=True)
        return

    # Initialize services
    gmail_client = GmailClient(user_id=user.id, db_session=db)
    telegram_bot = TelegramBotClient()
    await telegram_bot.initialize()

    # Create workflow with dependency injection
    workflow = _create_workflow_for_resumption(db, gmail_client, telegram_bot)
    config = {"configurable": {"thread_id": workflow_mapping.thread_id}}

    try:
        # Get current state from PostgreSQL checkpoint
        state_snapshot = await workflow.aget_state(config)
        state = dict(state_snapshot.values)

        # Update state with user decision and selected folder
        state["user_decision"] = "change_folder"
        state["selected_folder_id"] = folder_id
        state["selected_folder"] = folder.name

        logger.info(
            "callback_resuming_workflow",
            email_id=email_id,
            thread_id=workflow_mapping.thread_id,
            user_decision="change_folder",
            selected_folder_id=folder_id,
        )

        # Resume workflow
        await workflow.ainvoke(state, config=config)

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
