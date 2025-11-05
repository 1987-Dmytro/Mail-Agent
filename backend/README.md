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

### Telegram Settings (Epic 2)
- `TELEGRAM_BOT_TOKEN`: Telegram bot token

### LLM Settings (Epic 2)
- `LLM_API_KEY`: Gemini API key
- `LLM_MODEL`: Model name (gemini-pro)

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
