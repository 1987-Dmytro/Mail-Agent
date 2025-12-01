# Sprint Change Proposal: Pre-Deployment Critical Bug Fixes

**Document ID**: SCP-2025-01-18
**Created**: 2025-01-18
**Status**: PENDING APPROVAL
**Priority**: CRITICAL
**Requested By**: Dimcheg (Product Owner)
**Prepared By**: Bob (Scrum Master)

---

## Executive Summary

During pre-deployment testing, multiple critical bugs were discovered that block the core user journey. The system fails to execute the complete email processing workflow as defined in the PRD. Specifically:

1. **Post-onboarding automation does not trigger** - Users complete onboarding but no email indexing or polling starts
2. **Telegram button handlers fail** - Async/sync session mismatch causes errors
3. **Priority detection is bypassed** - Workflow node exists but is not connected
4. **Confirmation step crashes** - Sync session used in async context

These issues collectively prevent the MVP from functioning according to requirements.

---

## Change Trigger Analysis

### Trigger Type
- **Category**: Technical limitation discovered during integration testing
- **Discovery Phase**: Pre-deployment validation
- **Severity**: CRITICAL - Blocks core functionality

### Original Requirements (PRD Journey 1)

> **Step 10**: User confirms successful setup and completes onboarding
> **Step 11**: System begins monitoring Gmail inbox for new emails
> **Step 12**: Agent processes unread emails and proposes sorting
> **Step 13**: User receives Telegram message with sorting proposal
> **Step 14**: User approves/rejects via inline buttons

### Current Behavior

| Step | Expected | Actual | Status |
|------|----------|--------|--------|
| 10 | Onboarding completes | Works | ✅ |
| 11 | Indexing + polling starts | **Nothing happens** | 🔴 BROKEN |
| 12 | Emails processed | Not triggered | 🔴 BLOCKED |
| 13 | Telegram message sent | Partially works | 🟠 DEGRADED |
| 14 | Button clicks processed | **Fails silently** | 🔴 BROKEN |

---

## Detailed Bug Analysis

### BUG-1: Onboarding Does Not Trigger Backend Automation

**File**: `backend/app/api/v1/users.py`
**Function**: `complete_onboarding()` (lines 105-163)
**Severity**: 🔴 CRITICAL

#### Problem Description
The `/complete-onboarding` endpoint only sets a database flag. It does not:
- Trigger `index_user_emails.delay()` for 90-day history indexing
- Start `poll_user_emails.delay()` for inbox monitoring

#### Root Cause
Missing task queue invocations after successful onboarding completion.

#### PRD Requirement Violated
> Journey 1, Step 11: "System begins monitoring Gmail inbox for new emails"

#### Current Code (Problematic)
```python
async def complete_onboarding(current_user: User = Depends(get_current_user)):
    current_user.onboarding_completed = True
    await database_service.update_user(current_user)
    # BUG: No indexing or polling triggered here
    return {"success": True, "message": "Onboarding completed successfully"}
```

#### Proposed Fix
```python
async def complete_onboarding(current_user: User = Depends(get_current_user)):
    current_user.onboarding_completed = True
    await database_service.update_user(current_user)

    # Trigger email history indexing (90 days) - Story 3.3
    from app.tasks.indexing_tasks import index_user_emails
    index_user_emails.delay(user_id=current_user.id, days_back=90)

    # Start email polling for this user
    from app.tasks.email_tasks import poll_user_emails
    poll_user_emails.delay(user_id=current_user.id)

    logger.info("backend_automation_triggered", user_id=current_user.id)

    return {"success": True, "message": "Onboarding completed successfully"}
```

---

### BUG-2: Telegram Handler Uses Sync Session in Async Context

**File**: `backend/app/api/telegram_handlers.py`
**Function**: `handle_start_command()` (line 136)
**Severity**: 🔴 CRITICAL

#### Problem Description
The telegram handler uses synchronous `Session(engine)` inside an async function, causing:
- Blocking behavior in async context
- Potential deadlocks
- Silent failures when linking Telegram account

#### Root Cause
```python
# PROBLEMATIC CODE (line 136)
with Session(engine) as db:  # SYNC session in ASYNC function!
    result = link_telegram_account(...)  # SYNC function call
```

#### Proposed Fix
```python
# CORRECTED CODE
from app.services.database import database_service

async with database_service.async_session() as db:
    result = await link_telegram_account_async(
        telegram_id=telegram_id_str,
        telegram_username=telegram_username,
        code=code,
        db=db
    )
```

#### Additional Work Required
- Create async version of `link_telegram_account` in `telegram_linking.py`
- Or refactor existing function to accept AsyncSession

---

### BUG-3: Priority Detection Node Not Connected in Workflow

**File**: `backend/app/workflows/email_workflow.py`
**Section**: Workflow edge definitions (lines 246-264)
**Severity**: 🟠 HIGH

#### Problem Description
The `detect_priority` node is:
- ✅ Imported (line 64)
- ✅ Added as a node (line 225/237)
- ❌ **NOT connected via edges** - workflow skips it entirely

#### Current Workflow Flow (Broken)
```
extract_context → classify → [conditional_route] → send_telegram
                            ↓
                      generate_response (if needs_response)
```

#### Required Workflow Flow (Per Story 2.9)
```
extract_context → classify → detect_priority → [conditional_route] → send_telegram
                                               ↓
                                         generate_response (if needs_response)
```

#### Impact
- Priority emails (government, urgent keywords) not detected
- All emails treated with same priority
- Story 2.9 requirements not fulfilled

#### Current Code (Problematic)
```python
workflow.add_edge("extract_context", "classify")
workflow.add_conditional_edges(
    "classify",  # Routes directly from classify, skipping detect_priority
    route_by_classification,
    {...}
)
```

#### Proposed Fix
```python
workflow.add_edge("extract_context", "classify")
workflow.add_edge("classify", "detect_priority")  # ADD THIS LINE
workflow.add_conditional_edges(
    "detect_priority",  # CHANGE: Route from detect_priority
    route_by_classification,
    {...}
)
```

---

### BUG-4: send_confirmation Uses Sync Session Type

**File**: `backend/app/workflows/nodes.py`
**Function**: `send_confirmation()` (lines 1232-1413)
**Severity**: 🔴 CRITICAL

#### Problem Description
Function signature declares `db: Session` (sync) but:
- Function is `async def`
- Uses `await db.get()` which doesn't exist on sync Session
- Causes AttributeError crash at confirmation step

#### Root Cause
```python
async def send_confirmation(
    state: EmailWorkflowState,
    db: Session,  # WRONG: Should be AsyncSession
    telegram_bot_client: TelegramBotClient,
) -> EmailWorkflowState:
    ...
    user = await db.get(User, int(user_id))  # CRASH: db.get() is sync
```

#### Proposed Fix
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def send_confirmation(
    state: EmailWorkflowState,
    db: AsyncSession,  # FIXED: Use AsyncSession
    telegram_bot_client: TelegramBotClient,
) -> EmailWorkflowState:
    ...
    # Use async query pattern
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
```

#### Additional Changes Required
- Lines 1307-1309: Fix folder query (same pattern)
- Lines 1333-1335: Fix folder query (same pattern)

---

## Implementation Plan

### Phase 1: Critical Path Fixes (Immediate)

| Priority | Bug ID | Story Points | Assignee | ETA |
|----------|--------|--------------|----------|-----|
| P0 | BUG-1 | 2 | Dev | 2 hours |
| P0 | BUG-2 | 3 | Dev | 3 hours |
| P0 | BUG-4 | 2 | Dev | 2 hours |

### Phase 2: Workflow Enhancement

| Priority | Bug ID | Story Points | Assignee | ETA |
|----------|--------|--------------|----------|-----|
| P1 | BUG-3 | 1 | Dev | 1 hour |

### Total Estimated Effort
- **Story Points**: 8
- **Calendar Time**: 1 day (with testing)

---

## Testing Requirements

### Unit Tests Required
- [ ] `test_complete_onboarding_triggers_indexing`
- [ ] `test_complete_onboarding_triggers_polling`
- [ ] `test_telegram_link_async_session`
- [ ] `test_workflow_includes_detect_priority`
- [ ] `test_send_confirmation_async_session`

### Integration Tests Required
- [ ] Full onboarding → indexing → polling flow
- [ ] Telegram `/start CODE` linking flow
- [ ] Complete email workflow: extract → classify → detect → route → confirm
- [ ] Priority email detection and immediate notification

### Manual Testing Checklist
- [ ] Complete onboarding in frontend
- [ ] Verify Celery tasks triggered (check logs)
- [ ] Link Telegram via `/start CODE`
- [ ] Receive email sorting proposal in Telegram
- [ ] Click Approve/Reject buttons
- [ ] Verify confirmation message received

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Regression in existing functionality | Medium | High | Run full test suite before merge |
| Celery task failures | Low | Medium | Add monitoring alerts |
| Session handling edge cases | Low | High | Code review + integration tests |

---

## Approval Section

### Technical Review
- [ ] Code changes reviewed by senior developer
- [ ] Test coverage verified (>80% on changed files)
- [ ] No new security vulnerabilities introduced

### Product Review
- [ ] Changes align with PRD requirements
- [ ] User experience not degraded
- [ ] Rollback plan documented

---

## Signatures

| Role | Name | Approval | Date |
|------|------|----------|------|
| Scrum Master | Bob | PREPARED | 2025-01-18 |
| Product Owner | Dimcheg | PENDING | |
| Tech Lead | | PENDING | |

---

## Appendix A: File Change Summary

| File | Lines Changed | Type |
|------|---------------|------|
| `backend/app/api/v1/users.py` | +15 | Feature |
| `backend/app/api/telegram_handlers.py` | +8, -4 | Bug Fix |
| `backend/app/workflows/email_workflow.py` | +1, ~2 | Bug Fix |
| `backend/app/workflows/nodes.py` | +6, -3 | Bug Fix |
| `backend/app/services/telegram_linking.py` | +30 | New Function |

## Appendix B: Related Documentation

- PRD: `/docs/PRD.md` - Journey 1: Initial Setup and Onboarding
- Architecture: `/docs/architecture.md` - Workflow Architecture
- Epic 2 Tech Spec: `/docs/tech-spec-epic-2.md` - Telegram Integration
- Epic 3 Tech Spec: `/docs/tech-spec-epic-3.md` - Email Indexing
- Story 2.9: Priority Detection Implementation
- Story 3.3: Email History Indexing
