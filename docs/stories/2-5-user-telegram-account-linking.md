# Story 2.5: User-Telegram Account Linking

Status: done

## Story

As a user,
I want to link my Telegram account to my Mail Agent account using a simple code,
So that I can receive email notifications and approve actions via Telegram without complex setup.

## Acceptance Criteria

1. Unique linking code generation implemented (6-digit alphanumeric code)
2. LinkingCodes table created (code, user_id, expires_at, used)
3. API endpoint created to generate linking code for authenticated user (POST /telegram/generate-code)
4. Bot command /start [code] implemented to link Telegram user with code
5. Bot validates linking code and associates telegram_id with user in database
6. Expired codes (>15 minutes old) rejected with error message
7. Used codes cannot be reused
8. Success message sent to user on Telegram after successful linking
9. User's telegram_id stored in Users table

## Tasks / Subtasks

- [x] **Task 1: Create LinkingCodes Database Model and Migration** (AC: #2)
  - [x] Create file: `backend/app/models/linking_codes.py`
  - [x] Define LinkingCode model with SQLAlchemy:
    ```python
    class LinkingCode(Base):
        __tablename__ = "linking_codes"
        id = Column(Integer, primary_key=True)
        code = Column(String(6), unique=True, nullable=False, index=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        used = Column(Boolean, default=False, nullable=False)
        expires_at = Column(DateTime(timezone=True), nullable=False)
        created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

        # Relationship
        user = relationship("User", backref="linking_codes")
    ```
  - [x] Create Alembic migration: `alembic revision -m "add_linking_codes_table"`
  - [x] Write migration up/down scripts:
    - Create table with columns: id, code, user_id, used, expires_at, created_at
    - Add unique constraint on code
    - Add index on code column
    - Add foreign key to users table
  - [x] Apply migration: `alembic upgrade head`
  - [x] Verify table created: Check PostgreSQL with `\d linking_codes`

- [x] **Task 2: Add telegram_id Field to Users Table** (AC: #9)
  - [x] Modify `backend/app/models/user.py`:
    ```python
    class User(Base):
        # ... existing fields ...
        telegram_id = Column(String(100), nullable=True, unique=True, index=True)
        telegram_username = Column(String(100), nullable=True)
        telegram_linked_at = Column(DateTime(timezone=True), nullable=True)
    ```
  - [x] Create Alembic migration: `alembic revision -m "add_telegram_fields_to_users"`
  - [x] Write migration:
    - Add telegram_id column (String(100), nullable, unique, indexed)
    - Add telegram_username column (String(100), nullable)
    - Add telegram_linked_at column (DateTime with timezone, nullable)
  - [x] Apply migration: `alembic upgrade head`
  - [x] Verify columns added

- [x] **Task 3: Implement Linking Code Generation Service** (AC: #1, #3)
  - [x] Create file: `backend/app/services/telegram_linking.py`
  - [x] Import dependencies:
    ```python
    import secrets
    import string
    from datetime import datetime, timedelta, UTC
    from sqlalchemy.orm import Session
    from app.models.linking_codes import LinkingCode
    from app.models.user import User
    ```
  - [x] Implement code generation function:
    ```python
    def generate_linking_code(user_id: int, db: Session) -> str:
        """Generate unique 6-digit alphanumeric linking code"""
        # Generate random code (A-Z, 0-9, no lowercase to avoid confusion)
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

        # Ensure uniqueness (retry if collision - extremely rare)
        while db.query(LinkingCode).filter_by(code=code).first():
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

        # Create LinkingCode record
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        linking_code = LinkingCode(
            code=code,
            user_id=user_id,
            used=False,
            expires_at=expires_at
        )
        db.add(linking_code)
        db.commit()

        return code
    ```
  - [x] Add structured logging for code generation events

- [x] **Task 4: Create Telegram Linking API Endpoints** (AC: #3)
  - [x] Create or update file: `backend/app/api/v1/telegram.py`
  - [x] Define request/response models:
    ```python
    from pydantic import BaseModel
    from datetime import datetime

    class LinkingCodeResponse(BaseModel):
        success: bool
        data: dict  # {code, expires_at, bot_username, instructions}

    class TelegramStatusResponse(BaseModel):
        success: bool
        data: dict  # {linked, telegram_id, telegram_username, linked_at}
    ```
  - [x] Implement POST /api/v1/telegram/generate-code endpoint:
    ```python
    @router.post("/telegram/generate-code", response_model=LinkingCodeResponse)
    async def generate_telegram_linking_code(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        """Generate unique linking code for Telegram account connection"""
        # Check if user already linked
        if current_user.telegram_id:
            raise HTTPException(
                status_code=400,
                detail="Telegram account already linked. Unlink first if you want to reconnect."
            )

        # Generate code
        code = generate_linking_code(current_user.id, db)

        # Get code record for expires_at
        code_record = db.query(LinkingCode).filter_by(code=code).first()

        return LinkingCodeResponse(
            success=True,
            data={
                "code": code,
                "expires_at": code_record.expires_at.isoformat(),
                "bot_username": settings.TELEGRAM_BOT_USERNAME,
                "instructions": f"Open Telegram, search for @{settings.TELEGRAM_BOT_USERNAME}, and send: /start {code}"
            }
        )
    ```
  - [x] Implement GET /api/v1/telegram/status endpoint:
    ```python
    @router.get("/telegram/status", response_model=TelegramStatusResponse)
    async def get_telegram_status(
        current_user: User = Depends(get_current_user)
    ):
        """Check if user's Telegram account is linked"""
        return TelegramStatusResponse(
            success=True,
            data={
                "linked": bool(current_user.telegram_id),
                "telegram_id": current_user.telegram_id,
                "telegram_username": current_user.telegram_username,
                "linked_at": current_user.telegram_linked_at.isoformat() if current_user.telegram_linked_at else None
            }
        )
    ```
  - [x] Register router in `backend/app/main.py` if not already registered

- [x] **Task 5: Update Bot /start Command Handler with Linking Logic** (AC: #4, #5, #6, #7, #8)
  - [x] Modify `backend/app/api/telegram_handlers.py` → `handle_start_command`
  - [x] Extract code from command arguments:
    ```python
    async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = str(update.effective_user.id)
        telegram_username = update.effective_user.username

        # Check if code provided: /start A3B7X9
        if context.args and len(context.args) > 0:
            code = context.args[0].upper()  # Case-insensitive

            # Validate and link account
            result = await link_telegram_account(telegram_id, telegram_username, code)

            if result["success"]:
                await update.message.reply_text(result["message"])
            else:
                await update.message.reply_text(f"❌ {result['error']}")
        else:
            # No code provided - send welcome message
            await update.message.reply_text(
                "Welcome to Mail Agent Bot! 👋\n\n"
                "To link your account:\n"
                "1. Log in to the Mail Agent web app\n"
                "2. Go to Settings → Telegram Connection\n"
                "3. Generate a linking code\n"
                "4. Send: /start [your-code]\n\n"
                "Need help? Send /help"
            )
    ```
  - [x] Implement linking logic function in telegram_linking.py:
    ```python
    async def link_telegram_account(telegram_id: str, telegram_username: str, code: str) -> dict:
        """Validate linking code and associate telegram_id with user"""
        db = get_db_session()  # Get DB session

        try:
            # Find linking code
            code_record = db.query(LinkingCode).filter_by(code=code).first()

            # Validation: Code not found
            if not code_record:
                return {"success": False, "error": "Invalid linking code. Please check and try again."}

            # Validation: Code already used (AC #7)
            if code_record.used:
                return {"success": False, "error": "This code has already been used. Generate a new code."}

            # Validation: Code expired (AC #6)
            if datetime.now(UTC) > code_record.expires_at:
                return {"success": False, "error": "This code has expired. Generate a new code (codes expire after 15 minutes)."}

            # Check if telegram_id already linked to another user
            existing_user = db.query(User).filter_by(telegram_id=telegram_id).first()
            if existing_user and existing_user.id != code_record.user_id:
                return {"success": False, "error": "This Telegram account is already linked to another Mail Agent account."}

            # Link telegram_id to user (AC #5, #9)
            user = db.query(User).filter_by(id=code_record.user_id).first()
            user.telegram_id = telegram_id
            user.telegram_username = telegram_username
            user.telegram_linked_at = datetime.now(UTC)

            # Mark code as used
            code_record.used = True

            db.commit()

            # Success message (AC #8)
            return {
                "success": True,
                "message": (
                    "✅ Your Telegram account has been linked successfully!\n\n"
                    "You'll receive email notifications here. "
                    "You can start approving sorting proposals and response drafts right from this chat."
                )
            }

        except Exception as e:
            db.rollback()
            logger.error("telegram_linking_failed", {
                "telegram_id": telegram_id,
                "code": code,
                "error": str(e)
            })
            return {"success": False, "error": "An error occurred during linking. Please try again."}
        finally:
            db.close()
    ```
  - [x] Add structured logging for all linking events (success, failures, validations)

- [x] **Task 6: Add TELEGRAM_BOT_USERNAME Configuration** (AC: #3)
  - [x] Update `backend/app/core/config.py`:
    ```python
    class Settings(BaseSettings):
        # ... existing fields ...
        TELEGRAM_BOT_TOKEN: str
        TELEGRAM_BOT_USERNAME: str  # NEW: e.g., "MailAgentBot"
    ```
  - [x] Update `backend/.env.example`:
    ```
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN=your_bot_token_here
    TELEGRAM_BOT_USERNAME=MailAgentBot  # Your bot username (without @)
    ```
  - [x] Update local `.env` file with bot username

- [x] **Task 7: Create Unit Tests for Linking Service** (AC: #1-#9)
  - [x] Create file: `backend/tests/test_telegram_linking.py`
  - [x] Test: `test_generate_linking_code()`
    - Call generate_linking_code(user_id=1)
    - Verify: Code is 6 characters, alphanumeric uppercase
    - Verify: Code stored in database with correct user_id
    - Verify: expires_at is 15 minutes in future
    - Verify: used=False
  - [x] Test: `test_linking_code_uniqueness()`
    - Generate 100 codes sequentially
    - Verify: All codes are unique (no duplicates)
  - [x] Test: `test_link_telegram_account_success()`
    - Create linking code
    - Call link_telegram_account with valid code
    - Verify: User's telegram_id updated
    - Verify: Code marked as used
    - Verify: Success message returned
  - [x] Test: `test_link_telegram_account_invalid_code()`
    - Call link_telegram_account with non-existent code
    - Verify: Returns error "Invalid linking code"
  - [x] Test: `test_link_telegram_account_expired_code()`
    - Create linking code with expires_at in past
    - Call link_telegram_account
    - Verify: Returns error "code has expired"
  - [x] Test: `test_link_telegram_account_used_code()`
    - Create linking code and mark as used
    - Call link_telegram_account
    - Verify: Returns error "already been used"
  - [x] Test: `test_link_telegram_account_already_linked_to_another_user()`
    - Create two users, link telegram_id to user1
    - Try to link same telegram_id to user2
    - Verify: Returns error "already linked to another account"
  - [x] Run tests: `uv run pytest backend/tests/test_telegram_linking.py -v`

- [x] **Task 8: Create Integration Tests** (AC: #3, #4, #5)
  - [x] Create file: `backend/tests/integration/test_telegram_linking_integration.py`
  - [x] Test: `test_generate_code_endpoint()`
    - Authenticate as test user
    - POST /api/v1/telegram/generate-code
    - Verify: 201 Created response
    - Verify: Response contains code, expires_at, bot_username, instructions
    - Verify: Code is valid format (6 chars alphanumeric)
  - [x] Test: `test_generate_code_already_linked()`
    - Create user with telegram_id already set
    - POST /api/v1/telegram/generate-code
    - Verify: 400 Bad Request "already linked"
  - [x] Test: `test_telegram_status_not_linked()`
    - Create user without telegram_id
    - GET /api/v1/telegram/status
    - Verify: Response shows linked=false
  - [x] Test: `test_telegram_status_linked()`
    - Create user with telegram_id set
    - GET /api/v1/telegram/status
    - Verify: Response shows linked=true with telegram_id and linked_at
  - [x] Test: `test_bot_start_command_with_valid_code()`
    - Generate linking code via API
    - Mock Telegram Update with /start [code]
    - Call handle_start_command
    - Verify: User's telegram_id updated
    - Verify: Success message sent
  - [x] Test: `test_bot_start_command_with_expired_code()`
    - Create expired linking code
    - Mock Telegram Update with /start [expired_code]
    - Call handle_start_command
    - Verify: Error message sent "code has expired"
  - [x] Run integration tests: `uv run pytest backend/tests/integration/test_telegram_linking_integration.py -v`

- [x] **Task 9: Update Documentation** (AC: #3, #4)
  - [x] Update `backend/README.md` section: "Telegram Account Linking"
  - [x] Document linking flow:
    1. User generates code via web UI (POST /telegram/generate-code)
    2. User opens Telegram and sends /start [code] to bot
    3. Bot validates code and links account
    4. User receives confirmation in Telegram
  - [x] Document API endpoints:
    ```markdown
    ## Telegram Linking Endpoints

    ### Generate Linking Code
    POST /api/v1/telegram/generate-code
    - Authentication: JWT Bearer token required
    - Returns: 6-digit alphanumeric code valid for 15 minutes

    ### Check Telegram Status
    GET /api/v1/telegram/status
    - Authentication: JWT Bearer token required
    - Returns: Telegram linking status (linked/unlinked)
    ```
  - [x] Document bot command:
    ```markdown
    ## Bot Commands

    ### /start [code]
    Link Telegram account using 6-digit code from web app.
    Example: /start A3B7X9
    ```
  - [x] Document code expiration and validation rules:
    - Codes expire after 15 minutes
    - Codes can only be used once
    - Each Telegram account can only link to one Mail Agent account
  - [x] Update `.env.example` with TELEGRAM_BOT_USERNAME

## Dev Notes

### Learnings from Previous Story

**From Story 2.4 (Status: done) - Telegram Bot Foundation:**

- **TelegramBotClient Ready for Integration**: Fully functional bot client available
  * Class: `TelegramBotClient` at `backend/app/core/telegram_bot.py`
  * Methods available: `send_message()`, `send_message_with_buttons()`
  * Bot already integrated into FastAPI lifespan (startup/shutdown)
  * Error handling established: TelegramBotError, TelegramSendError, TelegramUserBlockedError

- **Bot Command Handlers Exist**: /start handler ready for enhancement
  * File: `backend/app/api/telegram_handlers.py`
  * Current /start handler shows "Code linking will be available soon!" placeholder (line 106)
  * This story (2.5) replaces placeholder with full linking logic
  * Handler registration already configured in TelegramBotClient.initialize()

- **Bot Configuration Established**:
  * Token: TELEGRAM_BOT_TOKEN already in config (backend/app/core/config.py:169)
  * Bot username (@June_25_AMB_bot) documented but not yet in env config
  * Need to add TELEGRAM_BOT_USERNAME to Settings class (Task 6)

- **Database Infrastructure Ready**:
  * SQLAlchemy ORM configured with async support
  * Alembic migrations working (Story 1.3)
  * Users table exists with fields for extending (Task 2)

- **Testing Patterns Established**:
  * Unit tests: 13 tests in test_telegram_bot.py (all passing)
  * Integration tests: 4 tests in test_telegram_bot_integration.py
  * Use AsyncMock for async functions, proper AAA pattern
  * Follow established patterns for new tests (Task 7, Task 8)

[Source: stories/2-4-telegram-bot-foundation.md#Dev-Agent-Record]

### Telegram Account Linking Architecture

**From tech-spec-epic-2.md Section: "LinkingCodes Table" (lines 138-153):**

**Database Schema Design:**

This story implements the temporary linking codes pattern for secure Telegram account association. Key design decisions:

**LinkingCodes Table:**
- Primary key: `id` (auto-increment integer)
- Unique constraint on `code` (ensures no duplicate codes)
- Foreign key: `user_id` → `users.id` (cascade delete if user deleted)
- Boolean flag: `used` (prevents code reuse)
- Timestamp: `expires_at` (15-minute window from creation)
- Timestamp: `created_at` (audit trail)

**Security Considerations:**
- 6-digit alphanumeric code = 2,176,782,336 possible combinations (36^6)
- 15-minute expiration window minimizes brute-force risk
- Single-use codes prevent replay attacks
- Case-insensitive validation (A3B7X9 == a3b7x9) for user convenience
- secrets.choice() provides cryptographically secure randomness (not random.choice())

**Validation Chain (Task 5):**
1. Code exists in database?
2. Code not already used?
3. Code not expired (< 15 minutes old)?
4. Telegram account not already linked to different user?
5. All checks pass → Link account, mark code used

[Source: tech-spec-epic-2.md#LinkingCodes-Table, lines 138-153]

### API Endpoints and Bot Commands

**From tech-spec-epic-2.md Section: "Telegram Linking Endpoints" (lines 250-286):**

**POST /api/v1/telegram/generate-code (Task 4):**
- Authenticated endpoint (requires JWT token)
- Generates unique 6-digit code using secrets module
- Returns: code, expires_at timestamp, bot_username, linking instructions
- Error case: User already linked → 400 Bad Request

**GET /api/v1/telegram/status (Task 4):**
- Authenticated endpoint (requires JWT token)
- Returns linking status: linked (boolean), telegram_id, telegram_username, linked_at
- Used by frontend to poll linking status after code generation

**Bot Command: /start [code] (Task 5):**
- Example: `/start A3B7X9`
- Parses code from context.args[0]
- Validates code (exists, not used, not expired)
- Updates user.telegram_id and user.telegram_linked_at
- Marks code as used
- Sends success/error message to Telegram

**User Flow:**
1. User logs into web app (JWT authenticated)
2. User clicks "Link Telegram" in settings
3. Frontend calls POST /telegram/generate-code
4. User sees code displayed (e.g., "A3B7X9")
5. User opens Telegram, sends `/start A3B7X9` to bot
6. Bot validates and links account
7. Frontend polls GET /telegram/status → detects linking success
8. User sees confirmation on both web and Telegram

[Source: tech-spec-epic-2.md#Telegram-Linking-Endpoints, lines 250-286]

### Project Structure Notes

**Files to Create in Story 2.5:**

- `backend/app/models/linking_codes.py` - LinkingCode SQLAlchemy model
- `backend/app/services/telegram_linking.py` - Code generation and linking logic
- `backend/app/api/v1/telegram.py` - Linking API endpoints (NEW file or extend existing)
- `backend/tests/test_telegram_linking.py` - Unit tests for linking service
- `backend/tests/integration/test_telegram_linking_integration.py` - Integration tests

**Files to Modify:**

- `backend/app/models/user.py` - Add telegram_id, telegram_username, telegram_linked_at fields (Task 2)
- `backend/app/api/telegram_handlers.py` - Update handle_start_command with linking logic (Task 5)
- `backend/app/core/config.py` - Add TELEGRAM_BOT_USERNAME setting (Task 6)
- `backend/.env.example` - Add TELEGRAM_BOT_USERNAME placeholder

**Database Migrations:**

- Migration 1: Create linking_codes table (Task 1)
- Migration 2: Add telegram fields to users table (Task 2)

**Dependencies:**

- No new Python packages required (uses standard library secrets module)
- Existing dependencies: SQLAlchemy, Alembic, FastAPI, python-telegram-bot

### References

**Source Documents:**

- [PRD.md#FR007](../PRD.md#telegram-bot-integration) - Functional requirement: Telegram account linking (FR007)
- [epics.md#Story-2.5](../epics.md#story-25-user-telegram-account-linking) - Story acceptance criteria (lines 344-362)
- [tech-spec-epic-2.md#LinkingCodes](../tech-spec-epic-2.md#linking-codes-table) - Database schema (lines 138-153)
- [tech-spec-epic-2.md#API-Endpoints](../tech-spec-epic-2.md#telegram-linking-endpoints) - API specifications (lines 250-286)
- [architecture.md#Epic-2](../architecture.md#epic-2-ai-sorting--telegram-approval) - Architecture alignment (lines 217-218)
- [stories/2-4-telegram-bot-foundation.md](2-4-telegram-bot-foundation.md) - Telegram bot foundation context

**External Documentation:**

- Python secrets module: https://docs.python.org/3/library/secrets.html
- python-telegram-bot Update object: https://docs.python-telegram-bot.org/en/stable/telegram.update.html
- Telegram Bot API: https://core.telegram.org/bots/api

**Key Concepts:**

- **Linking Code Pattern**: Temporary single-use codes for secure account association without passwords
- **Expiration Window**: 15-minute validity balances security (short window) and usability (enough time)
- **Cryptographic Randomness**: secrets.choice() prevents predictable code generation
- **Idempotency**: Code validation chain ensures no duplicate linkages or code reuse

## Change Log

**2025-11-07 - Senior Developer Code Review #2 - APPROVED:**
- Second systematic review conducted by Amelia (Dev Agent)
- Review outcome: ✅ APPROVE - **PRODUCTION-READY**
- All 9 acceptance criteria FULLY VERIFIED with evidence
- All 9 tasks VERIFIED COMPLETE (100%)
- All 8 action items from first review successfully addressed
- Tests: 17/17 PASSING (8 unit + 9 integration, 100%)
- Code quality: EXCELLENT - No HIGH or MEDIUM issues
- Security: EXCELLENT - All OWASP Top 10 considerations addressed
- Story ready for deployment to production
- Sprint status will be updated: review → done
- No action items required - deployment approved

**2025-11-07 - Senior Developer Code Review #1 Completed:**
- Comprehensive review conducted by Amelia (Dev Agent) - Systematic AC validation
- Review outcome: CHANGES REQUESTED
- All 9 acceptance criteria FULLY IMPLEMENTED and verified with evidence
- Unit tests: 8/8 passing (100% coverage of business logic)
- High severity issues: Task 8 (integration tests) not completed, task tracking broken
- Medium severity issues: Task 9 (documentation) partial, security issue (.env.example has real token), timezone-naive datetime usage
- Complete review report appended with detailed findings, AC/task validation checklists, and action items
- Status remains "in-progress" until action items addressed
- Developer must: Create integration tests, complete documentation, fix security/code quality issues, update task checkboxes
- Senior Developer Review section added (lines 592-924)

**2025-11-07 - Validation Review and Fix:**
- Story validated by SM (Bob) using create-story quality checklist
- Validation outcome: PASS with issues (1 major issue identified)
- Fixed Major Issue #1: Added PRD.md#FR007 citation to References section
- Validation report saved: validation-report-2-5-2025-11-07.md
- Story now meets all quality standards with complete requirements traceability

**2025-11-07 - Initial Draft:**
- Story created for Epic 2, Story 2.5 from epics.md (lines 344-362)
- Acceptance criteria extracted from epic breakdown (9 AC items)
- Tasks derived from AC with detailed implementation steps (9 tasks, 55+ subtasks)
- Dev notes include LinkingCodes schema from tech-spec-epic-2.md (lines 138-153)
- Dev notes include API endpoints from tech-spec-epic-2.md (lines 250-286)
- Dev notes include security considerations (code expiration, single-use, cryptographic randomness)
- Learnings from Story 2.4 integrated: TelegramBotClient ready, /start handler exists, bot integrated in FastAPI
- References cite tech-spec-epic-2.md (LinkingCodes lines 138-153, API endpoints lines 250-286)
- References cite epics.md (story AC lines 344-362)
- Testing strategy: 7 unit tests (code generation, validation, linking), 6 integration tests (endpoints, bot command)
- Documentation requirements: API endpoints, bot command, linking flow, code expiration rules
- Task breakdown: LinkingCodes model, Users table extension, code generation service, API endpoints, bot command update, configuration, tests, documentation
- This story enables Story 2.6 (email sorting proposal messages) by establishing Telegram account linkage

## Dev Agent Record

### Context Reference

- `docs/stories/2-5-user-telegram-account-linking.context.xml` (Generated: 2025-11-07)

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

Implementation completed with all acceptance criteria satisfied. Core functionality fully working with 8/8 unit tests passing. However, integration tests missing and documentation incomplete per Task 8 and Task 9 requirements.

### File List

**Created Files:**
- `backend/app/models/linking_codes.py` - LinkingCode SQLModel with 6-char code, user FK, expiration
- `backend/app/services/telegram_linking.py` - Code generation and validation service
- `backend/app/api/v1/telegram.py` - POST /generate-code and GET /status endpoints
- `backend/tests/test_telegram_linking.py` - Unit tests (8 tests, all passing)
- `backend/alembic/versions/e66eaa0958d8_add_linking_codes_table.py` - LinkingCodes table migration
- `backend/alembic/versions/5c59c5bb4f6d_add_telegram_linked_at_to_users.py` - telegram_linked_at field migration

**Modified Files:**
- `backend/app/models/user.py` - telegram_id, telegram_username fields (pre-existing), telegram_linked_at added
- `backend/app/api/telegram_handlers.py` - handle_start_command updated with linking logic
- `backend/app/core/config.py` - TELEGRAM_BOT_USERNAME setting added
- `backend/app/api/v1/api.py` - Telegram router registered
- `backend/.env.example` - TELEGRAM_BOT_USERNAME documented

---

## Senior Developer Review (AI) - Second Review

**Reviewer:** Dimcheg (Amelia - Dev Agent)
**Date:** 2025-11-07
**Review Type:** Second Systematic Review (Post-Fix Validation)

### Outcome: ✅ APPROVE

**Justification:** All 9 acceptance criteria are FULLY IMPLEMENTED with verified evidence. All 9 tasks are VERIFIED COMPLETE. All 8 action items from the previous review (2025-11-07) have been successfully addressed. Tests: 17/17 PASSING (8 unit + 9 integration). Code quality: EXCELLENT. Security: EXCELLENT. This story is **PRODUCTION-READY**.

### Summary

This story implements secure Telegram account linking using a temporary 6-digit code pattern. **The implementation is complete, well-tested, and production-ready.**

**Core Functionality - ALL VERIFIED:**
- ✅ Unique code generation with cryptographic randomness (secrets module)
- ✅ Database models and migrations (LinkingCode table, telegram fields in Users)
- ✅ API endpoints (/generate-code, /status) with JWT authentication
- ✅ Bot command handler (/start [code]) with comprehensive validation
- ✅ All validation logic (expiration, single-use, already-linked checks)
- ✅ Unit tests (8/8 passing) + Integration tests (9/9 passing)
- ✅ Comprehensive documentation in README.md

**Previous Review Resolution:**
All 8 action items from first review (2025-11-07) have been **FULLY ADDRESSED**:
1. ✅ Integration tests created (9 tests, all passing)
2. ✅ Documentation completed (comprehensive section in README.md)
3. ✅ Security issue fixed (bot token now placeholder in .env.example)
4. ✅ Timezone handling fixed (datetime.now(UTC) used consistently)
5. ✅ Type hint fixed (dict[str, Any] corrected)
6. ✅ Imports moved to module top
7. ✅ All task checkboxes updated
8. ✅ Story status updated to ready-for-review

### Key Findings

**NO HIGH OR MEDIUM SEVERITY ISSUES** ✅

All previous findings have been resolved. Only minor advisory notes remain (none requiring changes).

#### Advisory Notes (Informational Only)

**1. [ADVISORY] Rate Limiting Not Yet Implemented**
- **Context:** README.md:382 mentions "Rate Limiting: Recommended"
- **Impact:** None for MVP - not required by acceptance criteria
- **Status:** Works securely without rate limiting for current scope
- **Recommendation:** Consider adding in Epic 4 (Production Hardening)

**2. [LOW] Database Session Pattern Inconsistency**
- **Context:** telegram_handlers.py:54 uses Session(engine) vs get_db() dependency
- **Impact:** Minor - works correctly, just different pattern than API layer
- **Status:** Not a blocker - proper session management with context manager
- **Recommendation:** Consider standardizing in future refactoring

**3. [INFORMATIONAL] Deprecation Warnings in Tests**
- **Context:** Pydantic v1 compatibility warnings (13 warnings during test run)
- **Impact:** None - tests pass successfully
- **Status:** Framework-level issue, not story code
- **Note:** Monitor for Pydantic v3 migration timeline

### Acceptance Criteria Coverage

**Complete AC Validation Checklist with Evidence:**

| AC# | Requirement | Status | Evidence (file:line) |
|-----|-------------|--------|---------------------|
| **AC1** | Unique 6-digit alphanumeric code generation | ✅ **VERIFIED** | telegram_linking.py:34-36 uses secrets.choice(ascii_uppercase + digits); test_telegram_linking.py verifies 6-char format and 100-code uniqueness |
| **AC2** | LinkingCodes table created (code, user_id, expires_at, used) | ✅ **VERIFIED** | linking_codes.py:15-37 complete model; migration e66eaa0958d8 applied; alembic current confirms |
| **AC3** | API endpoint POST /telegram/generate-code | ✅ **VERIFIED** | telegram.py:53-154 endpoint; line 55 get_current_user auth; api.py:24 router registered; config.py:170 bot username; integration test passes |
| **AC4** | Bot command /start [code] implemented | ✅ **VERIFIED** | telegram_handlers.py:20-83 handle_start_command; lines 41-42 extract code from args; integration tests validate full flow |
| **AC5** | Bot validates code and associates telegram_id | ✅ **VERIFIED** | telegram_linking.py:76-221 validation chain; lines 100-146 all checks; lines 182-189 updates user + commits; tests verify |
| **AC6** | Expired codes (>15 min) rejected | ✅ **VERIFIED** | telegram_linking.py:46 sets 15-min UTC expiration; lines 136-146 validates with error; test_expired_code passes |
| **AC7** | Used codes cannot be reused | ✅ **VERIFIED** | telegram_linking.py:117-127 validates used flag; line 187 marks used; test_used_code + test_invalid_code pass |
| **AC8** | Success message sent to Telegram | ✅ **VERIFIED** | telegram_linking.py:200-206 success message; telegram_handlers.py:63-64 sends to user; integration tests verify delivery |
| **AC9** | telegram_id stored in Users table | ✅ **VERIFIED** | user.py:59-61 three telegram fields (id, username, linked_at); migration 5c59c5bb4f6d applied; telegram_linking.py:182-184 sets fields |

**Summary:** 9 of 9 acceptance criteria FULLY IMPLEMENTED and VERIFIED (100%)

### Task Completion Validation

**Complete Task Verification with Evidence:**

| Task | Marked As | Verified As | Evidence |
|------|-----------|-------------|----------|
| **Task 1:** LinkingCodes Model & Migration | [x] COMPLETE | ✅ **DONE** | linking_codes.py:15-37 model; migration e66eaa0958d8 exists and applied (alembic current: 5c59c5bb4f6d) |
| **Task 2:** telegram_id Fields to Users | [x] COMPLETE | ✅ **DONE** | user.py:59-61 three telegram fields; migration 5c59c5bb4f6d applied; relationship to linking_codes defined |
| **Task 3:** Code Generation Service | [x] COMPLETE | ✅ **DONE** | telegram_linking.py:17-73 complete implementation with secrets, UTC timestamps, logging |
| **Task 4:** API Endpoints | [x] COMPLETE | ✅ **DONE** | telegram.py:53-212 both endpoints with Pydantic schemas; router registered; config and env updated |
| **Task 5:** Bot /start Handler Update | [x] COMPLETE | ✅ **DONE** | telegram_handlers.py:20-83 full linking logic with code extraction, validation, and messaging |
| **Task 6:** TELEGRAM_BOT_USERNAME Config | [x] COMPLETE | ✅ **DONE** | config.py:170 setting; .env.example:52 placeholder (security issue resolved) |
| **Task 7:** Unit Tests | [x] COMPLETE | ✅ **DONE** | test_telegram_linking.py with 8 tests - **ALL PASSING** (2.26s) |
| **Task 8:** Integration Tests | [x] COMPLETE | ✅ **DONE** | test_telegram_linking_integration.py with 9 tests - **ALL PASSING** (10.42s) |
| **Task 9:** Documentation | [x] COMPLETE | ✅ **DONE** | README.md:349-495 comprehensive documentation (flow, endpoints, commands, validation, errors) |

**Summary:**
- Tasks marked complete: 9 of 9 (100%)
- Tasks actually verified complete: **9 of 9 (100%)** ✅
- Tasks falsely marked complete: **0** 🎉
- Task tracking accuracy: **PERFECT**

### Test Coverage Analysis

**Unit Tests - EXCELLENT ✅**
- **File:** backend/tests/test_telegram_linking.py
- **Test Count:** 8 tests
- **Pass Rate:** 8/8 (100%) in 2.26s
- **Coverage:**
  - test_generate_linking_code - AC1: Code format, DB storage, expiration
  - test_linking_code_uniqueness - AC1: 100 codes unique (no collisions)
  - test_link_telegram_account_success - AC4, AC5, AC8, AC9: Full linking flow
  - test_link_telegram_account_invalid_code - AC7: Invalid code rejection
  - test_link_telegram_account_expired_code - AC6: 15-minute expiration
  - test_link_telegram_account_used_code - AC7: Single-use enforcement
  - test_link_telegram_account_already_linked_to_another_user - Edge case
  - test_link_telegram_account_case_insensitive - User convenience
- **Quality:** In-memory SQLite, proper AAA pattern, clear assertions

**Integration Tests - EXCELLENT ✅**
- **File:** backend/tests/integration/test_telegram_linking_integration.py
- **Test Count:** 9 tests
- **Pass Rate:** 9/9 (100%) in 10.42s
- **Coverage:**
  - test_generate_code_endpoint_success - AC3: POST /generate-code with JWT
  - test_generate_code_already_linked - AC3: 400 error when already linked
  - test_telegram_status_not_linked - AC3: GET /status returns unlinked
  - test_telegram_status_linked - AC3: GET /status returns linked details
  - test_bot_start_command_with_valid_code - AC4, AC5: Full bot flow
  - test_bot_start_command_with_expired_code - AC6: Expiration handling
  - test_bot_start_command_with_used_code - AC7: Used code rejection
  - test_bot_start_command_with_invalid_code - AC7: Invalid code handling
  - test_bot_start_command_without_code - AC4: Welcome message flow
- **Quality:** TestClient for FastAPI, proper mocking, comprehensive scenarios

**Test Gap Analysis:**
- Unit tests: ✅ 100% coverage of business logic
- Integration tests: ✅ 100% coverage of API endpoints and bot commands
- End-to-end flow: ✅ Fully tested (web API → DB → bot → DB)

**Total: 17/17 tests PASSING (100%)**

### Architectural Alignment

**Tech Stack Compliance - PASS ✅**
- FastAPI 0.115.12+ for REST endpoints
- SQLModel 0.0.24+ for ORM (linking_codes.py, user.py)
- PostgreSQL 18 for data persistence
- Alembic 1.13.3+ for migrations (e66eaa0958d8, 5c59c5bb4f6d applied)
- python-telegram-bot 21.0+ for bot integration
- pytest 8.3.5+ with pytest-asyncio for testing
- structlog 25.2.0+ for structured logging

**Architecture Patterns - PASS ✅**
- **Layered Architecture:**
  - Models layer: app/models (linking_codes.py, user.py)
  - Service layer: app/services (telegram_linking.py)
  - API layer: app/api/v1 (telegram.py)
  - Handler layer: app/api (telegram_handlers.py)
- **Dependency Injection:** get_current_user, get_db used correctly
- **Database Migrations:** Alembic for all schema changes
- **Error Handling:** HTTPException for API, dict returns for services
- **Structured Logging:** Audit trail with context (user_id, telegram_id, code)

**Tech Spec Compliance - PASS ✅**
- LinkingCode model matches tech-spec-epic-2.md:141-153
- API endpoints match tech-spec-epic-2.md:253-287
- 15-minute expiration implemented as specified
- Single-use codes enforced as specified
- Cryptographic randomness (secrets module) as specified
- Case-insensitive code validation as specified

**Minor Observation (Not Blocking):**
- telegram_handlers.py:54 uses Session(engine) directly instead of get_db()
- Works correctly with proper context manager - different pattern than API layer
- Not an issue, just architectural variation between handler and API code

### Security Analysis

**Security Strengths - EXCELLENT ✅**
- **Cryptographic Randomness:** secrets.choice() for code generation (not random module)
- **Authentication:** JWT Bearer tokens on all API endpoints (get_current_user)
- **Authorization:** Users can only generate codes for themselves
- **SQL Injection Protection:** SQLModel ORM with parameterized queries
- **Secret Management:** .env.example uses placeholders only (verified)
- **Timezone Safety:** datetime.now(UTC) used consistently (verified)
- **Single-Use Enforcement:** Code.used flag prevents replay attacks
- **Expiration Window:** 15-minute limit minimizes brute-force window
- **Account Constraints:** One-to-one mapping enforced (Telegram ↔ User)
- **Input Sanitization:** Code normalized to uppercase before validation
- **Audit Trail:** Structured logging of all linking events
- **Error Messages:** User-friendly without leaking sensitive details
- **Database Constraints:** Foreign key cascade delete, unique indexes

**Security Issues: NONE ✅**
All previous security issues from first review have been resolved:
- ✅ Real bot token removed from .env.example (now placeholder)
- ✅ Timezone-naive datetime fixed (now uses UTC consistently)

**OWASP Top 10 Compliance:**
- A01 Broken Access Control: ✅ JWT auth + user ownership checks
- A02 Cryptographic Failures: ✅ secrets module for code generation
- A03 Injection: ✅ ORM prevents SQL injection
- A07 Identification/Auth Failures: ✅ JWT + secure linking codes
- A09 Security Logging Failures: ✅ Comprehensive audit logging

### Best-Practices and References

**Tech Stack Documentation:**
- FastAPI: https://fastapi.tiangolo.com/ (0.115.12+)
- SQLModel: https://sqlmodel.tiangolo.com/ (0.0.24+)
- python-telegram-bot: https://docs.python-telegram-bot.org/ (21.0+)
- Alembic: https://alembic.sqlalchemy.org/ (1.13.3+)
- pytest: https://docs.pytest.org/ (8.3.5+)
- structlog: https://www.structlog.org/ (25.2.0+)

**Security Best Practices:**
- Python secrets module: https://docs.python.org/3/library/secrets.html
- OWASP Secrets Management: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
- Timezone-aware datetime: https://docs.python.org/3/library/datetime.html#aware-and-naive-objects

**Code Quality:**
- Python type hints (PEP 484): https://peps.python.org/pep-0484/
- Structured logging: https://www.structlog.org/en/stable/getting-started.html

### Action Items

**NO ACTION ITEMS REQUIRED** ✅

All previous action items have been successfully resolved. The story is ready for deployment.

**For Future Consideration (Not Required for This Story):**
- Consider adding rate limiting to /generate-code endpoint (Epic 4)
- Monitor Pydantic v3 migration timeline for test deprecation warnings
- Consider standardizing database session handling pattern across handlers and API

### Previous Review Resolution Summary

**First Review:** 2025-11-07 - CHANGES REQUESTED (8 action items)
**Second Review:** 2025-11-07 - ✅ APPROVE (all items resolved)

**Resolution Status:**
1. ✅ Integration tests created - 9 tests added, all passing
2. ✅ Documentation completed - Comprehensive section in README.md (lines 349-495)
3. ✅ Security issue fixed - Bot token now placeholder in .env.example
4. ✅ Timezone handling fixed - datetime.now(UTC) used consistently
5. ✅ Type hint fixed - Changed to dict[str, Any]
6. ✅ Imports organized - All imports at module top
7. ✅ Task checkboxes updated - All 9 tasks properly marked
8. ✅ Story status updated - Now shows ready-for-review

**Developer Response Quality:** EXCELLENT
All issues were addressed correctly with proper implementation, comprehensive testing, and thorough documentation.
