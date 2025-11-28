"""LangGraph workflow state definitions for email processing.

This module defines the state containers for LangGraph workflows, providing type-safe
state management across workflow nodes. States are implemented as TypedDicts to enable
proper type checking and documentation.

The EmailWorkflowState tracks all data needed for the email classification and approval
workflow, enabling workflow pause/resume via PostgreSQL checkpointing.
"""

from typing import Literal, TypedDict


class EmailWorkflowState(TypedDict):
    """State container for the email classification and approval workflow.

    This state flows through all workflow nodes, accumulating data as the email
    moves through classification, Telegram approval, and Gmail label application.
    The state is persisted to PostgreSQL via LangGraph's checkpointer, enabling
    workflow pause/resume across service restarts and user interactions.

    Thread ID Format:
        email_{email_id}_{uuid4()} - Unique identifier for each workflow instance

    Workflow Flow:
        1. extract_context: Loads email from Gmail, populates email_content/sender/subject
        2. classify: Calls Gemini LLM, populates classification/proposed_folder/reasoning
        3. send_telegram: Sends approval request to user (stub in Story 2.3)
        4. await_approval: Pauses workflow, saves state to PostgreSQL checkpoint
        5. execute_action: User responds via Telegram, workflow resumes (Story 2.7)
        6. send_confirmation: Sends completion message (Story 2.6)

    Attributes:
        email_id: Unique email identifier from EmailProcessingQueue.id
        user_id: User ID who owns this email workflow
        thread_id: LangGraph thread ID for checkpoint tracking (format: email_{email_id}_{uuid})
        email_content: Full email body extracted from Gmail (plain text)
        sender: Email sender address
        subject: Email subject line
        classification: Email type classification ("sort_only" for Epic 2, "needs_response" for Epic 3)
        proposed_folder: AI-suggested folder name for email sorting
        classification_reasoning: AI reasoning for transparency (max 300 chars from Gemini)
        priority_score: AI-calculated priority (0-100 scale, >= 70 triggers immediate notification)
        user_decision: User's approval decision from Telegram ("approve", "reject", "change_folder")
        selected_folder: User-selected folder if user_decision == "change_folder"
        final_action: Description of action taken (e.g., "Moved to Work folder")
        error_message: Error description if workflow fails at any node
    """

    # Email identification and tracking
    email_id: str
    user_id: str
    thread_id: str

    # Email content (populated by extract_context node)
    email_content: str
    sender: str
    subject: str
    body_preview: str  # First 100 characters of email body (for Telegram message)

    # Classification results (populated by classify node)
    classification: Literal["sort_only", "needs_response"] | None
    proposed_folder: str | None
    proposed_folder_id: int | None  # Database FK to folder_categories
    classification_reasoning: str | None
    priority_score: int

    # Response generation (populated by draft_response node - Story 3.11)
    draft_response: str | None  # AI-generated response text from ResponseGenerationService
    detected_language: str | None  # Language code (en/de/ru/uk) from LanguageDetectionService
    tone: str | None  # Detected tone (formal/professional/casual) from ToneDetectionService

    # Telegram message tracking (populated by send_telegram node - Story 2.6)
    telegram_message_id: str | None  # Telegram message ID for editing/tracking

    # User approval (populated by await_approval/execute_action nodes - Story 2.7)
    user_decision: Literal["approve", "reject", "change_folder"] | None
    selected_folder: str | None  # Only used if user_decision == "change_folder"
    selected_folder_id: int | None  # Database FK for selected folder

    # Workflow completion (populated by execute_action node)
    final_action: str | None  # Description of action taken (e.g., "Moved to Work folder")

    # Error handling (populated by any node on failure)
    error_message: str | None
