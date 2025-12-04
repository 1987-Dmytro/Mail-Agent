# Mail Agent

An intelligent email management assistant that automatically sorts Gmail messages using AI and sends approval requests via Telegram, with multilingual response generation powered by RAG (Retrieval-Augmented Generation).

## Overview

Mail Agent helps you manage your inbox efficiently by:
- **Automated Email Sorting**: Uses Google's Gemini LLM to classify emails into custom categories
- **Telegram Approval Workflow**: Sends sorting proposals to your Telegram for quick approval
- **AI-Powered Response Generation**: Generates contextual email responses using RAG, preserving your writing style
- **Multilingual Support**: Automatically detects and responds in the email's original language
- **Vector Database Integration**: Uses ChromaDB for semantic search across your email history

## Project Status

✅ **MVP Complete** - Core features implemented and tested

**Completed Epics:**
- ✅ Epic 1: Backend Infrastructure (FastAPI, Database, Auth)
- ✅ Epic 2: Gmail Integration & AI Classification
- ✅ Epic 3: Telegram Notifications & RAG Response Generation
- ✅ Epic 4: Frontend Development (Next.js UI, Onboarding)

**Recent Updates (Dec 2025):**
- ✅ **Unified LLM Classification**: Single Gemini API call with RAG context
- ✅ **ChromaDB Integration**: Vector storage for semantic email search
- ✅ **Immediate Notifications**: Removed batch queue, all emails sent instantly
- ✅ **Bug Fixes**: State management, response draft handling
- ✅ **Frontend Fixes**: API response format, onboarding flow, dashboard statistics
- ✅ **Repository Cleanup**: Single monorepo, main branch only

## Prerequisites

Before setting up this project, ensure you have the following tools installed:

- **Python 3.13+** - Backend service runtime
- **uv** - Fast Python package installer ([install guide](https://github.com/astral-sh/uv))
- **Node.js 20+** and **npm** - Frontend development
- **Docker** and **Docker Compose** - Infrastructure and database management
- **Git** - Version control

### Recommended Tools

- **VS Code** with Python extension
- **Postman** or **HTTPie** - API testing
- **pgAdmin** or **DBeaver** - Database management

## Quick Start

### Option 1: Docker Compose (Recommended)

For the fastest setup using Docker Compose, see **[DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)**

### Option 2: Manual Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/1987-Dmytro/Mail-Agent.git
cd Mail-Agent
```

#### 2. Backend Setup

```bash
cd backend

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys (see Configuration section)

# Run database migrations
uv run alembic upgrade head

# Start development server
uv run uvicorn app.main:app --reload
```

Backend API will be available at http://localhost:8000

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env.local
# Edit .env.local with backend API URL (defaults to http://localhost:8000)

# Start development server
npm run dev
```

Frontend application will be available at http://localhost:3000

For detailed frontend documentation, see [frontend/README.md](frontend/README.md)

## Configuration

### Required API Keys

The following API keys are required to run the application:

1. **Gmail OAuth Credentials**
   - Obtain from [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
   - Required: Client ID and Client Secret
   - Add authorized redirect URI: `http://localhost:8000/api/v1/auth/gmail/callback`

2. **Telegram Bot Token**
   - Create bot via [@BotFather](https://t.me/BotFather) on Telegram
   - Save the bot token provided
   - Set bot commands for better UX

3. **Google Gemini API Key**
   - Obtain from [Google AI Studio](https://aistudio.google.com/)
   - Free tier available for development
   - Used for email classification and response generation

### Environment Variables

All environment variables are configured in `backend/.env`. See `backend/.env.example` for a complete template with documentation.

**⚠️ Security Warning**: Never commit `.env` files to version control. The `.gitignore` file is configured to prevent this, but always double-check before committing.

## Project Structure

```
Mail-Agent/
├── backend/              # FastAPI + LangGraph service
│   ├── app/              # Application code (API, services, models)
│   ├── alembic/          # Database migrations
│   ├── tests/            # Unit and integration tests
│   ├── docker-compose.yml # Backend services (PostgreSQL, Redis)
│   └── pyproject.toml    # Python dependencies (managed by uv)
├── frontend/             # Next.js configuration UI
│   ├── src/              # React components and pages
│   ├── tests/            # E2E tests (Playwright)
│   └── package.json      # Node.js dependencies
├── docs/                 # Project documentation
│   ├── epics/            # Epic specifications
│   ├── stories/          # Story documentation
│   └── sprints/          # Sprint tracking
├── docker-compose.yml    # Root docker-compose for full stack
├── DOCKER_QUICKSTART.md  # Quick start guide using Docker
└── README.md             # This file
```

## Email Processing Workflow

The system uses LangGraph for orchestrating the email processing workflow with the following automated steps:

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AUTOMATED EMAIL WORKFLOW                         │
└─────────────────────────────────────────────────────────────────────┘

1. 📧 Gmail Polling (Every 2 minutes)
   │
   ├─→ Celery Beat triggers polling task
   ├─→ Gmail API: Fetch new messages
   └─→ Duplicate detection via gmail_message_id

2. 🔍 Email Indexing & Vector Storage
   │
   ├─→ Extract email content (subject + body)
   ├─→ Generate embeddings with Gemini
   └─→ Store in ChromaDB for RAG retrieval

3. 🤖 Unified LLM Classification (Single API Call)
   │
   ├─→ Retrieve RAG context:
   │   ├─ Thread history (conversation context)
   │   └─ Semantic search (similar emails)
   │
   ├─→ Build classification prompt with:
   │   ├─ Email content (sender, subject, body preview)
   │   ├─ User's folder categories
   │   └─ RAG context for response generation
   │
   └─→ Gemini 2.5 Flash returns JSON:
       {
         "suggested_folder": "Government",
         "reasoning": "Official tax office communication...",
         "priority_score": 85,
         "confidence": 0.95,
         "needs_response": false,
         "response_draft": null
       }

4. 📱 Immediate Telegram Notification (All Emails)
   │
   ├─→ Format approval message:
   │   ├─ From: sender@example.com
   │   ├─ Subject: "Email subject..."
   │   ├─ AI Suggestion: "Government" folder
   │   ├─ Reasoning: "Official tax office..."
   │   └─ Priority indicator (⚠️ for score ≥ 70)
   │
   ├─→ Create inline keyboard:
   │   ├─ [✅ Approve] [❌ Reject]
   │   └─ [📁 Change Folder]
   │
   └─→ Send via Telegram Bot API
       └─→ Store telegram_message_id for tracking

5. ⏸️ Workflow Pause (await_approval)
   │
   ├─→ LangGraph checkpoint saves state
   ├─→ Email status → "awaiting_approval"
   └─→ Workflow waits for user decision

6. ✅ User Decision via Telegram Callback
   │
   ├─→ User clicks button in Telegram
   ├─→ Webhook receives callback_query
   ├─→ LangGraph resumes workflow from checkpoint
   │
   └─→ Decision handling:
       ├─ [Approve] → Move to suggested folder
       ├─ [Reject] → Keep in inbox
       └─ [Change] → Show folder selection menu

7. 📬 Gmail Action Execution
   │
   ├─→ Apply Gmail label (folder mapping)
   ├─→ Mark as read (if configured)
   └─→ Archive (if configured)

8. ✉️ Response Generation (if needs_response=true)
   │
   ├─→ Load response_draft from LLM
   ├─→ Detect language & tone
   ├─→ Format with user signature
   └─→ Send email via Gmail API

9. 🎉 Completion Notification
   │
   └─→ Edit original Telegram message:
       "✅ Email moved to [Folder Name]"
```

### Key Features

**🔄 Unified LLM Integration**
- Single Gemini API call determines folder, priority, and response needs
- RAG context from ChromaDB enhances classification accuracy
- Response drafts generated proactively if needed

**⚡ Immediate Notifications**
- All emails trigger instant Telegram notifications
- No batch queuing - real-time processing
- Priority indicator for urgent emails (score ≥ 70)

**🧠 Context-Aware Classification**
- Thread history: Previous emails in conversation
- Semantic search: Similar emails from past
- Token-optimized: ~2000 tokens per classification

**📊 State Management**
- LangGraph checkpoints enable pause/resume
- PostgreSQL persistence across service restarts
- Workflow state tracking per email

**🛡️ Error Handling**
- Graceful fallbacks for API failures
- Manual notification queue for Telegram errors
- Dead letter queue for persistent failures

## Documentation

Detailed documentation is available in the `docs/` directory:

- **[PRD.md](docs/PRD.md)** - Product Requirements Document
- **[architecture.md](docs/architecture.md)** - System architecture and technical decisions
- **[DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)** - Docker Compose setup guide
- **[docs/sprints/](docs/sprints/)** - Sprint planning and tracking
- **[docs/stories/](docs/stories/)** - Story specifications

## Development Workflow

This project follows the BMAD (Business Model Architecture Development) methodology:

1. Each epic is documented with technical specifications
2. Stories are broken down with acceptance criteria and tasks
3. Development follows story-by-story implementation
4. Code reviews and testing are mandatory before story completion

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **LangGraph** - Agent workflow orchestration
- **SQLModel** - SQL databases in Python with type safety
- **PostgreSQL** - Primary database
- **Redis** - Task queue and caching
- **Celery** - Background task processing
- **ChromaDB** - Vector database for RAG

### Frontend
- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - UI component library
- **Playwright** - E2E testing

### AI/ML
- **Google Gemini** - LLM for email classification and response generation
- **LangChain** - RAG implementation framework
- **ChromaDB** - Vector database for email history embeddings

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **uv** - Fast Python package management
- **Alembic** - Database migrations

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/test_email_indexing.py
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
npm run test

# Run E2E tests
npm run test:e2e:chromium
```

## Deployment

See [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) for Docker Compose deployment instructions.

For production deployment:
1. Set environment variables in production environment
2. Use `docker-compose up -d` to run services
3. Configure reverse proxy (nginx/traefik) for HTTPS
4. Set up backup strategy for PostgreSQL database
5. Configure monitoring and logging

## Contributing

This is currently a personal project. Contribution guidelines will be added in future releases.

## License

License information to be determined.

## Support

For issues or questions:
- Check documentation in `docs/` directory
- Review [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) for setup issues
- Check sprint status in `docs/sprints/sprint-status.yaml`

---

**Last Updated**: 2025-12-04
**Current Status**: MVP Complete (Epics 1-4) + Unified LLM + RAG Integration
**Recent Changes**:
- ✅ Unified LLM classification (single API call)
- ✅ RAG integration with ChromaDB
- ✅ Immediate Telegram notifications (batch removed)
- ✅ Bug fixes: state management, response draft handling

**Repository**: https://github.com/1987-Dmytro/Mail-Agent (Private)
**Branch**: main
