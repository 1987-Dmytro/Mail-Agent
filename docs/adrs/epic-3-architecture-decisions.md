# Epic 3 Architecture Decision Records

**Date:** 2025-11-09
**Epic:** 3 - RAG System & Response Generation
**Status:** Decisions Finalized
**Decision Makers:** Dimcheg (User/Developer), Winston (Architect), John (PM)

---

## Summary of Decisions

During the Epic 3 preparation sprint, we made 6 critical architectural decisions that define the RAG system implementation. All decisions prioritize the zero-cost infrastructure goal while maintaining high multilingual quality for Russian, Ukrainian, English, and German email responses.

---

## ADR-009: ChromaDB for Vector Database

**Status:** ✅ Accepted
**Date:** 2025-11-09

### Context

Epic 3 requires vector database for storing email embeddings and performing semantic search to retrieve relevant conversation context for response generation.

### Options Considered

1. **ChromaDB (Self-Hosted)**
   - Pros: 100% free, Python-native, simple setup, local data control
   - Cons: Manual scaling, requires disk space

2. **Pinecone (Cloud, Free Tier)**
   - Pros: Managed service, fast, 100K vectors free
   - Cons: Free tier limits, cloud dependency, potential future costs

3. **Qdrant (Self-Hosted)**
   - Pros: High performance, good documentation
   - Cons: More complex setup than ChromaDB

### Decision

**Use ChromaDB for vector database storage.**

### Rationale

1. **Zero Cost:** Self-hosted, no API costs, perfect alignment with free-tier infrastructure goal
2. **MVP Scale:** Handles 10K-50K emails easily (sufficient for target user base)
3. **Data Privacy:** Embeddings stay local, no cloud transmission (better security)
4. **Python-Native:** Simple integration (< 50 lines of code)
5. **Consistency:** Matches Epic 2 pattern (PostgreSQL self-hosted over managed cloud)

### Implementation Details

- Storage: Persistent SQLite backend
- Collection: `email_embeddings` with metadata (message_id, thread_id, sender, date, subject, language)
- Query: Cosine similarity distance metric
- Performance: <500ms for k=10 nearest neighbors

### Consequences

**Positive:**
- Zero ongoing costs
- Full data control and privacy
- Simple Python integration
- No vendor lock-in

**Negative:**
- Manual scaling if >100K emails per user
- Requires disk space monitoring

**Mitigation:**
- Monitor disk usage per user
- Plan for distributed ChromaDB if scaling beyond MVP (100+ users)

---

## ADR-010: Gemini Embeddings for Multilingual Email Representation

**Status:** ✅ Accepted
**Date:** 2025-11-09

### Context

Epic 3 requires embedding model to convert email content into vector representations for semantic search. Critical requirement: excellent multilingual support for Russian, Ukrainian, English, and German.

### Options Considered

1. **Gemini text-embedding-004**
   - Pros: Free unlimited, native multilingual, same provider as LLM
   - Cons: API dependency

2. **OpenAI text-embedding-3-small**
   - Pros: High quality, fast API
   - Cons: PAID ($0.02 per 1M tokens), breaks zero-cost goal

3. **sentence-transformers (paraphrase-multilingual-mpnet-base-v2)**
   - Pros: 100% free, self-hosted, no API calls
   - Cons: Model download (420MB), CPU inference slower

### Decision

**Use Google Gemini text-embedding-004 for email embeddings.**

### Rationale

1. **Zero Cost:** Free unlimited tier (as of 2025)
2. **Multilingual Excellence:** State-of-the-art Google model trained on 50+ languages including ru/uk/en/de
3. **Provider Consistency:** Same API as classification LLM (Gemini 2.5 Flash from Epic 2)
4. **Quality:** 768 dimensions, excellent for semantic search
5. **Simplicity:** Reuse existing LLMClient pattern from Epic 2

### Implementation Details

- Model: `text-embedding-004`
- Dimensions: 768 (optimal for ChromaDB)
- Batch size: 50 emails per minute (rate limit headroom)
- Token limit: Email content truncated to 2048 tokens max

### Consequences

**Positive:**
- Zero cost for unlimited embeddings
- Excellent multilingual quality
- Consistent API provider (single key management)
- Proven quality (Google state-of-the-art)

**Negative:**
- API dependency (rate limits possible)
- Network latency for embedding calls

**Mitigation:**
- Fallback to sentence-transformers for batch indexing if rate limits encountered
- Implement batch processing with 50/min limit for safety

---

## ADR-011: Smart Hybrid RAG Strategy (Thread + Semantic)

**Status:** ✅ Accepted
**Date:** 2025-11-09

### Context

Epic 3 requires context retrieval strategy for response generation. Need to balance conversation continuity (thread history) with broader context (semantic search) while staying within LLM token limits.

### Options Considered

1. **Thread-First Hybrid**
   - All thread emails + top 5 semantic
   - Pros: Comprehensive
   - Cons: High token usage, slow for long threads

2. **Semantic-Only**
   - Top 10 similar emails
   - Pros: Simple, fast, fixed tokens
   - Cons: Misses thread context, lower accuracy

3. **Smart Hybrid (Adaptive)**
   - Last 5 thread + top 3 semantic (adaptive based on thread length)
   - Pros: Balanced accuracy vs efficiency
   - Cons: More complex logic

### Decision

**Use Smart Hybrid RAG combining thread history (last 5 emails) with semantic search (top 3 similar emails), with adaptive logic based on thread length.**

### Rationale

1. **Conversation Continuity:** Thread history critical for government emails (German bureaucracy threads)
2. **Token Efficiency:** Cap thread at 5 emails (~3K tokens) prevents explosion
3. **Broader Context:** 3 semantic results add related conversations (~2K tokens)
4. **Adaptive Intelligence:** Short threads get more semantic (k=7), long threads skip semantic
5. **Token Budget:** ~6.5K tokens context leaves 25K+ for response generation (Gemini 32K window)

### Implementation Details

```python
# Adaptive logic
if thread_length < 3:
    k_semantic = 7  # More semantic for short threads
elif thread_length > 5:
    k_semantic = 0  # Skip semantic for long threads
else:
    k_semantic = 3  # Standard hybrid
```

**Token Budget:**
- System prompt: ~1K tokens
- Current email: ~500 tokens
- Thread history (5): ~3K tokens
- Semantic search (3): ~2K tokens
- Response generation: ~25K tokens
- **Total context used: ~6.5K tokens ✅**

### Consequences

**Positive:**
- Optimal accuracy for government email threads (critical use case)
- Efficient token usage (no waste)
- Handles various email types well
- Proven pattern (similar to industry best practices)

**Negative:**
- More complex retrieval logic than single-source
- Needs comprehensive testing for edge cases

**Mitigation:**
- Story 3.10: Multilingual quality testing with real email threads
- Story 3.11-3.13: Integration and performance testing

---

## ADR-012: 90-Day Email History Indexing Strategy

**Status:** ✅ Accepted
**Date:** 2025-11-09

### Context

Epic 3 requires initial email history indexing for semantic search. Need to balance comprehensive context availability with fast onboarding time and API usage.

### Options Considered

1. **Full Mailbox**
   - Index ALL emails (5K-50K)
   - Pros: Complete context
   - Cons: Hours of indexing, high API usage

2. **Recent 30 Days**
   - ~100-200 emails
   - Pros: Very fast (3-5 min)
   - Cons: May miss important context

3. **Recent 90 Days**
   - ~200-500 emails
   - Pros: Fast (5-10 min), covers most use cases
   - Cons: Old emails (>90 days) not available

4. **Incremental Expansion**
   - Start 30 days, expand to 90, then full
   - Pros: Progressive value delivery
   - Cons: Complex implementation

### Decision

**Index last 90 days of email history during initial setup (~200-500 emails typically).**

### Rationale

1. **Fast Onboarding:** 5-10 min indexing (meets NFR005: <10 min onboarding)
2. **Practical Coverage:** Most email responses reference last 1-3 months
3. **Government Communication:** German bureaucracy (Finanzamt, Ausländerbehörde) can take weeks to respond - 90 days covers these delays ✅ (User insight from Dimcheg)
4. **API Friendly:** 200-500 emails = ~20-50K API calls at 50/min = 10 min total
5. **User Experience:** Clear progress ("Indexing 437 emails... 80%") vs overwhelming count

### Implementation Details

- Batch size: 50 emails per minute
- Progress tracking: IndexingProgress table (user_id, total, processed, status)
- Notification: Telegram message when complete ("✅ 437 emails indexed")
- Resumption: Checkpoint mechanism for interrupted jobs

**Indexing Math:**
```
500 emails / 50 per minute = 10 minutes total ✅
Progress updates every 50 emails
```

### Consequences

**Positive:**
- Fast user onboarding (value in <10 minutes)
- Manageable API usage (no rate limit issues)
- Covers practical use cases (including government delays)
- Clear user progress visibility

**Negative:**
- Very old emails (>90 days) not available initially

**Mitigation:**
- Epic 4: Add "Index Full History" button in settings UI for power users
- Background job can expand to full mailbox after initial setup

---

## ADR-013: langdetect for Language Detection

**Status:** ✅ Accepted
**Date:** 2025-11-09

### Context

Epic 3 requires automatic language detection to generate email responses in the correct language (Russian, Ukrainian, English, German).

### Options Considered

1. **langdetect (Python library)**
   - Pros: Lightweight (5MB), fast (50-100ms), 55 languages
   - Cons: Lower accuracy for short texts

2. **fasttext (Facebook)**
   - Pros: Higher accuracy, very fast (10-50ms)
   - Cons: Larger model (130MB)

3. **Gemini LLM analysis**
   - Pros: No extra library, better context understanding
   - Cons: Slower (500ms), uses API quota

### Decision

**Use langdetect library for language detection.**

### Rationale

1. **Simplicity:** Single line install (`pip install langdetect`)
2. **Performance:** 50-100ms meets <100ms requirement
3. **Good Accuracy:** High accuracy for email bodies (typically >100 characters)
4. **Zero Cost:** No API calls, no quota usage
5. **Proven:** Widely used in production email systems

### Implementation Details

```python
def detect_language(email_body):
    try:
        detections = langdetect.detect_langs(email_body)
        primary = detections[0]

        if primary.prob < 0.7:
            # Low confidence - fallback to thread history
            return detect_from_thread_history()

        return primary.lang, primary.prob
    except:
        return "en", 0.5  # Default fallback
```

### Consequences

**Positive:**
- Fast detection (<100ms)
- Simple integration
- Zero cost (no API usage)
- Good accuracy for email-length texts

**Negative:**
- Lower accuracy for very short texts (<50 characters)

**Mitigation:**
- Confidence threshold (0.7) with fallback to thread history language
- Default to English if all detection fails

---

## ADR-014: Hybrid Tone Detection (Rules + LLM)

**Status:** ✅ Accepted
**Date:** 2025-11-09

### Context

Epic 3 requires tone detection to generate appropriately formal responses (formal for government, professional for business, casual for personal).

### Options Considered

1. **Rule-Based Only**
   - Government domains → formal
   - Known clients → professional
   - Pros: Fast, predictable
   - Cons: Misses nuances

2. **LLM-Based Only**
   - Analyze thread history with Gemini
   - Pros: More accurate
   - Cons: Extra API call for every email

3. **Hybrid (Rules + LLM Fallback)**
   - Use rules for known cases
   - Use LLM for ambiguous cases
   - Pros: Best of both worlds

### Decision

**Use hybrid approach: rule-based for known cases (government = formal), LLM analysis for ambiguous emails.**

### Rationale

1. **Efficiency:** Rules handle 80% of cases with zero API cost
2. **Accuracy:** Rules correct for clear cases (government always formal)
3. **Flexibility:** LLM handles edge cases intelligently
4. **Cost Optimization:** Minimize API calls while maintaining quality

### Implementation Details

**Rule Examples:**
- finanzamt.de, auslaenderbehoerde.de → "formal"
- Known business contacts → "professional"
- Personal contacts → "casual"

**LLM Fallback Prompt:**
```python
"Analyze the tone of this email thread.
What tone should be used to respond?
Answer with one word: formal, professional, or casual."
```

**Tone Mappings (German example):**
- Formal: "Sehr geehrte Damen und Herren," / "Mit freundlichen Grüßen"
- Professional: "Guten Tag Herr/Frau X," / "Beste Grüße"
- Casual: "Hallo X," / "Viele Grüße"

### Consequences

**Positive:**
- Optimal balance of speed, accuracy, and cost
- Handles clear cases instantly (rules)
- Intelligent handling of ambiguous cases (LLM)

**Negative:**
- More complex implementation than single approach
- Need to maintain rule database

**Mitigation:**
- Comprehensive greeting/closing examples in prompt template (Story 3.6)
- Story 3.10: Test tone appropriateness across scenarios

---

## ADR-015: Sequential Context Retrieval Execution

**Status:** ✅ Accepted
**Date:** 2025-11-09
**Context:** Story 3.4 Implementation

### Context

Story 3.4 implements context retrieval service with AC #12 stating "Performance optimization: Parallel retrieval of thread history and semantic search using asyncio." However, AC #5 requires adaptive k logic that depends on thread length.

### Problem

True parallel execution using `asyncio.gather()` conflicts with adaptive k requirement:
- Adaptive k (AC #5) requires: Calculate k BASED ON thread_length from Gmail thread history
- Parallel execution would require: Fixed k value BEFORE fetching thread history
- **These requirements are mutually exclusive**

### Options Considered

1. **Parallel Execution with Fixed k**
   - Use `asyncio.gather()` with fixed k=3 for all cases
   - Pros: True parallelization, faster execution
   - Cons: VIOLATES AC #5 adaptive k requirement, suboptimal context quality

2. **Sequential Execution (Current)**
   - Fetch thread history → Calculate adaptive k → Fetch semantic results
   - Pros: Correctly implements AC #5, optimal context quality
   - Cons: No parallelization, slightly slower (~0.5s difference)

3. **Speculative Parallel with Discard**
   - Fetch both in parallel with default k, discard/adjust after thread analysis
   - Pros: Parallel execution
   - Cons: Wasted API calls, complex logic, still violates AC #5 intent

### Decision

**Use sequential execution: thread history → adaptive k calculation → semantic search.**

### Rationale

1. **Correctness Over Optimization:** AC #5 adaptive k is a functional requirement; AC #12 parallelization is an optimization
2. **Performance Still Met:** Tests show <3s target achieved even with sequential execution
3. **Design Integrity:** Adaptive k logic is CORE to Smart Hybrid RAG strategy (ADR-011)
4. **Token Efficiency:** Correct k value prevents fetching unnecessary semantic results (k=0 for long threads)

### Implementation Details

```python
# backend/app/services/context_retrieval.py:673-682

# Step 2: Fetch thread history from Gmail
# NOTE: Must complete before Step 3 to enable adaptive k calculation (AC #5)
thread_history, original_thread_length = await self._get_thread_history(gmail_thread_id)

# Step 3: Calculate adaptive k based on thread length (AC #5)
# DESIGN DECISION: Sequential execution required here to satisfy AC #5
# Adaptive k logic DEPENDS on thread_length from Step 2, preventing parallelization
k = self._calculate_adaptive_k(original_thread_length)

# Step 4: Perform semantic search if k > 0
if k > 0:
    semantic_results = await self._get_semantic_results(email_body, k, user_id)
```

### Performance Analysis

**Sequential Execution Timing:**
- Gmail thread fetch: ~1000ms
- Adaptive k calculation: <1ms
- Semantic search (if k>0): ~500ms
- Context assembly: ~100ms
- **Total: ~1600ms (well under 3s target) ✅**

**Parallel Execution (hypothetical):**
- Parallel fetch: ~1000ms (max of thread + semantic)
- Context assembly: ~100ms
- **Total: ~1100ms (only ~500ms faster)**

**Trade-off:** 500ms performance gain NOT worth violating functional requirement AC #5.

### Consequences

**Positive:**
- ✅ AC #5 adaptive k correctly implemented
- ✅ AC #11 performance target <3s met
- ✅ Token efficiency optimized (correct k value)
- ✅ Code clarity and maintainability

**Negative:**
- ❌ AC #12 literal interpretation not satisfied (no asyncio.gather())
- ⚠️ Sequential execution ~500ms slower than parallel

**Mitigation:**
- Document design decision in code comments (context_retrieval.py:678-681)
- Update AC #12 interpretation: "Optimization" refers to avoiding synchronous blocking, not requiring literal parallelization
- Future optimization possible if Gmail API adds thread metadata endpoint (thread_length without full fetch)

### Acceptance Criteria Alignment

- **AC #5 (Adaptive k):** ✅ FULLY SATISFIED (requires sequential execution)
- **AC #11 (Performance <3s):** ✅ FULLY SATISFIED (measured at ~1.6s)
- **AC #12 (Parallel optimization):** ⚠️ INTERPRETED as async/await usage (satisfied), not literal asyncio.gather() (data dependency prevents)

**Conclusion:** Sequential execution is the CORRECT implementation given AC requirements. Performance target met without compromising functional correctness.

---

## Decision Summary Table

| ADR | Decision | Rationale | Status |
|-----|----------|-----------|--------|
| ADR-009 | ChromaDB for Vector DB | Zero cost, self-hosted, data privacy | ✅ Accepted |
| ADR-010 | Gemini Embeddings | Free unlimited, multilingual excellence | ✅ Accepted |
| ADR-011 | Smart Hybrid RAG | Balanced accuracy + efficiency | ✅ Accepted |
| ADR-012 | 90-Day Indexing | Fast onboarding, covers gov delays | ✅ Accepted |
| ADR-013 | langdetect Library | Fast, simple, zero cost | ✅ Accepted |
| ADR-014 | Hybrid Tone Detection | Optimal speed + accuracy balance | ✅ Accepted |
| ADR-015 | Sequential Context Retrieval | Correctness over optimization, AC #5 requires thread_length | ✅ Accepted |

---

## Architecture Alignment

All decisions align with project goals and NFRs:

**Zero-Cost Infrastructure (Project Goal):**
- ✅ ChromaDB: Self-hosted (zero cost)
- ✅ Gemini Embeddings: Free unlimited tier
- ✅ langdetect: Open-source library (zero cost)
- ✅ Hybrid Tone: Minimizes API usage

**Multilingual Quality (FR018, Goal #3):**
- ✅ Gemini: Native ru/uk/en/de support
- ✅ langdetect: 55 language coverage
- ✅ Prompt templates: Language-specific greetings/closings

**Performance (NFR001):**
- ✅ RAG retrieval: <3s (ChromaDB <500ms + Gmail ~1s)
- ✅ Language detection: <100ms (langdetect)
- ✅ Smart Hybrid: Token-efficient (~6.5K context)

**Usability (NFR005):**
- ✅ 90-day indexing: 5-10 min (supports <10 min onboarding)
- ✅ Progress tracking: Clear user visibility

**Reliability (NFR002):**
- ✅ Indexing resumption: Checkpoint mechanism
- ✅ Language fallback: Thread history backup
- ✅ Tone fallback: LLM for ambiguous cases

---

## Next Steps

**Immediate (Completed):**
1. ✅ All architectural decisions finalized
2. ✅ tech-spec-epic-3.md created (comprehensive)
3. ✅ ADR documentation complete

**Next (Before Epic 3 Story 1):**
1. ⏳ Update story template with Epic 2 retrospective improvements (DoD checklist, task reordering)
2. ⏳ Create LangGraph testing patterns documentation (`docs/testing-patterns-langgraph.md`)
3. ⏳ Begin Epic 3 story creation with new templates

**Epic 3 Kickoff:**
1. Run epic-tech-context workflow for Epic 3
2. Create Story 3.1 (Vector Database Setup) with enhanced template
3. Apply all Epic 2 lessons learned

---

**Document Version:** 1.0
**Last Updated:** 2025-11-09
**Status:** Decisions Finalized - Ready for Epic 3 Implementation
