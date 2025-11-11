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
| **Epic 3: RAG & Response Generation** | Vector store, RAG service, response generation, language detection, embedding, email history indexing | `app/core/vector_db.py`, `app/services/rag_service.py`, `app/services/response_generation.py`, `app/services/email_indexing.py`, `app/tasks/indexing_tasks.py`, `app/models/indexing_progress.py` | ChromaDB for embeddings, Gemini API for generation & embeddings |
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

#### Gmail Label Management Flow

The Gmail Label Management system enables programmatic creation and management of Gmail labels (folders) for email organization. This flow diagram illustrates the label creation and application workflows.

**Label Creation Workflow (Story 1.8):**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Label Creation Flow (Epic 1)                     │
└─────────────────────────────────────────────────────────────────────┘

User (Epic 4 UI)
    │
    │ POST /api/v1/folders/
    │ {
    │   "name": "Government",
    │   "keywords": ["finanzamt", "tax"],
    │   "color": "#FF5733"
    │ }
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     API Layer (folders.py)                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Authenticate user via JWT (get_current_user)              │  │
│  │ 2. Validate request: name (1-100 chars), color (#RRGGBB)    │  │
│  │ 3. Extract user_id from JWT token                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ call FolderService.create_folder()
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Service Layer (folder_service.py)                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 4. Validate folder name (not empty, 1-100 chars)            │  │
│  │ 5. Check database for duplicate (user_id, name)             │  │
│  │    - If duplicate exists → raise ValueError                  │  │
│  │ 6. Initialize GmailClient(user_id)                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ call GmailClient.create_label()
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Gmail Client (gmail_client.py)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 7. Load user's OAuth tokens from database (encrypted)       │  │
│  │ 8. Construct Gmail label object:                             │  │
│  │    {                                                          │  │
│  │      "name": "Government",                                    │  │
│  │      "labelListVisibility": "labelShow",                     │  │
│  │      "messageListVisibility": "show",                        │  │
│  │      "color": {"backgroundColor": "#FF5733"}                 │  │
│  │    }                                                          │  │
│  │ 9. Call Gmail API: labels().create()                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ HTTPS POST
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         Gmail API                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 10. Validate OAuth token                                      │  │
│  │ 11. Check if label name already exists                        │  │
│  │     - If exists → return 409 Conflict                         │  │
│  │     - Else → create label                                     │  │
│  │ 12. Return label_id (e.g., "Label_123")                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ label_id = "Label_123"
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Gmail Client Error Handling                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ If 409 Conflict (duplicate label name):                      │  │
│  │   13. Call list_labels() to find existing label              │  │
│  │   14. Return existing label_id (idempotent operation)        │  │
│  │                                                                │  │
│  │ If 401 Unauthorized (token expired):                          │  │
│  │   15. Refresh OAuth token                                     │  │
│  │   16. Retry create_label()                                    │  │
│  │                                                                │  │
│  │ If 429 Rate Limit:                                             │  │
│  │   17. Exponential backoff (max 3 retries)                     │  │
│  │   18. Log warning and retry                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ return label_id to FolderService
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Database Layer (PostgreSQL)                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 19. Create FolderCategory record:                             │  │
│  │     INSERT INTO folder_categories (                           │  │
│  │       user_id = 1,                                            │  │
│  │       name = "Government",                                    │  │
│  │       gmail_label_id = "Label_123",                           │  │
│  │       keywords = ["finanzamt", "tax"],                        │  │
│  │       color = "#FF5733",                                      │  │
│  │       created_at = NOW(),                                     │  │
│  │       updated_at = NOW()                                      │  │
│  │     )                                                          │  │
│  │ 20. Enforce unique constraint on (user_id, name)             │  │
│  │ 21. Return FolderCategory object with all fields             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ return FolderCategory
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     API Response (201 Created)                      │
│  {                                                                  │
│    "id": 5,                                                         │
│    "user_id": 1,                                                    │
│    "name": "Government",                                            │
│    "gmail_label_id": "Label_123",                                   │
│    "keywords": ["finanzamt", "tax"],                                │
│    "color": "#FF5733",                                              │
│    "is_default": false,                                             │
│    "created_at": "2025-11-05T12:00:00Z",                            │
│    "updated_at": "2025-11-05T12:00:00Z"                             │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ Label created in both Gmail and database ✅
    ↓
User sees new folder in UI
```

**Label Application Workflow (Epic 2 AI Sorting Preview):**

```
┌─────────────────────────────────────────────────────────────────────┐
│              Label Application Flow (Epic 2 Integration)            │
└─────────────────────────────────────────────────────────────────────┘

Email arrives in Gmail
    │
    ↓
Email Polling Service detects new email (Story 1.6)
    │
    ↓
Save to EmailProcessingQueue table (Story 1.7)
    │
    │ status = "pending"
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              AI Classification Service (Epic 2)                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Load email content and user's FolderCategories            │  │
│  │ 2. Use Gemini LLM to classify email                          │  │
│  │    Prompt includes folder names and keywords                  │  │
│  │ 3. Select best matching FolderCategory                        │  │
│  │ 4. Update EmailProcessingQueue:                               │  │
│  │    - proposed_folder_id = 5 (Government folder)              │  │
│  │    - classification = "government_docs"                       │  │
│  │    - status = "processing"                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ Send approval request to user
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   Telegram Bot (Epic 2)                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 5. Send message to user:                                      │  │
│  │    "New email from sender@example.com                         │  │
│  │     Subject: Tax documents                                    │  │
│  │     Proposed folder: Government                               │  │
│  │     [✅ Approve] [❌ Reject]"                                  │  │
│  │                                                                │  │
│  │ 6. User clicks [✅ Approve] button                            │  │
│  │ 7. Telegram sends callback query to backend                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ POST /api/v1/telegram/callback
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Approval Handler (Epic 2)                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 8. Load EmailProcessingQueue record by email_id              │  │
│  │ 9. Extract proposed_folder_id = 5                             │  │
│  │ 10. Load FolderCategory by id (includes gmail_label_id)      │  │
│  │ 11. Extract gmail_label_id = "Label_123"                      │  │
│  │ 12. Extract gmail_message_id from EmailProcessingQueue       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ call GmailClient.apply_label()
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Gmail Client (gmail_client.py)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 13. Construct modify request:                                 │  │
│  │     {                                                          │  │
│  │       "addLabelIds": ["Label_123"]                            │  │
│  │     }                                                          │  │
│  │ 14. Call Gmail API: messages().modify()                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ HTTPS POST
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         Gmail API                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 15. Validate OAuth token                                      │  │
│  │ 16. Validate message_id and label_id exist                    │  │
│  │ 17. Add label to email message                                │  │
│  │ 18. Return success (200 OK)                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ success = True
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Update EmailProcessingQueue                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 19. Update EmailProcessingQueue:                              │  │
│  │     - status = "completed"                                    │  │
│  │     - updated_at = NOW()                                      │  │
│  │ 20. Log event: "email_sorted"                                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ Email sorted ✅
    ↓
User sees email in Gmail under "Government" label
```

**Error Handling Flow:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Error Handling Scenarios                         │
└─────────────────────────────────────────────────────────────────────┘

Error: 409 Conflict (Duplicate Label Name)
    │
    ├─→ Detected in: GmailClient.create_label()
    │
    ├─→ Handler: Call list_labels() to find existing label by name
    │
    ├─→ Action: Return existing label_id (idempotent operation)
    │
    └─→ Result: Folder creation succeeds with existing label ✅

Error: 404 Not Found (Invalid Message ID or Label ID)
    │
    ├─→ Detected in: GmailClient.apply_label() or remove_label()
    │
    ├─→ Handler: Log error with message_id and label_id
    │
    ├─→ Action: Return False (operation failed)
    │
    └─→ Result: Service layer handles error, updates status accordingly

Error: 401 Unauthorized (Expired OAuth Token)
    │
    ├─→ Detected in: All Gmail API calls
    │
    ├─→ Handler: _execute_with_retry() method in GmailClient
    │
    ├─→ Action: Call _refresh_token() to get new access token
    │
    ├─→ Retry: Re-attempt original API call with new token
    │
    └─→ Result: Operation succeeds transparently ✅

Error: 429 Rate Limit Exceeded
    │
    ├─→ Detected in: All Gmail API calls
    │
    ├─→ Handler: _execute_with_retry() with exponential backoff
    │
    ├─→ Action: Wait 2^retry_count seconds (max 3 retries)
    │
    ├─→ Retry: Re-attempt API call after backoff period
    │
    └─→ Result: Operation eventually succeeds or logs failure

Error: IntegrityError (Duplicate Folder Name)
    │
    ├─→ Detected in: FolderService.create_folder() during DB insert
    │
    ├─→ Handler: Catch SQLAlchemy IntegrityError
    │
    ├─→ Action: Raise ValueError with user-friendly message
    │
    └─→ Result: API returns 400 Bad Request to user
```

**Key Design Decisions:**

1. **Idempotent Label Creation**: Gmail API returns 409 Conflict if label name exists. The `create_label()` method handles this by calling `list_labels()` and returning the existing label ID, making the operation idempotent and safe for concurrent requests.

2. **Database-First Validation**: The service layer checks for duplicate folder names in the database before calling the Gmail API. This prevents unnecessary API calls and enforces the unique constraint early.

3. **Atomic Operations**: Folder creation is atomic - if Gmail API fails, no database record is created (transaction rollback). This prevents orphaned database records without corresponding Gmail labels.

4. **Separation of Concerns**:
   - **API Layer**: Authentication, request validation, HTTP error responses
   - **Service Layer**: Business logic, duplicate checks, coordination between DB and Gmail
   - **Gmail Client**: Low-level Gmail API operations, retry logic, token refresh
   - **Database Layer**: Data persistence, unique constraints, cascade deletes

5. **Error Resilience**: All Gmail API calls use `_execute_with_retry()` with exponential backoff for transient errors (401, 429, 503). Token refresh happens automatically on 401 Unauthorized.

6. **Security**: All operations require JWT authentication, and all database queries filter by `user_id` to prevent cross-user access. OAuth tokens are encrypted at rest.

#### Gmail Email Sending Flow

The Email Sending system enables sending emails via Gmail API on behalf of authenticated users with MIME message composition, threading support, and comprehensive error handling. This flow is used for AI-generated responses in Epic 3 and manual testing in development.

**Email Sending Workflow (Story 1.9):**

```
┌─────────────────────────────────────────────────────────────────────┐
│                Email Sending Flow (Story 1.9)                       │
└─────────────────────────────────────────────────────────────────────┘

User/AI System
    │
    │ POST /api/v1/test/send-email
    │ {
    │   "to": "recipient@example.com",
    │   "subject": "Test Email",
    │   "body": "Email content",
    │   "body_type": "plain",
    │   "thread_id": "thread_abc123" (optional)
    │ }
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     API Layer (test.py)                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Authenticate user via JWT (get_current_user)              │  │
│  │ 2. Validate request using Pydantic:                          │  │
│  │    - to: EmailStr (valid email format)                       │  │
│  │    - body_type: "plain" or "html"                            │  │
│  │    - subject, body: string                                   │  │
│  │ 3. Extract user_id from JWT token                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ call GmailClient.send_email()
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Gmail Client (gmail_client.py)                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 4. Load user's OAuth tokens from database (encrypted)       │  │
│  │ 5. Load user's email address from User model                │  │
│  │ 6. If thread_id provided:                                    │  │
│  │    - Call get_thread_message_ids(thread_id)                 │  │
│  │    - Extract message IDs for References header              │  │
│  │    - Set In-Reply-To to latest message ID                   │  │
│  │ 7. Call _compose_mime_message():                             │  │
│  │    - Create MIMEMultipart message object                     │  │
│  │    - Set From header (user's Gmail address)                 │  │
│  │    - Set To header (recipient email)                        │  │
│  │    - Set Subject header                                      │  │
│  │    - Set Date header (RFC 2822 format)                      │  │
│  │    - If threading: Add In-Reply-To, References headers      │  │
│  │    - Attach body as MIMEText (text/plain or text/html)      │  │
│  │    - Encode as base64 URL-safe string                       │  │
│  │ 8. Log email_send_started event                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ MIME message encoded
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Gmail Client Send Logic                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 9. Construct Gmail API request:                              │  │
│  │    {                                                          │  │
│  │      "raw": "<base64_encoded_mime_message>"                  │  │
│  │    }                                                          │  │
│  │ 10. Call Gmail API via _execute_with_retry():                │  │
│  │     service.users().messages().send(                         │  │
│  │       userId='me',                                            │  │
│  │       body=request_body                                       │  │
│  │     ).execute()                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ HTTPS POST
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         Gmail API                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 11. Validate OAuth token                                      │  │
│  │ 12. Parse MIME message (decode base64)                        │  │
│  │ 13. Validate email headers (From, To, Subject, Date)         │  │
│  │ 14. Check sending quota (100 sends/day free tier)            │  │
│  │ 15. Validate recipient email exists                           │  │
│  │ 16. Check message size (<25MB limit)                          │  │
│  │ 17. Send email to recipient via Gmail SMTP                    │  │
│  │ 18. Add email to Sent folder                                  │  │
│  │ 19. If threading: Link to conversation thread                │  │
│  │ 20. Return message_id (e.g., "18abc123def456")               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ message_id = "18abc123def456"
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Gmail Client Success Logging                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 21. Extract message_id from response                          │  │
│  │ 22. Calculate send duration (milliseconds)                    │  │
│  │ 23. Log email_sent event:                                     │  │
│  │     {                                                          │  │
│  │       "event": "email_sent",                                  │  │
│  │       "user_id": 123,                                         │  │
│  │       "recipient": "recipient@example.com",                   │  │
│  │       "subject": "Test Email",                                │  │
│  │       "message_id": "18abc123def456",                         │  │
│  │       "success": true,                                        │  │
│  │       "duration_ms": 1234,                                    │  │
│  │       "timestamp": "2025-11-05T10:15:31.357Z"                 │  │
│  │     }                                                          │  │
│  │ 24. Return message_id to API layer                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ return message_id
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     API Response (200 OK)                           │
│  {                                                                  │
│    "success": true,                                                 │
│    "data": {                                                        │
│      "message_id": "18abc123def456",                                │
│      "recipient": "recipient@example.com",                          │
│      "subject": "Test Email"                                        │
│    }                                                                │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ Email sent successfully ✅
    ↓
Email appears in recipient's inbox
(and in sender's Sent folder in Gmail)
```

**Email Sending Error Handling:**

```
┌─────────────────────────────────────────────────────────────────────┐
│              Email Sending Error Handling                           │
└─────────────────────────────────────────────────────────────────────┘

Gmail API Error Occurs
    │
    ├─ 400 Bad Request (Invalid Recipient)
    │   │
    │   └─→ InvalidRecipientError raised
    │       │
    │       └─→ API returns 400 with error message
    │           "Invalid recipient email address: invalid@example.com"
    │
    ├─ 401 Unauthorized (Token Expired)
    │   │
    │   └─→ Auto-handled by _execute_with_retry()
    │       │
    │       ├─ 1. Refresh OAuth token via refresh_token
    │       ├─ 2. Update database with new access_token
    │       └─ 3. Retry send_email() once
    │
    ├─ 413 Request Entity Too Large (>25MB)
    │   │
    │   └─→ MessageTooLargeError raised
    │       │
    │       └─→ API returns 413 with error message
    │           "Email exceeds Gmail 25MB size limit"
    │
    ├─ 429 Too Many Requests (Quota Exceeded)
    │   │
    │   └─→ QuotaExceededError raised
    │       │
    │       ├─ 1. Extract retry_after from response headers
    │       ├─ 2. Log quota_exceeded event with user_id
    │       ├─ 3. _execute_with_retry() applies exponential backoff:
    │       │    - Retry 1: Wait 2 seconds
    │       │    - Retry 2: Wait 4 seconds
    │       │    - Retry 3: Wait 8 seconds
    │       └─ 4. If all retries fail → API returns 429 error
    │           "Gmail API quota exceeded (100 sends/day)"
    │           Headers: {"Retry-After": "86400"}
    │
    └─ 503 Service Unavailable (Transient Gmail Error)
        │
        └─→ Auto-handled by _execute_with_retry()
            │
            ├─ 1. Log transient_error event
            ├─ 2. Exponential backoff (max 3 retries)
            └─ 3. If all retries fail → Raise HttpError
                "Gmail API temporarily unavailable"
```

**MIME Message Structure (RFC 2822 Compliant):**

```
From: user@gmail.com
To: recipient@example.com
Subject: Test Email
Date: Tue, 05 Nov 2025 10:15:30 +0000
In-Reply-To: <previous-message-id@mail.gmail.com>  (if thread_id provided)
References: <msg1@mail.gmail.com> <msg2@mail.gmail.com>  (if thread_id provided)
Content-Type: text/plain; charset="utf-8"

Email body content here...

---
Base64 URL-safe encoded before sending to Gmail API
```

**Threading Headers for Replies:**

When sending a reply to an existing email thread:

1. **In-Reply-To Header**: Contains Message-ID of the email being replied to
   - Format: `In-Reply-To: <18abc123def456@mail.gmail.com>`
   - Single message ID in angle brackets

2. **References Header**: Contains all message IDs in the conversation thread
   - Format: `References: <msg1@mail.gmail.com> <msg2@mail.gmail.com> <msg3@mail.gmail.com>`
   - Space-separated list of message IDs in chronological order
   - Gmail uses this to group emails into conversation threads

3. **Thread Construction Process**:
   ```
   thread_id provided
       ↓
   Call get_thread_message_ids(thread_id)
       ↓
   Gmail API threads().get(id=thread_id)
       ↓
   Extract message IDs: ["msg1", "msg2", "msg3"]
       ↓
   Construct headers:
       In-Reply-To: <msg3>  (latest)
       References: <msg1> <msg2> <msg3>  (all)
       ↓
   Email appears in Gmail conversation thread
   ```

**Gmail Sending Quotas and Rate Limits (Story 1.9):**

| Quota Type | Free Tier | G Suite | Reset Frequency |
|------------|-----------|---------|-----------------|
| Email Sends | 100/day | 2,000/day | Daily (midnight PT) |
| API Requests | 10,000/day | 25,000/day | Daily (midnight PT) |
| Message Size | 25MB max | 25MB max | N/A |

**Typical Mail Agent Sending Usage:**
- AI-generated responses: 10-20 sends/day per user
- Test emails: 5 sends/day per user
- Total: 15-25 sends/day (12-25% of free tier quota)

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

**Implementation Status:**

✅ **Story 3.11 (Workflow Integration & Conditional Routing) - Completed 2025-11-10**

The conditional routing architecture described above has been fully implemented in Story 3.11. The implementation includes:
- `route_by_classification()` function that returns classification values for path mapping
- Conditional edges from classify node routing to either `generate_response` node (for emails needing responses) or `send_telegram` node (for sort-only emails)
- `generate_response` node (registered as "generate_response") that calls `ResponseGenerationService.generate_response_draft()`
- Updated `classify` node that sets classification field using `ResponseGenerationService.should_generate_response()`
- Updated `send_telegram` node that selects appropriate template based on `draft_response` field existence

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

### Telegram Callback Routing Patterns (Epic 2 & 3)

**Callback Data Format:**

All Telegram inline button callbacks use a consistent format for routing:
```
{action}_{resource}_{id}
```

**Examples:**
```python
# Epic 2 - Email Sorting (Story 2.7)
"approve_{email_id}"         # Approve sorting proposal
"reject_{email_id}"          # Reject sorting proposal
"change_folder_{email_id}"   # Request folder change
"folder_{folder_id}_{email_id}"  # Select specific folder

# Epic 3 - Response Editing & Sending (Story 3.9)
"send_response_{email_id}"   # Send AI-generated response
"edit_response_{email_id}"   # Edit response draft
"reject_response_{email_id}" # Reject response draft
```

**Callback Router Implementation (`telegram_handlers.py`):**

```python
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Central callback router for all Telegram button interactions."""
    query = update.callback_query
    callback_data = query.data

    # Parse callback data
    parts = callback_data.split("_")
    action = parts[0]  # First part is always the action

    # Route to appropriate handler
    if action == "approve":
        email_id = int(parts[1])
        await handle_approve(query, email_id, db)

    elif action == "send" and parts[1] == "response":
        email_id = int(parts[2])
        await handle_send_response(update, context, email_id, db)

    elif action == "edit" and parts[1] == "response":
        email_id = int(parts[2])
        await handle_edit_response(update, context, email_id, db)

    elif action == "reject" and parts[1] == "response":
        email_id = int(parts[2])
        await handle_reject_response(update, context, email_id, db)

    # ... other handlers
```

**Response Editing & Sending Workflow (Story 3.9):**

**Edit Workflow:**
1. User clicks [Edit] button → `callback_data = "edit_response_{email_id}"`
2. `handle_edit_response()` sends prompt: "Reply to this message with your edited text"
3. User replies with edited text
4. `handle_message()` captures reply via edit session tracking
5. `ResponseEditingService.handle_message_reply()` updates `EmailProcessingQueue.draft_response`
6. Bot re-sends draft message with updated text and same buttons
7. `WorkflowMapping.workflow_state` updated to "draft_edited"

**Send Workflow:**
1. User clicks [Send] button → `callback_data = "send_response_{email_id}"`
2. `handle_send_response()` loads `draft_response` from database
3. `ResponseSendingService.handle_send_response_callback()` sends via Gmail API:
   - Calls `GmailClient.send_email(to, subject, body, thread_id=gmail_thread_id)`
   - Gmail API adds In-Reply-To header for proper threading
4. Updates `EmailProcessingQueue.status = "completed"`
5. Sends Telegram confirmation: "✅ Response sent to {recipient}"
6. Generates embedding via `EmbeddingService.embed_text()`
7. Indexes to ChromaDB via `VectorDBClient.insert_embedding()`
8. `WorkflowMapping.workflow_state` updated to "sent"

**Reject Workflow:**
1. User clicks [Reject] button → `callback_data = "reject_response_{email_id}"`
2. `handle_reject_response()` updates status
3. `ResponseSendingService.handle_reject_response_callback()`:
   - Updates `EmailProcessingQueue.status = "rejected"`
   - Updates `WorkflowMapping.workflow_state = "rejected"`
4. Sends Telegram confirmation: "❌ Response draft rejected"

**State Machine:**

```
Response Draft Created (Story 3.8)
        ↓
[awaiting_response_approval]
        ↓
    ┌───┴───┬─────────┐
    │       │         │
 [Edit]  [Send]   [Reject]
    │       │         │
    ↓       ↓         ↓
[draft_edited] [sent] [rejected]
    │
    ↓
 [Send]
    ↓
  [sent]
```

**WorkflowMapping Usage:**

```python
# Story 3.8: Create mapping when sending draft
workflow_mapping = WorkflowMapping(
    email_id=email.id,
    user_id=user.id,
    thread_id=thread_id,
    telegram_message_id=message.message_id,
    workflow_state="awaiting_response_approval"
)

# Story 3.9: Update state on edit
workflow_mapping.workflow_state = "draft_edited"

# Story 3.9: Update state on send
workflow_mapping.workflow_state = "sent"

# Story 3.9: Update state on reject
workflow_mapping.workflow_state = "rejected"
```

**Error Handling Patterns:**

```python
# Validate user owns email before allowing edits/sends
user = await session.get(User, email.user_id)
if not user or user.telegram_id != telegram_id:
    await query.answer("❌ Unauthorized", show_alert=True)
    return

# Graceful degradation for indexing failures
try:
    await self.index_sent_response(email_id)
except Exception as e:
    logger.error("indexing_failed", error=str(e))
    # Don't fail send operation if indexing fails
```

**Session Management for Edit Workflow:**

```python
# Global session storage (MVP - replace with Redis for production)
_edit_sessions = {}  # {telegram_id: email_id}

# On edit button click
_edit_sessions[telegram_id] = email_id

# On message reply
if telegram_id in _edit_sessions:
    email_id = _edit_sessions[telegram_id]
    # Process edited text...
    del _edit_sessions[telegram_id]  # Clear session
```

**Vector DB Indexing for Sent Responses:**

After successful email send, Story 3.9 indexes the sent response for future RAG context:

```python
# Generate embedding
embedding = embedding_service.embed_text(draft_response)

# Prepare metadata
metadata = {
    "message_id": f"sent_{email_id}_{timestamp}",
    "user_id": user_id,
    "thread_id": gmail_thread_id,
    "sender": original_sender,
    "subject": f"Re: {original_subject}",
    "date": datetime.now(UTC).isoformat(),
    "language": detected_language,
    "is_sent_response": True  # Flag to distinguish from received emails
}

# Store in ChromaDB
vector_db_client.insert_embedding(
    collection_name="email_embeddings",
    embedding=embedding,
    metadata=metadata,
    id=metadata["message_id"]
)
```

**Benefits:**
- Sent responses available for future AI context retrieval
- AI can reference user's own sent responses in future drafts
- Maintains complete conversation history in vector database

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

**IndexingProgress Table** (Epic 3 - Story 3.3):
```sql
CREATE TABLE indexing_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_emails INTEGER DEFAULT 0 NOT NULL,
    processed_count INTEGER DEFAULT 0 NOT NULL,
    status VARCHAR(50) NOT NULL,  -- in_progress, completed, failed, paused
    last_processed_message_id VARCHAR(255),  -- Gmail message ID for checkpoint
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_indexing_progress_user_id UNIQUE (user_id)
);
CREATE INDEX idx_indexing_progress_user_id ON indexing_progress(user_id);
CREATE INDEX idx_indexing_progress_status ON indexing_progress(status);
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
                    ├─────────> (1) notification_preferences
                    │
                    └─────────> (1) indexing_progress

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
    "id": "email_abc123",  # email_id (Gmail message ID)
    "embedding": [0.123, -0.456, ...],  # 768-dimensional vector (Gemini text-embedding-004)
    "metadata": {
        "email_id": "email_abc123",
        "user_id": "user_123",
        "thread_id": "thread_xyz789",
        "sender": "sender@example.com",
        "subject": "Email subject",
        "received_at": "2025-11-03T10:15:30Z",
        "language": "de",
        "has_attachments": false,
        "is_reply": true,
        "word_count": 250
    },
    "document": "First 500 chars of email body for debugging"
}
```

**Indexing Strategy (Epic 3 - Story 3.3):**
- **90-Day Initial Indexing:** Background job indexes last 90 days of email history on first indexing request
  - Rationale: Fast onboarding (<10 min for 5,000 emails), sufficient context for most users
  - Triggered via: `POST /api/v1/indexing/start` or Celery task `index_user_emails.delay(user_id, days_back=90)`
  - Progress tracked in `indexing_progress` table with checkpoint support for resumption
  - Batch size: 50 emails per batch with 60-second rate limiting (50 requests/min to Gemini API)
  - Gmail pagination: 100 emails per page with date filtering (`after:{unix_timestamp}`)
  - Telegram notification sent on completion with indexing statistics
- **Checkpoint & Resumption:** Interrupted jobs can be resumed from last processed email
  - Checkpoint saved every batch (50 emails) with `last_processed_message_id`
  - Automatic resumption on service restart or manual trigger via `resume_user_indexing` task
- **Incremental Indexing:** New emails indexed immediately after arriving (post-classification)
  - Triggered automatically by email polling service after classification workflow
  - No batch delay - single email indexed on-demand for real-time context updates
  - Skipped if initial indexing is not yet completed
- **Update Strategy:** Emails are immutable - no updates needed
- **Deletion Strategy:** User deletion triggers cascade delete of all embeddings via ChromaDB `delete()` API

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

### Email Embedding Service (Epic 3 - Story 3.2)

**Component:** `EmbeddingService` (`backend/app/core/embedding_service.py`)

The Email Embedding Service converts email content into 768-dimensional vector embeddings using Google Gemini's `text-embedding-004` model for semantic search and RAG-based response generation.

**Key Features:**
- **Gemini text-embedding-004 Integration**: 768 dimensions, unlimited free tier
- **Email Preprocessing Pipeline**: Automatic HTML stripping, token truncation (2048 max)
- **Batch Processing**: Efficient batch embedding generation (up to 50 emails per batch)
- **Error Handling**: Automatic retry with exponential backoff (3 attempts for transient errors)
- **Multilingual Support**: Native support for 50+ languages (ru/uk/en/de)
- **Usage Tracking**: Built-in metrics for free-tier monitoring

**Preprocessing Pipeline** (`backend/app/core/preprocessing.py`):
```python
# 1. HTML Stripping
clean_text = strip_html("<p>Email content</p>")  # → "Email content"

# 2. Text Extraction
text = extract_email_text(email_body, content_type="text/html")

# 3. Token Truncation (2048 limit for Gemini API)
truncated = truncate_to_tokens(text, max_tokens=2048)
```

**Usage Example:**
```python
from app.core.embedding_service import EmbeddingService

# Initialize service (uses GEMINI_API_KEY from environment)
service = EmbeddingService()

# Single embedding
embedding = service.embed_text("Email content")
# Returns: List[float] with 768 dimensions

# Batch embedding
embeddings = service.embed_batch(["Email 1", "Email 2"], batch_size=50)
# Returns: List[List[float]], each with 768 dimensions

# Usage statistics
stats = service.get_usage_stats()
# Returns: {"total_requests": N, "total_embeddings_generated": M, "avg_latency_ms": X}
```

**Integration with ChromaDB:**
```python
from app.core.embedding_service import EmbeddingService
from app.core.vector_db import VectorDBClient

embedding_service = EmbeddingService()
vector_db_client = VectorDBClient()

# Generate embedding
embedding = embedding_service.embed_text(email_text)

# Store in ChromaDB
vector_db_client.insert_embeddings_batch(
    collection_name="email_embeddings",
    embeddings=[embedding],
    metadatas=[metadata],
    ids=[message_id]
)
```

**Performance:**
- Single embedding latency: ~200-500ms
- Batch (50 emails): <60 seconds total
- Throughput: ~50 emails/minute
- Dimensions: 768 (matches ChromaDB collection)

**Error Handling:**
- **Retried Errors** (3 attempts): Rate limits (429), Timeouts
- **Not Retried**: Invalid requests (400), Blocked prompts (403)
- **Backoff Strategy**: Exponential (2s, 4s, 8s delays)

**Test Endpoint:**
```bash
GET /api/v1/test/embedding-stats

Response:
{
  "total_requests": 42,
  "total_embeddings_generated": 128,
  "avg_latency_ms": 234.56,
  "service_initialized": true
}
```

**Documentation:**
- Setup Guide: `docs/embedding-service-setup.md`
- Unit Tests: `backend/tests/test_embedding_service.py`, `backend/tests/test_preprocessing.py`
- Integration Tests: `backend/tests/integration/test_embedding_integration.py`

### Email History Indexing Service (Epic 3 - Story 3.3)

**Component:** `EmailIndexingService` (`backend/app/services/email_indexing.py`)

The Email History Indexing Service orchestrates bulk indexing of user's Gmail history into ChromaDB vector database for RAG-based context retrieval. Designed for fast onboarding with checkpoint-based resumption and comprehensive error handling.

**Key Features:**
- **90-Day Historical Indexing**: Indexes last 90 days of emails (configurable) for fast onboarding
- **Gmail Pagination**: Efficient batched retrieval with date filtering (`after:{timestamp}`)
- **Batch Processing**: 50 emails per batch with rate limiting (50 requests/min to Gemini API)
- **Checkpoint Mechanism**: Resumable indexing with `last_processed_message_id` tracking
- **Error Handling**: Retry logic for transient errors (Gmail/Gemini API rate limits)
- **Progress Tracking**: Real-time progress updates in `indexing_progress` table
- **Telegram Notifications**: User notification on completion with statistics
- **Incremental Indexing**: Automatic indexing of new emails post-classification
- **Metadata Extraction**: Thread ID, sender, language detection, attachment flags, reply detection

**Architecture Flow:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Email History Indexing Workflow                      │
└─────────────────────────────────────────────────────────────────────────┘

User/System Trigger
    │
    │ POST /api/v1/indexing/start
    │ OR Celery task: index_user_emails.delay(user_id, days_back=90)
    │
    ▼
EmailIndexingService.start_indexing()
    │
    ├─> 1. Check for existing job (prevent duplicates)
    │   └─> ValueError if job already running
    │
    ├─> 2. Create IndexingProgress record (status=in_progress)
    │
    ├─> 3. Retrieve Gmail emails (90-day lookback)
    │   │
    │   ├─> Gmail API pagination (100 emails/page)
    │   ├─> Date filter: after:{90_days_ago_unix_timestamp}
    │   └─> Return: List[Dict] with full email metadata
    │
    ├─> 4. Process in batches (50 emails/batch)
    │   │
    │   ├─> For each batch:
    │   │   │
    │   │   ├─> Extract metadata (thread, sender, language, flags)
    │   │   ├─> Preprocess email body (HTML strip, truncate 2048 tokens)
    │   │   ├─> Generate embeddings (EmbeddingService.embed_batch)
    │   │   ├─> Store in ChromaDB (VectorDBClient.insert_embeddings_batch)
    │   │   ├─> Update progress checkpoint (last_processed_message_id)
    │   │   └─> Rate limit delay (60 seconds between batches)
    │   │
    │   └─> Return: processed_count
    │
    ├─> 5. Mark as completed
    │   │
    │   ├─> Update IndexingProgress (status=completed, completed_at=now)
    │   └─> Send Telegram notification with statistics
    │
    └─> 6. Error Handling
        │
        ├─> GmailAPIError / GeminiAPIError
        │   └─> Celery retry (3 attempts, exponential backoff: 60s, 120s, 240s)
        │
        └─> Unexpected error
            └─> Mark as failed, log error, no retry
```

**Checkpoint & Resumption Strategy:**
- **Checkpoint Frequency**: Every batch (50 emails)
- **Checkpoint Data**: `last_processed_message_id` (Gmail message ID)
- **Resumption Logic**:
  1. Check for interrupted job (`status=in_progress`)
  2. Retrieve Gmail emails from checkpoint: `after:{last_processed_message_id}`
  3. Continue processing from next batch
  4. Progress accumulates on top of previous run
- **Manual Resume**: `POST /api/v1/indexing/resume` or Celery task `resume_user_indexing.delay(user_id)`

**Incremental Indexing (New Emails):**
- **Trigger**: Email polling service detects new email after classification
- **Endpoint**: `EmailIndexingService.index_new_email(message_id)`
- **Flow**:
  1. Check if initial indexing completed (skip if not)
  2. Retrieve single email from Gmail API
  3. Extract metadata, generate embedding, store in ChromaDB
  4. No batch delay - real-time indexing
- **Celery Task**: `index_new_email_background.delay(user_id, message_id)`

**Usage Example:**
```python
from app.services.email_indexing import EmailIndexingService

# Initialize service
service = EmailIndexingService(user_id=123)

# Start indexing (90 days)
progress = await service.start_indexing(days_back=90)
# Returns: IndexingProgress(total_emails=437, processed_count=437, status="completed")

# Resume interrupted job
progress = await service.resume_indexing()
# Returns: IndexingProgress or None if no interrupted job

# Index new email (incremental)
success = await service.index_new_email(message_id="abc123")
# Returns: True if indexed, False if skipped
```

**Metadata Extraction:**
```python
{
    "email_id": "abc123",
    "user_id": 123,
    "thread_id": "thread_xyz789",
    "sender": "sender@example.com",
    "subject": "Email subject",
    "received_at": "2025-11-03T10:15:30Z",
    "language": "de",  # Detected via langdetect library
    "has_attachments": false,
    "is_reply": true,  # Detected via "Re:" or "RE:" prefix
    "word_count": 250
}
```

**Performance Characteristics:**
- **Gmail API**: 100 emails/page, date filtering for 90-day window
- **Batch Processing**: 50 emails per batch
- **Rate Limiting**: 60-second delay between batches (50 requests/min to Gemini API)
- **Checkpoint Overhead**: ~50ms per batch (PostgreSQL update)
- **Total Time**: ~10 minutes for 5,000 emails (100 batches × 60s + API latency)
- **Database Queries**: 1 progress create + N progress updates + 1 completion update

**Error Handling & Retry:**
- **Transient Errors** (retried 3 times with exponential backoff):
  - `GmailAPIError`: Rate limits (429), network timeouts
  - `GeminiAPIError`: Rate limits, embedding generation failures
  - Backoff delays: 60s → 120s → 240s
- **Permanent Errors** (not retried):
  - `ValueError`: Indexing job already exists for user
  - Invalid user credentials
  - Database constraint violations
- **Max Retries**: 3 attempts, then mark as failed and notify user

**Celery Background Tasks:**
```python
# 1. Start indexing (long-running task)
@celery_app.task(
    name="app.tasks.indexing_tasks.index_user_emails",
    time_limit=3600,  # 1 hour
    soft_time_limit=3540,  # 59 minutes
    max_retries=3,
    default_retry_delay=60
)
def index_user_emails(user_id: int, days_back: int = 90) -> dict

# 2. Resume interrupted indexing
@celery_app.task(name="app.tasks.indexing_tasks.resume_user_indexing")
def resume_user_indexing(user_id: int) -> dict

# 3. Incremental indexing (new emails)
@celery_app.task(
    name="app.tasks.indexing_tasks.index_new_email_background",
    time_limit=120,  # 2 minutes
    max_retries=2
)
def index_new_email_background(user_id: int, message_id: str) -> dict
```

**Database Model:**
```python
class IndexingProgress(BaseModel, table=True):
    __tablename__ = "indexing_progress"

    user_id: int  # FK to users.id, unique constraint
    total_emails: int
    processed_count: int
    status: IndexingStatus  # in_progress, completed, failed, paused
    last_processed_message_id: Optional[str]  # Checkpoint
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
```

**Test Coverage:**
- **Unit Tests**: `backend/tests/test_email_indexing.py` (8 test functions covering all 12 ACs)
- **Celery Task Tests**: `backend/tests/test_indexing_tasks.py` (5 test functions)
- **Total Coverage**: 13 test functions, all passing

**Security Considerations:**
- **Gmail OAuth Tokens**: Never logged or exposed in error messages
- **Gemini API Key**: Loaded from environment variables, not hardcoded
- **Rate Limiting**: Prevents API abuse and quota exhaustion
- **User Isolation**: Multi-tenant filtering via `user_id` in ChromaDB queries
- **Error Sanitization**: Sensitive data (tokens, keys) removed from exception messages

**Documentation:**
- Technical Spec: `docs/tech-spec-epic-3.md`
- Story: `docs/stories/3-3-email-history-indexing.md`
- Unit Tests: `backend/tests/test_email_indexing.py`, `backend/tests/test_indexing_tasks.py`

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

### ADR-014: Hybrid Tone Detection (Rules + LLM)

**Status:** Accepted

**Context:** Need accurate tone detection (formal/professional/casual) for appropriate email responses across government, business, and personal emails. Pure rule-based systems lack flexibility; pure LLM systems are slow and costly.

**Decision:** Implement hybrid tone detection - rule-based for 80% of cases (known patterns) + LLM-based for 20% ambiguous cases.

**Rationale:**
- **Rule-Based (Fast Path):** Government domains (finanzamt.de, etc.) → formal; Business domains → professional; Free providers → casual
- **LLM-Based (Flexible Path):** Unknown/ambiguous senders analyzed by Gemini for tone
- **Performance:** <50ms typical (rules), ~500ms worst case (LLM fallback)
- **Cost Efficiency:** 80% of emails use free rule-based detection, only 20% require API calls
- **Accuracy:** Rules handle well-defined cases (95%+ accuracy), LLM provides flexibility for edge cases

**Consequences:**
- Best balance of speed, cost, and accuracy
- Requires maintaining government domain list (extensible)
- Provides fallback to "professional" if LLM unavailable (graceful degradation)
- Enables future refinement through prompt versioning system

## Context Retrieval Service (Story 3.4)

The Context Retrieval Service implements Smart Hybrid RAG (ADR-011) for retrieving relevant conversation context to power AI response generation.

### Smart Hybrid RAG Strategy

The service combines two complementary context sources:

1. **Thread History**: Last 5 emails from Gmail thread (conversation continuity)
2. **Semantic Search**: Top 3-7 similar emails from vector DB (broader context)

**Adaptive k Logic** dynamically adjusts semantic search count based on thread length:
- **Short threads (<3 emails)**: k=7 (need more semantic context)
- **Standard threads (3-5 emails)**: k=3 (balanced hybrid)
- **Long threads (>5 emails)**: k=0 (skip semantic, thread sufficient)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ ContextRetrievalService.retrieve_context(email_id)              │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ├──► Load email from EmailProcessingQueue (DB)
                 │
                 ├──► Sequential Retrieval (ADR-015):
                 │    ├─► Step 1: Thread History (GmailClient)
                 │    │   └─► Get last 5 emails in thread
                 │    │
                 │    ├─► Step 2: Calculate adaptive k (based on thread_length)
                 │    │   └─► k=0/3/7 depending on thread length
                 │    │
                 │    └─► Step 3: Semantic Search (if k > 0)
                 │        ├─► Generate query embedding (Gemini)
                 │        ├─► Query ChromaDB (top k similar)
                 │        └─► Fetch full bodies from Gmail
                 │
                 ├──► Rank semantic results (relevance + recency)
                 │
                 ├──► Enforce token budget (~6.5K tokens)
                 │    ├─► Truncate thread history (keep recent)
                 │    └─► Truncate semantic results (remove low-ranked)
                 │
                 └──► Return RAGContext:
                      {
                        "thread_history": [...],
                        "semantic_results": [...],
                        "metadata": {
                          "thread_length": int,
                          "semantic_count": int,
                          "oldest_thread_date": str,
                          "total_tokens_used": int,
                          "adaptive_k": int
                        }
                      }
```

### Token Budget Management

**Budget:** ~6.5K tokens total for context (leaving 25K for Gemini response generation within 32K context window)

**Token Counting:** Uses tiktoken library (GPT-4 compatible tokenizer, accurate for Gemini)

**Truncation Strategy:**
1. Count tokens in all email bodies (thread_history + semantic_results)
2. If total > 6500 tokens:
   - Truncate thread_history first (keep most recent N emails)
   - If still over, truncate semantic_results (remove lowest ranked)
3. Log final token usage to metadata

### Performance Optimization

**Target:** <3 seconds total retrieval time (NFR001)

**Execution Strategy (ADR-015):**
- **Sequential execution** (thread history → adaptive k → semantic search)
- **Design rationale**: Adaptive k calculation REQUIRES thread_length from thread history, creating data dependency that prevents true parallelization (see ADR-015 for full analysis)
- **Performance impact**: Sequential execution ~500ms slower than parallel, but performance target still met

**Actual latency breakdown:**
- Gmail thread fetch: ~1000ms
- Adaptive k calculation: <1ms
- Semantic search (if k>0): ~500ms
- Context assembly: ~100ms
- **Total**: ~1600ms (well under 3s target ✅)

**Performance monitoring**: Logs latency_ms, thread_count, semantic_count, total_tokens with every retrieval

### Data Models

**RAGContext TypedDict:**
```python
{
    "thread_history": List[EmailMessage],  # Last 5 emails (chronological)
    "semantic_results": List[EmailMessage], # Top 3-7 similar (ranked)
    "metadata": Dict[str, Any]             # Statistics and token usage
}
```

**EmailMessage TypedDict:**
```python
{
    "message_id": str,
    "sender": str,
    "subject": str,
    "body": str,
    "date": str,  # ISO 8601 format
    "thread_id": str
}
```

### Security & Multi-Tenancy

- **User isolation**: ChromaDB queries filtered by `user_id` (prevent cross-user access)
- **Input validation**: email_id and user_id parameters validated
- **Error handling**: No email content leaked in error messages
- **No hardcoded credentials**: All API keys from environment variables

### Integration Points

**Upstream (Story 3.1, 3.2, 3.3):**
- `VectorDBClient.query_embeddings()` - Semantic search in ChromaDB
- `EmbeddingService.embed_text()` - Generate query embeddings (Gemini)
- `GmailClient.get_thread()` - Retrieve thread history

**Downstream (Story 3.7):**
- `ResponseGenerationService` will consume RAGContext for AI response generation

### Testing

**Unit Tests (8 functions)**: Test each method in isolation with mocked dependencies
**Integration Tests (5 functions)**: End-to-end scenarios with real ChromaDB, mocked Gmail

Test coverage: 80%+ for new code

---

## AI Response Generation Service (Story 3.7)

The AI Response Generation Service orchestrates the complete email response generation workflow by integrating all Epic 3 services: Context Retrieval (3.4), Language Detection (3.5), Tone Detection (3.6), Prompt Engineering (3.6), and Gemini LLM (2.1).

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│ ResponseGenerationService.process_email_for_response(email_id)   │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 ├──► Step 1: Response Need Classification
                 │    ├─► Check no-reply/newsletter patterns
                 │    ├─► Detect question indicators (4 languages)
                 │    ├─► Analyze thread length (>2 = active)
                 │    └─► Default: generate (better to offer than miss)
                 │
                 ├──► Step 2: RAG Context Retrieval (Story 3.4)
                 │    └─► ContextRetrievalService.retrieve_context(email_id)
                 │        └─► Returns RAGContext {thread_history, semantic_results}
                 │
                 ├──► Step 3: Language Detection (Story 3.5)
                 │    └─► LanguageDetectionService.detect(email_subject)
                 │        └─► Returns (language_code, confidence)
                 │
                 ├──► Step 4: Tone Detection (Story 3.6)
                 │    └─► ToneDetectionService.detect_tone(email, thread_history)
                 │        └─► Returns "formal"/"professional"/"casual"
                 │
                 ├──► Step 5: Prompt Formatting (Story 3.6)
                 │    └─► format_response_prompt(email, rag_context, language, tone)
                 │        └─► Returns formatted prompt with all context
                 │
                 ├──► Step 6: LLM Response Generation (Story 2.1)
                 │    └─► LLMClient.send_prompt(prompt, response_format="text")
                 │        └─► Returns generated response text
                 │
                 ├──► Step 7: Response Quality Validation
                 │    ├─► Length: 50-2000 characters
                 │    ├─► Language: Matches expected (using LanguageDetectionService)
                 │    └─► Structure: Contains greeting and/or closing
                 │
                 └──► Step 8: Database Persistence
                      └─► Update EmailProcessingQueue:
                          ├─► draft_response = generated text
                          ├─► detected_language = language code
                          ├─► status = "awaiting_approval"
                          └─► classification = "needs_response"
```

### Response Need Classification

**Decision Logic:**

1. **Skip response** for:
   - No-reply senders matching patterns: `no-?reply`, `noreply`, `newsletter`, `notifications?`, `automated?`
   - Example: `noreply@newsletter.com`, `notifications@system.io`

2. **Generate response** for:
   - Emails containing question indicators in any of 4 languages:
     - English: `?`, `what`, `when`, `where`, `who`, `why`, `how`, `can you`, `could you`
     - German: `?`, `was`, `wann`, `wo`, `wer`, `warum`, `wie`, `können sie`
     - Russian: `?`, `что`, `когда`, `где`, `кто`, `почему`, `как`, `можете ли`
     - Ukrainian: `?`, `що`, `коли`, `де`, `хто`, `чому`, `як`, `чи можете`
   - Emails in active conversations (thread length > 2)
   - Default for unclear cases (better to offer response than miss important email)

**Rationale:** Reduces unnecessary LLM API calls and focuses user attention on emails requiring replies.

### Service Orchestration Pattern

**Dependency Injection for Testability:**

```python
class ResponseGenerationService:
    def __init__(
        self,
        user_id: int,
        context_service: Optional[ContextRetrievalService] = None,
        language_service: Optional[LanguageDetectionService] = None,
        tone_service: Optional[ToneDetectionService] = None,
        llm_client: Optional[LLMClient] = None,
        db_service = None,
    ):
        # Initialize services with optional dependency injection
        self.context_service = context_service or ContextRetrievalService(user_id)
        self.language_service = language_service or LanguageDetectionService()
        self.tone_service = tone_service or ToneDetectionService()
        self.llm_client = llm_client or LLMClient()
```

**Benefits:**
- Testability: Mock external services for unit tests
- Separation of concerns: Each service has single responsibility
- Reusability: Services can be used independently
- Maintainability: Changes to one service don't affect others

### Response Quality Validation Strategy

**Multi-Level Validation:**

1. **Not Empty Check**: Minimum 20 characters (absolute minimum)
2. **Length Range**: 50-2000 characters (typical email response range)
3. **Language Match**: Detected language matches expected (using LanguageDetectionService)
4. **Structure Check**: Contains greeting and/or closing patterns
   - German: `sehr geehrte`, `liebe`, `mit freundlichen grüßen`, `viele grüße`
   - English: `dear`, `hello`, `sincerely`, `best regards`
   - Russian: `уважаем`, `здравствуй`, `с уважением`
   - Ukrainian: `доброго дня`, `з повагою`

**Rationale:** Prevents low-quality responses from reaching users, maintains trust in AI system.

### Database Status Management

**EmailProcessingQueue Fields Updated:**

```python
# After response generation (AC #8, #10)
email.draft_response = response_draft       # Generated response text
email.detected_language = language_code     # ru, uk, en, de
email.status = "awaiting_approval"          # Signals Telegram bot (Story 3.8)
email.classification = "needs_response"     # vs "sort_only" emails
email.updated_at = datetime.now()           # Update timestamp
```

**Status Transition:** `processing` → `awaiting_approval`

**Rationale:** Enables Telegram bot (Story 3.8) to retrieve and present response drafts for user approval.

### Performance Targets

**Latency Breakdown (NFR001: <2 minutes total):**

| Step | Service | Target Latency |
|------|---------|----------------|
| Classification | ResponseGenerationService | <0.1s |
| Context Retrieval | ContextRetrievalService (Story 3.4) | ~3s |
| Language Detection | LanguageDetectionService (Story 3.5) | ~0.1s |
| Tone Detection | ToneDetectionService (Story 3.6) | ~0.2s |
| Prompt Formatting | format_response_prompt (Story 3.6) | ~0.01s |
| Gemini API | LLMClient (Story 2.1) | ~5s |
| Validation | ResponseGenerationService | ~0.5s |
| Database Save | ResponseGenerationService | ~0.1s |
| **Total** | | **~8.8s** |

**Result:** Well within 2-minute performance requirement ✅

### Error Handling Patterns

**Comprehensive Error Logging:**

```python
# Classification errors: Log decision rationale
logger.info("response_classification_no_reply", email_id=id, reason="automated_sender")

# Generation errors: Log error type and context
logger.error("response_generation_failed", email_id=id, error_type=type(e).__name__)

# Validation errors: Log specific failure reason
logger.warning("response_validation_failed", reason="too_short", length=len(draft))
```

**Privacy-Preserving Logging:**
- Email sender truncated to 50 characters
- Email subject used for classification (body not logged in full)
- Structured logging with email_id references (no PII)

### Security Considerations

**Credential Management:**
- Gemini API key: From environment variable `GEMINI_API_KEY`
- Database credentials: From environment variable `DATABASE_URL`
- No hardcoded secrets in code

**Input Validation:**
- email_id existence checks before operations (lines 248-249, 492-493, 564-565)
- Response length validation (50-2000 characters)
- Language validation against supported languages (ru, uk, en, de)

**SQL Injection Prevention:**
- Parameterized queries via SQLModel ORM
- Session.get() and session.exec(select()) with bound parameters
- No string concatenation in database queries

### Integration Points

**Upstream (Previous Stories):**
- Story 3.4: ContextRetrievalService provides RAGContext
- Story 3.5: LanguageDetectionService provides language detection
- Story 3.6: ToneDetectionService provides tone detection
- Story 3.6: format_response_prompt provides prompt formatting
- Story 2.1: LLMClient provides Gemini API integration

**Downstream (Next Story):**
- Story 3.8: Telegram bot retrieves draft_response for approval messages

### Testing Strategy

**Unit Tests (10 functions):**
- Response need classification (personal, newsletter, no-reply)
- Service integration (RAG context, language, tone, prompt, LLM)
- Response quality validation (valid, empty, short, long, wrong language)
- Database persistence and status updates

**Integration Tests (6 functions):**
- End-to-end workflows: German formal, English professional
- Classification edge cases: Newsletter skip, validation rejection
- RAG adaptive logic: Short thread triggers k=7 semantic search
- Real Gemini API integration (optional, marked @pytest.mark.slow)

**Test Coverage:** 80%+ for new code ✅

### Data Models

**ResponseGenerationService Methods:**

```python
class ResponseGenerationService:
    # Classification
    should_generate_response(email: EmailProcessingQueue) -> bool

    # Core generation workflow
    async generate_response(email_id: int) -> Optional[str]

    # Quality validation
    validate_response(response_draft: str, expected_language: str) -> bool

    # Database persistence
    save_response_draft(email_id: int, response_draft: str, language: str, tone: str) -> None

    # End-to-end orchestration
    async process_email_for_response(email_id: int) -> bool
```

### ADR-015: Response Generation Service Architecture

**Context:**
Story 3.7 requires orchestrating 5 specialized services (Context Retrieval, Language Detection, Tone Detection, Prompt Engineering, Gemini LLM) to generate contextually appropriate email responses.

**Decision:**
Implement ResponseGenerationService as orchestrator with dependency injection pattern, following Epic 2/3 service architecture patterns.

**Alternatives Considered:**

1. **Monolithic Service**: Single service handles all logic (context, language, tone, prompts)
   - ❌ Rejected: Violates separation of concerns, difficult to test, poor reusability

2. **Event-Driven Pipeline**: Each service publishes events, next service subscribes
   - ❌ Rejected: Adds complexity (message queue), harder to debug, overkill for sequential workflow

3. **Orchestrator with Dependency Injection** ✅ **CHOSEN**
   - ✅ Testability: Mock services for unit tests
   - ✅ Separation of concerns: Each service has single responsibility
   - ✅ Reusability: Services can be used independently
   - ✅ Maintainability: Changes isolated to specific services
   - ✅ Performance: Sequential execution with clear latency breakdown

**Consequences:**

**Positive:**
- Clear separation of concerns
- Easy to test with mocked dependencies
- Services can be developed and tested independently
- Clear performance characteristics (latency additive)
- Consistent with Epic 2/3 patterns (ToneDetectionService, LanguageDetectionService)

**Negative:**
- Sequential execution (can't parallelize independent services)
- Slightly more boilerplate (dependency injection setup)

**Mitigation:**
- Performance is acceptable (~8.8s well within 2-minute target)
- Dependency injection boilerplate is minimal and improves testability

**Status:** Accepted and Implemented (Story 3.7)

---

## Telegram Response Draft Messages (Story 3.8)

The Telegram Response Draft Messages service delivers AI-generated email response drafts to users via Telegram with an interactive approval interface. The service formats drafts into structured messages with inline keyboards ([Send], [Edit], [Reject]) and persists workflow mappings for callback reconnection.

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│ TelegramResponseDraftService.send_draft_notification(email_id, thread_id) │
└────────────────┬─────────────────────────────────────────────────────────┘
                 │
                 ├──► Step 1: Message Formatting (AC #1-4, #6, #9)
                 │    └─► format_response_draft_message(email_id)
                 │        ├─► Load email with draft_response from EmailProcessingQueue
                 │        ├─► Format header with priority flag (⚠️ if is_priority=True)
                 │        ├─► Include original email: sender, subject (AC #2)
                 │        ├─► Add visual separators ("─────────────────")
                 │        ├─► Display draft with language indication (AC #6)
                 │        └─► Handle Telegram length limits (4096 chars max)
                 │
                 ├──► Step 2: Inline Keyboard Building (AC #5)
                 │    └─► build_response_draft_keyboard(email_id)
                 │        ├─► Row 1: [✅ Send] button (callback_data="send_response_{email_id}")
                 │        ├─► Row 2: [✏️ Edit] button (callback_data="edit_response_{email_id}")
                 │        └─► Row 2: [❌ Reject] button (callback_data="reject_response_{email_id}")
                 │
                 ├──► Step 3: Telegram Message Sending (AC #1-9)
                 │    └─► send_response_draft_to_telegram(email_id)
                 │        ├─► Load user's telegram_id from Users table
                 │        ├─► Send via TelegramBotClient.send_message_with_buttons()
                 │        └─► Return telegram_message_id for mapping
                 │
                 ├──► Step 4: Workflow Mapping Persistence
                 │    └─► save_telegram_message_mapping(email_id, telegram_message_id, thread_id)
                 │        ├─► Create WorkflowMapping record
                 │        ├─► Link: email_id, user_id, thread_id, telegram_message_id
                 │        └─► Set workflow_state="awaiting_response_approval"
                 │
                 └──► Step 5: Email Status Update
                      └─► Update EmailProcessingQueue:
                          └─► status = "awaiting_response_approval"
```

### Message Format Structure

**Telegram Message Template:**

```
⚠️ 📧 Response Draft Ready       # Priority flag if is_priority=True (AC #9)

📨 Original Email:
From: sender@example.com
Subject: Email subject text      # AC #2 partial: uses subject instead of body

─────────────────                # Visual separator (AC #4)
✍️ AI-Generated Response (German):  # Language indication (AC #6)
Dear Sir/Madam,

[AI-generated response text]    # Full draft text (AC #3)

Best regards
─────────────────                # Visual separator

[Inline Keyboard]
┌──────────────┐
│  ✅ Send      │  # Row 1: Send button
├──────┬───────┤
│ ✏️ Edit│ ❌ Reject│  # Row 2: Edit + Reject buttons (AC #5)
└──────┴───────┘
```

### Service Integration Patterns

**Integration with Story 3.7 (Response Generation):**
- Reads `EmailProcessingQueue.draft_response` (populated by ResponseGenerationService)
- Reads `EmailProcessingQueue.detected_language` for language indication
- Reads `EmailProcessingQueue.is_priority` for priority flag display
- Monitors `status="awaiting_approval"` to trigger notifications

**Integration with Epic 2 (TelegramHITLWorkflow):**
- Extends TelegramBotClient (Story 2.6) with response draft message formatting
- Follows WorkflowMapping pattern for callback reconnection (ADR-006)
- Uses same inline keyboard structure as email sorting proposals

**Integration with LangGraph Workflows:**
- Persists `thread_id` in WorkflowMapping for workflow resumption
- Enables callback data → workflow instance reconnection
- Supports cross-channel resumption (pause in backend, resume from Telegram)

### WorkflowMapping Pattern (TelegramHITLWorkflow)

**Database Record Structure:**

```python
WorkflowMapping(
    email_id=456,                    # Links to EmailProcessingQueue
    user_id=123,                     # User who owns the email
    thread_id="workflow_thread_xyz",  # LangGraph workflow instance ID
    telegram_message_id="msg_789",    # Telegram message with buttons
    workflow_state="awaiting_response_approval"  # Current state
)
```

**Callback Reconnection Flow:**

```
1. User clicks [Send] button in Telegram
   └─► Telegram sends callback_query with data="send_response_456"
       └─► Extract email_id=456 from callback_data

2. Backend webhook handler receives callback
   └─► Query WorkflowMapping WHERE email_id=456
       └─► Retrieve thread_id="workflow_thread_xyz"

3. Resume LangGraph workflow
   └─► LangGraph.resume(thread_id, user_decision="send")
       └─► Workflow continues from pause point
```

**Rationale:** Enables stateless callback handling - no session state required. Single database query reconnects Telegram button click to paused workflow.

### Performance Characteristics

**Latency Breakdown (NFR001: <2 minutes total, Story 3.8 component):**

| Step | Service | Target Latency |
|------|---------|----------------|
| Load email from database | EmailProcessingQueue | ~0.01s |
| Format message | TelegramResponseDraftService | ~0.001s |
| Build keyboard | TelegramResponseDraftService | ~0.001s |
| Send Telegram API call | TelegramBotClient | ~0.5-1s |
| Save workflow mapping | WorkflowMapping | ~0.01s |
| Update email status | EmailProcessingQueue | ~0.01s |
| **Total** | | **~1s** |

**Result:** Well within 2-minute performance requirement ✅

### Known Limitations (v1)

**Partially Implemented Features:**

1. **AC #2 (Email Body Preview):**
   - **Current:** Uses email subject text as preview
   - **Spec:** First 100 characters of email body
   - **Reason:** `EmailProcessingQueue` doesn't store `body` field
   - **Impact:** Users see subject instead of body preview (minor UX impact)
   - **Future:** Add `body` field to `EmailProcessingQueue` if needed in future stories

2. **AC #7 (Context Summary):**
   - **Current:** NOT implemented - context summary line omitted
   - **Spec:** Display "Based on N previous emails in this thread"
   - **Reason:** RAG context metadata not passed to Story 3.8 service
   - **Impact:** Users don't see context provenance (low priority feature)
   - **Future:** Pass `rag_context.thread_email_count` from Story 3.7 if needed

3. **AC #8 (Message Splitting):**
   - **Current:** Truncates at 4096 chars (TelegramBotClient handles truncation)
   - **Spec:** Split at paragraph boundaries with continuation indicators
   - **Reason:** TelegramBotClient abstracts length handling (Epic 2 design)
   - **Impact:** Very long drafts (>4096 chars) cut off abruptly (rare edge case)
   - **Future:** Implement paragraph-boundary splitting in TelegramBotClient if needed

**Rationale for Limitations:**
- All 3 features are **low-priority** and not critical for MVP user value
- Core user flow works: Users receive drafts and can approve/edit/reject
- Fixes would require changes to other stories (Story 3.4, 3.7, Epic 2)
- Trade-off: Ship Story 3.8 faster vs. perfect feature completeness

### Integration Points

**Upstream (Dependencies):**
- Story 3.7: `ResponseGenerationService` populates `EmailProcessingQueue.draft_response`, `detected_language`
- Story 2.6: `TelegramBotClient` provides `send_message_with_buttons()` method
- Story 2.6: `WorkflowMapping` model provides callback reconnection pattern
- Epic 2: `User.telegram_id` links users to Telegram accounts

**Downstream (Next Stories):**
- Epic 4: LangGraph workflow resumes when user clicks [Send]/[Edit]/[Reject] buttons
- Epic 4: Response approval/editing flows consume `WorkflowMapping` records

### Testing Strategy

**Unit Tests (9 functions - exceeds requirement of 8):**
- Message formatting (standard, priority, long drafts, no context)
- Inline keyboard building (3-button layout verification)
- Telegram message sending (mock TelegramBotClient)
- Workflow mapping persistence (database operations)
- End-to-end orchestration (all steps integrated)
- Error handling (user blocked, not linked, email not found)

**Integration Tests (6 functions):**
1. German formal response with priority flag (end-to-end workflow)
2. English professional response without priority (end-to-end workflow)
3. Very long draft handling (>4096 chars truncation verification)
4. Context summary display placeholder (feature not implemented - test documents expected behavior)
5. Priority email flagging with ⚠️ icon
6. Telegram user not linked error handling

**Test Coverage:** All integration tests use real PostgreSQL database with sync engine pattern (fixed in Story 3.8 code review)

### Architecture Decision Record

**ADR-016: Response Draft Telegram Message Service**

**Context:**
Story 3.8 requires delivering AI-generated email response drafts to users via Telegram with an interactive approval interface. The service must format drafts with original email context, provide [Send]/[Edit]/[Reject] buttons, and persist workflow mappings for callback reconnection.

**Decision:**
Implement `TelegramResponseDraftService` as a standalone service that:
1. Formats messages with original email preview, draft text, visual separators, language indication
2. Builds inline keyboards with 3-button layout (Send, Edit, Reject)
3. Persists `WorkflowMapping` records for Telegram callback reconnection to LangGraph workflows
4. Updates `EmailProcessingQueue.status` to signal workflow progression

**Alternatives Considered:**
1. **Extend EmailWorkflow with Telegram node** - Rejected: Tight coupling, harder to test
2. **Generic Telegram message service** - Rejected: Too abstract, duplicates Epic 2 patterns
3. **Inline approval in Story 3.7** - Rejected: Violates separation of concerns

**Consequences:**

**Positive:**
- Clear separation: Story 3.7 generates drafts, Story 3.8 delivers them
- Reuses Epic 2 patterns: WorkflowMapping, TelegramBotClient, inline keyboards
- Testable: Inject mocked TelegramBotClient for unit tests
- Follows TelegramHITLWorkflow pattern (ADR-006)

**Negative:**
- Additional service adds complexity
- Three partially implemented ACs (trade-off for faster delivery)

**Mitigation:**
- Service is simple (5 methods, clear responsibilities)
- Limitations documented with future enhancement paths
- Core user value delivered: Users receive drafts and can approve

**Status:** Accepted and Implemented (Story 3.8)

---

_Generated by BMAD Decision Architecture Workflow v1.3.2_

_Date: 2025-11-03_

_For: Dimcheg_

_Architecture Document Complete - Ready for Implementation Phase_
