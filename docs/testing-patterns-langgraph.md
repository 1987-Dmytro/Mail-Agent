# LangGraph Testing Patterns

**Document Version:** 1.0
**Created:** 2025-11-09
**Source:** Epic 2 Story 2.12 - Integration Testing Learnings
**Author:** Amelia (Developer) + Murat (TEA)
**Status:** Production-Ready Patterns

---

## Overview

This document provides proven testing patterns for LangGraph stateful workflows, based on real-world debugging sessions from Epic 2 Story 2.12. After 6 implementation sessions and fixing 16 critical issues, we've distilled these battle-tested patterns for Epic 3 (RAG System) and beyond.

**Why This Document Exists:**

Epic 2 Story 2.12 required 5-6 review/dev cycles to achieve 18/18 passing integration tests. The challenges were:
- LangGraph checkpoint API compatibility (v1 vs v2)
- Workflow dependency injection
- Multi-API mocking alignment
- Database persistence in workflow nodes
- Cross-channel workflow resumption

These patterns prevent those issues from recurring in Epic 3.

---

## Table of Contents

1. [LangGraph Workflow Testing Fundamentals](#langgraph-workflow-testing-fundamentals)
2. [MemorySaver Integration (Test Isolation)](#memorysaver-integration-test-isolation)
3. [Workflow Dependency Injection](#workflow-dependency-injection)
4. [Testing Workflow Resumption](#testing-workflow-resumption)
5. [Multi-API Mocking Strategy](#multi-api-mocking-strategy)
6. [Database Persistence in Workflows](#database-persistence-in-workflows)
7. [Testing Cross-Channel Workflows](#testing-cross-channel-workflows)
8. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)

---

## LangGraph Workflow Testing Fundamentals

### Concept: Stateful Workflows Are Different

LangGraph workflows maintain state across multiple nodes and can pause/resume. This is fundamentally different from testing stateless functions.

**Key Differences:**

| Stateless Function | LangGraph Workflow |
|-------------------|-------------------|
| Single execution | Multiple nodes with state transitions |
| No persistence | Checkpoint persistence to database |
| Simple mocking | Dependency injection + mocking |
| Synchronous (usually) | Async state machine |
| One test = one function call | One test = multiple node executions |

### Basic Testing Setup

```python
import pytest
from langgraph.checkpoint.memory import MemorySaver
from your_app.workflows.email_workflow import create_email_workflow
from your_app.workflows.states import EmailWorkflowState

@pytest.fixture
def memory_checkpointer():
    """In-memory checkpointer for test isolation"""
    return MemorySaver()

@pytest.fixture
def workflow_factory(memory_checkpointer):
    """Factory to create workflow instances with test dependencies"""
    def _create_workflow(**dependencies):
        return create_email_workflow(
            checkpointer=memory_checkpointer,
            **dependencies
        )
    return _create_workflow

@pytest.mark.asyncio
async def test_basic_workflow_execution(workflow_factory):
    """Template for basic workflow test"""
    # Create workflow with dependencies
    workflow = workflow_factory()

    # Initial state
    initial_state = EmailWorkflowState(
        email_id=1,
        user_id=100,
        gmail_message_id="msg_123",
        sender="test@example.com",
        subject="Test Email",
        body_preview="Test content"
    )

    # Configure workflow execution
    config = {"configurable": {"thread_id": "test_thread_123"}}

    # Execute workflow
    result = await workflow.ainvoke(initial_state, config=config)

    # Assert final state
    assert result["status"] == "completed"
```

**Key Takeaway:** Always use MemorySaver for tests (never PostgresSaver), and always use workflow factory pattern for dependency injection.

---

## MemorySaver Integration (Test Isolation)

### Problem Solved

**Issue from Story 2.12 Session 4:**
- Tests sharing PostgresSaver caused state pollution
- One test's checkpoint interfered with another
- ~70% test failure rate due to isolation issues

**Solution:** Use MemorySaver (in-memory, per-test isolation)

### Pattern: Test-Isolated Checkpointer

```python
import pytest
from langgraph.checkpoint.memory import MemorySaver

@pytest.fixture
def memory_checkpointer():
    """
    Create fresh MemorySaver instance for each test.

    MemorySaver provides:
    - In-memory checkpoint storage (no database)
    - Automatic cleanup after test (garbage collected)
    - Zero cross-test contamination
    - Same API as PostgresSaver (drop-in replacement)
    """
    return MemorySaver()

@pytest.fixture
def clean_workflow(memory_checkpointer, mock_dependencies):
    """
    Workflow factory with guaranteed clean state.

    Each test gets:
    - Fresh checkpointer
    - Fresh workflow instance
    - Isolated thread_id namespace
    """
    def _create(thread_id=None):
        if thread_id is None:
            thread_id = f"test_{uuid4()}"  # Unique per test

        workflow = create_email_workflow(
            checkpointer=memory_checkpointer,
            **mock_dependencies
        )

        config = {"configurable": {"thread_id": thread_id}}
        return workflow, config

    return _create

@pytest.mark.asyncio
async def test_with_isolation(clean_workflow):
    """Each test gets isolated workflow + checkpointer"""
    workflow, config = clean_workflow()

    # Test execution - no interference from other tests
    result = await workflow.ainvoke(initial_state, config=config)

    assert result["status"] == "completed"
```

### Thread ID Best Practices

```python
# ❌ BAD: Static thread IDs cause conflicts
config = {"configurable": {"thread_id": "test_thread"}}  # Reused!

# ✅ GOOD: Unique thread IDs per test
from uuid import uuid4

config = {"configurable": {"thread_id": f"test_{uuid4()}"}}

# ✅ BETTER: Fixture generates unique IDs
@pytest.fixture
def unique_config():
    return {"configurable": {"thread_id": f"test_{uuid4()}"}}
```

**Key Takeaway:** MemorySaver + unique thread IDs = perfect test isolation. Never share checkpointers between tests.

---

## Workflow Dependency Injection

### Problem Solved

**Issue from Story 2.12 Session 5:**
- Workflow nodes hardcoded dependencies (GmailClient, GeminiClient)
- Couldn't mock external APIs
- Tests making real API calls (failed, slow, quota issues)

**Solution:** Dependency injection using `functools.partial`

### Pattern: Workflow Factory with Dependency Injection

```python
from functools import partial
from langgraph.graph import StateGraph

def create_email_workflow(
    checkpointer,
    gmail_client=None,
    gemini_client=None,
    telegram_bot=None
):
    """
    Workflow factory supporting dependency injection.

    Args:
        checkpointer: PostgresSaver (production) or MemorySaver (tests)
        gmail_client: Real GmailClient (prod) or MockGmailClient (tests)
        gemini_client: Real GeminiClient (prod) or MockGeminiClient (tests)
        telegram_bot: Real TelegramBot (prod) or MockTelegramBot (tests)

    Returns:
        Compiled workflow with injected dependencies
    """
    # Default to real clients (production)
    if gmail_client is None:
        gmail_client = GmailClient()
    if gemini_client is None:
        gemini_client = GeminiClient()
    if telegram_bot is None:
        telegram_bot = TelegramBot()

    # Build workflow graph
    workflow = StateGraph(EmailWorkflowState)

    # Inject dependencies into nodes using functools.partial
    workflow.add_node(
        "classify",
        partial(classify_node, gemini_client=gemini_client)
    )
    workflow.add_node(
        "send_telegram",
        partial(send_telegram_node, telegram_bot=telegram_bot)
    )
    workflow.add_node(
        "execute_action",
        partial(execute_action_node, gmail_client=gmail_client)
    )

    # Add edges, set entry/finish points
    workflow.add_edge("classify", "send_telegram")
    workflow.add_edge("send_telegram", "execute_action")
    workflow.set_entry_point("classify")
    workflow.set_finish_point("execute_action")

    # Compile with checkpointer
    return workflow.compile(checkpointer=checkpointer)
```

### Pattern: Node Implementation with Dependency Injection

```python
async def classify_node(
    state: EmailWorkflowState,
    gemini_client: GeminiClient  # Injected dependency
) -> EmailWorkflowState:
    """
    Classify email using AI.

    Args:
        state: Current workflow state
        gemini_client: Injected Gemini client (real or mock)

    Returns:
        Updated state with classification
    """
    # Use injected client (works for real or mock)
    classification = await gemini_client.receive_completion(
        prompt=f"Classify this email: {state['body_preview']}"
    )

    # Update state
    state["classification"] = classification
    return state
```

### Pattern: Test with Mocked Dependencies

```python
@pytest.fixture
def mock_gemini_client():
    """Mock Gemini API client"""
    class MockGeminiClient:
        async def receive_completion(self, prompt):
            return "sort_only"  # Deterministic response

    return MockGeminiClient()

@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot"""
    class MockTelegramBot:
        def __init__(self):
            self.messages_sent = []

        async def send_message(self, chat_id, text, **kwargs):
            self.messages_sent.append({"chat_id": chat_id, "text": text})
            return {"message_id": 123}

    return MockTelegramBot()

@pytest.mark.asyncio
async def test_workflow_with_mocks(
    memory_checkpointer,
    mock_gemini_client,
    mock_telegram_bot
):
    """Test workflow with mocked dependencies"""
    # Create workflow with mocks injected
    workflow = create_email_workflow(
        checkpointer=memory_checkpointer,
        gemini_client=mock_gemini_client,
        telegram_bot=mock_telegram_bot
    )

    # Execute workflow
    config = {"configurable": {"thread_id": f"test_{uuid4()}"}}
    result = await workflow.ainvoke(initial_state, config=config)

    # Verify mock interactions
    assert len(mock_telegram_bot.messages_sent) == 1
    assert mock_telegram_bot.messages_sent[0]["text"] == "Email classified"
```

**Key Takeaway:** Use `functools.partial` to inject dependencies into workflow nodes. This enables mocking for tests while keeping production code clean.

---

## Testing Workflow Resumption

### Problem Solved

**Issue from Story 2.12 Session 5:**
- Workflow pauses at `await_approval` node (waiting for Telegram callback)
- Tests needed to simulate resume from paused state
- Checkpoint state not properly persisted/loaded

**Solution:** Explicit checkpoint save → load → resume pattern

### Pattern: Test Pause and Resume

```python
@pytest.mark.asyncio
async def test_workflow_pause_and_resume(memory_checkpointer):
    """
    Test workflow that pauses for user input and resumes later.

    Simulates Epic 2 pattern:
    1. Workflow pauses at await_approval node
    2. User clicks Telegram button (different channel, async)
    3. Callback resumes workflow from checkpoint
    """
    # Create workflow
    workflow = create_email_workflow(checkpointer=memory_checkpointer)
    config = {"configurable": {"thread_id": "test_pause_resume"}}

    # === PHASE 1: Execute until pause ===

    initial_state = EmailWorkflowState(
        email_id=1,
        classification="sort_only"
    )

    # Invoke workflow (will pause at await_approval)
    paused_result = await workflow.ainvoke(initial_state, config=config)

    # Verify workflow paused (not completed)
    assert paused_result["workflow_state"] == "awaiting_approval"
    assert paused_result.get("user_decision") is None

    # === PHASE 2: Simulate async user input ===

    # (In production: user clicks Telegram button hours later)
    # (In test: we simulate immediately)

    # === PHASE 3: Load checkpoint and resume ===

    # Get current state from checkpoint
    checkpoint_state = await workflow.aget_state(config)

    # Verify checkpoint has paused state
    assert checkpoint_state.values["workflow_state"] == "awaiting_approval"

    # Update state with user decision (simulating callback)
    resumed_state = checkpoint_state.values.copy()
    resumed_state["user_decision"] = "approve"

    # Resume workflow with updated state
    final_result = await workflow.ainvoke(resumed_state, config=config)

    # === PHASE 4: Verify completion ===

    assert final_result["workflow_state"] == "completed"
    assert final_result["user_decision"] == "approve"
    assert final_result["status"] == "completed"
```

### Pattern: WorkflowMapping for Cross-Channel Resumption

```python
@pytest.mark.asyncio
async def test_telegram_callback_resumption(
    memory_checkpointer,
    test_db_session,
    mock_telegram_bot
):
    """
    Test Epic 2 pattern: WorkflowMapping enables callback → workflow reconnection.

    Flow:
    1. Email workflow creates WorkflowMapping (email_id → thread_id)
    2. Telegram message sent with email_id in callback_data
    3. User clicks button (separate async event)
    4. Callback handler looks up thread_id from email_id
    5. Workflow resumed using thread_id
    """
    workflow = create_email_workflow(
        checkpointer=memory_checkpointer,
        telegram_bot=mock_telegram_bot
    )

    # === PHASE 1: Workflow execution and pause ===

    email_id = 42
    thread_id = f"email_{email_id}_{uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = EmailWorkflowState(email_id=email_id, user_id=100)
    paused_result = await workflow.ainvoke(initial_state, config=config)

    # Workflow creates WorkflowMapping during send_telegram node
    mapping = WorkflowMapping(
        email_id=email_id,
        user_id=100,
        thread_id=thread_id,
        telegram_message_id=123,
        workflow_state="awaiting_approval"
    )
    test_db_session.add(mapping)
    test_db_session.commit()

    # === PHASE 2: Simulate Telegram callback (hours later) ===

    # Callback handler receives callback_data from button click
    callback_data = f"approve_{email_id}"  # Format: {action}_{email_id}

    # Parse callback data
    action, email_id_str = callback_data.split("_")
    email_id_from_callback = int(email_id_str)

    # Look up thread_id from WorkflowMapping
    mapping = test_db_session.query(WorkflowMapping).filter(
        WorkflowMapping.email_id == email_id_from_callback
    ).first()

    assert mapping is not None
    assert mapping.thread_id == thread_id

    # === PHASE 3: Resume workflow using retrieved thread_id ===

    resume_config = {"configurable": {"thread_id": mapping.thread_id}}

    # Load checkpoint state
    checkpoint = await workflow.aget_state(resume_config)

    # Update with user decision
    resumed_state = checkpoint.values.copy()
    resumed_state["user_decision"] = action  # "approve"

    # Resume execution
    final_result = await workflow.ainvoke(resumed_state, config=resume_config)

    # === PHASE 4: Verify workflow completed ===

    assert final_result["user_decision"] == "approve"
    assert final_result["workflow_state"] == "completed"
```

**Key Takeaway:** Test pause/resume in 3 phases: (1) execute until pause, (2) simulate async event, (3) load checkpoint and resume. Use WorkflowMapping pattern for cross-channel reconnection.

---

## Multi-API Mocking Strategy

### Problem Solved

**Issue from Story 2.12 Sessions 4-5:**
- 11 mock API signature mismatches
- Method names didn't match production (get_message vs get_message_detail)
- Parameter ordering different (telegram_id position)
- Response types wrong (dict vs object)

**Solution:** Mock classes that precisely match production API signatures

### Pattern: Production-Aligned Mock Classes

```python
# backend/tests/mocks/gmail_mock.py

class MockGmailClient:
    """
    Mock Gmail API client matching production signatures EXACTLY.

    CRITICAL: Keep signatures synchronized with app/core/gmail_client.py

    Lessons from Story 2.12:
    - Method names must match exactly (get_message_detail, not get_message)
    - Parameter order must match
    - Return types must match (dict vs EmailMessage object)
    - Default parameters must match
    """

    def __init__(self):
        self.messages = {}  # message_id → message data
        self.labels_applied = []  # Track label operations
        self.call_history = []  # Track all method calls

    async def get_message_detail(self, message_id: str) -> dict:
        """
        Match production signature:
        app/core/gmail_client.py:123
        async def get_message_detail(self, message_id: str) -> dict:

        NOTE: Method name is get_message_DETAIL (not get_message)
        """
        self.call_history.append(("get_message_detail", message_id))

        if message_id in self.messages:
            return self.messages[message_id]

        # Return default structure matching production
        return {
            "id": message_id,
            "threadId": f"thread_{message_id}",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Test Subject"}
                ],
                "body": {"data": "SGVsbG8gV29ybGQ="}  # Base64: Hello World
            }
        }

    async def add_label_to_message(
        self,
        message_id: str,
        label_id: str,
        user_id: int = None  # Optional parameter (production has it)
    ) -> None:
        """
        Match production signature:
        app/core/gmail_client.py:234
        async def add_label_to_message(
            self, message_id: str, label_id: str, user_id: int = None
        ) -> None:

        NOTE: Returns None (not confirmation dict)
        """
        self.call_history.append(("add_label_to_message", message_id, label_id))
        self.labels_applied.append({
            "message_id": message_id,
            "label_id": label_id,
            "user_id": user_id
        })

    def inject_message(self, message_id: str, message_data: dict):
        """Test helper: inject message for retrieval"""
        self.messages[message_id] = message_data

    def verify_label_applied(self, message_id: str, label_id: str) -> bool:
        """Test helper: verify label was applied"""
        return any(
            l["message_id"] == message_id and l["label_id"] == label_id
            for l in self.labels_applied
        )
```

### Pattern: Mock Class with Failure Simulation

```python
class MockGeminiClient:
    """
    Mock Gemini API client with failure simulation.

    Supports:
    - Deterministic responses for testing
    - Failure injection for error handling tests
    - Call tracking for verification
    """

    def __init__(self, should_fail=False, failure_type="timeout"):
        self.should_fail = should_fail
        self.failure_type = failure_type
        self.call_count = 0
        self.call_history = []

    async def receive_completion(self, prompt: str, **kwargs) -> str:
        """
        Match production signature:
        app/core/llm_client.py:67
        async def receive_completion(self, prompt: str, **kwargs) -> str:
        """
        self.call_count += 1
        self.call_history.append({"prompt": prompt, "kwargs": kwargs})

        # Simulate failure if requested
        if self.should_fail:
            if self.failure_type == "timeout":
                raise TimeoutError("Gemini API timeout")
            elif self.failure_type == "rate_limit":
                raise RateLimitError("API quota exceeded")
            elif self.failure_type == "invalid_response":
                return "INVALID JSON {{"  # Malformed response

        # Deterministic response based on prompt content
        if "classify" in prompt.lower():
            return '{"suggested_folder": "Government", "reasoning": "Tax document"}'
        elif "generate response" in prompt.lower():
            return "Thank you for your email. I will review and respond shortly."

        return "Generic AI response"

    def embed(self, text: str) -> list[float]:
        """
        Match production signature for embedding (Epic 3):
        app/core/embedding_service.py:45
        def embed(self, text: str) -> list[float]:

        Returns deterministic 768-dim vector for testing
        """
        # Deterministic hash-based embedding for tests
        hash_val = hash(text) % 1000
        return [float(hash_val + i) for i in range(768)]
```

### Pattern: Pytest Fixture for Auto-Mocking

```python
# backend/tests/conftest.py

import pytest
from unittest.mock import patch
from tests.mocks.gmail_mock import MockGmailClient
from tests.mocks.gemini_mock import MockGeminiClient
from tests.mocks.telegram_mock import MockTelegramBot

@pytest.fixture
def mock_gmail(monkeypatch):
    """Auto-patch GmailClient with MockGmailClient"""
    mock = MockGmailClient()
    monkeypatch.setattr("app.core.gmail_client.GmailClient", lambda: mock)
    return mock

@pytest.fixture
def mock_gemini(monkeypatch):
    """Auto-patch GeminiClient with MockGeminiClient"""
    mock = MockGeminiClient()
    monkeypatch.setattr("app.core.llm_client.GeminiClient", lambda: mock)
    return mock

@pytest.fixture
def mock_all_apis(mock_gmail, mock_gemini, mock_telegram):
    """Convenience fixture for mocking all external APIs"""
    return {
        "gmail": mock_gmail,
        "gemini": mock_gemini,
        "telegram": mock_telegram
    }

# Usage in tests:
@pytest.mark.asyncio
async def test_with_auto_mocking(mock_all_apis):
    """All APIs automatically mocked"""
    result = await some_function_that_calls_apis()

    # Verify mock interactions
    assert mock_all_apis["gemini"].call_count == 1
    assert mock_all_apis["gmail"].verify_label_applied("msg_123", "label_456")
```

**Key Takeaway:** Mock classes MUST match production signatures exactly. Use call tracking and failure injection. Keep mocks synchronized with production code (document file:line references).

---

## Database Persistence in Workflows

### Problem Solved

**Issue from Story 2.12 Session 6:**
- Workflow nodes modified database but didn't commit
- Tests queried database but saw stale data
- WorkflowMapping not created at expected times

**Solution:** Explicit database commits in workflow nodes

### Pattern: Database Operations in Workflow Nodes

```python
from sqlmodel import Session
from app.core.database import get_db_session

async def classify_node(
    state: EmailWorkflowState,
    gemini_client: GeminiClient,
    db_session: Session  # Injected database session
) -> EmailWorkflowState:
    """
    Classify email and persist to database.

    CRITICAL: Must commit database changes within node.
    Tests won't see changes without commit.
    """
    # Call AI classification
    classification = await gemini_client.receive_completion(prompt)

    # Update EmailProcessingQueue in database
    email = db_session.query(EmailProcessingQueue).filter(
        EmailProcessingQueue.id == state["email_id"]
    ).first()

    if email:
        email.classification = classification
        email.status = "classified"
        email.updated_at = datetime.utcnow()

        # CRITICAL: Commit changes
        db_session.commit()

        # Refresh to get updated values
        db_session.refresh(email)

    # Update workflow state
    state["classification"] = classification
    state["workflow_state"] = "classified"

    return state
```

### Pattern: Testing Database Persistence

```python
@pytest.fixture
def test_db_session():
    """
    Create isolated test database session.

    Each test gets:
    - Fresh database transaction
    - Automatic rollback after test (cleanup)
    - Isolated from other tests
    """
    from app.core.database import engine
    from sqlmodel import Session, create_engine

    # Create test database engine
    test_engine = create_engine(
        "postgresql://user:pass@localhost/test_db",
        echo=False
    )

    # Create session
    session = Session(test_engine)

    # Begin transaction
    session.begin()

    yield session

    # Rollback transaction (cleanup)
    session.rollback()
    session.close()

@pytest.mark.asyncio
async def test_database_persistence_in_workflow(
    memory_checkpointer,
    test_db_session,
    mock_gemini
):
    """
    Test that workflow node commits persist to database.

    Verifies Story 2.12 fix: classify node commits WorkflowMapping creation
    """
    # Create workflow with database session injected
    workflow = create_email_workflow(
        checkpointer=memory_checkpointer,
        gemini_client=mock_gemini,
        db_session=test_db_session  # Inject test DB session
    )

    # Create test email in database
    email = EmailProcessingQueue(
        id=1,
        user_id=100,
        gmail_message_id="msg_123",
        sender="test@example.com",
        status="pending"
    )
    test_db_session.add(email)
    test_db_session.commit()

    # Execute workflow
    config = {"configurable": {"thread_id": "test_db_persist"}}
    result = await workflow.ainvoke(
        EmailWorkflowState(email_id=1, user_id=100),
        config=config
    )

    # === CRITICAL TEST: Verify database was updated ===

    # Refresh email from database
    test_db_session.refresh(email)

    # Verify node committed classification
    assert email.classification == "sort_only"  # From mock
    assert email.status == "classified"
    assert email.updated_at is not None

    # Verify WorkflowMapping was created and committed
    mapping = test_db_session.query(WorkflowMapping).filter(
        WorkflowMapping.email_id == 1
    ).first()

    assert mapping is not None
    assert mapping.thread_id == "test_db_persist"
    assert mapping.workflow_state == "classified"
```

### Pattern: Transaction Management in Tests

```python
@pytest.mark.asyncio
async def test_workflow_with_transaction_isolation():
    """
    Test workflow database operations with proper transaction isolation.

    Demonstrates:
    - Each test gets isolated transaction
    - Changes visible within test
    - Automatic rollback after test
    """
    # Setup: Create test data
    user = User(id=100, email="test@example.com")
    test_db_session.add(user)
    test_db_session.commit()

    # Execute: Run workflow that modifies database
    result = await workflow.ainvoke(state, config=config)

    # Verify: Check database changes within test transaction
    modified_user = test_db_session.query(User).filter(User.id == 100).first()
    assert modified_user.telegram_id == 12345  # Workflow set this

    # Cleanup: Automatic rollback after test (pytest fixture)
```

**Key Takeaway:** Workflow nodes MUST commit database changes explicitly. Tests need isolated database sessions with transaction management. Always refresh database objects after workflow execution to see changes.

---

## Testing Cross-Channel Workflows

### Problem Solved

**Issue from Story 2.12:**
- Workflow pauses in backend, user responds in Telegram (different process)
- Need to test reconnection across channels
- Thread ID lookup from email ID critical for resumption

**Solution:** WorkflowMapping pattern + explicit resumption testing

### Pattern: Epic 2 Cross-Channel Workflow Test

```python
@pytest.mark.asyncio
async def test_complete_cross_channel_workflow(
    memory_checkpointer,
    test_db_session,
    mock_gmail,
    mock_gemini,
    mock_telegram
):
    """
    Test Epic 2 complete cross-channel workflow:

    Channel 1 (Email Processing):
    1. Email arrives → classify → send Telegram proposal
    2. Workflow PAUSES at await_approval node
    3. WorkflowMapping created (email_id → thread_id)

    Channel 2 (Telegram - hours later, different process):
    4. User clicks [Approve] button
    5. Callback receives email_id from button data
    6. Look up thread_id from WorkflowMapping
    7. Resume workflow using thread_id

    Channel 1 (Email Processing resumes):
    8. Execute action (apply Gmail label)
    9. Send confirmation to Telegram
    10. Mark workflow completed
    """

    # === CHANNEL 1: Email Processing (Workflow Execution) ===

    email_id = 42
    user_id = 100
    thread_id = f"email_{email_id}_{uuid4()}"

    # Create workflow
    workflow = create_email_workflow(
        checkpointer=memory_checkpointer,
        gmail_client=mock_gmail,
        gemini_client=mock_gemini,
        telegram_bot=mock_telegram,
        db_session=test_db_session
    )

    # Create test email
    email = EmailProcessingQueue(
        id=email_id,
        user_id=user_id,
        gmail_message_id="msg_test_123",
        sender="finanzamt@berlin.de",
        subject="Tax Deadline",
        body_preview="Please submit by...",
        status="pending"
    )
    test_db_session.add(email)
    test_db_session.commit()

    # Execute workflow (will pause at await_approval)
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = EmailWorkflowState(
        email_id=email_id,
        user_id=user_id,
        gmail_message_id="msg_test_123"
    )

    paused_result = await workflow.ainvoke(initial_state, config=config)

    # Verify workflow paused
    assert paused_result["workflow_state"] == "awaiting_approval"

    # Verify WorkflowMapping was created by send_telegram node
    mapping = test_db_session.query(WorkflowMapping).filter(
        WorkflowMapping.email_id == email_id
    ).first()

    assert mapping is not None
    assert mapping.thread_id == thread_id
    assert mapping.telegram_message_id == 123  # From mock
    assert mapping.workflow_state == "awaiting_approval"

    # Verify Telegram message sent
    assert len(mock_telegram.messages_sent) == 1
    telegram_msg = mock_telegram.messages_sent[0]
    assert "Tax Deadline" in telegram_msg["text"]
    assert telegram_msg["buttons"] is not None  # Has [Approve] etc

    # === CHANNEL 2: Telegram Callback (Simulated) ===

    # Simulate: User clicks [Approve] button in Telegram (hours later)
    callback_data = f"approve_{email_id}"

    # Telegram callback handler receives callback_data
    action, callback_email_id_str = callback_data.split("_")
    callback_email_id = int(callback_email_id_str)

    # Look up WorkflowMapping to get thread_id
    callback_mapping = test_db_session.query(WorkflowMapping).filter(
        WorkflowMapping.email_id == callback_email_id
    ).first()

    assert callback_mapping is not None
    resume_thread_id = callback_mapping.thread_id

    # === CHANNEL 1: Workflow Resumption ===

    # Create resume config using looked-up thread_id
    resume_config = {"configurable": {"thread_id": resume_thread_id}}

    # Get current checkpoint state
    checkpoint = await workflow.aget_state(resume_config)

    # Update state with user decision
    resumed_state = checkpoint.values.copy()
    resumed_state["user_decision"] = action  # "approve"

    # Resume workflow execution
    final_result = await workflow.ainvoke(resumed_state, config=resume_config)

    # === VERIFICATION: Complete Workflow ===

    # Verify workflow completed
    assert final_result["workflow_state"] == "completed"
    assert final_result["user_decision"] == "approve"

    # Verify Gmail label was applied
    assert mock_gmail.verify_label_applied("msg_test_123", "label_government")

    # Verify confirmation message sent to Telegram
    assert len(mock_telegram.messages_sent) == 2  # Proposal + confirmation
    confirmation = mock_telegram.messages_sent[1]
    assert "✅" in confirmation["text"]
    assert "Government" in confirmation["text"]

    # Verify database updated
    test_db_session.refresh(email)
    assert email.status == "completed"

    # Verify WorkflowMapping updated
    test_db_session.refresh(mapping)
    assert mapping.workflow_state == "completed"
```

**Key Takeaway:** Cross-channel testing requires: (1) pause at boundary, (2) create mapping, (3) simulate async event, (4) lookup thread_id, (5) resume workflow. Test the complete round-trip.

---

## Common Pitfalls and Solutions

### Pitfall 1: LangGraph API Version Mismatch

**Problem:**
```python
# ❌ BAD: LangGraph v1 API (deprecated)
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver(connection_string)
```

**Solution:**
```python
# ✅ GOOD: LangGraph v2 API (current)
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(connection_string)
```

**Lesson from Story 2.12 Session 4:** API changed between v1 and v2. Always use `PostgresSaver.from_conn_string()` for production, `MemorySaver()` for tests.

---

### Pitfall 2: Forgetting Database Commits

**Problem:**
```python
# ❌ BAD: Database update without commit
async def classify_node(state, db_session):
    email = db_session.query(Email).filter(Email.id == state["email_id"]).first()
    email.classification = "sort_only"
    # Missing: db_session.commit()
    return state
```

**Solution:**
```python
# ✅ GOOD: Explicit commit in workflow node
async def classify_node(state, db_session):
    email = db_session.query(Email).filter(Email.id == state["email_id"]).first()
    email.classification = "sort_only"
    db_session.commit()  # CRITICAL
    db_session.refresh(email)
    return state
```

**Lesson from Story 2.12 Session 6:** Tests won't see database changes without commits. Always commit within workflow nodes.

---

### Pitfall 3: Mock Signature Mismatch

**Problem:**
```python
# ❌ BAD: Mock has different parameter order than production
class MockTelegramBot:
    async def send_message(self, text, chat_id):  # Wrong order!
        pass

# Production:
# async def send_message(self, chat_id, text):  # Correct order
```

**Solution:**
```python
# ✅ GOOD: Mock matches production signature exactly
class MockTelegramBot:
    async def send_message(self, chat_id, text, **kwargs):  # Match production
        self.messages_sent.append({"chat_id": chat_id, "text": text})
        return {"message_id": 123}
```

**Lesson from Story 2.12 Session 5:** 11 API signature mismatches found. Keep mocks synchronized with production. Document source location in mock docstring.

---

### Pitfall 4: Shared Thread IDs

**Problem:**
```python
# ❌ BAD: All tests use same thread_id (state pollution)
config = {"configurable": {"thread_id": "test_thread"}}

@pytest.mark.asyncio
async def test_1(workflow):
    await workflow.ainvoke(state, config=config)  # Uses "test_thread"

@pytest.mark.asyncio
async def test_2(workflow):
    await workflow.ainvoke(state, config=config)  # Reuses "test_thread" - CONFLICT!
```

**Solution:**
```python
# ✅ GOOD: Unique thread_id per test
from uuid import uuid4

@pytest.mark.asyncio
async def test_1(workflow):
    config = {"configurable": {"thread_id": f"test_{uuid4()}"}}
    await workflow.ainvoke(state, config=config)

@pytest.mark.asyncio
async def test_2(workflow):
    config = {"configurable": {"thread_id": f"test_{uuid4()}"}}
    await workflow.ainvoke(state, config=config)
```

**Lesson from Story 2.12 Session 4:** Shared thread IDs cause checkpoint contamination. Always use unique IDs.

---

### Pitfall 5: Not Testing Workflow Resumption

**Problem:**
```python
# ❌ BAD: Only tests initial execution (not resume)
@pytest.mark.asyncio
async def test_workflow(workflow):
    result = await workflow.ainvoke(initial_state, config=config)
    assert result["status"] == "completed"
    # Never tests pause/resume functionality
```

**Solution:**
```python
# ✅ GOOD: Tests pause AND resume
@pytest.mark.asyncio
async def test_workflow_with_resume(workflow):
    # Phase 1: Execute until pause
    paused = await workflow.ainvoke(initial_state, config=config)
    assert paused["workflow_state"] == "awaiting_approval"

    # Phase 2: Load checkpoint
    checkpoint = await workflow.aget_state(config)

    # Phase 3: Update and resume
    resumed_state = checkpoint.values.copy()
    resumed_state["user_decision"] = "approve"
    final = await workflow.ainvoke(resumed_state, config=config)

    assert final["status"] == "completed"
```

**Lesson from Epic 2:** If workflow pauses, MUST test resumption. Otherwise critical bugs hide until production.

---

## Epic 3 Specific Patterns

### Pattern: Testing RAG Context Retrieval Workflows

```python
@pytest.mark.asyncio
async def test_rag_workflow_with_vector_db(
    memory_checkpointer,
    mock_vector_db,
    mock_gemini
):
    """
    Test Epic 3 RAG workflow:
    1. Retrieve context (thread + semantic search)
    2. Generate response using context
    3. Send response draft to Telegram
    """
    # Create RAG workflow
    workflow = create_response_generation_workflow(
        checkpointer=memory_checkpointer,
        vector_db=mock_vector_db,
        gemini_client=mock_gemini
    )

    # Mock vector DB returns similar emails
    mock_vector_db.inject_similar_emails([
        {"id": "msg_1", "content": "Previous tax discussion"},
        {"id": "msg_2", "content": "Related deadline email"}
    ])

    # Execute workflow
    config = {"configurable": {"thread_id": f"rag_test_{uuid4()}"}}
    result = await workflow.ainvoke(
        ResponseWorkflowState(email_id=1, user_id=100),
        config=config
    )

    # Verify context retrieval
    assert len(result["rag_context"]["thread_history"]) == 5
    assert len(result["rag_context"]["semantic_results"]) == 3

    # Verify response generation
    assert result["response_draft"] is not None
    assert len(result["response_draft"]) > 50  # Non-trivial response
```

---

## Summary: Story 2.12 Lessons Applied to Epic 3

| Issue from Story 2.12 | Pattern to Use in Epic 3 |
|----------------------|--------------------------|
| 93% missing tests (17 of 18) | Specify exact test count in Task 2 template |
| LangGraph API compatibility | Use MemorySaver for tests, PostgresSaver.from_conn_string() for prod |
| Dependency injection issues | Use functools.partial for all workflow nodes |
| Mock signature mismatches | Keep mocks synchronized with production (document file:line) |
| Database persistence bugs | Explicit commits in workflow nodes |
| Cross-channel resumption | Test pause → lookup → resume complete flow |
| Thread ID conflicts | Unique thread_id per test (uuid4) |
| Workflow state management | Test aget_state → update → ainvoke pattern |

---

## Quick Reference Checklist

When writing LangGraph tests for Epic 3:

- [ ] Use MemorySaver (never PostgresSaver in tests)
- [ ] Use unique thread_id per test (uuid4)
- [ ] Inject dependencies via functools.partial
- [ ] Keep mock signatures matching production exactly
- [ ] Commit database changes within workflow nodes
- [ ] Test pause/resume for workflows that pause
- [ ] Use WorkflowMapping pattern for cross-channel resumption
- [ ] Verify mock interactions (call_count, parameters)
- [ ] Test failure scenarios (API timeouts, rate limits)
- [ ] Use isolated database transactions per test

---

**Document Version:** 1.0
**Last Updated:** 2025-11-09
**Next Review:** After Epic 3 Story 3.1 completion (validate patterns work)
**Maintenance:** Update after each epic with new patterns discovered
