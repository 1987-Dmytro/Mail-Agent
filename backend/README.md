# Mail Agent - AI-Powered Email Management System

**Intelligent email processing with Gmail integration, RAG-based context retrieval, and Telegram notifications**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue.svg)](https://www.postgresql.org/)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Business Logic](#business-logic)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Workflows](#workflows)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)

---

## 🎯 Overview

Mail Agent is an AI-powered email management system that automatically:

1. **Polls Gmail** for new emails using Gmail API
2. **Classifies emails** into folders (Important/Work/Personal/Updates/Promotions/Spam)
3. **Detects language and tone** (English/Russian/Ukrainian/German, Formal/Professional/Casual)
4. **Analyzes if response needed** using multilingual question indicators
5. **Retrieves context** from email history using RAG (Retrieval-Augmented Generation)
6. **Generates draft responses** using Gemini LLM with full conversation context
7. **Sends approval requests** to Telegram for user review
8. **Processes approvals** and sends/discards emails based on user decision
9. **Indexes emails** into vector database for semantic search

The system uses **LangGraph** for workflow orchestration, enabling complex multi-step email processing pipelines with conditional routing, approval interrupts, and state persistence.

---

## ✨ Key Features

### Email Processing
- ✅ **Gmail Integration** - OAuth 2.0 authentication, real-time polling (every 2 minutes)
- ✅ **Multi-folder Classification** - 6 folder system with confidence scores
- ✅ **Multilingual Support** - English, Russian, Ukrainian, German detection
- ✅ **Tone Detection** - Formal/Professional/Casual classification
- ✅ **Smart Response Detection** - Context-aware "needs response" analysis

### AI & RAG System
- ✅ **Vector Database** - ChromaDB with 768-dim embeddings (Gemini text-embedding-004)
- ✅ **Semantic Search** - Cosine similarity for related email retrieval
- ✅ **Thread History Retrieval** - Full conversation context from Gmail threads
- ✅ **Sender History Retrieval** - Complete 90-day email timeline per sender
- ✅ **Temporal Filtering** - Recency boost for recent emails (30-90 day windows)
- ✅ **Context Assembly** - Combines thread + sender + semantic search results

### Response Generation
- ✅ **LangGraph Workflows** - State machine for email processing pipeline
- ✅ **Draft Generation** - Gemini-powered responses with context awareness
- ✅ **Approval Workflow** - Telegram-based human-in-the-loop approval
- ✅ **Draft Editing** - Users can modify AI-generated drafts before sending
- ✅ **Multilingual Responses** - Match language and tone of original email

### Notifications & Integrations
- ✅ **Telegram Bot** - Real-time notifications and approval requests
- ✅ **Batch Notifications** - Daily digest at 18:00 UTC
- ✅ **Inline Keyboards** - Interactive approve/reject/edit buttons
- ✅ **Webhook Support** - Real-time Telegram updates

### Background Processing
- ✅ **Celery Task Queue** - Async email processing and indexing
- ✅ **Periodic Tasks** - Gmail polling, daily digests, cleanup jobs
- ✅ **Incremental Indexing** - Index new emails as they arrive
- ✅ **Interrupted Job Recovery** - Resume indexing after crashes

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Mail Agent System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐     │
│  │   Frontend   │      │   Backend    │      │   Telegram   │     │
│  │   (Next.js)  │◄────►│   (FastAPI)  │◄────►│     Bot      │     │
│  │   Port 3001  │      │   Port 8000  │      │  Webhooks    │     │
│  └──────────────┘      └──────┬───────┘      └──────────────┘     │
│                                │                                     │
│                                │                                     │
│  ┌─────────────────────────────▼────────────────────────────────┐  │
│  │                    Core Services Layer                        │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │                                                                │  │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐             │  │
│  │  │   Gmail    │  │   Email    │  │  Response   │             │  │
│  │  │   Client   │  │Classifier  │  │  Generator  │             │  │
│  │  └────────────┘  └────────────┘  └─────────────┘             │  │
│  │                                                                │  │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐             │  │
│  │  │  Context   │  │  Embedding │  │  Language   │             │  │
│  │  │ Retrieval  │  │  Service   │  │  Detection  │             │  │
│  │  └────────────┘  └────────────┘  └─────────────┘             │  │
│  │                                                                │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  Background Processing                       │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │                                                               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │   │
│  │  │  Celery  │  │  Celery  │  │  Flower  │  │  Gmail   │    │   │
│  │  │  Worker  │  │   Beat   │  │(Monitor) │  │  Poller  │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │   │
│  │                                                               │   │
│  │  Periodic Tasks:                                             │   │
│  │  - Poll Gmail (every 2 min)                                  │   │
│  │  - Batch notifications (daily 18:00 UTC)                     │   │
│  │  - Daily digest (daily 18:30 UTC)                            │   │
│  │  - Cleanup old embeddings (daily 03:00 UTC, >90 days)        │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      Data Layer                              │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │                                                               │   │
│  │  ┌──────────────────┐  ┌──────────────────┐                 │   │
│  │  │   PostgreSQL     │  │     ChromaDB     │                 │   │
│  │  │   (Port 5432)    │  │  Vector Database │                 │   │
│  │  │                  │  │                  │                 │   │
│  │  │ • Users          │  │ • Email          │                 │   │
│  │  │ • Emails         │  │   Embeddings     │                 │   │
│  │  │ • Folders        │  │ • 768-dim        │                 │   │
│  │  │ • Telegram       │  │   vectors        │                 │   │
│  │  │ • Indexing       │  │ • Cosine         │                 │   │
│  │  │   Progress       │  │   similarity     │                 │   │
│  │  │                  │  │ • Metadata       │                 │   │
│  │  └──────────────────┘  └──────────────────┘                 │   │
│  │                                                               │   │
│  │  ┌──────────────────┐                                        │   │
│  │  │      Redis       │                                        │   │
│  │  │   (Port 6379)    │                                        │   │
│  │  │                  │                                        │   │
│  │  │ • Celery Broker  │                                        │   │
│  │  │ • Result Backend │                                        │   │
│  │  │ • Task Queue     │                                        │   │
│  │  └──────────────────┘                                        │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                Monitoring & Observability                    │   │
│  ├──────────────────────────────────────────────────────────────┤   │
│  │                                                               │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐             │   │
│  │  │Prometheus  │  │  Grafana   │  │  cAdvisor  │             │   │
│  │  │ Port 9090  │  │ Port 3000  │  │ Port 8080  │             │   │
│  │  └────────────┘  └────────────┘  └────────────┘             │   │
│  │                                                               │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### LangGraph Workflow Architecture

```
┌────────────────────────────────────────────────────────────────┐
│            Email Processing Workflow (LangGraph)               │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  START: New Email Received                                     │
│    │                                                            │
│    ▼                                                            │
│  ┌─────────────────────┐                                       │
│  │  Classification     │                                       │
│  │  (Gemini LLM)       │                                       │
│  ├─────────────────────┤                                       │
│  │ • Folder            │                                       │
│  │ • Language          │                                       │
│  │ • Tone              │                                       │
│  │ • Needs Response?   │                                       │
│  └──────────┬──────────┘                                       │
│             │                                                   │
│             │ needs_response=False                              │
│             ├───────────────────► [Archive Only]               │
│             │                                                   │
│             │ needs_response=True                               │
│             ▼                                                   │
│  ┌─────────────────────┐                                       │
│  │  Context Retrieval  │                                       │
│  │  (RAG System)       │                                       │
│  ├─────────────────────┤                                       │
│  │ 1. Thread History   │◄─── Gmail API                         │
│  │ 2. Sender History   │◄─── ChromaDB (metadata filter)        │
│  │ 3. Semantic Search  │◄─── ChromaDB (vector similarity)      │
│  └──────────┬──────────┘                                       │
│             │                                                   │
│             ▼                                                   │
│  ┌─────────────────────┐                                       │
│  │ Draft Generation    │                                       │
│  │ (Gemini LLM)        │                                       │
│  ├─────────────────────┤                                       │
│  │ • Match language    │                                       │
│  │ • Match tone        │                                       │
│  │ • Use context       │                                       │
│  │ • Generate response │                                       │
│  └──────────┬──────────┘                                       │
│             │                                                   │
│             ▼                                                   │
│  ┌─────────────────────┐                                       │
│  │ Telegram Approval   │                                       │
│  │ (Interrupt)         │ ◄──── HUMAN IN THE LOOP               │
│  ├─────────────────────┤                                       │
│  │ Send notification   │                                       │
│  │ Wait for response   │                                       │
│  └──────────┬──────────┘                                       │
│             │                                                   │
│             ├──► APPROVE ──────► Send Email (Gmail API)        │
│             │                                                   │
│             ├──► REJECT ───────► Discard Draft                 │
│             │                                                   │
│             └──► EDIT ─────────► Update Draft → Re-approve     │
│                                                                 │
│  END: Email Processed                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💼 Business Logic

### Email Classification

**Folder System:**
- **Important** - High-priority emails requiring immediate attention
- **Work** - Professional correspondence, projects, meetings
- **Personal** - Family, friends, personal matters
- **Updates** - Newsletters, receipts, confirmations
- **Promotions** - Marketing emails, offers, sales
- **Spam** - Unwanted or suspicious emails

**Classification Process:**
1. **LLM Analysis** - Gemini processes email subject, sender, and body
2. **Confidence Score** - 0.0-1.0 score for classification certainty
3. **Fallback Rules** - If LLM fails, use domain-based heuristics
4. **Language Detection** - Auto-detect en/ru/uk/de
5. **Tone Analysis** - Classify as formal/professional/casual

### Context Retrieval (RAG)

**Three-Stage Retrieval:**

1. **Thread History**
   - Fetch ALL emails in same Gmail thread
   - Sorted chronologically
   - Full conversation context

2. **Sender History** (NEW)
   - Retrieve ALL emails from sender (90 days)
   - Chronologically sorted
   - Solves cross-thread context (e.g., "Re: Праздники" finds "Праздники 2025")

3. **Semantic Search**
   - Generate embedding for current email
   - Query ChromaDB for k=10 most similar
   - Filter by sender + temporal window
   - Ranked by cosine similarity

**Assembly:**
```python
context = {
    "thread_history": [...]      # 3-10 emails
    "sender_history": [...]       # Up to 50 emails
    "semantic_results": [...]     # k=10 similar
}
```

### Response Generation

**Prompt Engineering:**
- Match language (en/ru/uk/de)
- Match tone (formal/professional/casual)
- Reference specific details from context
- Sign as "AI Assistant"

**Quality Controls:**
- Context length validation (max 128K tokens)
- Retry logic (3 attempts)
- Fallback to simpler prompts
- Language/tone verification

---

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI 0.115+
- **Python:** 3.13+
- **AI/LLM:**
  - Gemini API (google-generativeai 0.8.3+)
  - LangGraph 1.0+
  - LangChain 0.3+
- **Database:**
  - PostgreSQL 18
  - ChromaDB (embedded)
- **Task Queue:**
  - Celery 5.4+
  - Redis 7+
- **Package Manager:** uv 0.5+

### Integrations
- **Gmail API:** google-api-python-client 2.154+
- **Telegram:** python-telegram-bot 22.0+

### Monitoring
- **Logging:** Structlog
- **Metrics:** Prometheus + Grafana
- **Task Monitoring:** Flower

---

## 🚀 Quick Start

### Prerequisites

- Docker 24.0+ and Docker Compose 2.0+
- Gmail OAuth Credentials
- Telegram Bot Token
- Gemini API Key

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/mail-agent.git
cd mail-agent/backend

# 2. Copy environment file
cp .env.example .env

# 3. Configure .env (add your API keys)
nano .env

# 4. Start all services
docker-compose up -d

# 5. Check health
./scripts/health-check.sh

# 6. Access services
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Flower: http://localhost:5555
# - Grafana: http://localhost:3000
```

### Environment Variables

```bash
# Application
APP_ENV=development
JWT_SECRET_KEY=your-secret-key

# Database
POSTGRES_DB=mailagent
POSTGRES_USER=mailagent
POSTGRES_PASSWORD=mailagent_dev_password_2024
DATABASE_URL=postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Gmail OAuth
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REDIRECT_URI=http://localhost:8000/api/v1/auth/gmail/callback

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token

# Gemini
GEMINI_API_KEY=your-gemini-api-key

# ChromaDB
CHROMADB_PATH=./backend/data/chromadb
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/v1/              # API endpoints
│   ├── core/                # Core services (Gmail, Telegram, Vector DB)
│   ├── models/              # SQLAlchemy models
│   ├── prompts/             # LLM prompt templates
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic services
│   ├── tasks/               # Celery tasks
│   ├── workflows/           # LangGraph workflows
│   ├── celery.py            # Celery configuration
│   └── main.py              # FastAPI app
├── tests/                   # Test suite
├── alembic/                 # Database migrations
├── scripts/                 # Deployment scripts
├── data/chromadb/           # Vector database storage
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Container image
├── pyproject.toml           # Python dependencies
└── README.md                # This file
```

---

## 📚 API Documentation

### Base URL

- **Development:** `http://localhost:8000`
- **Interactive Docs:** http://localhost:8000/docs

### Key Endpoints

#### Authentication
```http
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/gmail/authorize
GET  /api/v1/auth/gmail/callback
```

#### Emails
```http
GET    /api/v1/emails/
GET    /api/v1/emails/{email_id}
POST   /api/v1/emails/{email_id}/classify
POST   /api/v1/emails/{email_id}/generate-response
POST   /api/v1/emails/send
```

#### Telegram
```http
POST /api/v1/telegram/webhook
POST /api/v1/telegram/link
GET  /api/v1/telegram/status
```

---

## 🗄️ Database Schema

### PostgreSQL Tables

#### users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    gmail_refresh_token TEXT,
    gmail_access_token TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### emails
```sql
CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    thread_id VARCHAR(255) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    folder_id INTEGER REFERENCES folders(id),
    sender VARCHAR(255) NOT NULL,
    subject TEXT,
    body TEXT,
    received_at TIMESTAMP,
    language VARCHAR(10),
    tone VARCHAR(20),
    needs_response BOOLEAN DEFAULT FALSE,
    indexed BOOLEAN DEFAULT FALSE
);
```

### ChromaDB Collections

#### email_embeddings

**Metadata:**
```python
{
    "hnsw:space": "cosine",
    "embedding_dimension": 768
}
```

**Document Metadata:**
```python
{
    "user_id": "1",
    "message_id": "19af5d9380191947",
    "sender": "user@example.com",
    "subject": "Meeting Notes",
    "normalized_subject": "meeting notes",
    "language": "en",
    "timestamp": 1733519949
}
```

---

## 🔄 Workflows

### Email Processing (LangGraph)

**State:**
```python
class EmailState(TypedDict):
    email_id: int
    folder: str
    language: str
    tone: str
    needs_response: bool
    thread_history: List[Dict]
    sender_history: List[Dict]
    semantic_results: List[Dict]
    draft_body: str
    approved: Optional[bool]
```

**Nodes:**
1. `classify_email` - Classification
2. `retrieve_context` - RAG retrieval
3. `generate_draft` - Response generation
4. `send_approval_request` - Telegram notification
5. `process_approval` - Email sending

**Flow:**
```
START → classify → [needs_response?]
                    ├─ No → archive
                    └─ Yes → retrieve_context
                            → generate_draft
                            → send_approval
                            → [INTERRUPT]
                            → [approved?]
                               ├─ Yes → send_email
                               ├─ No → discard
                               └─ Edit → re-approve
```

---

## 🧪 Testing

```bash
# Run all tests
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
  uv run pytest tests/ -v

# Run with coverage
uv run coverage run -m pytest tests/
uv run coverage report
```

---

## 🚢 Deployment

### Docker Deployment

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f app

# Scale workers
docker-compose up -d --scale celery-worker=3

# Stop services
docker-compose down
```

### Management Scripts

```bash
./scripts/start-all.sh      # Start all services
./scripts/stop-all.sh       # Stop all services
./scripts/logs.sh app       # View logs
./scripts/health-check.sh   # Check health
```

### Production Checklist

- [ ] Change `POSTGRES_PASSWORD`
- [ ] Change `JWT_SECRET_KEY`
- [ ] Generate new `ENCRYPTION_KEY`
- [ ] Enable SSL/TLS
- [ ] Configure backups
- [ ] Set up monitoring alerts

---

## 📊 Monitoring

**Grafana Dashboards:**
- System metrics (CPU, memory, disk)
- Celery task metrics
- Email processing metrics
- API performance

**Flower (Celery):**
- Access at http://localhost:5555
- View active tasks, workers, queues
- Monitor task success/failure rates

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/mail-agent/issues)
- **Documentation:** [Wiki](https://github.com/yourusername/mail-agent/wiki)

---

**Built with ❤️ using FastAPI, LangGraph, and Gemini**
