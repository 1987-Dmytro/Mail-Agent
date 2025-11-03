# Story 1.1: Project Infrastructure Setup

Status: review

## Story

As a developer,
I want to initialize the project repository with proper structure and development tools,
so that I have a clean, organized foundation for building the application.

## Acceptance Criteria

1. ✅ Git repository initialized with .gitignore for Python/Node.js projects
2. ✅ Project structure created with separate folders for backend (Python), frontend (Next.js), and shared configs
3. ✅ README.md created with project overview and setup instructions
4. ✅ Development environment documentation includes required tools (Python 3.13+, Node.js, etc.)
5. ✅ Virtual environment setup instructions documented (venv or poetry)
6. ✅ Environment variables template file (.env.example) created for API keys and configs

## Tasks / Subtasks

- [x] **Task 1: Initialize Git repository and create .gitignore** (AC: #1)
  - [x] Run `git init` in project root
  - [x] Create comprehensive .gitignore for Python (venv, __pycache__, .env) and Node.js (node_modules, .next)
  - [x] Add IDE-specific ignores (.vscode, .idea)
  - [x] Make initial commit with .gitignore

- [x] **Task 2: Set up project directory structure** (AC: #2)
  - [x] Create `backend/` directory for FastAPI + LangGraph service
  - [x] Create `frontend/` directory for Next.js configuration UI
  - [x] Create `docs/` directory for project documentation (already exists with PRD, architecture)
  - [x] Create `.github/workflows/` for CI/CD pipelines (future)
  - [x] Verify structure matches architecture.md "Project Structure" section

- [x] **Task 3: Create comprehensive README.md** (AC: #3, #4)
  - [x] Write project overview section explaining Mail Agent purpose
  - [x] Document required tools with versions:
    - Python 3.13+ (for backend)
    - Node.js 20+ and npm (for frontend)
    - Docker and Docker Compose (for infrastructure)
    - Git
  - [x] Add quick start guide (clone → setup → run)
  - [x] Include links to detailed setup documentation
  - [x] Add project status/badges placeholder

- [x] **Task 4: Document virtual environment setup** (AC: #5)
  - [x] Create `backend/README.md` with Python venv setup instructions:
    - `python3.13 -m venv venv`
    - `source venv/bin/activate` (macOS/Linux)
    - `venv\Scripts\activate` (Windows)
  - [x] Document alternative: Poetry setup instructions
  - [x] Explain when to activate/deactivate virtual environment
  - [x] Add troubleshooting section for common venv issues

- [x] **Task 5: Create environment variables template** (AC: #6)
  - [x] Create `backend/.env.example` with all required variables:
    - DATABASE_URL (PostgreSQL connection string)
    - REDIS_URL (Celery broker)
    - GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET (OAuth credentials)
    - TELEGRAM_BOT_TOKEN (bot API key)
    - GEMINI_API_KEY (LLM API key)
    - ENCRYPTION_KEY (for token encryption)
    - JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
    - ENVIRONMENT (development/staging/production)
    - LOG_LEVEL (DEBUG/INFO/WARN/ERROR)
  - [x] Add inline comments explaining each variable
  - [x] Document where to obtain API keys (Google Cloud Console, BotFather, etc.)
  - [x] Add security warning: "Never commit .env file to version control"

- [x] **Task 6: Verify and test setup** (Testing)
  - [x] Clone repository to fresh directory to test setup instructions
  - [x] Follow README.md setup steps exactly as written
  - [x] Verify all directories exist
  - [x] Verify .env.example can be copied to .env
  - [x] Document any missing steps or unclear instructions

## Dev Notes

### Architecture Alignment

**Template Foundation:**
- This story prepares the repository for cloning the FastAPI + LangGraph production template (Story 1.2)
- Structure must accommodate template's expected layout: `backend/app/`, `frontend/src/`, `docker-compose.yml`
- Template URL: `https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template`

**Project Structure (from architecture.md):**
```
mail-agent/
├── backend/          # FastAPI + LangGraph service
├── frontend/         # Next.js configuration UI
├── docs/             # Project documentation (PRD, architecture, epics)
├── .github/          # CI/CD workflows (future)
├── README.md         # Project overview and setup
└── .gitignore        # Python + Node.js ignores
```

**Key Decisions:**
- Use `venv` for Python virtual environment (simpler than Poetry for MVP)
- Backend structure will be populated by template in Story 1.2
- Frontend structure will be created from scratch in Epic 4, Story 4.1
- Environment variables centralized in `backend/.env` (template standard)

### Security Considerations

**Sensitive Data Protection:**
- .gitignore MUST include: `.env`, `*.env`, `venv/`, `__pycache__/`
- .env.example shows structure but contains NO real secrets (placeholder values)
- README.md must warn users to NEVER commit .env files
- Encryption key generation documented but NOT included in repository

**API Key Documentation:**
- Gmail OAuth: Google Cloud Console → APIs & Services → Credentials
- Telegram Bot: BotFather (@BotFather) via Telegram
- Gemini API: Google AI Studio (aistudio.google.com)
- All keys obtained in Story 1.4+ (this story just prepares templates)

### Testing Standards

**Verification Approach:**
- Manual testing via fresh clone (simulate new developer onboarding)
- Checklist-based validation (all AC items must pass)
- Documentation quality: Can a non-technical user follow instructions?
- No automated tests for this story (infrastructure setup)

### NFR Alignment

**NFR005 (Usability):**
- Setup instructions must be clear enough for non-technical users (10-minute setup target in Epic 4)
- README.md should be beginner-friendly with troubleshooting tips
- No assumed knowledge of Python/Node.js tooling

**NFR004 (Security):**
- .gitignore prevents accidental secret commits
- .env.example provides security guidance
- README.md includes security best practices section

### Project Structure Notes

**Alignment with Architecture:**
- Directory structure matches `architecture.md` Section: "Project Structure"
- Backend follows template conventions (preserved in Story 1.2)
- Frontend deferred to Epic 4 (minimal placeholder for now)
- Docs folder already exists with PRD, architecture, epics, tech-spec files

**No Conflicts Detected:**
- Structure is minimal and foundational
- Template integration in Story 1.2 will populate backend/ with FastAPI scaffold
- Frontend/ remains empty until Epic 4

### References

**Source Documents:**
- [PRD.md](../PRD.md#epic-list) - Epic 1 overview and goals
- [epics.md](../epics.md#story-11-project-infrastructure-setup) - Story 1.1 acceptance criteria
- [architecture.md](../architecture.md#project-structure) - Canonical project structure
- [architecture.md](../architecture.md#project-initialization) - Setup commands and prerequisites
- [tech-spec-epic-1.md](../tech-spec-epic-1.md#dependencies-and-integrations) - Environment configuration requirements

**Key Architecture Sections:**
- Project Structure: Lines 91-212 in architecture.md
- Project Initialization: Lines 7-74 in architecture.md
- Security Architecture: Lines 1258-1364 in architecture.md (.gitignore requirements)
- Development Environment: Lines 1654-1758 in architecture.md (prerequisites, setup)

### Change Log

**2025-11-03 - Initial Draft:**
- Story created from Epic 1, Story 1.1 in epics.md
- Acceptance criteria extracted from epic breakdown
- Tasks derived from AC items with architecture alignment
- Dev notes include security, testing, and NFR considerations
- First story in epic - no predecessor learnings

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-1-project-infrastructure-setup.context.xml)

### Agent Model Used

- claude-sonnet-4-5-20250929

### Debug Log References

**Implementation Plan:**
1. Initialize Git repository and create comprehensive .gitignore covering Python, Node.js, IDEs, and security files
2. Create project directory structure: backend/, frontend/, .github/workflows/
3. Create root README.md with project overview, prerequisites, quick start guide, and documentation links
4. Create backend/README.md with detailed venv setup instructions, troubleshooting, and Poetry alternative
5. Create backend/.env.example with all required environment variables, inline documentation, and security warnings
6. Verify setup with manual testing and validation checks

All tasks executed successfully without issues or deviations.

### Completion Notes List

**Directory Structure Created:**
- ✅ backend/ - Empty directory ready for FastAPI + LangGraph template (Story 1.2)
- ✅ frontend/ - Empty directory ready for Next.js UI (Epic 4)
- ✅ .github/workflows/ - Empty directory for future CI/CD pipelines
- ✅ docs/ - Already existed with PRD, architecture, epics documentation

**README.md Sections Completed:**
- Project overview with Mail Agent purpose and features
- Project status (In Development - Epic 1)
- Prerequisites with exact version requirements (Python 3.13+, Node.js 20+, Docker, Git)
- Quick start guide for backend and frontend
- Configuration guide with API key instructions
- Project structure diagram
- Technology stack breakdown
- Links to all documentation files

**backend/.env.example Variables Included:**
- Database: DATABASE_URL (PostgreSQL connection string)
- Redis: REDIS_URL (Celery broker and caching)
- Gmail OAuth: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REDIRECT_URI
- Telegram: TELEGRAM_BOT_TOKEN
- Gemini: GEMINI_API_KEY
- Security: ENCRYPTION_KEY, JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS
- Application: ENVIRONMENT, LOG_LEVEL
- Future: SENTRY_DSN, VECTOR_DB_URL, CORS_ORIGINS (commented out)

**Security Measures Implemented:**
- .gitignore prevents committing .env, *.env, venv/, __pycache__/, node_modules/, .next/, IDE files
- .env.example includes prominent security warning
- README.md emphasizes never committing .env files
- All inline comments explain where to obtain API keys securely

**Lessons Learned for Story 1.2:**
- Directory structure is ready for template cloning
- backend/ is empty as planned - template will populate it
- .env.example provides good foundation for template's expected variables
- Documentation is beginner-friendly and matches NFR005 (Usability)

**No Deviations:** All tasks completed exactly as planned in acceptance criteria.

### File List

**NEW:**
- README.md (root project overview)
- .gitignore (Python, Node.js, security patterns)
- backend/README.md (venv setup and troubleshooting)
- backend/.env.example (environment variables template)

**DIRECTORIES CREATED:**
- backend/
- frontend/
- .github/workflows/

**MODIFIED:**
- docs/sprint-status.yaml (story status: ready-for-dev → in-progress)
