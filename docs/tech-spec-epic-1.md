# Epic Technical Specification: Foundation & Gmail Integration

Date: 2025-11-03
Author: Dimcheg
Epic ID: 1
Status: Draft

---

## Overview

Epic 1 establishes the technical foundation for Mail Agent by implementing the core Gmail integration infrastructure. This epic delivers a functional system capable of authenticating users via OAuth 2.0, monitoring Gmail inboxes for incoming emails, managing Gmail labels programmatically, and sending email responses on behalf of users. The implementation leverages the FastAPI + LangGraph production template as the architectural foundation, extended with Google Gmail API client integration, PostgreSQL database for user and email data persistence, and Celery background task processing for email polling. By completing this epic, the system validates the core Gmail connectivity required for all subsequent AI-powered features while establishing production-grade patterns for authentication, data management, and background job orchestration.

## Objectives and Scope

**In Scope:**
- Gmail OAuth 2.0 authentication flow (authorization code grant) with token storage and refresh
- PostgreSQL database schema for users, email processing queue, folder categories
- Gmail API client wrapper with methods for: reading emails, listing labels, creating labels, applying labels, sending emails
- Background email polling service using Celery (2-minute intervals, configurable)
- Email metadata extraction and storage (sender, subject, thread_id, message_id, received_at)
- Gmail label management (create, list, apply to messages, remove from messages)
- Integration testing framework for Gmail operations
- Development environment setup (Docker Compose with PostgreSQL, Redis, backend service)
- API documentation using FastAPI automatic OpenAPI/Swagger generation

**Out of Scope:**
- AI classification or response generation (Epic 2 & 3)
- Telegram bot integration (Epic 2)
- RAG vector database setup (Epic 3)
- Frontend configuration UI (Epic 4)
- Advanced email parsing (HTML, attachments) beyond basic text extraction
- Gmail push notifications (Pub/Sub webhooks) - deferred to post-MVP per ADR-004

## System Architecture Alignment

This epic implements the foundational layer of the Mail Agent architecture as defined in `architecture.md`. Key alignment points:

**FastAPI + LangGraph Template Foundation:**
- Leverages `wassim249/fastapi-langgraph-agent-production-ready-template` as base (ADR-006)
- Inherits FastAPI async endpoints, JWT authentication scaffolding, structured logging, Prometheus metrics, PostgreSQL + Alembic migrations
- Extends with Gmail-specific API clients and models

**Database Layer (PostgreSQL):**
- Implements `users` table for OAuth token storage (encrypted at rest)
- Implements `email_processing_queue` table for email metadata tracking
- Implements `folder_categories` table for Gmail label mapping
- Uses Alembic migrations for schema versioning

**Gmail API Integration:**
- Polling strategy (2-minute intervals) per ADR-004
- Retry logic with exponential backoff for transient failures
- Rate limit management (10,000 requests/day Gmail free tier)
- OAuth 2.0 scopes: `gmail.readonly`, `gmail.modify`, `gmail.send`, `gmail.labels`

**Background Task Processing (Celery + Redis):**
- Email polling task runs every 2 minutes per user
- Task priorities: normal (email polling), high (future priority emails in Epic 2)
- Redis as message broker

**Components Created:**
- `app/core/gmail_client.py` - Gmail API wrapper
- `app/api/auth.py` - OAuth endpoints
- `app/models/user.py`, `app/models/email_queue.py`, `app/models/folder_category.py` - Database models
- `app/tasks/email_tasks.py` - Celery background tasks
- `app/services/email_polling.py` - Email polling business logic

**NFR Alignment:**
- NFR001 (Performance): Email polling → database storage < 1 second per email
- NFR002 (Reliability): Gmail API retry logic ensures 99.9% operation success
- NFR004 (Security): OAuth tokens encrypted using Fernet symmetric encryption, TLS for all API calls
- NFR005 (Usability): OAuth flow designed for non-technical users (clear permission explanations in Epic 4 UI)

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner/Location |
|---------------|----------------|--------|---------|----------------|
| **GmailClient** | Gmail API wrapper for all email operations | OAuth tokens, email IDs, label data | Email objects, label objects, operation results | `app/core/gmail_client.py` |
| **OAuth Flow** | Handle Gmail authorization code flow | Authorization code from redirect | Access token, refresh token | `app/api/auth.py` |
| **EmailPollingService** | Periodically fetch new emails from Gmail | User ID, polling interval | List of new email metadata | `app/services/email_polling.py` |
| **EmailPollingTask** | Celery background task orchestrating polling | Celery schedule trigger | Database records created | `app/tasks/email_tasks.py` |
| **TokenRefreshService** | Auto-refresh expired OAuth tokens | Expired access token | New access token | `app/core/gmail_client.py` |
| **LabelManagementService** | Create and manage Gmail labels | Label name, color, user ID | Gmail label ID | `app/services/label_management.py` |

### Data Models and Contracts

**Users Table (PostgreSQL):**
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    gmail_oauth_token = Column(Text, nullable=True)  # Encrypted (Fernet)
    gmail_refresh_token = Column(Text, nullable=True)  # Encrypted (Fernet)
    telegram_id = Column(String(100), unique=True, nullable=True)  # Epic 2
    telegram_username = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
```

**EmailProcessingQueue Table:**
```python
class EmailProcessingQueue(Base):
    __tablename__ = "email_processing_queue"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    gmail_message_id = Column(String(255), unique=True, nullable=False, index=True)
    gmail_thread_id = Column(String(255), nullable=False, index=True)
    sender = Column(String(255), nullable=False)
    subject = Column(Text, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, processing, awaiting_approval, completed, rejected, error
    classification = Column(String(50), nullable=True)  # Epic 2: sort_only, needs_response
    proposed_folder_id = Column(Integer, ForeignKey("folder_categories.id"), nullable=True)
    draft_response = Column(Text, nullable=True)  # Epic 3
    language = Column(String(10), nullable=True)  # Epic 3: ru, uk, en, de
    priority_score = Column(Integer, default=0)  # Epic 2: 0-100
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="emails")
    proposed_folder = relationship("FolderCategory", foreign_keys=[proposed_folder_id])
```

**FolderCategories Table:**
```python
class FolderCategory(Base):
    __tablename__ = "folder_categories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    gmail_label_id = Column(String(100), nullable=True)  # Gmail's internal label ID
    keywords = Column(ARRAY(String), default=[])  # Epic 2: for classification hints
    color = Column(String(7), nullable=True)  # Hex color (#FF5733)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_folder_name'),
    )
```

**Encryption Schema (for OAuth tokens):**
```python
from cryptography.fernet import Fernet

# Encryption key stored in environment variable ENCRYPTION_KEY
# Generated via: Fernet.generate_key()

def encrypt_token(plaintext: str) -> str:
    """Encrypt OAuth token using Fernet symmetric encryption"""
    cipher = Fernet(ENCRYPTION_KEY)
    return cipher.encrypt(plaintext.encode()).decode()

def decrypt_token(ciphertext: str) -> str:
    """Decrypt OAuth token"""
    cipher = Fernet(ENCRYPTION_KEY)
    return cipher.decrypt(ciphertext.encode()).decode()
```

### APIs and Interfaces

**OAuth Authentication Endpoints:**

**POST /api/v1/auth/gmail/login**
- Purpose: Generate Gmail OAuth authorization URL
- Authentication: None (public endpoint)
- Request: `{}`
- Response:
```json
{
  "success": true,
  "data": {
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&scope=gmail.readonly+gmail.modify+gmail.send+gmail.labels&redirect_uri=..."
  }
}
```

**GET /api/v1/auth/gmail/callback**
- Purpose: Handle OAuth redirect and exchange code for tokens
- Authentication: None (OAuth callback)
- Query Parameters: `code` (authorization code), `state` (CSRF token)
- Response:
```json
{
  "success": true,
  "data": {
    "user_id": "123",
    "email": "user@gmail.com",
    "token_expires_at": "2025-11-04T10:15:30Z"
  }
}
```
- Side effects: Creates/updates User record, stores encrypted tokens, sets JWT session cookie

**GET /api/v1/auth/gmail/status**
- Purpose: Check Gmail connection status
- Authentication: Required (JWT)
- Response:
```json
{
  "success": true,
  "data": {
    "connected": true,
    "email": "user@gmail.com",
    "token_valid": true,
    "last_sync": "2025-11-03T10:15:30Z"
  }
}
```

**GmailClient Python Interface:**

```python
class GmailClient:
    """Wrapper for Gmail API operations with automatic token refresh"""

    def __init__(self, user_id: int):
        """Initialize client with user's OAuth credentials"""
        self.user_id = user_id
        self.service = self._build_gmail_service()

    async def get_messages(self, query: str = "is:unread", max_results: int = 50) -> List[Dict]:
        """
        Fetch emails matching query from Gmail inbox

        Args:
            query: Gmail search query (default: unread emails)
            max_results: Maximum emails to fetch (max 500 per Gmail API)

        Returns:
            List of email metadata dicts with keys:
            - message_id: str
            - thread_id: str
            - sender: str
            - subject: str
            - snippet: str (first 200 chars)
            - received_at: datetime
            - labels: List[str]
        """
        pass

    async def get_message_detail(self, message_id: str) -> Dict:
        """
        Get full email content including body and headers

        Returns:
            - message_id: str
            - thread_id: str
            - sender: str
            - subject: str
            - body: str (plain text extracted from HTML if needed)
            - headers: Dict[str, str]
            - received_at: datetime
        """
        pass

    async def get_thread(self, thread_id: str) -> List[Dict]:
        """Get all emails in a thread (conversation history)"""
        pass

    async def list_labels(self) -> List[Dict]:
        """List all Gmail labels for user"""
        pass

    async def create_label(self, name: str, color: str = None) -> str:
        """
        Create new Gmail label

        Returns: gmail_label_id (e.g., "Label_123")
        """
        pass

    async def apply_label(self, message_id: str, label_id: str) -> bool:
        """Apply label to email message"""
        pass

    async def remove_label(self, message_id: str, label_id: str) -> bool:
        """Remove label from email message"""
        pass

    async def send_email(self, to: str, subject: str, body: str,
                        in_reply_to: str = None, references: str = None) -> str:
        """
        Send email via Gmail API

        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text or HTML body
            in_reply_to: Message-ID for threading (optional)
            references: References header for threading (optional)

        Returns: message_id of sent email
        """
        pass
```

### Workflows and Sequencing

**OAuth Authentication Flow:**

```
1. User clicks "Connect Gmail" (Epic 4 UI)
   ↓
2. Frontend calls POST /api/v1/auth/gmail/login
   ↓
3. Backend generates OAuth URL with:
   - client_id (from environment variable)
   - scopes: gmail.readonly, gmail.modify, gmail.send, gmail.labels
   - redirect_uri: {FRONTEND_URL}/auth/gmail/callback
   - state: CSRF token (stored in session)
   ↓
4. User redirected to Google consent screen
   ↓
5. User grants permissions
   ↓
6. Google redirects to callback URL with authorization code
   ↓
7. Backend GET /api/v1/auth/gmail/callback:
   - Validates state parameter (CSRF check)
   - Exchanges code for access_token + refresh_token via Google OAuth API
   - Creates/updates User record
   - Encrypts tokens using Fernet cipher
   - Stores encrypted tokens in database
   - Issues JWT session token
   ↓
8. User authenticated, Gmail connected ✅
```

**Email Polling Workflow:**

```
1. Celery Beat scheduler triggers every 2 minutes
   ↓
2. EmailPollingTask executes:
   - Queries all active users (is_active=True, gmail_oauth_token IS NOT NULL)
   ↓
3. For each user:
   - Initialize GmailClient(user_id)
   - Call client.get_messages(query="is:unread", max_results=50)
   ↓
4. Gmail API returns list of message metadata
   ↓
5. For each message:
   - Check if gmail_message_id already exists in EmailProcessingQueue
   - If exists: SKIP (duplicate detection)
   - If new: Insert record with status="pending"
   ↓
6. Log polling results:
   - Emails found: N
   - New emails: M
   - Duplicates skipped: N-M
   ↓
7. Workflow continues in Epic 2 (AI classification)
```

**Token Refresh Flow (Automatic):**

```
1. GmailClient detects expired access_token (401 Unauthorized)
   ↓
2. Load user's refresh_token from database (decrypt)
   ↓
3. Call Google OAuth token endpoint:
   POST https://oauth2.googleapis.com/token
   Body: {
     "client_id": ...,
     "client_secret": ...,
     "refresh_token": ...,
     "grant_type": "refresh_token"
   }
   ↓
4. Google returns new access_token
   ↓
5. Update user record with new access_token (encrypted)
   ↓
6. Retry original Gmail API call ✅
```

**Label Creation and Application:**

```
1. User creates folder category via Epic 4 UI
   ↓
2. Frontend POST /api/v1/folders/ → Backend
   ↓
3. Backend:
   - Validate folder name (1-100 chars, unique per user)
   - Initialize GmailClient(user_id)
   - Call client.create_label(name="Government", color="#FF5733")
   ↓
4. Gmail API creates label, returns label_id
   ↓
5. Backend creates FolderCategory record:
   - name="Government"
   - gmail_label_id="Label_123"
   - user_id=123
   ↓
6. When applying label (Epic 2):
   - Load FolderCategory by id
   - Call client.apply_label(message_id, gmail_label_id)
   - Gmail moves email to folder ✅
```

## Non-Functional Requirements

### Performance

**NFR001 - Email Processing Latency:**
- Target: Email received in Gmail → stored in database < 5 seconds (well under 2-minute total requirement)
- Measured metrics:
  - Gmail API fetch latency: <500ms per email
  - Database insert: <100ms per email
  - Polling cycle duration: <30 seconds for 50 emails
- Optimization strategies:
  - Batch Gmail API calls (fetch 50 emails in single request)
  - Async database operations (SQLAlchemy async session)
  - Connection pooling (10 connections max per service)

**Database Query Performance:**
- Email lookup by gmail_message_id: <10ms (unique index)
- User email queue query (user_id + status): <50ms (composite index)
- Token encryption/decryption: <5ms (Fernet cipher)

**Gmail API Rate Limits:**
- Free tier: 10,000 requests/day per user
- Polling strategy:
  - 720 polls/day (every 2 minutes) = 720 requests
  - Avg 5 emails/poll × 720 = 3,600 requests/day
  - Buffer: 6,400 requests remaining for labels, sending (safe margin)

### Security

**OAuth Token Storage:**
- Access tokens encrypted at rest using Fernet (AES-128-CBC + HMAC)
- Refresh tokens encrypted with same key
- Encryption key (32-byte) stored in environment variable ENCRYPTION_KEY
- Key rotation strategy: Manual rotation with re-encryption migration (post-MVP)
- Token access logged for audit trail

**Authentication & Authorization:**
- JWT tokens for API session management (HS256, 24-hour expiry)
- HTTP-only cookies to prevent XSS token theft
- CSRF protection via state parameter in OAuth flow
- All API endpoints require valid JWT except OAuth callback

**TLS/HTTPS:**
- All external API calls use TLS 1.3 (Gmail API, Google OAuth)
- Backend API enforces HTTPS in production (redirects HTTP → HTTPS)
- PostgreSQL connections use TLS (sslmode=require)

**Data Isolation:**
- All queries MUST filter by user_id (row-level security)
- Foreign key constraints prevent cross-user data access
- Database user has minimal privileges (no DROP, no DDL)

**Input Validation:**
- Email addresses validated via regex (RFC 5322 compliant)
- Gmail API responses sanitized (strip dangerous HTML in email bodies)
- SQL injection prevented via SQLAlchemy ORM parameterized queries

### Reliability/Availability

**Target Uptime:** 99.5% (NFR002 - allows ~3.6 hours downtime/month for MVP)

**Error Handling & Retry:**
- Gmail API transient errors (network timeouts, 503 service unavailable): Retry with exponential backoff (3 attempts, 2^n seconds delay)
- Gmail API auth errors (401, 403): Trigger token refresh, then retry once
- Gmail quota exceeded (429): Log warning, pause polling for 1 hour, resume
- Database connection errors: Retry 3 times, then fail task (Celery will retry task itself)

**Data Consistency:**
- Email duplicate detection via unique constraint on gmail_message_id
- Idempotent email insertion (INSERT ... ON CONFLICT DO NOTHING)
- Atomic database transactions for multi-step operations

**Failure Recovery:**
- Celery tasks auto-retry on failure (max 3 retries, exponential backoff)
- Email polling: If task fails, next scheduled task continues (no permanent loss)
- OAuth tokens: Refresh token valid for 6 months (user must re-authenticate if expired)

**Health Checks:**
- `/health/db` - PostgreSQL connectivity
- `/health/gmail` - Gmail API reachability (test call to gmail.users.getProfile)
- `/health/redis` - Redis connectivity for Celery

### Observability

**Structured Logging (JSON format):**

```json
{
  "timestamp": "2025-11-03T10:15:30.123Z",
  "level": "INFO",
  "service": "email_polling",
  "user_id": "123",
  "message": "Email polling cycle completed",
  "duration_ms": 2450,
  "metadata": {
    "emails_fetched": 8,
    "new_emails": 5,
    "duplicates_skipped": 3,
    "polling_interval_sec": 120
  }
}
```

**Log Events:**
- OAuth flow started/completed/failed
- Email polling cycle (start, end, results)
- Gmail API calls (method, latency, success/failure)
- Token refresh events
- Database operations (query duration, errors)
- Label creation/application events

**Prometheus Metrics:**
- `gmail_api_requests_total` (counter) - Labels: method, status_code, user_id
- `gmail_api_latency_seconds` (histogram) - Labels: method
- `email_polling_duration_seconds` (histogram)
- `emails_processed_total` (counter) - Labels: status
- `database_query_duration_seconds` (histogram) - Labels: query_type
- `oauth_token_refresh_total` (counter) - Labels: success/failure

**Grafana Dashboards (Epic 1 specific):**
- Email Polling Performance: emails/hour, latency, errors
- Gmail API Usage: requests/day, quota remaining, error rate
- Database Health: connection pool usage, query latency, slow queries
- OAuth Activity: new authentications, token refreshes, expirations

**Error Tracking:**
- Sentry integration for exception tracking (provided by template)
- Error grouping by: service, error_code, user_id
- Alert thresholds:
  - Gmail API error rate > 5% → Slack notification
  - Database connection failures > 3 in 5 minutes → PagerDuty alert

## Dependencies and Integrations

**External Dependencies:**

```python
# requirements.txt (Epic 1 additions)
google-api-python-client==2.146.0  # Gmail API client
google-auth==2.34.0  # OAuth 2.0 authentication
google-auth-oauthlib==1.2.1  # OAuth flow helpers
google-auth-httplib2==0.2.0  # HTTP transport for Google APIs

cryptography==43.0.1  # Fernet encryption for tokens
celery[redis]==5.4.0  # Background task queue
redis==5.1.1  # Message broker for Celery

# Already in template:
fastapi==0.120.4
sqlalchemy[asyncio]==2.0.36
alembic==1.13.3
psycopg[binary]==3.2.3  # PostgreSQL driver
pydantic==2.10.4
uvicorn==0.34.0
python-dotenv==1.0.1
```

**Integration Points:**

1. **Gmail API (REST):**
   - Base URL: `https://gmail.googleapis.com/gmail/v1/`
   - Authentication: OAuth 2.0 Bearer token
   - Key endpoints:
     - `GET /users/me/messages` - List emails
     - `GET /users/me/messages/{id}` - Get email detail
     - `GET /users/me/threads/{id}` - Get thread
     - `POST /users/me/messages/send` - Send email
     - `GET /users/me/labels` - List labels
     - `POST /users/me/labels` - Create label
     - `POST /users/me/messages/{id}/modify` - Apply/remove labels

2. **Google OAuth 2.0:**
   - Authorization URL: `https://accounts.google.com/o/oauth2/v2/auth`
   - Token URL: `https://oauth2.googleapis.com/token`
   - Required scopes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.modify`
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/gmail.labels`

3. **PostgreSQL Database:**
   - Version: 18 (Docker image: postgres:18-alpine)
   - Connection: `postgresql://mailagent:${DB_PASSWORD}@postgres:5432/mailagent`
   - Migrations: Alembic (already configured in template)

4. **Redis (Celery Broker):**
   - Version: 7 (Docker image: redis:7-alpine)
   - Connection: `redis://localhost:6379/0`
   - Used for: Celery task queue, session storage (future)

**Configuration Requirements:**

```bash
# .env file for Epic 1
DATABASE_URL=postgresql://mailagent:password@localhost:5432/mailagent
REDIS_URL=redis://localhost:6379/0

# Gmail OAuth credentials (from Google Cloud Console)
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REDIRECT_URI=http://localhost:3000/auth/gmail/callback

# Encryption key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-32-byte-base64-encoded-key

# JWT secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-random-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Environment
ENVIRONMENT=development  # development | staging | production
LOG_LEVEL=INFO  # DEBUG | INFO | WARN | ERROR
```

## Acceptance Criteria (Authoritative)

1. ✅ **Git repository initialized** with .gitignore for Python/Node.js projects
2. ✅ **Project structure created** with backend (FastAPI), database configs, and documentation
3. ✅ **README.md created** with project overview and setup instructions
4. ✅ **FastAPI application running** with health check endpoint (GET /health) returning 200 OK
5. ✅ **CORS middleware configured** for local frontend development (allow localhost:3000)
6. ✅ **Environment variable loading** working via .env file and python-dotenv
7. ✅ **PostgreSQL database created** and connection verified via /health/db endpoint
8. ✅ **SQLAlchemy ORM integrated** with Users, EmailProcessingQueue, FolderCategories models
9. ✅ **Alembic migrations** set up with initial migration creating all tables
10. ✅ **Google Cloud Project created** with Gmail API enabled
11. ✅ **OAuth 2.0 credentials obtained** (client ID, secret) and stored in .env
12. ✅ **OAuth endpoint POST /api/v1/auth/gmail/login** returns valid authorization URL
13. ✅ **OAuth callback GET /api/v1/auth/gmail/callback** exchanges code for tokens successfully
14. ✅ **OAuth tokens encrypted** using Fernet and stored in database
15. ✅ **Token refresh logic** automatically refreshes expired access tokens
16. ✅ **GmailClient class** created with methods: get_messages, get_message_detail, get_thread
17. ✅ **GmailClient.get_messages()** retrieves unread emails from Gmail inbox
18. ✅ **GmailClient.get_message_detail()** fetches full email content including body
19. ✅ **Error handling** for expired tokens triggers automatic token refresh
20. ✅ **Celery configured** with Redis broker and worker running successfully
21. ✅ **Email polling task** created (runs every 2 minutes, configurable via environment)
22. ✅ **Polling task retrieves unread emails** using GmailClient.get_messages()
23. ✅ **Email metadata extracted** (message_id, thread_id, sender, subject, date, labels)
24. ✅ **Processed emails marked** to avoid duplicate processing (unique constraint on gmail_message_id)
25. ✅ **Polling task handles multiple users** (iterates through all active users)
26. ✅ **Polling logging** implemented (emails found, processing status per cycle)
27. ✅ **EmailProcessingQueue table** stores email metadata with status field
28. ✅ **Status field supports states:** pending, processing, awaiting_approval, completed, rejected, error
29. ✅ **Database migration** created and applied for EmailProcessingQueue
30. ✅ **SQLAlchemy relationships** configured (User ↔ EmailProcessingQueue)
31. ✅ **Duplicate detection** implemented (skip emails already in queue by gmail_message_id)
32. ✅ **GmailClient.list_labels()** returns all Gmail labels for user
33. ✅ **GmailClient.create_label()** creates new Gmail label with specified name
34. ✅ **GmailClient.apply_label()** applies label to email message successfully
35. ✅ **GmailClient.remove_label()** removes label from email message
36. ✅ **Label color and visibility** configurable when creating labels
37. ✅ **Error handling** for duplicate label names (returns existing label ID)
38. ✅ **FolderCategories table** created with fields: name, gmail_label_id, keywords, color
39. ✅ **GmailClient.send_email()** composes MIME email message correctly
40. ✅ **GmailClient.send_email()** sends email via Gmail API successfully
41. ✅ **Plain text and HTML email bodies** supported
42. ✅ **Reply-to-thread functionality** includes In-Reply-To and References headers
43. ✅ **Sent emails include proper headers** (From, To, Subject, Date)
44. ✅ **Error handling** for send failures (quota exceeded, invalid recipient)
45. ✅ **Logging for sent emails** (recipient, subject, timestamp, success/failure)
46. ✅ **Integration test** runs complete OAuth flow (mocked Google OAuth)
47. ✅ **Integration test** verifies email polling and storage in database
48. ✅ **Integration test** verifies label creation and application to emails
49. ✅ **Integration test** verifies email sending capability
50. ✅ **API documentation** generated using FastAPI automatic docs (Swagger UI at /docs)
51. ✅ **Architecture documentation** created explaining Gmail integration flow
52. ✅ **Setup guide** updated with Gmail API configuration steps
53. ✅ **Environment variables documented** in README.md with examples

## Traceability Mapping

| AC # | Spec Section | Component/API | Test Idea |
|------|-------------|---------------|-----------|
| AC 1-3 | Project Structure | Repository, README.md | Verify git init, structure exists, README complete |
| AC 4-6 | Backend Foundation | `app/main.py`, `/health` endpoint | GET /health returns 200, CORS allows localhost:3000 |
| AC 7-9 | Database Setup | `app/models/`, Alembic migrations | /health/db returns connected, tables exist in PostgreSQL |
| AC 10-15 | OAuth Flow | `app/api/auth.py`, GmailClient token refresh | Mock OAuth flow, test token encryption/decryption |
| AC 16-19 | Gmail API Client | `app/core/gmail_client.py` | Mock Gmail API, test get_messages, get_message_detail |
| AC 20-26 | Email Polling | `app/tasks/email_tasks.py`, Celery | Mock Celery task, verify polling logic, duplicate skip |
| AC 27-30 | Email Data Model | `app/models/email_queue.py` | Insert email, verify status transitions, relationships |
| AC 31 | Duplicate Detection | EmailProcessingQueue unique constraint | Insert same gmail_message_id twice, verify skip |
| AC 32-38 | Label Management | GmailClient label methods, FolderCategories | Mock label create/apply/remove, verify database storage |
| AC 39-45 | Email Sending | GmailClient.send_email() | Mock send API, verify MIME format, threading headers |
| AC 46-49 | Integration Tests | `tests/integration/` | End-to-end tests with mocked external APIs |
| AC 50-53 | Documentation | `/docs`, README.md, architecture.md | Verify OpenAPI spec, setup guide completeness |

## Risks, Assumptions, Open Questions

**Risks:**

1. **Risk:** Gmail API quota exhaustion (10,000 req/day free tier)
   - **Likelihood:** Medium (high email volume users)
   - **Impact:** High (service stops working until quota resets)
   - **Mitigation:** Monitor quota usage via Prometheus, implement user notifications, batch operations where possible

2. **Risk:** OAuth token refresh failure (user must re-authenticate)
   - **Likelihood:** Low (Google maintains refresh tokens for 6 months)
   - **Impact:** Medium (user inconvenience)
   - **Mitigation:** Graceful error handling, email notification to reconnect Gmail

3. **Risk:** Email polling latency variability (Gmail API response times)
   - **Likelihood:** Medium (Google API SLA is 99.9% but latency can spike)
   - **Impact:** Low (still meets <2 min requirement with buffer)
   - **Mitigation:** Timeout handling, exponential backoff, fallback to next polling cycle

4. **Risk:** Database migration failures in production
   - **Likelihood:** Low (Alembic is battle-tested)
   - **Impact:** High (service downtime)
   - **Mitigation:** Test migrations in staging, database backups before migration, rollback plan

**Assumptions:**

1. Gmail API free tier quotas remain stable (Google has not announced changes)
2. Users grant all required OAuth scopes (gmail.readonly, modify, send, labels)
3. Email volumes stay within 5-50 emails/day per user (as per PRD target)
4. PostgreSQL free tier (Supabase or Railway) provides sufficient storage (<1GB for 100 users)
5. FastAPI template includes all necessary infrastructure (JWT, logging, migrations)
6. Redis free tier sufficient for Celery message broker (<100MB memory usage)

**Open Questions:**

1. **Question:** Should we implement Gmail push notifications (Pub/Sub) in Epic 1 or defer to post-MVP?
   - **Answer:** Defer to post-MVP per ADR-004 (polling meets latency requirements)

2. **Question:** How long should we retain emails in EmailProcessingQueue after completion?
   - **Answer:** Indefinitely for MVP (user data, needed for approval history in Epic 2). Add retention policy post-MVP.

3. **Question:** Should encryption key rotation be automated or manual?
   - **Answer:** Manual for MVP (document rotation procedure). Automate post-MVP with zero-downtime migration.

4. **Question:** What happens if user revokes Gmail OAuth access?
   - **Answer:** Next Gmail API call fails with 401 → Mark user as disconnected → Send email notification to reconnect (Epic 4 UI).

5. **Question:** Should we support multiple Gmail accounts per user?
   - **Answer:** Out of scope for MVP. Single Gmail account per user. Multi-account support is post-MVP feature.

## Test Strategy Summary

**Unit Tests (pytest):**
- GmailClient methods (mocked Gmail API responses)
- OAuth token encryption/decryption
- Email metadata extraction
- Database model CRUD operations
- Label creation/application logic
- Celery task logic (isolated from external dependencies)
- **Coverage Target:** 80%+ for core business logic

**Integration Tests:**
- End-to-end OAuth flow (mocked Google OAuth endpoints)
- Email polling cycle (mocked Gmail API, real database)
- Label management (mocked Gmail API, real database)
- Email sending (mocked Gmail API)
- Database migrations (test database)
- **Coverage Target:** All critical user flows tested

**Test Fixtures:**
- Mock Gmail API responses (emails, labels, threads)
- Test database with sample users, emails, folders
- Encrypted test tokens
- Mock Celery tasks

**Testing Tools:**
- pytest - Test framework
- pytest-asyncio - Async test support
- pytest-cov - Coverage reporting
- httpx - Async HTTP client for API testing
- pytest-mock - Mocking library
- Factory Boy - Test data generation (users, emails)

**Manual Testing Checklist (for final epic validation):**
1. [ ] Complete OAuth flow in browser (real Google account)
2. [ ] Verify tokens stored encrypted in database
3. [ ] Trigger email polling task manually (Celery CLI)
4. [ ] Send test email to Gmail, verify it appears in EmailProcessingQueue
5. [ ] Create folder via API, verify Gmail label created
6. [ ] Apply label to email, verify in Gmail UI
7. [ ] Send email via API, verify received in recipient Gmail
8. [ ] Revoke OAuth access in Google settings, verify error handling
9. [ ] Check Prometheus metrics for Gmail API usage
10. [ ] Review logs for sensitive data leakage (no email bodies, no tokens)

**Performance Testing:**
- Load test: 100 concurrent email polling cycles
- Stress test: 1000 emails in single poll
- Token refresh under load (10 concurrent refreshes)
- Database query performance (10K emails in queue)

**Security Testing:**
- OAuth CSRF protection (invalid state parameter)
- SQL injection attempts (malicious email sender names)
- Token theft simulation (encrypted tokens unusable without key)
- XSS in email subject/body (sanitization verified)
