"""LangGraph email classification workflow with PostgreSQL checkpointing.

This module compiles the email classification state machine with persistent
checkpoint storage, enabling workflow pause/resume across service restarts
and asynchronous user interactions.

Key Features:
    - StateGraph: Directed workflow with 8 nodes
    - PostgreSQL Checkpointing: State persisted after every node execution
    - Pause/Resume: Workflow pauses at await_approval, resumes hours/days later
    - Thread Tracking: Each workflow instance identified by unique thread_id
    - Unified Email Sending: Email responses integrated into main workflow

Workflow Flow:
    START
      ↓
    extract_context (Load email from Gmail)
      ↓
    classify (AI classification with Gemini)
      ↓
    detect_priority (Priority detection - Story 2.9)
      ↓
    {CONDITIONAL ROUTING based on classification}
      ↓
    needs_response: generate_response (Draft AI response with RAG context)
      ↓
    sort_only: (skip response generation)
      ↓
    send_telegram (Send approval request or batch)
      ↓
    await_approval (⚠️ PAUSE - State saved to PostgreSQL)
      ↓
    (User responds via Telegram, workflow resumes from checkpoint - Story 2.7)
      ↓
    send_email_response (Send AI-generated email if needs_response + approved)
      ↓
    execute_action (Apply Gmail label)
      ↓
    send_confirmation (Send confirmation)
      ↓
    END

Usage:
    from app.workflows.email_workflow import create_email_workflow

    # Create compiled workflow with checkpointer
    workflow = create_email_workflow()

    # Initialize and run workflow
    initial_state = EmailWorkflowState(
        email_id="123",
        user_id="456",
        thread_id="email_123_abc-def-123",
        ...
    )
    config = {"configurable": {"thread_id": initial_state["thread_id"]}}
    result = await workflow.ainvoke(initial_state, config=config)

    # Workflow pauses at await_approval, state saved to PostgreSQL
    # Resume later via Telegram callback (Story 2.7)
"""

import os
import structlog
from functools import partial
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from app.workflows.states import EmailWorkflowState
from app.workflows.nodes import (
    extract_context,
    classify,
    detect_priority,
    send_telegram,
    draft_response,
    await_approval,
    send_email_response,  # New node for sending email responses
    execute_action,
    send_confirmation,
)


logger = structlog.get_logger(__name__)


def route_by_classification(state: EmailWorkflowState) -> str:
    """Conditional edge function to route workflow based on email classification (Story 3.11 - AC #2).

    Routes emails to different workflow paths based on classification:
    - "needs_response": Email requires AI response generation → generate_response node
    - "sort_only": Email only needs sorting → send_telegram node (skip response generation)

    This function implements the core conditional routing logic that enables
    the RAG system integration (Epic 3). Emails classified as needing responses
    will have AI drafts generated using full conversation context, while
    newsletters and notifications skip straight to approval.

    Args:
        state: Current EmailWorkflowState containing classification field

    Returns:
        str: Classification value - either "needs_response" or "sort_only"
            (path_map will map these to node names)

    Example:
        >>> state = EmailWorkflowState(classification="needs_response", ...)
        >>> classification = route_by_classification(state)
        >>> print(classification)  # "needs_response"
        >>> # path_map will route to "generate_response" node

        >>> state = EmailWorkflowState(classification="sort_only", ...)
        >>> classification = route_by_classification(state)
        >>> print(classification)  # "sort_only"
        >>> # path_map will route to "send_telegram" node
    """
    classification = state.get("classification", "sort_only")

    # Log routing decision
    if classification == "needs_response":
        logger.info(
            "workflow_routing_to_generate_response",
            email_id=state["email_id"],
            classification=classification,
            next_node="generate_response"
        )
    else:
        logger.info(
            "workflow_routing_to_send_telegram",
            email_id=state["email_id"],
            classification=classification,
            next_node="send_telegram"
        )

    # Return classification value (path_map will map to node name)
    return classification


def route_after_approval(state: EmailWorkflowState) -> str:
    """Conditional edge function to route workflow after user approval (Story 1.2).

    Routes emails based on classification AND user approval decision:
    - "needs_response" + "approve" → send_email_response (send AI response)
    - "sort_only" + "approve" → execute_action (skip email sending)
    - "reject" → send_confirmation (skip all actions, just confirm rejection)
    - "change_folder" → execute_action (use selected_folder instead of proposed_folder)

    This function fixes the critical business logic bug where ALL emails were being sent
    email responses, even "sort_only" emails that should only be sorted.

    Args:
        state: Current EmailWorkflowState containing classification and user_decision

    Returns:
        str: Routing key for path_map - one of:
            - "send_email" - Send email response then execute action
            - "execute_only" - Execute action without sending email
            - "reject" - Skip to confirmation

    Example:
        >>> state = EmailWorkflowState(
        ...     classification="needs_response",
        ...     user_decision="approve",
        ...     ...
        ... )
        >>> route = route_after_approval(state)
        >>> print(route)  # "send_email"

        >>> state = EmailWorkflowState(
        ...     classification="sort_only",
        ...     user_decision="approve",
        ...     ...
        ... )
        >>> route = route_after_approval(state)
        >>> print(route)  # "execute_only"

        >>> state = EmailWorkflowState(user_decision="reject", ...)
        >>> route = route_after_approval(state)
        >>> print(route)  # "reject"
    """
    classification = state.get("classification", "sort_only")
    user_decision = state.get("user_decision", "approve")
    email_id = state.get("email_id", "unknown")

    # Handle rejection - skip all actions
    if user_decision == "reject":
        logger.info(
            "workflow_routing_after_approval",
            email_id=email_id,
            classification=classification,
            user_decision=user_decision,
            next_node="send_confirmation",
            reason="User rejected - skipping all actions"
        )
        return "reject"

    # Handle folder change or approval
    # For both "approve" and "change_folder", we need to apply the Gmail action
    # But we only send email response if classification was "needs_response"
    if classification == "needs_response":
        logger.info(
            "workflow_routing_after_approval",
            email_id=email_id,
            classification=classification,
            user_decision=user_decision,
            next_node="send_email_response",
            reason="needs_response classification - will send email then execute action"
        )
        return "send_email"
    else:
        # sort_only - skip email sending, go straight to execute_action
        logger.info(
            "workflow_routing_after_approval",
            email_id=email_id,
            classification=classification,
            user_decision=user_decision,
            next_node="execute_action",
            reason="sort_only classification - skipping email send"
        )
        return "execute_only"


def create_email_workflow(
    checkpointer=None,
    db_session_factory=None,
    gmail_client=None,
    llm_client=None,
    telegram_client=None,
    context_service=None,
    embedding_service=None,
    vector_db_client=None,
):
    """Create and compile the email classification workflow with PostgreSQL checkpointer.

    This function builds the complete LangGraph state machine for email
    classification and approval. The workflow is compiled with a PostgreSQL
    checkpointer to enable persistent state storage across service restarts.

    Workflow Architecture:
        - Nodes: 8 workflow steps (extract, classify, detect_priority, generate_response, telegram, await, send_email_response, execute, confirm)
        - Edges: Sequential flow with conditional routing and pause at await_approval
        - Checkpointer: PostgreSQL storage for state persistence (or custom checkpointer for tests)
        - Thread ID: Unique identifier for each workflow instance

    Args:
        checkpointer: Optional checkpointer instance (MemorySaver for tests, None for production PostgreSQL)
        db_session_factory: AsyncSession factory for creating database sessions (required for tests, optional for production)
        gmail_client: Gmail API client instance (for tests/production)
        llm_client: LLM client instance for classification (for tests/production)
        telegram_client: Telegram bot client instance (for tests/production)
        context_service: Optional ContextRetrievalService for response generation (for tests with mocks)
        embedding_service: Optional EmbeddingService for context retrieval (for tests with mocks)
        vector_db_client: Optional VectorDBClient for semantic search (for tests with mocks)

    Returns:
        CompiledGraph: Compiled LangGraph workflow ready for execution
            - Use ainvoke() for async execution
            - Pass config={"configurable": {"thread_id": "..."}} for checkpointing
            - State automatically saved after each node execution
            - Workflow pauses at await_approval node

    Example:
        >>> # Production usage with PostgreSQL
        >>> workflow = create_email_workflow()
        >>>
        >>> # Test usage with MemorySaver and mocks
        >>> from langgraph.checkpoint.memory import MemorySaver
        >>> from sqlalchemy.ext.asyncio import async_sessionmaker
        >>> workflow = create_email_workflow(
        ...     checkpointer=MemorySaver(),
        ...     db_session_factory=async_sessionmaker(engine),
        ...     gmail_client=mock_gmail,
        ...     llm_client=mock_llm,
        ...     telegram_client=mock_telegram
        ... )
        >>>
        >>> initial_state = EmailWorkflowState(email_id="123", ...)
        >>> config = {"configurable": {"thread_id": "email_123_abc"}}
        >>> result = await workflow.ainvoke(initial_state, config=config)
        >>> # Workflow pauses at await_approval, state in checkpointer
    """
    # Use provided checkpointer or create PostgreSQL checkpointer
    if checkpointer is None:
        logger.info("creating_email_workflow", checkpointer="PostgreSQL")

        # Initialize PostgreSQL checkpointer for workflow state persistence
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required for workflow checkpointing"
            )

        # Convert psycopg:// to postgresql:// for PostgresSaver compatibility
        if database_url.startswith("postgresql+psycopg://"):
            checkpoint_url = database_url.replace("postgresql+psycopg://", "postgresql://")
        else:
            checkpoint_url = database_url

        logger.debug(
            "initializing_checkpointer",
            database_url_prefix=checkpoint_url.split("@")[0].split("://")[0],
        )

        # PostgresSaver.from_conn_string returns a context manager
        # We need to enter it to get the actual checkpointer instance
        checkpointer_cm = PostgresSaver.from_conn_string(checkpoint_url)
        checkpointer = checkpointer_cm.__enter__()
    else:
        logger.info("creating_email_workflow", checkpointer="Custom (test mode)")

    # Build StateGraph workflow with EmailWorkflowState
    logger.debug("building_workflow_graph")

    workflow = StateGraph(EmailWorkflowState)

    # Add workflow nodes with dependencies bound via functools.partial
    # For tests: dependencies are passed as parameters (mocks)
    # For production: dependencies would be injected via DI container or created here
    # Note: Nodes are async functions, but LangGraph handles the async execution

    if db_session_factory and gmail_client and llm_client and telegram_client:
        # Test mode: bind mock dependencies
        logger.debug("binding_mock_dependencies_to_nodes")
        workflow.add_node("extract_context", partial(extract_context, db_factory=db_session_factory, gmail_client=gmail_client))
        workflow.add_node("classify", partial(classify, db_factory=db_session_factory, gmail_client=gmail_client, llm_client=llm_client))
        workflow.add_node("detect_priority", partial(detect_priority, db_factory=db_session_factory))
        workflow.add_node("generate_response", partial(draft_response, db_factory=db_session_factory, context_service=context_service, embedding_service=embedding_service, vector_db_client=vector_db_client, gmail_client=gmail_client))  # Story 3.11 - AC #3
        workflow.add_node("send_telegram", partial(send_telegram, db_factory=db_session_factory, telegram_bot_client=telegram_client))
        workflow.add_node("await_approval", await_approval)  # No dependencies needed
        workflow.add_node("send_email_response", partial(send_email_response, db_factory=db_session_factory, gmail_client=gmail_client))
        workflow.add_node("execute_action", partial(execute_action, db_factory=db_session_factory, gmail_client=gmail_client))
        workflow.add_node("send_confirmation", partial(send_confirmation, db_factory=db_session_factory, telegram_bot_client=telegram_client))
    else:
        # Production mode: nodes will get dependencies from global/DI container
        # TODO: Implement proper dependency injection for production
        logger.warning("no_dependencies_provided", note="Production mode needs DI implementation")
        workflow.add_node("extract_context", extract_context)
        workflow.add_node("classify", classify)
        workflow.add_node("detect_priority", detect_priority)
        workflow.add_node("generate_response", draft_response)  # Story 3.11 - AC #3
        workflow.add_node("send_telegram", send_telegram)
        workflow.add_node("await_approval", await_approval)
        workflow.add_node("send_email_response", send_email_response)
        workflow.add_node("execute_action", execute_action)
        workflow.add_node("send_confirmation", send_confirmation)

    # Define workflow edges (sequential flow with conditional routing - Story 3.11)
    # Entry point: extract_context is the first node
    workflow.set_entry_point("extract_context")

    # Sequential edges up to conditional routing
    workflow.add_edge("extract_context", "classify")
    workflow.add_edge("classify", "detect_priority")  # Story 5-3: Add detect_priority to workflow

    # Conditional routing based on classification (Story 3.11 - AC #4, #5)
    # detect_priority → route_by_classification → {needs_response: generate_response, sort_only: send_telegram}
    workflow.add_conditional_edges(
        "detect_priority",  # Story 5-3: Route from detect_priority (was: classify)
        route_by_classification,
        {
            "needs_response": "generate_response",
            "sort_only": "send_telegram",
        }
    )

    # generate_response → send_telegram (Story 3.11 - AC #5)
    workflow.add_edge("generate_response", "send_telegram")

    # Continue to await_approval (workflow pauses here)
    workflow.add_edge("send_telegram", "await_approval")

    # Conditional routing after user approval (Story 1.2)
    # Route based on classification AND user decision
    workflow.add_conditional_edges(
        "await_approval",
        route_after_approval,
        {
            "send_email": "send_email_response",  # needs_response + approved → send email
            "execute_only": "execute_action",     # sort_only + approved → skip email
            "reject": "send_confirmation",         # rejected → skip all actions
        }
    )

    # send_email_response → execute_action (for needs_response emails)
    workflow.add_edge("send_email_response", "execute_action")

    # execute_action → send_confirmation (for all approved emails)
    workflow.add_edge("execute_action", "send_confirmation")

    # send_confirmation → END (workflow complete)
    workflow.add_edge("send_confirmation", END)

    # Compile workflow with checkpointer
    logger.debug("compiling_workflow_with_checkpointer")

    app = workflow.compile(checkpointer=checkpointer)

    logger.info(
        "workflow_compiled_successfully",
        node_count=8,
        checkpointer="PostgreSQL",
        pause_point="await_approval",
    )

    return app


# Export factory function for workflow creation
__all__ = ["create_email_workflow"]
