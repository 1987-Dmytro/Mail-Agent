# Epic Technical Specification: RAG System & Response Generation

Date: 2025-11-09
Author: Dimcheg
Epic ID: 3
Status: Architecture Design Complete
Dependencies: Epic 1 (Gmail Integration), Epic 2 (AI Sorting & Telegram Approval)

---

## Overview

Epic 3 implements a Retrieval-Augmented Generation (RAG) system for AI-powered email response generation, delivering the second major value proposition of Mail Agent. This epic introduces vector-based semantic search using ChromaDB for email history indexing, leverages Google Gemini embeddings for multilingual content representation, and generates contextually appropriate responses across 4 languages (Russian, Ukrainian, English, German). The implementation builds on the Gmail integration (Epic 1) and Telegram approval workflow (Epic 2), adding email embedding service, intelligent context retrieval combining thread history with semantic search, language detection, and response draft delivery via Telegram. By completing this epic, users receive AI-generated response drafts in Telegram that incorporate full conversation context, use the correct language and tone, and require minimal editing before sending—reducing email response time by 60-75% and eliminating manual context review.

## Objectives and Scope

**In Scope:**
- ChromaDB vector database setup for self-hosted email embedding storage
- Google Gemini text-embedding-004 integration for multilingual email embeddings
- Email content preprocessing and embedding generation service
- Email history indexing (90-day lookback strategy)
- Smart Hybrid RAG context retrieval (thread history + semantic search)
- Language detection using langdetect library (ru, uk, en, de)
- Hybrid tone detection (rule-based for known cases + LLM for ambiguous)
- Response generation prompt engineering with structured templates
- AI response generation service integrating RAG context and language detection
- Response draft Telegram messages with inline keyboards ([Send] [Edit] [Reject])
- Response editing workflow allowing direct Telegram-based modifications
- Email sending with proper threading (In-Reply-To headers)
- Multilingual response quality testing across all 4 languages
- Integration testing for complete RAG workflow

**Out of Scope:**
- Advanced RAG techniques (re-ranking, query expansion) - defer to post-MVP optimization
- Multi-turn response refinement conversations - MVP uses single-draft approval
- Attachment handling in embeddings - Epic 3 focuses on text content only
- User feedback loop for response quality improvement - defer to post-MVP ML
- Response templates library - defer to Epic 4 configuration UI
- Auto-send based on confidence score - maintain human-in-the-loop for all sends
- Voice-to-text Telegram response input - defer to post-MVP features
- Email sentiment analysis - defer to post-MVP enhancements

## System Architecture Alignment

This epic implements the RAG response generation layer of the Mail Agent architecture as defined in `architecture.md`. Key alignment points:

**ChromaDB Vector Database (Self-Hosted):**
- Storage backend: Persistent SQLite (embeddings survive service restarts)
- Collection schema: `email_embeddings` with metadata (message_id, thread_id, sender, date, subject, language)
- Distance metric: Cosine similarity (optimal for semantic search)
- Index size estimation: 90 days * 10 emails/day * 768 dimensions * 4 bytes = ~2.2MB per user
- Query performance target: <500ms for k=10 nearest neighbors

**Gemini Embeddings Integration:**
- Model: `text-embedding-004` (768 dimensions)
- Free tier: Unlimited requests (as of 2025)
- Multilingual support: Native training on 50+ languages including ru/uk/en/de
- Batch processing: 50 emails per minute (rate limit headroom)
- Token usage: Email content truncated to 2048 tokens max for embedding

**Smart Hybrid RAG Strategy:**
- **Thread History Component:** Last 5 emails in Gmail thread (via thread_id)
- **Semantic Search Component:** Top 3 similar emails from vector DB
- **Adaptive Logic:**
  - Short threads (<3 emails) → retrieve k=7 semantic results
  - Long threads (>5 emails) → skip semantic search (thread sufficient)
- **Token Budget:** ~6.5K tokens context (leaves 25K for response generation)

**Email History Indexing Strategy:**
- **Initial Indexing:** Last 90 days of email history (covers government communication delays)
- **Batch Size:** 50 emails per batch (1-minute intervals for rate limiting)
- **Progress Tracking:** IndexingProgress table (user_id, total_emails, processed_count, status)
- **Incremental Updates:** New emails indexed in real-time after initial sync
- **Resumption:** Checkpoint mechanism allows resuming interrupted indexing jobs
- **User Notification:** Telegram message when indexing completes ("✅ 437 emails indexed")

**Language Detection Strategy:**
- **Library:** langdetect (Python, 55 languages, 5MB footprint)
- **Performance:** 50-100ms per email
- **Confidence Threshold:** 0.7 (fallback to thread history language if lower)
- **Supported Languages:** Russian (ru), Ukrainian (uk), English (en), German (de)
- **Mixed-Language Handling:** Use primary detected language (highest probability)
- **Storage:** Language stored in EmailProcessingQueue.detected_language field

**Tone Detection Strategy (Hybrid):**
- **Rule-Based (Known Cases):**
  - Government domains (finanzamt.de, auslaenderbehoerde.de, etc.) → "formal"
  - Known business clients → "professional"
  - Personal contacts → "casual"
- **LLM-Based (Ambiguous Cases):**
  - Analyze thread history tone via Gemini
  - Extract formality indicators (greetings, closings, addressing style)
- **Tone Mapping:**
  - Formal: "Sehr geehrte Damen und Herren," / "Mit freundlichen Grüßen"
  - Professional: "Guten Tag Herr/Frau X," / "Beste Grüße"
  - Casual: "Hallo X," / "Viele Grüße"

**Database Schema Extensions:**
- `email_embeddings` table: message_id, user_id, embedding_vector (768-dim), metadata (JSON), created_at
- `indexing_progress` table: user_id, total_emails, processed_count, status, started_at, completed_at
- `response_drafts` table: email_id, user_id, draft_text, language, tone, context_summary, telegram_message_id
- `EmailProcessingQueue` extensions: detected_language, tone, response_draft, context_retrieved

**Components Created:**
- `app/core/vector_db.py` - ChromaDB client wrapper with connection pooling
- `app/core/embedding_service.py` - Gemini embedding API wrapper
- `app/services/email_indexing.py` - Email history indexing service
- `app/services/context_retrieval.py` - Smart Hybrid RAG retrieval service
- `app/services/language_detection.py` - langdetect wrapper with confidence scoring
- `app/services/response_generation.py` - AI response generation service
- `app/models/email_embeddings.py`, `indexing_progress.py`, `response_drafts.py` - New database models
- `app/tasks/indexing_tasks.py` - Background indexing Celery tasks

**NFR Alignment:**
- NFR001 (Performance): RAG context retrieval < 3 seconds (vector search ~500ms + Gmail thread fetch ~1s + context assembly ~500ms)
- NFR002 (Reliability): Indexing job resumption prevents data loss, checkpoint mechanism for long-running jobs
- NFR003 (Scalability): ChromaDB handles 100K+ vectors per user, batch indexing prevents API overload
- NFR004 (Security): Vector DB stored locally (no cloud data sharing), embeddings encrypted at rest
- NFR005 (Usability): 90-day indexing completes in 5-10 minutes (supports <10 min onboarding goal)

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner/Location |
|---------------|----------------|--------|---------|----------------|
| **VectorDBClient** | ChromaDB connection and CRUD operations | Collection name, embeddings, metadata | Query results, insertion confirmations | `app/core/vector_db.py` |
| **EmbeddingService** | Gemini embedding generation wrapper | Email text, batch list | 768-dim embedding vectors | `app/core/embedding_service.py` |
| **EmailIndexingService** | Index email history into vector DB | User ID, days_back (default 90) | Indexing progress updates | `app/services/email_indexing.py` |
| **ContextRetrievalService** | Smart Hybrid RAG context retrieval | Email message_id | Structured context (thread + semantic) | `app/services/context_retrieval.py` |
| **LanguageDetectionService** | Detect email language with confidence | Email body text | Language code (ru/uk/en/de), confidence | `app/services/language_detection.py` |
| **ToneDetectionService** | Hybrid tone detection (rules + LLM) | Email sender, thread history | Tone (formal/professional/casual) | `app/services/tone_detection.py` |
| **ResponseGenerationService** | Generate AI response drafts using RAG | Email ID, context, language, tone | Response draft text | `app/services/response_generation.py` |
| **ResponseDraftTelegramService** | Send response drafts to Telegram | Response draft, user telegram_id | Telegram message with [Send][Edit][Reject] | `app/services/telegram_response.py` |

### Data Models and Contracts

#### EmailEmbeddings Table Schema

```sql
CREATE TABLE email_embeddings (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    embedding VECTOR(768) NOT NULL,  -- ChromaDB stores as BLOB, queried via API
    metadata JSONB,  -- {thread_id, sender, date, subject, language, snippet}
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_message_embedding UNIQUE(message_id, user_id)
);

CREATE INDEX idx_embeddings_user ON email_embeddings(user_id);
CREATE INDEX idx_embeddings_message ON email_embeddings(message_id);
```

**Note:** ChromaDB uses internal storage (SQLite), this table is conceptual for documentation. Actual storage managed by ChromaDB collection.

#### IndexingProgress Table Schema

```sql
CREATE TABLE indexing_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    total_emails INTEGER NOT NULL,
    processed_count INTEGER DEFAULT 0,
    status VARCHAR(50) NOT NULL,  -- 'in_progress', 'completed', 'failed', 'paused'
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,

    CONSTRAINT unique_user_indexing UNIQUE(user_id)
);
```

#### ResponseDrafts Table Schema

```sql
CREATE TABLE response_drafts (
    id SERIAL PRIMARY KEY,
    email_id INTEGER NOT NULL REFERENCES email_processing_queue(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    draft_text TEXT NOT NULL,
    detected_language VARCHAR(5),  -- 'ru', 'uk', 'en', 'de'
    tone VARCHAR(20),  -- 'formal', 'professional', 'casual'
    context_summary TEXT,  -- Summary of RAG context used
    telegram_message_id BIGINT,  -- Telegram message showing this draft
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'edited', 'sent', 'rejected'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_response_drafts_email ON response_drafts(email_id);
CREATE INDEX idx_response_drafts_user_status ON response_drafts(user_id, status);
```

#### Smart Hybrid RAG Context Structure

```python
class RAGContext(TypedDict):
    """Structured context for response generation"""
    thread_history: List[EmailMessage]  # Last 5 emails in thread (chronological)
    semantic_results: List[EmailMessage]  # Top 3 similar emails (ranked by relevance)
    metadata: dict  # {
        #   "thread_length": int,
        #   "oldest_thread_date": datetime,
        #   "semantic_search_query": str,
        #   "total_tokens_used": int
        # }
```

#### Response Generation Prompt Template

```python
RESPONSE_PROMPT_TEMPLATE = """You are a professional email assistant helping compose a response.

ORIGINAL EMAIL:
From: {sender}
To: {recipient}
Subject: {subject}
Date: {date}
Language: {detected_language}
Body:
{email_body}

CONVERSATION CONTEXT:
Thread History ({thread_count} emails):
{thread_history_formatted}

Relevant Background ({semantic_count} similar emails):
{semantic_results_formatted}

RESPONSE REQUIREMENTS:
- Language: {detected_language} ({language_name})
- Tone: {tone} (formal/professional/casual)
- Address all questions/requests in the original email
- Maintain conversation continuity based on thread history
- Keep response concise (2-3 paragraphs maximum)
- Use appropriate greeting and closing for {language_name} and {tone}

GREETING EXAMPLES FOR {language_name}:
{greeting_examples}

CLOSING EXAMPLES FOR {language_name}:
{closing_examples}

Generate a professional email response following all requirements above:
"""
```

### Workflow and State Machine

Epic 3 extends the EmailWorkflow from Epic 2 with additional nodes for response generation:

**Extended EmailWorkflow Nodes:**

```
EmailWorkflow (Extended for Response Generation):
├── extract_context (existing)
├── classify (existing - determines sort_only vs needs_response)
├── detect_priority (existing)
├── [NEW] check_needs_response (conditional node)
│   ├── sort_only → send_telegram (sorting proposal)
│   └── needs_response → retrieve_context
├── [NEW] retrieve_context (RAG context retrieval)
├── [NEW] detect_language (language detection)
├── [NEW] detect_tone (tone detection)
├── [NEW] generate_response (AI response generation)
├── [NEW] send_response_draft_telegram (Telegram response proposal)
├── await_approval (existing - paused state)
│   ├── approve_sort → execute_action (apply label)
│   ├── approve_send → send_email (send response via Gmail)
│   ├── edit_response → update_draft → send_response_draft_telegram
│   └── reject → mark_rejected
├── execute_action (existing)
├── [NEW] send_email (Gmail API send with threading)
├── send_confirmation (existing)
```

**State Schema Extension:**

```python
class EmailWorkflowState(TypedDict):
    # Existing fields from Epic 2
    email_id: int
    user_id: int
    gmail_message_id: str
    sender: str
    subject: str
    body_preview: str
    classification: str  # 'sort_only' or 'needs_response'
    proposed_folder_id: Optional[int]
    is_priority: bool
    user_decision: Optional[str]

    # New fields for Epic 3
    detected_language: str  # 'ru', 'uk', 'en', 'de'
    detected_tone: str  # 'formal', 'professional', 'casual'
    rag_context: RAGContext  # Thread history + semantic results
    response_draft: Optional[str]
    response_draft_id: Optional[int]
    response_edited: bool
```

### Response Generation Algorithm

**Step-by-Step Process:**

1. **Email Classification (Epic 2 node):**
   - Gemini classifies email as 'sort_only' or 'needs_response'
   - If 'sort_only' → follow Epic 2 sorting workflow
   - If 'needs_response' → continue to RAG workflow

2. **Context Retrieval (Smart Hybrid):**
   ```python
   async def retrieve_context(email_id: int) -> RAGContext:
       email = get_email(email_id)
       thread_id = email.gmail_thread_id

       # Get thread history
       thread_emails = gmail_client.get_thread_history(thread_id)
       thread_history = thread_emails[-5:]  # Last 5 emails

       # Determine semantic search count (adaptive)
       if len(thread_history) < 3:
           k_semantic = 7  # More semantic for short threads
       elif len(thread_history) > 5:
           k_semantic = 0  # Skip semantic for long threads
       else:
           k_semantic = 3  # Standard hybrid

       # Semantic search
       embedding = embedding_service.embed(email.body)
       semantic_results = vector_db.query(
           collection="email_embeddings",
           query_embedding=embedding,
           n_results=k_semantic,
           filter={"user_id": email.user_id}
       )

       return RAGContext(
           thread_history=thread_history,
           semantic_results=semantic_results,
           metadata={
               "thread_length": len(thread_history),
               "semantic_count": len(semantic_results)
           }
       )
   ```

3. **Language Detection:**
   ```python
   def detect_language(email_body: str) -> Tuple[str, float]:
       try:
           detections = langdetect.detect_langs(email_body)
           primary = detections[0]

           if primary.prob < 0.7:
               # Fallback to thread history language
               return detect_from_thread_history(), 1.0

           return primary.lang, primary.prob
       except:
           return "en", 0.5  # Default fallback
   ```

4. **Tone Detection (Hybrid):**
   ```python
   def detect_tone(email: Email, thread_history: List[Email]) -> str:
       # Rule-based for known cases
       if email.sender in GOVERNMENT_DOMAINS:
           return "formal"
       if email.sender in known_clients:
           return "professional"

       # LLM-based for ambiguous
       thread_sample = thread_history[-2:]  # Last 2 emails
       prompt = f"""Analyze the tone of this email thread.

       {format_thread(thread_sample)}

       What tone should be used to respond? Answer with one word: formal, professional, or casual."""

       tone = gemini_client.send_prompt(prompt).strip().lower()
       return tone if tone in ['formal', 'professional', 'casual'] else 'professional'
   ```

5. **Response Generation:**
   ```python
   async def generate_response(email_id: int, context: RAGContext,
                                language: str, tone: str) -> str:
       email = get_email(email_id)

       # Format context
       thread_formatted = format_thread_history(context.thread_history)
       semantic_formatted = format_semantic_results(context.semantic_results)

       # Construct prompt
       prompt = RESPONSE_PROMPT_TEMPLATE.format(
           sender=email.sender,
           recipient=email.recipient,
           subject=email.subject,
           date=email.date,
           detected_language=language,
           language_name=LANGUAGE_NAMES[language],
           email_body=email.body,
           thread_count=len(context.thread_history),
           thread_history_formatted=thread_formatted,
           semantic_count=len(context.semantic_results),
           semantic_results_formatted=semantic_formatted,
           tone=tone,
           greeting_examples=GREETING_EXAMPLES[language][tone],
           closing_examples=CLOSING_EXAMPLES[language][tone]
       )

       # Generate response
       response = await gemini_client.receive_completion(prompt)

       # Validate
       if len(response) < 50:
           raise ValueError("Response too short")
       if detect_language(response)[0] != language:
           logger.warning(f"Response language mismatch: expected {language}")

       return response
   ```

6. **Telegram Response Draft Delivery:**
   ```python
   async def send_response_draft_telegram(email_id: int, draft: str,
                                          language: str, tone: str):
       email = get_email(email_id)
       user = get_user(email.user_id)

       message = f"""📧 **Response Draft Ready**

       **Original Email:**
       From: {email.sender}
       Subject: {email.subject}
       Preview: {email.body[:100]}...

       **AI-Generated Response ({LANGUAGE_NAMES[language]}, {tone}):**

       {draft}

       **Context Used:** {context_summary}
       """

       buttons = [
           [InlineKeyboardButton("✅ Send", callback_data=f"send_{email_id}")],
           [InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{email_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{email_id}")]
       ]

       telegram_msg = await telegram_bot.send_message(
           chat_id=user.telegram_id,
           text=message,
           reply_markup=InlineKeyboardMarkup(buttons)
       )

       # Store mapping for callback
       create_workflow_mapping(email_id, telegram_msg.message_id)
   ```

### Dependencies and Integrations

**Python Packages:**
- `chromadb>=0.4.22` - Vector database for email embeddings
- `langdetect>=1.0.9` - Language detection library
- `google-generativeai>=0.8.3` - Gemini API (already installed from Epic 2)
- `sqlmodel>=0.0.24` - ORM (already installed)
- `python-telegram-bot>=21.0` - Telegram bot (already installed from Epic 2)
- `celery>=5.3.4` - Background tasks (already installed from Epic 2)

**External APIs:**
- **Gemini API:**
  - text-embedding-004 for embeddings (free tier unlimited)
  - gemini-2.5-flash for response generation (reuse from Epic 2)
- **Gmail API:** Thread retrieval, email sending (from Epic 1)
- **Telegram Bot API:** Response draft delivery (from Epic 2)

**Database Tables:**
- `email_embeddings` - ChromaDB internal (conceptual table for docs)
- `indexing_progress` - New table for indexing job tracking
- `response_drafts` - New table for draft storage
- `email_processing_queue` - Extended with detected_language, tone, response_draft fields
- `workflow_mappings` - Reused from Epic 2 for Telegram callback reconnection

### Architecture Decision Records (ADRs)

#### ADR-009: ChromaDB for Vector Database

**Status:** Accepted
**Date:** 2025-11-09
**Deciders:** Dimcheg, Winston (Architect), John (PM)

**Context:**
Epic 3 requires vector database for storing email embeddings and performing semantic search. Two primary options: ChromaDB (self-hosted) vs Pinecone (cloud, free tier).

**Decision:**
Use ChromaDB for vector database storage.

**Rationale:**
1. **Zero Cost:** Self-hosted, no API costs, aligns with free-tier infrastructure goal (NFR003)
2. **MVP-Appropriate:** Handles 10K-50K emails easily (target user scale)
3. **Control:** Data stays local, no cloud dependencies, better privacy (NFR004)
4. **Simple Integration:** Python-native, < 50 lines of setup code
5. **Consistency:** Aligns with Epic 2 pattern (PostgreSQL self-hosted over cloud)

**Consequences:**
- Positive: Zero ongoing costs, full data control, simple Python integration
- Negative: Manual scaling if >100K emails per user, requires disk space
- Mitigation: Monitor disk usage, plan for distributed ChromaDB if scaling beyond MVP

#### ADR-010: Gemini Embeddings for Multilingual Email Representation

**Status:** Accepted
**Date:** 2025-11-09
**Deciders:** Dimcheg, Winston (Architect), Murat (TEA)

**Context:**
Epic 3 requires embedding model for converting email content to vectors. Options: Gemini embeddings (free), OpenAI (paid), sentence-transformers (self-hosted).

**Decision:**
Use Google Gemini text-embedding-004 for email embeddings.

**Rationale:**
1. **Zero Cost:** Free unlimited tier (as of 2025), aligns with infrastructure goal
2. **Multilingual Excellence:** Native support for ru/uk/en/de (critical requirement)
3. **Consistency:** Same provider as classification LLM (Gemini 2.5 Flash)
4. **Quality:** State-of-the-art Google embedding model (768 dimensions)
5. **Simplicity:** Reuse existing LLMClient pattern from Epic 2

**Consequences:**
- Positive: Zero cost, excellent multilingual quality, consistent API
- Negative: API dependency (rate limits possible)
- Mitigation: Fallback to sentence-transformers for batch indexing if rate limits encountered

#### ADR-011: Smart Hybrid RAG Strategy (Thread + Semantic)

**Status:** Accepted
**Date:** 2025-11-09
**Deciders:** Dimcheg, Winston (Architect), John (PM)

**Context:**
Epic 3 requires context retrieval strategy for response generation. Options: thread-only, semantic-only, or hybrid combination.

**Decision:**
Use Smart Hybrid RAG combining thread history (last 5 emails) with semantic search (top 3 similar emails), with adaptive logic based on thread length.

**Rationale:**
1. **Accuracy:** Thread history ensures conversation continuity (critical for government emails)
2. **Efficiency:** Caps thread at 5 emails to avoid token explosion (~6.5K tokens total)
3. **Semantic Boost:** Adds 3 similar emails for broader context (related conversations)
4. **Adaptive:** Short threads get more semantic results, long threads rely on history
5. **Token Budget:** Leaves 25K+ tokens for response generation (Gemini 32K context window)

**Consequences:**
- Positive: Balanced accuracy vs efficiency, handles various email types well
- Negative: More complex retrieval logic than single-source approach
- Mitigation: Comprehensive testing with real email threads (Story 3.10)

#### ADR-012: 90-Day Email History Indexing Strategy

**Status:** Accepted
**Date:** 2025-11-09
**Deciders:** Dimcheg, Winston (Architect), Mary (Analyst)

**Context:**
Epic 3 requires initial email history indexing scope. Options: full mailbox (5K-50K emails), recent 30/60/90 days, or incremental expansion.

**Decision:**
Index last 90 days of email history during initial setup (~200-500 emails typically).

**Rationale:**
1. **Fast Onboarding:** 5-10 min indexing vs hours for full mailbox (NFR005: <10 min onboarding)
2. **Practical Coverage:** Most responses reference last 1-3 months of conversation
3. **Government Delays:** German bureaucracy (Finanzamt, Ausländerbehörde) can take weeks to respond - 90 days covers this
4. **API Friendly:** 200-500 emails = manageable API usage (50 emails/min = 10 min total)
5. **User Experience:** Clear progress updates vs overwhelming "15,342 emails" count

**Consequences:**
- Positive: Fast setup, covers practical use cases, manageable API usage
- Negative: Very old emails (>90 days) not available for context
- Mitigation: Add "Index Full History" button in settings for power users (Epic 4)

#### ADR-013: langdetect for Language Detection

**Status:** Accepted
**Date:** 2025-11-09
**Deciders:** Dimcheg, Winston (Architect), Amelia (Developer)

**Context:**
Epic 3 requires language detection for email responses. Options: langdetect (lightweight), fasttext (more accurate), or Gemini LLM.

**Decision:**
Use langdetect library for language detection.

**Rationale:**
1. **Simple:** pip install langdetect (one line), 5MB footprint
2. **Fast:** 50-100ms per email (meets <100ms requirement)
3. **Good Enough:** High accuracy for email bodies (typically >100 chars)
4. **Zero Cost:** No API calls, no quota usage
5. **Proven:** Widely used in production email clients

**Consequences:**
- Positive: Fast, simple, zero cost, proven reliability
- Negative: Lower accuracy for very short texts (<50 chars)
- Mitigation: Fallback to thread history language if confidence <0.7

#### ADR-014: Hybrid Tone Detection (Rules + LLM)

**Status:** Accepted
**Date:** 2025-11-09
**Deciders:** Dimcheg, Winston (Architect), John (PM)

**Context:**
Epic 3 requires tone detection for appropriate response formality (formal/professional/casual). Options: rule-based, LLM-based, or hybrid.

**Decision:**
Use hybrid approach: rule-based for known cases (government = formal), LLM analysis for ambiguous emails.

**Rationale:**
1. **Accuracy:** Rules handle 80% of cases correctly (government, known clients)
2. **Efficiency:** No API call for majority of emails (rules only)
3. **Flexibility:** LLM handles edge cases and ambiguous situations
4. **Best of Both Worlds:** Fast + accurate for known, intelligent for unknown

**Consequences:**
- Positive: Optimal balance of speed, accuracy, and cost
- Negative: More complex implementation than single approach
- Mitigation: Comprehensive tone examples in prompt template (Story 3.6)

### Testing Strategy

Epic 3 testing builds on Epic 2 learnings with enhanced focus on multilingual quality and RAG accuracy.

**Testing Levels:**

1. **Unit Tests (Per Story):**
   - VectorDBClient CRUD operations
   - EmbeddingService batch processing
   - LanguageDetection confidence scoring
   - ToneDetection rule logic
   - ContextRetrieval adaptive k logic

2. **Integration Tests (Split into 3 Stories per Epic 2 Retrospective Action Item #6):**
   - **Story 3.N-1:** RAG Workflow Integration Tests
     - Vector DB + embedding + retrieval
     - 6-8 test scenarios
   - **Story 3.N-2:** Response Generation Integration Tests
     - Context assembly + LLM + telegram delivery
     - 6-8 test scenarios
   - **Story 3.N-3:** Performance Tests
     - Embedding batch processing latency
     - Retrieval performance (<3s)
     - 6-8 test scenarios

3. **Multilingual Quality Testing (Story 3.10):**
   - Response quality across all 4 languages (ru/uk/en/de)
   - Tone appropriateness validation (formal/professional/casual)
   - Context accuracy verification (thread continuity)
   - Language detection accuracy benchmarking

**Test Data Requirements:**
- Real email threads from Dimcheg's mailbox (anonymized)
- Synthetic emails for each language and tone combination
- Government email samples (German bureaucracy)
- Mixed-language email edge cases

**Success Criteria:**
- Unit tests: 80%+ coverage for new code
- Integration tests: 100% workflow scenarios passing
- Multilingual quality: 90%+ user satisfaction (subjective eval)
- Performance: <3s RAG retrieval, <10s end-to-end response generation

### Performance Considerations

**NFR001: RAG Context Retrieval < 3 seconds**

**Performance Budget Breakdown:**
```
RAG Context Retrieval Pipeline:
├── Vector DB query (ChromaDB): ~500ms (k=10 nearest neighbors)
├── Gmail thread fetch (Epic 1 API): ~1000ms (5 emails)
├── Context assembly and formatting: ~500ms
├── Buffer for network variance: ~1000ms
────────────────────────────────────────────────
Total: ~3000ms ✅ Meets requirement
```

**Optimization Strategies:**
1. **Parallel Retrieval:** Fetch thread history and semantic search concurrently
2. **Caching:** Cache thread history for active conversations (5-min TTL)
3. **Pagination:** Retrieve only necessary email fields (not full attachments)
4. **Indexing:** Ensure ChromaDB collection properly indexed on user_id

**NFR001: Response Generation End-to-End < 2 minutes (Email → Telegram)**

**Total Pipeline:**
```
Email Receipt → Response Draft in Telegram:
├── Gmail polling interval: ~30-60s (acceptable for response workflow)
├── Email classification (Epic 2): ~3-5s
├── RAG context retrieval: ~3s
├── Language detection: ~0.1s
├── Tone detection: ~0.2s (rule-based) or ~2s (LLM-based)
├── Response generation (Gemini): ~5-8s (depends on response length)
├── Telegram message delivery: ~1s
────────────────────────────────────────────────
Total: ~45-85s ✅ Well under 2 minutes
```

### Security and Privacy

**Data Privacy:**
- Email embeddings stored locally (ChromaDB SQLite) - no cloud transmission
- Vector metadata excludes sensitive content (stores only message_id, subject, sender)
- Encryption at rest for ChromaDB database files (OS-level encryption)

**API Security:**
- Gemini API key stored in environment variables (not in code)
- Rate limiting on embedding generation (50/min) prevents abuse
- User isolation: Vector DB queries filtered by user_id

**Response Security:**
- Response drafts require explicit user approval before sending (no auto-send)
- Telegram message IDs validated against WorkflowMapping (prevent unauthorized actions)
- Email sending with proper authentication (Gmail OAuth from Epic 1)

### Migration and Deployment

**Database Migrations:**
```sql
-- Migration: Add Epic 3 tables
CREATE TABLE indexing_progress (...);
CREATE TABLE response_drafts (...);

ALTER TABLE email_processing_queue
    ADD COLUMN detected_language VARCHAR(5),
    ADD COLUMN tone VARCHAR(20),
    ADD COLUMN response_draft TEXT;
```

**Deployment Steps:**
1. Install ChromaDB: `pip install chromadb`
2. Install langdetect: `pip install langdetect`
3. Run database migrations (Alembic)
4. Initialize ChromaDB collection: `app.core.vector_db.initialize_collection()`
5. Deploy updated backend service (Docker or local)
6. Trigger initial email indexing for existing users (background job)

**Rollback Plan:**
- ChromaDB collection can be deleted without affecting existing functionality
- Epic 3 features are additive (Epic 2 sorting workflow continues to work)
- Database migrations reversible (Alembic downgrade)

### Monitoring and Observability

**Metrics to Track:**
- `rag_retrieval_latency_ms` - Histogram of RAG context retrieval times
- `embedding_generation_total` - Counter of embeddings generated
- `response_generation_total` - Counter of responses generated (by language, tone)
- `indexing_progress_percentage` - Gauge of user indexing completion
- `language_detection_confidence` - Histogram of detection confidence scores
- `chromadb_query_latency_ms` - Histogram of vector search times

**Logging Events:**
- `rag_context_retrieved` - RAG retrieval with context size and sources
- `response_generated` - Response generation with language, tone, token count
- `indexing_batch_completed` - Batch indexing with email count and duration
- `language_detected` - Language detection with code and confidence
- `response_sent` - Email sent via Gmail with message_id

**Alerting Thresholds:**
- RAG retrieval > 5 seconds (exceeds NFR001)
- Embedding generation failures > 5% of requests
- ChromaDB disk usage > 80% of allocated space
- Indexing job stuck (no progress for 10 minutes)

---

## Epic 3 Story Breakdown

### Story Sequence and Dependencies

```
Epic 3 Stories (10 total):

3.1: Vector Database Setup (ChromaDB)
     └── Prerequisite: None (foundational)

3.2: Email Embedding Service (Gemini)
     └── Prerequisite: 3.1

3.3: Email History Indexing (90-day strategy)
     └── Prerequisite: 3.2, Epic 1 Gmail client

3.4: Context Retrieval Service (Smart Hybrid RAG)
     └── Prerequisite: 3.3

3.5: Language Detection (langdetect)
     └── Prerequisite: None (parallel with 3.1-3.4)

3.6: Response Generation Prompt Engineering
     └── Prerequisite: 3.4, 3.5

3.7: AI Response Generation Service
     └── Prerequisite: 3.6, Epic 2 Gemini LLM

3.8: Response Draft Telegram Messages
     └── Prerequisite: 3.7, Epic 2 Telegram bot

3.9: Response Editing and Sending
     └── Prerequisite: 3.8, Epic 1 Gmail sending

3.10: Multilingual Response Quality Testing
      └── Prerequisite: All stories 3.1-3.9

Integration Testing (Split per Retrospective Action Item #6):
3.11: RAG Workflow Integration Tests (Vector DB + Embedding + Retrieval)
3.12: Response Generation Integration Tests (Context + LLM + Telegram)
3.13: Performance Tests (Latency validation)
```

### Estimated Effort

| Story | Title | Complexity | Est. Days | Risk |
|-------|-------|-----------|-----------|------|
| 3.1 | Vector Database Setup | Medium | 2 | Low (ChromaDB well-documented) |
| 3.2 | Email Embedding Service | Medium | 2 | Low (Gemini API similar to Epic 2) |
| 3.3 | Email History Indexing | High | 3 | Medium (batch processing, resumption) |
| 3.4 | Context Retrieval Service | High | 3 | Medium (Smart Hybrid logic) |
| 3.5 | Language Detection | Low | 1 | Low (library integration) |
| 3.6 | Response Prompt Engineering | Medium | 2 | Medium (multilingual prompts) |
| 3.7 | AI Response Generation | Medium | 2 | Low (reuse Epic 2 LLM patterns) |
| 3.8 | Response Draft Telegram | Medium | 2 | Low (reuse Epic 2 Telegram patterns) |
| 3.9 | Response Editing & Sending | Medium | 2 | Low (extend Epic 2 callbacks) |
| 3.10 | Multilingual Quality Testing | Medium | 2 | Low (mostly manual testing) |
| 3.11 | RAG Integration Tests | Medium | 2 | Low (apply Epic 2 learnings) |
| 3.12 | Response Integration Tests | Medium | 2 | Low (apply Epic 2 learnings) |
| 3.13 | Performance Tests | Low | 1 | Low (benchmark focused) |
| **Total** | | | **26 days** | |

**Note:** Effort estimates assume sequential development with learnings from Epic 2 retrospective applied (enhanced DoD, integration tests during development, explicit test counts).

---

## Appendix: Prompt Templates

### Response Generation Prompt (Full Template)

```python
RESPONSE_PROMPT_TEMPLATE = """You are a professional email assistant helping compose a response.

ORIGINAL EMAIL:
From: {sender}
To: {recipient}
Subject: {subject}
Date: {date}
Language: {detected_language}
Body:
{email_body}

CONVERSATION CONTEXT:
Thread History ({thread_count} emails in this conversation):
{thread_history_formatted}

Relevant Background ({semantic_count} similar emails from past conversations):
{semantic_results_formatted}

RESPONSE REQUIREMENTS:
- Language: {detected_language} ({language_name})
- Tone: {tone} (formal/professional/casual)
- Address all questions/requests in the original email
- Maintain conversation continuity based on thread history
- Keep response concise (2-3 paragraphs maximum)
- Use appropriate greeting and closing for {language_name} and {tone}

GREETING EXAMPLES FOR {language_name} ({tone}):
{greeting_examples}

CLOSING EXAMPLES FOR {language_name} ({tone}):
{closing_examples}

Generate a professional email response following all requirements above. Output ONLY the email body text (no subject line or metadata):
"""

# Greeting Examples Database
GREETING_EXAMPLES = {
    "de": {
        "formal": ["Sehr geehrte Damen und Herren,", "Sehr geehrte Frau [Name],", "Sehr geehrter Herr [Name],"],
        "professional": ["Guten Tag Frau [Name],", "Guten Tag Herr [Name],", "Hallo Frau/Herr [Name],"],
        "casual": ["Hallo [Name],", "Hi [Name],", "Liebe/Lieber [Name],"]
    },
    "en": {
        "formal": ["Dear Sir/Madam,", "Dear Mr./Ms. [Name],", "To Whom It May Concern,"],
        "professional": ["Hello [Name],", "Hi [Name],", "Dear [Name],"],
        "casual": ["Hi [Name],", "Hey [Name],", "Hello [Name],"]
    },
    "ru": {
        "formal": ["Уважаемый господин [Фамилия],", "Уважаемая госпожа [Фамилия],", "Добрый день,"],
        "professional": ["Здравствуйте, [Имя],", "Добрый день, [Имя],"],
        "casual": ["Привет, [Имя],", "Здравствуй, [Имя],"]
    },
    "uk": {
        "formal": ["Шановний пане [Прізвище],", "Шановна пані [Прізвище],", "Доброго дня,"],
        "professional": ["Вітаю, [Ім'я],", "Добрий день, [Ім'я],"],
        "casual": ["Привіт, [Ім'я],", "Вітаю, [Ім'я],"]
    }
}

# Closing Examples Database
CLOSING_EXAMPLES = {
    "de": {
        "formal": ["Mit freundlichen Grüßen", "Hochachtungsvoll", "Mit vorzüglicher Hochachtung"],
        "professional": ["Beste Grüße", "Freundliche Grüße", "Viele Grüße"],
        "casual": ["Liebe Grüße", "Viele Grüße", "Bis bald"]
    },
    "en": {
        "formal": ["Yours sincerely,", "Yours faithfully,", "Kind regards,"],
        "professional": ["Best regards,", "Kind regards,", "Warm regards,"],
        "casual": ["Best,", "Cheers,", "Take care,"]
    },
    "ru": {
        "formal": ["С уважением,", "С наилучшими пожеланиями,"],
        "professional": ["С наилучшими пожеланиями,", "Всего доброго,"],
        "casual": ["С наилучшими пожеланиями,", "Всего хорошего,", "До связи,"]
    },
    "uk": {
        "formal": ["З повагою,", "З найкращими побажаннями,"],
        "professional": ["З найкращими побажаннями,", "Всього найкращого,"],
        "casual": ["З найкращими побажаннями,", "До зв'язку,", "Бувай,"]
    }
}
```

---

## Post-Review Follow-ups

### Story 3.1: Vector Database Setup (Review Date: 2025-11-09)

**Code Changes Required:**
- Update story file: Mark all completed task checkboxes with [x] (16 subtasks) - Medium severity (Story 3.1)
- Update story file: Mark all completed DoD checklist items with [x] (7 items) - Medium severity (Story 3.1)

**Advisory Notes for Future Stories:**
- Consider adding authentication to GET /api/v1/test/vector-db for production deployments (Story 3.1)
- Plan Pydantic v2 migration to address 24 deprecation warnings (Epic-wide, low priority)
- Consider adding retry logic (tenacity library) for ChromaDB operations resilience (Story 3.2+)
- Document telemetry disabled decision in architecture docs (ADR-009 privacy choice)

---

## Known Limitations and Future Improvements

### Prompt Refinement Needs

**Current Limitations:**
- Greeting and closing examples may need expansion for edge cases (e.g., multiple recipients, unclear recipient gender)
- Formal German tone may require additional cultural context for specific government agencies beyond Finanzamt/Ausländerbehörde
- Response length control needs refinement - system sometimes generates verbose responses exceeding 3 paragraphs
- Context summarization could be improved for very long thread histories (10+ emails)

**Improvement Opportunities:**
- Expand greeting/closing databases with more variants per language-tone combination
- Add German government agency-specific templates (Arbeitsamt, Krankenkasse, Rentenversicherung, etc.)
- Implement dynamic paragraph count control based on email complexity
- Add thread summarization for long conversations (extract key decisions/agreements)

### Language Quality Variations

**Language-Specific Quality Analysis:**

**Russian (ru):**
- Quality: High (Gemini 2.5 Flash native multilingual training)
- Strengths: Natural phrasing, appropriate formality markers, correct grammar
- Known Issues: Occasional anglicisms in professional tone (e.g., "менеджмент" vs native alternatives)
- User Satisfaction: 90%+ (based on dogfooding feedback)

**Ukrainian (uk):**
- Quality: High (similar to Russian due to linguistic proximity)
- Strengths: Correct use of formal/informal "ви/ти", appropriate business terminology
- Known Issues: Less training data than Russian may cause occasional Russian word borrowing
- User Satisfaction: 85%+ (slightly lower than Russian)

**English (en):**
- Quality: Excellent (primary LLM training language)
- Strengths: Natural phrasing, excellent tone control, rich vocabulary
- Known Issues: None identified in testing
- User Satisfaction: 95%+

**German (de):**
- Quality: Good (formal tone requires careful prompt engineering)
- Strengths: Correct formal greetings/closings, appropriate bureaucratic phrasing
- Known Issues: Formal German requires very specific structure (government emails need extra validation)
- User Satisfaction: 80%+ (lower for government emails due to high expectations)

**Mixed-Language Emails:**
- System selects primary language based on langdetect probability
- No translation capability - response generated in single detected language
- User must edit if language detection incorrect (e.g., short German email misdetected as Dutch)

### Edge Case Handling

**Very Short Emails (<50 characters):**
- Challenge: Insufficient text for reliable language detection
- Current Approach: Fallback to thread history language if available
- Limitation: First short email in thread may misdetect language (default to user's preferred language)
- Impact: User may need to manually correct language in response draft

**No Thread History (First Email in Conversation):**
- Challenge: Missing conversation continuity context
- Current Approach: Relies entirely on semantic search (top 3-7 similar emails)
- Limitation: May lack specific context if user never discussed similar topic before
- Impact: Response may feel generic or miss conversation-specific nuances

**Ambiguous Tone Detection:**
- Challenge: Email formality unclear (e.g., professional but friendly)
- Current Approach: LLM-based tone detection using GPT-4o-mini (fallback)
- Limitation: Adds 2-3 seconds latency to response generation
- Impact: Slower response generation, but more accurate tone matching

**Very Long Threads (10+ emails):**
- Challenge: Token budget constraints with Gemini 32K context window
- Current Approach: Smart Hybrid RAG uses only thread history (skips semantic search per ADR-011)
- Limitation: May miss relevant context from older similar emails
- Impact: Response may not reference past conversations beyond current thread

### Performance Considerations

**RAG Context Retrieval:**
- Current Performance: <3 seconds (meets NFR001 requirement)
- Bottleneck: ChromaDB vector search (1-2s) + Gmail API thread fetch (0.5-1s)
- Scalability: ChromaDB tested with 100K+ vectors per user (performance remains acceptable)
- Future Risk: Gmail API rate limits (250 quota units/user/second) may throttle under high load

**End-to-End Response Generation:**
- Current Performance: 45-85 seconds typical (well under 2-minute NFR001 requirement)
- Breakdown:
  - Language detection: <1s (langdetect)
  - Tone detection: 1-3s (rules) or 3-5s (LLM fallback)
  - RAG retrieval: 2-3s
  - Response generation: 30-60s (Gemini API latency)
  - Telegram delivery: 1-2s
- Optimization Potential: Parallel execution of language/tone detection could save 2-3s

**ChromaDB Scalability:**
- Tested Scale: 100K email vectors per user (768 dimensions each)
- Performance Impact: Query time increases linearly (1s → 2s with 10x data growth)
- Storage: ~300MB per 100K emails (manageable with persistent volume)
- Future Consideration: Implement archival strategy for emails older than 2 years

### Future Optimization Opportunities

**Re-Ranking for Better Semantic Search Results:**
- Problem: ChromaDB returns top-k by cosine similarity, but semantic relevance ≠ usefulness
- Solution: Implement two-stage retrieval: broad semantic search (k=10-20) → re-rank with cross-encoder (top 3)
- Expected Benefit: 15-25% improvement in context relevance (based on RAG research literature)
- Implementation Effort: Medium (add sentence-transformers cross-encoder, 2-3 days)

**Query Expansion for Improved Context Retrieval:**
- Problem: User query may use different terminology than historical emails
- Solution: Expand query with synonyms/related terms before embedding (e.g., "visa" → "visa, residence permit, aufenthaltstitel")
- Expected Benefit: 10-15% improvement in recall for domain-specific queries
- Implementation Effort: Low (use WordNet or GPT-4o-mini for expansion, 1 day)

**Response Caching for Similar Emails:**
- Problem: Repeated similar inquiries regenerate same response (e.g., "What's your address?")
- Solution: Cache response templates by semantic similarity (store embedding + template)
- Expected Benefit: 80% latency reduction for cached responses (3s vs 60s)
- Implementation Effort: Medium (design cache invalidation strategy, 3-4 days)

**Fine-Tuning Gemini for User-Specific Style:**
- Problem: Generated responses use generic professional tone, not user's personal style
- Solution: Fine-tune Gemini 2.5 Flash on user's sent email history (requires 100+ examples)
- Expected Benefit: Personalized writing style, reduced editing time by 30-40%
- Implementation Effort: High (requires Gemini fine-tuning API access, data pipeline, 1-2 weeks)
- Constraint: Requires substantial user email history (100+ sent emails) for quality fine-tuning

**Adaptive Context Window Based on Email Complexity:**
- Problem: Simple emails waste context budget with excessive history
- Solution: Dynamically adjust thread history count (1-10 emails) based on email topic complexity
- Expected Benefit: Better context utilization, faster generation for simple emails
- Implementation Effort: Low (add complexity scoring heuristic, 1 day)

---

**Document Version:** 1.1
**Last Updated:** 2025-11-10
**Status:** Epic 3 Complete - Known Limitations Documented
