# Technical Specification: Epic 4 - Configuration UI & Onboarding

**Version:** 1.0
**Date:** 2025-11-11
**Status:** Draft
**Epic:** 4 - Configuration UI & Onboarding

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Goals and Non-Goals](#goals-and-non-goals)
3. [Architecture Overview](#architecture-overview)
4. [Database Schema](#database-schema)
5. [API Endpoints](#api-endpoints)
6. [Telegram Bot Commands](#telegram-bot-commands)
7. [Onboarding Wizard Flow](#onboarding-wizard-flow)
8. [Integration with Epic 1-3](#integration-with-epic-1-3)
9. [Testing Strategy](#testing-strategy)
10. [Security Considerations](#security-considerations)
11. [Performance Requirements](#performance-requirements)
12. [Implementation Phases](#implementation-phases)

---

## Executive Summary

Epic 4 delivers a user-friendly configuration interface and guided onboarding flow through Telegram Bot UI. The system enables non-technical users to complete setup (Gmail OAuth, folder configuration, notification preferences) within 10 minutes through conversational wizard interactions.

**Key Decisions (from ADRs):**
- **ADR-016**: Telegram Bot UI for configuration (zero infrastructure cost)
- **ADR-017**: Localhost OAuth redirect for Gmail (officially supported)
- **ADR-018**: PostgreSQL UserSettings tables for persistence
- **ADR-019**: Conversational wizard with inline keyboards

**Business Value:**
- Accessible 10-minute setup process (NFR005)
- Zero technical knowledge required
- Zero infrastructure costs (Telegram Bot only)
- Multi-user ready (database-backed configuration)

---

## Goals and Non-Goals

### Goals

1. **User-Friendly Onboarding (NFR005)**
   - Complete setup in <10 minutes
   - Clear step-by-step wizard guidance
   - Resumable (user can close and continue later)
   - Error recovery with retry mechanisms

2. **Gmail OAuth Integration**
   - Secure localhost redirect flow
   - Token persistence and automatic refresh
   - Clear permission explanations

3. **Flexible Configuration**
   - Folder categories customization
   - Notification preferences (batch timing, quiet hours)
   - Language preference selection

4. **System Status Visibility**
   - Connection health (Gmail, Telegram)
   - Email processing statistics
   - RAG indexing progress

5. **Zero Infrastructure Cost**
   - Telegram Bot UI only (no web hosting)
   - PostgreSQL persistence (already running)
   - Localhost OAuth (no domain required)

### Non-Goals

1. **Web UI** - Deferred to Epic 5 (optional)
2. **Multi-User Management UI** - Single user MVP only
3. **Advanced Analytics Dashboard** - Basic statistics only
4. **Mobile App** - Telegram Bot sufficient
5. **Visual Customization** - Functional UI only, no themes/skins

---

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                        User (Dimcheg)                       │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      Telegram App                            │
│  - /start, /settings, /status commands                      │
│  - Inline keyboards for interactions                         │
│  - Rich text messages with emojis                           │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼ HTTPS (Telegram API)
┌─────────────────────────────────────────────────────────────┐
│                 Telegram Bot Backend                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   OnboardingWizard Service                             │ │
│  │   - State machine for wizard steps                     │ │
│  │   - Progress tracking in database                      │ │
│  │   - Conversational flow with inline buttons            │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   SettingsService                                       │ │
│  │   - UserSettings CRUD operations                       │ │
│  │   - Notification preferences management                │ │
│  │   - Folder categories management                       │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   OAuth Integration                                     │ │
│  │   - Gmail OAuth flow (localhost:8000)                  │ │
│  │   - Token persistence and refresh                      │ │
│  │   - Telegram notification on success                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                        │
│  - user_settings (preferences, onboarding progress)         │
│  - folder_categories (custom email categories)              │
│  - oauth_tokens (Gmail refresh tokens)                      │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Google OAuth & Gmail API                        │
│  - OAuth consent screen (user authorization)                │
│  - Access token exchange                                     │
│  - Refresh token management                                 │
└─────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
backend/
├── app/
│   ├── services/
│   │   ├── onboarding_wizard.py        # NEW - Wizard state machine
│   │   ├── settings_service.py         # NEW - Settings CRUD
│   │   ├── oauth_service.py            # NEW - OAuth flow management
│   │   └── status_service.py           # NEW - System health checks
│   ├── models/
│   │   ├── settings.py                 # NEW - UserSettings, FolderCategory, OAuthTokens
│   │   └── onboarding.py               # NEW - OnboardingState enum
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py                 # NEW - /auth/gmail/* endpoints
│   │       └── settings.py             # NEW - /settings/* endpoints
│   └── api/
│       └── telegram_handlers.py        # UPDATED - Onboarding commands
│
└── alembic/
    └── versions/
        └── xxxx_add_user_settings.py   # NEW - Schema migration
```

---

## Database Schema

### UserSettings Table

```sql
CREATE TABLE user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Notification Preferences
    batch_notifications_enabled BOOLEAN DEFAULT TRUE,
    batch_time VARCHAR(5) DEFAULT '18:00',      -- Format: "HH:MM"
    priority_alerts_enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_start VARCHAR(5) DEFAULT '22:00',
    quiet_hours_end VARCHAR(5) DEFAULT '08:00',

    -- Onboarding Progress
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_current_step INTEGER DEFAULT 1,  -- 1-6
    gmail_connected_at TIMESTAMP,
    telegram_linked_at TIMESTAMP,
    folders_setup_at TIMESTAMP,

    -- System Preferences
    language_preference VARCHAR(2) DEFAULT 'en', -- ru, uk, en, de
    timezone VARCHAR(50) DEFAULT 'Europe/Berlin',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_settings_user_id ON user_settings(user_id);
```

**SQLModel Definition:**

```python
from sqlmodel import SQLModel, Field
from datetime import datetime

class UserSettings(SQLModel, table=True):
    __tablename__ = "user_settings"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)

    # Notification preferences
    batch_notifications_enabled: bool = True
    batch_time: str = "18:00"
    priority_alerts_enabled: bool = True
    quiet_hours_start: str | None = "22:00"
    quiet_hours_end: str | None = "08:00"

    # Onboarding progress
    onboarding_completed: bool = False
    onboarding_current_step: int = 1
    gmail_connected_at: datetime | None = None
    telegram_linked_at: datetime | None = None
    folders_setup_at: datetime | None = None

    # System preferences
    language_preference: str = "en"
    timezone: str = "Europe/Berlin"

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### FolderCategories Table

```sql
CREATE TABLE folder_categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name VARCHAR(50) NOT NULL,
    keywords TEXT,                      -- Comma-separated: "finanzamt, tax, steuer"
    color VARCHAR(7),                   -- Hex color: "#FF5733"
    gmail_label_id VARCHAR(100),        -- Gmail label ID after sync

    is_default BOOLEAN DEFAULT FALSE,   -- True for system-created defaults
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, name)
);

CREATE INDEX idx_folder_categories_user_id ON folder_categories(user_id);
```

**SQLModel Definition:**

```python
class FolderCategory(SQLModel, table=True):
    __tablename__ = "folder_categories"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")

    name: str = Field(max_length=50)
    keywords: str | None = None
    color: str | None = None
    gmail_label_id: str | None = None

    is_default: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### OAuthTokens Table

```sql
CREATE TABLE oauth_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expiry TIMESTAMP NOT NULL,
    scope TEXT NOT NULL,                -- Space-separated scopes

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_oauth_tokens_user_id ON oauth_tokens(user_id);
CREATE INDEX idx_oauth_tokens_expiry ON oauth_tokens(token_expiry); -- For cleanup job
```

**SQLModel Definition:**

```python
class OAuthTokens(SQLModel, table=True):
    __tablename__ = "oauth_tokens"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)

    access_token: str
    refresh_token: str
    token_expiry: datetime
    scope: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## API Endpoints

### OAuth Endpoints

**Endpoint: `GET /auth/gmail/login`**

Initiate Gmail OAuth flow.

```python
@router.get("/auth/gmail/login")
async def gmail_login(user_id: int):
    """
    Initiate Gmail OAuth flow

    Query Params:
        user_id: Telegram user ID

    Returns:
        Redirect to Google OAuth consent screen
    """
    # Generate authorization URL
    auth_url = oauth_client.get_authorization_url(
        redirect_uri="http://localhost:8000/auth/gmail/callback",
        state=f"user_{user_id}",
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.labels",
            "https://www.googleapis.com/auth/gmail.modify"
        ]
    )

    return RedirectResponse(auth_url)
```

**Endpoint: `GET /auth/gmail/callback`**

Handle OAuth callback from Google.

```python
@router.get("/auth/gmail/callback")
async def gmail_callback(
    code: str,
    state: str,
    settings_service: SettingsService = Depends(),
    telegram_bot: TelegramBotClient = Depends()
):
    """
    Handle Gmail OAuth callback

    Query Params:
        code: Authorization code from Google
        state: State parameter (contains user_id)

    Returns:
        HTML success page
    """
    # Extract user_id from state
    user_id = int(state.split("_")[1])

    # Exchange code for tokens
    tokens = await oauth_client.exchange_code_for_tokens(code)

    # Save tokens to database
    await settings_service.save_oauth_tokens(
        user_id=user_id,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_expiry=tokens["expiry"],
        scope=tokens["scope"]
    )

    # Mark Gmail as connected in settings
    await settings_service.mark_gmail_connected(user_id)

    # Send Telegram notification
    await telegram_bot.send_message(
        chat_id=user_id,
        text="✅ Gmail connected successfully!\n\nReturning to onboarding wizard..."
    )

    # Trigger wizard continuation
    await onboarding_wizard.handle_gmail_connected(user_id)

    return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Gmail Connected</title>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; }
                h1 { color: #34A853; }
            </style>
        </head>
        <body>
            <h1>✅ Success!</h1>
            <p>Gmail connected successfully.</p>
            <p><strong>You can close this window and return to Telegram.</strong></p>
        </body>
        </html>
    """)
```

### Settings Endpoints (Internal)

**Endpoint: `GET /api/settings/{user_id}`**

Get user settings (used by backend services).

```python
@router.get("/api/settings/{user_id}")
async def get_settings(
    user_id: int,
    settings_service: SettingsService = Depends()
) -> UserSettings:
    """Get user settings"""
    return await settings_service.get_or_create_settings(user_id)
```

**Endpoint: `PATCH /api/settings/{user_id}/notifications`**

Update notification preferences (used by Telegram bot handlers).

```python
@router.patch("/api/settings/{user_id}/notifications")
async def update_notification_preferences(
    user_id: int,
    batch_enabled: bool | None = None,
    batch_time: str | None = None,
    priority_enabled: bool | None = None,
    quiet_hours_start: str | None = None,
    quiet_hours_end: str | None = None,
    settings_service: SettingsService = Depends()
):
    """Update notification preferences"""
    await settings_service.update_notification_preferences(
        user_id=user_id,
        batch_enabled=batch_enabled,
        batch_time=batch_time,
        priority_enabled=priority_enabled,
        quiet_hours_start=quiet_hours_start,
        quiet_hours_end=quiet_hours_end
    )

    return {"status": "updated"}
```

---

## Telegram Bot Commands

### Primary Commands

| Command | Description | Handler |
|---------|-------------|---------|
| `/start` | Start onboarding wizard or show status if complete | `handle_start_command()` |
| `/settings` | View and update notification preferences | `handle_settings_command()` |
| `/folders` | Manage email folder categories | `handle_folders_command()` |
| `/status` | Show system health and statistics | `handle_status_command()` |
| `/help` | Show available commands and tutorial | `handle_help_command()` |

### Admin Commands (Future)

| Command | Description | Handler |
|---------|-------------|---------|
| `/reset` | Reset onboarding and start over | `handle_reset_command()` |
| `/logs` | Show recent error logs | `handle_logs_command()` |

### Callback Queries (Inline Buttons)

| Callback Data | Description | Handler |
|---------------|-------------|---------|
| `onboarding_next_2` | Advance to step 2 (Gmail connection) | `handle_onboarding_next()` |
| `onboarding_next_3` | Advance to step 3 (Telegram confirmation) | `handle_onboarding_next()` |
| `settings_batch_time` | Update batch notification time | `handle_settings_batch_time()` |
| `folder_add` | Add new folder category | `handle_folder_add()` |
| `folder_edit_{id}` | Edit folder category | `handle_folder_edit()` |
| `folder_delete_{id}` | Delete folder category | `handle_folder_delete()` |

---

## Onboarding Wizard Flow

### State Machine

```
┌──────────────┐
│   START      │
│  (Step 1)    │
└──────────────┘
       │
       ▼
┌──────────────┐
│  WELCOME     │  "Welcome to Mail Agent! Let's set you up."
│  (Step 1)    │  [▶️ Start Setup]
└──────────────┘
       │
       ▼
┌──────────────┐
│GMAIL_CONNECT │  "Step 1 of 4: Connect Gmail"
│  (Step 2)    │  [🔗 Connect Gmail] → Opens OAuth URL
└──────────────┘  ⏳ Waits for OAuth callback...
       │
       ▼ (OAuth success)
┌──────────────┐
│TELEGRAM_CONF │  "Step 2 of 4: Telegram Connection ✅"
│  (Step 3)    │  "You're already connected!"
└──────────────┘  [▶️ Continue]
       │
       ▼
┌──────────────┐
│FOLDER_SETUP  │  "Step 3 of 4: Email Categories 📁"
│  (Step 4)    │  "Default categories created."
└──────────────┘  [✏️ Add Category] [✅ Use Defaults]
       │
       ▼
┌──────────────┐
│NOTIFICATION  │  "Step 4 of 4: Notification Settings 🔔"
│PREFERENCES   │  "Recommended defaults set."
│  (Step 5)    │  [⚙️ Customize] [✅ Use Defaults]
└──────────────┘
       │
       ▼
┌──────────────┐
│  COMPLETION  │  "🎉 Setup Complete!"
│  (Step 6)    │  "Mail Agent is now monitoring your inbox."
└──────────────┘  [🚀 Start Using Mail Agent]
       │
       ▼
┌──────────────┐
│   ACTIVE     │  Normal operation - user receives email notifications
│              │  Available commands: /settings, /status, /folders, /help
└──────────────┘
```

### Wizard Implementation (Pseudo-Code)

```python
class OnboardingWizard:
    """Conversational onboarding wizard"""

    async def handle_start_command(self, user_id: int):
        """Entry point: /start command"""
        settings = await self.settings_service.get_or_create_settings(user_id)

        if settings.onboarding_completed:
            await self.send_already_completed_message(user_id)
        else:
            await self.resume_from_step(user_id, settings.onboarding_current_step)

    async def resume_from_step(self, user_id: int, step: int):
        """Resume wizard from saved step"""
        if step == 1:
            await self.send_step_1_welcome(user_id)
        elif step == 2:
            await self.send_step_2_gmail_connection(user_id)
        elif step == 3:
            await self.send_step_3_telegram_confirmation(user_id)
        elif step == 4:
            await self.send_step_4_folder_setup(user_id)
        elif step == 5:
            await self.send_step_5_notification_preferences(user_id)
        elif step == 6:
            await self.send_step_6_completion(user_id)

    async def send_step_2_gmail_connection(self, user_id: int):
        """Step 2: Gmail OAuth"""
        # Check if already connected
        settings = await self.settings_service.get_settings(user_id)
        if settings.gmail_connected_at:
            await self.advance_to_step_3(user_id)
            return

        # Send connection button
        auth_url = f"http://localhost:8000/auth/gmail/login?user_id={user_id}"
        keyboard = [[InlineKeyboardButton("🔗 Connect Gmail", url=auth_url)]]

        await self.bot.send_message(
            user_id,
            "**Step 1 of 4: Connect Gmail** 📧\n\n"
            "Click the button below to authorize access.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await self.settings_service.update_onboarding_step(user_id, 2)

    async def handle_gmail_connected(self, user_id: int):
        """Called by OAuth callback"""
        await self.bot.send_message(user_id, "✅ Gmail connected!")
        await self.advance_to_step_3(user_id)

    async def advance_to_step_3(self, user_id: int):
        """Move to step 3"""
        await self.send_step_3_telegram_confirmation(user_id)
```

### Error Handling & Recovery

**Gmail OAuth Failure:**
```python
async def handle_gmail_oauth_error(self, user_id: int, error: str):
    """Handle OAuth error"""
    message = (
        "❌ Gmail connection failed\n\n"
        f"Error: {error}\n\n"
        "Common issues:\n"
        "• Browser blocked popup\n"
        "• Network problem\n\n"
        "Want to try again?"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 Try Again", callback_data="onboarding_retry_gmail")],
        [InlineKeyboardButton("❓ Get Help", url="https://docs.mailagent.app/troubleshoot")]
    ]

    await self.bot.send_message(user_id, message, reply_markup=InlineKeyboardMarkup(keyboard))
```

**Session Resumption:**
```python
async def handle_start_command(self, user_id: int):
    """Resume from last saved step"""
    settings = await self.settings_service.get_settings(user_id)

    if not settings.onboarding_completed:
        await self.bot.send_message(
            user_id,
            f"Welcome back! Resuming from Step {settings.onboarding_current_step}..."
        )
        await self.resume_from_step(user_id, settings.onboarding_current_step)
```

---

## Integration with Epic 1-3

### Reused Services

**From Epic 1 (Foundation & Gmail):**
- `DatabaseService` - Async session management
- `GmailClient` - OAuth token refresh, label creation
- `Users` table - User ID references

**From Epic 2 (AI Sorting & Telegram):**
- `TelegramBotClient` - Message sending, inline keyboards
- `EmailClassificationService` - Folder recommendations

**From Epic 3 (RAG & Response Generation):**
- `EmailIndexingService` - Trigger initial indexing after onboarding

### Integration Points

**1. Post-Onboarding Indexing:**
```python
async def send_step_6_completion(self, user_id: int):
    """Completion step - trigger indexing"""
    # Mark complete
    await self.settings_service.mark_onboarding_complete(user_id)

    # Send completion message
    await self.bot.send_message(
        user_id,
        "🎉 Setup Complete!\n\n"
        "Indexing your email history...\n"
        "This takes 5-10 minutes."
    )

    # Trigger background indexing (Story 3.3)
    await self.indexing_service.start_initial_indexing(user_id)
```

**2. Settings Integration with Batch Notifications:**
```python
# backend/app/services/batch_notification_service.py (Epic 2)

async def should_send_batch(self, user_id: int) -> bool:
    """Check if batch notifications enabled"""
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

**3. Folder Sync with Gmail Labels:**
```python
# backend/app/services/settings_service.py

async def create_folder_category(
    self,
    user_id: int,
    name: str,
    keywords: str | None = None,
    color: str | None = None
):
    """Create folder and sync with Gmail"""
    # Create database record
    folder = FolderCategory(
        user_id=user_id,
        name=name,
        keywords=keywords,
        color=color
    )

    async with self.db.async_session() as session:
        session.add(folder)
        await session.commit()
        await session.refresh(folder)

    # Create Gmail label (Story 1.8 integration)
    label_id = await self.gmail_client.create_label(user_id, name, color)

    # Update folder with Gmail label ID
    folder.gmail_label_id = label_id
    await session.commit()

    return folder
```

---

## Testing Strategy

### Unit Tests

**Test Coverage Targets:**
- OnboardingWizard: 100% (state machine logic critical)
- SettingsService: 100% (CRUD operations)
- OAuthService: 100% (token management)

**Test Files:**
```
backend/tests/
├── test_onboarding_wizard.py           # 15 unit tests
├── test_settings_service.py            # 12 unit tests
├── test_oauth_service.py               # 10 unit tests
└── test_status_service.py              # 8 unit tests
```

**Example Test:**
```python
# backend/tests/test_onboarding_wizard.py

async def test_resume_from_step_2_gmail_connection(mock_bot, mock_db):
    """Test resuming wizard from Gmail connection step"""
    wizard = OnboardingWizard(bot=mock_bot, db=mock_db)
    user_id = 12345

    # Setup: User at step 2, Gmail not connected
    mock_db.get_settings.return_value = UserSettings(
        user_id=user_id,
        onboarding_current_step=2,
        gmail_connected_at=None
    )

    # Execute
    await wizard.resume_from_step(user_id, step=2)

    # Assert: Gmail connection message sent
    mock_bot.send_message.assert_called_once()
    message = mock_bot.send_message.call_args[0][1]
    assert "Step 1 of 4: Connect Gmail" in message
    assert "http://localhost:8000/auth/gmail/login" in str(mock_bot.send_message.call_args)
```

### Integration Tests

**Test Scenarios:**
1. Complete onboarding flow (Step 1 → 6)
2. Gmail OAuth callback handling
3. Settings update via Telegram commands
4. Folder creation and Gmail label sync
5. Wizard resumption after close
6. Error recovery (OAuth failure, network errors)

**Test Files:**
```
backend/tests/integration/
├── test_onboarding_flow_e2e.py         # 8 integration tests
├── test_oauth_integration.py           # 6 integration tests
├── test_settings_telegram_integration.py # 10 integration tests
└── test_folder_gmail_sync.py           # 5 integration tests
```

**Example Integration Test:**
```python
# backend/tests/integration/test_onboarding_flow_e2e.py

async def test_complete_onboarding_flow_with_defaults(
    async_db_session,
    mock_telegram_bot,
    mock_gmail_client
):
    """Test complete onboarding flow using all defaults"""
    user_id = 12345

    # Step 1: Start wizard
    await wizard.handle_start_command(user_id)
    assert_message_sent(mock_telegram_bot, "Welcome to Mail Agent!")

    # Step 2: Click "Start Setup" button
    await wizard.handle_callback("onboarding_next_2", user_id)
    assert_message_sent(mock_telegram_bot, "Step 1 of 4: Connect Gmail")

    # Step 2: Gmail OAuth completes (simulated)
    await oauth_service.handle_oauth_callback(
        code="test_code_12345",
        state=f"user_{user_id}"
    )
    assert_message_sent(mock_telegram_bot, "✅ Gmail connected!")

    # Step 3: Telegram auto-confirmed
    assert_message_sent(mock_telegram_bot, "Step 2 of 4: Telegram Connection ✅")

    # Step 4: Use default folders
    await wizard.handle_callback("onboarding_next_5", user_id)
    folders = await db.get_user_folders(user_id)
    assert len(folders) == 4  # Important, Government, Clients, Newsletters
    assert all(f.is_default for f in folders)

    # Step 5: Use default notification settings
    await wizard.handle_callback("onboarding_next_6", user_id)
    settings = await db.get_settings(user_id)
    assert settings.batch_time == "18:00"
    assert settings.quiet_hours_start == "22:00"

    # Step 6: Completion
    assert_message_sent(mock_telegram_bot, "🎉 Setup Complete!")
    assert settings.onboarding_completed == True

    # Verify indexing triggered
    mock_gmail_client.get_messages.assert_called_once()  # Initial indexing started
```

### Usability Testing

**Target: 3-5 non-technical users**

**Test Protocol:**
1. Give user only Telegram bot link and say "Set up Mail Agent"
2. Observe without intervention (screen recording)
3. Measure completion time
4. Note confusion points, unclear messages
5. Collect feedback questionnaire

**Success Criteria:**
- 90%+ complete onboarding successfully
- <10 minutes completion time (NFR005)
- No critical usability issues

---

## Security Considerations

### OAuth Security

**1. State Parameter Validation:**
```python
@router.get("/auth/gmail/callback")
async def gmail_callback(code: str, state: str):
    """Validate state parameter to prevent CSRF"""
    # Extract user_id from state
    if not state.startswith("user_"):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user_id = int(state.split("_")[1])

    # Verify user exists
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Continue OAuth flow...
```

**2. Token Storage:**
```python
# Encrypt refresh tokens at rest
from cryptography.fernet import Fernet

class OAuthService:
    def __init__(self):
        self.cipher = Fernet(settings.ENCRYPTION_KEY)

    async def save_tokens(self, user_id: int, tokens: dict):
        """Encrypt and save OAuth tokens"""
        encrypted_refresh_token = self.cipher.encrypt(
            tokens["refresh_token"].encode()
        )

        await self.db.save_oauth_tokens(
            user_id=user_id,
            access_token=tokens["access_token"],  # Short-lived, OK to store plaintext
            refresh_token=encrypted_refresh_token.decode(),
            token_expiry=tokens["expiry"]
        )
```

**3. Localhost Verification:**
```python
@router.get("/auth/gmail/login")
async def gmail_login(user_id: int, request: Request):
    """Verify request from localhost only"""
    client_host = request.client.host

    # Only allow localhost requests
    if client_host not in ["127.0.0.1", "localhost"]:
        raise HTTPException(
            status_code=403,
            detail="OAuth flow only available from localhost"
        )

    # Continue OAuth flow...
```

### Input Validation

**Folder Category Name:**
```python
async def create_folder_category(
    self,
    user_id: int,
    name: str,
    keywords: str | None = None
):
    """Create folder with validation"""
    # Validate name
    if not name or len(name) > 50:
        raise ValueError("Name must be 1-50 characters")

    if not name.replace(" ", "").isalnum():
        raise ValueError("Name must be alphanumeric")

    # Prevent SQL injection (SQLModel handles this)
    # Prevent XSS (Telegram escapes HTML automatically)

    # Check for duplicates
    existing = await self.db.get_folder_by_name(user_id, name)
    if existing:
        raise ValueError(f"Category '{name}' already exists")

    # Create folder...
```

### Rate Limiting (Future)

```python
# Prevent abuse of OAuth endpoints
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@router.get(
    "/auth/gmail/login",
    dependencies=[Depends(RateLimiter(times=5, seconds=60))]
)
async def gmail_login(user_id: int):
    """Rate limit: 5 requests per minute per user"""
    pass
```

---

## Performance Requirements

### NFR005: Onboarding Completion <10 Minutes

**Target Flow (With Defaults):**
```
Step 1: Welcome                     30 seconds
Step 2: Gmail OAuth                 2 minutes (Google consent + redirect)
Step 3: Telegram Confirmation       10 seconds (auto-detected)
Step 4: Default Folders             30 seconds (click "Use Defaults")
Step 5: Default Settings            30 seconds (click "Use Defaults")
Step 6: Completion                  1 minute (read message, click "Start")
---------------------------------------------------------
Total: 5 minutes ✅ (50% under target)
```

**With Customization:**
```
Step 4: Add 3 custom folders        +3 minutes (typing names, keywords)
Step 5: Customize settings          +2 minutes (select times, toggle options)
---------------------------------------------------------
Total: 10 minutes ✅ (exactly at target)
```

### Database Performance

**Query Optimization:**
```sql
-- Index for settings lookups
CREATE INDEX idx_user_settings_user_id ON user_settings(user_id);

-- Index for folder queries
CREATE INDEX idx_folder_categories_user_id ON folder_categories(user_id);

-- Index for OAuth token cleanup
CREATE INDEX idx_oauth_tokens_expiry ON oauth_tokens(token_expiry);
```

**Expected Query Times:**
- Get settings: <5ms (indexed lookup)
- Get folders: <10ms (indexed + LIMIT 50)
- Save OAuth tokens: <20ms (single INSERT)

### Telegram Bot Response Time

**Target: <1 second for all command responses**

**Optimization:**
- Use async database queries (no blocking)
- Cache user settings in memory (Redis future)
- Inline keyboards pregenerated (no dynamic rendering)

```python
# backend/app/services/onboarding_wizard.py

async def send_step_4_folder_setup(self, user_id: int):
    """Fast folder setup message"""
    # Async database query (non-blocking)
    folders = await self.db.get_user_folders(user_id)

    # Pregenerate message (no complex logic)
    message = self._format_folder_list(folders)

    # Send immediately
    await self.bot.send_message(user_id, message)

    # Total time: <500ms ✅
```

---

## Implementation Phases

### Phase 1: Database & Core Services (Story 4.1)

**Deliverables:**
- Alembic migration for UserSettings, FolderCategories, OAuthTokens tables
- SettingsService with CRUD operations
- OAuthService with token management
- StatusService with health checks

**Acceptance Criteria:**
- All tables created successfully
- All services have unit tests (100% coverage)
- Database migration reversible

**Estimated Time:** 1-2 days

---

### Phase 2: Gmail OAuth Integration (Story 4.2)

**Deliverables:**
- `/auth/gmail/login` endpoint
- `/auth/gmail/callback` endpoint
- OAuth token encryption
- Telegram notification on success

**Acceptance Criteria:**
- OAuth flow completes successfully
- Tokens saved to database
- Refresh token encrypted at rest
- Integration tests passing (6 tests)

**Estimated Time:** 1-2 days

---

### Phase 3: Telegram Command Handlers (Story 4.3-4.4)

**Deliverables:**
- `/settings` command with inline keyboards
- `/folders` command for category management
- Callback query handlers for all buttons
- Settings update logic

**Acceptance Criteria:**
- All commands respond <1 second
- Settings persist correctly
- Folder changes sync with Gmail labels
- Integration tests passing (15 tests)

**Estimated Time:** 2-3 days

---

### Phase 4: Onboarding Wizard (Story 4.5)

**Deliverables:**
- OnboardingWizard service
- 6-step wizard flow
- Resumable state machine
- Error recovery

**Acceptance Criteria:**
- Complete flow <10 minutes (NFR005)
- Resumable from any step
- All 6 steps tested
- Integration test passing (8 tests)

**Estimated Time:** 2-3 days

---

### Phase 5: Status Commands (Story 4.6)

**Deliverables:**
- `/status` command with system health
- `/help` command with tutorial
- Statistics aggregation

**Acceptance Criteria:**
- Status shows Gmail, Telegram connection
- Email processing statistics accurate
- Help message comprehensive

**Estimated Time:** 1 day

---

### Phase 6: Testing & Polish (Story 4.7-4.8)

**Deliverables:**
- Usability testing with 3-5 users
- Completion time measurement
- Copy and messaging refinement
- Final integration tests

**Acceptance Criteria:**
- 90%+ completion rate
- <10 minutes average time (NFR005)
- All tests passing (29 unit + 29 integration = 58 tests)

**Estimated Time:** 2-3 days

---

**Total Estimated Time:** 10-15 days (2-3 weeks)

---

## Appendix A: Example Messages

### Welcome Message
```
Welcome to Mail Agent! 👋

I'm your intelligent email assistant. I'll help you:
✅ Sort emails automatically using AI
✅ Generate smart responses with conversation context
✅ Save 60-75% of your email time

**Setup takes about 5-10 minutes.**

Let's get started! 🚀

[▶️ Start Setup]  [❓ Learn More]
```

### Gmail Connection Message
```
**Step 1 of 4: Connect Gmail** 📧

Mail Agent needs access to your Gmail to:
• Read incoming emails
• Send responses
• Create labels for organization

Click the button below to authorize access.
You'll be redirected to Google's secure login page.

⚠️ Make sure the URL starts with `http://localhost:8000`

[🔗 Connect Gmail]  [❓ Why is this needed?]
```

### Folder Setup Message
```
**Step 3 of 4: Email Categories** 📁

I've created these default categories for you:

✅ **Important** - urgent, asap
✅ **Government** - finanzamt, auslaenderbehoerde, tax
✅ **Clients** - client, customer, partner
✅ **Newsletters** - newsletter, unsubscribe

Want to add more categories now, or use defaults?

[✏️ Add Category]  [✅ Use Defaults]
```

### Completion Message
```
🎉 **Setup Complete!** 🎉

You're all set! Mail Agent is now:
✅ Monitoring your Gmail inbox
✅ Classifying emails with AI
✅ Ready to generate smart responses

**What happens next?**
1. I'll start processing your emails
2. You'll receive sorting proposals here in Telegram
3. Approve/reject with one tap

**Indexing your email history...**
This takes 5-10 minutes for RAG context.
I'll notify you when complete! 📊

Use /help to see available commands.

[🚀 Start Using Mail Agent]  [📖 View Tutorial]
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-11
**Status:** Ready for Epic 4 Implementation
**Next:** Create Service Inventory document
