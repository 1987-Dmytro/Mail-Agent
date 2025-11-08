# Epic Technical Specification: AI Sorting Engine & Telegram Approval

Date: 2025-11-06
Author: Dimcheg
Epic ID: 2
Status: Draft

---

## Overview

Epic 2 implements the AI-powered email classification system and human-in-the-loop approval workflow via Telegram, delivering the first major user-facing value proposition of Mail Agent. This epic integrates Google Gemini 2.5 Flash LLM for intelligent email categorization, introduces the novel **TelegramHITLWorkflow** pattern using LangGraph state machines with PostgreSQL checkpointing for cross-channel workflow resumption, and establishes the Telegram bot interface for mobile-first user approvals. The implementation builds on the Gmail integration foundation from Epic 1, adding AI classification service, priority email detection, batch notification system, and complete approval tracking. By completing this epic, users receive Telegram notifications about incoming emails with AI-generated sorting proposals, approve or reject suggestions via interactive inline buttons, and have emails automatically organized into Gmail folders—demonstrating the core "AI + human control" paradigm that defines Mail Agent's value proposition of reducing email management time by 60-75%.

## Objectives and Scope

**In Scope:**
- Google Gemini 2.5 Flash LLM integration with structured JSON output parsing
- Email classification prompt engineering for folder categorization across 4 languages (Russian, Ukrainian, English, German)
- AI email classification service integrating with email processing queue
- LangGraph state machine workflow (EmailWorkflow) with PostgreSQL checkpointing for pause/resume
- WorkflowMapping database table for Telegram callback → workflow instance reconnection
- Telegram bot foundation using python-telegram-bot library (long polling mode)
- User-Telegram account linking via 6-digit codes (LinkingCodes table)
- Telegram approval message templates with inline keyboards ([Approve] [Change Folder] [Reject])
- Telegram callback handlers for button interactions with workflow resumption
- Batch notification system (configurable daily scheduling, default: end of day)
- Priority email detection (government domains, urgency keywords) with immediate notification bypass
- Approval history tracking (ApprovalHistory table) for user decisions
- Error handling and retry mechanisms for Gmail API, Gemini API, and Telegram API failures
- End-to-end integration testing for complete sorting → approval → execution flow

**Out of Scope:**
- RAG system and response generation (Epic 3)
- Vector database and embedding service (Epic 3)
- Frontend configuration UI (Epic 4)
- Multi-language UI localization (Telegram messages in English only for MVP)
- Advanced notification scheduling (quiet hours, custom batch times - defer to Epic 4 settings)
- Telegram webhook mode (using long polling for MVP simplicity)
- Machine learning from user corrections (post-MVP adaptive learning)

## System Architecture Alignment

This epic implements the AI classification and approval workflow layer of the Mail Agent architecture as defined in `architecture.md`. Key alignment points:

**LangGraph State Machine Workflow (Novel TelegramHITLWorkflow Pattern):**
- Implements `EmailWorkflow` state machine with nodes: extract_context → classify → send_telegram → await_approval → execute_action → send_confirmation
- Uses PostgreSQL checkpointing (PostgresSaver.from_conn_string) for persistent workflow state across service restarts
- `await_approval` node pauses workflow indefinitely, waiting for Telegram callback from separate channel
- Thread ID format: `email_{email_id}_{uuid4()}` for unique workflow instance tracking
- Enables cross-channel resumption: workflow pauses in backend, user responds hours later in Telegram app

**WorkflowMapping Table (Novel Pattern):**
- Maps `email_id` → `thread_id` (LangGraph) → `telegram_message_id` for callback reconnection
- Critical for resuming correct workflow instance when user clicks Telegram button
- Schema: `email_id` (unique), `user_id`, `thread_id` (unique), `telegram_message_id`, `workflow_state`, timestamps
- Indexed on `thread_id` and `(user_id, workflow_state)` for fast lookups

**Gemini API Integration (ADR-008):**
- Model: `gemini-2.5-flash` for classification (free tier: 1M tokens/minute)
- Structured output: JSON mode with schema validation (`{"suggested_folder": str, "reasoning": str}`)
- Multilingual capability: Native support for Russian, Ukrainian, English, German
- Token usage tracking via Langfuse integration (inherited from template)

**Telegram Bot Integration:**
- Library: `python-telegram-bot` (official Python library)
- Mode: Long polling (getUpdates) for MVP simplicity (webhooks deferred to production scaling)
- Callback data format: `{action}_{email_id}` (e.g., `approve_123`, `reject_456`, `change_789`)
- Message format: Markdown with inline keyboards, priority indicators (⚠️ emoji)

**Database Schema Extensions:**
- `LinkingCodes` table: User-Telegram account linking with expiration (15 minutes)
- `WorkflowMapping` table: LangGraph thread tracking (new pattern)
- `ApprovalHistory` table: User decision tracking for accuracy monitoring
- `NotificationPreferences` table: Batch timing configuration per user
- `EmailProcessingQueue` extensions: `classification` (sort_only/needs_response), `proposed_folder_id`, `priority_score` fields

**Components Created:**
- `app/workflows/email_workflow.py` - LangGraph state machine (EmailWorkflow)
- `app/workflows/states.py` - TypedDict state definitions
- `app/workflows/nodes.py` - Workflow node implementations
- `app/core/telegram_bot.py` - Telegram bot client wrapper
- `app/core/llm_client.py` - Gemini API wrapper
- `app/services/classification.py` - AI email classification service
- `app/services/priority_detection.py` - Government email & urgency detection
- `app/models/workflow_mapping.py`, `linking_codes.py`, `approval_history.py` - New database models
- `app/tasks/notification_tasks.py` - Batch notification Celery tasks

**NFR Alignment:**
- NFR001 (Performance): Email processing → Telegram notification < 2 minutes (polling: 2 min + classification: ~3-5 sec + Telegram send: ~1 sec)
- NFR002 (Reliability): Workflow checkpointing ensures zero data loss, retry logic for all external APIs
- NFR004 (Security): Telegram bot token stored in environment variable, callback data validated (user owns email)
- NFR005 (Usability): Telegram linking code generation (<30 seconds), inline buttons for mobile-first approval

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner/Location |
|---------------|----------------|--------|---------|----------------|
| **LLMClient** | Gemini API wrapper for classification and generation | Prompt text, model config, JSON schema | LLM response (JSON parsed) | `app/core/llm_client.py` |
| **TelegramBotClient** | Telegram Bot API wrapper for messaging and callbacks | Message text, user ID, inline keyboard | Message ID, callback query | `app/core/telegram_bot.py` |
| **EmailClassificationService** | AI-powered email categorization | Email content, user folders | Classification result (folder, reasoning) | `app/services/classification.py` |
| **PriorityDetectionService** | Government/urgent email detection | Email metadata (sender, subject, content) | Priority score (0-100) | `app/services/priority_detection.py` |
| **WorkflowInstanceTracker** | LangGraph workflow lifecycle management | Email data, user decision | Workflow thread_id, completion status | `app/services/workflow_tracker.py` |
| **TelegramLinkingService** | User-Telegram account linking | User ID | 6-digit linking code | `app/services/telegram_linking.py` |
| **ApprovalHandlerService** | Process Telegram button callbacks | Callback data, user decision | Workflow resumption result | `app/services/approval_handler.py` |
| **BatchNotificationService** | Daily batch notification orchestration | Scheduled trigger | Telegram messages sent count | `app/services/batch_notification.py` |
| **EmailWorkflow (LangGraph)** | State machine for email processing with HITL | Email metadata | Completed action result | `app/workflows/email_workflow.py` |

### Data Models and Contracts

**WorkflowMapping Table (Novel Pattern - Story 2.6):**
```python
class WorkflowMapping(Base):
    """Maps email processing to LangGraph workflow instances and Telegram messages"""
    __tablename__ = "workflow_mappings"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("email_processing_queue.id", ondelete="CASCADE"),
                      unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(String(255), unique=True, nullable=False, index=True)  # LangGraph thread ID
    telegram_message_id = Column(String(100), nullable=True)  # Set after message sent
    workflow_state = Column(String(50), nullable=False, default="initialized")
    # States: initialized, awaiting_approval, completed, error
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    email = relationship("EmailProcessingQueue", backref="workflow_mapping")
    user = relationship("User")

    __table_args__ = (
        Index('idx_workflow_mappings_thread_id', 'thread_id'),
        Index('idx_workflow_mappings_user_state', 'user_id', 'workflow_state'),
    )
```

**LinkingCodes Table (Story 2.5):**
```python
class LinkingCode(Base):
    """Temporary codes for linking Telegram accounts to users"""
    __tablename__ = "linking_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(6), unique=True, nullable=False, index=True)  # e.g., "A3B7X9"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 15 minutes from creation
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", backref="linking_codes")
```

**ApprovalHistory Table (Story 2.10):**
```python
class ApprovalHistory(Base):
    """Tracks user approval decisions for accuracy monitoring"""
    __tablename__ = "approval_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email_queue_id = Column(Integer, ForeignKey("email_processing_queue.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String(50), nullable=False)  # approve, reject, change_folder
    ai_suggested_folder_id = Column(Integer, ForeignKey("folder_categories.id", ondelete="SET NULL"), nullable=True)
    user_selected_folder_id = Column(Integer, ForeignKey("folder_categories.id", ondelete="SET NULL"), nullable=True)
    approved = Column(Boolean, nullable=False)  # True for approve/change, False for reject
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Relationships
    user = relationship("User")
    email = relationship("EmailProcessingQueue")
    ai_suggested_folder = relationship("FolderCategory", foreign_keys=[ai_suggested_folder_id])
    user_selected_folder = relationship("FolderCategory", foreign_keys=[user_selected_folder_id])

    __table_args__ = (
        Index('idx_approval_history_user_timestamp', 'user_id', 'timestamp'),
    )
```

**NotificationPreferences Table (Story 2.8):**
```python
class NotificationPreferences(Base):
    """User notification settings for batch timing"""
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    batch_enabled = Column(Boolean, default=True, nullable=False)
    batch_time = Column(Time, default=time(18, 0), nullable=False)  # Default: 6 PM
    priority_immediate = Column(Boolean, default=True, nullable=False)  # Bypass batch for priority
    quiet_hours_start = Column(Time, nullable=True)  # e.g., 22:00 (10 PM)
    quiet_hours_end = Column(Time, nullable=True)    # e.g., 08:00 (8 AM)
    timezone = Column(String(50), default="UTC", nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="notification_prefs")
```

**EmailProcessingQueue Extensions (Epic 2 Fields):**
```python
# Added to existing EmailProcessingQueue model from Epic 1
class EmailProcessingQueue(Base):
    # ... existing fields from Epic 1 ...

    # NEW Epic 2 fields:
    classification = Column(String(50), nullable=True)  # "sort_only" or "needs_response"
    proposed_folder_id = Column(Integer, ForeignKey("folder_categories.id", ondelete="SET NULL"), nullable=True)
    classification_reasoning = Column(Text, nullable=True)  # AI reasoning for transparency
    priority_score = Column(Integer, default=0, nullable=False)  # 0-100 scale
    is_priority = Column(Boolean, default=False, nullable=False)  # priority_score >= 70
```

**EmailWorkflowState (TypedDict for LangGraph - Story 2.3):**
```python
from typing import TypedDict, Literal

class EmailWorkflowState(TypedDict):
    """State definition for EmailWorkflow LangGraph state machine"""
    email_id: str
    user_id: str
    thread_id: str  # LangGraph thread ID
    email_content: str
    sender: str
    subject: str
    classification: Literal["sort_only", "needs_response"] | None
    proposed_folder: str | None
    classification_reasoning: str | None
    priority_score: int
    user_decision: Literal["approve", "reject", "change_folder"] | None
    selected_folder: str | None  # For change_folder action
    final_action: str | None
    error_message: str | None
```

**Gemini Classification Response Schema (Story 2.2):**
```json
{
  "suggested_folder": "Government",
  "reasoning": "Email from Finanzamt (Tax Office) regarding tax documents deadline",
  "priority_score": 85,
  "confidence": 0.92
}
```

### APIs and Interfaces

**Telegram Linking Endpoints:**

**POST /api/v1/telegram/generate-code** (Story 2.5)
- Purpose: Generate unique 6-digit linking code for Telegram account connection
- Authentication: JWT Bearer token (authenticated user)
- Request:
```json
{}
```
- Response (201 Created):
```json
{
  "success": true,
  "data": {
    "code": "A3B7X9",
    "expires_at": "2025-11-06T12:30:00Z",
    "bot_username": "MailAgentBot",
    "instructions": "Open Telegram, search for @MailAgentBot, and send: /start A3B7X9"
  }
}
```

**GET /api/v1/telegram/status** (Story 2.5)
- Purpose: Check if user's Telegram account is linked
- Authentication: JWT Bearer token
- Response (200 OK):
```json
{
  "success": true,
  "data": {
    "linked": true,
    "telegram_id": "123456789",
    "telegram_username": "@dimcheg",
    "linked_at": "2025-11-05T10:00:00Z"
  }
}
```

**Testing & Monitoring Endpoints:**

**POST /api/v1/test/gemini** (Story 2.1)
- Purpose: Test Gemini API connectivity and response
- Authentication: JWT Bearer token
- Request:
```json
{
  "prompt": "Classify this email: From finanzamt@berlin.de Subject: Tax deadline"
}
```
- Response (200 OK):
```json
{
  "success": true,
  "data": {
    "response": {
      "suggested_folder": "Government",
      "reasoning": "Official tax office communication",
      "priority_score": 85
    },
    "tokens_used": 42,
    "latency_ms": 1850
  }
}
```

**POST /api/v1/test/telegram** (Story 2.4)
- Purpose: Send test message to user's Telegram
- Authentication: JWT Bearer token
- Request:
```json
{
  "message": "Test notification from Mail Agent"
}
```
- Response (200 OK):
```json
{
  "success": true,
  "data": {
    "message_id": "12345",
    "sent_at": "2025-11-06T12:00:00Z"
  }
}
```

**GET /api/v1/stats/approvals** (Story 2.10)
- Purpose: Get user's approval history statistics
- Authentication: JWT Bearer token
- Query Parameters: `?from=2025-11-01&to=2025-11-30`
- Response (200 OK):
```json
{
  "success": true,
  "data": {
    "total_decisions": 150,
    "approved": 120,
    "rejected": 20,
    "folder_changed": 10,
    "approval_rate": 0.80,
    "top_folders": [
      {"name": "Government", "count": 45},
      {"name": "Clients", "count": 35}
    ]
  }
}
```

**Telegram Bot Commands & Callbacks:**

**Bot Command: /start [code]** (Story 2.5)
- Purpose: Link Telegram account using generated code
- Example: `/start A3B7X9`
- Response: "✅ Your Telegram account has been linked successfully! You'll receive email notifications here."

**Bot Command: /help**
- Response: Instructions for using the bot and available commands

**Callback Data Format (Story 2.7):**
```
approve_{email_id}       → Approve AI suggestion
reject_{email_id}        → Reject email processing
change_{email_id}        → Show folder selection menu
select_folder_{folder_id}_{email_id} → Apply selected folder
```

**Example Callback Handler Flow:**
```python
# User clicks [Approve] button
callback_data = "approve_123"
action, email_id = callback_data.split("_")  # ("approve", "123")

# Lookup workflow instance
workflow_mapping = db.query(WorkflowMapping).filter_by(email_id=email_id).first()
thread_id = workflow_mapping.thread_id

# Resume LangGraph workflow with user decision
workflow = create_email_workflow()
config = {"configurable": {"thread_id": thread_id}}
result = await workflow.ainvoke({"user_decision": "approve"}, config=config)

# Send confirmation
await bot.send_message(user_id, "✅ Email sorted to Government folder!")
```

### Workflows and Sequencing

**EmailWorkflow LangGraph State Machine (Story 2.3, 2.6, 2.7):**

```
┌─────────────────────────────────────────────────────────────────────┐
│               EmailWorkflow State Machine Flow                      │
└─────────────────────────────────────────────────────────────────────┘

NEW EMAIL DETECTED (EmailPollingTask)
    │
    ↓
┌──────────────────────────────────────┐
│ START: Initialize Workflow           │
│ - Generate thread_id                 │
│ - Create EmailWorkflowState          │
│ - Create WorkflowMapping record      │
└──────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────┐
│ NODE: extract_context                │
│ - Load email from Gmail              │
│ - Extract sender, subject, body      │
│ - Load user's folder categories      │
└──────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────┐
│ NODE: classify                       │
│ - Call Gemini API with prompt        │
│ - Parse JSON response                │
│ - Store: proposed_folder, reasoning  │
│ - Determine: sort_only or needs_response │
└──────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────┐
│ NODE: detect_priority                │
│ - Check sender domain (government?)  │
│ - Check subject keywords (urgent?)   │
│ - Calculate priority_score (0-100)   │
│ - Set is_priority flag if >= 70     │
└──────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────┐
│ NODE: send_telegram                  │
│ - Format message (sender, subject)   │
│ - Add AI reasoning                   │
│ - Create inline keyboard buttons     │
│ - Send to user's Telegram           │
│ - Store telegram_message_id          │
└──────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────┐
│ NODE: await_approval                 │
│ ⚠️  WORKFLOW PAUSES HERE             │
│ - State saved to PostgreSQL          │
│ - Workflow instance marked awaiting  │
│ - Returns (no further nodes)         │
└──────────────────────────────────────┘
    │
    │ (HOURS/DAYS PASS)
    │ User clicks button in Telegram
    │
    ↓
┌──────────────────────────────────────┐
│ RESUME: Telegram Callback Handler    │
│ - Parse callback_data                │
│ - Lookup WorkflowMapping by email_id │
│ - Get thread_id                      │
│ - Invoke workflow with user_decision │
└──────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────┐
│ CONDITIONAL: route_by_user_decision  │
│                                       │
│ ┌─ user_decision == "approve"        │
│ │     → execute_action               │
│ │                                     │
│ ├─ user_decision == "reject"         │
│ │     → send_confirmation (skip action) │
│ │                                     │
│ └─ user_decision == "change_folder"  │
│       → show_folder_menu → execute_action │
└──────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────┐
│ NODE: execute_action                 │
│ - Load Gmail client                  │
│ - Apply label to email               │
│ - Update EmailProcessingQueue status │
│ - Record ApprovalHistory             │
└──────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────┐
│ NODE: send_confirmation              │
│ - Format confirmation message        │
│ - Send to Telegram                   │
│ - "✅ Email sorted to [Folder]"      │
└──────────────────────────────────────┘
    │
    ↓
┌──────────────────────────────────────┐
│ END: Workflow Complete                │
│ - Update WorkflowMapping to completed │
│ - Delete checkpoint from PostgreSQL  │
└──────────────────────────────────────┘
```

**Batch Notification Flow (Story 2.8):**

```
CELERY SCHEDULED TASK (Daily 6 PM per user)
    │
    ↓
For each active user:
    │
    ├─ Load NotificationPreferences
    │   ├─ Check batch_enabled
    │   ├─ Check batch_time
    │   └─ Check quiet_hours
    │
    ├─ Query EmailProcessingQueue
    │   └─ status = "awaiting_approval" AND is_priority = false
    │
    ├─ If pending emails > 0:
    │   │
    │   ├─ Send batch summary message:
    │   │   "📬 You have 8 emails needing review:
    │   │    • 3 → Government
    │   │    • 2 → Clients
    │   │    • 3 → Newsletters"
    │   │
    │   └─ For each pending email:
    │       └─ Trigger EmailWorkflow (if not already started)
    │           └─ Sends individual proposal messages
    │
    └─ If pending emails == 0:
        └─ Skip (no notification sent)
```

**Priority Email Immediate Notification (Story 2.9):**

```
EMAIL POLLING DETECTS NEW EMAIL
    │
    ↓
PriorityDetectionService.detect_priority()
    │
    ├─ Check sender domain:
    │   └─ Match against priority_domains list
    │       (finanzamt.de, auslaenderbehoerde.de, arbeitsagentur.de)
    │
    ├─ Check subject keywords:
    │   └─ Search for: "urgent", "wichtig", "deadline", "frist"
    │
    ├─ Calculate priority_score (0-100):
    │   └─ government_domain: +50
    │   └─ urgent_keyword: +30
    │   └─ user_configured_priority_sender: +40
    │
    └─ If priority_score >= 70:
        │
        ├─ Set is_priority = true
        │
        ├─ BYPASS BATCH SCHEDULING
        │
        └─ Immediately trigger EmailWorkflow
            └─ Send Telegram notification with ⚠️ icon
                "⚠️ PRIORITY EMAIL
                 From: finanzamt@berlin.de
                 Subject: Tax Deadline - Action Required"
```

**Cross-Channel Workflow Resumption Sequence (TelegramHITLWorkflow Pattern):**

```
DAY 1, 9:00 AM - Backend
    │
    EmailWorkflow starts
    └─ Pauses at await_approval node
        └─ State saved to PostgreSQL checkpoints table
            └─ WorkflowMapping created:
                email_id=123, thread_id="email_123_uuid", telegram_message_id=456

TELEGRAM APP
    │
    User sees message in Telegram
    └─ [Approve] [Change Folder] [Reject] buttons displayed

DAY 1, 6:30 PM - Telegram (Different device, 9.5 hours later)
    │
    User clicks [Approve] button
    └─ Telegram sends callback to backend webhook
        callback_data = "approve_123"

Backend Callback Handler
    │
    ├─ Parse email_id from callback_data
    ├─ Query WorkflowMapping by email_id → get thread_id
    ├─ Load EmailWorkflow
    └─ Resume workflow:
        workflow.ainvoke(
            {"user_decision": "approve"},
            config={"configurable": {"thread_id": thread_id}}
        )

LangGraph PostgreSQL Checkpointer
    │
    ├─ Loads saved state from checkpoints table using thread_id
    ├─ Reconstructs EmailWorkflowState with all context
    └─ Continues from await_approval node → execute_action

Workflow continues exactly where it left off
    └─ Applies Gmail label
    └─ Sends confirmation to Telegram
    └─ Deletes checkpoint (workflow complete)
```

## Non-Functional Requirements

### Performance

**NFR001: Email Processing Latency < 2 Minutes (PRD Reference)**

**Target:** Email receipt → Telegram notification delivery ≤ 120 seconds

**Breakdown:**
- Email polling interval: 120 seconds (configurable, default 2 minutes)
- Email retrieval from Gmail API: ~500ms
- AI classification (Gemini API): ~2-4 seconds (95th percentile)
- Priority detection processing: ~100ms
- Telegram message delivery: ~500-1000ms
- **Total worst case:** 120s (polling) + 5.5s (processing) = 125.5 seconds ✅

**Performance Optimizations:**
- **Parallel processing:** Multiple users' emails processed concurrently via Celery worker pool
- **Gemini free tier:** 1M tokens/minute ensures no rate limit delays (typical classification: ~200 tokens)
- **Database indexing:** `email_id`, `thread_id`, `(user_id, workflow_state)` indexed for fast workflow resumption
- **Telegram long polling:** 30 messages/second capacity (far exceeds typical 5-10 emails/day per user)

**Monitoring:**
- Prometheus metrics: `email_processing_duration_seconds` histogram
- Alert threshold: p95 latency > 10 seconds (excluding polling interval)
- Langfuse tracking: LLM call duration per classification

**NFR: Gemini API Response Time**

**Target:** Classification prompt → parsed JSON response ≤ 5 seconds (p95)

**Measurement:**
- Tracked via Langfuse integration (inherited from template)
- Metric: `llm_classification_duration_ms`
- Typical observed: 1.5-3 seconds for 150-250 token prompts

**NFR: Workflow Resumption Performance**

**Target:** Telegram button click → workflow resumed ≤ 2 seconds

**Breakdown:**
- Telegram callback received: ~100ms
- WorkflowMapping database lookup: ~50ms (indexed query)
- LangGraph checkpoint load from PostgreSQL: ~300-500ms
- Workflow execution (execute_action node): ~1-2 seconds (Gmail API label application)
- **Total:** ~1.5-2.7 seconds ✅

**NFR: Batch Notification Processing**

**Target:** Process all pending emails for batch notification ≤ 30 seconds per user

**Scenario:** User has 20 pending emails awaiting approval
- Query EmailProcessingQueue: ~100ms
- Format batch summary message: ~50ms
- Send 21 Telegram messages (1 summary + 20 proposals): ~5-10 seconds
- **Total:** ~10-15 seconds for 20 emails ✅

### Security

**NFR004: Security & Privacy (PRD Reference)**

**Telegram Bot Token Protection:**
- Bot token stored in environment variable `TELEGRAM_BOT_TOKEN`
- Never logged or exposed in API responses
- Accessed only via secure configuration loader
- Rotated via BotFather if compromised (emergency procedure documented)

**Callback Data Validation (Story 2.7):**
```python
async def handle_telegram_callback(update: Update):
    """Validate user owns the email before resuming workflow"""
    callback_data = update.callback_query.data
    action, email_id = callback_data.split("_")

    # SECURITY CHECK: Verify user owns this email
    user_telegram_id = update.callback_query.from_user.id
    workflow_mapping = db.query(WorkflowMapping).filter_by(email_id=email_id).first()

    if not workflow_mapping:
        await update.callback_query.answer("Error: Email not found")
        return

    user = db.query(User).filter_by(id=workflow_mapping.user_id).first()
    if user.telegram_id != str(user_telegram_id):
        # SECURITY VIOLATION: User trying to approve someone else's email
        logger.warning(f"Unauthorized callback attempt: telegram_id={user_telegram_id}, email_id={email_id}")
        await update.callback_query.answer("Error: Unauthorized action")
        return

    # Proceed with workflow resumption
    await WorkflowInstanceTracker.resume_workflow(email_id, action)
```

**Linking Code Security (Story 2.5):**
- 6-digit alphanumeric codes: 36^6 = ~2.1 billion combinations (collision-resistant for concurrent users)
- 15-minute expiration (enforced at database level with `expires_at` column)
- Single-use: `used` flag prevents code reuse
- Rate limiting: Max 5 code generation requests per user per hour (API endpoint protected)

**Multi-Tenant Data Isolation:**
- All database queries filtered by `user_id` (ORM-level enforcement)
- WorkflowMapping includes `user_id` validation before resumption
- LangGraph thread IDs include email-specific identifiers (no cross-user access possible)
- ApprovalHistory records tied to user_id (audit trail per user)

**TLS/HTTPS for All Communications:**
- Gmail API: HTTPS only (enforced by Google)
- Gemini API: HTTPS only (enforced by Google)
- Telegram Bot API: HTTPS only (enforced by Telegram)
- Backend API: TLS configured in production (Let's Encrypt certificates)

**Sensitive Data Handling:**
- Email content never stored in logs (structured logging excludes body text)
- LLM prompts logged via Langfuse with PII redaction options
- Classification reasoning stored in database (contains no sensitive email body)
- Telegram messages contain email preview only (first 100 chars, no full body)

**GDPR Compliance (Basic Requirements):**
- User can delete account → CASCADE deletes all related data (WorkflowMapping, ApprovalHistory, LinkingCodes)
- Data retention: ApprovalHistory retained 90 days, then auto-deleted (future enhancement)
- Data export: User can request JSON export of ApprovalHistory via API
- Right to be forgotten: Account deletion API endpoint implemented

### Reliability/Availability

**NFR002: System Reliability - 99.5% Uptime, Zero Data Loss (PRD Reference)**

**LangGraph PostgreSQL Checkpointing (Zero Data Loss Guarantee):**
- Workflow state persisted to PostgreSQL after every node execution
- Service restart → workflows automatically resume from last checkpoint
- Power failure during workflow → state recovered on service startup
- Checkpoint cleanup: Only deleted after workflow reaches terminal state (completed/error)

**API Retry Logic with Exponential Backoff (Story 2.11):**

```python
class RetryConfig:
    """Retry configuration for external API calls"""
    MAX_RETRIES = 3
    BASE_DELAY = 2  # seconds
    MAX_DELAY = 16  # seconds
    EXPONENTIAL_BASE = 2

async def execute_with_retry(func, *args, **kwargs):
    """Execute function with exponential backoff retry"""
    for attempt in range(RetryConfig.MAX_RETRIES):
        try:
            return await func(*args, **kwargs)
        except (RequestException, TimeoutError, HttpError) as e:
            if attempt == RetryConfig.MAX_RETRIES - 1:
                # Final retry failed - log error and raise
                logger.error(f"All retries exhausted for {func.__name__}: {e}")
                raise

            # Calculate exponential backoff delay
            delay = min(
                RetryConfig.BASE_DELAY * (RetryConfig.EXPONENTIAL_BASE ** attempt),
                RetryConfig.MAX_DELAY
            )

            logger.warning(f"Retry {attempt + 1}/{RetryConfig.MAX_RETRIES} for {func.__name__} after {delay}s")
            await asyncio.sleep(delay)
```

**Error Recovery Strategies:**

**Gemini API Failures (Story 2.11):**
- Transient errors (503, 429): Retry with exponential backoff (max 3 attempts)
- Persistent errors: Move email to `error` status, notify user via Telegram
- User notification: "⚠️ Classification failed for email from {sender}. Please review manually."
- Manual retry: User can trigger re-classification via Telegram command `/retry {email_id}`

**Gmail API Failures (Label Application):**
- Token expiration (401): Auto-refresh OAuth token, retry operation once
- Rate limit (429): Exponential backoff with up to 16 second delay
- Network timeout: Retry up to 3 times
- Persistent failure: Email status → `error`, user notified, retry option provided

**Telegram API Failures (Message Send):**
- Network timeout: Retry up to 3 times with exponential backoff
- User blocked bot: Mark user as inactive, disable notifications, log event
- Message too long (>4096 chars): Truncate message, send with "..." indicator
- Persistent failure: Log error, continue workflow (don't block email processing)

**Celery Task Reliability:**
- Task acknowledgment: Tasks acknowledged only after successful completion
- Task retries: Failed tasks automatically retried (max 3 attempts, configurable)
- Dead letter queue: Tasks failing all retries moved to DLQ for manual investigation
- Redis persistence: Task queue persisted to disk (RDB snapshots + AOF)

**Database Connection Resilience:**
- Connection pooling: SQLAlchemy pool_size=10, max_overflow=20
- Connection health checks: Pre-ping before each query
- Transaction rollback: Failed transactions automatically rolled back
- Deadlock handling: Automatic retry with jitter for deadlock errors

**Workflow State Corruption Prevention:**
- State validation: Pydantic models validate EmailWorkflowState before persistence
- Atomic state updates: PostgreSQL transactions ensure all-or-nothing state changes
- Checkpoint versioning: LangGraph maintains checkpoint history (last 5 states retained)
- State recovery: If current checkpoint corrupted, rollback to previous checkpoint

### Observability

**Structured Logging (JSON Format):**

```python
# Example structured log entry for workflow start
{
  "timestamp": "2025-11-06T12:00:00Z",
  "level": "INFO",
  "service": "email_workflow",
  "event": "workflow_started",
  "email_id": 123,
  "user_id": 45,
  "thread_id": "email_123_abc-uuid",
  "sender": "finanzamt@berlin.de",
  "classification": "sort_only",
  "priority_score": 85
}
```

**Key Log Events:**
- `workflow_started`: EmailWorkflow initialized with email metadata
- `classification_completed`: Gemini API classification result received
- `priority_detected`: Email flagged as priority (score >= 70)
- `telegram_message_sent`: Proposal message delivered to user
- `user_decision_received`: Telegram callback processed (approve/reject/change)
- `workflow_resumed`: LangGraph workflow resumed from checkpoint
- `action_executed`: Gmail label applied or email sent
- `workflow_completed`: EmailWorkflow reached terminal state
- `error_occurred`: Exception caught with full stack trace

**Prometheus Metrics (Inherited from Template + Custom):**

**Epic 2 Custom Metrics:**
```python
# Classification metrics
email_classification_duration_seconds = Histogram(
    "email_classification_duration_seconds",
    "Time to classify email via Gemini API",
    ["user_id", "classification_type"]
)

gemini_token_usage_total = Counter(
    "gemini_token_usage_total",
    "Total tokens consumed by Gemini API",
    ["operation"]  # classification, response_generation
)

# Workflow metrics
workflow_state_transitions_total = Counter(
    "workflow_state_transitions_total",
    "Workflow state transitions count",
    ["from_state", "to_state"]
)

workflow_pause_duration_seconds = Histogram(
    "workflow_pause_duration_seconds",
    "Time workflow spent in await_approval state",
    ["user_id"]
)

workflow_resumption_duration_seconds = Histogram(
    "workflow_resumption_duration_seconds",
    "Time to resume workflow from Telegram callback",
    ["user_id"]
)

# Approval metrics
approval_decisions_total = Counter(
    "approval_decisions_total",
    "User approval decision counts",
    ["decision_type", "user_id"]  # approve, reject, change_folder
)

approval_accuracy_ratio = Gauge(
    "approval_accuracy_ratio",
    "Ratio of approved to total decisions (AI accuracy proxy)",
    ["user_id"]
)

# Telegram metrics
telegram_messages_sent_total = Counter(
    "telegram_messages_sent_total",
    "Telegram messages sent count",
    ["message_type"]  # proposal, confirmation, batch_summary
)

telegram_callback_errors_total = Counter(
    "telegram_callback_errors_total",
    "Telegram callback handling errors",
    ["error_type"]  # unauthorized, not_found, workflow_error
)

# Priority detection metrics
priority_emails_detected_total = Counter(
    "priority_emails_detected_total",
    "Count of emails detected as priority",
    ["user_id", "detection_reason"]  # government_domain, urgent_keyword
)
```

**Langfuse LLM Observability:**

- **Automatic tracing:** All Gemini API calls traced with full context
- **Prompt versioning:** Classification prompts versioned and tracked
- **Token tracking:** Input/output tokens per classification logged
- **Cost estimation:** Token usage → estimated cost (free tier monitoring)
- **Latency analysis:** p50, p95, p99 latencies for classification calls
- **Error tracking:** Failed LLM calls with error messages and retry attempts

**Grafana Dashboards (To Be Created):**

**Dashboard: Epic 2 - Email Classification & Approval**
- Panel 1: Classification duration (p50, p95, p99) - time series
- Panel 2: Gemini token usage rate - counter with rate()
- Panel 3: Workflow pause duration distribution - histogram
- Panel 4: Approval decision breakdown (approve/reject/change) - pie chart
- Panel 5: AI accuracy proxy (approval rate) - gauge per user
- Panel 6: Priority emails detected over time - time series
- Panel 7: Telegram callback errors - counter with alerts
- Panel 8: Active workflows in await_approval state - gauge

**Dashboard: Workflow Health**
- Panel 1: Workflow completion rate (completed vs error) - time series
- Panel 2: Average workflow duration (start → complete) - histogram
- Panel 3: Checkpoint storage size - gauge
- Panel 4: Workflow state distribution - stacked area chart
- Panel 5: Error rate by workflow node - heatmap

**Alerting Rules:**

```yaml
# Prometheus alert rules for Epic 2

- alert: HighClassificationLatency
  expr: histogram_quantile(0.95, email_classification_duration_seconds) > 10
  for: 5m
  annotations:
    summary: "Gemini API classification latency > 10s (p95)"

- alert: LowApprovalRate
  expr: approval_accuracy_ratio < 0.6
  for: 1h
  annotations:
    summary: "User approval rate < 60% (AI classification quality issue)"

- alert: WorkflowStuckInAwaitApproval
  expr: time() - workflow_last_transition_timestamp{state="await_approval"} > 86400
  for: 1h
  annotations:
    summary: "Workflow stuck in await_approval for > 24 hours"

- alert: HighTelegramCallbackErrors
  expr: rate(telegram_callback_errors_total[5m]) > 0.1
  for: 5m
  annotations:
    summary: "Telegram callback error rate > 10%"

- alert: GeminiAPIFailureRate
  expr: rate(gemini_api_errors_total[5m]) > 0.05
  for: 5m
  annotations:
    summary: "Gemini API error rate > 5%"
```

## Dependencies and Integrations

**Python Dependencies (Epic 2 Additions to pyproject.toml):**

```toml
dependencies = [
    # Existing from Epic 1
    "fastapi>=0.115.12",
    "langgraph>=0.4.1",
    "langgraph-checkpoint-postgres>=2.0.19",
    "sqlmodel>=0.0.24",
    "alembic>=1.13.3",
    "google-api-python-client>=2.146.0",
    "google-auth>=2.34.0",
    "google-auth-oauthlib>=1.2.1",
    "celery>=5.4.0",
    "redis>=5.0.1",
    "cryptography>=43.0.1",
    "structlog>=25.2.0",
    "prometheus-client>=0.19.0",
    "langfuse==3.0.3",

    # NEW Epic 2 Dependencies
    "google-generativeai>=0.8.3",      # Gemini API client (Story 2.1)
    "python-telegram-bot>=21.0",       # Telegram Bot API (Story 2.4)
    "pydantic>=2.11.1",                # TypedDict validation for LangGraph states (Story 2.3)
]
```

**Dependency Version Constraints & Rationale:**

| Dependency | Version | Rationale | Story |
|-----------|---------|-----------|-------|
| **google-generativeai** | >=0.8.3 | Official Gemini API client, supports gemini-2.5-flash model and JSON mode | 2.1 |
| **python-telegram-bot** | >=21.0 | Official Telegram Bot API library, async/await support, inline keyboards | 2.4 |
| **langgraph** | >=0.4.1 | State machine workflows with PostgreSQL checkpointing (TelegramHITLWorkflow pattern) | 2.3 |
| **langgraph-checkpoint-postgres** | >=2.0.19 | PostgreSQL checkpointer for persistent workflow state | 2.3 |
| **pydantic** | >=2.11.1 | Runtime validation for EmailWorkflowState TypedDict | 2.3 |
| **langfuse** | ==3.0.3 | LLM observability for Gemini API tracing (inherited from template) | 2.1 |

**External API Integrations:**

**1. Google Gemini API (Story 2.1)**
- **Service:** Google AI Studio / Vertex AI
- **Model:** `gemini-2.5-flash` (or `gemini-2.5-flash-latest` alias)
- **Endpoint:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`
- **Authentication:** API Key (stored in `GEMINI_API_KEY` environment variable)
- **Rate Limits:** 1,000,000 tokens/minute (free tier)
- **Cost:** Free tier unlimited (as of 2025)
- **Usage:** Email classification, priority detection, classification reasoning generation
- **Configuration:**
```python
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

# JSON mode configuration
generation_config = genai.GenerationConfig(
    response_mime_type="application/json",
    response_schema={
        "type": "object",
        "properties": {
            "suggested_folder": {"type": "string"},
            "reasoning": {"type": "string"},
            "priority_score": {"type": "integer"},
            "confidence": {"type": "number"}
        },
        "required": ["suggested_folder", "reasoning"]
    }
)
```

**2. Telegram Bot API (Story 2.4)**
- **Service:** Telegram Bot Platform
- **Endpoint:** `https://api.telegram.org/bot{token}/`
- **Authentication:** Bot Token (obtained via BotFather, stored in `TELEGRAM_BOT_TOKEN` env var)
- **Mode:** Long polling (getUpdates) for MVP
- **Rate Limits:** 30 messages/second per bot, 20 messages/minute per chat
- **Cost:** Free (no usage limits)
- **Usage:** Send email proposals, receive button callbacks, user-Telegram linking
- **Configuration:**
```python
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

application = (
    Application.builder()
    .token(os.getenv("TELEGRAM_BOT_TOKEN"))
    .build()
)

# Register handlers
application.add_handler(CommandHandler("start", handle_start_command))
application.add_handler(CallbackQueryHandler(handle_telegram_callback))

# Start long polling
await application.run_polling()
```

**3. Gmail API (Inherited from Epic 1)**
- Used for label application (execute_action node in workflow)
- Already configured in Epic 1 (Story 1.5, 1.8)

**4. PostgreSQL (Checkpoint Storage)**
- **Connection:** Via `langgraph-checkpoint-postgres` library
- **Database:** Same PostgreSQL instance as main application database
- **Tables:**
  - `checkpoints`: LangGraph workflow state storage
  - `checkpoint_writes`: State change history
- **Configuration:**
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    conn_string=DATABASE_URL,
    sync=False  # Async mode for FastAPI
)
```

**5. Redis (Celery Message Broker)**
- Used for batch notification task scheduling (Story 2.8)
- Already configured in Epic 1
- **Configuration:**
```python
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
```

**Integration Flow Diagram:**

```
┌─────────────────────────────────────────────────────────────────┐
│                   Epic 2 Integration Points                     │
└─────────────────────────────────────────────────────────────────┘

                          FastAPI Backend
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ↓               ↓               ↓
        ┌───────────┐   ┌──────────┐   ┌──────────────┐
        │ Gemini API │   │ Telegram │   │ Gmail API    │
        │ (LLM)      │   │ Bot API  │   │ (Labels)     │
        └───────────┘   └──────────┘   └──────────────┘
                │               │               │
                │               │               │
        Classification    Button Callbacks   Apply Labels
        Reasoning         Message Send        (Approved)
                │               │               │
                └───────────────┼───────────────┘
                                │
                                ↓
                        ┌──────────────┐
                        │ LangGraph    │
                        │ Workflow     │
                        │ (EmailFlow)  │
                        └──────────────┘
                                │
                                ↓
                        ┌──────────────┐
                        │ PostgreSQL   │
                        │ Checkpointer │
                        └──────────────┘
                                │
                        Persistent State
                        (Cross-channel
                         resumption)
```

**Environment Variables (Epic 2 Additions):**

```bash
# Epic 2 Required Environment Variables

# Gemini API (Story 2.1)
GEMINI_API_KEY=your_gemini_api_key_here  # From Google AI Studio
GEMINI_MODEL=gemini-2.5-flash            # Model name

# Telegram Bot (Story 2.4, 2.5)
TELEGRAM_BOT_TOKEN=your_bot_token_here   # From BotFather
TELEGRAM_BOT_USERNAME=MailAgentBot       # Bot username (for linking instructions)

# Notification Settings (Story 2.8)
DEFAULT_BATCH_TIME=18:00                 # Default batch time (6 PM)
DEFAULT_TIMEZONE=UTC                     # Default timezone

# Priority Detection (Story 2.9)
PRIORITY_THRESHOLD=70                    # Priority score threshold (0-100)
PRIORITY_GOVERNMENT_DOMAINS=finanzamt.de,auslaenderbehoerde.de,arbeitsagentur.de
PRIORITY_KEYWORDS=urgent,wichtig,deadline,frist

# LangGraph (Story 2.3)
LANGGRAPH_CHECKPOINT_CLEANUP_ENABLED=true  # Auto-delete completed checkpoints
LANGGRAPH_CHECKPOINT_RETENTION_DAYS=7      # Keep checkpoints for 7 days before cleanup
```

**Docker Compose Services (No Changes Required):**

Epic 2 reuses existing services from Epic 1:
- PostgreSQL (for checkpointing + main database)
- Redis (for Celery task queue)
- Prometheus (for metrics)
- Grafana (for dashboards)

No additional Docker containers needed for Gemini or Telegram (API-only integrations).

## Acceptance Criteria (Authoritative)

Extracted from Epic 2 stories in `epics.md` - these are the authoritative acceptance criteria for Epic 2 completion:

**Story 2.1: Gemini LLM Integration**
1. Gemini API key obtained from Google AI Studio and stored in environment variables
2. Gemini Python SDK (google-generativeai) integrated into backend service
3. Model configured: gemini-2.5-flash (or gemini-2.5-flash-latest alias)
4. Basic prompt-response method created (send_prompt, receive_completion)
5. Error handling implemented for API failures, rate limits, and timeouts
6. Token usage tracking implemented for monitoring free tier usage (1M tokens/minute)
7. Fallback strategy documented for Gemini unavailability (Claude/GPT-4 alternatives)
8. Test endpoint created to verify Gemini connectivity (POST /test/gemini)
9. Response parsing implemented to extract structured data from LLM responses (JSON mode)

**Story 2.2: Email Classification Prompt Engineering**
1. Classification prompt template created with placeholders for email metadata and user categories
2. Prompt includes email sender, subject, body preview, and user-defined folder categories
3. Prompt instructs LLM to output structured JSON with folder suggestion and reasoning
4. Prompt examples created showing expected input/output format
5. Testing performed with sample emails across different categories (government, clients, newsletters)
6. Multilingual capability validated (prompt works for Russian, Ukrainian, English, German emails)
7. Edge cases handled (unclear emails, multiple possible categories)
8. Prompt version stored in config for future refinement

**Story 2.3: AI Email Classification Service**
1. Email classification service created that processes emails from EmailProcessingQueue
2. Service retrieves email full content from Gmail using stored message_id
3. Service loads user's folder categories from FolderCategories table
4. Service constructs classification prompt with email content and categories
5. Service calls Gemini LLM API and parses JSON response (suggested_folder, reasoning)
6. Classification result stored in EmailProcessingQueue (proposed_action field added to schema)
7. Service handles classification errors (falls back to "Unclassified" category)
8. Processing status updated to "awaiting_approval" after successful classification
9. LangGraph workflow compiled with PostgreSQL checkpointer (PostgresSaver.from_conn_string)
10. Checkpoint storage configured to persist workflow state for pause/resume functionality

**Story 2.4: Telegram Bot Foundation**
1. Telegram bot created via BotFather and bot token obtained
2. Bot token stored securely in environment variables
3. python-telegram-bot library integrated into backend service
4. Bot initialized and connected on application startup
5. Basic bot commands implemented (/start, /help)
6. Bot can send messages to specific Telegram user IDs
7. Bot can receive messages and button clicks from users
8. Webhook or polling mechanism set up for receiving updates
9. Test command created to verify bot connectivity (/test)

**Story 2.5: User-Telegram Account Linking**
1. Unique linking code generation implemented (6-digit alphanumeric code)
2. LinkingCodes table created (code, user_id, expires_at, used)
3. API endpoint created to generate linking code for authenticated user (POST /telegram/generate-code)
4. Bot command /start [code] implemented to link Telegram user with code
5. Bot validates linking code and associates telegram_id with user in database
6. Expired codes (>15 minutes old) rejected with error message
7. Used codes cannot be reused
8. Success message sent to user on Telegram after successful linking
9. User's telegram_id stored in Users table

**Story 2.6: Email Sorting Proposal Messages**
1. Message template created for sorting proposals with email preview
2. Message includes: sender name, subject line, first 100 characters of body
3. Message includes AI's suggested folder and reasoning (1-2 sentences)
4. Message formatted with clear visual hierarchy (bold for sender/subject)
5. Inline buttons added: [Approve] [Change Folder] [Reject]
6. Service created to send sorting proposal messages to users via Telegram
7. Message ID stored in EmailProcessingQueue for tracking responses
8. Multiple proposals batched into single Telegram message thread when possible
9. Priority emails flagged with ⚠️ icon in message
10. WorkflowMapping table created with schema: email_id (unique), user_id, thread_id (unique), telegram_message_id, workflow_state, created_at, updated_at
11. Indexes created: idx_workflow_mappings_thread_id, idx_workflow_mappings_user_state
12. Database migration applied for WorkflowMapping table
13. WorkflowMapping entry created for each email workflow to enable Telegram callback reconnection

**Story 2.7: Approval Button Handling**
1. Button callback handlers implemented for [Approve], [Change Folder], [Reject]
2. [Approve] callback applies suggested Gmail label and updates status to "completed"
3. [Reject] callback updates status to "rejected" and leaves email in inbox
4. [Change Folder] callback presents list of available folders as inline keyboard
5. Folder selection callback applies selected label to email
6. Confirmation message sent after each action ("✅ Email sorted to [Folder]")
7. Button callback includes email queue ID for tracking
8. Callback data validated (user owns the email being processed)
9. Error handling for Gmail API failures during label application

**Story 2.8: Batch Notification System**
1. Batch notification scheduling implemented (configurable time, default: end of day)
2. Batch job retrieves all pending emails (status="awaiting_approval") for each user
3. Summary message created showing count of emails needing review
4. Summary includes breakdown by proposed category (e.g., "3 to Government, 2 to Clients")
5. Individual proposal messages sent after summary (one message per email)
6. High-priority emails bypass batching and notify immediately
7. User preference stored for batch timing (NotificationPreferences table)
8. Empty batch handling (no message sent if no pending emails)
9. Batch completion logged for monitoring

**Story 2.9: Priority Email Detection**
1. Priority detection rules defined (keywords: "urgent", "deadline", "wichtig", specific senders)
2. Government sender detection implemented (domains: finanzamt.de, auslaenderbehoerde.de, etc.)
3. Priority scoring algorithm created (0-100 score based on multiple factors)
4. Emails scoring above threshold (e.g., 70+) marked as high-priority
5. High-priority flag stored in EmailProcessingQueue
6. High-priority emails bypass batch scheduling and notify immediately
7. Priority indicator added to Telegram messages (⚠️ emoji)
8. User can configure custom priority senders in FolderCategories settings
9. Priority detection logged for analysis and refinement

**Story 2.10: Approval History Tracking**
1. ApprovalHistory table created (id, user_id, email_queue_id, action_type, ai_suggested_folder, user_selected_folder, approved, timestamp)
2. Approval event recorded when user clicks [Approve] (approved=true)
3. Rejection event recorded when user clicks [Reject] (approved=false)
4. Folder change event recorded with both AI suggestion and user selection
5. History queryable by user, date range, and approval type
6. Statistics endpoint created showing approval rate per user (GET /stats/approvals)
7. Database indexes added for efficient history queries
8. Privacy considerations documented (history retention policy)

**Story 2.11: Error Handling and Recovery**
1. Gmail API errors caught and logged with context (email_id, user_id, error type)
2. Telegram API errors caught and logged (message send failures, button callback failures)
3. Retry mechanism implemented for transient failures (max 3 retries with exponential backoff)
4. Failed emails moved to "error" status after max retries
5. Error notification sent to user via Telegram for persistent failures
6. Manual retry command implemented in Telegram (/retry [email_id])
7. Admin dashboard endpoint shows emails in error state (GET /admin/errors)
8. Dead letter queue implemented for emails that repeatedly fail processing
9. Health monitoring alerts configured for high error rates

**Story 2.12: Epic 2 Integration Testing**
1. Integration test simulates complete flow: new email → AI classification → Telegram proposal → user approval → Gmail label applied
2. Test mocks Gmail API, Gemini API, and Telegram API
3. Test verifies email moves through all status states correctly
4. Test validates approval history is recorded accurately
5. Test covers rejection and folder change scenarios
6. Test validates batch notification logic
7. Test validates priority email immediate notification
8. Performance test ensures processing completes within 2 minutes (NFR001)
9. Documentation updated with Epic 2 architecture and flow diagrams

## Traceability Mapping

This table maps each acceptance criterion to specific technical implementation details and test strategies:

| AC # | Story | Spec Section(s) | Component(s)/API(s) | Test Idea |
|------|-------|----------------|---------------------|-----------|
| 2.1.1-9 | Gemini Integration | Dependencies, APIs | `app/core/llm_client.py`, `/test/gemini` | Mock Gemini API, verify JSON parsing, test error handling |
| 2.2.1-8 | Prompt Engineering | Data Models (Gemini Schema) | Classification prompt template in config | Test multilingual samples (RU/UK/EN/DE), validate JSON output |
| 2.3.1-10 | Classification Service | Services (EmailClassificationService), Workflows (EmailWorkflow) | `app/services/classification.py`, `app/workflows/email_workflow.py` | Mock workflow execution, verify state transitions, test checkpoint persistence |
| 2.4.1-9 | Telegram Bot | Dependencies, APIs | `app/core/telegram_bot.py` | Mock Telegram API, test command handlers, verify long polling |
| 2.5.1-9 | Telegram Linking | Data Models (LinkingCodes), APIs | `LinkingCodes` table, `/telegram/generate-code`, `/start` command | Test code expiration (15 min), verify single-use constraint, test linking flow |
| 2.6.1-13 | Proposal Messages | Data Models (WorkflowMapping), Workflows | `WorkflowMapping` table, `send_telegram` node | Test message formatting, verify inline buttons, test workflow mapping creation |
| 2.7.1-9 | Approval Buttons | Workflows, APIs | Telegram callback handler, `execute_action` node | Test callback parsing, verify user ownership validation, mock Gmail label application |
| 2.8.1-9 | Batch Notifications | Services (BatchNotificationService), Data Models (NotificationPreferences) | `app/services/batch_notification.py`, `NotificationPreferences` table | Test batch scheduling (Celery), verify summary format, test empty batch handling |
| 2.9.1-9 | Priority Detection | Services (PriorityDetectionService) | `app/services/priority_detection.py`, `detect_priority` node | Test government domain detection, verify keyword matching, test priority bypass |
| 2.10.1-8 | Approval History | Data Models (ApprovalHistory), APIs | `ApprovalHistory` table, `/stats/approvals` | Test history recording, verify approval rate calculation, test query performance |
| 2.11.1-9 | Error Handling | Reliability/Availability (Retry Logic) | `execute_with_retry()`, error handlers | Test exponential backoff, verify dead letter queue, test error notifications |
| 2.12.1-9 | Integration Testing | All sections | Complete EmailWorkflow end-to-end | Full flow test: email → classify → Telegram → approve → label applied |

**FR → Epic 2 Traceability:**

| Functional Requirement (PRD) | Epic 2 Implementation | Verification |
|------------------------------|----------------------|--------------|
| FR007: Allow users to link Telegram account | Story 2.5 (Telegram Linking) | Test `/start [code]` command, verify `Users.telegram_id` stored |
| FR008: Send email sorting proposals via Telegram | Story 2.6 (Proposal Messages) | Test message template, verify inline buttons rendered |
| FR010: Provide interactive approval buttons | Story 2.7 (Approval Button Handling) | Test [Approve] [Reject] [Change] callbacks |
| FR012: Send batch notifications | Story 2.8 (Batch Notification System) | Test daily batch job, verify summary message format |
| FR013: Analyze emails based on sender, subject, content | Story 2.2, 2.3 (Classification) | Test classification prompt, verify AI reasoning output |
| FR014: Classify emails into user-defined categories | Story 2.3 (AI Classification Service) | Test with multiple folder categories, verify correct classification |
| FR015: Provide reasoning for sorting proposals | Story 2.2 (Prompt Engineering) | Verify `classification_reasoning` field populated, test reasoning quality |
| FR016: Execute approved sorting by applying Gmail labels | Story 2.7 (execute_action node) | Test Gmail API label application, verify label_id applied |

**NFR → Epic 2 Traceability:**

| Non-Functional Requirement (PRD) | Epic 2 Implementation | Verification |
|----------------------------------|----------------------|--------------|
| NFR001: Processing latency ≤ 2 minutes | Performance section, EmailWorkflow optimization | Performance test: measure email → Telegram notification time |
| NFR002: 99.5% uptime, zero data loss | PostgreSQL checkpointing, retry logic | Test service restart during workflow, verify state recovered |
| NFR004: Encrypt tokens, TLS communications | Security section (Bot token protection) | Verify bot token never logged, test callback data validation |
| NFR005: Non-technical user onboarding | Telegram linking UX (simple code entry) | Usability test: time to link Telegram account < 30 seconds |

## Risks, Assumptions, Open Questions

**Risks:**

| Risk ID | Description | Impact | Probability | Mitigation Strategy |
|---------|-------------|--------|-------------|---------------------|
| R2.1 | **Gemini API free tier limits change** - Google may introduce usage caps or pricing changes | HIGH | MEDIUM | Document fallback to Claude/GPT-4, implement provider abstraction layer, monitor Google AI announcements |
| R2.2 | **LangGraph checkpoint storage growth** - PostgreSQL checkpoint table grows unbounded | MEDIUM | HIGH | Implement automatic checkpoint cleanup after workflow completion, set retention policy (7 days), add monitoring alert for table size |
| R2.3 | **Workflow stuck in await_approval state indefinitely** - User never responds to Telegram message | LOW | MEDIUM | Implement timeout mechanism (24-48 hours), auto-expire stale workflows, send reminder notification after 12 hours |
| R2.4 | **Telegram Bot API rate limiting** - High-volume users exceed 30 msg/sec limit | MEDIUM | LOW | Implement message queuing with rate limiter, batch multiple emails into single message thread, prioritize high-priority emails |
| R2.5 | **Classification accuracy below user expectations** - AI suggests wrong folders > 40% of time | HIGH | MEDIUM | Track approval rate per user (Story 2.10), refine prompts based on rejections, implement user-specific prompt tuning (post-MVP) |
| R2.6 | **Cross-channel workflow resumption failure** - thread_id lookup fails after Telegram callback | HIGH | LOW | Add database indexes on WorkflowMapping, implement error logging for failed resumptions, provide manual retry mechanism |
| R2.7 | **Priority detection false positives** - Non-urgent emails flagged as priority, overwhelming user | MEDIUM | MEDIUM | Make priority threshold configurable per user (default: 70), allow users to disable priority notifications, log false positive rates |
| R2.8 | **User blocks Telegram bot** - Cannot send notifications after user blocks bot | MEDIUM | MEDIUM | Detect TelegramError (403 Forbidden), mark user inactive, notify via email as fallback, implement re-linking flow |

**Assumptions:**

| Assumption ID | Description | Validation Strategy |
|---------------|-------------|---------------------|
| A2.1 | **Users check Telegram daily** - Batch notification at end of day will be seen within 24 hours | User research: survey users about Telegram usage patterns, monitor workflow pause duration metrics |
| A2.2 | **Gemini multilingual quality sufficient** - AI classification works equally well for RU/UK/EN/DE emails | Test with real multilingual samples from target users, measure approval rate by language (Story 2.10) |
| A2.3 | **Gmail label application reliable** - Gmail API label operations succeed 99%+ of the time | Monitor Gmail API error rates (Story 2.11), implement retry logic with exponential backoff |
| A2.4 | **Users prefer Telegram over web UI for approvals** - Mobile-first assumption holds true | User feedback after MVP release, track approval response times (Telegram vs hypothetical web UI) |
| A2.5 | **LangGraph checkpoint performance acceptable** - PostgreSQL can handle 100+ concurrent workflows without degradation | Load testing with 100 concurrent workflows, monitor PostgreSQL checkpoint table query performance |
| A2.6 | **Priority detection keywords adequate** - "urgent", "wichtig", "deadline" catch most priority emails | Analyze priority detection accuracy via user feedback, expand keyword list based on false negatives |
| A2.7 | **6-digit alphanumeric codes sufficient security** - 2.1 billion combinations prevent brute force during 15-min window | Calculate attack probability (36^6 combinations / 15 min expiration), monitor failed linking attempts |

**Open Questions:**

| Question ID | Question | Decision Needed By | Impact on Epic 2 |
|-------------|----------|-------------------|------------------|
| Q2.1 | **Should we support Telegram webhook mode instead of long polling for production?** | Before Epic 4 deployment | MEDIUM - Webhooks improve performance but require HTTPS endpoint and more complex setup |
| Q2.2 | **What should happen if user deletes linking code before entering it in Telegram?** | Story 2.5 implementation | LOW - Current design: code remains valid until expiration or use, no deletion API |
| Q2.3 | **Should batch notifications respect user timezone or use fixed UTC time?** | Story 2.8 implementation | MEDIUM - Impact user experience; current design uses UTC 18:00, consider timezone support in Epic 4 |
| Q2.4 | **How long should we retain ApprovalHistory records?** | Before production deployment | LOW - Privacy concern (GDPR); current design: indefinite retention, consider 90-day auto-deletion |
| Q2.5 | **Should priority emails allow snoozing (delay notification)?** | Post-MVP enhancement | LOW - Not in Epic 2 scope, but users may request this feature |
| Q2.6 | **What happens if two users link to same Telegram account (shared account)?** | Story 2.5 implementation | MEDIUM - Current design: last user overwrites telegram_id, should we prevent this? |
| Q2.7 | **Should we auto-delete expired LinkingCodes from database?** | Story 2.5 implementation | LOW - Performance concern; consider cleanup job or soft-delete pattern |
| Q2.8 | **How should we handle very long classification reasoning (> 500 chars)?** | Story 2.2 implementation | LOW - Telegram message length OK (4096 max), database TEXT column sufficient |

## Test Strategy Summary

**Testing Levels:**

**1. Unit Tests (pytest)**

**Target Coverage:** 80%+ for Epic 2 code

**Key Test Suites:**
- **`test_llm_client.py`** (Story 2.1)
  - Mock Gemini API responses
  - Test JSON parsing with valid/invalid schemas
  - Test error handling (rate limits, timeouts, API failures)
  - Verify token usage tracking

- **`test_classification_service.py`** (Story 2.3)
  - Mock LLMClient and Gmail client
  - Test classification prompt construction
  - Test folder matching logic
  - Verify EmailProcessingQueue updates

- **`test_telegram_bot.py`** (Story 2.4)
  - Mock python-telegram-bot Application
  - Test command handlers (/start, /help)
  - Test message sending
  - Verify callback query handling

- **`test_telegram_linking.py`** (Story 2.5)
  - Test linking code generation (uniqueness, expiration)
  - Test code validation logic
  - Test expired code rejection
  - Test single-use enforcement

- **`test_priority_detection.py`** (Story 2.9)
  - Test government domain detection
  - Test keyword matching (multilingual)
  - Test priority score calculation
  - Verify threshold-based flagging

- **`test_workflow_tracker.py`** (Story 2.6)
  - Test WorkflowMapping CRUD operations
  - Test thread_id generation (uniqueness)
  - Test workflow instance lookup
  - Verify database indexes used

**2. Integration Tests (pytest-asyncio)**

**Target:** All critical flows with real database (test DB)

**Key Integration Tests:**
- **`test_email_workflow_integration.py`** (Story 2.12)
  - Mock external APIs (Gemini, Telegram, Gmail)
  - Test complete EmailWorkflow execution
  - Verify state transitions through all nodes
  - Test checkpoint persistence and restoration
  - Test workflow resumption after pause

- **`test_telegram_callback_integration.py`** (Story 2.7)
  - Test Telegram callback → workflow resumption flow
  - Verify WorkflowMapping lookup
  - Test user ownership validation
  - Test Gmail label application after approval

- **`test_batch_notification_integration.py`** (Story 2.8)
  - Test Celery task execution (real Redis broker)
  - Test batch email query logic
  - Test summary message generation
  - Verify individual proposal messages sent

- **`test_approval_history_integration.py`** (Story 2.10)
  - Test history recording on all decision types
  - Test approval rate calculation
  - Test statistics endpoint queries
  - Verify database indexes performance

**3. End-to-End Tests (pytest + mocked external APIs)**

**Target:** Complete user journeys

**E2E Test Scenarios:**
- **`test_e2e_email_sorting_flow.py`**
  ```python
  async def test_complete_email_sorting_with_approval():
      # Setup
      user = create_test_user_with_gmail_oauth()
      telegram_id = link_telegram_account(user)
      folders = create_test_folders(user, ["Government", "Clients"])

      # Simulate new email arrival
      email = mock_gmail_email(sender="finanzamt@berlin.de", subject="Tax deadline")

      # Trigger workflow
      workflow_result = await start_email_workflow(email, user)

      # Verify classification
      assert workflow_result.classification == "sort_only"
      assert workflow_result.proposed_folder == "Government"
      assert workflow_result.priority_score >= 70

      # Verify Telegram message sent
      telegram_msg = get_last_telegram_message(telegram_id)
      assert "finanzamt@berlin.de" in telegram_msg.text
      assert "Government" in telegram_msg.text
      assert telegram_msg.reply_markup.inline_keyboard  # Has buttons

      # Simulate user approval
      callback_data = f"approve_{email.id}"
      await simulate_telegram_callback(telegram_id, callback_data)

      # Verify label applied
      gmail_labels = mock_gmail_client.get_message_labels(email.id)
      assert "Government" in gmail_labels

      # Verify history recorded
      history = get_approval_history(user, email.id)
      assert history.action_type == "approve"
      assert history.approved == True

      # Verify workflow completed
      workflow_mapping = get_workflow_mapping(email.id)
      assert workflow_mapping.workflow_state == "completed"
  ```

- **`test_e2e_priority_email_immediate_notification.py`**
  - Test priority detection → immediate Telegram notification (bypass batch)
  - Verify ⚠️ icon in message
  - Test approval within seconds

- **`test_e2e_workflow_resumption_after_restart.py`**
  - Start workflow → pause at await_approval
  - Simulate backend service restart
  - Verify workflow can still resume from Telegram callback
  - Assert checkpoint recovered from PostgreSQL

**4. Performance Tests (locust or pytest-benchmark)**

**Target:** Meet NFR001 (< 2 min latency)

**Performance Test Scenarios:**
- **`test_classification_latency.py`**
  - Measure Gemini API response time (target: p95 < 5 seconds)
  - Test with emails of varying lengths (100-2000 words)

- **`test_workflow_resumption_latency.py`**
  - Measure Telegram callback → workflow resumed time (target: < 2 seconds)
  - Test with 100 concurrent workflows paused

- **`test_checkpoint_storage_performance.py`**
  - Measure PostgreSQL checkpoint write time (target: < 500ms)
  - Test with large workflow states (10KB+ serialized state)

- **`test_batch_notification_processing.py`**
  - Measure time to process 50 pending emails per user (target: < 30 seconds)
  - Test with 10 concurrent users

**5. Acceptance Testing (Manual + Automated)**

**Test Plan (Story 2.12):**
1. **Setup:**
   - Deploy backend with Epic 2 code
   - Create Telegram bot via BotFather
   - Configure test Gmail account with OAuth

2. **Telegram Linking (AC 2.5.1-9):**
   - Generate linking code via API
   - Open Telegram, send `/start [code]`
   - Verify success message received
   - Verify `Users.telegram_id` populated in database

3. **Email Classification (AC 2.1-2.3):**
   - Send test email to Gmail inbox (from finanzamt.de)
   - Wait 2 minutes (polling interval)
   - Verify classification completed (check database)
   - Verify proposed_folder = "Government"

4. **Telegram Proposal (AC 2.6):**
   - Verify Telegram message received
   - Check message format (sender, subject, reasoning)
   - Verify inline buttons rendered

5. **Approval Flow (AC 2.7):**
   - Click [Approve] button
   - Verify confirmation message received
   - Check Gmail - verify label applied
   - Verify ApprovalHistory record created

6. **Batch Notification (AC 2.8):**
   - Send 10 test emails to inbox
   - Wait for batch time (6 PM)
   - Verify batch summary message received
   - Verify 10 individual proposals sent

7. **Priority Email (AC 2.9):**
   - Send urgent email from finanzamt.de
   - Verify immediate notification (no batching)
   - Verify ⚠️ icon in message

**Test Frameworks and Tools:**
- **Unit/Integration:** pytest, pytest-asyncio, pytest-mock
- **API Mocking:** responses, httpx-mock
- **Database:** pytest-postgresql (test DB fixture)
- **Performance:** pytest-benchmark, locust (load testing)
- **E2E:** Playwright (future - for Epic 4 UI testing)
- **Coverage:** pytest-cov (minimum 80% for Epic 2 code)

**Test Execution Strategy:**
- **Pre-commit:** Fast unit tests (<5 seconds total)
- **CI Pipeline:** All unit + integration tests (<2 minutes total)
- **Nightly:** E2E tests + performance tests (<30 minutes total)
- **Pre-release:** Full acceptance testing (manual + automated)
