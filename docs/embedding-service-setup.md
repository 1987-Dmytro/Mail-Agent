# Email Embedding Service Setup Guide

**Epic 3 - Story 3.2: Email Embedding Service**

This guide covers the setup, configuration, and usage of the Gemini Embedding Service for the Mail Agent RAG (Retrieval-Augmented Generation) system.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Setup & Configuration](#setup--configuration)
- [Usage Examples](#usage-examples)
- [Email Preprocessing Pipeline](#email-preprocessing-pipeline)
- [Batch Processing](#batch-processing)
- [Error Handling & Retries](#error-handling--retries)
- [Monitoring & Logging](#monitoring--logging)
- [Performance](#performance)
- [Security Considerations](#security-considerations)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Email Embedding Service converts email content into 768-dimensional vector embeddings using Google's Gemini `text-embedding-004` model. These embeddings enable semantic search and RAG-based response generation by representing email content in a high-dimensional vector space where semantically similar emails are close together.

### Key Features

- **Gemini text-embedding-004 Model**: 768 dimensions, unlimited free tier
- **Multilingual Support**: Native support for 50+ languages including ru/uk/en/de
- **Email Preprocessing**: Automatic HTML stripping and token truncation (2048 max)
- **Batch Processing**: Efficient batch embedding generation (up to 50 emails per batch)
- **Error Handling**: Automatic retry with exponential backoff for transient errors
- **Usage Tracking**: Built-in metrics for free-tier monitoring

### Model Characteristics

| Characteristic | Value |
|----------------|-------|
| Model | `text-embedding-004` |
| Dimensions | 768 |
| Max Input Tokens | 2048 |
| Free Tier Limit | Unlimited requests |
| Rate Recommendation | 50 requests/minute (safe margin) |
| Multilingual | Yes (50+ languages) |
| Cost | Free |

---

## Architecture

The embedding service integrates with the Mail Agent RAG system as follows:

```
Email Content → Preprocessing → EmbeddingService → ChromaDB
                                      ↓
                                 Gemini API
                              (text-embedding-004)
```

### Component Responsibilities

**EmbeddingService** (`backend/app/core/embedding_service.py`)
- Gemini API client wrapper
- Embedding generation (single and batch)
- Dimension validation (768-dim)
- Usage tracking and metrics

**Preprocessing** (`backend/app/core/preprocessing.py`)
- HTML tag stripping
- Text extraction from emails
- Token-based truncation (2048 limit)

**VectorDBClient** (`backend/app/core/vector_db.py`)
- ChromaDB storage for embeddings
- Semantic search and retrieval
- Collection management

---

## Setup & Configuration

### 1. Install Dependencies

The embedding service requires `google-generativeai` and `beautifulsoup4`:

```bash
cd backend
uv pip install "google-generativeai>=0.8.3" "beautifulsoup4>=4.12.0"
```

### 2. Configure Gemini API Key

Get your free API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

**Add to `.env` file:**

```bash
# Gemini API Configuration
GEMINI_API_KEY="your-gemini-api-key-here"
GEMINI_MODEL="gemini-2.5-flash"  # For LLM operations
```

**Verify configuration:**

```python
from app.core.config import settings

print(settings.GEMINI_API_KEY)  # Should print your API key
```

### 3. Initialize Embedding Service

```python
from app.core.embedding_service import EmbeddingService

# Initialize service (uses GEMINI_API_KEY from environment)
embedding_service = EmbeddingService()

# Or provide API key explicitly
embedding_service = EmbeddingService(api_key="your-key-here")
```

---

## Usage Examples

### Single Email Embedding

```python
from app.core.embedding_service import EmbeddingService

# Initialize service
service = EmbeddingService()

# Email content (HTML will be stripped automatically)
email_text = """
<html>
<body>
<p>Dear Customer,</p>
<p>Your order #12345 has been shipped.</p>
</body>
</html>
"""

# Generate embedding
embedding = service.embed_text(email_text)

print(f"Embedding dimensions: {len(embedding)}")  # Output: 768
print(f"First 5 values: {embedding[:5]}")
```

### Batch Email Embedding

```python
from app.core.embedding_service import EmbeddingService

service = EmbeddingService()

# List of emails
emails = [
    "Email 1: Meeting reminder for 10 AM tomorrow.",
    "Email 2: Your invoice is ready for download.",
    "Email 3: Password reset request confirmation.",
    # ... up to 50 emails per batch
]

# Generate batch embeddings
embeddings = service.embed_batch(emails, batch_size=50)

print(f"Generated {len(embeddings)} embeddings")
for i, embedding in enumerate(embeddings):
    print(f"Email {i+1}: {len(embedding)} dimensions")
```

### Integration with ChromaDB

```python
from app.core.embedding_service import EmbeddingService
from app.core.vector_db import VectorDBClient

# Initialize services
embedding_service = EmbeddingService()
vector_db_client = VectorDBClient()

# Email content
email_text = "Project deadline reminder: Submit deliverables by Friday."

# Generate embedding
embedding = embedding_service.embed_text(email_text)

# Prepare metadata
metadata = {
    "message_id": "msg_abc123",
    "thread_id": "thread_xyz",
    "sender": "project-manager@company.com",
    "date": "2025-11-09",
    "subject": "Project Deadline Reminder",
    "language": "en",
    "snippet": email_text[:200],
}

# Store in ChromaDB
vector_db_client.insert_embeddings_batch(
    collection_name="email_embeddings",
    embeddings=[embedding],
    metadatas=[metadata],
    ids=["msg_abc123"],
)

# Query similar emails
results = vector_db_client.query_embeddings(
    collection_name="email_embeddings",
    query_embedding=embedding,
    n_results=5,
)

print(f"Found {len(results['ids'][0])} similar emails")
```

---

## Email Preprocessing Pipeline

The embedding service automatically preprocesses email content before generating embeddings:

### 1. HTML Stripping

```python
from app.core.preprocessing import strip_html

html_email = "<p>Hello <b>World</b>!</p>"
plain_text = strip_html(html_email)

print(plain_text)  # Output: "Hello World!"
```

**Features:**
- Removes all HTML tags
- Removes `<script>` and `<style>` blocks
- Preserves text content
- Normalizes whitespace
- Handles malformed HTML gracefully

### 2. Text Extraction

```python
from app.core.preprocessing import extract_email_text

# HTML email
html_body = "<html><body><p>Email content</p></body></html>"
text = extract_email_text(html_body, content_type="text/html")

# Plain text email
plain_body = "Email content"
text = extract_email_text(plain_body, content_type="text/plain")
```

### 3. Token Truncation

```python
from app.core.preprocessing import truncate_to_tokens

long_email = " ".join(["word"] * 3000)  # 3000 words
truncated = truncate_to_tokens(long_email, max_tokens=2048)

print(len(truncated.split()))  # Output: 2048
```

**Why 2048 tokens?**
- Gemini `text-embedding-004` performs best with inputs ≤2048 tokens
- Prevents API errors from oversized inputs
- Optimizes API usage for free tier

---

## Batch Processing

Batch processing improves efficiency when embedding multiple emails:

### Batch Size Recommendations

| Scenario | Batch Size | Rationale |
|----------|-----------|-----------|
| Real-time processing | 1-10 | Low latency, immediate results |
| Background indexing | 50 | Optimal throughput, rate limit safe |
| Bulk import | 50 | Maximum safe batch size |

### Rate Limiting Strategy

The embedding service implements rate limiting awareness:

```python
service = EmbeddingService()

# Process 100 emails in batches of 50
emails = [f"Email {i}" for i in range(100)]

batch_1 = emails[:50]
batch_2 = emails[50:]

embeddings_1 = service.embed_batch(batch_1, batch_size=50)
time.sleep(1)  # Brief pause between large batches
embeddings_2 = service.embed_batch(batch_2, batch_size=50)
```

**Rate Limit Guidelines:**
- Recommended: 50 requests/minute
- Free tier: Unlimited (but rate limiting recommended)
- Automatic retry with exponential backoff for 429 errors

---

## Error Handling & Retries

The embedding service automatically handles transient API errors:

### Automatic Retry Logic

```python
from app.core.embedding_service import EmbeddingService
from app.utils.errors import GeminiRateLimitError

service = EmbeddingService()

try:
    # Automatic retry (3 attempts) for rate limits and timeouts
    embedding = service.embed_text("Email content")
except GeminiRateLimitError as e:
    print(f"Rate limit exceeded after 3 retries: {e}")
```

### Retry Strategy

- **Retried Errors**: Rate limits (429), Timeouts
- **Not Retried**: Invalid requests (400), Blocked prompts (403)
- **Max Attempts**: 3
- **Backoff**: Exponential (2s, 4s, 8s)

### Error Types

```python
from app.utils.errors import (
    GeminiRateLimitError,      # 429: Rate limit exceeded
    GeminiTimeoutError,         # Timeout: Request took too long
    GeminiInvalidRequestError,  # 400/403: Invalid/blocked request
    GeminiAPIError,             # Other API errors
)

try:
    embedding = service.embed_text("Content")
except GeminiRateLimitError:
    # Wait and retry manually
    time.sleep(10)
    embedding = service.embed_text("Content")
except GeminiInvalidRequestError as e:
    # Do not retry - permanent error
    print(f"Invalid request: {e}")
```

---

## Monitoring & Logging

### Usage Statistics

Track API usage for free-tier monitoring:

```python
from app.core.embedding_service import EmbeddingService

service = EmbeddingService()

# Generate some embeddings
service.embed_text("Email 1")
service.embed_batch(["Email 2", "Email 3"])

# Get usage stats
stats = service.get_usage_stats()

print(f"Total requests: {stats['total_requests']}")
print(f"Total embeddings: {stats['total_embeddings_generated']}")
print(f"Avg latency: {stats['avg_latency_ms']}ms")
```

### Monitoring Endpoint

The test API provides a monitoring endpoint:

```bash
curl http://localhost:8000/api/v1/test/embedding-stats
```

**Response:**
```json
{
  "total_requests": 42,
  "total_embeddings_generated": 128,
  "avg_latency_ms": 234.56,
  "service_initialized": true
}
```

### Structured Logging

All embedding operations are logged with structured data:

```python
# Logs include:
# - embedding_started: text_length, model
# - embedding_completed: dimensions, latency_ms
# - embedding_error: error_type, retry_attempt
# - batch_embedding_completed: batch_size, avg_latency_per_embedding_ms
```

---

## Performance

### Benchmarks

| Metric | Value |
|--------|-------|
| Single embedding latency | ~200-500ms |
| Batch (50 emails) | <60 seconds |
| Throughput | ~50 emails/minute |
| Memory usage | <100MB for service |

### Performance Optimization

1. **Use Batch Processing**
   ```python
   # Inefficient
   for email in emails:
       embedding = service.embed_text(email)

   # Efficient
   embeddings = service.embed_batch(emails, batch_size=50)
   ```

2. **Preprocess Once**
   ```python
   from app.core.preprocessing import strip_html, truncate_to_tokens

   # Preprocess manually for reuse
   clean_text = strip_html(html_email)
   truncated = truncate_to_tokens(clean_text, max_tokens=2048)
   embedding = service.embed_text(truncated)
   ```

3. **Cache Embeddings**
   ```python
   # Store embeddings in ChromaDB to avoid regeneration
   vector_db_client.insert_embeddings_batch(
       collection_name="email_embeddings",
       embeddings=embeddings,
       metadatas=metadatas,
       ids=message_ids,
   )
   ```

---

## Security Considerations

### API Key Protection

✅ **DO:**
- Store API key in `.env` file (never commit)
- Use environment variables (`GEMINI_API_KEY`)
- Rotate API keys regularly
- Restrict API key permissions if available

❌ **DON'T:**
- Hardcode API keys in source code
- Commit `.env` to version control
- Share API keys in logs or error messages
- Expose API keys in client-side code

### Input Validation

The service validates all inputs:

```python
# Empty input rejected
try:
    service.embed_text("")
except ValueError as e:
    print(f"Validation error: {e}")

# Invalid batch size rejected
try:
    service.embed_batch(emails, batch_size=0)
except ValueError as e:
    print(f"Validation error: {e}")
```

### PII Handling

**Email Content Preprocessing:**
- HTML stripped before API submission
- Content truncated to 2048 tokens
- No email content logged by default (only lengths/dimensions)

---

## Testing

### Run Unit Tests

```bash
cd backend
uv run pytest tests/test_preprocessing.py tests/test_embedding_service.py -v
```

**Coverage:**
- 11 preprocessing tests (HTML stripping, truncation, validation)
- 16 embedding service tests (initialization, embedding generation, error handling)

### Run Integration Tests

```bash
DATABASE_URL="postgresql+psycopg://..." uv run pytest tests/integration/test_embedding_integration.py -v
```

**Coverage:**
- ChromaDB integration (embed and store)
- Multilingual batch processing (ru/uk/en/de)
- Performance test (50 emails < 60s)

### Test with Real API

```bash
# Set environment variable for e2e testing
export USE_REAL_GEMINI_API=true
export GEMINI_API_KEY="your-real-key"

uv run pytest tests/integration/test_embedding_integration.py -v
```

---

## Troubleshooting

### Issue: `GEMINI_API_KEY environment variable not set`

**Solution:**
1. Verify `.env` file exists in `backend/` directory
2. Add `GEMINI_API_KEY="your-key-here"` to `.env`
3. Restart application to load new environment variables

### Issue: `Invalid embedding dimensions: expected 768, got X`

**Solution:**
- Verify using `text-embedding-004` model (not a different model)
- Check `EmbeddingService` initialization: `model="text-embedding-004"`
- Contact support if persistent

### Issue: Rate limit errors (429)

**Solution:**
1. Reduce batch size: `batch_size=25` instead of 50
2. Add delays between batches: `time.sleep(2)`
3. Implement exponential backoff (already automatic for 3 retries)

### Issue: Timeouts for long emails

**Solution:**
- Email content automatically truncated to 2048 tokens
- If persistent, manually truncate before embedding:
  ```python
  from app.core.preprocessing import truncate_to_tokens
  truncated = truncate_to_tokens(email_text, max_tokens=1024)
  ```

---

## References

- **Gemini Embeddings API**: https://ai.google.dev/gemini-api/docs/embeddings
- **Story 3.1 (ChromaDB Setup)**: `docs/vector-database-setup.md`
- **Epic 3 Technical Spec**: `docs/tech-spec-epic-3.md`
- **ADR-010 (Embedding Model Selection)**: `docs/adrs/epic-3-architecture-decisions.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-09
**Author**: Epic 3, Story 3.2 - Email Embedding Service
