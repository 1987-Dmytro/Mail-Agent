# Mail Agent

An intelligent email management assistant that automatically sorts Gmail messages using AI and sends approval requests via Telegram, with multilingual response generation powered by RAG (Retrieval-Augmented Generation).

## Overview

Mail Agent helps you manage your inbox efficiently by:
- **Automated Email Sorting**: Uses Google's Gemini LLM to classify emails into custom categories
- **Telegram Approval Workflow**: Sends sorting proposals to your Telegram for quick approval
- **AI-Powered Response Generation**: Generates contextual email responses using RAG, preserving your writing style
- **Multilingual Support**: Automatically detects and responds in the email's original language

## Project Status

🚧 **In Development** - Currently implementing Epic 1: Foundation & Gmail Integration

## Prerequisites

Before setting up this project, ensure you have the following tools installed:

- **Python 3.13+** - Backend service runtime
- **Node.js 20+** and **npm** - Frontend development
- **Docker** and **Docker Compose** - Infrastructure and database management
- **Git** - Version control

### Recommended Tools

- **VS Code** with Python extension
- **Postman** or **HTTPie** - API testing
- **pgAdmin** or **DBeaver** - Database management

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd mail-agent
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3.13 -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Install dependencies (available in Story 1.2)
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys (see Configuration section)

# Run database migrations (available in Story 1.3)
alembic upgrade head

# Start development server (available in Story 1.2)
uvicorn app.main:app --reload
```

### 3. Frontend Setup (Epic 4)

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.local.example .env.local

# Start development server
npm run dev
```

## Configuration

### Required API Keys

The following API keys are required to run the application:

1. **Gmail OAuth Credentials** (Story 1.4)
   - Obtain from [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
   - Required: Client ID and Client Secret

2. **Telegram Bot Token** (Epic 2)
   - Create bot via [@BotFather](https://t.me/BotFather) on Telegram
   - Save the bot token provided

3. **Google Gemini API Key** (Epic 2)
   - Obtain from [Google AI Studio](https://aistudio.google.com/)
   - Free tier available for development

### Environment Variables

All environment variables are configured in `backend/.env`. See `backend/.env.example` for a complete template with documentation.

**⚠️ Security Warning**: Never commit `.env` files to version control. The `.gitignore` file is configured to prevent this, but always double-check before committing.

## Project Structure

```
mail-agent/
├── backend/          # FastAPI + LangGraph service
├── frontend/         # Next.js configuration UI
├── docs/             # Project documentation (PRD, architecture, epics)
├── .github/          # CI/CD workflows (future)
├── README.md         # This file
└── .gitignore        # Git ignore rules
```

## Documentation

Detailed documentation is available in the `docs/` directory:

- **[PRD.md](docs/PRD.md)** - Product Requirements Document
- **[architecture.md](docs/architecture.md)** - System architecture and technical decisions
- **[epics.md](docs/epics.md)** - Epic and story breakdown
- **[tech-spec-epic-1.md](docs/tech-spec-epic-1.md)** - Epic 1 technical specifications

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
- **SQLAlchemy** - Database ORM
- **PostgreSQL** - Primary database
- **Redis** - Task queue and caching
- **Celery** - Background task processing

### Frontend
- **Next.js 15** - React framework
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - UI component library

### AI/ML
- **Google Gemini** - LLM for email classification and response generation
- **LangChain** - RAG implementation
- **Vector Database** - Email history embeddings (TBD in Epic 3)

## Contributing

This is currently a personal project. Contribution guidelines will be added in future releases.

## License

License information to be determined.

## Support

For issues or questions, please refer to the project documentation in `docs/` directory.

---

**Last Updated**: 2025-11-03
**Current Epic**: Epic 1 - Foundation & Gmail Integration
**Next Milestone**: Backend service foundation (Story 1.2)
