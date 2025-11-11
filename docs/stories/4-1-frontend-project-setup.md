# Story 4.1: Telegram Bot Onboarding Foundation

Status: drafted

## Story

As a developer,
I want to create the foundational database schema and core services for the onboarding wizard,
So that I have the infrastructure needed to build the Telegram Bot onboarding flow.

## Acceptance Criteria

1. UserSettings table created with Alembic migration (batch_notifications_enabled, batch_time, priority_alerts_enabled, quiet_hours_start, quiet_hours_end, onboarding_completed, onboarding_current_step, gmail_connected_at, telegram_linked_at, folders_setup_at, language_preference, timezone)
2. FolderCategories table created with Alembic migration (user_id, name, keywords, color, gmail_label_id, is_default)
3. OAuthTokens table created with Alembic migration (user_id, access_token, refresh_token, token_expiry, scope)
4. SettingsService implemented with CRUD operations (get_or_create_settings, update_notification_preferences, create_folder_category, save_oauth_tokens)
5. OnboardingWizard service skeleton created with state machine structure (start_onboarding, resume_from_step, send_step_N methods)
6. Database indexes created for performance (idx_user_settings_user_id, idx_folder_categories_user_id, idx_oauth_tokens_user_id)
7. All database operations use async-only patterns (`async with db_service.async_session()`)
8. OAuth token encryption implemented using cryptography.fernet.Fernet
9. Unit tests implemented: 8 for SettingsService, 5 for OnboardingWizard skeleton (13 total)
10. Integration tests implemented: 6 for database operations, 3 for service integration (9 total)
11. Migration reversible (downgrade script tested)
12. Documentation updated: README.md with Epic 4 overview, async-database-patterns.md reference

### Standard Quality & Security Criteria (Auto-included)

These criteria apply to ALL stories unless explicitly not applicable:

- **Input Validation**: All user inputs and external data validated before processing (type checking, range validation, sanitization)
- **Security Review**: No hardcoded secrets, credentials in environment variables, parameterized queries for database operations, rate limiting implemented where applicable
- **Code Quality**: No deprecated APIs used, comprehensive type hints/annotations, structured logging for debugging, error handling with proper exception types
- **Database Access**: Use ONLY async database patterns (`async with db_service.async_session()`), NO sync Session usage

## Definition of Done (DoD)

Before marking this story as "review-ready", verify ALL items are complete:

- [ ] **All acceptance criteria implemented and verified**
  - Each AC has corresponding implementation
  - Manual verification completed for each AC

- [ ] **Unit tests implemented and passing (NOT stubs)**
  - Tests cover business logic for all AC
  - No placeholder tests with `pass` statements
  - Coverage target: 80%+ for new code
  - Total: 13 tests (8 SettingsService + 5 OnboardingWizard)

- [ ] **Integration tests implemented and passing (NOT stubs)**
  - Tests cover end-to-end workflows
  - Real database/API interactions (test environment)
  - No placeholder tests with `pass` statements
  - Total: 9 tests (6 database + 3 service integration)
  - Includes 1 complete e2e test

- [ ] **Documentation complete**
  - README sections updated if applicable
  - Architecture docs updated if new patterns introduced
  - API documentation generated/updated

- [ ] **Security review passed**
  - No hardcoded credentials or secrets
  - Input validation present for all user inputs
  - SQL queries parameterized (no string concatenation)
  - OAuth tokens encrypted at rest

- [ ] **Code quality verified**
  - No deprecated APIs used
  - Type hints present (Python) or TypeScript types (JS/TS)
  - Structured logging implemented
  - Error handling comprehensive

- [ ] **Database access verified (async-only)**
  - All database operations use `async with db_service.async_session()`
  - No `Session(engine)` sync pattern usage
  - All queries use `await session.execute()` pattern

- [ ] **All task checkboxes updated**
  - Completed tasks marked with [x]
  - File List section updated with created/modified files
  - Completion Notes added to Dev Agent Record

## Tasks / Subtasks

**IMPORTANT**: Follow new task ordering pattern from Epic 2 retrospective:
- Task 1: Core implementation + unit tests (interleaved, not separate)
- Task 2: Integration tests (implemented DURING development, not after)
- Task 3: Documentation + security review
- Task 4: Final validation

### Task 1: Database Schema & Migration (AC: #1, #2, #3, #6, #11)

- [ ] **Subtask 1.1**: Create Alembic migration for all 3 tables
  - [ ] Create migration file: `backend/alembic/versions/xxxx_add_user_settings_tables.py`
  - [ ] Define UserSettings table schema (12 fields from AC #1)
  - [ ] Define FolderCategories table schema (7 fields from AC #2)
  - [ ] Define OAuthTokens table schema (6 fields from AC #3)
  - [ ] Create indexes (AC #6): idx_user_settings_user_id, idx_folder_categories_user_id, idx_oauth_tokens_user_id
  - [ ] Implement downgrade() function for rollback (AC #11)
- [ ] **Subtask 1.2**: Write unit tests for migration
  - [ ] Implement exactly 3 unit test functions:
    1. `test_migration_upgrade_creates_tables()` (AC: #1-3) - Verify all 3 tables created
    2. `test_migration_creates_indexes()` (AC: #6) - Verify all indexes created
    3. `test_migration_downgrade_removes_tables()` (AC: #11) - Verify rollback works
  - [ ] All unit tests passing (3/3)

### Task 2: SettingsService Implementation (AC: #4, #7, #8)

- [ ] **Subtask 2.1**: Create SettingsService class
  - [ ] Create file: `backend/app/services/settings_service.py`
  - [ ] Implement `get_or_create_settings(user_id)` - Returns UserSettings with defaults
  - [ ] Implement `update_notification_preferences(user_id, **kwargs)` - Updates batch_time, quiet_hours, etc.
  - [ ] Implement `create_folder_category(user_id, name, keywords, color)` - Creates FolderCategory
  - [ ] Implement `save_oauth_tokens(user_id, access_token, refresh_token, token_expiry, scope)` - Saves encrypted tokens
  - [ ] All methods use `async with db_service.async_session()` pattern (AC #7)
  - [ ] Implement token encryption using Fernet (AC #8)
  - [ ] Add comprehensive type hints and docstrings
  - [ ] Add structured logging for all operations
- [ ] **Subtask 2.2**: Write unit tests for SettingsService
  - [ ] Implement exactly 8 unit test functions:
    1. `test_get_or_create_settings_creates_new()` (AC: #4) - Verify creates with defaults
    2. `test_get_or_create_settings_returns_existing()` (AC: #4) - Verify returns existing
    3. `test_update_notification_preferences()` (AC: #4) - Verify updates batch_time
    4. `test_create_folder_category()` (AC: #4) - Verify creates folder
    5. `test_save_oauth_tokens_encrypts()` (AC: #4, #8) - Verify encryption applied
    6. `test_settings_service_uses_async_session()` (AC: #7) - Verify async pattern
    7. `test_token_encryption_decryption()` (AC: #8) - Verify encrypt/decrypt works
    8. `test_settings_validation()` (AC: #4) - Verify input validation (batch_time format, etc.)
  - [ ] Use AsyncMock for database operations
  - [ ] All unit tests passing (8/8)

### Task 3: OnboardingWizard Service Skeleton (AC: #5)

- [ ] **Subtask 3.1**: Create OnboardingWizard class
  - [ ] Create file: `backend/app/services/onboarding_wizard.py`
  - [ ] Define wizard state enum: WELCOME, GMAIL_CONNECT, TELEGRAM_CONFIRM, FOLDER_SETUP, NOTIFICATION_PREFS, COMPLETION
  - [ ] Implement `start_onboarding(user_id)` - Initialize wizard
  - [ ] Implement `resume_from_step(user_id, step)` - Resume from saved progress
  - [ ] Create skeleton methods: `send_step_1_welcome()`, `send_step_2_gmail_connection()`, etc.
  - [ ] Add state machine logic: track current step, validate transitions
  - [ ] Add comprehensive type hints and docstrings
- [ ] **Subtask 3.2**: Write unit tests for OnboardingWizard skeleton
  - [ ] Implement exactly 5 unit test functions:
    1. `test_start_onboarding_initializes_state()` (AC: #5) - Verify sets step=1
    2. `test_resume_from_step_calls_correct_method()` (AC: #5) - Verify routing works
    3. `test_wizard_state_transitions()` (AC: #5) - Verify step progression
    4. `test_onboarding_already_completed()` (AC: #5) - Verify handles completed state
    5. `test_wizard_skeleton_methods_exist()` (AC: #5) - Verify all step methods defined
  - [ ] Use AsyncMock for TelegramBotClient and SettingsService
  - [ ] All unit tests passing (5/5)

### Task 4: Integration Tests (AC: all)

**Integration Test Scope**: Implement exactly 9 integration test functions:

**IMPORTANT (Epic 3 Learning):** Include 1 end-to-end integration test validating complete flow

- [ ] **Subtask 4.1**: Database integration tests (6 tests)
  - [ ] `test_migration_upgrade_downgrade_e2e()` (AC: #1-3, #11) - Full migration cycle with real database
  - [ ] `test_settings_crud_operations()` (AC: #4, #7) - Create, read, update settings
  - [ ] `test_folder_category_crud()` (AC: #4, #7) - Create, read, update, delete folders
  - [ ] `test_oauth_tokens_encryption_e2e()` (AC: #4, #8) - Save encrypted, retrieve decrypted
  - [ ] `test_concurrent_settings_updates()` (AC: #7) - Verify async safety
  - [ ] `test_indexes_improve_query_performance()` (AC: #6) - Measure query time with/without indexes
- [ ] **Subtask 4.2**: Service integration tests (3 tests)
  - [ ] `test_settings_service_integration()` (AC: #4, #7) - SettingsService with real database
  - [ ] `test_onboarding_wizard_state_persistence()` (AC: #5) - Wizard state saved to database
  - [ ] `test_complete_onboarding_infrastructure_e2e()` (AC: all) - End-to-end: Create user → Settings → Folder → OAuth token → Resume wizard
- [ ] **Subtask 4.3**: Verify all integration tests passing (9/9)

### Task 5: Documentation + Security Review (AC: #12)

- [ ] **Subtask 5.1**: Update architecture documentation (AC #12)
  - [ ] Add implementation status to `docs/architecture.md`
    - Section: Epic 4 > Database Schema
    - Note: "Story 4.1 (Onboarding Foundation) - Completed [date]"
    - Schema diagrams for 3 new tables
  - [ ] Update `backend/README.md` with Epic 4 overview
    - New services: SettingsService, OnboardingWizard
    - Database tables: UserSettings, FolderCategories, OAuthTokens
    - Reference: `docs/async-database-patterns.md`
- [ ] **Subtask 5.2**: Security review
  - [ ] Verify ENCRYPTION_KEY in .env (not hardcoded) (AC #8)
  - [ ] Verify no OAuth tokens logged
  - [ ] Verify database queries parameterized (SQLModel handles this)
  - [ ] Verify input validation for user inputs (batch_time format, folder name length)
  - [ ] Code review: Check for SQL injection vulnerabilities

### Task 6: Final Validation (AC: all)

- [ ] **Subtask 6.1**: Run complete test suite
  - [ ] All 13 unit tests passing
  - [ ] All 9 integration tests passing
  - [ ] No test warnings or errors
  - [ ] Migration upgrade + downgrade successful
- [ ] **Subtask 6.2**: Verify DoD checklist
  - [ ] Review each DoD item
  - [ ] Update all task checkboxes
  - [ ] Update File List with created files
  - [ ] Add Completion Notes
  - [ ] Mark story as review-ready

## Dev Notes

**Relevant Architecture Patterns:**

- **Database Schema Design (ADR-018):** PostgreSQL UserSettings tables for configuration persistence. Consistent with Epic 1-3 database patterns using SQLModel + async sessions.
- **Async-Only Database Access:** ALL database operations MUST use `async with db_service.async_session()` pattern. Reference: `docs/async-database-patterns.md`
- **Token Encryption (Security):** OAuth refresh tokens encrypted at rest using `cryptography.fernet.Fernet` with ENCRYPTION_KEY from environment
- **Service Dependency Injection:** Follow Epic 1-3 pattern - services injected via constructor, not global imports
- **Structured Logging:** Use `structlog.get_logger(__name__)` for all operations, include user_id and operation context

**Source Tree Components:**

**Files to CREATE:**
- `backend/alembic/versions/xxxx_add_user_settings_tables.py` - Database migration (3 tables + indexes)
- `backend/app/models/settings.py` - SQLModel definitions (UserSettings, FolderCategory, OAuthTokens)
- `backend/app/services/settings_service.py` - Settings CRUD operations
- `backend/app/services/onboarding_wizard.py` - Wizard state machine skeleton
- `backend/tests/test_settings_service.py` - Unit tests (8 functions)
- `backend/tests/test_onboarding_wizard.py` - Unit tests (5 functions)
- `backend/tests/integration/test_settings_integration.py` - Integration tests (9 functions)

**Files to MODIFY:**
- `backend/.env.example` - Add ENCRYPTION_KEY example
- `backend/app/models/__init__.py` - Export new models
- `backend/app/services/__init__.py` - Export new services
- `backend/README.md` - Add Epic 4 section

**Testing Standards:**

- **Unit Tests:** 13 total (8 SettingsService + 5 OnboardingWizard)
  - Use `pytest.mark.asyncio` for all async tests
  - Mock database with AsyncMock
  - Test encryption/decryption separately from database operations
  - Verify async session pattern usage

- **Integration Tests:** 9 total (6 database + 3 service integration)
  - Use real PostgreSQL test database (not SQLite)
  - Test migration upgrade + downgrade with real DB
  - Verify indexes actually improve performance (measure query time)
  - Include 1 complete e2e test (Epic 3 learning)

**Service Inventory Reference:**

Before creating new services, check `docs/epic-4-service-inventory.md` for existing services.

**Epic 1-3 Services to REUSE (DO NOT recreate):**

- **DatabaseService** (Epic 1) - `backend/app/core/database.py`
  - **Apply to Story 4.1:** Use `db_service.async_session()` for all database operations
  - Method: `async_session()` - Context manager for async database sessions
  - Pattern: `async with self.db.async_session() as session:`

- **TelegramBotClient** (Epic 2) - `backend/app/core/telegram_bot.py`
  - **Apply to Story 4.1:** OnboardingWizard will use for sending messages (skeleton only, full integration in Story 4.5)
  - Methods: `send_message()`, `edit_message_text()`, inline keyboards
  - Import in OnboardingWizard constructor

### Learnings from Previous Story

**From Story 3-11-workflow-integration-and-conditional-routing (Status: done, APPROVED)**

**Services/Modules Available:**
- **ResponseGenerationService** available at `backend/app/services/response_generation.py`
  - Story 3.11 integrated into workflow with conditional routing
  - Method: `should_generate_response(email)` - Determines if email needs response
  - Method: `generate_response_draft(email_id, user_id)` - Generates AI response
  - **Note for Story 4.1:** Not directly used, but establishes pattern for service orchestration

- **Email Workflow Patterns** established in `backend/app/workflows/email_workflow.py`
  - Conditional routing pattern using `add_conditional_edges()`
  - Node dependency injection via `functools.partial`
  - State machine pattern with LangGraph
  - **Note for Story 4.1:** OnboardingWizard should follow similar state machine pattern

**Key Technical Details from Story 3.11:**
- **Async/Sync Pattern Learning:** Story 3.11 used correct async patterns throughout - maintain this in Story 4.1
- **Conditional Routing Pattern:** `route_by_classification()` function returns state value for path mapping - similar pattern can be used for wizard step transitions
- **Integration Test Pattern:** Complete e2e test (`test_complete_email_sorting_workflow`) validated entire workflow - Story 4.1 should include similar e2e test for onboarding infrastructure
- **Review Findings:** Initial implementation had path_map key mismatch bug - ensure OnboardingWizard step routing keys match function return values exactly

**Epic 3 Retrospective Learnings Applied:**
1. **Service Reuse:** Explicitly documented DatabaseService and TelegramBotClient for reuse
2. **Async-Only Database:** All database operations use `async_session()` - no sync patterns
3. **E2E Integration Test:** Story 4.1 includes complete infrastructure e2e test (Task 4, Subtask 4.2)
4. **Architecture Sync:** Task 5.1 requires updating architecture.md during implementation

[Source: docs/stories/3-11-workflow-integration-and-conditional-routing.md, docs/retrospectives/epic-3-retro-2025-11-11.md]

### Project Structure Notes

**Alignment with Epic 1-3 Structure:**
- Database models follow Epic 1 pattern: `backend/app/models/*.py` with SQLModel
- Services follow Epic 2 pattern: `backend/app/services/*.py` with dependency injection
- Tests follow Epic 3 pattern: Unit tests in `backend/tests/`, integration in `backend/tests/integration/`
- Migration files follow Epic 1 pattern: Alembic migrations in `backend/alembic/versions/`

**Database Schema Alignment:**
- UserSettings foreign key references `users.id` (Epic 1 table)
- FolderCategories will sync with Gmail labels (Story 1.8 integration point)
- OAuthTokens will be used by GmailClient (Story 1.4 integration point)

### References

- **Tech Spec:** [docs/tech-spec-epic-4.md#Database-Schema](../tech-spec-epic-4.md#database-schema) - Complete schema definitions
- **ADR-018:** [docs/adrs/epic-4-architecture-decisions.md#ADR-018](../adrs/epic-4-architecture-decisions.md#adr-018-postgresql-usersettings-table-for-configuration-persistence) - PostgreSQL UserSettings decision
- **Service Inventory:** [docs/epic-4-service-inventory.md](../epic-4-service-inventory.md) - Reusable Epic 1-3 services
- **Async Patterns:** [docs/async-database-patterns.md](../async-database-patterns.md) - Async-only database guidelines
- **Epic 3 Retrospective:** [docs/retrospectives/epic-3-retro-2025-11-11.md](../retrospectives/epic-3-retro-2025-11-11.md) - Learnings applied to Story 4.1

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

### Completion Notes List

### File List
