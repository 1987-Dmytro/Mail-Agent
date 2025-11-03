# Decision Architecture - Mail Agent

## Executive Summary

Mail Agent is a **LangGraph-orchestrated AI agent system** that automates Gmail email management through intelligent sorting and RAG-powered response generation with human-in-the-loop approval via Telegram. The architecture leverages a production-ready FastAPI + LangGraph template as the foundation, extended with Gmail API integration, ChromaDB vector database for RAG, Google Gemini 2.5 Flash for LLM operations, and a Next.js 15 configuration UI. The system is designed for zero-cost infrastructure operation (free-tier services) while maintaining production-grade quality through comprehensive monitoring, structured logging, and persistent state management via PostgreSQL checkpointing. A novel **TelegramHITLWorkflow** pattern enables LangGraph workflows to pause for user approval in Telegram and resume exactly where they left off, ensuring complete user control over all AI actions.

## Project Initialization

**First Implementation Story:** Clone and configure the FastAPI + LangGraph production template

### Backend Setup

```bash
# Clone the production-ready template
git clone https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template mail-agent-backend
cd mail-agent-backend

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys and database URLs

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Create Next.js 15 project with TypeScript and Tailwind
npx create-next-app@latest mail-agent-ui --typescript --tailwind --eslint --app --src-dir
cd mail-agent-ui

# Initialize shadcn/ui
npx shadcn@latest init
# Select: Default style, Zinc slate, CSS variables: yes

# Install additional dependencies
npm install axios date-fns

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

### Infrastructure Setup (Docker)

```bash
# Start PostgreSQL, Redis, ChromaDB, Prometheus, Grafana
docker-compose up -d

# Verify services
docker-compose ps
curl http://localhost:8000/health  # Backend health
curl http://localhost:3000          # Frontend
```

**The template provides:** FastAPI with async endpoints, LangGraph integration, PostgreSQL with ORM, JWT authentication, rate limiting, structured logging, Prometheus + Grafana monitoring, Docker deployment configs, and environment management (dev/staging/prod).

## Decision Summary

| Category | Decision | Version | Affects Epics | Rationale |
| -------- | -------- | ------- | ------------- | --------- |
| **Agent Framework** | LangGraph | 1.0.2 | All Epics | State machine-based workflow orchestration with persistent checkpointing for human-in-the-loop patterns |
| **Backend Framework** | FastAPI | 0.120.4 | All Epics | High-performance async API, native Python 3.13+ support, excellent LangGraph integration |
| **Frontend Framework** | Next.js | 15.5 | Epic 4 | Modern React framework with App Router, server-side rendering, optimal for configuration UI |
| **Database** | PostgreSQL | 18 | All Epics | Robust RDBMS for user data, workflow state, and LangGraph checkpointing |
| **Vector Database** | ChromaDB | Latest | Epic 3 | Self-hosted, unlimited free tier, supports semantic search for RAG |
| **LLM Provider** | Google Gemini 2.5 Flash | gemini-2.5-flash | Epics 2, 3 | True unlimited free tier (1M tokens/min), excellent multilingual support, fast inference |
| **Embedding Model** | Google Gemini Embeddings | text-embedding-004 | Epic 3 | Free tier compatible with Gemini, high-quality embeddings (1536 dimensions) |
| **Task Queue** | Celery + Redis | Latest | Epics 1, 2, 3 | Production-grade background task processing for email polling and RAG indexing |
| **Telegram Bot Library** | python-telegram-bot | Latest | Epic 2 | Official library, supports long polling and inline keyboards |
| **Gmail API Strategy** | Polling (2 min intervals) | - | Epic 1 | Simpler than webhooks, meets <2 min latency requirement, easier local development |
| **UI Component Library** | shadcn/ui + Tailwind CSS | Latest | Epic 4 | Accessible, professional components, rapid development, WCAG 2.1 compliant |
| **Monitoring** | Prometheus + Grafana | Provided by template | All Epics | Production-grade observability for API metrics, database performance, LLM usage |
| **LLM Observability** | Langfuse | Provided by template | Epics 2, 3 | Specialized LLM tracing, token usage tracking, prompt debugging |

## Project Structure

```
mail-agent/
├── backend/                          # FastAPI + LangGraph service
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI application entry
│   │   ├── config.py                 # Environment configuration
│   │   │
│   │   ├── api/                      # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── health.py             # Health check endpoints
│   │   │   ├── auth.py               # Gmail OAuth endpoints
│   │   │   ├── telegram.py           # Telegram linking endpoints
│   │   │   ├── folders.py            # Folder management API
│   │   │   ├── settings.py           # User settings API
│   │   │   └── webhooks.py           # Telegram bot webhooks
│   │   │
│   │   ├── core/                     # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── gmail_client.py       # Gmail API wrapper
│   │   │   ├── telegram_bot.py       # Telegram bot client
│   │   │   ├── llm_client.py         # Gemini API wrapper
│   │   │   └── vector_store.py       # ChromaDB wrapper
│   │   │
│   │   ├── workflows/                # LangGraph workflows
│   │   │   ├── __init__.py
│   │   │   ├── email_workflow.py     # Main email processing state machine
│   │   │   ├── states.py             # State definitions (TypedDict)
│   │   │   └── nodes.py              # Workflow node implementations
│   │   │
│   │   ├── services/                 # Business services
│   │   │   ├── __init__.py
│   │   │   ├── email_polling.py      # Gmail polling service
│   │   │   ├── classification.py     # AI email classification
│   │   │   ├── rag_service.py        # RAG context retrieval
│   │   │   ├── response_generation.py # AI response drafting
│   │   │   ├── priority_detection.py # Government email detection
│   │   │   └── language_detection.py # Email language detection
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py               # User model
│   │   │   ├── email_queue.py        # EmailProcessingQueue model
│   │   │   ├── folder_category.py    # FolderCategories model
│   │   │   ├── approval_history.py   # ApprovalHistory model
│   │   │   ├── workflow_mapping.py   # WorkflowMapping model (novel pattern)
│   │   │   └── notification_prefs.py # NotificationPreferences model
│   │   │
│   │   ├── tasks/                    # Background tasks (Celery)
│   │   │   ├── __init__.py
│   │   │   ├── email_tasks.py        # Email polling & processing tasks
│   │   │   ├── indexing_tasks.py     # RAG indexing tasks
│   │   │   └── notification_tasks.py # Batch notification tasks
│   │   │
│   │   ├── db/                       # Database management
│   │   │   ├── __init__.py
│   │   │   ├── session.py            # DB session management
│   │   │   └── migrations/           # Alembic migrations
│   │   │
│   │   └── utils/                    # Utilities
│   │       ├── __init__.py
│   │       ├── logger.py             # Structured logging setup
│   │       ├── errors.py             # Error classes & handlers
│   │       └── validators.py         # Input validation
│   │
│   ├── tests/                        # Backend tests
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   │
│   ├── requirements.txt              # Python dependencies
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
│
├── frontend/                         # Next.js configuration UI
│   ├── src/
│   │   ├── app/                      # Next.js 15 App Router
│   │   │   ├── layout.tsx            # Root layout
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── onboarding/           # Onboarding wizard pages
│   │   │   │   ├── page.tsx
│   │   │   │   ├── gmail/page.tsx
│   │   │   │   ├── telegram/page.tsx
│   │   │   │   └── folders/page.tsx
│   │   │   ├── dashboard/page.tsx    # Dashboard
│   │   │   └── settings/page.tsx     # Settings
│   │   │
│   │   ├── components/               # React components
│   │   │   ├── ui/                   # shadcn/ui components
│   │   │   ├── onboarding/
│   │   │   ├── dashboard/
│   │   │   └── shared/
│   │   │
│   │   ├── lib/                      # Utilities
│   │   │   ├── api-client.ts         # Backend API client
│   │   │   └── utils.ts
│   │   │
│   │   └── types/                    # TypeScript types
│   │       └── index.ts
│   │
│   ├── public/                       # Static assets
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
│
├── docs/                             # Project documentation
│   ├── PRD.md                        # Product Requirements
│   ├── epics.md                      # Epic breakdown (40 stories)
│   ├── product-brief-Mail Agent-2025-11-03.md
│   └── architecture.md               # This document
│
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       └── frontend-ci.yml
│
├── README.md
└── .gitignore
```

## Epic to Architecture Mapping

| Epic | Components | Key Files | Integration Points |
| ---- | ---------- | --------- | ------------------ |
| **Epic 1: Foundation & Gmail Integration** | Gmail API client, OAuth flow, database models, email polling service | `app/core/gmail_client.py`, `app/api/auth.py`, `app/models/user.py`, `app/tasks/email_tasks.py` | Gmail API REST endpoints, PostgreSQL for user tokens |
| **Epic 2: AI Sorting & Telegram Approval** | LangGraph workflow, Telegram bot, AI classification service, approval handlers | `app/workflows/email_workflow.py`, `app/core/telegram_bot.py`, `app/services/classification.py`, `app/models/workflow_mapping.py` | Gemini API for classification, Telegram Bot API, PostgreSQL checkpointing |
| **Epic 3: RAG & Response Generation** | Vector store, RAG service, response generation, language detection, embedding | `app/core/vector_store.py`, `app/services/rag_service.py`, `app/services/response_generation.py`, `app/tasks/indexing_tasks.py` | ChromaDB for embeddings, Gemini API for generation & embeddings |
| **Epic 4: Configuration UI & Onboarding** | Next.js frontend, onboarding wizard, dashboard, settings management | `frontend/src/app/onboarding/`, `frontend/src/components/`, `frontend/src/lib/api-client.ts` | FastAPI REST API, OAuth redirect handling |

## Technology Stack Details

### Core Technologies

**Backend Runtime:**
- **Python:** 3.13+ (latest stable, async/await support, performance improvements)
- **FastAPI:** 0.120.4 (async web framework, automatic OpenAPI docs, Pydantic v2 validation)
- **LangGraph:** 1.0.2 (agent workflow orchestration, state management, PostgreSQL checkpointing)
- **Celery:** Latest (distributed task queue for background jobs)
- **Redis:** Latest (message broker for Celery, caching layer)

**Database Layer:**
- **PostgreSQL:** 18 (primary database for user data, workflow state, LangGraph checkpoints)
- **ChromaDB:** Latest (vector database for RAG, self-hosted, unlimited free tier)
- **Alembic:** Latest (database migration tool)
- **SQLAlchemy:** 2.x (ORM with async support)

**AI & LLM:**
- **Google Gemini 2.5 Flash:** `gemini-2.5-flash` (text generation, classification, response drafting)
- **Gemini Embeddings:** `text-embedding-004` (vector embeddings for RAG, 1536 dimensions)
- **Langfuse:** Provided by template (LLM observability, token tracking, prompt debugging)

**External APIs:**
- **Gmail API:** Official Google API Python client (OAuth 2.0, email read/write/labels/send)
- **Telegram Bot API:** `python-telegram-bot` library (long polling mode, inline keyboards)

**Frontend:**
- **Next.js:** 15.5 (React framework with App Router, server components, TypeScript)
- **React:** 18.x (UI library)
- **Tailwind CSS:** Latest (utility-first CSS framework)
- **shadcn/ui:** Latest (accessible UI components built on Radix UI)
- **TypeScript:** 5.x (type-safe JavaScript)

**Infrastructure:**
- **Docker:** Containerization for all services
- **Docker Compose:** Local development orchestration
- **Prometheus:** Metrics collection and storage
- **Grafana:** Dashboards for monitoring (API, database, LLM usage)

### Integration Points

**1. Gmail API Integration**
- **Protocol:** REST/gRPC over HTTPS
- **Authentication:** OAuth 2.0 (authorization code flow)
- **Scopes Required:** `gmail.readonly`, `gmail.modify`, `gmail.send`, `gmail.labels`
- **Data Flow:** Bidirectional (read emails, create labels, send emails)
- **Rate Limits:** 10,000 requests/day (free tier) - managed via retry logic with exponential backoff
- **Quota Management Strategy:**
  - Batch operations where possible (read multiple emails in single call)
  - Use Gmail push notifications (Pub/Sub) for future optimization (post-MVP)
  - Cache label IDs to reduce list_labels calls
  - Respect rate limit headers and back off proactively

**2. Telegram Bot API Integration**
- **Protocol:** HTTPS REST API
- **Authentication:** Bot token (stored in environment variable)
- **Mode:** Long polling (getUpdates) for MVP, webhooks for production scaling
- **Data Flow:** Bidirectional (send messages with buttons, receive callback queries)
- **Message Format:**
  - Rich text with Markdown formatting
  - Inline keyboards for approval actions
  - Callback data encoding: `{action}_{email_id}` (e.g., `approve_email_abc123`)
- **Rate Limits:** 30 messages/second per bot - well within requirements

**3. Gemini API Integration**
- **Protocol:** REST API over HTTPS
- **Authentication:** API key (stored in environment variable)
- **Models Used:**
  - `gemini-2.5-flash` for text generation (classification, response drafting)
  - `text-embedding-004` for vector embeddings
- **Data Flow:** Request/response (stateless)
- **Rate Limits:** 1 million tokens/minute (free tier) - effectively unlimited for MVP scale
- **Context Window:** 1 million tokens (massive - entire email history if needed)
- **Multilingual Support:** Native support for Russian, Ukrainian, English, German

**4. ChromaDB Integration**
- **Protocol:** Native Python SDK (embedded or client-server mode)
- **Deployment:** Self-hosted in Docker container
- **Collections:** Single collection `email_embeddings` with metadata
- **Metadata Schema:**
  ```python
  {
      "email_id": str,
      "user_id": str,
      "thread_id": str,
      "sender": str,
      "subject": str,
      "received_at": str (ISO 8601),
      "language": str
  }
  ```
- **Query Strategy:** Semantic similarity search using cosine distance, top-k retrieval (k=5-10)
- **Indexing Strategy:**
  - Initial bulk indexing on user signup (all historical emails)
  - Incremental indexing via Celery task after each new email processed

**5. LangGraph Checkpointing (PostgreSQL)**
- **Protocol:** Internal (SQLAlchemy ORM)
- **Table:** `checkpoints` (managed by LangGraph)
- **Purpose:** Persist workflow state for human-in-the-loop pause/resume
- **Checkpoint Format:** Serialized state dictionary stored as JSON
- **Thread ID Format:** `email_{email_id}_{uuid4()}` - unique per email workflow
- **Cleanup Strategy:** Delete checkpoints after workflow completion (terminal state reached)

## Novel Pattern: TelegramHITLWorkflow

### Pattern Description

**TelegramHITLWorkflow** (Human-In-The-Loop via Telegram) is a novel architectural pattern that enables LangGraph state machine workflows to pause indefinitely at a human approval decision point, wait for user input via Telegram from a completely separate communication channel, and then resume execution exactly where it left off with full context preservation.

### Why This Pattern is Novel

Standard LangGraph examples show synchronous human-in-the-loop patterns (CLI input, web form submission within same session). Mail Agent requires:
1. **Cross-channel resumption:** Workflow pauses in backend, user responds in Telegram app (different device, hours later)
2. **Concurrent multi-user workflows:** Dozens of workflows paused simultaneously (one per email per user)
3. **Callback data → workflow instance mapping:** Telegram button clicks must reconnect to the exact paused workflow
4. **Persistent state across service restarts:** Workflows must survive backend deployments

### Architecture Components

**1. LangGraph State Machine with Checkpointing**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import TypedDict, Literal

class EmailWorkflowState(TypedDict):
    email_id: str
    user_id: str
    thread_id: str
    email_content: str
    sender: str
    subject: str
    rag_context: list[str]
    classification: Literal["sort_only", "needs_response"]
    proposed_folder: str
    draft_response: str | None
    user_decision: Literal["approve", "reject", "edit"] | None
    edited_text: str | None
    final_action: str | None

def create_email_workflow():
    """Create the LangGraph workflow with PostgreSQL checkpointing"""

    # Initialize PostgreSQL checkpointer
    checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)

    workflow = StateGraph(EmailWorkflowState)

    # Define nodes (workflow steps)
    workflow.add_node("extract_context", extract_context_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("draft_response", draft_response_node)
    workflow.add_node("send_telegram", send_telegram_proposal_node)
    workflow.add_node("await_approval", await_approval_node)  # PAUSES HERE
    workflow.add_node("execute_action", execute_action_node)
    workflow.add_node("send_confirmation", send_confirmation_node)

    # Define edges (flow between nodes)
    workflow.set_entry_point("extract_context")
    workflow.add_edge("extract_context", "classify")
    workflow.add_conditional_edges(
        "classify",
        route_by_classification,  # Routes to draft_response or send_telegram
        {
            "needs_response": "draft_response",
            "sort_only": "send_telegram"
        }
    )
    workflow.add_edge("draft_response", "send_telegram")
    workflow.add_edge("send_telegram", "await_approval")

    # CRITICAL: await_approval node returns END → workflow pauses
    # When resumed with user_decision, conditional routing takes over
    workflow.add_conditional_edges(
        "await_approval",
        route_by_user_decision,
        {
            "approved": "execute_action",
            "edited": "execute_action",
            "rejected": "send_confirmation"
        }
    )
    workflow.add_edge("execute_action", "send_confirmation")
    workflow.add_edge("send_confirmation", END)

    # Compile with checkpointer
    return workflow.compile(checkpointer=checkpointer)

# Node implementations
async def await_approval_node(state: EmailWorkflowState) -> EmailWorkflowState:
    """
    This node does NOTHING except return the state.
    The workflow will pause here because the graph reaches END.
    When resumed with user_decision, the conditional edge routes appropriately.
    """
    return state  # State preserved via PostgreSQL checkpoint

async def execute_action_node(state: EmailWorkflowState) -> EmailWorkflowState:
    """Execute the approved action (apply label or send email)"""
    if state["classification"] == "sort_only":
        # Apply Gmail label
        gmail_client.apply_label(state["email_id"], state["proposed_folder"])
    else:
        # Send email response
        response_text = state["edited_text"] or state["draft_response"]
        gmail_client.send_reply(state["email_id"], response_text)

    return {**state, "final_action": "completed"}
```

**2. Workflow Instance Tracker**

```python
from app.models.workflow_mapping import WorkflowMapping
from app.db.session import get_db
from uuid import uuid4

class WorkflowInstanceTracker:
    """Manages the mapping between emails, Telegram messages, and LangGraph thread IDs"""

    @staticmethod
    async def start_workflow(email_id: str, user_id: str, email_data: dict):
        """
        Start a new LangGraph workflow for an email.
        Returns the thread_id for tracking.
        """
        # Generate unique thread ID
        thread_id = f"email_{email_id}_{uuid4()}"

        # Create initial state
        initial_state = EmailWorkflowState(
            email_id=email_id,
            user_id=user_id,
            thread_id=thread_id,
            email_content=email_data["content"],
            sender=email_data["sender"],
            subject=email_data["subject"],
            rag_context=[],
            classification=None,
            proposed_folder=None,
            draft_response=None,
            user_decision=None,
            edited_text=None,
            final_action=None
        )

        # Invoke workflow (will run until await_approval, then pause)
        config = {"configurable": {"thread_id": thread_id}}
        workflow = create_email_workflow()

        # Run asynchronously
        result = await workflow.ainvoke(initial_state, config=config)

        # Store mapping in database
        async with get_db() as db:
            mapping = WorkflowMapping(
                email_id=email_id,
                user_id=user_id,
                thread_id=thread_id,
                telegram_message_id=None,  # Will be set when message sent
                workflow_state="await_approval",
                created_at=datetime.now(timezone.utc)
            )
            db.add(mapping)
            await db.commit()

        return thread_id

    @staticmethod
    async def store_telegram_message(email_id: str, telegram_message_id: str):
        """Update mapping with Telegram message ID after proposal sent"""
        async with get_db() as db:
            mapping = await db.query(WorkflowMapping).filter_by(email_id=email_id).first()
            mapping.telegram_message_id = telegram_message_id
            mapping.updated_at = datetime.now(timezone.utc)
            await db.commit()

    @staticmethod
    async def resume_workflow(email_id: str, user_decision: str, edited_text: str = None):
        """
        Resume a paused workflow with user's decision from Telegram.

        Args:
            email_id: The email being processed
            user_decision: "approve" | "reject" | "edit"
            edited_text: Modified response text if user_decision == "edit"
        """
        # Lookup thread_id from database
        async with get_db() as db:
            mapping = await db.query(WorkflowMapping).filter_by(email_id=email_id).first()
            if not mapping:
                raise ValueError(f"No workflow found for email {email_id}")

            thread_id = mapping.thread_id

        # Resume workflow with user decision
        config = {"configurable": {"thread_id": thread_id}}
        workflow = create_email_workflow()

        # Invoke with user decision - LangGraph loads checkpoint and continues
        resume_state = {
            "user_decision": user_decision,
            "edited_text": edited_text
        }

        result = await workflow.ainvoke(resume_state, config=config)

        # Update mapping to completed
        async with get_db() as db:
            mapping.workflow_state = "completed"
            mapping.updated_at = datetime.now(timezone.utc)
            await db.commit()

        return result
```

**3. Telegram Bot Integration**

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

async def send_telegram_proposal_node(state: EmailWorkflowState) -> EmailWorkflowState:
    """Send proposal message to user in Telegram"""

    # Format message based on classification
    if state["classification"] == "sort_only":
        message_text = f"""
📧 **New Email**

From: {state["sender"]}
Subject: {state["subject"]}

{state["email_content"][:100]}...

**Suggested Folder:** {state["proposed_folder"]}

What would you like to do?
"""
        buttons = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{state['email_id']}")],
            [InlineKeyboardButton("📁 Change Folder", callback_data=f"change_{state['email_id']}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{state['email_id']}")]
        ]
    else:
        message_text = f"""
📧 **Draft Response**

To: {state["sender"]}
Re: {state["subject"]}

**Draft:**
{state["draft_response"]}

What would you like to do?
"""
        buttons = [
            [InlineKeyboardButton("📤 Send", callback_data=f"approve_{state['email_id']}")],
            [InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{state['email_id']}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{state['email_id']}")]
        ]

    keyboard = InlineKeyboardMarkup(buttons)

    # Send message to user
    telegram_bot = get_telegram_bot()
    message = await telegram_bot.send_message(
        chat_id=state["user_id"],
        text=message_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

    # Store Telegram message ID in workflow mapping
    await WorkflowInstanceTracker.store_telegram_message(
        email_id=state["email_id"],
        telegram_message_id=str(message.message_id)
    )

    return state

async def handle_telegram_callback(update: Update, context):
    """Handle button clicks from Telegram"""
    query = update.callback_query
    await query.answer()  # Acknowledge button click

    # Parse callback data: "approve_email_abc123"
    action, email_id = query.data.split("_", 1)

    # Handle edit action specially (requires text input)
    if action == "edit":
        await query.message.reply_text(
            "Please send your edited response text:"
        )
        # Store context for next message
        context.user_data["awaiting_edit_for"] = email_id
        return

    # Resume workflow with user decision
    try:
        await WorkflowInstanceTracker.resume_workflow(
            email_id=email_id,
            user_decision=action  # "approve" or "reject"
        )

        # Confirmation message
        if action == "approve":
            await query.message.reply_text("✅ Action completed successfully!")
        else:
            await query.message.reply_text("❌ Action cancelled.")

    except Exception as e:
        logger.error(f"Error resuming workflow: {e}", extra={"email_id": email_id})
        await query.message.reply_text("❌ Error processing your request. Please try again.")

async def handle_edit_text(update: Update, context):
    """Handle edited response text from user"""
    if "awaiting_edit_for" not in context.user_data:
        return  # Not in edit mode

    email_id = context.user_data["awaiting_edit_for"]
    edited_text = update.message.text

    # Resume workflow with edited text
    await WorkflowInstanceTracker.resume_workflow(
        email_id=email_id,
        user_decision="edit",
        edited_text=edited_text
    )

    await update.message.reply_text("✅ Response sent with your changes!")

    # Clear context
    del context.user_data["awaiting_edit_for"]

# Telegram bot setup
def setup_telegram_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CallbackQueryHandler(handle_telegram_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_text))

    # Start polling
    application.run_polling()
```

**4. Database Schema for Workflow Mapping**

```python
from sqlalchemy import Column, Integer, String, DateTime, Index
from app.db.base import Base

class WorkflowMapping(Base):
    """
    Maps emails to LangGraph workflow instances and Telegram messages.
    Critical for reconnecting Telegram callbacks to paused workflows.
    """
    __tablename__ = "workflow_mappings"

    id = Column(Integer, primary_key=True)
    email_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    thread_id = Column(String, unique=True, nullable=False, index=True)  # LangGraph thread
    telegram_message_id = Column(String, index=True)  # Telegram message with buttons
    workflow_state = Column(String, nullable=False)  # Current state: await_approval, completed, error
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('idx_user_state', 'user_id', 'workflow_state'),  # Query active workflows by user
    )
```

### Integration with Epic 2 & 3

**Epic 2 Stories Affected:**
- **Story 2.6:** Send sorting proposal messages → Implements `send_telegram_proposal_node()`
- **Story 2.7:** Approval button handling → Implements `handle_telegram_callback()`

**Epic 3 Stories Affected:**
- **Story 3.8:** Send response draft messages → Extends `send_telegram_proposal_node()` for responses
- **Story 3.9:** Response editing and sending → Implements `handle_edit_text()`

### Key Implementation Rules for AI Agents

When implementing stories that touch this pattern:

1. **ALWAYS use PostgreSQL checkpointing** when creating LangGraph workflows
2. **ALWAYS create WorkflowMapping entries** before sending Telegram messages
3. **ALWAYS include email_id in Telegram callback data** (format: `{action}_{email_id}`)
4. **ALWAYS lookup thread_id from WorkflowMapping** before resuming workflows
5. **NEVER create new workflow instances** for existing emails (check WorkflowMapping first)
6. **ALWAYS handle workflow errors** with user notifications and error state updates
7. **ALWAYS clean up completed workflows** (delete WorkflowMapping after terminal state)

## Implementation Patterns

### Naming Conventions

**API Endpoints:**
- Format: `/api/v1/{resource}/{action}`
- Plural resource names: `/api/v1/emails/`, `/api/v1/folders/`, `/api/v1/users/`
- Route parameters: `{id}` not `:id` → `/api/v1/emails/{email_id}/thread`
- Example: `GET /api/v1/emails/{email_id}`, `POST /api/v1/folders/`, `PUT /api/v1/settings/notifications`

**Database Tables:**
- Lowercase with underscores: `email_processing_queue`, `folder_categories`, `approval_history`
- Plural for entity tables: `users`, `emails`, `folders`
- Singular for junction/mapping tables: `workflow_mapping`, `user_folder_assignment`

**Database Columns:**
- snake_case: `user_id`, `created_at`, `gmail_message_id`, `telegram_chat_id`
- Foreign keys: `{table_singular}_id` → `user_id`, `email_id`, `folder_id`
- Timestamps: `created_at`, `updated_at` (MANDATORY on all tables)
- Boolean flags: `is_active`, `has_response`, `needs_approval`

**Python Code:**
- **Files:** snake_case → `email_workflow.py`, `gmail_client.py`, `rag_service.py`
- **Classes:** PascalCase → `EmailWorkflowState`, `GmailClient`, `RAGService`
- **Functions/methods:** snake_case → `extract_context()`, `send_telegram_message()`, `classify_email()`
- **Constants:** UPPER_SNAKE_CASE → `MAX_RETRIES = 3`, `DEFAULT_BATCH_SIZE = 10`, `GMAIL_SCOPES = [...]`
- **Private methods:** Leading underscore → `_validate_token()`, `_parse_email_body()`

**Frontend (TypeScript/React):**
- **Files:** kebab-case → `email-preview.tsx`, `onboarding-wizard.tsx`, `folder-settings.tsx`
- **Components:** PascalCase → `EmailPreview`, `OnboardingWizard`, `FolderSettings`
- **Functions:** camelCase → `fetchUserData()`, `handleApproval()`, `validateEmailFormat()`
- **Types/Interfaces:** PascalCase → `UserSettings`, `EmailData`, `TelegramMessage`
- **Constants:** UPPER_SNAKE_CASE → `API_BASE_URL`, `MAX_EMAIL_PREVIEW_LENGTH`

### Code Organization

**Import Order (Python):**
```python
# 1. Standard library imports
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict

# 2. Third-party imports
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from telegram import Update, InlineKeyboardButton

# 3. Local application imports
from app.core.gmail_client import GmailClient
from app.models.user import User
from app.workflows.email_workflow import create_email_workflow
from app.utils.logger import logger
```

**Test File Organization:**
- Mirror source structure: `app/services/classification.py` → `tests/unit/services/test_classification.py`
- Test class per source class: `class TestClassificationService`
- Test method naming: `test_{method_name}_{scenario}` → `test_classify_email_government_sender()`

**Configuration Files:**
- Root level: `.env`, `docker-compose.yml`, `requirements.txt`, `README.md`
- Service-specific: `backend/.env.example`, `frontend/.env.local`, `backend/alembic.ini`

### Error Handling

**Error Response Format:**
```python
{
    "success": False,
    "error": {
        "code": "GMAIL_API_QUOTA_EXCEEDED",
        "message": "Gmail API quota exceeded. Daily limit of 10,000 requests reached.",
        "user_message": "We're processing a lot of emails right now. Please try again in a few hours.",
        "retry_after": 3600,  # Seconds until retry (optional)
        "context": {
            "user_id": "user_123",
            "email_id": "email_abc",
            "quota_reset_at": "2025-11-04T00:00:00Z"
        }
    }
}
```

**Error Code Categories:**
- `GMAIL_*` - Gmail API errors (GMAIL_AUTH_FAILED, GMAIL_API_QUOTA_EXCEEDED, GMAIL_NETWORK_ERROR)
- `TELEGRAM_*` - Telegram Bot API errors (TELEGRAM_SEND_FAILED, TELEGRAM_INVALID_CHAT_ID)
- `LLM_*` - Gemini API errors (LLM_RATE_LIMIT, LLM_TIMEOUT, LLM_INVALID_RESPONSE)
- `RAG_*` - Vector DB errors (RAG_CONNECTION_FAILED, RAG_QUERY_ERROR, RAG_INDEX_FAILED)
- `VALIDATION_*` - Input validation (VALIDATION_MISSING_FIELD, VALIDATION_INVALID_FORMAT)
- `AUTH_*` - Authentication/authorization (AUTH_TOKEN_EXPIRED, AUTH_UNAUTHORIZED)
- `WORKFLOW_*` - LangGraph errors (WORKFLOW_STATE_INVALID, WORKFLOW_RESUME_FAILED)

**Retry Strategy:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((NetworkError, RateLimitError))
)
async def call_gmail_api(operation: str, *args, **kwargs):
    """
    Retry transient Gmail API errors with exponential backoff.
    Auth errors are NOT retried (fail immediately).
    """
    try:
        return await gmail_client.execute(operation, *args, **kwargs)
    except AuthenticationError:
        logger.error("Gmail auth failed - notify user to reconnect")
        raise  # Don't retry auth errors
    except QuotaExceededError as e:
        logger.warn("Gmail quota exceeded", extra={"reset_at": e.reset_time})
        raise  # Retry via decorator
```

**Error Logging:**
```python
logger.error(
    "Gmail API call failed",
    extra={
        "error_code": "GMAIL_API_QUOTA_EXCEEDED",
        "user_id": user_id,
        "operation": "send_email",
        "retry_attempt": 2,
        "quota_reset_at": "2025-11-04T00:00:00Z"
    },
    exc_info=True  # Include stack trace
)
```

### Logging Strategy

**Structured JSON Format:**
```python
{
    "timestamp": "2025-11-03T10:15:30.123456Z",
    "level": "INFO",
    "service": "email_processor",
    "user_id": "user_123",
    "email_id": "email_abc",
    "thread_id": "email_abc_uuid",
    "workflow_state": "ClassifyEmail",
    "message": "Email classified successfully",
    "duration_ms": 245,
    "metadata": {
        "classification": "needs_response",
        "confidence": 0.92,
        "language": "de"
    }
}
```

**Log Levels:**
- `DEBUG` - Development only (detailed state transitions, variable values) - NOT in production
- `INFO` - Normal operations (email processed, user approved, workflow completed)
- `WARN` - Recoverable issues (retry after rate limit, temporary network error)
- `ERROR` - Failures requiring attention (persistent API errors, unexpected exceptions)
- `CRITICAL` - System-wide issues (database down, service crash, data corruption)

**Sensitive Data Rules:**
- ❌ **NEVER log email body content** (full text, preview beyond 50 chars for debugging)
- ❌ **NEVER log OAuth tokens, refresh tokens, or API keys**
- ❌ **NEVER log passwords or authentication credentials**
- ❌ **NEVER log Telegram chat IDs in public logs** (GDPR concern)
- ✅ **DO log email metadata** (sender, subject, message_id, thread_id, timestamp)
- ✅ **DO log user actions** (approved, rejected, edited, skipped)
- ✅ **DO log LLM token usage** for monitoring free tier limits
- ✅ **DO log performance metrics** (duration, latency, throughput)
- ✅ **DO log workflow state transitions** for debugging

**Logger Configuration:**
```python
import logging
import json
from datetime import datetime, timezone

class StructuredLogger:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)

    def _format_log(self, level: str, message: str, **kwargs):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "service": self.service_name,
            "message": message,
            **kwargs  # Additional context
        }
        return json.dumps(log_entry)

    def info(self, message: str, **kwargs):
        self.logger.info(self._format_log("INFO", message, **kwargs))

    def error(self, message: str, **kwargs):
        self.logger.error(self._format_log("ERROR", message, **kwargs))

# Usage
logger = StructuredLogger("email_processor")
logger.info(
    "Email classified",
    user_id="user_123",
    email_id="email_abc",
    classification="needs_response",
    duration_ms=245
)
```

## Data Architecture

### Database Models

**Users Table:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    gmail_oauth_token TEXT,  -- Encrypted
    gmail_refresh_token TEXT,  -- Encrypted
    telegram_id VARCHAR(100) UNIQUE,
    telegram_username VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
```

**FolderCategories Table:**
```sql
CREATE TABLE folder_categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    gmail_label_id VARCHAR(100),  -- Gmail's internal label ID
    keywords TEXT[],  -- Array of keywords for classification hints
    color VARCHAR(7),  -- Hex color code for UI
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(user_id, name)
);
CREATE INDEX idx_folder_categories_user_id ON folder_categories(user_id);
```

**EmailProcessingQueue Table:**
```sql
CREATE TABLE email_processing_queue (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gmail_message_id VARCHAR(255) UNIQUE NOT NULL,
    gmail_thread_id VARCHAR(255) NOT NULL,
    sender VARCHAR(255) NOT NULL,
    subject TEXT,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL,  -- pending, processing, awaiting_approval, completed, rejected, error
    classification VARCHAR(50),  -- sort_only, needs_response
    proposed_folder_id INTEGER REFERENCES folder_categories(id),
    draft_response TEXT,
    language VARCHAR(10),  -- ru, uk, en, de
    priority_score INTEGER DEFAULT 0,  -- 0-100
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_email_queue_user_status ON email_processing_queue(user_id, status);
CREATE INDEX idx_email_queue_gmail_message_id ON email_processing_queue(gmail_message_id);
```

**WorkflowMapping Table** (Novel Pattern):
```sql
CREATE TABLE workflow_mappings (
    id SERIAL PRIMARY KEY,
    email_id VARCHAR(255) UNIQUE NOT NULL REFERENCES email_processing_queue(gmail_message_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id VARCHAR(255) UNIQUE NOT NULL,  -- LangGraph thread ID
    telegram_message_id VARCHAR(100),  -- Telegram message with approval buttons
    workflow_state VARCHAR(50) NOT NULL,  -- await_approval, completed, error
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_workflow_mappings_thread_id ON workflow_mappings(thread_id);
CREATE INDEX idx_workflow_mappings_user_state ON workflow_mappings(user_id, workflow_state);
```

**ApprovalHistory Table:**
```sql
CREATE TABLE approval_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email_queue_id INTEGER NOT NULL REFERENCES email_processing_queue(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,  -- sort, send_response
    ai_suggested_folder_id INTEGER REFERENCES folder_categories(id),
    user_selected_folder_id INTEGER REFERENCES folder_categories(id),
    approved BOOLEAN NOT NULL,
    user_edited BOOLEAN DEFAULT FALSE,  -- Did user modify AI draft?
    response_length INTEGER,  -- Characters in final response (for analytics)
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE INDEX idx_approval_history_user_id ON approval_history(user_id);
CREATE INDEX idx_approval_history_timestamp ON approval_history(timestamp);
```

**NotificationPreferences Table:**
```sql
CREATE TABLE notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    batch_enabled BOOLEAN DEFAULT TRUE,
    batch_time VARCHAR(5) DEFAULT '18:00',  -- HH:MM format
    priority_immediate BOOLEAN DEFAULT TRUE,
    quiet_hours_start VARCHAR(5),  -- HH:MM format
    quiet_hours_end VARCHAR(5),
    timezone VARCHAR(50) DEFAULT 'Europe/Berlin',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### Data Relationships

```
users (1) ──────────┬─────────> (N) folder_categories
                    │
                    ├─────────> (N) email_processing_queue
                    │
                    ├─────────> (N) workflow_mappings
                    │
                    ├─────────> (N) approval_history
                    │
                    └─────────> (1) notification_preferences

folder_categories (1) ─────────> (N) email_processing_queue (proposed_folder_id)
                      └─────────> (N) approval_history (ai_suggested, user_selected)

email_processing_queue (1) ────> (1) workflow_mappings
                           └────> (N) approval_history
```

### ChromaDB Vector Storage Schema

**Collection:** `email_embeddings`

**Document Structure:**
```python
{
    "id": "email_abc123",  # email_id
    "embedding": [0.123, -0.456, ...],  # 1536-dimensional vector
    "metadata": {
        "email_id": "email_abc123",
        "user_id": "user_123",
        "thread_id": "thread_xyz789",
        "sender": "sender@example.com",
        "subject": "Email subject",
        "received_at": "2025-11-03T10:15:30Z",
        "language": "de"
    },
    "document": "First 500 chars of email body for debugging"
}
```

**Indexing Strategy:**
- **Initial Indexing:** Bulk index all historical emails on user signup (Celery task)
- **Incremental Indexing:** Index new emails after classification (triggered by workflow)
- **Update Strategy:** Emails are immutable - no updates needed
- **Deletion Strategy:** User deletion triggers cascade delete of all embeddings

**Query Pattern:**
```python
# Semantic search for context retrieval
results = chroma_collection.query(
    query_embeddings=[email_embedding],
    n_results=10,
    where={"user_id": user_id},  # Multi-tenant filtering
    include=["metadatas", "documents", "distances"]
)
```

## API Contracts

### Authentication Endpoints

**POST /api/v1/auth/gmail/login**
- **Purpose:** Initiate Gmail OAuth 2.0 flow
- **Request:** `{}`
- **Response:** `{"success": true, "data": {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."}}`
- **Redirects user to Google consent screen**

**GET /api/v1/auth/gmail/callback**
- **Purpose:** Handle OAuth redirect with authorization code
- **Query Params:** `code`, `state`
- **Response:** `{"success": true, "data": {"user_id": "user_123", "email": "user@gmail.com"}}`
- **Sets session cookie or JWT token**

### Telegram Endpoints

**POST /api/v1/telegram/generate-code**
- **Purpose:** Generate unique 6-digit linking code
- **Authentication:** Required (JWT)
- **Request:** `{}`
- **Response:** `{"success": true, "data": {"code": "A7X9K2", "expires_at": "2025-11-03T10:30:00Z"}}`

**POST /api/v1/telegram/verify-link**
- **Purpose:** Verify Telegram account linked successfully
- **Authentication:** Required
- **Request:** `{}`
- **Response:** `{"success": true, "data": {"linked": true, "telegram_username": "@username"}}`

### Folder Management Endpoints

**GET /api/v1/folders/**
- **Purpose:** List user's folder categories
- **Authentication:** Required
- **Response:**
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "name": "Government",
            "color": "#FF5733",
            "keywords": ["finanzamt", "ausländerbehörde"],
            "is_default": false
        }
    ]
}
```

**POST /api/v1/folders/**
- **Purpose:** Create new folder category
- **Authentication:** Required
- **Request:** `{"name": "Clients", "keywords": ["client", "project"], "color": "#3498DB"}`
- **Response:** `{"success": true, "data": {"id": 2, "name": "Clients", "gmail_label_id": "Label_123"}}`

**PUT /api/v1/folders/{folder_id}**
- **Purpose:** Update folder category
- **Authentication:** Required
- **Request:** `{"name": "Important Clients", "keywords": ["vip", "urgent"]}`
- **Response:** `{"success": true, "data": {...}}`

**DELETE /api/v1/folders/{folder_id}**
- **Purpose:** Delete folder category
- **Authentication:** Required
- **Response:** `{"success": true}`

### Settings Endpoints

**GET /api/v1/settings/notifications**
- **Purpose:** Get notification preferences
- **Authentication:** Required
- **Response:**
```json
{
    "success": true,
    "data": {
        "batch_enabled": true,
        "batch_time": "18:00",
        "priority_immediate": true,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "08:00",
        "timezone": "Europe/Berlin"
    }
}
```

**PUT /api/v1/settings/notifications**
- **Purpose:** Update notification preferences
- **Authentication:** Required
- **Request:** `{"batch_enabled": false, "priority_immediate": true}`
- **Response:** `{"success": true, "data": {...}}`

### Email Processing Endpoints (Internal/Admin)

**GET /api/v1/emails/queue**
- **Purpose:** Get user's email processing queue status
- **Authentication:** Required
- **Query Params:** `status` (optional filter)
- **Response:**
```json
{
    "success": true,
    "data": {
        "pending": 3,
        "awaiting_approval": 5,
        "completed_today": 12,
        "emails": [...]
    }
}
```

### Response Format Standards

**Success Response:**
```json
{
    "success": true,
    "data": { ... },
    "metadata": {
        "timestamp": "2025-11-03T10:15:30Z",
        "request_id": "req_abc123"
    }
}
```

**Error Response:**
```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Technical error message for developers",
        "user_message": "User-friendly error message",
        "details": { ... }
    }
}
```

**Pagination (for list endpoints):**
```json
{
    "success": true,
    "data": [...],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 45,
        "total_pages": 3
    }
}
```

## Security Architecture

### Authentication & Authorization

**OAuth 2.0 Flow (Gmail):**
1. User clicks "Connect Gmail" → Redirect to Google consent screen
2. User grants permissions → Google redirects to `/api/v1/auth/gmail/callback?code=...`
3. Backend exchanges code for access token + refresh token
4. Tokens encrypted (Fernet encryption) and stored in PostgreSQL
5. JWT issued to user for API access

**Token Management:**
- **Access tokens:** Stored encrypted in database, decrypted on use
- **Refresh tokens:** Automatically used when access token expires
- **JWT tokens:** HS256 algorithm, 24-hour expiration, stored in HTTP-only cookie
- **Token rotation:** Refresh tokens rotated on each use (OAuth 2.1 best practice)

**Session Management:**
- JWT-based stateless authentication
- Session data stored in Redis for fast lookups (user_id → preferences)
- Session timeout: 24 hours
- Refresh token: 30 days
- Logout: Blacklist JWT in Redis until expiration

### Data Encryption

**At Rest:**
- OAuth tokens: Fernet encryption (symmetric) with key stored in environment variable
- Database: PostgreSQL TLS connections enforced
- Backups: Encrypted with AES-256

**In Transit:**
- HTTPS/TLS 1.3 for all external communications
- Gmail API: TLS enforced by Google
- Telegram API: TLS enforced by Telegram
- Internal services: TLS in production, plaintext allowed in dev

### Multi-Tenancy & Data Isolation

**Database Level:**
- All queries MUST filter by `user_id`: `WHERE user_id = :current_user_id`
- Foreign key constraints enforce referential integrity
- No shared data between users (each user has isolated folders, emails, history)

**Vector Database Level:**
- ChromaDB metadata filtering: `where={"user_id": user_id}`
- No cross-user queries possible

**API Level:**
- JWT contains `user_id` claim
- Every endpoint validates JWT and extracts `user_id`
- Authorization middleware rejects requests for other users' resources

### GDPR Compliance

**Data Subject Rights:**
- **Right to Access:** API endpoint to export all user data (JSON format)
- **Right to Deletion:** Cascade delete on `users` table removes all associated data
- **Right to Rectification:** User can update all settings via UI

**Data Minimization:**
- Email body content NOT stored in database (only in vector embeddings)
- Embeddings are anonymized (no PII in metadata beyond email_id)
- Logs rotated after 30 days

**Consent:**
- OAuth consent screen explains data access requirements
- User explicitly grants Gmail permissions (read, write, labels, send)

**Data Retention:**
- Active users: Data retained indefinitely (or until user deletes account)
- Inactive users (>1 year): Email sent with account deletion warning
- Deleted users: All data purged within 48 hours (GDPR 72-hour requirement)

### Rate Limiting

**API Endpoints:**
- 100 requests/minute per user (token bucket algorithm via Redis)
- 1000 requests/hour per user
- Admin endpoints: 10 requests/minute

**External APIs:**
- Gmail: Managed via exponential backoff + respect rate limit headers
- Telegram: 30 messages/second (enforced by Telegram) - well above needs
- Gemini: 1M tokens/minute (free tier) - effectively unlimited

### Input Validation

**API Validation (Pydantic):**
```python
from pydantic import BaseModel, EmailStr, Field

class CreateFolderRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    keywords: list[str] = Field(default=[], max_items=20)
    color: str = Field(..., regex=r'^#[0-9A-Fa-f]{6}$')

# FastAPI automatically validates against schema
@router.post("/folders/")
async def create_folder(request: CreateFolderRequest, user_id: str = Depends(get_current_user)):
    ...
```

**SQL Injection Prevention:**
- SQLAlchemy ORM parameterized queries (no raw SQL with string interpolation)
- Input validation via Pydantic before database queries

**XSS Prevention:**
- Frontend: React auto-escapes all user-provided content
- API responses: JSON format prevents script injection
- Telegram messages: Markdown parsing sanitized by telegram library

## Performance Considerations

### NFR001: Email Processing Latency (<2 minutes)

**Target:** Email receipt → Telegram notification < 2 minutes

**Breakdown:**
- Gmail polling interval: 2 minutes (configurable)
- Email fetch from Gmail: ~200-500ms per email
- LangGraph workflow execution:
  - Extract context (RAG query): ~1-3 seconds (ChromaDB semantic search)
  - Classify email (Gemini API): ~500-1000ms
  - Draft response (if needed): ~1-2 seconds
- Send Telegram message: ~100-300ms
- **Total:** ~5-10 seconds per email (well under 2 minute requirement)

**Optimizations:**
- Batch polling: Fetch multiple new emails in single API call
- Parallel workflow execution: Process multiple emails concurrently (Celery workers)
- ChromaDB indexing: Pre-compute embeddings asynchronously

### NFR001: RAG Context Retrieval (<3 seconds)

**Target:** Semantic search + context formatting < 3 seconds

**Current Architecture:**
- ChromaDB semantic search: ~500-1500ms (10 results from 10K+ vectors)
- Gmail thread fetch: ~200-500ms (if thread history needed)
- Context formatting: ~100ms
- **Total:** ~1-2 seconds (meets requirement)

**Scaling Optimizations:**
- ChromaDB in-memory mode for hot data
- Index optimization: HNSW algorithm (default in ChromaDB)
- Limit result set: Top-10 most relevant emails (configurable)

### Database Query Optimization

**Indexes:**
- All foreign keys indexed: `user_id`, `folder_id`, `email_queue_id`
- Composite indexes for common queries: `(user_id, status)`, `(user_id, workflow_state)`
- Unique indexes on natural keys: `email`, `gmail_message_id`, `thread_id`

**Query Patterns:**
- Avoid N+1 queries: Use `joinedload()` for relationships
- Pagination for list endpoints: `LIMIT` + `OFFSET` with total count
- Connection pooling: SQLAlchemy async pool (size=20, max_overflow=10)

### Caching Strategy

**Redis Cache:**
- User preferences: 5-minute TTL (updated on settings change)
- Gmail label list: 1-hour TTL (rarely changes)
- Telegram bot instance: No expiration (singleton)

**Application Cache:**
- LangGraph workflows: In-memory (lifecycle tied to workflow completion)
- Gemini API client: Singleton (reuse HTTP connection pool)

### Background Task Optimization

**Celery Workers:**
- 2 workers per CPU core (I/O bound tasks)
- Task priorities: `high` (priority emails), `normal` (regular emails), `low` (RAG indexing)
- Task timeout: 5 minutes (safety net)

**Email Polling:**
- Configurable interval (default 2 minutes)
- Staggered start times for multiple users (avoid thundering herd)
- Batch size: 50 emails per poll (Gmail API limit)

**RAG Indexing:**
- Initial bulk indexing: 100 emails per batch (rate-limited to avoid overwhelming ChromaDB)
- Incremental indexing: Real-time after email processed
- Retry failed embeddings: Exponential backoff up to 24 hours

## Deployment Architecture

### Production Environment

**Services:**
1. **Backend (FastAPI + LangGraph):** Docker container on Railway/Render free tier
2. **Frontend (Next.js):** Deployed on Vercel free tier
3. **PostgreSQL:** Managed service (Supabase free tier or Railway)
4. **Redis:** Managed service (Upstash free tier or Railway)
5. **ChromaDB:** Self-hosted in Docker on Railway/Render

**Docker Compose (Production):**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - GMAIL_CLIENT_ID=${GMAIL_CLIENT_ID}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - postgres
      - redis
      - chromadb

  celery_worker:
    build: ./backend
    command: celery -A app.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis

  celery_beat:
    build: ./backend
    command: celery -A app.tasks beat --loglevel=info
    environment:
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis

  postgres:
    image: postgres:18-alpine
    environment:
      - POSTGRES_USER=mailagent
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=mailagent
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/chroma

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}

volumes:
  postgres_data:
  chromadb_data:
```

### Monitoring & Observability

**Prometheus Metrics:**
- API latency (p50, p95, p99)
- Request rate & error rate
- Celery task queue depth
- Database connection pool usage
- Gmail API quota usage
- Gemini API token usage
- ChromaDB query latency

**Grafana Dashboards:**
- API Performance (request rate, latency, errors)
- Email Processing Pipeline (emails polled, classified, approved, sent)
- LLM Usage (tokens consumed, cost estimation)
- Database Performance (query time, connection pool)
- Celery Workers (active tasks, queue depth)

**Langfuse (LLM Observability):**
- Prompt tracking (classification prompts, response prompts)
- Token usage per user/per day
- LLM latency tracking
- Error rate for LLM calls

**Health Checks:**
- `/health` - Basic service health
- `/health/db` - Database connectivity
- `/health/redis` - Redis connectivity
- `/health/gmail` - Gmail API reachability
- `/health/telegram` - Telegram API reachability

### CI/CD Pipeline

**GitHub Actions (Backend):**
```yaml
name: Backend CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=app
      - run: black --check app/
      - run: ruff check app/

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Railway
        run: railway up --service backend
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

**GitHub Actions (Frontend):**
```yaml
name: Frontend CI/CD

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - run: npm ci
      - run: npm run lint
      - run: npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
```

### Scaling Path (Post-MVP)

**1-100 Users (Current Architecture):**
- Single backend instance
- 2 Celery workers
- PostgreSQL free tier (10GB storage)
- ChromaDB single instance (~1M vectors)

**100-1,000 Users:**
- Horizontal scaling: 3 backend instances (load balancer)
- 5 Celery workers
- PostgreSQL upgrade (100GB, connection pooling)
- ChromaDB: Upgrade to Pinecone free tier or managed Weaviate

**1,000-10,000 Users:**
- Kubernetes deployment (auto-scaling)
- 20+ Celery workers
- PostgreSQL read replicas
- Pinecone paid tier or Weaviate cluster
- Migrate Gemini to paid tier (predictable costs)

## Development Environment

### Prerequisites

**Required:**
- Python 3.13+ (`python --version`)
- Node.js 20+ and npm (`node --version`)
- Docker and Docker Compose (`docker --version`)
- Git (`git --version`)

**Recommended:**
- VS Code with Python extension
- Postman or HTTPie (API testing)
- pgAdmin or DBeaver (database management)

### Setup Commands

**Backend Setup:**
```bash
# Clone template
git clone https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template mail-agent-backend
cd mail-agent-backend

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials:
# - DATABASE_URL=postgresql://user:pass@localhost:5432/mailagent
# - REDIS_URL=redis://localhost:6379
# - GMAIL_CLIENT_ID=...
# - GMAIL_CLIENT_SECRET=...
# - TELEGRAM_BOT_TOKEN=...
# - GEMINI_API_KEY=...

# Start infrastructure services
docker-compose up -d postgres redis chromadb

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In separate terminal: Start Celery worker
celery -A app.tasks worker --loglevel=info

# In separate terminal: Start Celery beat scheduler
celery -A app.tasks beat --loglevel=info
```

**Frontend Setup:**
```bash
# Create Next.js project
npx create-next-app@latest mail-agent-ui --typescript --tailwind --eslint --app --src-dir
cd mail-agent-ui

# Initialize shadcn/ui
npx shadcn@latest init
# Select: Default style, Zinc, CSS variables: yes

# Install dependencies
npm install axios date-fns @tanstack/react-query

# Configure environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
# Frontend available at http://localhost:3000
```

**Verify Setup:**
```bash
# Backend health check
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Database connection
curl http://localhost:8000/health/db
# Expected: {"status": "connected"}

# Frontend
open http://localhost:3000
# Should show landing page
```

**Testing:**
```bash
# Backend tests
cd mail-agent-backend
pytest tests/ --cov=app --cov-report=html
# Coverage report: htmlcov/index.html

# Frontend tests
cd mail-agent-ui
npm run test
npm run test:coverage
```

## Architecture Decision Records (ADRs)

### ADR-001: LangGraph over LangChain for Agent Orchestration

**Status:** Accepted

**Context:** Need state machine-based workflow orchestration for email processing with human-in-the-loop approval pattern.

**Decision:** Use LangGraph 1.0 as the agent framework instead of LangChain.

**Rationale:**
- LangGraph provides built-in state management via TypedDict
- PostgreSQL checkpointing enables workflow pause/resume (critical for Telegram approval)
- More explicit control flow vs. LangChain's callback-based approach
- Better suited for complex multi-step workflows with conditional branching

**Consequences:**
- Steeper learning curve (LangGraph newer, less documentation)
- Excellent fit for human-in-the-loop pattern
- Easier to debug (explicit state transitions)

### ADR-002: Google Gemini over Grok/GPT-4 for LLM

**Status:** Accepted

**Context:** Need free-tier LLM for email classification and response generation.

**Decision:** Use Google Gemini 2.5 Flash instead of Grok (as specified in original PRD).

**Rationale:**
- Grok has NO true free tier (requires payment)
- Gemini offers 1M tokens/minute FREE (effectively unlimited)
- Excellent multilingual support (Russian, Ukrainian, German, English)
- Fast inference (<2 seconds for most operations)
- Easy migration path to other LLMs (abstracted via LLMClient)

**Consequences:**
- Deviation from original PRD (Grok assumption was incorrect)
- Zero-cost goal maintained
- Risk: Google may introduce limits in future (mitigation: provider abstraction)

### ADR-003: ChromaDB over Pinecone for Vector Database

**Status:** Accepted

**Context:** Need vector database for RAG system with 10,000 user target scale.

**Decision:** Use self-hosted ChromaDB for MVP, design for easy migration to Pinecone later.

**Rationale:**
- ChromaDB is completely free (self-hosted)
- Pinecone free tier limited to 100K vectors (~100 users)
- MVP can run on free tier with ChromaDB
- Architecture designed for easy swap (VectorStore abstraction)

**Consequences:**
- Infrastructure overhead (manage ChromaDB deployment)
- Scaling challenge at 1000+ users (requires migration or optimization)
- Clear migration path documented

### ADR-004: Polling over Gmail Push Notifications (MVP)

**Status:** Accepted

**Context:** Need to detect new Gmail emails for processing.

**Decision:** Use polling (every 2 minutes) for MVP, defer Gmail Pub/Sub webhooks to post-MVP.

**Rationale:**
- Polling is simpler to implement and test
- No need for public webhook endpoint during development
- 2-minute latency acceptable per NFR001
- Gmail quota manageable (720 requests/day/user well under 10K limit)

**Consequences:**
- Slight latency (~2 minutes max)
- More API calls (but within quota)
- Easy to upgrade to webhooks later (same GmailClient interface)

### ADR-005: Telegram Long Polling over Webhooks (MVP)

**Status:** Accepted

**Context:** Need to receive user approval responses from Telegram.

**Decision:** Use long polling for MVP, webhooks for production scaling.

**Rationale:**
- Long polling works locally (no public endpoint needed)
- Simpler to debug and test during development
- Telegram API handles the polling complexity
- Webhooks require HTTPS endpoint (adds deployment complexity)

**Consequences:**
- Slightly higher latency (polling interval ~1 second)
- More network traffic (constant polling)
- Easy migration to webhooks in production

### ADR-006: FastAPI Template as Foundation

**Status:** Accepted

**Context:** Need production-ready FastAPI + LangGraph foundation.

**Decision:** Use `wassim249/fastapi-langgraph-agent-production-ready-template` as starting point.

**Rationale:**
- Provides 80% of infrastructure needs (FastAPI, LangGraph, PostgreSQL, monitoring)
- Production-grade patterns (JWT auth, rate limiting, structured logging)
- Prometheus + Grafana + Langfuse pre-configured
- Docker Compose ready
- Saves ~20-30 hours of setup time

**Consequences:**
- Template-specific patterns must be learned
- Need to customize for Gmail/Telegram integrations
- Excellent foundation for all 40 stories

### ADR-007: Novel TelegramHITLWorkflow Pattern

**Status:** Accepted

**Context:** Need to pause LangGraph workflows for Telegram approval and resume from different channel.

**Decision:** Implement custom TelegramHITLWorkflow pattern with PostgreSQL checkpointing and WorkflowMapping table.

**Rationale:**
- No standard solution exists for cross-channel workflow resumption
- PostgreSQL checkpointing provides reliable state persistence
- WorkflowMapping table enables Telegram callback → workflow reconnection
- Pattern is reusable for future human-in-the-loop scenarios

**Consequences:**
- Custom pattern increases complexity
- Requires careful implementation in Stories 2.6, 2.7, 3.8, 3.9
- Provides unique architectural value (demonstrable in portfolio)

---

_Generated by BMAD Decision Architecture Workflow v1.3.2_

_Date: 2025-11-03_

_For: Dimcheg_

_Architecture Document Complete - Ready for Implementation Phase_
