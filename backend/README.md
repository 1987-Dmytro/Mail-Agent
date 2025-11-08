# Mail Agent Backend Service

**FastAPI + LangGraph Foundation for AI-Powered Email Management**

## Overview

This is the backend service for Mail Agent, an AI-powered email management system that uses Gmail API, Gemini LLM for intelligent email classification, and Telegram for user approvals.

**Status:** Story 1.2 - Backend Service Foundation (Complete)

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
