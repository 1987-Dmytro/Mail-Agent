# SPRINT: Critical Fixes & Business Logic Recovery
**Sprint ID**: SPRINT-001-CRITICAL-FIXES
**Sprint Goal**: Fix critical blocking issues and restore proper business logic
**Duration**: 2 weeks (10 working days)
**Start Date**: 2025-12-02 (Monday)
**End Date**: 2025-12-13 (Friday)
**Team**: Solo Developer + Claude Code AI Assistant

---

## 🎯 SPRINT GOAL

**Primary Objective**:
Fix 6 critical blocking issues preventing production deployment and restore correct business logic in email workflow.

**Success Criteria**:
1. ✅ All 50 test emails complete workflow without blocking
2. ✅ Telegram errors handled gracefully (no workflow stops)
3. ✅ Email responses sent ONLY for needs_response classification
4. ✅ Gmail actions execute atomically with proper rollback
5. ✅ No duplicate email sends (idempotency working)
6. ✅ Services auto-start via Docker Compose

**Definition of Done**:
- All critical issues resolved and tested
- Integration tests pass (50/50 emails)
- Documentation updated
- Docker Compose deployment working
- Code reviewed and merged

---

## 📊 SPRINT BACKLOG

### EPIC 1: Workflow Error Recovery (Priority: CRITICAL)

**Total Story Points**: 13
**Estimated Time**: 20 hours

#### Story 1.1: Fix send_telegram Error Handling
**Story Points**: 5 | **Time**: 6 hours | **Priority**: P0 (CRITICAL)

**Description**:
Implement comprehensive error handling in `send_telegram` node to prevent workflow blocking when Telegram API fails.

**Acceptance Criteria**:
- [ ] Markdown symbols properly escaped using `telegram.helpers.escape_markdown`
- [ ] Fallback to plain text if MarkdownV2 fails
- [ ] Fallback to manual notification queue if Telegram API unreachable
- [ ] Workflow CONTINUES even if Telegram fails
- [ ] Error logged with full context for debugging
- [ ] State includes `telegram_notification_failed` flag when fallback used

**Technical Tasks**:
- [ ] Add `escape_markdown()` utility function
- [ ] Implement try/except with TelegramMarkdownError handler
- [ ] Implement try/except with TelegramAPIError handler
- [ ] Create `create_manual_notification_task()` function
- [ ] Add fallback state tracking
- [ ] Update tests to verify fallback behavior

**Files to Modify**:
- `app/workflows/nodes.py:446` (send_telegram function)
- `app/core/telegram_bot.py:200` (send_message_with_buttons)
- `app/models/manual_notification.py` (new model)

**Testing**:
- Unit test: Telegram markdown error → plain text fallback
- Unit test: Telegram API error → manual queue + continue
- Integration test: Email #24 (problematic markdown) completes workflow

---

#### Story 1.2: Add Conditional Routing After await_approval
**Story Points**: 3 | **Time**: 5 hours | **Priority**: P1 (CRITICAL)

**Description**:
Implement conditional routing after `await_approval` to ensure `send_email_response` only executes for `needs_response` + approved emails.

**Acceptance Criteria**:
- [ ] New routing function `route_after_approval()` created
- [ ] Routes `needs_response + approved` → `send_email_response`
- [ ] Routes `sort_only + approved` → `execute_action` (skip send)
- [ ] Routes `rejected` → `send_confirmation` (skip all)
- [ ] Routes `folder_changed` → `execute_action` with new folder
- [ ] Integration test: sort_only email does NOT send response

**Technical Tasks**:
- [ ] Create `route_after_approval()` function in email_workflow.py
- [ ] Replace `workflow.add_edge()` with `workflow.add_conditional_edges()`
- [ ] Add path mapping for 3 routes
- [ ] Update workflow diagram documentation
- [ ] Add logging for routing decisions

**Files to Modify**:
- `app/workflows/email_workflow.py:288-293` (replace edge with conditional)
- `app/workflows/email_workflow.py:86` (add new routing function)

**Testing**:
- Unit test: needs_response + approved → send_email_response
- Unit test: sort_only + approved → execute_action
- Integration test: sort_only email skips email sending

---

#### Story 1.3: Implement Atomic Transactions for Gmail Actions
**Story Points**: 5 | **Time**: 6 hours | **Priority**: P1 (CRITICAL)

**Description**:
Wrap Gmail label application and database updates in atomic transaction with exponential backoff retry.

**Acceptance Criteria**:
- [ ] Gmail modify_message + database update in single transaction
- [ ] Exponential backoff retry (3 attempts: 1s, 2s, 4s)
- [ ] Rollback database status to "failed" if all retries fail
- [ ] Continue workflow to send failure confirmation
- [ ] No partial states (either both succeed or both fail)
- [ ] Error details logged for debugging

**Technical Tasks**:
- [ ] Wrap `execute_action` node logic in retry loop
- [ ] Implement exponential backoff (2^attempt seconds)
- [ ] Add transaction rollback on failure
- [ ] Update database status atomically with Gmail action
- [ ] Add `action_failed` state flag
- [ ] Create Dead Letter Queue record for failures

**Files to Modify**:
- `app/workflows/nodes.py:execute_action` (entire function rewrite)
- `app/models/dead_letter_queue.py` (new model)

**Testing**:
- Unit test: Gmail API success → database updated
- Unit test: Gmail API failure → database rollback, retry triggered
- Integration test: Gmail 503 error → 3 retries → DLQ record

---

### EPIC 2: Data Consistency & Reliability (Priority: HIGH)

**Total Story Points**: 8
**Estimated Time**: 12 hours

#### Story 2.1: Implement Idempotency for send_email_response
**Story Points**: 3 | **Time**: 4 hours | **Priority**: P2 (HIGH)

**Description**:
Add idempotency checks to prevent duplicate email sends when workflow is retried.

**Acceptance Criteria**:
- [ ] Check `EmailProcessingQueue.email_sent_at` before sending
- [ ] Skip send if already sent, log warning
- [ ] Set `email_sent_at` timestamp after successful send
- [ ] Use Gmail threading (In-Reply-To, References headers)
- [ ] Idempotency key based on email_id + timestamp

**Technical Tasks**:
- [ ] Add database check for `email_sent_at IS NOT NULL`
- [ ] Add `email_sent_at` column if missing (migration)
- [ ] Update send logic to set timestamp atomically
- [ ] Add Gmail threading headers
- [ ] Add idempotency logging

**Files to Modify**:
- `app/workflows/nodes.py:send_email_response`
- `alembic/versions/XXX_add_email_sent_at.py` (migration)

**Testing**:
- Unit test: Second send attempt → skip, return state
- Integration test: Workflow retry → no duplicate email

---

#### Story 2.2: Fix Indexing Failure Recovery
**Story Points**: 3 | **Time**: 5 hours | **Priority**: P2 (HIGH)

**Description**:
Change indexing status from FAILED → RATE_LIMITED and schedule automatic retry task.

**Acceptance Criteria**:
- [ ] Gemini rate limit → status = "RATE_LIMITED"
- [ ] Store `retry_after` timestamp from Gemini response
- [ ] Schedule `resume_user_indexing` Celery task with countdown
- [ ] Indexing resumes from last checkpoint (processed_count)
- [ ] Max 5 retry attempts before permanent failure
- [ ] Admin notification on permanent failure

**Technical Tasks**:
- [ ] Add `retry_after` and `retry_count` columns to indexing_progress
- [ ] Update error handling in `process_batch()`
- [ ] Create `resume_user_indexing` Celery task
- [ ] Implement checkpoint resume logic
- [ ] Add retry limit check (max 5)

**Files to Modify**:
- `app/services/email_indexing.py:process_batch`
- `app/tasks/indexing_tasks.py:resume_user_indexing` (new task)
- `alembic/versions/XXX_add_indexing_retry.py` (migration)

**Testing**:
- Unit test: Rate limit → RATE_LIMITED status, task scheduled
- Integration test: Indexing resumes from checkpoint after 60s

---

#### Story 2.3: Implement Batching for Non-Priority Emails
**Story Points**: 2 | **Time**: 3 hours | **Priority**: P3 (MEDIUM)

**Description**:
Queue non-priority emails (score < 70) for daily batch digest instead of immediate Telegram send.

**Acceptance Criteria**:
- [ ] Priority check: score >= 70 → immediate, < 70 → batch
- [ ] Batched emails stored in `batch_queue` table
- [ ] Daily digest Celery task sends at 9:00 AM
- [ ] Digest includes all pending emails with inline buttons
- [ ] Workflow ENDS for batched emails (skip await_approval)
- [ ] User can configure batch time in settings

**Technical Tasks**:
- [ ] Create `batch_queue` model and table
- [ ] Add priority check in `send_telegram` node
- [ ] Create `queue_for_daily_batch()` function
- [ ] Create `send_daily_digest` Celery task
- [ ] Add Celery Beat schedule for daily digest
- [ ] Update workflow to END early for batched emails

**Files to Modify**:
- `app/workflows/nodes.py:send_telegram` (add priority check)
- `app/models/batch_queue.py` (new model)
- `app/tasks/telegram_batch.py` (new task)
- `app/celery.py` (add Beat schedule)

**Testing**:
- Unit test: Priority 50 → queued for batch
- Unit test: Priority 80 → sent immediately
- Integration test: Daily digest sends 10 batched emails

---

### EPIC 3: Infrastructure & DevOps (Priority: HIGH)

**Total Story Points**: 5
**Estimated Time**: 8 hours

#### Story 3.1: Implement Docker Compose Auto-Start
**Story Points**: 3 | **Time**: 5 hours | **Priority**: P1 (CRITICAL)

**Description**:
Create Docker Compose configuration for automatic service orchestration.

**Acceptance Criteria**:
- [ ] docker-compose.yml defines 5 services: backend, celery, celery-beat, redis, postgres
- [ ] All services restart automatically (`restart: always`)
- [ ] Health checks configured for all services
- [ ] Environment variables loaded from .env file
- [ ] Volume mounts for persistent data (postgres, redis, chromadb)
- [ ] `docker-compose up -d` starts all services correctly
- [ ] Services communicate via Docker network

**Technical Tasks**:
- [ ] Create `docker-compose.yml` in project root
- [ ] Create `Dockerfile` for backend service
- [ ] Create `.dockerignore` file
- [ ] Add health check endpoints to backend
- [ ] Configure Redis persistence (AOF + RDB)
- [ ] Configure PostgreSQL initialization scripts
- [ ] Add docker-compose documentation to README

**Files to Create**:
- `docker-compose.yml`
- `Dockerfile`
- `.dockerignore`
- `docker/postgres/init.sql`
- `docs/deployment/docker-compose-guide.md`

**Testing**:
- Manual test: `docker-compose up -d` → all services running
- Manual test: System reboot → services auto-restart
- Manual test: Health checks return 200 OK

---

#### Story 3.2: Add Monitoring & Alerting
**Story Points**: 2 | **Time**: 3 hours | **Priority**: P3 (MEDIUM)

**Description**:
Implement basic health checks and error alerting via Telegram.

**Acceptance Criteria**:
- [ ] `/health` endpoint shows all service statuses
- [ ] Celery worker health check (ping task)
- [ ] Database connection health check
- [ ] Redis connection health check
- [ ] Critical errors send Telegram alert to admin
- [ ] Daily summary report sent to admin

**Technical Tasks**:
- [ ] Extend `/api/v1/health` endpoint
- [ ] Add `ping` Celery task for health check
- [ ] Create `send_admin_alert()` utility
- [ ] Add error middleware to capture critical exceptions
- [ ] Create daily summary Celery task

**Files to Modify**:
- `app/api/v1/health.py` (extend endpoint)
- `app/utils/alerting.py` (new module)
- `app/tasks/monitoring.py` (new tasks)

**Testing**:
- Unit test: Health endpoint returns correct status
- Integration test: Critical error → admin alert sent

---

## 📅 SPRINT TIMELINE

### Week 1: Critical Workflow Fixes

#### Day 1 (Mon 12/02) - Story 1.1
**Focus**: Fix send_telegram error handling

- [ ] 09:00-10:00: Sprint planning meeting
- [ ] 10:00-12:00: Implement escape_markdown + fallbacks
- [ ] 12:00-13:00: Lunch
- [ ] 13:00-15:00: Create manual_notification model + queue
- [ ] 15:00-17:00: Write unit tests
- [ ] 17:00-17:30: Daily standup (record progress)

**Deliverable**: send_telegram handles all errors gracefully

---

#### Day 2 (Tue 12/03) - Story 1.1 (cont.) + 1.2
**Focus**: Complete Story 1.1, start conditional routing

- [ ] 09:00-11:00: Integration testing (email #24 test)
- [ ] 11:00-13:00: Story 1.2 - Create route_after_approval()
- [ ] 13:00-14:00: Lunch
- [ ] 14:00-16:00: Replace edges with conditional routing
- [ ] 16:00-17:00: Unit tests for routing
- [ ] 17:00-17:30: Daily standup

**Deliverable**: Conditional routing implemented

---

#### Day 3 (Wed 12/04) - Story 1.2 (cont.) + 1.3
**Focus**: Complete routing, start atomic transactions

- [ ] 09:00-10:00: Integration test for routing
- [ ] 10:00-12:00: Story 1.3 - Implement retry loop
- [ ] 12:00-13:00: Lunch
- [ ] 13:00-15:00: Add exponential backoff
- [ ] 15:00-17:00: Create DLQ model + rollback logic
- [ ] 17:00-17:30: Daily standup

**Deliverable**: Atomic transactions implemented

---

#### Day 4 (Thu 12/05) - Story 1.3 (cont.) + 2.1
**Focus**: Complete transactions, start idempotency

- [ ] 09:00-11:00: Unit tests for atomic transactions
- [ ] 11:00-13:00: Story 2.1 - Add email_sent_at checks
- [ ] 13:00-14:00: Lunch
- [ ] 14:00-16:00: Database migration + timestamp logic
- [ ] 16:00-17:00: Unit tests for idempotency
- [ ] 17:00-17:30: Daily standup

**Deliverable**: Idempotency working

---

#### Day 5 (Fri 12/06) - Story 2.2
**Focus**: Fix indexing recovery

- [ ] 09:00-11:00: Add retry_after + retry_count columns
- [ ] 11:00-13:00: Implement resume_user_indexing task
- [ ] 13:00-14:00: Lunch
- [ ] 14:00-16:00: Checkpoint resume logic
- [ ] 16:00-17:00: Unit tests
- [ ] 17:00-17:30: Weekly review + retrospective

**Deliverable**: Indexing auto-recovers from rate limits

---

### Week 2: Infrastructure & Testing

#### Day 6 (Mon 12/09) - Story 3.1
**Focus**: Docker Compose setup

- [ ] 09:00-11:00: Create docker-compose.yml
- [ ] 11:00-13:00: Create Dockerfile + .dockerignore
- [ ] 13:00-14:00: Lunch
- [ ] 14:00-16:00: Configure health checks + volumes
- [ ] 16:00-17:00: Test `docker-compose up -d`
- [ ] 17:00-17:30: Daily standup

**Deliverable**: Docker Compose working

---

#### Day 7 (Tue 12/10) - Story 2.3
**Focus**: Batching for non-priority emails

- [ ] 09:00-11:00: Create batch_queue model
- [ ] 11:00-13:00: Implement queue_for_daily_batch()
- [ ] 13:00-14:00: Lunch
- [ ] 14:00-16:00: Create send_daily_digest task
- [ ] 16:00-17:00: Unit tests
- [ ] 17:00-17:30: Daily standup

**Deliverable**: Batching implemented

---

#### Day 8 (Wed 12/11) - Story 3.2
**Focus**: Monitoring & alerting

- [ ] 09:00-11:00: Extend /health endpoint
- [ ] 11:00-13:00: Create admin alert utility
- [ ] 13:00-14:00: Lunch
- [ ] 14:00-16:00: Daily summary task
- [ ] 16:00-17:00: Unit tests
- [ ] 17:00-17:30: Daily standup

**Deliverable**: Monitoring functional

---

#### Day 9 (Thu 12/12) - Integration Testing
**Focus**: End-to-end testing

- [ ] 09:00-11:00: Run full workflow test (50 emails)
- [ ] 11:00-13:00: Fix any failures found
- [ ] 13:00-14:00: Lunch
- [ ] 14:00-16:00: Load testing (100 emails)
- [ ] 16:00-17:00: Performance optimization
- [ ] 17:00-17:30: Daily standup

**Deliverable**: All integration tests pass

---

#### Day 10 (Fri 12/13) - Documentation & Review
**Focus**: Sprint closure

- [ ] 09:00-11:00: Update documentation
- [ ] 11:00-13:00: Code review & cleanup
- [ ] 13:00-14:00: Lunch
- [ ] 14:00-15:00: Create deployment guide
- [ ] 15:00-17:00: Sprint review & retrospective
- [ ] 17:00-17:30: Plan next sprint

**Deliverable**: Sprint complete, ready for deployment

---

## 📈 PROGRESS TRACKING

### Daily Standup Template

**Date**: _______
**Completed Today**:
- [ ] Task 1
- [ ] Task 2

**Blocked/Issues**:
- Issue 1: [description]

**Tomorrow's Plan**:
- [ ] Task 1
- [ ] Task 2

**Burndown**: __ story points remaining

---

## 🎯 SUCCESS METRICS

### Velocity Tracking
- **Planned Velocity**: 26 story points
- **Completed Velocity**: ___ story points
- **Velocity %**: ___ %

### Quality Metrics
- **Test Coverage**: Target 80%+
- **Bug Count**: Target 0 critical bugs
- **Code Review**: 100% reviewed

### Business Metrics
- **Workflow Completion Rate**: Target 100% (50/50 emails)
- **Error Rate**: Target <1%
- **Average Processing Time**: Target <30s per email

---

## 🚧 RISKS & MITIGATION

### Risk 1: Telegram API Rate Limiting
**Likelihood**: Medium | **Impact**: Medium
**Mitigation**: Implement request queuing, use exponential backoff

### Risk 2: Database Migration Failures
**Likelihood**: Low | **Impact**: High
**Mitigation**: Test migrations on staging first, have rollback script ready

### Risk 3: Docker Compose Complexity
**Likelihood**: Medium | **Impact**: Medium
**Mitigation**: Start simple, add features incrementally, document thoroughly

### Risk 4: Scope Creep
**Likelihood**: Medium | **Impact**: High
**Mitigation**: Strict adherence to sprint backlog, no new features mid-sprint

---

## 📋 DEFINITION OF DONE

### Code Level
- [ ] Code written and tested locally
- [ ] Unit tests written (80%+ coverage)
- [ ] Integration tests pass
- [ ] No lint errors or warnings
- [ ] Code reviewed by peer (or AI assistant)

### Documentation Level
- [ ] Inline code comments added
- [ ] README updated (if needed)
- [ ] API documentation updated (if needed)
- [ ] Deployment guide updated

### System Level
- [ ] All acceptance criteria met
- [ ] Manual testing completed
- [ ] Performance acceptable (<30s per email)
- [ ] No regressions introduced
- [ ] Deployed to staging environment
- [ ] Product owner approval (or self-approval with checklist)

---

## 📊 SPRINT RETROSPECTIVE (to be filled at end)

### What Went Well
-

### What Could Be Improved
-

### Action Items for Next Sprint
-

---

**Sprint Status**: 🟡 PLANNED (Not Started)
**Last Updated**: 2025-11-30
**Next Review**: 2025-12-06 (End of Week 1)
