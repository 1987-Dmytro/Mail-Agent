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

**Recent Fixes (Dec 2025):**
- Fixed API response format consistency
- Fixed onboarding flow for existing users
- Fixed dashboard statistics accuracy
- Cleaned up repository structure (single monorepo, main branch)

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

**Last Updated**: 2025-12-01
**Current Status**: MVP Complete (Epics 1-4)
**Repository**: https://github.com/1987-Dmytro/Mail-Agent (Private)
**Branch**: main
