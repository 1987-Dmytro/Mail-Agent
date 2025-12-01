# Story 5-1: Fix Onboarding Does Not Trigger Backend Automation

**Epic:** Epic 5 - Pre-Deployment Critical Fixes
**Priority:** P0 CRITICAL
**Effort:** 2 SP (~2 hours)
**Status:** Done
**Created:** 2025-01-18
**Reference:** Sprint Change Proposal `docs/sprint-change-proposal-2025-01-18.md` - BUG-1

---

## Description

The `/complete-onboarding` endpoint only sets a database flag but does not trigger backend automation. After users complete onboarding, no email indexing or polling starts - the system remains idle.

**Root Cause:**
Missing Celery task invocations after successful onboarding completion in `backend/app/api/v1/users.py`.

**PRD Requirement Violated:**
> Journey 1, Step 11: "System begins monitoring Gmail inbox for new emails"

**User Impact:**
- Users complete onboarding wizard successfully
- Nothing happens - no emails indexed, no processing starts
- System appears broken/non-functional

---

## Acceptance Criteria

### AC 1: Indexing Task Triggered
- [ ] `index_user_emails.delay(user_id, days_back=90)` called after onboarding completion
- [ ] Task enqueued in Celery with correct parameters
- [ ] Logging confirms task was triggered

**Verification:** Check Celery worker logs after completing onboarding

### AC 2: Polling Task Triggered
- [ ] `poll_user_emails.delay(user_id)` called after onboarding completion
- [ ] Task starts monitoring user's Gmail inbox
- [ ] Logging confirms polling was started

**Verification:** Check Celery worker logs for poll_user_emails task

### AC 3: Error Handling
- [ ] If task queueing fails, endpoint still returns success (flag was set)
- [ ] Task failures logged but don't block onboarding completion
- [ ] User receives success message regardless of task queue status

**Verification:** Disconnect Redis, complete onboarding - should not crash

### AC 4: Logging
- [ ] Log entry for "indexing_task_triggered" with user_id and days_back
- [ ] Log entry for "polling_task_triggered" with user_id
- [ ] Structured logging follows existing patterns

**Verification:** Review logs after onboarding completion

---

## Technical Tasks

### Task 1: Add Task Imports
**File:** `backend/app/api/v1/users.py`

Add imports at function level to avoid circular imports:
```python
from app.tasks.indexing_tasks import index_user_emails
from app.tasks.email_tasks import poll_user_emails
```

**Checklist:**
- [x] Import added inside function (not at module level)
- [x] No circular import errors

### Task 2: Trigger Indexing Task
**File:** `backend/app/api/v1/users.py`
**Function:** `complete_onboarding()` (after line 139)

**Changes:**
```python
# After: await database_service.update_user(current_user)

# Trigger email history indexing (90 days) - Story 3.3
from app.tasks.indexing_tasks import index_user_emails
index_user_emails.delay(user_id=current_user.id, days_back=90)

logger.info(
    "indexing_task_triggered",
    user_id=current_user.id,
    days_back=90,
)
```

**Checklist:**
- [x] Task called with correct user_id
- [x] days_back=90 matches PRD requirement
- [x] Logging added

### Task 3: Trigger Polling Task
**File:** `backend/app/api/v1/users.py`
**Function:** `complete_onboarding()` (after indexing task)

**Changes:**
```python
# Start email polling for this user
from app.tasks.email_tasks import poll_user_emails
poll_user_emails.delay(user_id=current_user.id)

logger.info(
    "polling_task_triggered",
    user_id=current_user.id,
)
```

**Checklist:**
- [x] Task called with correct user_id
- [x] Logging added

### Task 4: Unit Test
**File:** `backend/tests/test_users_api.py` (new or existing)

**Test Cases:**
```python
@pytest.mark.asyncio
async def test_complete_onboarding_triggers_indexing(mock_celery):
    """Test that complete_onboarding triggers index_user_emails task."""
    # Arrange
    mock_celery.tasks['app.tasks.indexing_tasks.index_user_emails'].delay = MagicMock()

    # Act
    response = await client.post("/api/v1/users/complete-onboarding", headers=auth_headers)

    # Assert
    assert response.status_code == 200
    mock_celery.tasks['app.tasks.indexing_tasks.index_user_emails'].delay.assert_called_once()

@pytest.mark.asyncio
async def test_complete_onboarding_triggers_polling(mock_celery):
    """Test that complete_onboarding triggers poll_user_emails task."""
    # Similar pattern
```

**Checklist:**
- [x] Test indexing task is called
- [x] Test polling task is called
- [x] Test passes with mocked Celery

---

## Definition of Done

- [ ] All 4 Acceptance Criteria verified
- [ ] All 4 Technical Tasks completed
- [ ] Indexing task triggered on onboarding completion
- [ ] Polling task triggered on onboarding completion
- [ ] Unit tests pass
- [ ] No TypeScript/Python errors
- [ ] Code committed

---

## Dev Agent Record

**Context Reference:** `docs/sprint-change-proposal-2025-01-18.md`

**Implementation Priority:**
1. Task 1: Add imports
2. Task 2: Trigger indexing
3. Task 3: Trigger polling
4. Task 4: Unit tests

**Debug Log:**
- 2025-01-18: Story created from Sprint Change Proposal BUG-1
- 2025-01-18: Implemented - added task triggers to complete_onboarding endpoint with error handling
- 2025-01-18: Created test_users_api.py with 5 unit tests - all passing

**File List:**
- Modified: `backend/app/api/v1/users.py` - Added task triggers
- Created: `backend/tests/test_users_api.py` - Unit tests for onboarding
