# LangGraph Learning Guide for Epic 2
**Created:** 2025-11-06
**For:** Story 2.3 - AI Email Classification Service
**Status:** Preparation Sprint - Task 1.1

---

## 📚 Overview

LangGraph is a framework for building **stateful, multi-step applications** with large language models (LLMs). It's perfect for our Epic 2 use case: **human-in-the-loop email classification workflows**.

**Why LangGraph for Mail Agent?**
- ✅ **Persistent workflows** - Pause email classification, wait for Telegram response, resume
- ✅ **State management** - Track email processing status across async operations
- ✅ **PostgreSQL checkpointing** - Durable state storage for reliability
- ✅ **Human-in-the-loop** - Built-in support for external approvals (Telegram buttons)
- ✅ **Multi-step flows** - Email arrives → AI classifies → User approves → Label applied

---

## 🎯 Core Concepts for Story 2.3

### 1. **Graph = Workflow**
A LangGraph "graph" models your workflow as nodes and edges:
- **Nodes** = Steps in your workflow (e.g., "classify_email", "wait_for_approval", "apply_label")
- **Edges** = Transitions between steps (e.g., "after classification, wait for approval")

```python
from langgraph.graph import StateGraph, END

# Define workflow
workflow = StateGraph(EmailState)
workflow.add_node("classify", classify_email)
workflow.add_node("wait_approval", wait_for_telegram)
workflow.add_node("apply_label", apply_gmail_label)

# Define transitions
workflow.set_entry_point("classify")
workflow.add_edge("classify", "wait_approval")
workflow.add_edge("wait_approval", "apply_label")
workflow.add_edge("apply_label", END)
```

---

### 2. **State = Shared Data**
State is shared data that flows through your workflow:

```python
from typing import TypedDict

class EmailState(TypedDict):
    email_id: str
    message_id: str
    sender: str
    subject: str
    body: str
    user_categories: list[str]
    suggested_folder: str  # AI classification result
    reasoning: str         # AI reasoning
    user_action: str       # "approve", "reject", "change"
    final_folder: str      # Final folder after user decision
    status: str            # "pending", "awaiting_approval", "completed"
```

**Key Principle:** Nodes read from state, update state, and pass it to next node.

---

### 3. **Checkpointing = Pause & Resume**
**Checkpointers** save workflow state to a database (PostgreSQL) so workflows can:
- ✅ Pause execution (e.g., wait for Telegram button click)
- ✅ Resume from last checkpoint when external event happens
- ✅ Survive server restarts (durable execution)

**For Mail Agent:**
1. Email arrives → LangGraph workflow starts
2. AI classifies → Workflow saves checkpoint → **PAUSES**
3. Telegram message sent with buttons
4. User clicks button (minutes/hours later) → Workflow **RESUMES** from checkpoint
5. Label applied → Workflow completes

---

### 4. **PostgresSaver = Checkpoint Storage**
Store checkpoints in PostgreSQL (we already have PostgreSQL from Epic 1!):

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Connect to existing PostgreSQL database
DB_URI = "postgresql://user:password@localhost:5432/mailagent"
checkpointer = PostgresSaver.from_conn_string(DB_URI)

# Compile workflow with checkpointing
app = workflow.compile(checkpointer=checkpointer)
```

**Database Setup:**
PostgresSaver automatically creates checkpoint tables in your database. No manual migration needed!

---

### 5. **Thread ID = Workflow Instance**
Each email workflow gets a **thread_id** (unique identifier):

```python
config = {"configurable": {"thread_id": f"email-{email_id}"}}

# Start workflow
app.invoke(initial_state, config=config)

# Later: Resume workflow when Telegram button clicked
app.invoke({"user_action": "approve"}, config=config)
```

**Thread ID** reconnects Telegram callbacks to the correct workflow instance.

---

## 🛠️ Implementation Pattern for Story 2.3

### Step 1: Define State Schema

```python
from typing import TypedDict, Literal

class EmailClassificationState(TypedDict):
    # Input data (from email monitoring)
    email_id: str
    gmail_message_id: str
    gmail_thread_id: str
    user_id: str
    sender: str
    subject: str
    body: str

    # User configuration
    folder_categories: list[dict]  # [{name: "Government", gmail_label_id: "..."}]

    # AI classification results
    suggested_folder: str
    reasoning: str
    confidence: float

    # User interaction
    telegram_message_id: str
    user_action: Literal["approve", "reject", "change"]
    selected_folder: str | None

    # Workflow status
    status: Literal["pending", "classifying", "awaiting_approval", "completed", "error"]
    error_message: str | None
```

---

### Step 2: Create Workflow Nodes

```python
async def classify_email_node(state: EmailClassificationState):
    """Node 1: Use Gemini to classify email"""
    # Call Gemini API with prompt
    classification = await gemini_classify(
        sender=state["sender"],
        subject=state["subject"],
        body=state["body"],
        categories=state["folder_categories"]
    )

    # Update state
    return {
        "suggested_folder": classification["folder"],
        "reasoning": classification["reasoning"],
        "confidence": classification["confidence"],
        "status": "awaiting_approval"
    }


async def send_telegram_proposal_node(state: EmailClassificationState):
    """Node 2: Send Telegram message with approval buttons"""
    message_id = await send_telegram_message(
        user_id=state["user_id"],
        sender=state["sender"],
        subject=state["subject"],
        suggested_folder=state["suggested_folder"],
        reasoning=state["reasoning"]
    )

    # Save telegram_message_id to reconnect callback
    return {
        "telegram_message_id": message_id
    }


async def wait_for_approval_node(state: EmailClassificationState):
    """Node 3: PAUSE here - wait for Telegram callback"""
    # This node does nothing - workflow pauses here via interrupt()
    # Workflow will resume when Telegram callback provides user_action
    from langgraph.checkpoint import interrupt

    # Interrupt execution until external input arrives
    user_decision = interrupt("Waiting for user approval via Telegram")

    return {"user_action": user_decision}


async def apply_label_node(state: EmailClassificationState):
    """Node 4: Apply Gmail label based on user decision"""
    if state["user_action"] == "approve":
        folder = state["suggested_folder"]
    elif state["user_action"] == "change":
        folder = state["selected_folder"]
    else:  # reject
        # Leave in inbox, mark completed
        return {"status": "completed"}

    # Apply Gmail label
    await gmail_client.apply_label(
        message_id=state["gmail_message_id"],
        label_name=folder
    )

    return {"status": "completed", "final_folder": folder}
```

---

### Step 3: Build the Graph

```python
from langgraph.graph import StateGraph, END

# Create graph
workflow = StateGraph(EmailClassificationState)

# Add nodes
workflow.add_node("classify", classify_email_node)
workflow.add_node("send_proposal", send_telegram_proposal_node)
workflow.add_node("wait_approval", wait_for_approval_node)
workflow.add_node("apply_label", apply_label_node)

# Define workflow flow
workflow.set_entry_point("classify")
workflow.add_edge("classify", "send_proposal")
workflow.add_edge("send_proposal", "wait_approval")
workflow.add_edge("wait_approval", "apply_label")
workflow.add_edge("apply_label", END)

# Compile with PostgreSQL checkpointer
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = os.getenv("DATABASE_URL")
checkpointer = PostgresSaver.from_conn_string(DB_URI)

app = workflow.compile(checkpointer=checkpointer)
```

---

### Step 4: Start Workflow (Email Arrives)

```python
async def on_new_email(email_data: dict):
    """Called when email monitoring detects new email"""

    # Load user's folder categories from database
    folder_categories = await db.get_user_categories(email_data["user_id"])

    # Create initial state
    initial_state = {
        "email_id": email_data["id"],
        "gmail_message_id": email_data["gmail_message_id"],
        "gmail_thread_id": email_data["gmail_thread_id"],
        "user_id": email_data["user_id"],
        "sender": email_data["sender"],
        "subject": email_data["subject"],
        "body": email_data["body"],
        "folder_categories": folder_categories,
        "status": "pending"
    }

    # Start workflow with unique thread_id
    thread_id = f"email-{email_data['id']}"
    config = {"configurable": {"thread_id": thread_id}}

    # Invoke workflow (will pause at wait_approval node)
    result = await app.ainvoke(initial_state, config=config)

    # Workflow is now paused, waiting for Telegram callback
    # Store thread_id in WorkflowMapping table for callback reconnection
    await db.save_workflow_mapping(
        email_id=email_data["id"],
        user_id=email_data["user_id"],
        thread_id=thread_id,
        telegram_message_id=result["telegram_message_id"],
        workflow_state="awaiting_approval"
    )
```

---

### Step 5: Resume Workflow (Telegram Button Clicked)

```python
async def on_telegram_callback(callback_query):
    """Called when user clicks button in Telegram"""

    # Parse callback data
    email_id = callback_query.data["email_id"]
    user_action = callback_query.data["action"]  # "approve", "reject", "change"
    selected_folder = callback_query.data.get("folder")

    # Retrieve workflow thread_id from database
    workflow_mapping = await db.get_workflow_mapping(email_id=email_id)
    thread_id = workflow_mapping["thread_id"]

    # Resume workflow with user decision
    config = {"configurable": {"thread_id": thread_id}}
    resume_state = {
        "user_action": user_action,
        "selected_folder": selected_folder
    }

    # Resume workflow - will continue from wait_approval node
    result = await app.ainvoke(resume_state, config=config)

    # Workflow completes - label applied!
    await telegram_bot.send_confirmation(
        user_id=workflow_mapping["user_id"],
        message=f"✅ Email sorted to {result['final_folder']}"
    )
```

---

## 🗄️ Database Schema for Story 2.6

**WorkflowMapping Table** (required for reconnecting Telegram callbacks):

```sql
CREATE TABLE workflow_mapping (
    id SERIAL PRIMARY KEY,
    email_id INTEGER UNIQUE NOT NULL REFERENCES email_processing_queue(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    thread_id VARCHAR(255) UNIQUE NOT NULL,
    telegram_message_id BIGINT,
    workflow_state VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_workflow_mappings_thread_id (thread_id),
    INDEX idx_workflow_mappings_user_state (user_id, workflow_state)
);
```

**Why this table is critical:**
- Maps `email_id` ↔ `thread_id` for workflow reconnection
- Maps `telegram_message_id` ↔ `thread_id` for callback routing
- Tracks `workflow_state` for monitoring

---

## 🧪 Testing LangGraph Locally

### Simple Test: Hello World Workflow

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver  # In-memory for testing
from typing import TypedDict

class State(TypedDict):
    message: str
    count: int

def node1(state: State):
    print(f"Node 1: {state['message']}")
    return {"count": state.get("count", 0) + 1}

def node2(state: State):
    print(f"Node 2: Count is {state['count']}")
    return {"message": "Workflow complete!"}

# Build graph
workflow = StateGraph(State)
workflow.add_node("step1", node1)
workflow.add_node("step2", node2)
workflow.set_entry_point("step1")
workflow.add_edge("step1", "step2")
workflow.add_edge("step2", END)

# Compile with in-memory checkpointer for testing
app = workflow.compile(checkpointer=MemorySaver())

# Run workflow
config = {"configurable": {"thread_id": "test-1"}}
result = app.invoke({"message": "Hello LangGraph!", "count": 0}, config=config)
print(result)
# Output: {'message': 'Workflow complete!', 'count': 1}
```

---

### Test with Pause/Resume (Simulating Telegram Callback)

```python
from langgraph.checkpoint.postgres import interrupt

def pause_node(state: State):
    """Node that pauses workflow"""
    print("Pausing workflow, waiting for external input...")
    external_input = interrupt("Waiting for user action")
    print(f"Resumed with input: {external_input}")
    return {"message": external_input}

# Add pause_node to workflow
workflow.add_node("pause", pause_node)
# ...

# Start workflow - will pause at pause_node
config = {"configurable": {"thread_id": "test-pause"}}
try:
    result = app.invoke({"message": "Start"}, config=config)
except Exception as e:
    print(f"Workflow paused: {e}")

# Resume workflow with external input
result = app.invoke({"message": "User approved!"}, config=config)
print(result)
```

---

## 📦 Dependencies for Story 2.3

Add to `requirements.txt` or `pyproject.toml`:

```txt
langgraph>=0.2.0
langgraph-checkpoint-postgres>=0.1.0
psycopg2-binary>=2.9.0  # PostgreSQL adapter (if not already installed)
```

---

## ✅ Key Takeaways for Story 2.3

1. **LangGraph = Stateful Workflows**
   - Perfect for multi-step, pause/resume email classification

2. **PostgresSaver = Durable Checkpointing**
   - Store workflow state in existing PostgreSQL database
   - Workflows survive server restarts

3. **interrupt() = Human-in-the-Loop**
   - Pause workflow execution at specific node
   - Resume when external event (Telegram callback) arrives

4. **thread_id = Workflow Instance**
   - Unique ID reconnects Telegram callback to correct workflow
   - Store in `workflow_mapping` table

5. **State = Shared Data**
   - Flows through all nodes
   - Updated incrementally by each node

---

## 🔗 Official Resources

- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **Human-in-the-Loop Tutorial:** https://langchain-ai.github.io/langgraph/tutorials/get-started/4-human-in-the-loop/
- **Persistence Guide:** https://langchain-ai.github.io/langgraph/concepts/persistence/
- **PostgreSQL Checkpointer:** https://langchain-ai.github.io/langgraph/how-tos/persistence/

---

## 🎯 Next Steps

After understanding this guide:

1. ✅ Install LangGraph dependencies
2. ✅ Test simple workflow locally (Hello World example)
3. ✅ Test pause/resume pattern (simulating Telegram callback)
4. ✅ Create technical spec for Story 2.3 using these patterns
5. ✅ Ready to implement AI Email Classification Service!

---

**Status:** 📚 Learning guide complete - ready for Story 2.3 implementation!
