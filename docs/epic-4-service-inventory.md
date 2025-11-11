# Epic 4 Service Inventory: Reusable Epic 1-3 Components

**Date:** 2025-11-11
**Purpose:** Catalog all Epic 1-3 services, models, and utilities available for Epic 4 reuse
**Epic:** 4 - Configuration UI & Onboarding

---

## Overview

This document catalogs all services, models, and utilities created in Epic 1-3 that are available for reuse in Epic 4. Following the Epic 3 retrospective learning ("Service Reuse > Service Recreation"), this inventory prevents accidental duplication and ensures architectural consistency.

**Key Principle:** ALWAYS check this inventory before creating new services. If functionality exists, extend or compose existing services rather than recreating.

---

## Table of Contents

1. [Epic 1 Services (Foundation & Gmail)](#epic-1-services-foundation--gmail)
2. [Epic 2 Services (AI Sorting & Telegram)](#epic-2-services-ai-sorting--telegram)
3. [Epic 3 Services (RAG & Response Generation)](#epic-3-services-rag--response-generation)
4. [Database Models](#database-models)
5. [Utilities & Helpers](#utilities--helpers)
6. [Quick Reference Table](#quick-reference-table)

---

## Epic 1 Services (Foundation & Gmail)

### DatabaseService

**Location:** `backend/app/core/database.py`

**Purpose:** Async PostgreSQL session management and connection pooling

**Key Methods:**
```python
async def async_session() -> AsyncSession:
    """Create async database session"""
    async with AsyncSession(engine) as session:
        yield session

@property
def engine() -> AsyncEngine:
    """Get async database engine"""
```

**Epic 4 Usage:**
- All database operations (UserSettings, FolderCategories, OAuthTokens CRUD)
- Settings persistence
- OAuth token storage

**Pattern:**
```python
# backend/app/services/settings_service.py

class SettingsService:
    def __init__(self, db_service: DatabaseService):
        self.db = db_service

    async def get_settings(self, user_id: int):
        async with self.db.async_session() as session:
            result = await session.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            return result.scalar_one_or_none()
```

---

### GmailClient

**Location:** `backend/app/core/gmail_client.py`

**Purpose:** Gmail API integration for email operations

**Key Methods:**
```python
async def get_messages(self, user_id: int, query: str = "", max_results: int = 100):
    """Fetch emails with optional query"""

async def send_email(self, user_id: int, to: str, subject: str, body: str, thread_id: str | None):
    """Send email with optional threading"""

async def create_label(self, user_id: int, label_name: str, color: dict | None):
    """Create Gmail label"""

async def apply_label(self, user_id: int, message_id: str, label_id: str):
    """Apply label to email"""

async def refresh_access_token(self, user_id: int):
    """Refresh expired OAuth token"""
```

**Epic 4 Usage:**
- OAuth token refresh (automatic when tokens expire)
- Label creation for folder categories (Story 4.3)
- Label sync when user creates/edits folders

**Pattern:**
```python
# backend/app/services/settings_service.py

async def create_folder_category(self, user_id: int, name: str, color: str):
    """Create folder and sync with Gmail"""
    # Create database record
    folder = FolderCategory(user_id=user_id, name=name, color=color)
    await self.db.save(folder)

    # Create Gmail label (reuse GmailClient)
    label_id = await self.gmail_client.create_label(user_id, name, {"rgbColor": color})
    folder.gmail_label_id = label_id
    await self.db.save(folder)
```

---

### LLMClient

**Location:** `backend/app/core/llm_client.py`

**Purpose:** Google Gemini API integration for LLM operations

**Key Methods:**
```python
async def send_prompt(self, prompt: str, temperature: float = 0.7) -> str:
    """Send prompt to Gemini and get response"""

async def send_structured_prompt(self, prompt: str, schema: dict) -> dict:
    """Send prompt with JSON schema response"""
```

**Epic 4 Usage:**
- NOT directly used (onboarding doesn't require LLM)
- Available if needed for future features (e.g., folder suggestion based on email content)

---

## Epic 2 Services (AI Sorting & Telegram)

### TelegramBotClient

**Location:** `backend/app/core/telegram_bot.py`

**Purpose:** Telegram Bot API integration for messaging and inline keyboards

**Key Methods:**
```python
async def send_message(
    self,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "Markdown"
) -> Message:
    """Send message with optional inline keyboard"""

async def edit_message_text(
    self,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None
) -> Message:
    """Edit existing message"""

async def answer_callback_query(
    self,
    callback_query_id: str,
    text: str | None = None,
    show_alert: bool = False
):
    """Answer inline button callback"""
```

**Epic 4 Usage:**
- ALL Telegram bot interactions (onboarding wizard, settings commands, status messages)
- Inline keyboards for wizard navigation
- Message editing for dynamic updates

**Pattern:**
```python
# backend/app/services/onboarding_wizard.py

async def send_step_1_welcome(self, user_id: int):
    """Send welcome message with inline keyboard"""
    keyboard = [
        [InlineKeyboardButton("▶️ Start Setup", callback_data="onboarding_next_2")],
        [InlineKeyboardButton("❓ Learn More", callback_data="onboarding_help")]
    ]

    await self.bot.send_message(
        chat_id=user_id,
        text="Welcome to Mail Agent! 👋\n\nSetup takes 5-10 minutes.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
```

---

### EmailClassificationService

**Location:** `backend/app/services/email_classification.py`

**Purpose:** AI-powered email classification and folder recommendation

**Key Methods:**
```python
async def classify_email(self, email: Email) -> tuple[str, float]:
    """
    Classify email and recommend folder

    Returns:
        tuple[str, float]: (folder_name, confidence_score)
    """

async def should_generate_response(self, email: Email) -> bool:
    """Determine if email needs response (not newsletter/notification)"""
```

**Epic 4 Usage:**
- Folder recommendations during setup (Story 4.3)
- Suggest categories based on user's email patterns

**Pattern:**
```python
# backend/app/services/settings_service.py

async def suggest_folder_categories(self, user_id: int):
    """Suggest custom folders based on recent emails"""
    # Get recent emails
    recent_emails = await self.gmail_client.get_messages(user_id, max_results=50)

    # Analyze patterns
    suggested_folders = []
    for email in recent_emails:
        folder, confidence = await self.classification_service.classify_email(email)
        if confidence > 0.8 and folder not in suggested_folders:
            suggested_folders.append(folder)

    return suggested_folders[:5]  # Top 5 suggestions
```

---

### BatchNotificationService

**Location:** `backend/app/services/batch_notification_service.py`

**Purpose:** Batch email notifications at scheduled times

**Key Methods:**
```python
async def should_send_batch(self, user_id: int) -> bool:
    """Check if batch notifications should be sent now"""

async def send_batch_notification(self, user_id: int, emails: list[Email]):
    """Send batch notification with email list"""
```

**Epic 4 Usage:**
- Integrate with UserSettings.batch_time (Story 4.4)
- Use UserSettings.quiet_hours_start/end for scheduling

**Pattern:**
```python
# backend/app/services/batch_notification_service.py

async def should_send_batch(self, user_id: int) -> bool:
    """Check settings before sending batch"""
    # Get user settings (NEW from Epic 4)
    settings = await self.settings_service.get_settings(user_id)

    if not settings.batch_notifications_enabled:
        return False

    # Check batch time
    current_time = datetime.now(tz=timezone(settings.timezone)).strftime("%H:%M")
    if current_time != settings.batch_time:
        return False

    # Check quiet hours
    if self.is_quiet_hours(settings):
        return False

    return True
```

---

## Epic 3 Services (RAG & Response Generation)

### EmbeddingService

**Location:** `backend/app/services/embedding_service.py`

**Purpose:** Generate email embeddings using Gemini text-embedding-004

**Key Methods:**
```python
async def generate_embedding(self, text: str) -> list[float]:
    """
    Generate 768-dim embedding for text

    Args:
        text: Email content to embed

    Returns:
        list[float]: 768-dimensional vector
    """
```

**Epic 4 Usage:**
- NOT directly used (no embeddings during onboarding)
- Triggered in background after onboarding complete (Story 3.3 integration)

---

### EmailIndexingService

**Location:** `backend/app/services/email_indexing.py`

**Purpose:** Index email history into ChromaDB for RAG

**Key Methods:**
```python
async def start_initial_indexing(self, user_id: int):
    """Start background indexing of last 90 days (ADR-012)"""

async def get_indexing_progress(self, user_id: int) -> dict:
    """
    Get indexing progress

    Returns:
        dict: {"total": 500, "processed": 120, "status": "in_progress"}
    """
```

**Epic 4 Usage:**
- Triggered at end of onboarding wizard (Story 4.5)
- Progress displayed in `/status` command (Story 4.6)

**Pattern:**
```python
# backend/app/services/onboarding_wizard.py

async def send_step_6_completion(self, user_id: int):
    """Completion step - trigger indexing"""
    # Mark onboarding complete
    await self.settings_service.mark_onboarding_complete(user_id)

    # Send completion message
    await self.bot.send_message(
        user_id,
        "🎉 Setup Complete!\n\n"
        "Indexing your email history...\n"
        "This takes 5-10 minutes."
    )

    # Trigger background indexing (Epic 3 integration)
    await self.indexing_service.start_initial_indexing(user_id)
```

---

### ResponseGenerationService

**Location:** `backend/app/services/response_generation.py`

**Purpose:** Generate AI email responses using RAG context

**Key Methods:**
```python
async def generate_response_draft(
    self,
    email_id: int,
    user_id: int
) -> ResponseDraft:
    """
    Generate response draft for email

    Returns:
        ResponseDraft: {
            response_text: str,
            detected_language: str,
            tone: str
        }
    """
```

**Epic 4 Usage:**
- NOT directly used (no response generation during onboarding)
- Available for future "Test Response" feature in settings

---

### LanguageDetectionService

**Location:** `backend/app/services/language_detection.py`

**Purpose:** Detect email language (ru, uk, en, de)

**Key Methods:**
```python
def detect_language(self, text: str) -> tuple[str, float]:
    """
    Detect language of text

    Returns:
        tuple[str, float]: (language_code, confidence)
    """
```

**Epic 4 Usage:**
- Set UserSettings.language_preference based on detected language (Story 4.1)
- Auto-detect user's preferred language from Telegram messages

**Pattern:**
```python
# backend/app/services/settings_service.py

async def auto_detect_language_preference(self, user_id: int):
    """Auto-detect language from recent Telegram messages"""
    # Get recent messages from user
    recent_messages = await self.bot.get_user_messages(user_id, limit=10)

    # Detect language
    for message in recent_messages:
        lang, confidence = self.language_service.detect_language(message.text)
        if confidence > 0.8:
            # Update settings
            await self.update_language_preference(user_id, lang)
            return lang

    return "en"  # Default fallback
```

---

## Database Models

### User

**Location:** `backend/app/models/user.py`

**Purpose:** User account representation

**Fields:**
```python
class User(SQLModel, table=True):
    id: int (primary key)
    telegram_id: int (unique, not null)
    email: str | None
    created_at: datetime
    updated_at: datetime
```

**Epic 4 Usage:**
- Foreign key for UserSettings, FolderCategories, OAuthTokens
- User lookup by telegram_id

---

### Email / EmailProcessingQueue

**Location:** `backend/app/models/email.py`

**Purpose:** Email storage and workflow state

**Fields:**
```python
class EmailProcessingQueue(SQLModel, table=True):
    id: int (primary key)
    user_id: int (foreign key)
    message_id: str (Gmail message ID)
    gmail_thread_id: str
    sender: str
    recipient: str
    subject: str
    body: str
    classification: str  # "sort_only" | "needs_response"
    proposed_folder: str
    priority_score: float
    draft_response: str | None
    detected_language: str | None
    tone: str | None
    approval_status: str
    created_at: datetime
```

**Epic 4 Usage:**
- Statistics in `/status` command (count emails processed, approval rate)
- Recent activity feed (last 10 emails)

**Pattern:**
```python
# backend/app/services/status_service.py

async def get_email_statistics(self, user_id: int) -> dict:
    """Get email processing stats"""
    async with self.db.async_session() as session:
        # Count emails processed today
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        result = await session.execute(
            select(func.count(EmailProcessingQueue.id))
            .where(EmailProcessingQueue.user_id == user_id)
            .where(EmailProcessingQueue.created_at >= today_start)
        )
        emails_today = result.scalar_one()

        # Calculate approval rate
        result = await session.execute(
            select(
                func.count(case((EmailProcessingQueue.approval_status == "approved", 1))),
                func.count(EmailProcessingQueue.id)
            )
            .where(EmailProcessingQueue.user_id == user_id)
        )
        approved, total = result.one()
        approval_rate = (approved / total * 100) if total > 0 else 0

        return {
            "emails_today": emails_today,
            "approval_rate": round(approval_rate, 1),
            "total_processed": total
        }
```

---

## Utilities & Helpers

### Structlog Configuration

**Location:** `backend/app/core/logging.py`

**Purpose:** Structured logging for all services

**Usage:**
```python
import structlog

log = structlog.get_logger(__name__)

# Epic 4 example
async def create_folder_category(self, user_id: int, name: str):
    log.info(
        "creating_folder_category",
        user_id=user_id,
        folder_name=name
    )

    try:
        folder = await self.db.create_folder(user_id, name)
        log.info(
            "folder_category_created",
            user_id=user_id,
            folder_id=folder.id,
            folder_name=name
        )
    except Exception as e:
        log.error(
            "folder_creation_failed",
            user_id=user_id,
            folder_name=name,
            error=str(e)
        )
        raise
```

---

### Configuration (Pydantic Settings)

**Location:** `backend/app/core/config.py`

**Purpose:** Environment variable management

**Fields:**
```python
class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Gmail API
    GMAIL_CLIENT_ID: str
    GMAIL_CLIENT_SECRET: str
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/auth/gmail/callback"

    # Gemini API
    GEMINI_API_KEY: str

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_URL: str | None

    # Security (NEW for Epic 4)
    ENCRYPTION_KEY: str  # For OAuth token encryption

    class Config:
        env_file = ".env"
```

**Epic 4 Usage:**
- GMAIL_REDIRECT_URI for OAuth flow (ADR-017)
- ENCRYPTION_KEY for token encryption (security)

---

## Quick Reference Table

| Service | Location | Primary Epic 4 Use Case |
|---------|----------|-------------------------|
| **DatabaseService** | `backend/app/core/database.py` | All UserSettings, FolderCategories, OAuthTokens CRUD |
| **GmailClient** | `backend/app/core/gmail_client.py` | OAuth token refresh, Gmail label creation/sync |
| **TelegramBotClient** | `backend/app/core/telegram_bot.py` | ALL Telegram interactions (wizard, commands, keyboards) |
| **EmailClassificationService** | `backend/app/services/email_classification.py` | Folder recommendations during setup |
| **BatchNotificationService** | `backend/app/services/batch_notification_service.py` | Integrate with UserSettings batch_time/quiet_hours |
| **EmailIndexingService** | `backend/app/services/email_indexing.py` | Trigger background indexing after onboarding complete |
| **LanguageDetectionService** | `backend/app/services/language_detection.py` | Auto-detect language preference from Telegram messages |
| **User (Model)** | `backend/app/models/user.py` | Foreign key for all Epic 4 tables |
| **EmailProcessingQueue (Model)** | `backend/app/models/email.py` | Statistics in /status command (emails processed, approval rate) |
| **Structlog** | `backend/app/core/logging.py` | Structured logging for all Epic 4 services |
| **Settings (Config)** | `backend/app/core/config.py` | OAuth redirect URI, encryption key |

---

## Integration Checklist for Epic 4 Stories

Before implementing any Epic 4 story, verify:

- [ ] **DatabaseService** used for all database operations (NO raw SQLAlchemy imports)
- [ ] **async_session()** used consistently (NO sync Session pattern)
- [ ] **TelegramBotClient** used for all bot interactions (NO direct python-telegram-bot API)
- [ ] **GmailClient** used for Gmail operations (NO direct google-api-python-client calls)
- [ ] **Structlog** used for logging (NO print statements or standard logging module)
- [ ] **UserSettings** foreign key references User.id (consistent relationships)
- [ ] **Inline keyboards** used for all buttons (consistent UX with Epic 2)
- [ ] **Error handling** follows Epic 2/3 patterns (try/except with structured logging)
- [ ] **Type hints** on all functions (consistent with Epic 1-3)

---

## Anti-Patterns to Avoid (From Epic 3 Retrospective)

❌ **DO NOT:**
1. Create new database service (reuse DatabaseService)
2. Create new Telegram bot wrapper (reuse TelegramBotClient)
3. Use sync database sessions (use async_session() only)
4. Import raw SQLAlchemy (use SQLModel)
5. Use print statements (use structlog)
6. Recreate OAuth flow (extend GmailClient)
7. Build custom JSON serialization (SQLModel handles it)

✅ **DO:**
1. Import and inject existing services via Depends()
2. Use async/await for all I/O operations
3. Follow Epic 2/3 naming conventions (e.g., `handle_` for handlers)
4. Add comprehensive type hints
5. Write unit tests before integration tests
6. Document integration points in Dev Notes

---

## Epic 4 New Services to Create

These are the ONLY new services Epic 4 should create (all others should reuse):

1. **OnboardingWizard** (`backend/app/services/onboarding_wizard.py`)
   - Purpose: Conversational wizard state machine
   - Dependencies: TelegramBotClient, SettingsService, GmailClient

2. **SettingsService** (`backend/app/services/settings_service.py`)
   - Purpose: UserSettings, FolderCategories CRUD
   - Dependencies: DatabaseService, GmailClient

3. **OAuthService** (`backend/app/services/oauth_service.py`)
   - Purpose: Gmail OAuth flow management, token encryption
   - Dependencies: DatabaseService, GmailClient

4. **StatusService** (`backend/app/services/status_service.py`)
   - Purpose: System health checks, statistics aggregation
   - Dependencies: DatabaseService, GmailClient, TelegramBotClient

---

**Document Version:** 1.0
**Last Updated:** 2025-11-11
**Next:** Update story template with Epic 3 learnings
