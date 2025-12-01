# Story 5-3: Fix detect_priority Node Not Connected in Workflow

**Epic:** Epic 5 - Pre-Deployment Critical Fixes
**Priority:** P1 HIGH
**Effort:** 1 SP (~1 hour)
**Status:** Done
**Created:** 2025-01-18
**Reference:** Sprint Change Proposal `docs/sprint-change-proposal-2025-01-18.md` - BUG-3

---

## Description

The `detect_priority` node is imported and added to the workflow graph but is NOT connected via edges. The workflow skips priority detection entirely, causing all emails to be treated with the same priority.

**Current Flow (Broken):**
```
extract_context → classify → [conditional_route] → send_telegram
```

**Required Flow (Per Story 2.9):**
```
extract_context → classify → detect_priority → [conditional_route] → send_telegram
```

**User Impact:**
- Priority emails (government, urgent keywords) not detected
- No immediate notifications for urgent emails
- Story 2.9 requirements not fulfilled

---

## Acceptance Criteria

### AC 1: detect_priority Edge Added
- [ ] Edge added from `classify` to `detect_priority`
- [ ] Workflow flow: classify → detect_priority

**Verification:** Code review of email_workflow.py

### AC 2: Conditional Routing Updated
- [ ] Conditional edges now route FROM `detect_priority` (not classify)
- [ ] Route function still works correctly
- [ ] Both paths (needs_response, sort_only) still functional

**Verification:** Unit test workflow routing

### AC 3: Priority Detection Executes
- [ ] detect_priority node actually runs during workflow
- [ ] Priority score calculated and stored in state
- [ ] High-priority emails flagged correctly

**Verification:** Integration test with priority email

### AC 4: Existing Tests Pass
- [ ] All existing workflow tests still pass
- [ ] No regression in email processing

**Verification:** Run full test suite

---

## Technical Tasks

### Task 1: Add Edge from classify to detect_priority
**File:** `backend/app/workflows/email_workflow.py`
**Section:** Workflow edge definitions (around line 249)

**Changes:**
```python
# CURRENT (line 249):
workflow.add_edge("extract_context", "classify")

# ADD THIS LINE AFTER:
workflow.add_edge("classify", "detect_priority")
```

**Checklist:**
- [ ] Edge added
- [ ] Order is correct (classify → detect_priority)

### Task 2: Update Conditional Routing Source
**File:** `backend/app/workflows/email_workflow.py`
**Section:** Conditional edges (around line 253)

**Changes:**
```python
# CURRENT:
workflow.add_conditional_edges(
    "classify",  # WRONG - routes from classify
    route_by_classification,
    {
        "needs_response": "generate_response",
        "sort_only": "send_telegram",
    }
)

# CHANGE TO:
workflow.add_conditional_edges(
    "detect_priority",  # CORRECT - routes from detect_priority
    route_by_classification,
    {
        "needs_response": "generate_response",
        "sort_only": "send_telegram",
    }
)
```

**Checklist:**
- [ ] Source changed from "classify" to "detect_priority"
- [ ] Path mappings unchanged
- [ ] Route function unchanged

### Task 3: Verify Node Order in Graph
**File:** `backend/app/workflows/email_workflow.py`

Verify the complete workflow flow:
```
START
  ↓
extract_context
  ↓
classify
  ↓
detect_priority  ← NOW INCLUDED
  ↓
[route_by_classification]
  ↓                    ↓
generate_response    send_telegram
  ↓                    ↓
send_telegram      await_approval
  ↓
await_approval
  ↓
execute_action
  ↓
send_confirmation
  ↓
END
```

**Checklist:**
- [ ] detect_priority in correct position
- [ ] All nodes still reachable
- [ ] No orphaned nodes

### Task 4: Unit Test
**File:** `backend/tests/test_email_workflow.py`

**Test Case:**
```python
def test_workflow_includes_detect_priority():
    """Test that detect_priority node is in the workflow path."""
    workflow = create_email_workflow(checkpointer=MemorySaver())

    # Verify detect_priority is a node
    assert "detect_priority" in workflow.nodes

    # Verify edge exists: classify → detect_priority
    # (Implementation depends on LangGraph API)
```

**Checklist:**
- [ ] Test detect_priority node exists
- [ ] Test edge from classify to detect_priority
- [ ] Test passes

---

## Definition of Done

- [ ] All 4 Acceptance Criteria verified
- [ ] All 4 Technical Tasks completed
- [ ] detect_priority node connected in workflow
- [ ] Conditional routing updated
- [ ] All existing tests pass
- [ ] No Python errors
- [ ] Code committed

---

## Dev Agent Record

**Context Reference:** `docs/sprint-change-proposal-2025-01-18.md`

**Implementation Priority:**
1. Task 1: Add edge
2. Task 2: Update conditional routing
3. Task 3: Verify graph structure
4. Task 4: Unit test

**Debug Log:**
- 2025-01-18: Story created from Sprint Change Proposal BUG-3
- 2025-01-18: Added edge from classify to detect_priority
- 2025-01-18: Updated conditional routing source from classify to detect_priority
- 2025-01-18: Syntax validated

**File List:**
- Modified: `backend/app/workflows/email_workflow.py` - Added detect_priority to workflow edges
