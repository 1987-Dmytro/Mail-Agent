# Mail Agent Backend Service

**FastAPI + LangGraph Foundation for AI-Powered Email Management**

## Overview

This is the backend service for Mail Agent, an AI-powered email management system that uses Gmail API, Gemini LLM for intelligent email classification, and Telegram for user approvals.

**Status:** Epic 3 Complete - Story 3-11 in Review (RAG System & Response Generation)

---

## Technology Stack

- **Framework:** FastAPI 0.115.12+ (async web framework)
- **Python:** 3.13+ (latest stable)
- **AI/LLM:** LangGraph 1.0+ (deferred to Epic 2)
- **Database:** PostgreSQL 18 (setup in Story 1.3)
- **Task Queue:** Celery + Redis (setup in Epic 2)
- **Logging:** Structlog (JSON format)
- **Monitoring:** Prometheus + Grafana
- **Authentication:** JWT (setup in Story 1.4)

---

## Quick Start

### Prerequisites

- Python 3.13+
- Virtual environment (venv)
- PostgreSQL 18 (for Story 1.3+)
- Redis (for Epic 2+)

### Setup Instructions

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3.13 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # OR
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```

4. **Configure environment variables:**
   ```bash
   # .env file is already created from .env.example
   # Update the following variables as needed:
   # - Gmail OAuth credentials (Story 1.4)
   # - Telegram bot token (Epic 2)
   # - Gemini API key (Epic 2)
   # - Database credentials (Story 1.3)
   ```

5. **Run development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the API:**
   - API: http://localhost:8000
   - Health Check: http://localhost:8000/health
   - Interactive Docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

---

## Gmail API Setup

To enable Gmail integration, you need to create a Google Cloud Project and configure OAuth 2.0 credentials. Follow these step-by-step instructions:

### Step 1: Create Google Cloud Project

1. Navigate to [Google Cloud Console](https://console.cloud.google.com)
2. Sign in with your Google account
3. Click "Select a project" dropdown at the top
4. Click "NEW PROJECT"
5. Enter project name: `mail-agent` (or your preferred name)
6. Click "CREATE"
7. Wait for project creation (usually takes 10-30 seconds)

### Step 2: Enable Gmail API

1. Select your newly created project from the dropdown
2. Navigate to **APIs & Services** > **Library** (from the left sidebar or search bar)
3. Search for "Gmail API" in the search box
4. Click on **Gmail API** in the results
5. Click the blue **ENABLE** button
6. Wait for the API to be enabled (you'll see "API enabled" confirmation)

### Step 3: Create OAuth 2.0 Credentials

1. Navigate to **APIs & Services** > **Credentials** (left sidebar)
2. Click **+ CREATE CREDENTIALS** button at the top
3. Select **OAuth client ID** from the dropdown
4. If prompted to configure consent screen:
   - Click **CONFIGURE CONSENT SCREEN**
   - Choose **External** user type (or Internal if using Google Workspace)
   - Click **CREATE**
   - Fill in required fields:
     - App name: `Mail Agent`
     - User support email: Your email
     - Developer contact: Your email
   - Click **SAVE AND CONTINUE** through remaining steps
   - Click **BACK TO DASHBOARD**
   - Return to **Credentials** tab

5. Create OAuth client ID:
   - Click **+ CREATE CREDENTIALS** > **OAuth client ID**
   - Application type: **Web application**
   - Name: `Mail Agent Web Client` (or your preferred name)
   - **Authorized redirect URIs:**
     - For local development: `http://localhost:3000/auth/gmail/callback`
     - For production: `https://yourdomain.com/auth/gmail/callback`
   - Click **CREATE**

6. Download credentials:
   - A popup appears with your Client ID and Client Secret
   - **IMPORTANT:** Copy both values immediately
   - Click **DOWNLOAD JSON** to save credentials file (optional backup)

### Step 4: Configure OAuth Scopes

The Mail Agent requires the following OAuth scopes (automatically requested by the application):

- `https://www.googleapis.com/auth/gmail.readonly` - Read emails
- `https://www.googleapis.com/auth/gmail.modify` - Modify emails (apply labels)
- `https://www.googleapis.com/auth/gmail.send` - Send emails
- `https://www.googleapis.com/auth/gmail.labels` - Manage labels

These scopes are configured in the application code and don't require manual setup in Google Cloud Console.

### Step 5: Configure OAuth Consent Screen (Test Users for Development)

For development/testing, you need to add test users to bypass Google's verification process:

1. Navigate to **APIs & Services** > **OAuth consent screen**
2. Scroll to **Test users** section
3. Click **+ ADD USERS**
4. Enter email addresses of users who will test the app (including yourself)
5. Click **SAVE**

**Note:** While in "Testing" mode, only added test users can authenticate. To make the app public, you'll need to submit it for Google's verification (not required for MVP).

### Step 6: Add Credentials to Environment Variables

1. Copy `.env.example` to `.env` (if not already done):
   ```bash
   cp .env.example .env
   ```

2. Open `.env` file and update Gmail OAuth settings:
   ```bash
   # Gmail OAuth Credentials (from Step 3)
   GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GMAIL_CLIENT_SECRET=your-client-secret
   GMAIL_REDIRECT_URI=http://localhost:3000/auth/gmail/callback
   ```

3. Generate encryption key for token storage:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Copy the output and add to `.env`:
   ```bash
   ENCRYPTION_KEY=your-generated-key-here
   ```

### Gmail API Quotas and Limits

**Free Tier Quotas:**
- Daily quota: **1,000,000,000 quota units/day**
- Per-user rate limit: **250 quota units/second**
- Batch requests: **1000 requests/second**

**Common Operations Cost:**
- List messages: 5 quota units
- Get message: 5 quota units
- Send message: 100 quota units
- Modify message (apply label): 5 quota units

**For Mail Agent MVP:** The free tier is sufficient for up to 10,000 emails/day with typical usage patterns.

**Monitor Quotas:**
- Navigate to **APIs & Services** > **Dashboard**
- Click on **Gmail API**
- View "Queries" graph to monitor usage

### Troubleshooting Common OAuth Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `redirect_uri_mismatch` | Redirect URI in code doesn't match Google Cloud Console | Verify `GMAIL_REDIRECT_URI` in `.env` exactly matches authorized redirect URI in OAuth client settings |
| `access_denied` | User denied permissions | Ensure user grants all requested scopes during OAuth flow |
| `invalid_client` | Client ID or secret is incorrect | Double-check `GMAIL_CLIENT_ID` and `GMAIL_CLIENT_SECRET` in `.env` |
| `unauthorized_client` | OAuth client not authorized for Gmail API | Ensure Gmail API is enabled in Google Cloud Console |
| `quota_exceeded` | Daily quota limit reached | Wait for quota reset (midnight Pacific Time) or request quota increase |
| `User is not authorized` | Test user not added in OAuth consent screen | Add user email to test users list in OAuth consent screen settings |

### Security Best Practices

1. **Never commit `.env` file to git** - Already added to `.gitignore`
2. **Rotate secrets regularly** - Regenerate OAuth credentials and encryption keys every 90 days
3. **Use environment-specific redirect URIs:**
   - Development: `http://localhost:3000/auth/gmail/callback`
   - Staging: `https://staging.yourdomain.com/auth/gmail/callback`
   - Production: `https://yourdomain.com/auth/gmail/callback`
4. **Store production secrets in secure vault** - Use services like AWS Secrets Manager, Google Secret Manager, or HashiCorp Vault
5. **Monitor OAuth logs** - Regularly check Google Cloud Console > OAuth consent screen > User metrics for suspicious activity

---

## Environment Variables

See `.env.example` for all configuration options. Key variables:

### Application Settings
- `PROJECT_NAME`: Application name (Mail Agent)
- `VERSION`: Current version (0.1.0)
- `APP_ENV`: Environment (development/staging/production)
- `DEBUG`: Debug mode (true/false)

### API Settings
- `API_V1_STR`: API version prefix (/api/v1)
- `ALLOWED_ORIGINS`: CORS allowed origins (localhost:3000,127.0.0.1:3000)

### Database Settings (Story 1.3)
- `POSTGRES_HOST`: PostgreSQL host
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_PORT`: Database port (5432)

### Gmail API Settings (Story 1.4)
- `GMAIL_CLIENT_ID`: OAuth client ID
- `GMAIL_CLIENT_SECRET`: OAuth client secret
- `GMAIL_REDIRECT_URI`: OAuth redirect URI

### Telegram Bot Setup (Epic 2 - Story 2.4)

Mail Agent uses a Telegram bot to send email sorting proposals and receive user approval/rejection through interactive buttons. This section covers bot creation, configuration, and testing.

#### Step 1: Create Telegram Bot via BotFather

1. **Open Telegram** and search for **@BotFather** (official Telegram bot for creating bots)
2. **Start conversation** by sending `/start` to @BotFather
3. **Create new bot** by sending `/newbot` command
4. **Provide bot name**: Enter a display name (e.g., "Mail Agent Bot")
   - This name will be shown in chats
   - Can contain spaces and special characters
5. **Provide bot username**: Enter a unique username ending in "bot" (e.g., "MailAgentBot" or "YourNameMailBot")
   - Must be unique across all Telegram
   - Can only contain letters, numbers, and underscores
   - Must end with "bot"
6. **Copy bot token**: BotFather will provide a token like:
   ```
   7223802190:AAHCN-N0nmQIXS_J1StwX_urv2ddeSnCMjo
   ```
   - Keep this token **secret** - it grants full access to your bot

#### Step 2: Configure Bot Token

1. **Add to `.env` file**:
   ```bash
   # In backend/.env file:
   TELEGRAM_BOT_TOKEN=7223802190:AAHCN-N0nmQIXS_J1StwX_urv2ddeSnCMjo
   ```

2. **Verify `.env.example` has placeholder**:
   ```bash
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

3. **Security Notes**:
   - **NEVER** commit bot token to git
   - Token is already gitignored in `.env`
   - Rotate token if accidentally exposed via @BotFather `/revoke` command

#### Step 3: Optional Bot Customization

You can enhance your bot's appearance via @BotFather commands:

- `/setdescription` - Set bot description (shown before starting chat)
- `/setabouttext` - Set about text (shown in bot profile)
- `/setuserpic` - Set bot profile picture
- `/setcommands` - Set command menu (auto-complete for /start, /help, /test)

Example commands to set:
```
start - Link your Telegram account
help - Show available commands
test - Send a test message
```

#### Step 4: Test Bot Connectivity

1. **Start the backend server**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Test via Telegram**:
   - Open Telegram and search for your bot (e.g., @MailAgentBot)
   - Send `/start` - bot should respond with welcome message
   - Send `/help` - bot should show available commands
   - Send `/test` - bot should confirm connectivity and show your Telegram ID

3. **Test via API** (requires authenticated user with `telegram_id`):
   ```bash
   curl -X POST http://localhost:8000/api/v1/test/telegram \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"message": "Test notification from Mail Agent"}'
   ```

#### Bot Commands

The bot implements the following commands (Story 2.4):

| Command | Description | Status |
|---------|-------------|--------|
| `/start` | Display welcome message and account linking instructions | ✅ Implemented |
| `/start <code>` | Link Telegram account using 6-character code | ⏳ Story 2.5 |
| `/help` | Show available commands and usage instructions | ✅ Implemented |
| `/test` | Verify bot connectivity and display Telegram ID | ✅ Implemented |

#### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | (required) | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_URL` | `""` | Webhook URL for production (empty = long polling) |
| `TELEGRAM_WEBHOOK_SECRET` | `""` | Webhook secret for signature verification |

**Note**: Mail Agent MVP uses **long polling mode** (simpler setup, no HTTPS required). Webhook mode can be configured in production for better scalability.

### Telegram Account Linking (Epic 2 - Story 2.5)

Mail Agent uses a secure linking code system to associate user Telegram accounts with their Mail Agent accounts. This enables users to receive email notifications and approve actions directly in Telegram.

#### User Linking Flow

The complete linking flow works as follows:

1. **User logs into Mail Agent web app** (JWT authenticated)
2. **User navigates to Settings → Telegram Connection**
3. **Frontend calls API to generate linking code**:
   ```http
   POST /api/v1/telegram/generate-code
   Authorization: Bearer <jwt_token>
   ```
4. **User sees 6-digit code displayed** (e.g., "A3B7X9")
5. **User opens Telegram** and searches for bot (e.g., @MailAgentBot)
6. **User sends linking command**: `/start A3B7X9`
7. **Bot validates code and links account**
8. **Frontend polls status endpoint** to detect successful linking:
   ```http
   GET /api/v1/telegram/status
   Authorization: Bearer <jwt_token>
   ```
9. **User sees confirmation** on both web app and Telegram

#### API Endpoints

##### POST /api/v1/telegram/generate-code

Generate a unique 6-digit linking code for Telegram account connection.

**Authentication**: JWT Bearer token required
**Rate Limiting**: Recommended to prevent code generation spam

**Request**:
```bash
curl -X POST http://localhost:8000/api/v1/telegram/generate-code \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "code": "A3B7X9",
    "expires_at": "2025-11-07T12:15:00Z",
    "bot_username": "MailAgentBot",
    "instructions": "Open Telegram, search for @MailAgentBot, and send: /start A3B7X9"
  }
}
```

**Error Responses**:
- `400 Bad Request`: User already has Telegram account linked
- `401 Unauthorized`: Invalid or missing JWT token
- `500 Internal Server Error`: Code generation failed

##### GET /api/v1/telegram/status

Check if user's Telegram account is currently linked.

**Authentication**: JWT Bearer token required

**Request**:
```bash
curl -X GET http://localhost:8000/api/v1/telegram/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response** (200 OK) - Not Linked:
```json
{
  "success": true,
  "data": {
    "linked": false,
    "telegram_id": null,
    "telegram_username": null,
    "linked_at": null
  }
}
```

**Response** (200 OK) - Linked:
```json
{
  "success": true,
  "data": {
    "linked": true,
    "telegram_id": "123456789",
    "telegram_username": "johndoe",
    "linked_at": "2025-11-07T11:45:23Z"
  }
}
```

#### Bot Command: /start [code]

Link your Telegram account using the 6-digit code from the web app.

**Usage**:
```
/start A3B7X9
```

**Success Response**:
```
✅ Your Telegram account has been linked successfully!

You'll receive email notifications here. You can start approving
sorting proposals and response drafts right from this chat.
```

**Error Responses**:
- `❌ Invalid linking code. Please check and try again.` - Code doesn't exist
- `❌ This code has expired. Generate a new code (codes expire after 15 minutes).` - Code too old
- `❌ This code has already been used. Generate a new code.` - Code reused
- `❌ This Telegram account is already linked to another Mail Agent account.` - Telegram ID conflict

#### Code Validation Rules

The linking system implements strict validation to ensure security:

1. **Code Format**:
   - Exactly 6 characters
   - Alphanumeric uppercase only (A-Z, 0-9)
   - Generated using cryptographic randomness (`secrets` module)

2. **Expiration Window**:
   - Codes expire after **15 minutes** from generation
   - Expired codes are rejected with clear error message
   - Balances security (short window) and usability (enough time)

3. **Single-Use Enforcement**:
   - Each code can only be used **once**
   - After successful linking, code is marked as used
   - Prevents replay attacks and code reuse

4. **Account Constraints**:
   - One Telegram account per Mail Agent user
   - One Mail Agent account per Telegram ID
   - Attempting to link already-linked accounts returns error

5. **Case Insensitivity**:
   - Codes are normalized to uppercase for validation
   - User can type `/start a3b7x9` or `/start A3B7X9` - both work

#### Security Considerations

- **Cryptographic Randomness**: Uses Python's `secrets` module (not `random`) for unpredictable code generation
- **Short Expiration**: 15-minute window minimizes brute-force attack risk
- **Code Space**: 36^6 = 2,176,782,336 possible codes (collision extremely rare)
- **No Authentication Required for Bot**: Telegram's built-in user authentication is trusted
- **Audit Trail**: All linking events logged with structured logging (user_id, telegram_id, code, success/failure)

#### Database Schema

**LinkingCodes Table**:
- `id`: Primary key
- `code`: Unique 6-char code (indexed)
- `user_id`: Foreign key to users table (cascade delete)
- `used`: Boolean flag (prevents reuse)
- `expires_at`: Timestamp with timezone (UTC)
- `created_at`: Timestamp with timezone (UTC)

**Users Table Extensions**:
- `telegram_id`: Unique Telegram user ID (indexed)
- `telegram_username`: Telegram username (optional)
- `telegram_linked_at`: Timestamp when account was linked (UTC)

#### Frontend Integration Example

```javascript
// 1. Generate linking code
const generateCode = async () => {
  const response = await fetch('/api/v1/telegram/generate-code', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwtToken}`
    }
  });
  const data = await response.json();
  displayCode(data.data.code);
  displayInstructions(data.data.instructions);
  startPolling(); // Poll /status until linked
};

// 2. Poll status endpoint
const pollStatus = async () => {
  const response = await fetch('/api/v1/telegram/status', {
    headers: {
      'Authorization': `Bearer ${jwtToken}`
    }
  });
  const data = await response.json();

  if (data.data.linked) {
    showSuccessMessage();
    stopPolling();
  }
};
```

#### Troubleshooting

**Bot doesn't start:**
- Check `TELEGRAM_BOT_TOKEN` is set in `.env`
- Verify token is valid (test with @BotFather `/getme`)
- Check backend logs for initialization errors

**Bot doesn't respond to commands:**
- Ensure backend server is running
- Check bot polling is active (look for "telegram_bot_started" log)
- Verify bot isn't blocked by Telegram (spam detection)

**"User blocked bot" error:**
- User needs to unblock bot in Telegram
- Check bot wasn't deleted or banned
- User can restart bot with `/start`

For more details, see:
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

### Telegram Callback Handlers (Epic 2 - Story 2.7)

Mail Agent uses Telegram inline keyboard buttons to enable users to approve, reject, or modify AI email sorting suggestions directly in the chat. This section explains the callback handler workflow and data formats.

#### Email Workflow Architecture

When a user receives an email sorting proposal in Telegram and clicks one of the action buttons, the following workflow executes:

**Complete Callback Handler Flow:**

1. **Telegram sends CallbackQuery** to bot via long polling
2. **`handle_callback_query()`** parses `callback_data` to extract action and email_id
3. **User ownership validated** - ensures telegram_id owns the email being processed (security check)
4. **WorkflowMapping queried** - lookup by email_id to retrieve LangGraph `thread_id`
5. **LangGraph workflow state loaded** from PostgreSQL checkpoint using `thread_id`
6. **State updated** with user decision:
   - `user_decision = "approve"` → Apply proposed folder
   - `user_decision = "reject"` → Mark as rejected, no Gmail action
   - `user_decision = "change_folder"` → Display folder selection menu
7. **Workflow resumed** from `await_approval` node using `workflow.ainvoke()`
8. **`execute_action` node** applies Gmail label (if approved/changed) or updates status (if rejected)
9. **`send_confirmation` node** edits original Telegram message with result confirmation
10. **Workflow completes** and reaches END terminal state

**Workflow State Machine:**
```
START → extract_context → classify → send_telegram → await_approval
          ↓ (User clicks button)
await_approval → execute_action → send_confirmation → END
```

#### Callback Data Format

Telegram inline buttons send structured callback data to identify the action and target email:

**Primary Actions:**
- **Approve**: `approve_{email_id}`
  - Example: `approve_123`
  - Action: Apply AI-suggested folder label to email

- **Reject**: `reject_{email_id}`
  - Example: `reject_456`
  - Action: Mark email as rejected, leave in inbox

- **Change Folder**: `change_{email_id}`
  - Example: `change_789`
  - Action: Display folder selection menu with user's configured folders

**Folder Selection (Two-Step Flow):**
- **Select Folder**: `folder_{folder_id}_{email_id}`
  - Example: `folder_5_123`
  - Action: Apply selected folder (folder_id=5) instead of AI suggestion

#### Code Example: Workflow Resumption

```python
# User clicks [Approve] button in Telegram
callback_data = "approve_123"  # From Telegram CallbackQuery

# 1. Parse callback data
action, email_id, folder_id = parse_callback_data(callback_data)
# Returns: ("approve", 123, None)

# 2. Validate user ownership (security check)
telegram_user_id = query.from_user.id
if not validate_user_owns_email(telegram_user_id, email_id, db):
    await query.answer("❌ Unauthorized")
    return

# 3. Lookup workflow instance by email_id
workflow_mapping = db.query(WorkflowMapping).filter_by(email_id=email_id).first()
thread_id = workflow_mapping.thread_id  # e.g., "email_123_abc-def-ghi"

# 4. Resume LangGraph workflow with user decision
workflow = create_email_workflow(db, gmail_client, telegram_bot)
config = {"configurable": {"thread_id": thread_id}}

# Load current state from PostgreSQL checkpoint
state_snapshot = await workflow.aget_state(config)
state = dict(state_snapshot.values)

# Update state with user decision
state["user_decision"] = "approve"

# Resume workflow execution
await workflow.ainvoke(state, config=config)

# Workflow continues: execute_action → send_confirmation → END
```

#### Security Validation

**User Ownership Check (`validate_user_owns_email`):**

The callback handler validates that the Telegram user owns the email before processing any action:

```python
async def validate_user_owns_email(telegram_user_id: int, email_id: int, db: AsyncSession) -> bool:
    # 1. Get user by telegram_id
    user = db.query(User).filter_by(telegram_id=str(telegram_user_id)).first()
    if not user:
        return False

    # 2. Get email and verify ownership
    email = db.query(EmailProcessingQueue).filter_by(id=email_id).first()
    if not email or email.user_id != user.id:
        return False

    return True
```

**Security Features:**
- ✅ Prevents users from approving emails they don't own
- ✅ Structured logging of all authorization failures
- ✅ Error messages don't leak sensitive information ("Unauthorized" only)

#### Workflow Nodes

**`execute_action` Node (Story 2.7):**
- Receives state with `user_decision` from callback handler
- Applies appropriate action based on decision:
  - **Approve**: Apply `proposed_folder_id` label via Gmail API
  - **Reject**: Update status to "rejected", skip Gmail API
  - **Change Folder**: Apply `selected_folder_id` label
- Updates `EmailProcessingQueue.status` to "completed" or "rejected"
- Error handling: Catches `GmailAPIError`, logs with structured logging, sets `error_message` in state

**`send_confirmation` Node (Story 2.7):**
- Formats confirmation message based on `final_action`:
  - Approved: `✅ Email sorted to "{folder_name}"`
  - Rejected: `❌ Email sorting rejected. Email remains in inbox.`
  - Changed: `✅ Email sorted to "{selected_folder_name}"`
- Edits original Telegram message using `telegram_message_id` from state
- Terminal node - workflow reaches END after confirmation

#### Testing Callback Handlers

**Unit Tests:**
```bash
# Run callback handler unit tests (15 tests)
DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db" \
  uv run pytest tests/test_telegram_callbacks.py -v
```

**Integration Tests:**
```bash
# Run approval workflow integration tests (3 tests)
DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db" \
  uv run pytest tests/integration/test_approval_workflow_integration.py -v
```

**Test Coverage:**
- ✅ Callback data parsing (approve/reject/change/folder formats)
- ✅ Malformed data handling (invalid format, non-numeric IDs)
- ✅ User ownership validation (valid, user not found, email not found, ownership mismatch)
- ✅ Unauthorized callback rejection
- ✅ Complete approve workflow (email → classification → approval → Gmail label application)
- ✅ Complete reject workflow (status update without Gmail API call)
- ✅ Complete change folder workflow (menu display → selection → label application)

#### Error Handling

**Gmail API Failures:**
```python
try:
    success = await gmail_client.apply_label(
        message_id=email.gmail_message_id,
        label_id=folder.gmail_label_id
    )
except Exception as e:
    logger.error(
        "execute_action_gmail_error",
        email_id=email_id,
        error=str(e),
        error_type=type(e).__name__
    )
    state["error_message"] = f"Gmail API error: {str(e)}"
    return state
```

**Common Error Scenarios:**
- Gmail API rate limit exceeded → Logged, error message set in state
- Gmail message not found (deleted) → Logged, error message set in state
- Network timeout → Logged, error message set in state
- Invalid label ID → Logged, error message set in state

All errors are logged with structured logging and surfaced to the user via Telegram error messages.

#### Troubleshooting

**Callback buttons not responding:**
- Check `CallbackQueryHandler` is registered in `TelegramBotClient.initialize()`
- Verify bot polling is active
- Check backend logs for callback handler errors

**"Unauthorized" errors:**
- Verify user's Telegram account is linked (check `users.telegram_id`)
- Ensure email belongs to the user (check `email_processing_queue.user_id`)
- Check structured logs for ownership validation failures

**Workflow not resuming:**
- Verify `WorkflowMapping` entry exists for email_id
- Check PostgreSQL `checkpoints` table has state for thread_id
- Ensure database connection pool is healthy

**For More Information:**
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph Workflow Resumption](https://langchain-ai.github.io/langgraph/how-tos/persistence/)
- [python-telegram-bot CallbackQueryHandler](https://docs.python-telegram-bot.org/en/stable/telegram.ext.callbackqueryhandler.html)

---

### Gemini LLM Integration (Epic 2 - Story 2.1)

Mail Agent uses Google's Gemini 2.5 Flash for AI-powered email classification and response generation. This section covers setup, configuration, and troubleshooting.

#### API Key Setup

1. **Get API Key from Google AI Studio** (4 steps):
   - Visit https://makersuite.google.com/app/apikey
   - Sign in with your Google account
   - Click "Create API Key" button
   - Copy the generated API key (starts with `AIza...`)

2. **Add to Environment Variables**:
   ```bash
   # In backend/.env file:
   GEMINI_API_KEY=your-api-key-here
   GEMINI_MODEL=gemini-2.5-flash
   ```

3. **Security Notes**:
   - **NEVER** commit `.env` to git (already in `.gitignore`)
   - API key should be kept confidential
   - Rotate API key if accidentally exposed
   - Use separate API keys for development and production

#### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | (required) | API key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model identifier (use latest flash model) |
| `DEFAULT_LLM_TEMPERATURE` | `0.1` | Temperature for generation (0.0-1.0, lower = more deterministic) |
| `MAX_TOKENS` | `500` | Maximum tokens per response |
| `MAX_LLM_CALL_RETRIES` | `3` | Number of retry attempts for transient errors |

#### Free Tier Limits

Gemini 2.5 Flash offers **unlimited free tier** usage with the following limits:

- **Token Rate Limit**: 1,000,000 tokens/minute
- **Cost**: FREE (no usage fees)
- **Monitoring**: Application tracks token usage via Prometheus metrics

**Recommendation**: Set up alerts if approaching 900,000 tokens/minute (90% of limit)

```python
# Token usage tracking is automatic - check metrics at:
# http://localhost:8000/metrics
# Metric name: gemini_token_usage_total{operation="classification"}
```

#### Testing Connectivity

Use the test endpoint to verify Gemini API integration:

```bash
# Text mode
curl -X POST http://localhost:8000/api/v1/test/gemini \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Say hello in 5 words",
    "response_format": "text"
  }'

# JSON mode (for structured classification)
curl -X POST http://localhost:8000/api/v1/test/gemini \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Classify email: From tax@gov.de Subject: Tax deadline",
    "response_format": "json"
  }'
```

#### Troubleshooting Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `GEMINI_API_KEY environment variable not set` | API key not configured | Add `GEMINI_API_KEY` to `.env` file |
| `Invalid Gemini API key` (403) | API key is incorrect or revoked | Generate new API key from Google AI Studio |
| `Rate limit exceeded` (429) | Exceeded 1M tokens/minute | Wait 1 minute and retry (automatic retry with exponential backoff) |
| `Request timeout` | Gemini API slow response or network issue | Check internet connection, API will retry automatically |
| `Blocked prompt` (400) | Prompt violated Gemini safety filters | Rephrase prompt to avoid inappropriate content |

#### Fallback Strategy for Gemini Unavailability

In case Gemini API becomes unavailable, the following fallback options are available:

**Scenarios Requiring Fallback**:
- API downtime or maintenance
- Rate limit exhaustion (> 1M tokens/minute sustained)
- API key revocation or expiration
- Geographic restrictions (API not available in region)

**Fallback Options** (Implementation deferred to post-MVP):

1. **Option A: Claude 3.5 Sonnet** (Anthropic API)
   - **Pros**: High quality, excellent multilingual support, strong reasoning
   - **Cons**: Paid API ($3/$15 per 1M tokens), requires separate API key
   - **Configuration**: Add `ANTHROPIC_API_KEY` to `.env`
   - **Use Case**: Production environments with budget for premium LLM

2. **Option B: GPT-4o Mini** (OpenAI API)
   - **Pros**: Fast, cost-effective ($0.15/$0.60 per 1M tokens), good quality
   - **Cons**: Paid API, requires OpenAI account
   - **Configuration**: Add `OPENAI_API_KEY` to `.env`
   - **Use Case**: Cost-conscious production with moderate quality needs

3. **Option C: Rule-Based Fallback** (No LLM)
   - **Pros**: Zero cost, always available, no external dependencies
   - **Cons**: No response generation, limited classification accuracy
   - **Implementation**: Keyword matching for email classification
   - **Use Case**: Temporary fallback until LLM service restored

**Implementation Approach** (Future):
- Create `LLMProviderFactory` class to abstract provider selection
- Add `LLM_PROVIDER` environment variable (default: "gemini")
- Implement automatic fallback on consecutive failures
- Monitor Gemini API status: https://status.cloud.google.com/

**Current Status**: Gemini-only implementation (Story 2.1)
**Fallback Implementation**: Deferred to post-Epic 2 (out of MVP scope)

#### Monitoring and Observability

- **Structured Logs**: All LLM calls logged with prompt preview, tokens, latency
- **Prometheus Metrics**: `gemini_token_usage_total{operation="classification"}`
- **Token Tracking**: `LLMClient.get_token_usage_stats()` returns cumulative usage
- **Error Tracking**: Automatic structured logging for all error types

#### Multilingual Support

Gemini 2.5 Flash natively supports the 4 target languages without configuration:
- Russian (ru)
- Ukrainian (uk)
- English (en)
- German (de)

No translation layer or language detection required.

### Email Classification Prompt Engineering (Story 2.2)

Mail Agent uses advanced prompt engineering techniques to achieve accurate email classification across multiple languages. This section covers the classification prompt system, versioning strategy, and optimization approaches.

#### Overview

The classification prompt system enables Gemini 2.5 Flash to analyze incoming emails and suggest appropriate folder categories. The system achieves:
- **100% accuracy** across test categories (government, clients, newsletters, multilingual)
- **~3.8 second** average response time per classification
- **Multilingual support** for Russian, Ukrainian, English, and German emails
- **Token efficiency** with 500-character email body limit (~700 tokens per classification)

#### Prompt Design Principles

**1. Few-Shot Learning**
- Includes 5 diverse examples in each prompt
- Covers all major categories (Government, Clients, Newsletters, Unclassified)
- Demonstrates expected JSON output format
- Shows multilingual classification patterns

**2. Structured JSON Output**
- Uses Pydantic schema validation (`ClassificationResponse` model)
- Required fields: `suggested_folder` (string), `reasoning` (string, max 300 chars)
- Optional fields: `priority_score` (0-100), `confidence` (0.0-1.0)
- No markdown code fences in response (pure JSON)

**3. Multilingual Capability**
- Prompt written in English (LLM instructions)
- Input emails in any of 4 target languages (RU/UK/EN/DE)
- Output reasoning always in English for consistency
- No language detection required (Gemini processes natively)

**4. Token Optimization**
- Email body limited to 500 characters (balance context vs. speed)
- HTML tags stripped, plain text extracted
- Total prompt budget: ~700 tokens per classification
- Maintains sub-4-second response times

**5. User-Specific Context**
- Dynamic user folder categories included in prompt
- "Unclassified" fallback for ambiguous emails
- Priority scoring guidelines (government=high, newsletters=low)
- Confidence levels for accuracy tracking

#### Prompt Template Structure

The classification prompt (`backend/app/prompts/classification_prompt.py`) consists of:

```
┌─────────────────────────────────────────┐
│ System Role                             │
│ "You are an AI email classification     │
│  assistant..."                          │
├─────────────────────────────────────────┤
│ Task Description                        │
│ - Goal: Classify into user's folders   │
│ - Consider: sender, subject, content    │
│ - User approval workflow               │
├─────────────────────────────────────────┤
│ Classification Guidelines               │
│ - Government: finanzamt, bureaucracy    │
│ - Clients: business correspondence      │
│ - Newsletters: marketing, promotional   │
│ - Unclassified: ambiguous emails        │
├─────────────────────────────────────────┤
│ Email to Classify                       │
│ - From: {email_sender}                  │
│ - Subject: {email_subject}              │
│ - Body: {email_body_preview}           │
├─────────────────────────────────────────┤
│ Few-Shot Examples (5)                   │
│ Example 1: Government (German)          │
│ Example 2: Client (English)             │
│ Example 3: Newsletter (English)         │
│ Example 4: Unclear (Russian)            │
│ Example 5: Urgent Gov (German)          │
├─────────────────────────────────────────┤
│ JSON Schema Specification               │
│ - suggested_folder (required)           │
│ - reasoning (required, max 300 chars)   │
│ - priority_score (optional, 0-100)      │
│ - confidence (optional, 0.0-1.0)        │
└─────────────────────────────────────────┘
```

#### Usage Example

```python
from app.prompts import build_classification_prompt
from app.core.llm_client import LLMClient
from app.models.classification_response import ClassificationResponse

# Prepare email data
email_data = {
    "sender": "finanzamt@berlin.de",
    "subject": "Steuererklärung 2024 - Frist",
    "body": "<p>Sehr geehrte Damen und Herren...</p>",
    "user_email": "user@example.com"
}

# User's folder categories
user_folders = [
    {"name": "Government", "description": "Official government communications"},
    {"name": "Clients", "description": "Business correspondence"},
    {"name": "Newsletters", "description": "Marketing emails"}
]

# Build classification prompt
prompt = build_classification_prompt(email_data, user_folders)

# Call Gemini API
llm_client = LLMClient()
response_json = llm_client.receive_completion(prompt, operation="classification")

# Parse and validate response
classification = ClassificationResponse(**response_json)

print(f"Folder: {classification.suggested_folder}")
print(f"Reasoning: {classification.reasoning}")
print(f"Priority: {classification.priority_score}")
print(f"Confidence: {classification.confidence}")
```

**Output:**
```
Folder: Government
Reasoning: Official communication from Finanzamt (Tax Office) regarding tax return deadline
Priority: 85
Confidence: 0.95
```

#### Prompt Versioning

Prompt versions are tracked in `backend/app/config/prompts.yaml`:

```yaml
classification_prompt:
  version: "1.0"
  created: "2025-11-07"
  last_updated: "2025-11-07"
  description: "Initial classification prompt with multilingual support"

  performance:
    average_latency_ms: 3800
    classification_accuracy:
      government_emails: 100%
      client_emails: 100%
      newsletters: 100%
      multilingual: 100%
```

**Version Format:**
- **MAJOR.MINOR** (e.g., 1.0, 1.1, 2.0)
- **MAJOR**: Breaking changes (new output schema, incompatible API)
- **MINOR**: Prompt improvements (new examples, guideline tweaks)

#### Prompt Refinement Workflow

When classification accuracy drops or new edge cases emerge:

1. **Analyze Failure Patterns**
   - Track user rejections via ApprovalHistory (Story 2.10)
   - Identify common misclassifications (e.g., specific senders, keywords)
   - Review confidence scores for uncertain classifications

2. **Update Prompt Template**
   - Add new few-shot examples for edge cases
   - Refine classification guidelines
   - Adjust priority scoring rules
   - Update `backend/app/prompts/classification_prompt.py`

3. **Increment Version**
   - Minor version: Wording/example changes (1.0 → 1.1)
   - Major version: Schema changes (1.1 → 2.0)
   - Update `CLASSIFICATION_PROMPT_VERSION` constant

4. **Run Test Suite**
   ```bash
   # Unit tests (prompt structure, schema validation)
   pytest backend/tests/test_classification_prompt.py -v

   # Integration tests (real Gemini API calls)
   pytest backend/tests/integration/test_classification_integration.py -v
   ```

5. **Update Configuration**
   - Update `backend/app/config/prompts.yaml` with new version
   - Document changes in `changelog` section
   - Record test results and accuracy metrics

6. **Monitor Performance**
   - Track accuracy for 1 week before marking stable
   - Compare metrics against baseline (v1.0: 100% accuracy)
   - Roll back if accuracy drops below 85% for any category

#### Performance Metrics (Version 1.0)

From integration testing (2025-11-07):

| Metric | Value |
|--------|-------|
| Average Latency | 3.8 seconds |
| Token Usage | ~1,320 tokens per classification |
| Government Emails | 100% accuracy (3/3 correct) |
| Client Emails | 100% accuracy (1/1 correct) |
| Newsletters | 100% accuracy (1/1 correct) |
| Multilingual | 100% accuracy (RU/UK/DE) |
| Edge Cases | 100% accuracy (no body, special chars) |

**Priority Score Distribution:**
- Government (urgent): 95 (high priority)
- Government (standard): 85-90 (high priority)
- Clients: 60 (medium priority)
- Newsletters: 10-15 (low priority)
- Unclassified: 40-45 (medium-low priority)

**Confidence Scores:**
- Clear matches: 0.90-0.98 (high confidence)
- Unclear emails: 0.50-0.70 (low confidence, suggests manual review)

#### Testing Strategy

**Unit Tests** (`tests/test_classification_prompt.py`):
- Prompt structure validation (sections, placeholders)
- HTML stripping and body truncation
- Schema validation (valid/invalid JSON)
- Multiple folder categories
- Edge cases (empty body, long body)

**Integration Tests** (`tests/integration/test_classification_integration.py`):
- Real Gemini API calls (marked `@pytest.mark.integration`)
- Government emails (German)
- Client emails (English)
- Newsletters (marketing)
- Unclear emails (Russian)
- Multilingual validation (RU/UK/DE)
- Edge cases (no body, special characters, emojis)

**Run Tests:**
```bash
# Run all classification tests
pytest backend/tests/test_classification_prompt.py backend/tests/integration/test_classification_integration.py -v

# Run only integration tests (requires GEMINI_API_KEY)
pytest backend/tests/integration/test_classification_integration.py -v
```

#### Token Budget Breakdown

Total classification prompt: ~700 tokens

| Component | Tokens | Purpose |
|-----------|--------|---------|
| System role | ~50 | AI assistant identity |
| Task description | ~100 | Classification goal and context |
| Classification guidelines | ~100 | Category definitions |
| Few-shot examples (5) | ~300 | Demonstration patterns |
| JSON schema | ~50 | Output format specification |
| Email content | ~150 | Sender, subject, body preview (500 chars) |
| User folder categories | ~50 | Dynamic folder list (5 folders) |

**Optimization Strategies:**
- Email body limited to 500 characters (sufficient context)
- HTML stripped to plain text (reduces token overhead)
- Few-shot examples concise but informative
- Schema specification referenced once

#### Future Enhancements (Post-MVP)

- **A/B Testing**: Compare prompt versions with subset of users
- **Dynamic Examples**: Select few-shot examples based on user's folder categories
- **Adaptive Guidelines**: Learn from user corrections over time
- **Multi-Model Support**: Fallback to Claude or GPT for Gemini unavailability
- **Confidence Calibration**: Fine-tune confidence thresholds based on user feedback

#### References

**Files:**
- Prompt template: `backend/app/prompts/classification_prompt.py`
- Response model: `backend/app/models/classification_response.py`
- Unit tests: `backend/tests/test_classification_prompt.py`
- Integration tests: `backend/tests/integration/test_classification_integration.py`
- Configuration: `backend/app/config/prompts.yaml`

**External Resources:**
- Prompt Engineering Guide: https://www.promptingguide.ai/techniques/fewshot
- Google Gemini Best Practices: https://ai.google.dev/gemini-api/docs/prompting-strategies
- JSON Mode Documentation: https://ai.google.dev/gemini-api/docs/json-mode

### Email Classification Workflow Architecture (Story 2.3)

Mail Agent uses LangGraph state machine workflows to orchestrate email classification, user approval, and Gmail label application. The workflow implements a novel **TelegramHITLWorkflow** (Human-In-The-Loop) pattern that allows workflows to pause for hours/days while awaiting user responses, then resume exactly where they left off.

#### Overview

The EmailWorkflow is a 6-node LangGraph state machine with PostgreSQL checkpointing for persistent state management across service restarts and asynchronous user interactions.

**Key Features:**
- **Stateful Execution**: PostgreSQL checkpoint persistence enables pause/resume
- **Async User Approval**: Workflow pauses for Telegram approval, resumes hours later
- **Error Resilience**: Gemini API failures fall back to "Unclassified" folder
- **Cross-Channel Integration**: Email (Gmail) → AI (Gemini) → Approval (Telegram) → Action (Gmail)

**Workflow Flow:**
```
NEW EMAIL DETECTED (Email Polling Task)
    ↓
┌──────────────────────────────────────┐
│ START: Initialize Workflow           │
│ - Generate thread_id                 │
│ - Create EmailWorkflowState          │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ NODE: extract_context                │
│ - Load email from Gmail              │
│ - Extract sender, subject, body      │
│ - Load user's folder categories      │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ NODE: classify                       │
│ - Call Gemini API with prompt        │
│ - Parse JSON response                │
│ - Store: proposed_folder, reasoning  │
│ - Classification: "sort_only"        │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ NODE: send_telegram (Story 2.6)     │
│ - Format message preview             │
│ - Include approval buttons           │
│ - Send via Telegram Bot API          │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ NODE: await_approval                 │
│ ⚠️  WORKFLOW PAUSES HERE             │
│ - State saved to PostgreSQL          │
│ - Workflow instance awaiting         │
│ - User responds hours/days later     │
└──────────────────────────────────────┘
    ↓ (User clicks Telegram button)
┌──────────────────────────────────────┐
│ NODE: execute_action (Story 2.7)    │
│ - Apply Gmail label                  │
│ - Update database status             │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ NODE: send_confirmation (Story 2.6) │
│ - Send completion message            │
│ - Cleanup checkpoint                 │
└──────────────────────────────────────┘
    ↓
  END
```

#### Workflow State Definition

The workflow state is defined as a TypedDict (`EmailWorkflowState`) containing all data flowing through the workflow:

```python
class EmailWorkflowState(TypedDict):
    # Email identification
    email_id: str
    user_id: str
    thread_id: str  # Format: email_{email_id}_{uuid}

    # Email content (extract_context node)
    email_content: str
    sender: str
    subject: str

    # Classification results (classify node)
    classification: Literal["sort_only", "needs_response"] | None
    proposed_folder: str | None
    classification_reasoning: str | None
    priority_score: int

    # User approval (await_approval/execute_action nodes - Story 2.7)
    user_decision: Literal["approve", "reject", "change_folder"] | None
    selected_folder: str | None

    # Workflow completion (execute_action node)
    final_action: str | None

    # Error handling
    error_message: str | None
```

**Thread ID Format:**
- Pattern: `email_{email_id}_{uuid4()}`
- Example: `email_123_a1b2c3d4-e5f6-4789-0abc-def123456789`
- Unique identifier for checkpoint tracking and workflow resumption

#### Workflow Nodes

**1. extract_context** (Story 2.3)
- **Purpose**: Load email content and user context
- **Actions**:
  - Query EmailProcessingQueue for email metadata
  - Call Gmail API `get_message_detail()` to retrieve full email
  - Extract sender, subject, body (plain text, HTML stripped)
  - Load user's FolderCategory list from database
- **State Updates**: `email_content`, `sender`, `subject`
- **Error Handling**: Gmail API errors propagated (workflow cannot continue without email)

**2. classify** (Story 2.3)
- **Purpose**: Classify email using Gemini LLM
- **Actions**:
  - Initialize `EmailClassificationService` with dependencies
  - Construct prompt via `build_classification_prompt()` (Story 2.2)
  - Call Gemini API with JSON response format
  - Parse response into `ClassificationResponse` Pydantic model
  - Set classification type to "sort_only" (Epic 2 only handles sorting)
- **State Updates**: `classification`, `proposed_folder`, `classification_reasoning`, `priority_score`
- **Error Handling**: Gemini API errors → fallback to "Unclassified" folder (workflow continues)

**3. send_telegram** (Story 2.6 - stub in 2.3)
- **Purpose**: Send Telegram approval request to user
- **Actions** (Story 2.6):
  - Format message with email preview (sender, subject, snippet)
  - Include AI reasoning for classification
  - Create inline keyboard: [Approve] [Change Folder] [Reject]
  - Send via `TelegramBotClient.send_message()`
  - Store `telegram_message_id` in state
- **Current Implementation**: Stub that logs the action

**4. await_approval** (Story 2.3)
- **Purpose**: Pause workflow for user response
- **Actions**:
  - Return state unchanged
  - LangGraph checkpointer saves state to PostgreSQL
  - No outgoing edges from this node (workflow stops here)
- **State Updates**: None (workflow paused)
- **Resumption**: Story 2.7 Telegram callback handler resumes from `thread_id`

**5. execute_action** (Story 2.7 - stub in 2.3)
- **Purpose**: Apply user's decision to Gmail
- **Actions** (Story 2.7):
  - Determine folder based on `user_decision` and `selected_folder`
  - Lookup `FolderCategory.gmail_label_id` by folder name
  - Call `GmailClient.apply_label(message_id, label_id)`
  - Update `EmailProcessingQueue.status` to "completed"
  - Set `final_action` with description (e.g., "Moved to Work folder")
- **Current Implementation**: Stub that logs the action

**6. send_confirmation** (Story 2.6 - stub in 2.3)
- **Purpose**: Send completion message to user
- **Actions** (Story 2.6):
  - Format confirmation with `final_action` result
  - Send via `TelegramBotClient.send_message()`
  - Optionally edit original message to show completion
- **Current Implementation**: Stub that logs the action

#### PostgreSQL Checkpointing

**Checkpoint Storage:**
- **Tables**: `checkpoints`, `checkpoint_writes` (created automatically by LangGraph)
- **Connection**: Reuses same PostgreSQL instance as application database
- **Sync Mode**: Async (`sync=False`) for FastAPI compatibility
- **Configuration**:
  ```python
  from langgraph.checkpoint.postgres import PostgresSaver

  checkpointer = PostgresSaver.from_conn_string(
      conn_string=DATABASE_URL,
      sync=False  # Async mode
  )

  workflow = StateGraph(EmailWorkflowState)
  # ... add nodes and edges ...
  app = workflow.compile(checkpointer=checkpointer)
  ```

**Checkpoint Lifecycle:**
1. **Save**: After each node execution, state automatically saved
2. **Pause**: `await_approval` node returns without edges → workflow stops
3. **Resume**: Story 2.7 callback loads checkpoint via `thread_id`:
   ```python
   config = {"configurable": {"thread_id": thread_id}}
   result = await workflow.ainvoke(None, config=config)  # Resumes from checkpoint
   ```
4. **Cleanup**: Checkpoints deleted after workflow completion (Story 2.7)

**Checkpoint Query Example:**
```sql
-- Find checkpoint for specific workflow instance
SELECT thread_id, checkpoint_ns, checkpoint
FROM checkpoints
WHERE thread_id = 'email_123_abc-def-456'
ORDER BY checkpoint_id DESC
LIMIT 1;
```

#### Dependency Injection Pattern

LangGraph nodes typically only accept state parameters, but our nodes need database sessions and API clients. We solve this using **functools.partial** to bind dependencies:

```python
from functools import partial
from app.workflows import nodes

# Create workflow tracker with dependencies
tracker = WorkflowInstanceTracker(
    db=db_session,
    gmail_client=gmail_client,
    llm_client=llm_client,
    database_url=DATABASE_URL,
)

# Build workflow with dependency-injected nodes
workflow = StateGraph(EmailWorkflowState)

# Bind dependencies using functools.partial
extract_context_with_deps = partial(
    nodes.extract_context,
    db=db_session,
    gmail_client=gmail_client,
)

classify_with_deps = partial(
    nodes.classify,
    db=db_session,
    gmail_client=gmail_client,
    llm_client=llm_client,
)

# Add nodes with dependencies bound
workflow.add_node("extract_context", extract_context_with_deps)
workflow.add_node("classify", classify_with_deps)
# ... add remaining nodes ...

# Compile with checkpointer
app = workflow.compile(checkpointer=checkpointer)
```

This pattern allows nodes to access dependencies while maintaining LangGraph's state-based execution model.

#### Workflow Integration Points

**1. Email Polling (Story 1.6 + 2.3)**
- **Trigger**: New unread email detected by Celery task
- **Action**: `WorkflowInstanceTracker.start_workflow(email_id, user_id)`
- **Location**: `backend/app/tasks/email_tasks.py` → `_poll_user_emails_async()`
- **Flow**:
  ```python
  # After saving new email to EmailProcessingQueue
  workflow_tracker = WorkflowInstanceTracker(db, gmail, llm, db_url)
  thread_id = await workflow_tracker.start_workflow(email_id, user_id)
  # Workflow runs until await_approval, then pauses
  ```

**2. Database Updates**
- **EmailProcessingQueue** fields updated during workflow:
  - `status`: `pending` → `awaiting_approval` (after classification)
  - `classification`: "sort_only" (Epic 2 only)
  - `proposed_folder_id`: ForeignKey to FolderCategory
  - `classification_reasoning`: AI reasoning (max 300 chars)
  - `priority_score`: 0-100 scale
  - `is_priority`: `True` if priority_score >= 70

**3. Error Handling**
- **Gemini API Errors**: Caught by `EmailClassificationService`, fallback to "Unclassified"
- **Gmail API Errors**: Propagated (workflow cannot continue without email content)
- **Workflow Failures**: Logged, email status set to "error"
- **Email Not Lost**: Even if workflow fails, email is saved to database for retry

#### Testing Strategy

**Unit Tests** (`tests/test_classification_service.py`):
- Successful classification with valid Gemini response
- Gemini API error handling (fallback to "Unclassified")
- Invalid JSON response handling (Pydantic ValidationError)
- Gmail API error propagation (workflow halts)

**Integration Tests** (`tests/integration/test_email_workflow_integration.py`):
- Workflow state transitions through all nodes
- PostgreSQL checkpoint persistence and query
- Classification results stored in EmailProcessingQueue
- Workflow error handling with fallback classification

**Run Tests:**
```bash
# Run unit tests (mocked APIs)
pytest backend/tests/test_classification_service.py -v

# Run integration tests (real database, mocked external APIs)
pytest backend/tests/integration/test_email_workflow_integration.py -v --integration
```

#### Usage Example

```python
from app.services.workflow_tracker import WorkflowInstanceTracker
from app.core.gmail_client import GmailClient
from app.core.llm_client import LLMClient

# Initialize dependencies
gmail_client = GmailClient(user_id=456)
llm_client = LLMClient()
database_url = os.getenv("DATABASE_URL")

# Create workflow tracker
tracker = WorkflowInstanceTracker(
    db=db_session,
    gmail_client=gmail_client,
    llm_client=llm_client,
    database_url=database_url,
)

# Start workflow for new email
thread_id = await tracker.start_workflow(
    email_id=123,
    user_id=456,
)

# Workflow executes: extract_context → classify → send_telegram → await_approval
# Then PAUSES with state saved to PostgreSQL

print(f"Workflow paused at await_approval, thread_id: {thread_id}")
# Output: Workflow paused at await_approval, thread_id: email_123_abc-def-456

# Hours/days later, user clicks Telegram button (Story 2.7)
# Telegram callback handler resumes workflow from checkpoint
```

#### Files and Locations

**Core Workflow Files:**
- State definition: `backend/app/workflows/states.py`
- Workflow nodes: `backend/app/workflows/nodes.py`
- Workflow compilation: `backend/app/workflows/email_workflow.py` (deprecated in favor of tracker)
- Workflow tracker: `backend/app/services/workflow_tracker.py`

**Classification Service:**
- Service class: `backend/app/services/classification.py`
- Response model: `backend/app/models/classification_response.py`
- Prompt builder: `backend/app/prompts/classification_prompt.py`

**Integration:**
- Email polling: `backend/app/tasks/email_tasks.py`
- Database models: `backend/app/models/email.py`, `backend/app/models/folder_category.py`

**Tests:**
- Unit tests: `backend/tests/test_classification_service.py`
- Integration tests: `backend/tests/integration/test_email_workflow_integration.py`

#### References

**External Documentation:**
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- LangGraph PostgreSQL Checkpointer: https://langchain-ai.github.io/langgraph/how-tos/persistence/
- LangGraph State Management: https://langchain-ai.github.io/langgraph/concepts/low_level/#state
- TypedDict Documentation: https://docs.python.org/3/library/typing.html#typing.TypedDict

**Internal References:**
- Story 2.1: Gemini LLM Integration
- Story 2.2: Email Classification Prompt Engineering
- Story 2.3: AI Email Classification Service (this story)
- Story 2.6: Telegram Message Sending (send_telegram, send_confirmation nodes)
- Story 2.7: Telegram Approval Handling (execute_action node, workflow resumption)

### Logging
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)
- `LOG_FORMAT`: Log format (console/json)
- `LOG_DIR`: Log directory path

---

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/                 # API endpoints
│   │   └── v1/
│   │       ├── api.py       # API router configuration
│   │       ├── auth.py      # Authentication endpoints (Story 1.4)
│   │       └── chatbot.py   # LangGraph chatbot (deferred to Epic 2)
│   ├── core/                # Core functionality
│   │   ├── config.py        # Environment configuration
│   │   ├── logging.py       # Structured logging setup
│   │   ├── metrics.py       # Prometheus metrics
│   │   ├── middleware.py    # Custom middleware
│   │   └── limiter.py       # Rate limiting
│   ├── models/              # Database models (Story 1.3)
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic services
│   │   └── database.py      # Database service
│   └── utils/               # Utility functions
├── .env.example             # Environment variables template
├── .env                     # Environment variables (not in git)
├── pyproject.toml           # Project dependencies
├── README.md                # This file
└── venv/                    # Virtual environment (not in git)
```

---

## API Endpoints

### Core Endpoints

- `GET /` - Root endpoint, returns API information
- `GET /health` - Health check endpoint with component status
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

### API v1 Endpoints

- `POST /api/v1/auth/register` - User registration (Story 1.4)
- `POST /api/v1/auth/login` - User login (Story 1.4)
- `GET /api/v1/auth/gmail/authorize` - Start Gmail OAuth flow (Story 1.4)
- `GET /api/v1/auth/gmail/callback` - Gmail OAuth callback (Story 1.4)

### Future Endpoints (Epic 2+)
- Gmail integration endpoints
- Email classification endpoints
- Telegram webhook endpoints
- Response generation endpoints

---

## Development

### Running Tests

Tests will be implemented starting from Story 1.3.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_health.py
```

### Code Quality

```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
ruff check app/

# Type checking (if mypy is configured)
mypy app/
```

### Hot Reload

The development server automatically reloads when you modify Python files. This is enabled by the `--reload` flag.

---

## Features Implemented (Story 1.2)

✅ FastAPI application initialized with main.py entry point
✅ Health check endpoint (GET /health) with timestamp and component status
✅ CORS middleware configured for localhost:3000
✅ Environment variable loading with python-dotenv
✅ Development server runs on localhost:8000 with hot reload
✅ Structured JSON logging configured
✅ Dependencies managed via pyproject.toml

---

## Database Setup (Story 1.3)

### Prerequisites

- Docker and Docker Compose installed
- PostgreSQL 18 (via Docker) or free-tier cloud service (Supabase)

### Starting PostgreSQL Database

The project uses PostgreSQL 18 via Docker Compose for local development:

```bash
# Start PostgreSQL container
docker-compose up -d db

# Verify PostgreSQL is running
docker ps --filter "name=postgres"

# Check container logs
docker logs <container-id>

# Connect to database manually (optional)
psql -h localhost -U mailagent -d mailagent
```

### Database Migrations with Alembic

This project uses Alembic for database schema versioning. All schema changes must go through migrations.

#### Apply Migrations

```bash
# Apply all pending migrations (run after git pull or initial setup)
alembic upgrade head

# Check current migration version
alembic current

# View migration history
alembic history
```

#### Create New Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new table or field"

# Review the generated migration file in alembic/versions/
# Edit if needed, then apply:
alembic upgrade head
```

#### Rollback Migrations

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Rollback all migrations (reset database)
alembic downgrade base
```

#### Reset Database

To completely reset your local database:

```bash
# Stop and remove database container with volumes
docker-compose down -v

# Start fresh database container
docker-compose up -d db

# Apply all migrations
alembic upgrade head
```

### Database Health Check

The backend provides a health check endpoint to verify database connectivity:

```bash
# Check database connection
curl http://localhost:8000/api/v1/health/db

# Expected response when connected:
# {"status": "connected", "database": "mailagent", "message": "PostgreSQL connection successful"}
```

### Database Models

Current database schema (Story 1.3):

- **Users table**: Stores user accounts with Gmail OAuth tokens and Telegram integration
  - `id`: Primary key
  - `email`: User email (unique, indexed)
  - `gmail_oauth_token`: Encrypted Gmail access token
  - `gmail_refresh_token`: Encrypted Gmail refresh token
  - `telegram_id`: Telegram user ID (unique, indexed)
  - `telegram_username`: Telegram username
  - `is_active`: Account status flag
  - `onboarding_completed`: Onboarding completion flag
  - `created_at`: Timestamp (auto-generated)
  - `updated_at`: Timestamp (auto-updated)

## Gmail Label Management (Story 1.8)

The Gmail Label Management system enables programmatic creation and management of Gmail labels (folders) for organizing emails into user-defined categories. This foundation supports AI-powered email classification in Epic 2 and provides the organizational structure for the entire application.

### FolderCategories Table

The `folder_categories` table stores user-defined email organization folders. Each folder maps to a Gmail label and includes metadata for AI classification and UI display:

```sql
CREATE TABLE folder_categories (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                VARCHAR(100) NOT NULL,
    gmail_label_id      VARCHAR(100),                 -- Gmail's internal label ID
    keywords            TEXT[],                       -- AI classification hints (Epic 2)
    color               VARCHAR(7),                   -- Hex color code (#FF5733)
    is_default          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_folder_name UNIQUE (user_id, name)
);

-- Performance Indexes
CREATE INDEX idx_folder_user_id ON folder_categories(user_id);
CREATE INDEX idx_folder_gmail_label_id ON folder_categories(gmail_label_id);
```

**Key Features:**
- **Gmail Integration**: Each folder creates a corresponding Gmail label via Gmail API
- **Unique Constraint**: `(user_id, name)` prevents duplicate folder names per user
- **Cascade Delete**: Deleting a user automatically removes all associated folders (GDPR compliance)
- **Keywords Array**: Stores classification hints for Epic 2 AI engine (e.g., ["finanzamt", "tax"] for "Government" folder)
- **Color Codes**: Hex color format (#FF5733) for Epic 4 UI visual differentiation
- **Gmail Label ID**: Stores Gmail's internal label ID (e.g., "Label_123") for label operations

### FolderService API Methods

The `FolderService` class provides business logic for folder management, coordinating between database and Gmail API:

#### create_folder()
Creates a new folder in both database and Gmail:

```python
from app.services.folder_service import FolderService

service = FolderService()
folder = await service.create_folder(
    user_id=1,
    name="Government",
    keywords=["finanzamt", "tax", "ausländerbehörde"],
    color="#FF5733"
)

print(f"Folder created with Gmail label ID: {folder.gmail_label_id}")
```

**Process:**
1. Validates folder name (1-100 chars, not empty)
2. Checks for duplicate name (enforces unique constraint)
3. Creates Gmail label via `GmailClient.create_label()`
4. Stores `FolderCategory` record with `gmail_label_id` in database
5. Returns created folder object

**Error Handling:**
- `ValueError`: Invalid or duplicate folder name
- `HttpError`: Gmail API failure (token expired, quota exceeded, etc.)

#### list_folders()
Retrieves all folders for a user:

```python
folders = await service.list_folders(user_id=1)
for folder in folders:
    print(f"{folder.name}: {folder.gmail_label_id}")
```

#### get_folder_by_id()
Fetches a single folder by ID (with user ownership verification):

```python
folder = await service.get_folder_by_id(folder_id=5, user_id=1)
if folder:
    print(f"Found folder: {folder.name}")
```

#### delete_folder()
Deletes folder from database and Gmail:

```python
success = await service.delete_folder(folder_id=5, user_id=1)
if success:
    print("Folder deleted from both database and Gmail")
```

**Note:** Gmail label deletion is performed via Gmail API when deleting the folder record.

### Gmail Label Management Methods

The `GmailClient` class provides low-level Gmail API operations for labels:

#### list_labels()
Lists all Gmail labels for authenticated user:

```python
from app.core.gmail_client import GmailClient

client = GmailClient(user_id=1)
labels = await client.list_labels()

for label in labels:
    print(f"{label['name']}: {label['label_id']} ({label['type']})")
```

**Returns:**
```python
[
    {
        "label_id": "Label_123",
        "name": "Government",
        "type": "user",  # "system" or "user"
        "visibility": "labelShow"
    },
    ...
]
```

#### create_label()
Creates a new Gmail label with optional color and visibility:

```python
label_id = await client.create_label(
    name="Government",
    color="#FF5733",
    visibility="labelShow"
)
print(f"Created Gmail label: {label_id}")
```

**Idempotent Operation:** If label name already exists, Gmail returns 409 Conflict. The method automatically falls back to `list_labels()` and returns the existing label ID, making the operation idempotent.

**Color Format:** Hex code (#FF5733). Gmail maps this to its internal color palette.

**Visibility Options:**
- `labelShow` (default): Label visible in label list
- `labelHide`: Label hidden but messages still labeled

#### apply_label()
Applies label to an email message (moves email to folder):

```python
success = await client.apply_label(
    message_id="abc123def456",  # Gmail message ID
    label_id="Label_123"         # Gmail label ID
)
if success:
    print("Email moved to folder")
```

**Use Case:** This method is called by Epic 2's AI sorting engine after user approves classification via Telegram.

#### remove_label()
Removes label from an email message:

```python
success = await client.remove_label(
    message_id="abc123def456",
    label_id="Label_123"
)
if success:
    print("Label removed from email")
```

### REST API Endpoints

#### POST /api/v1/folders/
Creates a new folder for authenticated user:

```bash
curl -X POST https://api.example.com/api/v1/folders/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Government",
    "keywords": ["finanzamt", "tax", "ausländerbehörde"],
    "color": "#FF5733"
  }'
```

**Response (201 Created):**
```json
{
  "id": 5,
  "user_id": 1,
  "name": "Government",
  "gmail_label_id": "Label_123",
  "keywords": ["finanzamt", "tax", "ausländerbehörde"],
  "color": "#FF5733",
  "is_default": false,
  "created_at": "2025-11-05T12:00:00Z",
  "updated_at": "2025-11-05T12:00:00Z"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid folder name or duplicate exists
- `401 Unauthorized`: Missing or invalid JWT token
- `500 Internal Server Error`: Gmail API failure

#### GET /api/v1/folders/
Lists all folders for authenticated user:

```bash
curl -X GET https://api.example.com/api/v1/folders/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response (200 OK):**
```json
[
  {
    "id": 5,
    "user_id": 1,
    "name": "Government",
    "gmail_label_id": "Label_123",
    "keywords": ["finanzamt", "tax"],
    "color": "#FF5733",
    "is_default": false,
    "created_at": "2025-11-05T12:00:00Z",
    "updated_at": "2025-11-05T12:00:00Z"
  },
  ...
]
```

#### GET /api/v1/folders/{folder_id}
Retrieves a single folder by ID:

```bash
curl -X GET https://api.example.com/api/v1/folders/5 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response (200 OK):** Single folder object (same schema as POST response)

**Error Response:**
- `404 Not Found`: Folder does not exist or user does not own it

#### DELETE /api/v1/folders/{folder_id}
Deletes a folder from both database and Gmail:

```bash
curl -X DELETE https://api.example.com/api/v1/folders/5 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response (204 No Content):** Folder successfully deleted

**Error Response:**
- `404 Not Found`: Folder does not exist or user does not own it

### Label Application Workflow (Epic 2 Preview)

**Label Creation and Application Process:**

```
1. User creates folder via Epic 4 UI
   ↓
2. Frontend POST /api/v1/folders/ → Backend
   ↓
3. Backend FolderService:
   - Validate folder name (1-100 chars, unique per user)
   - Initialize GmailClient(user_id)
   - Call client.create_label(name="Government", color="#FF5733")
   ↓
4. Gmail API creates label, returns label_id (e.g., "Label_123")
   ↓
5. Backend creates FolderCategory record:
   - name="Government"
   - gmail_label_id="Label_123"
   - user_id=123
   - keywords=["finanzamt", "tax"]  # Optional
   ↓
6. Return FolderCategory JSON to frontend
   ↓

When applying label (Epic 2 AI Sorting):
   ↓
7. AI classifies email, selects FolderCategory
   ↓
8. User approves via Telegram
   ↓
9. Load FolderCategory by id from database
   ↓
10. Call client.apply_label(message_id, gmail_label_id)
    ↓
11. Gmail API moves email to folder (applies label)
    ↓
12. Email appears in Gmail UI under "Government" label ✅
```

### Color Format and Visibility Options

**Color Format:**
- Must be 7-character hex code: `#RRGGBB`
- Valid examples: `#FF5733`, `#00FF00`, `#0000FF`
- Invalid examples: `#FFF` (too short), `red` (not hex), `FF5733` (missing #)
- Validation regex: `^#[0-9A-Fa-f]{6}$`

**Gmail maps hex colors to its internal palette:**
| Hex Code | Gmail Color Name |
|----------|------------------|
| #FF5733  | Red Orange       |
| #FFC107  | Yellow           |
| #4CAF50  | Green            |
| #2196F3  | Blue             |
| #9C27B0  | Purple           |

**Visibility Options:**
| Option | Description | Use Case |
|--------|-------------|----------|
| `labelShow` | Label visible in Gmail label list (default) | Normal folders |
| `labelHide` | Label hidden but messages still tagged | Internal system labels |

**Example:**
```python
# Create visible folder with green color
folder = await service.create_folder(
    user_id=1,
    name="Important",
    color="#4CAF50"
)
```

### Security Considerations

**Authentication:**
- All folder endpoints require JWT authentication (`get_current_user` dependency)
- User ID extracted from JWT token, preventing cross-user access

**Authorization:**
- All service methods verify user ownership before operations
- Database queries filter by `user_id` to prevent unauthorized access

**Data Integrity:**
- Unique constraint on `(user_id, name)` prevents duplicates
- Cascade delete ensures orphaned folders don't exist after user deletion

**Gmail API Security:**
- OAuth tokens encrypted at rest (Fernet encryption)
- Token refresh handled automatically on 401 Unauthorized errors
- Rate limiting: 10K requests/day quota, ~100/day budgeted for label ops

### Environment Variables

Configure database connection in `.env`:

```bash
# Local Development (Docker Compose)
DATABASE_URL=postgresql://mailagent:password@localhost:5432/mailagent

# Production (Supabase example)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

**Security Note:** Never commit `.env` to git. Database credentials are sensitive.

---

## Gmail OAuth Setup (Story 1.4)

### Prerequisites

- Google Cloud Project with Gmail API enabled
- OAuth 2.0 credentials (Client ID and Secret)

### Setting Up Gmail OAuth

Follow these steps to configure Gmail OAuth for Mail Agent:

#### 1. Create Google Cloud Project

1. Visit [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project named "Mail Agent"
3. Select the project from the project selector

#### 2. Enable Gmail API

1. Navigate to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click **Enable**

#### 3. Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type
3. Fill in required information:
   - **App name**: Mail Agent
   - **User support email**: Your email address
   - **Developer contact**: Your email address
4. Click **Save and Continue**
5. **Scopes**: Add the following Gmail API scopes:
   - `https://www.googleapis.com/auth/gmail.readonly` - Read email content
   - `https://www.googleapis.com/auth/gmail.modify` - Apply labels to emails
   - `https://www.googleapis.com/auth/gmail.send` - Send email responses
   - `https://www.googleapis.com/auth/gmail.labels` - Manage custom labels
6. Click **Save and Continue**

#### 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Web application**
4. Name: **Mail Agent Backend**
5. **Authorized redirect URIs**:
   - Development: `http://localhost:8000/api/v1/auth/gmail/callback`
   - Production: `https://your-domain.com/api/v1/auth/gmail/callback`
6. Click **Create**
7. Copy the **Client ID** and **Client Secret**

#### 5. Configure Environment Variables

Add the OAuth credentials to your `.env` file:

```bash
# Gmail OAuth Configuration
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REDIRECT_URI=http://localhost:8000/api/v1/auth/gmail/callback

# Encryption Key (for storing OAuth tokens securely)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-generated-encryption-key
```

**Security Note:**
- Never commit OAuth credentials to git
- Rotate `ENCRYPTION_KEY` periodically in production
- Use HTTPS redirect URIs in production

### Gmail OAuth Endpoints

The backend provides the following OAuth endpoints:

#### Initiate OAuth Flow
```bash
# Start OAuth flow
curl -X POST http://localhost:8000/api/v1/auth/gmail/login

# Response:
# {
#   "success": true,
#   "data": {
#     "authorization_url": "https://accounts.google.com/o/oauth2/auth?..."
#   }
# }
```

Redirect the user to the `authorization_url` to grant Gmail permissions.

#### OAuth Callback
```bash
# Google redirects back to this endpoint with code and state
GET /api/v1/auth/gmail/callback?code=...&state=...

# Response:
# {
#   "success": true,
#   "data": {
#     "user_id": 1,
#     "email": "user@gmail.com"
#   }
# }
```

#### Check Gmail Connection Status
```bash
# Check if user has valid Gmail tokens (requires JWT authentication)
curl http://localhost:8000/api/v1/auth/gmail/status \
  -H "Authorization: Bearer <your-jwt-token>"

# Response:
# {
#   "success": true,
#   "data": {
#     "connected": true,
#     "email": "user@gmail.com",
#     "token_valid": true,
#     "last_sync": "2025-11-04T10:15:30Z"
#   }
# }
```

### Gmail API Scopes Explained

The application requests the following Gmail API scopes:

| Scope | Purpose | Required For |
|-------|---------|-------------|
| `gmail.readonly` | Read email content for monitoring and classification | Epic 2 - Email classification |
| `gmail.modify` | Apply labels to emails for sorting | Epic 1 - Label management |
| `gmail.send` | Send email responses on behalf of user | Epic 3 - Response generation |
| `gmail.labels` | Create and manage custom labels/folders | Epic 1 - Folder categories |

Users can revoke access anytime via [Google Account Settings](https://myaccount.google.com/permissions).

### Token Security

OAuth tokens are encrypted at rest using **Fernet symmetric encryption**:

- **Algorithm**: AES-128-CBC with HMAC authentication
- **Key Size**: 32 bytes (base64-encoded)
- **Refresh**: Access tokens automatically refresh when expired
- **Storage**: Tokens stored encrypted in PostgreSQL
- **Decryption**: Only happens when making Gmail API calls

**Security Best Practices:**
- Tokens never logged or exposed in API responses
- Encryption key stored in environment variable (not code)
- CSRF protection via state parameter in OAuth flow
- TLS/HTTPS enforced for all OAuth communications

### Testing Gmail OAuth

1. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Call the login endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/gmail/login
   ```

3. Open the `authorization_url` in your browser

4. Grant Gmail permissions

5. You'll be redirected to the callback URL with your tokens stored

6. Verify database storage:
   ```bash
   psql -h localhost -U mailagent -d mailagent
   SELECT email, LENGTH(gmail_oauth_token), LENGTH(gmail_refresh_token) FROM users;
   ```

Tokens should be encrypted (unreadable strings).

---

## Gmail API Client Usage

The `GmailClient` class provides a high-level wrapper around the Gmail API for performing email operations. It automatically handles OAuth token refresh, rate limiting, and error recovery.

### Prerequisites

- Gmail OAuth flow must be completed (Story 1.4)
- User must have valid OAuth tokens stored in database
- Gmail API dependencies installed (google-api-python-client, etc.)

### Basic Usage

#### Initialize the Client

```python
from app.core.gmail_client import GmailClient

# Initialize client for a specific user
client = GmailClient(user_id=123)
```

#### Fetch Unread Emails

```python
# Fetch unread emails from inbox
emails = await client.get_messages(query="is:unread", max_results=10)

for email in emails:
    print(f"From: {email['sender']}")
    print(f"Subject: {email['subject']}")
    print(f"Preview: {email['snippet']}")
    print(f"Received: {email['received_at']}")
```

**Query Examples:**
- `"is:unread"` - Unread emails only
- `"from:user@example.com"` - Emails from specific sender
- `"subject:urgent"` - Emails with "urgent" in subject
- `"has:attachment"` - Emails with attachments
- `"newer_than:1d"` - Emails from last 24 hours

#### Read Full Email Content

```python
# Get complete email including body
detail = await client.get_message_detail(message_id="abc123xyz")

print(f"Subject: {detail['subject']}")
print(f"From: {detail['sender']}")
print(f"Body: {detail['body']}")  # Plain text extracted from HTML if needed
print(f"Headers: {detail['headers']}")  # All email headers
```

**Note:** The body is automatically extracted from MIME parts and HTML is stripped to plain text.

#### Read Email Thread History

```python
# Get all messages in a conversation
thread_messages = await client.get_thread(thread_id="thread123")

for msg in thread_messages:
    print(f"{msg['received_at']}: {msg['sender']}")
    print(f"  Subject: {msg['subject']}")
    print(f"  Body: {msg['body'][:100]}...")
```

**Note:** Messages are returned in chronological order (oldest first).

### Advanced Usage

#### Dependency Injection for Testing

```python
from app.services.database import DatabaseService

# Use custom database service
db_service = DatabaseService()
client = GmailClient(user_id=123, db_service=db_service)
```

#### Error Handling

The client automatically handles:
- **Token Expiry (401):** Refreshes token and retries
- **Rate Limits (429):** Exponential backoff (2s, 4s, 8s)
- **Transient Errors (500-503):** Automatic retry with backoff

All errors are logged with structured logging for monitoring.

```python
from googleapiclient.errors import HttpError

try:
    emails = await client.get_messages(query="is:unread")
except HttpError as e:
    # Permanent Gmail API error (not transient)
    print(f"Gmail API error: {e.resp.status}")
```

### Gmail API Rate Limits

**Free Tier Quotas (per user per day):**
- API requests: 10,000 requests/day
- Message sends: 100 sends/day

**Typical Mail Agent Usage:**
- Email polling (every 2 min): ~720 requests/day
- Message detail fetches: ~3,600 requests/day
- Thread history: ~200 requests/day
- Total: ~4,620 requests/day (46% of quota)

**Rate Limit Handling:**
- 429 errors trigger exponential backoff
- Quota exhaustion logs warning and pauses operations
- Critical operations prioritized in quota allocation

### Security Notes

- OAuth tokens encrypted at rest (Fernet symmetric encryption)
- TLS enforced for all Gmail API calls
- Email content never logged (privacy protection)
- Token details never logged (only user_id for context)

### Method Reference

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_messages()` | `query`, `max_results` | List of email metadata | Fetch emails matching Gmail search query |
| `get_message_detail()` | `message_id` | Full email dict | Get complete email content including body |
| `get_thread()` | `thread_id` | List of messages | Get all messages in a conversation thread |

### Complete Example

```python
from app.core.gmail_client import GmailClient
from googleapiclient.errors import HttpError

async def process_unread_emails(user_id: int):
    """Fetch and process unread emails for a user"""
    client = GmailClient(user_id=user_id)

    try:
        # Fetch unread emails
        emails = await client.get_messages(query="is:unread", max_results=50)

        for email in emails:
            # Get full content for each email
            detail = await client.get_message_detail(email['message_id'])

            # Process email (classify, respond, etc.)
            print(f"Processing: {detail['subject']}")
            print(f"Body preview: {detail['body'][:200]}...")

            # If part of a thread, get conversation history
            if email['thread_id']:
                thread = await client.get_thread(email['thread_id'])
                print(f"Thread has {len(thread)} messages")

    except HttpError as e:
        print(f"Gmail API error: {e.resp.status} - {e}")
```

---

## Email Sending Capability (Story 1.9)

The Email Sending system enables sending emails via Gmail API on behalf of authenticated users, supporting plain text and HTML body types, conversation threading, and comprehensive error handling. This foundation enables AI-generated response emails in Epic 3.

### Prerequisites

- Gmail OAuth flow completed (Story 1.4)
- User must have valid OAuth tokens with `gmail.send` scope
- Gmail API sending quota: 100 sends/day per user (free tier)

### GmailClient.send_email() Method

The core method for sending emails via Gmail API:

```python
from app.core.gmail_client import GmailClient

client = GmailClient(user_id=123)

# Send plain text email
message_id = await client.send_email(
    to="recipient@example.com",
    subject="Test Email",
    body="This is a plain text message",
    body_type="plain"
)

print(f"Email sent with message ID: {message_id}")
```

**Method Signature:**
```python
async def send_email(
    self,
    to: str,
    subject: str,
    body: str,
    body_type: str = "plain",
    thread_id: Optional[str] = None
) -> str:
    """Send email via Gmail API.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content (plain text or HTML)
        body_type: "plain" or "html" (default: "plain")
        thread_id: Gmail thread ID for reply-to functionality (optional)

    Returns:
        Gmail message_id of sent email

    Raises:
        InvalidRecipientError: Recipient email invalid or does not exist
        QuotaExceededError: Gmail API sending quota exceeded (100/day)
        MessageTooLargeError: Email exceeds 25MB size limit
        ValueError: Invalid parameters (e.g., body_type not "plain"/"html")
    """
```

### Sending HTML Emails

Send emails with HTML formatting:

```python
# HTML email with formatting
html_body = """
<html>
  <body>
    <h1>Welcome to Mail Agent</h1>
    <p>This is an <strong>HTML</strong> email with <em>formatting</em>.</p>
    <ul>
      <li>Bullet point 1</li>
      <li>Bullet point 2</li>
    </ul>
  </body>
</html>
"""

message_id = await client.send_email(
    to="recipient@example.com",
    subject="HTML Email Example",
    body=html_body,
    body_type="html"
)
```

**MIME Message Structure:**
- Plain text: `Content-Type: text/plain; charset="utf-8"`
- HTML: `Content-Type: text/html; charset="utf-8"`
- Emails include proper headers: From, To, Subject, Date (RFC 2822 format)

### Reply to Email Threads

Send emails as replies to existing conversation threads:

```python
# Reply to an email thread
message_id = await client.send_email(
    to="recipient@example.com",
    subject="Re: Original Subject",
    body="This is a reply message",
    body_type="plain",
    thread_id="thread_abc123"  # Gmail thread ID from original email
)
```

**Threading Headers:**
- **In-Reply-To**: Contains Message-ID of email being replied to
- **References**: Contains all message IDs in thread conversation
- Gmail uses these headers to group emails into conversation threads
- Format: `<message-id@mail.gmail.com>` (angle brackets required)

**How Thread IDs Work:**
1. Fetch original email metadata via `client.get_messages()`
2. Extract `thread_id` from email metadata
3. Pass `thread_id` to `send_email()` method
4. Client automatically constructs In-Reply-To and References headers
5. Reply appears in Gmail conversation thread

### Error Handling

The email sending system handles Gmail API errors gracefully:

#### Quota Exceeded (429 Rate Limit)

```python
from app.utils.errors import QuotaExceededError

try:
    message_id = await client.send_email(
        to="recipient@example.com",
        subject="Test",
        body="Test body"
    )
except QuotaExceededError as e:
    print(f"Quota exceeded: {e}")
    print(f"Retry after: {e.retry_after} seconds")
    # Implement retry logic or notify user
```

**Gmail API Quota:**
- Free tier: 100 sends/day per user
- G Suite: 2,000 sends/day per user
- Quota resets daily at midnight Pacific Time
- Exceeded quota triggers automatic exponential backoff

#### Invalid Recipient (400 Bad Request)

```python
from app.utils.errors import InvalidRecipientError

try:
    message_id = await client.send_email(
        to="invalid-email",
        subject="Test",
        body="Test body"
    )
except InvalidRecipientError as e:
    print(f"Invalid recipient: {e.recipient}")
    # Validate email format before sending
```

#### Message Too Large (413 Request Entity Too Large)

```python
from app.utils.errors import MessageTooLargeError

# Gmail enforces 25MB size limit (including attachments)
large_body = "A" * 26_000_000  # 26MB body

try:
    message_id = await client.send_email(
        to="recipient@example.com",
        subject="Large Email",
        body=large_body
    )
except MessageTooLargeError as e:
    print(f"Email too large: {e.size_bytes} bytes")
    # Compress or split content
```

**Error Summary Table:**

| Error Code | Exception | Description | Retry? |
|------------|-----------|-------------|--------|
| 400 | `InvalidRecipientError` | Invalid recipient email address | No |
| 401 | Auto-handled | OAuth token expired (auto-refreshed) | Yes (once) |
| 413 | `MessageTooLargeError` | Email exceeds 25MB limit | No |
| 429 | `QuotaExceededError` | Daily sending quota exceeded (100/day) | Yes (exponential backoff) |
| 503 | Auto-handled | Transient Gmail API error | Yes (3 retries) |

### Structured Logging

All email sending operations are logged with structured metadata:

```json
{
  "event": "email_send_started",
  "user_id": 123,
  "recipient": "recipient@example.com",
  "subject": "Test Email",
  "has_threading": false,
  "timestamp": "2025-11-05T10:15:30.123Z"
}

{
  "event": "email_sent",
  "user_id": 123,
  "recipient": "recipient@example.com",
  "subject": "Test Email",
  "message_id": "18abc123def456",
  "success": true,
  "duration_ms": 1234,
  "timestamp": "2025-11-05T10:15:31.357Z"
}
```

**GDPR Compliance:**
- ❌ Email body content is NOT logged (privacy protection)
- ✅ Metadata logged: recipient, subject, message_id, timestamp, success status
- ✅ No sensitive data in logs (OAuth tokens excluded)

### Test Endpoint

A test endpoint is provided for manual email sending:

#### POST /api/v1/test/send-email

Send a test email via authenticated API endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/test/send-email \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Test Email",
    "body": "This is a test message",
    "body_type": "plain"
  }'
```

**Request Model:**
```json
{
  "to": "recipient@example.com",
  "subject": "Email subject line",
  "body": "Email body content (plain text or HTML)",
  "body_type": "plain",  // "plain" or "html"
  "thread_id": null      // Optional: Gmail thread ID for replies
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message_id": "18abc123def456",
    "recipient": "recipient@example.com",
    "subject": "Test Email"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid recipient or body_type parameter
- `401 Unauthorized`: Missing or invalid JWT token
- `413 Request Entity Too Large`: Email exceeds 25MB limit
- `429 Too Many Requests`: Gmail API quota exceeded (100 sends/day)
- `500 Internal Server Error`: Gmail API failure

#### Example: Send HTML Email

```bash
curl -X POST http://localhost:8000/api/v1/test/send-email \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "HTML Email Test",
    "body": "<h1>Hello</h1><p>This is <strong>HTML</strong></p>",
    "body_type": "html"
  }'
```

#### Example: Reply to Thread

```bash
curl -X POST http://localhost:8000/api/v1/test/send-email \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Re: Original Subject",
    "body": "This is a reply",
    "thread_id": "thread_abc123"
  }'
```

### Integration Testing

Run email sending tests:

```bash
# Unit tests (MIME composition, error handling, etc.)
pytest backend/tests/test_email_sending.py -v

# Integration tests (end-to-end API → Gmail)
pytest backend/tests/test_email_integration.py -v
```

**Test Coverage:**
- ✅ MIME message composition (plain text and HTML)
- ✅ Threading headers (In-Reply-To, References)
- ✅ Gmail API integration (send endpoint)
- ✅ Error handling (quota, invalid recipient, message too large)
- ✅ Structured logging validation
- ✅ API endpoint authentication and responses

### Security Notes

- **OAuth Tokens**: Encrypted at rest using Fernet symmetric encryption
- **TLS/HTTPS**: Enforced for all Gmail API calls
- **JWT Authentication**: Test endpoint requires valid JWT token
- **Rate Limiting**: Gmail API quota tracking prevents abuse
- **No Sensitive Logs**: Email body content never logged (GDPR compliance)
- **Input Validation**: body_type parameter validated, thread_id sanitized

### Gmail API Quotas and Limits

**Free Tier (Gmail Personal Accounts):**
- Sending quota: 100 emails/day per user
- API requests: 10,000 requests/day per user
- Message size: 25MB maximum (including attachments)

**G Suite / Google Workspace:**
- Sending quota: 2,000 emails/day per user
- API requests: 25,000 requests/day per user
- Message size: 25MB maximum

**Typical Mail Agent Usage:**
- AI-generated responses: ~10-20 sends/day per user
- Test emails: ~5 sends/day per user
- Total: ~15-25 sends/day (12-25% of free tier quota)

**Quota Management:**
- 429 errors trigger exponential backoff (2s, 4s, 8s delays)
- Quota exhaustion logged for monitoring
- Critical responses prioritized in quota allocation

### Future Enhancements (Epic 3)

- Attachment support (files, images)
- Email templates with variable substitution
- Batch sending for multiple recipients
- Send scheduling (delayed delivery)
- Read receipts and delivery confirmation

---

## Response Editing and Sending (Story 3.9)

The Response Editing and Sending system enables users to edit AI-generated response drafts directly in Telegram before sending them via Gmail API. After successful sending, responses are automatically indexed into the vector database for future RAG context retrieval.

### Purpose

This service implements the final step of the AI response generation workflow (Epic 3), allowing users to:
- Review AI-generated response drafts in Telegram
- Edit draft text inline using Telegram message replies
- Send approved responses via Gmail API with proper email threading
- Automatically index sent responses for future context

### Architecture

**Service Components:**

1. **ResponseEditingService** (`app/services/response_editing_service.py`)
   - Handles [Edit] button callbacks from Telegram
   - Prompts users to reply with edited text
   - Updates `EmailProcessingQueue.draft_response` in database
   - Re-displays draft message with updated text

2. **ResponseSendingService** (`app/services/response_sending_service.py`)
   - Handles [Send] button callbacks from Telegram
   - Sends emails via GmailClient with proper threading (In-Reply-To headers)
   - Sends confirmation messages to users
   - Indexes sent responses to ChromaDB vector database
   - Handles [Reject] button callbacks

**Integration Points:**

- **Story 3.8 (Response Draft Telegram Messages):** Provides draft messages with inline buttons [Send] [Edit] [Reject]
- **Story 1.9 (Email Sending Capability):** Reuses `GmailClient.send_email()` for sending via Gmail API
- **Story 3.2 (Email Embedding Service):** Reuses `EmbeddingService.embed_text()` for generating embeddings
- **Story 3.1 (Vector Database Setup):** Reuses `VectorDBClient.insert_embedding()` for indexing to ChromaDB
- **Epic 2 (Telegram Bot):** Reuses `TelegramBotClient` for message sending and callback handling

### Edit Workflow

1. User receives response draft message in Telegram with [Edit] button
2. User clicks [Edit] button
3. Bot sends prompt: "Please reply to this message with your edited response"
4. User replies with edited text (using Telegram native reply feature)
5. Bot validates edited text (length < 5000 chars, not empty)
6. Bot updates `EmailProcessingQueue.draft_response` with new text
7. Bot sends confirmation and re-displays draft with same buttons
8. `WorkflowMapping.workflow_state` updated to "draft_edited"

**Example:**
```
User: [Clicks Edit button on draft message]
Bot: ✏️ Edit Response Draft
     Please reply to this message with your edited response.
     📝 Your current draft will be replaced with the new text.

User: [Replies] This is my updated response with corrections.

Bot: ✅ Response Updated
     Your draft has been updated with the new text.
     Use the buttons below to send or make further edits.

     [Re-sends draft message with updated text and buttons]
```

### Send Workflow

1. User clicks [Send] button on response draft (original or edited)
2. Bot loads `draft_response` from `EmailProcessingQueue`
3. Bot initializes `GmailClient` with user's OAuth credentials
4. Bot sends email via `gmail_client.send_email()` with:
   - Recipient: Original email sender
   - Subject: "Re: {original_subject}"
   - Body: Draft response text
   - Thread ID: `email.gmail_thread_id` (ensures proper threading with In-Reply-To headers)
5. Bot updates `EmailProcessingQueue.status` to "completed"
6. Bot sends Telegram confirmation: "✅ Response sent to {recipient}"
7. Bot generates embedding for sent response using `EmbeddingService`
8. Bot indexes sent response to ChromaDB "email_embeddings" collection with metadata
9. `WorkflowMapping.workflow_state` updated to "sent"

**Example:**
```
User: [Clicks Send button]
Bot: ✅ Response sent to john@example.com
     Subject: Re: Project Update Request

     Your response has been delivered successfully.
```

### Vector DB Indexing

After successful email send, the sent response is automatically indexed into ChromaDB for future RAG context:

**Metadata Structure:**
```python
{
    "message_id": "sent_{email_id}_{timestamp}",
    "user_id": user_id,
    "thread_id": gmail_thread_id,
    "sender": original_sender,  # Recipient of our response
    "subject": "Re: {original_subject}",
    "date": datetime.now(UTC).isoformat(),
    "language": detected_language,
    "tone": detected_tone,
    "is_sent_response": True  # Flag to distinguish from received emails
}
```

**Benefits:**
- Sent responses become available for future AI context retrieval
- Enables AI to reference user's own sent responses in future drafts
- Improves response consistency across conversations
- Maintains complete conversation history in vector database

### State Management

**WorkflowMapping State Transitions:**
```
"awaiting_response_approval" (Story 3.8)
    ↓ [User clicks Edit]
"draft_edited" (edit workflow)
    ↓ [User clicks Send]
"sent" (send workflow)

OR

"awaiting_response_approval" (Story 3.8)
    ↓ [User clicks Send directly]
"sent" (send workflow - original draft)

OR

"awaiting_response_approval" (Story 3.8)
    ↓ [User clicks Reject]
"rejected" (reject workflow)
```

**EmailProcessingQueue Status:**
- `"awaiting_response_approval"` → Draft ready for user review
- `"draft_edited"` → User edited the draft
- `"completed"` → Response successfully sent
- `"rejected"` → User rejected the draft

### Security

**Input Validation:**
- Edited text length limit: 5000 characters
- Empty text rejected with error message
- Null checks on all database lookups

**Authorization:**
- User ownership validated before editing or sending
- Telegram user to database user mapping verified
- Email belongs to user check before any modification

**Privacy:**
- Email content not logged in full (only lengths logged)
- OAuth tokens retrieved from database per request
- No credentials hardcoded

### Error Handling

**Edit Workflow Errors:**
- Email not found: "❌ Email not found"
- No draft available: "❌ No draft available to edit"
- Empty edited text: "❌ Edited text cannot be empty"
- Text too long: "❌ Edited text too long ({length} characters). Maximum: 5000"
- Unauthorized: "❌ Unauthorized"

**Send Workflow Errors:**
- Gmail API failure: "❌ Failed to send email: {error}"
- Email not found: "❌ Email not found"
- No draft available: "❌ No draft available to send"
- Indexing failure: Logged but doesn't block send operation (graceful degradation)

### Callback Routing

Telegram callback handlers registered in `app/api/telegram_handlers.py`:

```python
# Callback data format: "{action}_response_{email_id}"
if action == "send_response":
    await handle_send_response(update, context, email_id, db)
elif action == "edit_response":
    await handle_edit_response(update, context, email_id, db)
elif action == "reject_response":
    await handle_reject_response(update, context, email_id, db)
```

### Testing

**Unit Tests:** 10 tests covering:
- Edit button callback handling
- Message reply capture and validation
- Send button handling (original and edited drafts)
- Gmail API threading verification
- Telegram confirmation messages
- Status updates
- Vector DB indexing
- Reject button handling
- Error handling for invalid inputs

**Integration Tests:** 6 tests covering:
- End-to-end edit workflow with database
- End-to-end send workflow (original draft)
- End-to-end send workflow (edited draft)
- Email threading verification (In-Reply-To headers)
- Vector DB indexing verification (ChromaDB)
- Reject workflow with database

**Run Tests:**
```bash
# Unit tests
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
  uv run pytest tests/test_response_editing_sending.py -v

# Integration tests (requires PostgreSQL and ChromaDB running)
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
  uv run pytest tests/integration/test_response_editing_sending_integration.py -v
```

### Related Services

- **Story 3.7:** AI Response Generation Service - Generates initial draft responses
- **Story 3.8:** Response Draft Telegram Messages - Delivers drafts to Telegram with buttons
- **Story 3.6:** Response Generation Prompt Engineering - Defines AI prompts for drafts
- **Story 3.4:** Context Retrieval Service - Retrieves relevant email history for AI context
- **Story 1.9:** Email Sending Capability - Gmail API sending functionality
- **Story 3.1:** Vector Database Setup - ChromaDB for embedding storage

---

## Email Polling Service (Story 1.6)

The email polling service automatically checks Gmail inboxes for new emails at configurable intervals. It uses Celery with Redis as the message broker for background task processing.

### Prerequisites

- Redis server running (via Docker Compose)
- Gmail OAuth flow completed for users
- Celery and Redis dependencies installed

### Starting the Email Polling Service

#### 1. Start Redis Server

```bash
# Start Redis via Docker Compose
docker-compose up -d redis

# Verify Redis is running
docker ps --filter "name=redis"

# Test Redis connection
redis-cli ping  # Should return: PONG
```

#### 2. Start Celery Worker

The Celery worker processes email polling tasks:

```bash
# Start Celery worker in terminal 1
cd backend
source .venv/bin/activate
celery -A app.celery worker --loglevel=info

# Or with specific queue
celery -A app.celery worker --loglevel=info -Q email_polling
```

**Worker Output:**
```
 -------------- celery@hostname v5.5.3
---- **** -----
--- * ***  * -- Darwin-25.0.0-arm64-arm-64bit 2025-11-05 10:00:00
-- * - **** ---
- ** ---------- [config]
- ** ---------- .> app:         mail_agent:0x...
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     redis://localhost:6379/0
- *** --- * --- .> concurrency: 4 (prefork)
-- ******* ---- .> task events: OFF
--- ***** -----
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery

[tasks]
  . app.tasks.email_tasks.poll_all_users
  . app.tasks.email_tasks.poll_user_emails

[2025-11-05 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-11-05 10:00:00,100: INFO/MainProcess] ready.
```

#### 3. Start Celery Beat Scheduler

The Beat scheduler triggers periodic polling tasks:

```bash
# Start Celery beat in terminal 2
cd backend
source .venv/bin/activate
celery -A app.celery beat --loglevel=info
```

**Beat Output:**
```
celery beat v5.5.3 is starting.
__    -    ... __   -        _
LocalTime -> 2025-11-05 10:00:00
Configuration ->
    . broker -> redis://localhost:6379/0
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> celery.beat.PersistentScheduler
    . db -> celerybeat-schedule
    . logfile -> [stderr]@%INFO
    . maxinterval -> 5.00 minutes (300s)
```

### Configuration

Email polling is configured via environment variables in `.env`:

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Polling Interval (seconds)
POLLING_INTERVAL_SECONDS=120  # Poll every 2 minutes
```

### Monitoring

#### Check Polling Status

```bash
# View Celery worker logs
# Terminal 1 shows worker processing tasks:
[2025-11-05 10:00:00,000: INFO] Task poll_all_users started
[2025-11-05 10:00:01,234: INFO] Active users found: 3
[2025-11-05 10:00:01,567: INFO] Task poll_user_emails[user_id=1] started
[2025-11-05 10:00:02,890: INFO] emails_fetched: 5 (user_id=1)
[2025-11-05 10:00:03,123: INFO] new_emails_detected: 2 (user_id=1)
```

#### View Task Queue

```bash
# Inspect active tasks
celery -A app.celery inspect active

# View scheduled tasks
celery -A app.celery inspect scheduled

# View registered tasks
celery -A app.celery inspect registered
```

#### Redis Monitoring

```bash
# Connect to Redis CLI
redis-cli

# View queue length
> LLEN celery
(integer) 3

# View pending tasks
> LRANGE celery 0 -1

# Monitor real-time commands
> MONITOR
```

### Testing

#### Manual Task Trigger

You can manually trigger polling tasks without waiting for the schedule:

```python
from app.tasks.email_tasks import poll_user_emails, poll_all_users

# Poll specific user
result = poll_user_emails.delay(user_id=123)
print(f"Task ID: {result.id}")

# Poll all active users
result = poll_all_users.delay()
print(f"Task ID: {result.id}")
```

#### Integration Test Checklist

1. **Start Services:**
   - ✅ Redis running: `docker-compose up -d redis`
   - ✅ Celery worker running: `celery -A app.celery worker --loglevel=info`
   - ✅ Celery beat running: `celery -A app.celery beat --loglevel=info`

2. **Send Test Email:**
   - Send email to Gmail account connected via OAuth
   - Subject: "Test Email for Mail Agent"

3. **Verify Polling (within 2 minutes):**
   - Watch Celery worker logs for "new_email_detected"
   - Check log entries for message_id, sender, subject

4. **Verify Duplicate Detection:**
   - Wait for next polling cycle (2 minutes)
   - Email should be skipped (already processed)
   - Log should show "duplicates_skipped: 1"

#### Expected Log Output

```json
{
  "event": "polling_cycle_started",
  "user_id": 123,
  "timestamp": "2025-11-05T10:00:00.000Z"
}
{
  "event": "emails_fetched",
  "user_id": 123,
  "count": 3,
  "timestamp": "2025-11-05T10:00:01.234Z"
}
{
  "event": "new_email_detected",
  "user_id": 123,
  "message_id": "abc123xyz",
  "sender": "sender@example.com",
  "subject": "Test Email",
  "received_at": "2025-11-05T09:55:00.000Z",
  "timestamp": "2025-11-05T10:00:02.456Z"
}
{
  "event": "polling_cycle_completed",
  "user_id": 123,
  "new_emails": 2,
  "duplicates": 1,
  "duration_ms": 1234,
  "timestamp": "2025-11-05T10:00:03.678Z"
}
```

### Troubleshooting

#### Redis Connection Errors

```
Error: Redis connection refused
Solution: Ensure Redis is running: docker-compose up -d redis
```

#### Worker Not Processing Tasks

```
Issue: Tasks queued but not executed
Solution:
1. Check worker is running: ps aux | grep celery
2. Restart worker: celery -A app.celery worker --loglevel=info
3. Verify Redis connection: redis-cli ping
```

#### Gmail API Quota Exceeded

```
Error: 429 Too Many Requests
Solution:
1. Reduce polling frequency in .env (POLLING_INTERVAL_SECONDS=180)
2. Check quota usage in Google Cloud Console
3. Implement request batching (future enhancement)
```

#### No Emails Detected

```
Issue: Polling runs but no emails found
Check:
1. User has valid Gmail OAuth token: SELECT gmail_oauth_token FROM users WHERE id=123;
2. Gmail inbox has unread emails
3. Token not expired: Check token_expiry column
4. OAuth scopes granted: Verify gmail.readonly scope
```

### Architecture

The email polling service consists of:

- **poll_all_users()**: Orchestrator task triggered every 2 minutes by Celery Beat
- **poll_user_emails(user_id)**: Individual user polling task spawned by orchestrator
- **Redis**: Message broker for task queuing and result storage
- **Celery Worker**: Background process that executes polling tasks
- **Celery Beat**: Scheduler that triggers poll_all_users() periodically

**Flow:**
1. Beat scheduler → poll_all_users() every 2 minutes
2. poll_all_users() → Query active users from database
3. For each user → Spawn poll_user_emails(user_id) task
4. poll_user_emails() → Call GmailClient.get_messages(query="is:unread")
5. For each email → Check for duplicates, log metadata
6. Future: Save to EmailProcessingQueue (Story 1.7)

### Performance

- **Polling Latency**: New emails detected within 2 minutes
- **Concurrent Users**: Worker handles 4 users concurrently
- **Gmail API Quota**: ~720 polling requests/day per user (7% of quota)
- **Rate Limiting**: 1-second delay between users to avoid API spikes

### Future Enhancements (Epic 2+)

- Priority email detection (immediate notification)
- Batch notifications (digest mode)
- Dynamic polling frequency based on email volume
- AI classification integration (Epic 2)

---

## Email Data Model and Storage (Story 1.7)

The Email Data Model provides persistent storage for email metadata, enabling state tracking and processing workflows. This foundation supports duplicate detection, status management, and query operations for future AI classification and response generation features.

### EmailProcessingQueue Table

The `email_processing_queue` table stores metadata for all emails detected by the polling service:

```sql
CREATE TABLE email_processing_queue (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    gmail_message_id    VARCHAR(255) NOT NULL UNIQUE,
    gmail_thread_id     VARCHAR(255) NOT NULL,
    sender              VARCHAR(255) NOT NULL,
    subject             TEXT,
    received_at         TIMESTAMP WITH TIME ZONE NOT NULL,
    status              VARCHAR(50) NOT NULL DEFAULT 'pending',
    classification      VARCHAR(50),              -- Epic 2
    proposed_folder_id  INTEGER,                  -- Epic 2
    draft_response      TEXT,                     -- Epic 3
    language            VARCHAR(10),              -- Epic 3
    priority_score      INTEGER DEFAULT 0,        -- Epic 2
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX idx_email_user_id ON email_processing_queue(user_id);
CREATE INDEX idx_email_gmail_message_id ON email_processing_queue(gmail_message_id);
CREATE INDEX idx_email_status ON email_processing_queue(status);
CREATE INDEX idx_email_gmail_thread_id ON email_processing_queue(gmail_thread_id);
```

**Key Features:**
- **Unique Constraint**: `gmail_message_id` prevents duplicate emails
- **Cascade Delete**: Deleting a user automatically removes all associated emails (GDPR compliance)
- **Timezone-Aware Timestamps**: All datetime fields use `timezone=True`
- **Future-Proof**: Includes nullable columns for Epic 2 (AI classification) and Epic 3 (response generation)

### Email Status States

The `status` field tracks email processing lifecycle:

| Status | Description | Next State |
|--------|-------------|------------|
| `pending` | Email detected, awaiting classification | `processing` |
| `processing` | AI classification in progress | `approved` / `rejected` |
| `approved` | User approved sorting via Telegram | `completed` |
| `rejected` | User rejected sorting suggestion | `pending` |
| `completed` | Email sorted and processed | Terminal state |

**Status Transitions:**
```
pending → processing → approved → completed
                    ↘ rejected → pending (retry)
```

### EmailService API Methods

The `EmailService` class provides query and status management methods:

#### Get Emails by Status

```python
from app.services.email_service import EmailService

email_service = EmailService()

# Fetch all pending emails for a user
pending_emails = await email_service.get_pending_emails(user_id=123)

for email in pending_emails:
    print(f"{email.sender}: {email.subject}")
```

#### Get Email by Gmail Message ID

```python
# Check if email already exists (duplicate detection)
email = await email_service.get_email_by_message_id(
    gmail_message_id="abc123xyz"
)

if email:
    print(f"Email already processed with status: {email.status}")
```

#### Update Email Status

```python
# Update email status after classification
updated_email = await email_service.update_email_status(
    email_id=456,
    new_status="approved"
)
```

#### Query by Custom Status

```python
# Get all emails in processing state
processing_emails = await email_service.get_emails_by_status(
    user_id=123,
    status="processing"
)
```

### Example Queries

#### Find Unprocessed Emails

```sql
SELECT id, sender, subject, received_at, status
FROM email_processing_queue
WHERE user_id = 123 AND status = 'pending'
ORDER BY received_at DESC;
```

#### Check Duplicate Detection

```sql
SELECT COUNT(*) as total_emails,
       COUNT(DISTINCT gmail_message_id) as unique_emails
FROM email_processing_queue
WHERE user_id = 123;
```

#### Status Distribution

```sql
SELECT status, COUNT(*) as count
FROM email_processing_queue
WHERE user_id = 123
GROUP BY status
ORDER BY count DESC;
```

### Integration with Email Polling

The polling service (`poll_user_emails` task) automatically persists new emails:

```python
# In backend/app/tasks/email_tasks.py

@shared_task(bind=True, max_retries=3)
def poll_user_emails(self, user_id: int):
    """Poll Gmail and save new emails to database"""
    emails = await gmail_client.get_messages(query="is:unread", max_results=50)

    new_count = 0
    skip_count = 0

    async with database_service.async_session() as session:
        for email in emails:
            # Check for duplicate
            existing = await email_service.get_email_by_message_id(
                email['message_id']
            )

            if existing:
                skip_count += 1
                continue

            # Create new email record
            new_email = EmailProcessingQueue(
                user_id=user_id,
                gmail_message_id=email['message_id'],
                gmail_thread_id=email['thread_id'],
                sender=email['sender'],
                subject=email['subject'],
                received_at=email['received_at'],
                status="pending"
            )

            session.add(new_email)
            new_count += 1

        await session.commit()

    logger.info("polling_completed",
        user_id=user_id,
        new_emails=new_count,
        duplicates_skipped=skip_count
    )
```

### Performance Considerations

- **Duplicate Detection**: < 1ms via unique index on `gmail_message_id`
- **Status Queries**: < 10ms via index on `status` column
- **User Email Lookup**: < 5ms via index on `user_id`
- **Thread Grouping**: Efficient via index on `gmail_thread_id` (Epic 2)

**Scalability:**
- Supports 10,000+ emails per user with indexed queries
- Batch insert performance: 50 emails in < 500ms
- Optimized for high-frequency polling (every 2 minutes)

### Testing

Run email model tests:

```bash
# Test EmailProcessingQueue model
pytest backend/tests/test_email_model.py -v

# Test EmailService query methods
pytest backend/tests/test_email_service.py -v

# Test polling integration with database
pytest backend/tests/test_email_polling.py -v
```

---

## Features Deferred

The following template features are deferred to later stories:

- **JWT Authentication** - Story 1.4 (user registration, login, JWT tokens)
- **LangGraph Workflows** - Epic 2 (AI email classification, chatbot endpoints)
- **Langfuse Integration** - Epic 2 (LLM observability and monitoring)

---

## Batch Notification System (Epic 2 - Story 2.8)

The batch notification system sends daily summaries of pending emails to users via Telegram, reducing interruptions throughout the day. High-priority emails bypass batching and notify immediately.

### Overview

Instead of sending individual Telegram notifications for every email that needs approval, Mail Agent batches non-priority emails and sends:
1. **Summary message** showing total count and breakdown by proposed category
2. **Individual proposal messages** for each pending email with approval buttons

This reduces notification fatigue while ensuring priority emails (urgent government documents, important client emails) are still delivered immediately.

### Batch Flow

1. **Celery Beat Scheduler** triggers `send_batch_notifications` task daily at configured time (default: 6 PM UTC)
2. **For each active user:**
   - Load NotificationPreferences (batch_enabled, batch_time, quiet_hours)
   - Query EmailProcessingQueue for pending emails (status="awaiting_approval", is_priority=False)
   - If no pending emails → skip user (no notification sent)
   - Create summary message with count and category breakdown
   - Send summary message to Telegram
   - Send individual proposal messages for each pending email
   - Log batch completion with metrics

### Priority Email Detection System (Story 2.9)

The priority email detection system analyzes incoming emails and assigns a priority score (0-100) to determine if they require immediate notification. Emails scoring >= 70 bypass batch processing and are sent to users immediately via Telegram.

#### Priority Scoring Algorithm

The system uses a multi-factor scoring algorithm:

| Factor | Points | Trigger |
|--------|--------|---------|
| **Government Domain** | +50 | Email from official government domains (finanzamt.de, auslaenderbehoerde.de, arbeitsagentur.de, etc.) |
| **Urgency Keywords** | +30 | Subject/body contains keywords: "urgent", "deadline", "wichtig", "dringend", "срочно", "терміново" (multilingual) |
| **User-Configured Sender** | +40 | Sender matches FolderCategory with is_priority_sender=True |
| **Maximum Score** | 100 | Score is capped at 100 (won't exceed even if all factors present) |

**Priority Threshold:** Emails with priority_score >= 70 are marked as high-priority.

#### Government Domains (Default List)

The following government domains automatically trigger +50 priority points:

- `finanzamt.de` - Tax Office (Finanzamt)
- `auslaenderbehoerde.de` - Immigration Office (Ausländerbehörde)
- `arbeitsagentur.de` - Employment Agency (Arbeitsagentur)
- `bundesagentur.de` - Federal Agency
- `bmf.de` - Federal Ministry of Finance
- `bmi.de` - Federal Ministry of Interior

**Custom domains:** Additional government domains can be configured via `PRIORITY_GOVERNMENT_DOMAINS` environment variable.

#### Urgency Keywords (Multilingual)

The system detects urgency keywords in 4 languages:

- **English:** urgent, deadline, immediate, asap, action required
- **German:** wichtig, dringend, frist, eilig, sofort
- **Russian:** срочно, важно, крайний срок
- **Ukrainian:** терміново, важливо, дедлайн

Keywords are matched case-insensitively in both subject and body preview.

#### Priority Email Flow

```
Email Received
    ↓
extract_context (load email content)
    ↓
classify (AI classification)
    ↓
detect_priority (priority scoring) ← Story 2.9
    │
    ├─ Check government domain
    ├─ Check urgency keywords
    ├─ Check user-configured senders
    ├─ Calculate total score (capped at 100)
    └─ Set is_priority = (score >= 70)
    ↓
send_telegram
    │
    ├─ If is_priority=True:
    │   ├─ Send immediately with ⚠️ indicator
    │   └─ Log: "priority_email_sent_immediate"
    │
    └─ If is_priority=False:
        ├─ Mark status="awaiting_approval"
        └─ Queue for batch notification
```

#### User-Configurable Priority Senders

Users can mark specific senders as priority in their FolderCategory settings:

1. Create or edit a FolderCategory
2. Set `is_priority_sender=True`
3. Add sender patterns to `keywords` field (e.g., "important-client@example.com")
4. Emails matching those patterns receive +40 priority points

**Example:**
```python
folder = FolderCategory(
    user_id=user.id,
    name="VIP Clients",
    keywords=["ceo@company.com", "priority@client.com"],
    is_priority_sender=True  # Adds +40 to priority score
)
```

#### Configuration

Priority detection can be configured via environment variables in `.env`:

```bash
# Priority Detection Configuration
PRIORITY_THRESHOLD=70                    # Score threshold (0-100), default: 70
PRIORITY_GOVERNMENT_DOMAINS=finanzamt.de,auslaenderbehoerde.de,arbeitsagentur.de
```

**Variables:**
- `PRIORITY_THRESHOLD`: Minimum score required for immediate notification (default: 70)
- `PRIORITY_GOVERNMENT_DOMAINS`: Comma-separated list of additional government domains

#### Priority Detection Examples

**Example 1: Government Email with Deadline (Priority)**
```
Email:
  From: finanzamt@berlin.de
  Subject: Wichtig: Steuerfrist 15.12.2024

Detection:
  government_domain: +50 (finanzamt.de)
  keyword: +30 (wichtig, frist)
  user_config: +0

  priority_score = 80
  is_priority = True (>= 70)

Result: Immediate Telegram notification with ⚠️
```

**Example 2: Newsletter (Non-Priority)**
```
Email:
  From: newsletter@company.com
  Subject: Weekly updates

Detection:
  government_domain: +0
  keyword: +0
  user_config: +0

  priority_score = 0
  is_priority = False (< 70)

Result: Batched for end-of-day notification
```

**Example 3: User-Configured Priority Sender**
```
Email:
  From: important-client@example.com
  Subject: Project status

Detection (assuming FolderCategory.is_priority_sender=True):
  government_domain: +0
  keyword: +0
  user_config: +40

  priority_score = 40
  is_priority = False (< 70)

Result: Batched (user can adjust threshold or add keywords)
```

#### Testing

```bash
# Run unit tests (priority detection service logic)
DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" uv run pytest tests/test_priority_detection.py -v

# Run integration tests (workflow integration)
DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" uv run pytest tests/integration/test_priority_detection_integration.py -v

# Test specific scenario
uv run pytest tests/test_priority_detection.py::test_government_domain_detection -v
```

#### Monitoring and Logging

Priority detection events are logged with structured logging:

```python
logger.info(
    "priority_detection_completed",
    email_id=123,
    sender="steuer@finanzamt.de",
    priority_score=80,
    is_priority=True,
    detection_reasons=["government_domain:finanzamt.de", "keyword:wichtig"]
)
```

**Key log events:**
- `priority_detection_completed` - Detection result for each email
- `priority_email_sent_immediate` - High-priority email sent to Telegram
- `email_marked_for_batch` - Non-priority email queued for batch

#### Troubleshooting

**Priority emails not sent immediately:**
1. Check priority_score in database: `SELECT priority_score, is_priority FROM email_processing_queue WHERE id=123;`
2. Verify threshold: Ensure priority_score >= PRIORITY_THRESHOLD (default: 70)
3. Check Telegram bot connection: User must have telegram_id linked
4. Review logs: Search for "priority_detection_completed" and "priority_email_sent_immediate"

**Government domain not detected:**
1. Verify domain in GOVERNMENT_DOMAINS list (backend/app/config/priority_config.py)
2. Check sender format: System handles "Name <email@domain.de>" and "email@domain.de"
3. Add custom domain via PRIORITY_GOVERNMENT_DOMAINS env var

**Keywords not triggering priority:**
1. Keywords must be in subject OR body_preview (first 200 characters)
2. Matching is case-insensitive
3. Review keyword list: backend/app/config/priority_config.py → PRIORITY_KEYWORDS
4. Check logs for detection_reasons: Should include "keyword:wichtig" etc.

**User-configured senders not working:**
1. Verify FolderCategory.is_priority_sender=True in database
2. Check keywords field matches sender (case-insensitive substring match)
3. Ensure sender is in FolderCategory.keywords array
4. Example: keywords=["important@example.com"] matches "John <important@example.com>"

---

### Priority Email Bypass (AC #6)

High-priority emails (priority_score >= 70) bypass batch scheduling:
- Detected in detect_priority node based on government domains, keywords, and user configuration
- Sent immediately via send_telegram_node with ⚠️ indicator
- NOT included in batch notification query (is_priority=False filter in batch service)
- Database fields: EmailProcessingQueue.priority_score (0-100) and EmailProcessingQueue.is_priority (boolean)

### NotificationPreferences Configuration

Users can configure batch notification settings (stored in `notification_preferences` table):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `batch_enabled` | boolean | True | Enable/disable daily batch notifications |
| `batch_time` | time | 18:00 | Preferred batch time (UTC) |
| `priority_immediate` | boolean | True | Send priority emails immediately |
| `quiet_hours_start` | time | null | Suppress notifications after this time (e.g., 22:00) |
| `quiet_hours_end` | time | null | Resume notifications after this time (e.g., 08:00) |
| `timezone` | string | UTC | User timezone for scheduling (future enhancement) |

**Future Enhancement (Epic 4):** Users will configure these preferences via the frontend UI. Currently, defaults are applied automatically.

### Testing

```bash
# Run unit tests
DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" uv run pytest backend/tests/test_batch_notification_service.py -v

# Run integration tests
DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" uv run pytest backend/tests/integration/test_batch_notification_integration.py -v

# Manual Celery task trigger (development)
celery -A app.celery call app.tasks.notification_tasks.send_batch_notifications
```

### Running Celery Workers

The batch notification system requires Celery Beat and workers to be running:

```bash
# Terminal 1: Start Celery worker for notifications queue
celery -A app.celery worker --loglevel=info --queue=notifications

# Terminal 2: Start Celery Beat scheduler
celery -A app.celery beat --loglevel=info

# Combined (development only):
celery -A app.celery worker --beat --loglevel=info --queue=notifications
```

### Troubleshooting

**Batch not sending:**
- Verify Celery Beat is running: `celery -A app.celery inspect active`
- Check NotificationPreferences: `batch_enabled` must be True
- Check quiet hours: current time must be outside `quiet_hours_start`/`quiet_hours_end`
- Check pending emails: EmailProcessingQueue must have status="awaiting_approval", is_priority=False
- Verify Redis is running: `docker ps | grep redis`

**Individual proposals not sent:**
- Check Telegram rate limits: 30 messages/second, 20 messages/minute per chat
- Verify rate limiting delay (100ms between sends) in logs
- Check telegram_message_id stored in WorkflowMapping

**Priority emails not bypassing batch:**
- Verify priority_score >= 70 in EmailProcessingQueue
- Check send_telegram node logs for "priority_email_sent_immediate"
- Confirm is_priority field set to True for priority emails

---

## Epic 2: Integration Testing

### Overview

Epic 2 includes comprehensive integration testing for the AI-powered email classification and Telegram approval workflow (Story 2.12).

**Test Coverage:**
- Complete email sorting workflow
- Rejection and folder change scenarios
- Batch notification system
- Priority email immediate notifications
- Approval history tracking
- Performance validation (NFR001: <120s latency)
- Error handling and recovery

### Running Tests

```bash
# All Epic 2 integration tests
DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
uv run pytest tests/integration/test_epic_2_workflow_integration.py -v

# Specific test scenarios
DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
uv run pytest tests/integration/test_epic_2_workflow_integration.py::TestCompleteEmailWorkflow -v
```

### Test Infrastructure

**Mock Classes:** `backend/tests/mocks/`
- `MockGeminiClient` - Deterministic AI responses
- `MockGmailClient` - Gmail API mock with call tracking
- `MockTelegramBot` - Telegram API mock with message simulation

**Test Fixtures:** Defined in `backend/tests/conftest.py`
- Database isolation with per-test cleanup
- LangGraph checkpoint cleanup between tests
- Pre-populated test users, folders, and preferences

### Performance Benchmarks

**NFR001 Target:** Email → Telegram notification ≤ 120 seconds

**Measured (p95):**
- Total processing (excluding polling): ~10s ✅
- Workflow resumption: ~3s
- AI classification: ~5s
- Gmail/Telegram API calls: ~1s each

### Documentation

- **Architecture:** `docs/epic-2-architecture.md`
- **Workflow Diagram:** `docs/diagrams/email-workflow-flow.mermaid`
- **Story Details:** `docs/stories/2-12-epic-2-integration-testing.md`

---

## Epic 3: Multilingual Response Quality Testing

### Overview

Epic 3 completes the RAG-powered AI response generation system with comprehensive multilingual quality validation across 4 supported languages (Russian, Ukrainian, English, German). Story 3.10 implements a systematic testing framework to ensure response quality meets production standards.

**Test Coverage:**
- Multilingual response generation (Russian, Ukrainian, English, German)
- Response quality evaluation (language accuracy, tone appropriateness, context awareness)
- Formal German government email responses (Finanzamt, Ausländerbehörde)
- Edge case handling (mixed languages, no thread history, ambiguous tone, short emails, long threads)
- Performance benchmarks (RAG retrieval <3s, end-to-end <120s per NFR001)
- Complete workflow validation (email → RAG → response → Telegram → approval → send → indexing)

### Test Data Fixtures

**Location:** `backend/tests/fixtures/multilingual_emails/`

**Structure:**
```
tests/fixtures/multilingual_emails/
├── russian/
│   ├── business_inquiry.json
│   ├── personal_casual.json
│   └── formal_government.json
├── ukrainian/
│   ├── client_request.json
│   ├── casual_personal.json
│   └── professional_business.json
├── english/
│   ├── business_proposal.json
│   ├── casual_friend.json
│   └── formal_corporate.json
├── german/
│   ├── finanzamt_tax.json           # Government formal German
│   ├── auslaenderbehoerde_visa.json  # Government formal German
│   ├── business_professional.json
│   └── casual_personal.json
└── edge_cases/
    ├── mixed_language_email.json
    ├── no_thread_history.json
    ├── unclear_tone.json
    ├── short_email.json
    └── very_long_thread.json
```

**JSON Format:**
```json
{
  "original_email": {
    "sender": "sender@example.com",
    "subject": "Email subject",
    "body": "Email body text...",
    "language": "de",
    "expected_tone": "formal"
  },
  "thread_history": [
    {
      "sender": "previous@example.com",
      "subject": "Re: Previous email",
      "body": "Previous email body...",
      "date": "2024-01-15"
    }
  ],
  "expected_response_criteria": {
    "language": "de",
    "tone": "formal",
    "must_include_greeting": "Sehr geehrte Damen und Herren,",
    "must_include_closing": "Mit freundlichen Grüßen",
    "context_keywords": ["visa", "application", "deadline"]
  }
}
```

### Response Quality Evaluation Framework

**Module:** `backend/tests/evaluation/response_quality.py`

**Evaluation Dimensions:**

1. **Language Accuracy (40% weight):**
   - Uses `langdetect` library to verify response language matches expected (ru/uk/en/de)
   - Returns score (0-100) and confidence level
   - Example: `evaluate_language_accuracy(response, expected_language="de")`

2. **Tone Appropriateness (30% weight):**
   - Checks for appropriate greetings (e.g., "Sehr geehrte Damen und Herren" for formal German)
   - Verifies appropriate closings (e.g., "Mit freundlichen Grüßen")
   - Validates formality level matches expected (formal/professional/casual)
   - Example: `evaluate_tone_appropriateness(response, expected_tone="formal", language="de")`

3. **Context Awareness (30% weight):**
   - Checks if response references thread history appropriately
   - Verifies key topics from original email are addressed
   - Returns score (0-100) with matched keywords
   - Example: `evaluate_context_awareness(response, expected_context_keywords=["visa", "deadline"])`

**Overall Quality Scoring:**
```python
from evaluation.response_quality import evaluate_response_quality, ResponseQualityReport

# Evaluate response
report: ResponseQualityReport = evaluate_response_quality(
    response_text="Sehr geehrte Damen und Herren...",
    expected_criteria={
        "language": "de",
        "tone": "formal",
        "greeting": "Sehr geehrte Damen und Herren,",
        "closing": "Mit freundlichen Grüßen",
        "context_keywords": ["visa", "application"]
    }
)

# Check quality threshold (80% for standard, 90% for government emails)
assert report.overall_score >= 80  # Standard threshold
assert report.is_acceptable()      # True if >= 80%

# Access detailed scores
print(f"Language: {report.language_score}")  # 0-100
print(f"Tone: {report.tone_score}")          # 0-100
print(f"Context: {report.context_score}")    # 0-100
```

### Running Tests

**Unit Tests (8 tests - evaluation framework):**
```bash
# Run response quality evaluation unit tests
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
uv run pytest backend/tests/test_response_quality_evaluation.py -v

# Expected output:
# test_evaluate_language_accuracy_russian      PASSED
# test_evaluate_language_accuracy_german       PASSED
# test_evaluate_tone_appropriateness_formal_german PASSED
# test_evaluate_tone_appropriateness_casual_english PASSED
# test_evaluate_context_awareness_thread_reference PASSED
# test_evaluate_context_awareness_no_context   PASSED
# test_response_quality_report_aggregation     PASSED
# test_response_quality_acceptable_threshold   PASSED
```

**Integration Tests (12 tests - multilingual scenarios):**
```bash
# Run all Epic 3 multilingual response quality integration tests
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
uv run pytest backend/tests/integration/test_multilingual_response_quality.py -v

# Run specific test scenario (German government email - critical for AC #4)
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
uv run pytest backend/tests/integration/test_multilingual_response_quality.py::test_german_government_email_formal_response -v

# Run only performance benchmark tests
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
uv run pytest backend/tests/integration/test_multilingual_response_quality.py -v -k "performance"
```

**Test Categories:**

1. **Multilingual Tests (4 tests):**
   - `test_russian_business_inquiry_response` - Russian email workflow
   - `test_ukrainian_client_request_response` - Ukrainian email workflow
   - `test_english_business_proposal_response` - English email workflow
   - `test_german_government_email_formal_response` - **Critical:** Formal German government email (AC #4)

2. **Edge Case Tests (5 tests):**
   - `test_mixed_language_email_response` - German + English mixed
   - `test_no_thread_history_response` - First email in thread
   - `test_unclear_tone_detection` - Ambiguous formality
   - `test_short_email_language_detection` - <50 characters
   - `test_very_long_thread_response` - 10+ emails in thread

3. **Performance Tests (2 tests):**
   - `test_rag_context_retrieval_performance` - RAG retrieval <3s (NFR001)
   - `test_response_generation_end_to_end_performance` - Full pipeline <120s (NFR001)

4. **Complete Workflow Test (1 test):**
   - `test_complete_email_to_telegram_to_send_workflow` - End-to-end workflow validation

### Performance Benchmark Interpretation

**RAG Context Retrieval (<3s requirement):**
```
Test output breakdown:
- Vector search time: 1.2s (ChromaDB semantic search)
- Gmail thread fetch time: 0.8s (Gmail API call)
- Context assembly time: 0.3s (formatting for prompt)
- Total: 2.3s ✅ (meets NFR001 <3s requirement)
```

**End-to-End Response Generation (<120s requirement):**
```
Test output breakdown:
- Language detection: 0.5s (langdetect)
- Tone detection: 2.1s (rule-based) or 4.3s (LLM fallback)
- RAG retrieval: 2.3s (see above)
- Response generation: 45-60s (Gemini API latency)
- Telegram delivery: 1.2s
- Total: 50-70s ✅ (well under 120s requirement)
```

**Interpreting Results:**
- If RAG retrieval >3s: Check ChromaDB performance, consider indexing optimization
- If end-to-end >120s: Check Gemini API latency, consider prompt optimization
- Performance degradation may indicate need for vector database maintenance

### Test Infrastructure

**Response Quality Evaluation Module:** `backend/tests/evaluation/response_quality.py`
- Language accuracy evaluation using langdetect
- Tone appropriateness evaluation with greeting/closing validation
- Context awareness evaluation with keyword matching
- Aggregated scoring with weighted dimensions (language 40%, tone 30%, context 30%)

**Test Fixtures:** `backend/tests/fixtures/multilingual_emails/`
- 17 anonymized multilingual email samples (Russian, Ukrainian, English, German + edge cases)
- JSON format with original_email, thread_history, expected_response_criteria
- Government email samples (German Finanzamt/Ausländerbehörde) for formal tone testing

**Mock Strategy:**
- Real database (PostgreSQL) with test isolation
- Mocked external services (Gmail API, Telegram API) for fast execution
- Real language detection (langdetect) and quality evaluation
- Mocked Gemini API responses with realistic multilingual samples

### Success Criteria

**Unit Tests:**
- 8/8 unit tests passing for evaluation framework
- 80%+ code coverage for response_quality.py module

**Integration Tests:**
- 12/12 integration tests passing (4 multilingual + 5 edge cases + 2 performance + 1 complete workflow)
- No test failures or errors
- Performance benchmarks within NFR001 limits (RAG <3s, end-to-end <120s)

**Quality Thresholds:**
- Standard emails: 80%+ overall response quality score
- Government emails: 90%+ overall response quality score (higher expectations for formal German)
- Language detection: 95%+ accuracy across all 4 languages

### Documentation

- **Epic 3 Tech Spec:** `docs/tech-spec-epic-3.md` (Smart Hybrid RAG strategy, response quality evaluation framework, known limitations)
- **Architecture:** `docs/architecture.md` (Epic 3 RAG flow diagrams, context retrieval logic)
- **Story Details:** `docs/stories/3-10-multilingual-response-quality-testing.md` (Comprehensive test plan and acceptance criteria)

---

## E2E (End-to-End) Testing

### Overview

E2E tests verify **REAL integration** with external services (Gmail, Gemini AI, Telegram). These tests:
- ✅ Use REAL APIs (not mocks)
- ✅ Verify complete workflow end-to-end
- ⚠️ Cost money (Gemini API)
- ⚠️ Take 30-60 seconds to complete
- ⚠️ Should be run MANUALLY before releases only

**Why separate E2E tests?**
- **Integration tests (with mocks):** Fast, free, run in CI/CD on every commit
- **E2E tests (with real APIs):** Slow, paid, run manually before releases
- E2E tests are "smoke tests" for production readiness

### Running E2E Tests

**⚠️ WARNING: E2E tests make REAL API calls that cost money!**

```bash
# 1. Configure environment variables (see tests/e2e/README.md)
export GMAIL_TEST_OAUTH_TOKEN="ya29.a0..."
export TELEGRAM_BOT_TOKEN="123456789:ABC..."
export TELEGRAM_TEST_CHAT_ID="123456789"
export GEMINI_API_KEY="AIzaSy..."
export DATABASE_URL="postgresql+psycopg://..."

# 2. Run ALL E2E tests
pytest tests/e2e/ -v -m e2e

# 3. Run specific test suite
pytest tests/e2e/test_gmail_real_api.py -v -m e2e          # Gmail only
pytest tests/e2e/test_telegram_real_api.py -v -m e2e       # Telegram only
pytest tests/e2e/test_complete_workflow_e2e.py -v -m e2e   # Complete workflow (CRITICAL!)
```

### E2E Test Suites

1. **Gmail API Tests** (`test_gmail_real_api.py`)
   - Create/delete real Gmail labels
   - Apply labels to messages
   - OAuth token refresh

2. **Telegram API Tests** (`test_telegram_real_api.py`)
   - Send real messages
   - Inline keyboard buttons
   - Message editing
   - HTML formatting

3. **Complete Workflow Tests** (`test_complete_workflow_e2e.py`) 🚨 **CRITICAL**
   - Full flow: Gmail → Gemini AI → Telegram → Database
   - Verifies ALL services integrate correctly
   - **THIS IS THE MOST IMPORTANT TEST!**

### What to Check After Running

After running E2E tests:

1. ✅ All tests pass without errors
2. **📱 CHECK YOUR TELEGRAM APP:**
   - You should receive test messages
   - Buttons should display correctly
   - Formatting should work
3. ✅ Check test output for verification checkmarks:
   ```
   ✅ Verified:
      ✅ Gmail API: Fetched real email
      ✅ Gemini AI: Classified email with real AI
      ✅ Telegram Bot: Sent real notification
      ✅ Database: Persisted data correctly
      ✅ Integration: All services work together
   ```

### Setup Guide

**Detailed setup instructions:** See `tests/e2e/README.md`

Quick setup:
1. Get Gmail OAuth tokens from your dev database
2. Create Telegram bot with @BotFather
3. Get Gemini API key from Google AI Studio
4. Create `.env.e2e` file with credentials
5. Load environment variables: `export $(cat .env.e2e | xargs)`

### Cost Estimate

- **Gmail API:** Free (up to 250 requests/day)
- **Telegram API:** Free (unlimited)
- **Gemini API:** ~$0.001-0.002 per test run
- **Total per run:** ~$0.01-0.03 (1-3 cents)

### When to Run E2E Tests

✅ **MUST run before:**
- Production releases
- Major integration changes
- After dependency updates

⚠️ **Optional:**
- Before client demos
- After bugfixes in integrations

❌ **DO NOT run:**
- On every commit (use integration tests with mocks)
- During development (use mock tests)
- Frequently (costs money)

### Troubleshooting

See detailed troubleshooting guide in `tests/e2e/README.md`

Common issues:
- Missing environment variables
- Invalid OAuth tokens
- Bot not started in Telegram
- No emails in test Gmail account

---

## ChromaDB Vector Database Setup (Epic 3)

ChromaDB is a self-hosted vector database used for storing email embeddings for semantic search in the RAG (Retrieval-Augmented Generation) system.

### Installation

ChromaDB is automatically installed with project dependencies:

```bash
# Included in pyproject.toml
chromadb>=0.4.22
```

To manually install or upgrade:
```bash
uv pip install "chromadb>=0.4.22"
```

Verify installation:
```bash
python -c "import chromadb; print(chromadb.__version__)"
# Expected output: 1.3.4 (or higher)
```

### Configuration

Add to your `.env` file:

```bash
# ChromaDB Vector Database (Epic 3 - Story 3.1)
# Path for persistent vector database storage
CHROMADB_PATH=./backend/data/chromadb
```

The ChromaDB storage directory is automatically created and gitignored (`backend/data/`).

### Initialization

ChromaDB is automatically initialized on application startup. The `email_embeddings` collection is created with:

- **Distance Metric**: Cosine similarity (optimal for semantic search)
- **Storage Backend**: Persistent SQLite (embeddings survive service restarts)
- **Embedding Dimensions**: 768 (matches Gemini text-embedding-004 model)

### Test Endpoint

Verify ChromaDB connectivity:

```bash
# GET /api/v1/test/vector-db
curl http://localhost:8000/api/v1/test/vector-db
```

Expected response:
```json
{
  "status": "connected",
  "collection_name": "email_embeddings",
  "total_embeddings": 0,
  "distance_metric": "cosine",
  "persist_directory": "./backend/data/chromadb"
}
```

### Performance

- **Query Performance**: k=10 nearest neighbors in ~2ms (target: <500ms)
- **Storage**: ~2.7 MB per user (90 days, 10 emails/day)
- **MVP Scale**: 100 users ≈ 270 MB total

### Security & Privacy

- ✅ **Local Storage**: All embeddings stored on your server (no cloud transmission)
- ✅ **No Hardcoded Secrets**: ChromaDB path from environment variable
- ✅ **Data Sovereignty**: Full control over email embeddings
- ✅ **GDPR Compliant**: Self-hosted, privacy-first design

### Detailed Documentation

For comprehensive ChromaDB documentation, see:
- **Setup Guide**: `docs/vector-database-setup.md`
- **VectorDBClient API**: `backend/app/core/vector_db.py`
- **Unit Tests**: `backend/tests/test_vector_db_client.py`
- **Integration Tests**: `backend/tests/integration/test_vector_db_integration.py`

---

## Email Embedding Service Setup (Epic 3)

The Email Embedding Service converts email content into 768-dimensional vector embeddings using Google's Gemini `text-embedding-004` model for semantic search in the RAG system.

### Installation

The embedding service dependencies are automatically installed with project dependencies:

```bash
# Included in pyproject.toml
google-generativeai>=0.8.3
beautifulsoup4>=4.12.0
```

To manually install or upgrade:
```bash
uv pip install "google-generativeai>=0.8.3" "beautifulsoup4>=4.12.0"
```

### Configuration

Add to your `.env` file (if not already present from Epic 2):

```bash
# Gemini API Configuration (Epic 2 - AI Classification, Epic 3 - Embeddings)
GEMINI_API_KEY="your-gemini-api-key-here"
GEMINI_MODEL="gemini-2.5-flash"
```

**Get your free API key**: [Google AI Studio](https://makersuite.google.com/app/apikey)

### Usage

```python
from app.core.embedding_service import EmbeddingService

# Initialize service (uses GEMINI_API_KEY from environment)
service = EmbeddingService()

# Single embedding
email_text = "Your order #12345 has been shipped."
embedding = service.embed_text(email_text)
print(f"Dimensions: {len(embedding)}")  # Output: 768

# Batch embedding (up to 50 emails)
emails = ["Email 1", "Email 2", "Email 3"]
embeddings = service.embed_batch(emails, batch_size=50)
```

### Features

- **Automatic HTML Stripping**: Removes HTML tags from email content
- **Token Truncation**: Limits input to 2048 tokens (Gemini API limit)
- **Batch Processing**: Efficient batch embedding (up to 50 emails per batch)
- **Error Handling**: Automatic retry with exponential backoff (3 attempts)
- **Multilingual Support**: Native support for ru/uk/en/de and 50+ languages
- **Usage Tracking**: Built-in metrics for free-tier monitoring

### Test Endpoint

Verify embedding service connectivity and get usage statistics:

```bash
# GET /api/v1/test/embedding-stats
curl http://localhost:8000/api/v1/test/embedding-stats
```

Expected response:
```json
{
  "total_requests": 0,
  "total_embeddings_generated": 0,
  "avg_latency_ms": 0.0,
  "service_initialized": true
}
```

### Performance

- **Single Embedding**: ~200-500ms latency
- **Batch (50 emails)**: <60 seconds total
- **Throughput**: ~50 emails/minute
- **Dimensions**: 768 (matches ChromaDB collection)

### Detailed Documentation

For comprehensive embedding service documentation, see:
- **Setup Guide**: `docs/embedding-service-setup.md`
- **EmbeddingService API**: `backend/app/core/embedding_service.py`
- **Preprocessing API**: `backend/app/core/preprocessing.py`
- **Unit Tests**: `backend/tests/test_embedding_service.py`, `backend/tests/test_preprocessing.py`
- **Integration Tests**: `backend/tests/integration/test_embedding_integration.py`

---

## Email History Indexing Service (Epic 3 - Story 3.3)

The Email History Indexing Service orchestrates bulk indexing of user's Gmail history into ChromaDB vector database for RAG-based context retrieval. Designed for fast onboarding with checkpoint-based resumption and comprehensive error handling.

### Overview

**Key Features:**
- **90-Day Historical Indexing**: Indexes last 90 days of emails (configurable) for fast onboarding
- **Gmail Pagination**: Efficient batched retrieval with date filtering
- **Batch Processing**: 50 emails per batch with 60-second rate limiting
- **Checkpoint Mechanism**: Resumable indexing with progress tracking
- **Error Handling**: Retry logic for transient API errors
- **Telegram Notifications**: User notification on completion
- **Incremental Indexing**: Automatic indexing of new emails post-classification

### Installation

The indexing service dependencies are automatically installed with project dependencies:

```bash
# Core dependencies (included in pyproject.toml)
google-generativeai>=0.8.3   # Gemini API for embeddings
chromadb>=0.4.22              # Vector database
langdetect>=1.0.9             # Language detection for metadata

# Already installed with Epic 1 & 2
celery>=5.3.0                 # Background task queue
redis>=5.0.0                  # Celery broker
```

To manually install or upgrade:
```bash
uv pip install langdetect
```

Verify installation:
```bash
python -c "import langdetect; print('langdetect installed')"
```

### Configuration

Add to your `.env` file:

```bash
# ChromaDB Vector Database (required)
CHROMADB_PATH=./backend/data/chromadb

# Gemini API (required for embeddings)
GEMINI_API_KEY=your_gemini_api_key_here

# Celery (required for background tasks)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Gmail API (required for email retrieval)
# Set up via Story 1.4 (OAuth flow)
```

### Database Migration

The indexing service requires the `indexing_progress` table:

```bash
# Apply migration (auto-created during implementation)
alembic upgrade head

# Verify table exists
alembic current
# Should show: 395af0dd3ac6 (add_indexing_progress_table)
```

**Table Schema:**
```sql
CREATE TABLE indexing_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
    total_emails INTEGER DEFAULT 0,
    processed_count INTEGER DEFAULT 0,
    status VARCHAR(50) NOT NULL,  -- in_progress, completed, failed, paused
    last_processed_message_id VARCHAR(255),  -- Checkpoint for resumption
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

### Usage

#### 1. Trigger Initial Indexing (Background Task)

```python
from app.tasks.indexing_tasks import index_user_emails

# Start 90-day indexing job for user
result = index_user_emails.delay(user_id=123, days_back=90)

# Check task status
if result.ready():
    print(result.result)
    # Output: {'success': True, 'total_emails': 437, 'processed': 437, 'status': 'completed'}
```

#### 2. Resume Interrupted Indexing

```python
from app.tasks.indexing_tasks import resume_user_indexing

# Resume from checkpoint
result = resume_user_indexing.delay(user_id=123)

# Check result
if result.ready():
    print(result.result)
    # Output: {'success': True, 'total_emails': 437, 'processed': 437}
```

#### 3. Incremental Indexing (New Emails)

```python
from app.tasks.indexing_tasks import index_new_email_background

# Triggered automatically by email polling service
# Can also be called manually:
result = index_new_email_background.delay(user_id=123, message_id="msg_abc123")
```

#### 4. Direct Service Usage (Advanced)

```python
from app.services.email_indexing import EmailIndexingService

# Initialize service
service = EmailIndexingService(user_id=123)

# Start indexing (async)
progress = await service.start_indexing(days_back=90)
print(f"Indexed {progress.processed_count}/{progress.total_emails} emails")

# Resume interrupted job
progress = await service.resume_indexing()

# Index single email
success = await service.index_new_email(message_id="msg_abc123")
```

### Workflow

**Initial Indexing Workflow:**
```
User Trigger → Celery Task → EmailIndexingService
    │
    ├─> 1. Check for existing job (prevent duplicates)
    ├─> 2. Create IndexingProgress record
    ├─> 3. Retrieve Gmail emails (90-day lookback, paginated)
    ├─> 4. Process in batches (50 emails/batch)
    │       │
    │       ├─> Extract metadata (thread, sender, language, flags)
    │       ├─> Generate embeddings (EmbeddingService)
    │       ├─> Store in ChromaDB (VectorDBClient)
    │       ├─> Update checkpoint (last_processed_message_id)
    │       └─> Rate limit delay (60 seconds)
    │
    ├─> 5. Mark as completed
    └─> 6. Send Telegram notification
```

**Checkpoint & Resumption:**
- Checkpoint saved every batch (50 emails)
- Stores `last_processed_message_id` for recovery
- Automatic resume on service restart (if job interrupted)
- Manual resume via `resume_user_indexing` task

### Performance

- **Gmail API**: 100 emails/page, date filtering for 90-day window
- **Batch Processing**: 50 emails per batch
- **Rate Limiting**: 60-second delay between batches (50 requests/min to Gemini API)
- **Total Time**: ~10 minutes for 5,000 emails (100 batches × 60s + API latency)
- **Checkpoint Overhead**: ~50ms per batch (PostgreSQL update)

**Example Timeline:**
```
User with 1,000 emails (last 90 days):
- 20 batches × 60 seconds = 20 minutes total
- Checkpoint saved every 50 emails
- Can resume from any checkpoint if interrupted
```

### Metadata Extraction

Each indexed email includes rich metadata for RAG context:

```python
{
    "email_id": "msg_abc123",
    "user_id": 123,
    "thread_id": "thread_xyz789",
    "sender": "sender@example.com",
    "subject": "Email subject",
    "received_at": "2025-11-03T10:15:30Z",
    "language": "de",           # Detected via langdetect
    "has_attachments": false,
    "is_reply": true,            # Detected via "Re:" prefix
    "word_count": 250
}
```

### Error Handling

**Transient Errors (retried 3 times):**
- `GmailAPIError`: Rate limits (429), network timeouts
- `GeminiAPIError`: Rate limits, embedding generation failures
- Exponential backoff: 60s → 120s → 240s

**Permanent Errors (not retried):**
- `ValueError`: Indexing job already exists for user
- Invalid user credentials
- Database constraint violations

**Error Recovery:**
- All errors logged with `structlog`
- Failed jobs marked with `status=failed` and `error_message`
- User notified via Telegram on failure

### Test Endpoints

Check indexing status and trigger jobs manually:

```bash
# Check indexing progress for user
GET /api/v1/indexing/progress/{user_id}

# Start indexing job
POST /api/v1/indexing/start
{
  "user_id": 123,
  "days_back": 90
}

# Resume interrupted job
POST /api/v1/indexing/resume
{
  "user_id": 123
}
```

### Monitoring

**Celery Task Monitoring:**
```bash
# Check Celery worker logs
celery -A app.celery worker --loglevel=info

# Monitor task execution
# Look for: "indexing_task_started", "indexing_task_completed"
```

**Database Monitoring:**
```sql
-- Check indexing progress for all users
SELECT user_id, total_emails, processed_count, status, completed_at
FROM indexing_progress
ORDER BY created_at DESC;

-- Check for failed jobs
SELECT user_id, error_message, updated_at
FROM indexing_progress
WHERE status = 'failed'
ORDER BY updated_at DESC;
```

### Troubleshooting

**Issue: langdetect module not found**
```bash
# Solution: Install langdetect
uv pip install langdetect

# Verify installation
python -c "import langdetect; print('OK')"
```

**Issue: VectorDBClient initialization error**
```bash
# Solution: Set ChromaDB path in .env
echo "CHROMADB_PATH=./backend/data/chromadb" >> .env

# Restart FastAPI server
```

**Issue: Indexing task fails with GmailAPIError**
```bash
# Check Gmail API quota
# Solution: Wait 60 seconds, task will auto-retry
# Or check Gmail OAuth token validity
```

**Issue: Checkpoint not saving**
```bash
# Check database connection
curl http://localhost:8000/api/v1/health/db

# Verify indexing_progress table exists
psql -h localhost -U mailagent -d mailagent -c "\d indexing_progress"
```

### Detailed Documentation

For comprehensive indexing service documentation, see:
- **Technical Spec**: `docs/tech-spec-epic-3.md`
- **Story**: `docs/stories/3-3-email-history-indexing.md`
- **EmailIndexingService API**: `backend/app/services/email_indexing.py`
- **Celery Tasks**: `backend/app/tasks/indexing_tasks.py`
- **Database Model**: `backend/app/models/indexing_progress.py`
- **Unit Tests**: `backend/tests/test_email_indexing.py`, `backend/tests/test_indexing_tasks.py`
- **Architecture**: `docs/architecture.md` (Email History Indexing Service section)

---

## Language Detection Service (Epic 3 - Story 3.5)

The Language Detection Service automatically identifies the language of incoming emails to enable AI response generation in the correct language. Supports 4 target languages with confidence scoring and fallback logic for ambiguous cases.

### Overview

**Key Features:**
- **4 Language Support**: Russian (ru), Ukrainian (uk), English (en), German (de)
- **Confidence Scoring**: Returns probability (0.0-1.0) for detection reliability
- **Confidence Threshold**: 0.7 minimum threshold with fallback to English
- **Mixed-Language Handling**: Selects primary language (highest probability)
- **Fast Detection**: <100ms per email (50-100ms typical)
- **HTML Email Support**: Strips HTML tags before detection
- **Database Integration**: Stores detected language in EmailProcessingQueue

### Installation

The langdetect library is automatically installed with project dependencies:

```bash
# Included in pyproject.toml
langdetect>=1.0.9  # Language detection (55 languages, 5MB footprint)
```

To manually install or verify:
```bash
uv pip install langdetect
python -c "import langdetect; print('langdetect installed')"
```

### Usage

#### Basic Language Detection

```python
from app.services.language_detection import LanguageDetectionService

# Initialize service
detector = LanguageDetectionService()

# Detect language with confidence
email_body = "Hallo! Dies ist eine wichtige E-Mail."
lang_code, confidence = detector.detect(email_body)
print(f"Detected: {lang_code} (confidence: {confidence:.2f})")
# Output: Detected: de (confidence: 0.95)
```

#### Detection with Fallback

```python
# Use detect_with_fallback for low-confidence handling
ambiguous_text = "OK thx"
lang, conf = detector.detect_with_fallback(ambiguous_text)
# Returns ("en", 0.45) - fallback to English if confidence < 0.7
```

#### Mixed-Language Emails

```python
# Detect primary language from mixed-language content
mixed_email = """
    Hallo! Dies ist wichtig für unser Projekt.
    Please review and confirm receipt.
"""
primary_lang = detector.detect_primary_language(mixed_email)
print(f"Primary language: {primary_lang}")
# Output: Primary language: de (German has highest probability)
```

#### Validate Supported Languages

```python
# Check if language is supported
is_supported = detector.is_supported_language("de")  # True
is_supported = detector.is_supported_language("fr")  # False
```

#### Database Integration

```python
from app.models.email import EmailProcessingQueue
from datetime import datetime, UTC

# Detect language and store in EmailProcessingQueue
lang_code, confidence = detector.detect(email_body)

email = EmailProcessingQueue(
    user_id=user.id,
    gmail_message_id="msg_123",
    gmail_thread_id="thread_123",
    sender="sender@example.com",
    subject="Important email",
    received_at=datetime.now(UTC),
    status="pending",
    detected_language=lang_code,  # Store 2-letter code
)
session.add(email)
await session.commit()
```

### Configuration

**Supported Languages**: `["ru", "uk", "en", "de"]`
**Confidence Threshold**: `0.7`
**Fallback Language**: `"en"` (English)

These constants are defined in the `LanguageDetectionService` class and can be accessed:

```python
print(detector.SUPPORTED_LANGUAGES)  # ['ru', 'uk', 'en', 'de']
print(detector.CONFIDENCE_THRESHOLD)  # 0.7
```

### Architecture Decision (ADR-013)

**Decision**: Use langdetect library for language detection

**Rationale**:
- Simple: pip install langdetect (5MB footprint)
- Fast: 50-100ms per email (meets <100ms NFR requirement)
- Good accuracy for email bodies (>100 chars)
- Zero cost: No API calls required
- Proven reliability: Widely used, battle-tested

**Trade-offs**:
- Lower accuracy for very short texts (<50 chars) - mitigated by fallback logic
- Ukrainian/Russian confusion possible - mitigated by confidence threshold
- No active language model training - acceptable for 4-language use case

**See**: `docs/architecture.md` (Language Detection section), `docs/tech-spec-epic-3.md` (ADR-013)

### Performance

**Typical Latency**:
- Clear language text (>100 chars): 50-100ms
- Short text (<50 chars): 100-150ms
- HTML emails: +10-20ms (HTML stripping overhead)

**Confidence Scores**:
- High confidence (>0.9): Clear single-language text
- Medium confidence (0.7-0.9): Acceptable, language detected correctly
- Low confidence (<0.7): Triggers fallback to English

### Error Handling

**Edge Cases Handled**:
- Empty email body: Raises `ValueError`
- Very short text (<20 chars): Logs warning, attempts detection
- HTML content: Automatically strips tags before detection
- Ambiguous text: Catches `LangDetectException`, logs error
- Mixed languages: Returns primary language (highest probability)

```python
# Example error handling
try:
    lang, conf = detector.detect(email_body)
except ValueError as e:
    # Empty body
    lang = "en"  # Default
except LangDetectException as e:
    # Detection failed
    lang, conf = detector.detect_with_fallback(email_body, fallback_lang="en")
```

### Database Schema

The `detected_language` field is stored in the `email_processing_queue` table:

```sql
-- detected_language column (Story 3.5)
ALTER TABLE email_processing_queue
ADD COLUMN detected_language VARCHAR(5);  -- Stores 2-letter codes: ru, uk, en, de
```

**Migration**: `backend/alembic/versions/c6c872982e1e_add_detected_language_field.py`

### Testing

**Unit Tests**: `backend/tests/test_language_detection.py` (9 tests)
**Integration Tests**: `backend/tests/integration/test_language_detection_integration.py` (4 tests)

---

## Response Generation Prompts (Epic 3 - Story 3.6)

The Response Generation Prompt system creates structured, context-aware prompts for AI email response generation with multilingual support, tone detection, and RAG context integration.

### Overview

**Key Features:**
- **Multilingual Support**: Russian (ru), Ukrainian (uk), English (en), German (de)
- **Hybrid Tone Detection**: Rule-based (80% cases) + LLM-based (20% ambiguous cases)
- **3 Tone Levels**: Formal (government), Professional (business), Casual (personal)
- **RAG Context Integration**: Thread history + semantic search results
- **Prompt Versioning**: Database-backed A/B testing and refinement
- **Greeting/Closing Database**: 12 combinations (4 languages × 3 tones)

### Installation

All dependencies are already installed from previous Epic 3 stories:

```bash
# Already included in pyproject.toml
google-generativeai>=0.8.3  # Gemini API for LLM-based tone detection
langdetect>=1.0.9           # Language detection integration
sqlmodel>=0.0.24            # Prompt version database storage
```

### Usage

#### Basic Prompt Generation

```python
from app.prompts.response_generation import format_response_prompt
from app.services.tone_detection import ToneDetectionService
from app.services.language_detection import LanguageDetectionService

# Initialize services
tone_service = ToneDetectionService()
lang_service = LanguageDetectionService()

# Detect tone and language
tone = tone_service.detect_tone(email, thread_history=[])
language, confidence = lang_service.detect(email.body)

# Generate complete prompt with RAG context
prompt = format_response_prompt(
    email=email,
    rag_context=rag_context,  # {thread_history: [...], semantic_results: [...]}
    language=language,
    tone=tone
)

# Send to Gemini API for response generation
response = gemini_model.generate_content(prompt)
```

#### Tone Detection Examples

```python
from app.services.tone_detection import ToneDetectionService

service = ToneDetectionService()

# Government email → "formal"
gov_email.sender = "info@finanzamt.de"
tone = service.detect_tone(gov_email)  # "formal"

# Business email → "professional"
biz_email.sender = "contact@startup.io"
tone = service.detect_tone(biz_email)  # "professional"

# Personal email → "casual"
personal_email.sender = "friend@gmail.com"
tone = service.detect_tone(personal_email)  # "casual"
```

#### Greeting/Closing Selection

```python
from app.prompts.response_generation import GREETING_EXAMPLES, CLOSING_EXAMPLES

# Get appropriate greeting for language+tone
greeting = GREETING_EXAMPLES["de"]["formal"]  # "Sehr geehrte Damen und Herren"
closing = CLOSING_EXAMPLES["de"]["formal"]    # "Mit freundlichen Grüßen"

# Professional English
greeting = GREETING_EXAMPLES["en"]["professional"]  # "Hello {name}"
closing = CLOSING_EXAMPLES["en"]["professional"]    # "Best regards"

# Casual Russian
greeting = GREETING_EXAMPLES["ru"]["casual"]  # "Привет, {name}"
closing = CLOSING_EXAMPLES["ru"]["casual"]    # "Всего хорошего"
```

#### Prompt Version Management

```python
from app.config.prompts_config import save_prompt_version, load_prompt_version

# Save new prompt version
version = save_prompt_version(
    template_name="response_generation",
    template_content=RESPONSE_PROMPT_TEMPLATE,
    version="1.0.0",
    parameters={"token_budget": 6500, "max_paragraphs": 3}
)

# Load latest active version
current_prompt = load_prompt_version("response_generation")

# Load specific version
v1_prompt = load_prompt_version("response_generation", version="1.0.0")
```

### Tone Detection Strategy (ADR-014)

**Hybrid Approach** - Rule-based + LLM:

1. **Rule-Based Detection (80% cases, fast)**:
   - Government domains (finanzamt.de, auslaenderbehoerde.de) → "formal"
   - Business domains (non-free providers, non-government) → "professional"
   - Free email providers (gmail.com, yahoo.com) → "casual"

2. **LLM-Based Detection (20% ambiguous cases)**:
   - Unknown/ambiguous senders → Gemini analyzes thread tone
   - Fallback to "professional" if LLM unavailable

**Rationale**: Optimal balance of speed (rules), accuracy (known cases), and flexibility (LLM for edge cases)

### Prompt Template Structure

```
ORIGINAL EMAIL:
From: {sender}
Subject: {subject}
Language: {language_name}
Body: {email_body}

CONVERSATION CONTEXT:
Thread History (Chronological):
{thread_history}

Relevant Context from Previous Emails (Semantic Search):
{semantic_results}

RESPONSE REQUIREMENTS:
1. Language: Write the response in {language_name} ({language_code})
2. Tone: {tone_description}
3. Length: 2-3 paragraphs maximum
4. Formality: {formality_instructions}

GREETING AND CLOSING EXAMPLES:
Appropriate Greeting: "{greeting_example}"
Appropriate Closing: "{closing_example}"

INSTRUCTIONS:
[Generate complete email response following requirements...]
```

**Token Budget**: ~6.5K tokens for context (leaves 25K for response generation in Gemini 32K window)

### Database Schema

The `prompt_versions` table stores versioned prompt templates:

```sql
CREATE TABLE prompt_versions (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR NOT NULL,
    template_content TEXT NOT NULL,
    version VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    parameters JSON,
    is_active BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX ix_prompt_versions_template_name ON prompt_versions(template_name);
```

**Migration**: `backend/alembic/versions/f21dea91e261_add_prompt_versions_table.py`

### Testing

**Unit Tests**: `backend/tests/test_response_generation_prompts.py` (8 tests)
- Tone detection (government, business, personal)
- Prompt template formatting with all placeholders
- Greeting/closing selection for all language+tone combinations
- Length constraints and formality instructions
- Multilingual support (de, en, ru, uk)
- Prompt version storage and retrieval

**Integration Tests**: `backend/tests/integration/test_prompt_generation_integration.py` (5 tests)
- Formal German government email prompts
- Professional English business email prompts
- Casual Russian personal email prompts
- Multilingual prompt quality across all 4 languages
- Real Gemini API tone detection for ambiguous cases

### Performance

- **Tone Detection**: <50ms (rule-based), ~500ms (LLM-based for ambiguous)
- **Prompt Generation**: <10ms (template formatting)
- **Total Latency**: <60ms typical, <550ms worst case

### Error Handling

```python
# Handle invalid language or tone
try:
    prompt = format_response_prompt(email, rag_context, "fr", "formal")
except ValueError as e:
    # Unsupported language: "fr"
    pass

# Fallback for LLM tone detection failure
tone = tone_service.detect_tone(email)  # Returns "professional" if LLM fails
```

### Configuration

**Government Domains** (configurable in `app/services/tone_detection.py`):
```python
GOVERNMENT_DOMAINS = [
    "finanzamt.de",
    "auslaenderbehoerde.de",
    "bundesagentur-fuer-arbeit.de",
    "stadt.de",
    "gov.de",
    # Add more as needed
]
```

### API Documentation

- **ToneDetectionService**: `backend/app/services/tone_detection.py`
- **Prompt Template**: `backend/app/prompts/response_generation.py`
- **Prompt Versioning**: `backend/app/config/prompts_config.py`
- **Architecture Decision**: `docs/architecture.md#ADR-014`

Run tests:
```bash
# Unit tests
env DATABASE_URL="..." uv run pytest tests/test_language_detection.py -v

# Integration tests (requires database)
env DATABASE_URL="..." uv run pytest tests/integration/test_language_detection_integration.py -v
```

### Detailed Documentation

For comprehensive language detection documentation, see:
- **Technical Spec**: `docs/tech-spec-epic-3.md` (Language Detection Strategy, ADR-013)
- **Story**: `docs/stories/3-5-language-detection.md`
- **LanguageDetectionService API**: `backend/app/services/language_detection.py`
- **Database Model**: `backend/app/models/email.py` (EmailProcessingQueue.detected_language)
- **Unit Tests**: `backend/tests/test_language_detection.py`
- **Integration Tests**: `backend/tests/integration/test_language_detection_integration.py`
- **Architecture**: `docs/architecture.md` (Language Detection section)

---

## AI Response Generation Service (Epic 3 - Story 3.7)

The AI Response Generation Service orchestrates the complete email response generation workflow by integrating all Epic 3 services: Context Retrieval (3.4), Language Detection (3.5), Tone Detection (3.6), Prompt Engineering (3.6), and Gemini LLM (2.1). The service generates contextually appropriate, multilingual email responses with proper tone and formality levels.

### Overview

**Key Features:**
- **Response Need Classification**: Automatically determines if email requires response (skips newsletters, no-reply senders)
- **Service Orchestration**: Integrates 5 specialized services for complete RAG workflow
- **Multilingual Support**: Russian, Ukrainian, English, German with automatic language detection
- **Response Quality Validation**: Length, language, and structure checks before presenting to users
- **Database Persistence**: Saves drafts with status="awaiting_approval" for Telegram approval (Story 3.8)
- **Privacy-Preserving Logging**: Email content truncated, structured logging with email_id references

### Installation

All dependencies are already installed from previous Epic 3 stories:

```bash
# Already included in pyproject.toml
google-generativeai>=0.8.3  # Gemini API for response generation
sqlmodel>=0.0.24            # Database ORM
structlog>=25.2.0           # Structured logging
langdetect>=1.0.9           # Language detection (Story 3.5)
chromadb>=0.4.22            # Vector database (Story 3.1)
```

### Usage

#### Basic Response Generation

```python
from app.services.response_generation import ResponseGenerationService

# Initialize service for specific user
service = ResponseGenerationService(user_id=123)

# Process email for response (end-to-end workflow)
success = await service.process_email_for_response(email_id=456)

if success:
    print("Response generated and saved to database")
else:
    print("No response needed (newsletter/no-reply)")
```

#### Response Need Classification

```python
from app.models.email import EmailProcessingQueue

# Check if email requires response
email = session.get(EmailProcessingQueue, email_id)
should_respond = service.should_generate_response(email)

# Returns False for:
# - no-reply senders (noreply@example.com)
# - newsletters (newsletter@company.com)
# - automated notifications (notifications@system.com)

# Returns True for:
# - Personal emails with questions
# - Business inquiries
# - Emails in active conversation threads (>2 emails)
```

#### Manual Workflow Steps

```python
# Step 1: Generate response
response_draft = await service.generate_response(email_id=456)

if response_draft:
    # Step 2: Validate response quality
    is_valid = service.validate_response(response_draft, expected_language="de")

    if is_valid:
        # Step 3: Save to database
        service.save_response_draft(
            email_id=456,
            response_draft=response_draft,
            language="de",
            tone="formal"
        )
```

#### Custom Service Integration

```python
from app.services.context_retrieval import ContextRetrievalService
from app.services.language_detection import LanguageDetectionService
from app.services.tone_detection import ToneDetectionService
from app.core.llm_client import LLMClient

# Initialize with custom service instances (e.g., for testing)
custom_context = ContextRetrievalService(user_id=123)
custom_language = LanguageDetectionService()
custom_tone = ToneDetectionService()
custom_llm = LLMClient()

service = ResponseGenerationService(
    user_id=123,
    context_service=custom_context,
    language_service=custom_language,
    tone_service=custom_tone,
    llm_client=custom_llm
)
```

### Service Workflow

The complete response generation workflow executes these steps:

1. **Response Need Classification** (AC #2)
   - Check for no-reply/newsletter patterns
   - Detect question indicators in 4 languages
   - Analyze thread length for active conversations
   - Default: generate response for unclear cases

2. **RAG Context Retrieval** (AC #3) - Story 3.4
   - Retrieve Gmail thread history (last 5 emails)
   - Semantic search in ChromaDB (top k similar emails)
   - Adaptive k logic: short threads get more semantic results
   - Token budget management (~6.5K tokens)

3. **Language Detection** (AC #4) - Story 3.5
   - Detect email language using langdetect
   - Confidence threshold: 0.7
   - Fallback to thread history language if low confidence
   - Supports: ru, uk, en, de

4. **Tone Detection** (AC #5) - Story 3.6
   - Rule-based for known domains (government → formal, business → professional)
   - LLM-based for ambiguous cases
   - Returns: "formal", "professional", or "casual"

5. **Prompt Formatting** (AC #6) - Story 3.6
   - format_response_prompt() constructs structured prompt
   - Includes: email content, RAG context, language instructions, tone requirements
   - Greeting/closing examples (12 combinations: 4 languages × 3 tones)

6. **LLM Response Generation** (AC #7) - Story 2.1
   - Send prompt to Gemini 2.5 Flash API
   - Model: gemini-2.5-flash (fast, multilingual, free tier)
   - Token budget: ~6.5K context + ~25K response = 32K total

7. **Response Quality Validation** (AC #9)
   - Length: 50-2000 characters
   - Language: Matches expected using LanguageDetectionService
   - Structure: Contains greeting and/or closing
   - Empty check: Minimum 20 characters

8. **Database Persistence** (AC #8, #10)
   - Update EmailProcessingQueue:
     - draft_response = generated text
     - detected_language = language code
     - status = "awaiting_approval"
     - classification = "needs_response"
     - updated_at = NOW()

### Configuration

**Response Validation Thresholds** (configurable in `app/services/response_generation.py`):

```python
MIN_RESPONSE_LENGTH = 50     # Minimum characters
MAX_RESPONSE_LENGTH = 2000   # Maximum characters
MIN_VALID_LENGTH = 20        # Absolute minimum (not empty)
TARGET_GENERATION_TIME = 8.0 # Performance target (seconds)
```

**No-Reply Patterns** (configurable):

```python
NO_REPLY_PATTERNS = [
    r"no-?reply",
    r"noreply",
    r"do-?not-?reply",
    r"newsletter",
    r"notifications?",
    r"automated?",
    r"mailer-daemon"
]
```

**Question Indicators** (4 languages):

```python
QUESTION_INDICATORS = {
    "en": ["?", "what", "when", "where", "who", "why", "how", "can you", "could you"],
    "de": ["?", "was", "wann", "wo", "wer", "warum", "wie", "können sie"],
    "ru": ["?", "что", "когда", "где", "кто", "почему", "как", "можете ли"],
    "uk": ["?", "що", "коли", "де", "хто", "чому", "як", "чи можете"]
}
```

### Database Schema

The service updates the `email_processing_queue` table:

```python
# EmailProcessingQueue model fields
draft_response: Optional[str]      # Generated response text (AC #8)
detected_language: Optional[str]   # Language code: ru, uk, en, de
status: str                        # "awaiting_approval" after generation (AC #10)
classification: Optional[str]      # "needs_response" vs "sort_only" (AC #10)
updated_at: datetime               # Last update timestamp
```

### Testing

**Unit Tests**: `backend/tests/test_response_generation.py` (10 tests)

```bash
# Run unit tests
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
    uv run pytest tests/test_response_generation.py -v

# Test coverage:
# - Response need classification (personal, newsletter, no-reply)
# - RAG context retrieval integration
# - Language detection integration
# - Tone detection integration
# - Prompt formatting integration
# - Response quality validation (success, failures)
# - Database persistence and status updates
```

**Integration Tests**: `backend/tests/integration/test_response_generation_integration.py` (6 tests)

```bash
# Run integration tests (excludes slow tests)
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
    uv run pytest tests/integration/test_response_generation_integration.py -v -m "not slow"

# Test scenarios:
# 1. German formal government email (end-to-end)
# 2. English professional business email (end-to-end)
# 3. Newsletter correctly skips response generation
# 4. Response quality validation rejects invalid responses
# 5. Short thread triggers adaptive k=7 semantic search
# 6. Real Gemini API integration (optional, marked @pytest.mark.slow)
```

### Performance

**Latency Breakdown** (NFR001: <2 minutes total, response generation component):

- RAG Context Retrieval: ~3s (Story 3.4)
- Language Detection: ~0.1s (Story 3.5)
- Tone Detection: ~0.2s (Story 3.6)
- Prompt Formatting: ~0.01s (Story 3.6)
- Gemini API Call: ~5s (model: gemini-2.5-flash)
- Response Validation: ~0.5s
- Database Persistence: ~0.1s
- **Total**: ~8.8s (well within 2-minute target)

### Error Handling

```python
# Handle email not found
try:
    response = await service.generate_response(999999)
except ValueError as e:
    print(f"Email not found: {e}")

# Handle validation failure
try:
    success = await service.process_email_for_response(email_id)
except ValueError as e:
    print(f"Validation failed: {e}")

# Handle service failures
try:
    response = await service.generate_response(email_id)
except Exception as e:
    # Service errors logged with structured logging
    # Check logs for: email_id, error_type, error_message
    print(f"Generation failed: {e}")
```

### Security

**Privacy-Preserving Logging:**
- Email sender truncated to 50 characters
- Email subject used for classification (body not logged)
- Structured logging with email_id references (no PII)

**Input Validation:**
- email_id existence checks before operations
- Response length validation (50-2000 chars)
- Language validation against supported languages

**Credential Management:**
- Gemini API key from environment: GEMINI_API_KEY
- Database credentials from environment: DATABASE_URL
- No hardcoded secrets in code

### API Documentation

**Service Class**: `backend/app/services/response_generation.py`

Main Methods:
- `should_generate_response(email) -> bool` - Classification logic
- `generate_response(email_id) -> Optional[str]` - Core generation
- `validate_response(draft, language) -> bool` - Quality checks
- `save_response_draft(email_id, draft, language, tone)` - Persistence
- `process_email_for_response(email_id) -> bool` - End-to-end workflow

**Dependencies**:
- Story 3.4: `backend/app/services/context_retrieval.py` (ContextRetrievalService)
- Story 3.5: `backend/app/services/language_detection.py` (LanguageDetectionService)
- Story 3.6: `backend/app/services/tone_detection.py` (ToneDetectionService)
- Story 3.6: `backend/app/prompts/response_generation.py` (format_response_prompt)
- Story 2.1: `backend/app/core/llm_client.py` (LLMClient)

### Detailed Documentation

For comprehensive AI Response Generation documentation, see:
- **Technical Spec**: `docs/tech-spec-epic-3.md` (Response Generation Service, Algorithm)
- **Story**: `docs/stories/3-7-ai-response-generation-service.md`
- **Architecture**: `docs/architecture.md` (Response Generation section - to be added)
- **Code Review**: Story file includes complete systematic review with evidence
- **Unit Tests**: `backend/tests/test_response_generation.py` (10 tests, all passing)
- **Integration Tests**: `backend/tests/integration/test_response_generation_integration.py` (6 tests)

---

## Response Draft Telegram Messages (Epic 3 - Story 3.8)

The Response Draft Telegram Messages service delivers AI-generated email response drafts to users via Telegram with an interactive approval interface. The service formats drafts into structured messages with inline keyboards ([Send], [Edit], [Reject]) and persists workflow mappings for callback reconnection.

### Overview

**Key Features:**
- **Message Formatting**: Structured Telegram messages with original email preview, AI draft, and visual separators
- **Inline Keyboard**: Three-button approval interface (Send, Edit, Reject) with callback data
- **Priority Flagging**: ⚠️ icon for urgent emails requiring immediate attention
- **Language Indication**: Clear display of response language (English, German, Russian, Ukrainian)
- **Workflow Mapping**: Persists Telegram message IDs with LangGraph thread IDs for callback reconnection
- **Privacy-Preserving**: Email content truncated in logs, structured logging with email_id references
- **Error Handling**: Graceful handling of unlinked Telegram accounts and API failures

### Installation

All dependencies are already installed from previous Epic 2 and 3 stories:

```bash
# Already included in pyproject.toml
python-telegram-bot>=21.0  # Telegram Bot API (Epic 2)
sqlmodel>=0.0.24           # Database ORM
structlog>=25.2.0          # Structured logging
```

### Usage

#### Basic Response Draft Notification

```python
from app.services.telegram_response_draft import TelegramResponseDraftService
from app.core.telegram_bot import TelegramBotClient

# Initialize bot and service
telegram_bot = TelegramBotClient()
service = TelegramResponseDraftService(telegram_bot=telegram_bot)

# Send response draft notification (end-to-end workflow)
success = await service.send_draft_notification(
    email_id=456,
    workflow_thread_id="thread_xyz_123"
)

if success:
    print("Response draft sent to Telegram")
else:
    print("User hasn't linked Telegram account")
```

#### Message Formatting Only

```python
# Format message without sending (for testing/preview)
message_text = service.format_response_draft_message(email_id=456)

print(message_text)
# Output:
# ⚠️ 📧 Response Draft Ready
#
# 📨 Original Email:
# From: urgent@example.com
# Subject: URGENT: Action required
#
# ─────────────────
# ✍️ AI-Generated Response (English):
# Dear Sir/Madam,
#
# I will address this urgent matter immediately.
#
# Best regards
# ─────────────────
```

#### Inline Keyboard Building

```python
# Build keyboard for manual message construction
keyboard_buttons = service.build_response_draft_keyboard(email_id=456)

# Returns list of button rows:
# Row 1: [[✅ Send Button]]
# Row 2: [[✏️ Edit Button], [❌ Reject Button]]
```

#### Manual Workflow Steps

```python
# Step 1: Send Telegram message
telegram_message_id = await service.send_response_draft_to_telegram(email_id=456)

# Step 2: Save workflow mapping for callback reconnection
service.save_telegram_message_mapping(
    email_id=456,
    telegram_message_id=telegram_message_id,
    thread_id="workflow_thread_xyz_123"
)

# Step 3: Update email status (done automatically by send_draft_notification)
```

#### Custom Service Integration

```python
from app.services.database import DatabaseService

# Initialize with custom database service (e.g., for testing)
custom_db = DatabaseService()

service = TelegramResponseDraftService(
    telegram_bot=telegram_bot,
    db_service=custom_db
)
```

### Service Workflow

The complete response draft notification workflow executes these steps:

1. **Message Formatting** (AC #1-4, #6, #9)
   - Load email with draft_response from EmailProcessingQueue
   - Format header with priority flag (⚠️) if is_priority=True
   - Include original email: sender, subject (AC #2 partial: uses subject as preview)
   - Add visual separators for clarity (AC #4)
   - Display draft with language indication (AC #6)
   - Handle Telegram length limits (4096 chars max - currently truncates, AC #8 partial)

2. **Inline Keyboard Building** (AC #5)
   - Row 1: [✅ Send] button with callback_data="send_response_{email_id}"
   - Row 2: [✏️ Edit] button with callback_data="edit_response_{email_id}"
   - Row 2: [❌ Reject] button with callback_data="reject_response_{email_id}"

3. **Telegram Message Sending** (AC #1-9)
   - Load user's telegram_id from Users table
   - Send message via TelegramBotClient.send_message_with_buttons()
   - Return telegram_message_id for workflow mapping

4. **Workflow Mapping Persistence**
   - Create WorkflowMapping record with:
     - email_id (links to EmailProcessingQueue)
     - user_id (from email.user_id)
     - thread_id (LangGraph workflow instance ID)
     - telegram_message_id (for message editing)
     - workflow_state="awaiting_response_approval"

5. **Email Status Update**
   - Update EmailProcessingQueue.status = "awaiting_response_approval"
   - Timestamp updated_at field

### Configuration

**Message Formatting Constants** (configurable in `app/services/telegram_response_draft.py`):

```python
MAX_BODY_PREVIEW_CHARS = 100  # Original email preview length
TELEGRAM_MAX_LENGTH = 4096    # Telegram message length limit
VISUAL_SEPARATOR = "─────────────────"  # Visual separation

LANGUAGE_NAMES = {
    "en": "English",
    "de": "German",
    "ru": "Russian",
    "uk": "Ukrainian"
}
```

### Database Schema

The service uses these tables:

**EmailProcessingQueue** (reads from):
```python
draft_response: Optional[str]      # Generated response text (from Story 3.7)
detected_language: Optional[str]   # Language code: ru, uk, en, de
is_priority: bool                  # Priority flag for ⚠️ icon
status: str                        # Updated to "awaiting_response_approval"
```

**WorkflowMapping** (writes to):
```python
email_id: int                      # Links to EmailProcessingQueue
user_id: int                       # User who owns the email
thread_id: str                     # LangGraph workflow instance ID
telegram_message_id: str           # Telegram message ID for editing
workflow_state: str                # "awaiting_response_approval"
```

### Testing

**Unit Tests**: `backend/tests/test_telegram_response_draft.py` (9 tests)

```bash
# Run unit tests
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
    uv run pytest tests/test_telegram_response_draft.py -v

# Test coverage:
# - Message formatting (standard, priority, long drafts, no context)
# - Inline keyboard building (3-button layout)
# - Telegram message sending
# - Workflow mapping persistence
# - End-to-end orchestration
# - Error handling (user blocked, not linked)
```

**Integration Tests**: `backend/tests/integration/test_response_draft_telegram_integration.py` (6 tests)

```bash
# Run integration tests
env DATABASE_URL="postgresql+psycopg://mailagent:mailagent_dev_password_2024@localhost:5432/mailagent" \
    uv run pytest tests/integration/test_response_draft_telegram_integration.py -v

# Test scenarios:
# 1. German formal response with priority flag (end-to-end)
# 2. English professional response without priority (end-to-end)
# 3. Very long draft handling (>4096 chars truncation)
# 4. Context summary display (placeholder - AC #7 not implemented)
# 5. Priority email flagging with ⚠️ icon
# 6. Telegram user not linked error handling
```

### Performance

**Latency Breakdown** (NFR001: <2 minutes total, Telegram notification component):

- Load email from database: ~0.01s
- Format message: ~0.001s
- Build keyboard: ~0.001s
- Send Telegram API call: ~0.5-1s
- Save workflow mapping: ~0.01s
- Update email status: ~0.01s
- **Total**: ~1s (well within 2-minute target)

### Error Handling

```python
# Handle email not found
try:
    message = service.format_response_draft_message(999999)
except ValueError as e:
    print(f"Email not found: {e}")

# Handle user without Telegram account
try:
    success = await service.send_draft_notification(email_id, thread_id)
except ValueError as e:
    print(f"User not linked: {e}")

# Handle Telegram API errors
from app.utils.errors import TelegramUserBlockedError

try:
    message_id = await service.send_response_draft_to_telegram(email_id)
except TelegramUserBlockedError as e:
    print(f"User blocked bot: {e}")
    # Service logs this with structured logging
```

### Security

**Privacy-Preserving Logging:**
- Email content NOT logged in full (only email_id referenced)
- Sender/subject truncated in message formatting logs
- Structured logging: email_id, user_id, telegram_message_id

**Input Validation:**
- email_id existence checks before operations
- User telegram_id validation (ValueError if not set)
- SQLModel ORM for parameterized queries (no SQL injection)

**Credential Management:**
- Telegram bot token from environment: TELEGRAM_BOT_TOKEN
- Database credentials from environment: DATABASE_URL
- No hardcoded secrets in code

### API Documentation

**Service Class**: `backend/app/services/telegram_response_draft.py`

Main Methods:
- `format_response_draft_message(email_id) -> str` - Message formatting
- `build_response_draft_keyboard(email_id) -> List[List[InlineKeyboardButton]]` - Keyboard building
- `send_response_draft_to_telegram(email_id) -> str` - Send message, return telegram_message_id
- `save_telegram_message_mapping(email_id, telegram_message_id, thread_id)` - Persist mapping
- `send_draft_notification(email_id, workflow_thread_id) -> bool` - End-to-end workflow

**Dependencies**:
- Story 3.7: `backend/app/services/response_generation.py` (Response draft source)
- Story 2.6: `backend/app/core/telegram_bot.py` (TelegramBotClient)
- Story 2.6: `backend/app/models/workflow_mapping.py` (WorkflowMapping)
- Epic 2: `backend/app/models/user.py` (User.telegram_id)

### Known Limitations (v1)

**Partially Implemented Features:**
1. **AC #2 (Email Body Preview)**: Uses subject text instead of first 100 chars of email body (EmailProcessingQueue doesn't store body field)
2. **AC #7 (Context Summary)**: NOT implemented - "Based on N emails" context display not included
3. **AC #8 (Message Splitting)**: Truncates instead of splits - long drafts (>4096 chars) are cut off by TelegramBotClient

**Future Enhancements** (if needed in future stories):
- Add body field to EmailProcessingQueue for AC #2 completion
- Pass RAG context metadata for AC #7 display
- Implement paragraph-boundary splitting for AC #8 enhancement

### Detailed Documentation

For comprehensive Response Draft Telegram Messages documentation, see:
- **Technical Spec**: `docs/tech-spec-epic-3.md` (Response Draft Telegram Delivery)
- **Story**: `docs/stories/3-8-response-draft-telegram-messages.md`
- **Architecture**: `docs/architecture.md` (Telegram Response Draft section - to be added)
- **Code Review**: Story file includes complete systematic review with evidence
- **Unit Tests**: `backend/tests/test_telegram_response_draft.py` (9 tests, all passing)
- **Integration Tests**: `backend/tests/integration/test_response_draft_telegram_integration.py` (6 tests, all passing)

---

## Context Retrieval Service (Epic 3 - Story 3.4)

The Context Retrieval Service implements Smart Hybrid RAG for retrieving relevant conversation context to power AI response generation. It combines Gmail thread history with semantic search in ChromaDB, using adaptive k logic and token budget management.

### Installation

Dependencies automatically installed with project:

```bash
# Included in pyproject.toml
tiktoken>=0.5.0  # For accurate token counting
```

### Configuration

Uses existing environment variables from previous stories:

```bash
# Already configured in Epic 2-3
GEMINI_API_KEY="your-key-here"          # For embeddings
CHROMA_PERSIST_DIR="./data/chroma"      # For vector search
DATABASE_URL="postgresql://..."         # For email queue
```

### Usage

#### Basic Usage

```python
from app.services.context_retrieval import ContextRetrievalService

# Initialize service for user
service = ContextRetrievalService(user_id=123)

# Retrieve context for incoming email
context = await service.retrieve_context(email_id=456)

# Access context components
thread_history = context["thread_history"]     # Last 5 emails in thread
semantic_results = context["semantic_results"]  # Top 3-7 similar emails
metadata = context["metadata"]                 # Statistics

print(f"Thread length: {metadata['thread_length']}")
print(f"Semantic count: {metadata['semantic_count']}")
print(f"Total tokens: {metadata['total_tokens_used']}")
print(f"Adaptive k: {metadata['adaptive_k']}")
```

#### Advanced Usage with Dependency Injection

```python
# For testing or custom configurations
from app.core.gmail_client import GmailClient
from app.core.embedding_service import EmbeddingService
from app.core.vector_db import VectorDBClient

service = ContextRetrievalService(
    user_id=123,
    gmail_client=custom_gmail_client,
    embedding_service=custom_embedding_service,
    vector_db_client=custom_vector_db
)
```

### Smart Hybrid RAG Strategy

The service combines two complementary context sources:

1. **Thread History**: Last 5 emails from Gmail thread (conversation continuity)
2. **Semantic Search**: Top 3-7 similar emails from ChromaDB (broader context)

**Adaptive k Logic** dynamically adjusts semantic search based on thread length:

| Thread Length | Adaptive k | Strategy Reason |
|--------------|------------|-----------------|
| <3 emails (short) | k=7 | Need more semantic context |
| 3-5 emails (standard) | k=3 | Balanced hybrid approach |
| >5 emails (long) | k=0 | Skip semantic, thread sufficient |

### Token Budget Management

- **Budget**: ~6.5K tokens total (leaves 25K for Gemini response in 32K window)
- **Token Counter**: Uses tiktoken (GPT-4 tokenizer, accurate for Gemini)
- **Truncation Strategy**:
  1. Truncate thread_history first (keep most recent)
  2. If still over, truncate semantic_results (remove low-ranked)

### Performance

- **Target**: <3 seconds total retrieval time (NFR001)
- **Execution Strategy**: Sequential execution (thread history → adaptive k → semantic search)
  - **Rationale (ADR-015)**: Adaptive k calculation requires thread_length, preventing true parallelization
- **Actual latency**:
  - Gmail thread fetch: ~1000ms
  - Adaptive k calculation: <1ms
  - Semantic search (if k>0): ~500ms
  - Assembly: ~100ms
  - **Total**: ~1600ms (well under 3s target ✅)

Performance metrics logged automatically:
```python
{
  "latency_ms": 1850.23,
  "thread_count": 4,
  "semantic_count": 3,
  "total_tokens": 4200,
  "adaptive_k": 3
}
```

### Data Models

**RAGContext TypedDict:**
```python
{
    "thread_history": [EmailMessage, ...],   # Chronological order
    "semantic_results": [EmailMessage, ...],  # Ranked by relevance
    "metadata": {
        "thread_length": 4,
        "semantic_count": 3,
        "oldest_thread_date": "2025-11-01T10:00:00Z",
        "total_tokens_used": 4200,
        "adaptive_k": 3,
        "thread_tokens": 2800,
        "semantic_tokens": 1400
    }
}
```

**EmailMessage TypedDict:**
```python
{
    "message_id": "18b7c8d9e0f1a2b3",
    "sender": "sender@example.com",
    "subject": "Email subject",
    "body": "Full email body text...",
    "date": "2025-11-09T10:00:00Z",  # ISO 8601 format
    "thread_id": "thread123"
}
```

### Security & Multi-Tenancy

- **User Isolation**: ChromaDB queries filtered by `user_id`
- **Input Validation**: email_id and user_id validated
- **Error Handling**: No email content leaked in errors
- **No Hardcoded Credentials**: All keys from environment

### Integration Points

**Upstream Dependencies** (Stories 3.1-3.3):
- `VectorDBClient.query_embeddings()` - Semantic search
- `EmbeddingService.embed_text()` - Query embeddings
- `GmailClient.get_thread()` - Thread history

**Downstream Consumers** (Story 3.7):
- `ResponseGenerationService` will use RAGContext for AI responses

### Testing

Run unit tests (8 test functions):
```bash
pytest tests/test_context_retrieval.py -v
```

Run integration tests (5 test functions):
```bash
pytest tests/integration/test_context_retrieval_integration.py -v -m integration
```

### Documentation

- **Story**: `docs/stories/3-4-context-retrieval-service.md`
- **Service API**: `backend/app/services/context_retrieval.py`
- **Data Models**: `backend/app/models/context_models.py`
- **Unit Tests**: `backend/tests/test_context_retrieval.py`
- **Integration Tests**: `backend/tests/integration/test_context_retrieval_integration.py`
- **Architecture**: `docs/architecture.md` (Context Retrieval Service section)

---

## Troubleshooting

### Server won't start

- Ensure Python 3.13+ is installed: `python --version`
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -e .`
- Check for port conflicts: `lsof -i :8000`

### Database connection errors

- Ensure PostgreSQL container is running: `docker-compose up -d db`
- Check DATABASE_URL in `.env` matches your database credentials
- Verify database is accessible: `psql -h localhost -U mailagent -d mailagent`
- Check health endpoint: `curl http://localhost:8000/api/v1/health/db`
- Review Alembic migration status: `alembic current`

### Import errors

- Ensure you're in the virtual environment
- Reinstall dependencies: `pip install -e .`
- Check Python version: `python --version` (should be 3.13+)

---

## Contributing

This project follows the BMM (BMAD Methodology for Modern software) workflow:

1. Stories are defined in `/docs/stories/`
2. Each story has acceptance criteria and tasks
3. Implementation follows the story requirements
4. Code review happens via `code-review` workflow
5. Stories are marked done via `story-done` workflow

---

## License

[To be determined]

---

## Contact

For questions or issues, please refer to the project documentation in `/docs/`.
