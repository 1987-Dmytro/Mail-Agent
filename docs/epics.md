# Mail Agent - Epic Breakdown

**Author:** Dimcheg
**Date:** 2025-11-03
**Project Level:** 3
**Target Scale:** 10,000 users

---

## Overview

This document provides the detailed epic breakdown for Mail Agent, expanding on the high-level epic list in the [PRD](./PRD.md).

Each epic includes:

- Expanded goal and value proposition
- Complete story breakdown with user stories
- Acceptance criteria for each story
- Story sequencing and dependencies

**Epic Sequencing Principles:**

- Epic 1 establishes foundational infrastructure and initial functionality
- Subsequent epics build progressively, each delivering significant end-to-end value
- Stories within epics are vertically sliced and sequentially ordered
- No forward dependencies - each story builds only on previous work

---

## Epic 1: Foundation & Gmail Integration

**Expanded Goal:**

Establish the technical foundation for Mail Agent by setting up development infrastructure, implementing Gmail API connectivity, and creating basic email monitoring capabilities. This epic delivers a working system that can authenticate users, read emails from Gmail, and provide foundational infrastructure for subsequent AI and Telegram features.

**Value Delivery:**

By the end of this epic, the system can authenticate users via Gmail OAuth and monitor incoming emails, proving the core Gmail integration works. This validates the technical feasibility of the entire project and establishes the foundation for all subsequent features.

**Estimated Stories:** 10 stories

---

### Story 1.1: Project Infrastructure Setup

As a developer,
I want to initialize the project repository with proper structure and development tools,
So that I have a clean, organized foundation for building the application.

**Acceptance Criteria:**
1. Git repository initialized with .gitignore for Python/Node.js projects
2. Project structure created with separate folders for backend (Python), frontend (Next.js), and shared configs
3. README.md created with project overview and setup instructions
4. Development environment documentation includes required tools (Python 3.11+, Node.js, etc.)
5. Virtual environment setup instructions documented (venv or poetry)
6. Environment variables template file (.env.example) created for API keys and configs

**Prerequisites:** None (first story)

---

### Story 1.2: Backend Service Foundation

As a developer,
I want to set up the FastAPI backend service with basic structure,
So that I have a running API server ready for Gmail integration.

**Acceptance Criteria:**
1. FastAPI application initialized with main.py entry point
2. Basic API health check endpoint created (GET /health) returning status
3. CORS middleware configured for local frontend development
4. Environment variable loading implemented using python-dotenv
5. Development server runs successfully on localhost:8000
6. Basic logging configured (structured JSON format)
7. Requirements.txt or pyproject.toml created with initial dependencies (fastapi, uvicorn, python-dotenv)

**Prerequisites:** Story 1.1 (project infrastructure)

---

### Story 1.3: Database Setup for User Data

As a developer,
I want to set up PostgreSQL database with initial schema for user management,
So that I can store user authentication tokens and settings.

**Acceptance Criteria:**
1. PostgreSQL database created (local development or free-tier cloud service like Supabase)
2. Database connection string configured in environment variables
3. SQLAlchemy ORM integrated into backend service
4. Initial database schema created with Users table (id, email, gmail_oauth_token, telegram_id, created_at, updated_at)
5. Database migrations framework set up (Alembic)
6. Initial migration successfully applied to database
7. Database connection test endpoint created (GET /db/health)

**Prerequisites:** Story 1.2 (backend service foundation)

---

### Story 1.4: Gmail OAuth Flow - Backend Implementation

As a developer,
I want to implement Gmail OAuth 2.0 authentication flow in the backend,
So that users can grant permission for the application to access their Gmail.

**Acceptance Criteria:**
1. Google Cloud Project created with Gmail API enabled
2. OAuth 2.0 credentials (client ID and secret) obtained and stored in environment variables
3. OAuth scopes configured for Gmail read/write access (gmail.readonly, gmail.modify, gmail.send, gmail.labels)
4. Backend endpoint created for initiating OAuth flow (GET /auth/gmail/login) returning authorization URL
5. Backend callback endpoint created (GET /auth/gmail/callback) to handle OAuth redirect
6. OAuth token exchange implemented (authorization code → access token + refresh token)
7. Access and refresh tokens encrypted and stored in database for authenticated user
8. Token refresh logic implemented for expired access tokens

**Prerequisites:** Story 1.3 (database setup)

---

### Story 1.5: Gmail API Client Integration

As a developer,
I want to create a Gmail API client wrapper that uses stored OAuth tokens,
So that I can read emails and perform Gmail operations programmatically.

**Acceptance Criteria:**
1. Gmail API Python client library integrated (google-api-python-client)
2. Gmail client class created that loads user's OAuth tokens from database
3. Method implemented to list emails from inbox (get_messages)
4. Method implemented to read full email content including body and metadata (get_message_detail)
5. Method implemented to read email thread history (get_thread)
6. Error handling implemented for expired tokens (triggers automatic refresh)
7. Unit tests created for Gmail client methods using mock responses
8. Rate limiting considerations documented (Gmail API quotas)

**Prerequisites:** Story 1.4 (Gmail OAuth backend)

---

### Story 1.6: Basic Email Monitoring Service

As a system,
I want to periodically poll Gmail inbox for new emails,
So that I can detect incoming emails that need processing.

**Acceptance Criteria:**
1. Background task scheduler implemented (asyncio or Celery with Redis)
2. Email polling task created that runs at configurable intervals (default: every 2 minutes)
3. Polling task retrieves unread emails from Gmail inbox using Gmail client
4. Email metadata extracted (message_id, thread_id, sender, subject, date, labels)
5. Processed emails marked internally to avoid duplicate processing
6. Polling task handles multiple users (iterates through all active users)
7. Logging implemented for each polling cycle (emails found, processing status)
8. Configuration added for polling interval via environment variable

**Prerequisites:** Story 1.5 (Gmail API client)

---

### Story 1.7: Email Data Model and Storage

As a developer,
I want to store email metadata in the database for tracking and processing,
So that I can maintain state of which emails have been processed.

**Acceptance Criteria:**
1. EmailProcessingQueue table created in database schema (id, user_id, gmail_message_id, gmail_thread_id, sender, subject, received_at, status, created_at)
2. Status field supports states: pending, processing, approved, rejected, completed
3. Database migration created and applied for EmailProcessingQueue table
4. SQLAlchemy model created for EmailProcessingQueue with relationships to Users
5. Email polling task saves newly detected emails to EmailProcessingQueue with status=pending
6. Duplicate detection implemented (skip emails already in queue based on gmail_message_id)
7. Query methods created to fetch emails by status and user

**Prerequisites:** Story 1.6 (email monitoring service)

---

### Story 1.8: Gmail Label Management

As a system,
I want to create and manage Gmail labels (folders) programmatically,
So that I can organize emails into user-defined categories.

**Acceptance Criteria:**
1. Method implemented in Gmail client to list existing Gmail labels
2. Method implemented to create new Gmail label with specified name
3. Method implemented to apply label to email message (add label to message)
4. Method implemented to remove label from email message
5. Label color and visibility settings configurable when creating labels
6. Error handling for duplicate label names (return existing label ID)
7. Database table created for FolderCategories (id, user_id, name, gmail_label_id, keywords, created_at)
8. Migration applied for FolderCategories table

**Prerequisites:** Story 1.5 (Gmail API client)

---

### Story 1.9: Email Sending Capability

As a system,
I want to send emails via Gmail API on behalf of authenticated users,
So that I can execute approved response actions.

**Acceptance Criteria:**
1. Method implemented in Gmail client to compose email message (MIME format)
2. Method implemented to send email using Gmail API (messages.send)
3. Support for plain text and HTML email bodies
4. Support for reply-to-thread functionality (includes In-Reply-To and References headers)
5. Sent emails include proper headers (From, To, Subject, Date)
6. Error handling for send failures (quota exceeded, invalid recipient)
7. Logging implemented for all sent emails (recipient, subject, timestamp, success/failure)
8. Test endpoint created for sending test email (POST /test/send-email)

**Prerequisites:** Story 1.5 (Gmail API client)

---

### Story 1.10: Integration Testing and Documentation

As a developer,
I want to create integration tests and documentation for Gmail integration,
So that I can verify the foundation works end-to-end and others can understand the system.

**Acceptance Criteria:**
1. Integration test created that runs complete OAuth flow (mocked Google OAuth)
2. Integration test verifies email polling and storage in database
3. Integration test verifies label creation and application to emails
4. Integration test verifies email sending capability
5. API documentation generated using FastAPI automatic docs (Swagger UI at /docs)
6. Architecture documentation created in docs/ folder explaining Gmail integration flow
7. Setup guide updated with Gmail API configuration steps
8. Environment variables documented in README.md

**Prerequisites:** Stories 1.4-1.9 (all Gmail integration stories)

---

**Epic 1 Summary:**
- **Total Stories:** 10
- **Delivers:** Complete Gmail integration foundation with OAuth, email monitoring, label management, and sending capabilities
- **Ready for:** Epic 2 (AI Sorting) and Epic 3 (Telegram Bot)

---

## Epic 2: AI Sorting Engine & Telegram Approval

**Expanded Goal:**

Implement the AI-powered email classification system using Grok LLM and create the human-in-the-loop approval workflow via Telegram bot. This epic delivers the first major user-facing value proposition: intelligent email sorting with mobile-first approval interface that eliminates manual email triage.

**Value Delivery:**

By the end of this epic, users can receive Telegram notifications about incoming emails with AI-generated sorting proposals, approve or reject suggestions via interactive buttons, and have emails automatically organized into folders in Gmail. This demonstrates the core "AI + human control" paradigm that defines Mail Agent.

**Estimated Stories:** 12 stories

---

### Story 2.1: Gemini LLM Integration

As a developer,
I want to integrate Google Gemini 2.5 Flash API into the backend service,
So that I can use AI for email classification and response generation.

**Acceptance Criteria:**
1. Gemini API key obtained from Google AI Studio and stored in environment variables
2. Gemini Python SDK (google-generativeai) integrated into backend service
3. Model configured: gemini-2.5-flash (or gemini-2.5-flash-latest alias)
4. Basic prompt-response method created (send_prompt, receive_completion)
5. Error handling implemented for API failures, rate limits, and timeouts
6. Token usage tracking implemented for monitoring free tier usage (1M tokens/minute)
7. Fallback strategy documented for Gemini unavailability (Claude/GPT-4 alternatives)
8. Test endpoint created to verify Gemini connectivity (POST /test/gemini)
9. Response parsing implemented to extract structured data from LLM responses (JSON mode)

**Prerequisites:** Story 1.2 (backend service foundation)

---

### Story 2.2: Email Classification Prompt Engineering

As a developer,
I want to create effective prompts for email classification,
So that the AI can accurately suggest which folder category each email belongs to.

**Acceptance Criteria:**
1. Classification prompt template created with placeholders for email metadata and user categories
2. Prompt includes email sender, subject, body preview, and user-defined folder categories
3. Prompt instructs LLM to output structured JSON with folder suggestion and reasoning
4. Prompt examples created showing expected input/output format
5. Testing performed with sample emails across different categories (government, clients, newsletters)
6. Multilingual capability validated (prompt works for Russian, Ukrainian, English, German emails)
7. Edge cases handled (unclear emails, multiple possible categories)
8. Prompt version stored in config for future refinement

**Prerequisites:** Story 2.1 (Grok integration)

---

### Story 2.3: AI Email Classification Service

As a system,
I want to analyze pending emails and generate folder classification suggestions using AI,
So that I can propose intelligent sorting actions to users.

**Acceptance Criteria:**
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

**Prerequisites:** Story 2.2 (classification prompts), Story 1.7 (email data model)

---

### Story 2.4: Telegram Bot Foundation

As a developer,
I want to set up a Telegram bot that can send and receive messages,
So that I can implement the approval workflow interface.

**Acceptance Criteria:**
1. Telegram bot created via BotFather and bot token obtained
2. Bot token stored securely in environment variables
3. python-telegram-bot library integrated into backend service
4. Bot initialized and connected on application startup
5. Basic bot commands implemented (/start, /help)
6. Bot can send messages to specific Telegram user IDs
7. Bot can receive messages and button clicks from users
8. Webhook or polling mechanism set up for receiving updates
9. Test command created to verify bot connectivity (/test)

**Prerequisites:** Story 1.2 (backend service foundation)

---

### Story 2.5: User-Telegram Account Linking

As a user,
I want to link my Telegram account to my Mail Agent account,
So that I can receive email notifications and approve actions via Telegram.

**Acceptance Criteria:**
1. Unique linking code generation implemented (6-digit alphanumeric code)
2. LinkingCodes table created (code, user_id, expires_at, used)
3. API endpoint created to generate linking code for authenticated user (POST /telegram/generate-code)
4. Bot command /start [code] implemented to link Telegram user with code
5. Bot validates linking code and associates telegram_id with user in database
6. Expired codes (>15 minutes old) rejected with error message
7. Used codes cannot be reused
8. Success message sent to user on Telegram after successful linking
9. User's telegram_id stored in Users table

**Prerequisites:** Story 2.4 (Telegram bot foundation), Story 1.4 (user authentication)

---

### Story 2.6: Email Sorting Proposal Messages

As a user,
I want to receive Telegram messages showing email sorting proposals with preview and reasoning,
So that I can review AI suggestions before they are applied.

**Acceptance Criteria:**
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

**Prerequisites:** Story 2.5 (Telegram linking), Story 2.3 (AI classification)

---

### Story 2.7: Approval Button Handling

As a user,
I want to interact with approval buttons in Telegram,
So that I can approve, reject, or modify AI sorting suggestions.

**Acceptance Criteria:**
1. Button callback handlers implemented for [Approve], [Change Folder], [Reject]
2. [Approve] callback applies suggested Gmail label and updates status to "completed"
3. [Reject] callback updates status to "rejected" and leaves email in inbox
4. [Change Folder] callback presents list of available folders as inline keyboard
5. Folder selection callback applies selected label to email
6. Confirmation message sent after each action ("✅ Email sorted to [Folder]")
7. Button callback includes email queue ID for tracking
8. Callback data validated (user owns the email being processed)
9. Error handling for Gmail API failures during label application

**Prerequisites:** Story 2.6 (sorting proposal messages), Story 1.8 (label management)

---

### Story 2.8: Batch Notification System

As a user,
I want to receive daily batch notifications summarizing emails that need my review,
So that I'm not interrupted constantly throughout the day.

**Acceptance Criteria:**
1. Batch notification scheduling implemented (configurable time, default: end of day)
2. Batch job retrieves all pending emails (status="awaiting_approval") for each user
3. Summary message created showing count of emails needing review
4. Summary includes breakdown by proposed category (e.g., "3 to Government, 2 to Clients")
5. Individual proposal messages sent after summary (one message per email)
6. High-priority emails bypass batching and notify immediately
7. User preference stored for batch timing (NotificationPreferences table)
8. Empty batch handling (no message sent if no pending emails)
9. Batch completion logged for monitoring

**Prerequisites:** Story 2.6 (sorting proposal messages)

---

### Story 2.9: Priority Email Detection

As a system,
I want to detect high-priority emails that need immediate attention,
So that users are notified immediately rather than waiting for batch processing.

**Acceptance Criteria:**
1. Priority detection rules defined (keywords: "urgent", "deadline", "wichtig", specific senders)
2. Government sender detection implemented (domains: finanzamt.de, auslaenderbehoerde.de, etc.)
3. Priority scoring algorithm created (0-100 score based on multiple factors)
4. Emails scoring above threshold (e.g., 70+) marked as high-priority
5. High-priority flag stored in EmailProcessingQueue
6. High-priority emails bypass batch scheduling and notify immediately
7. Priority indicator added to Telegram messages (⚠️ emoji)
8. User can configure custom priority senders in FolderCategories settings
9. Priority detection logged for analysis and refinement

**Prerequisites:** Story 2.3 (AI classification), Story 2.8 (batch notifications)

---

### Story 2.10: Approval History Tracking

As a system,
I want to track all user approval decisions,
So that I can monitor accuracy and potentially learn from user patterns in the future.

**Acceptance Criteria:**
1. ApprovalHistory table created (id, user_id, email_queue_id, action_type, ai_suggested_folder, user_selected_folder, approved, timestamp)
2. Approval event recorded when user clicks [Approve] (approved=true)
3. Rejection event recorded when user clicks [Reject] (approved=false)
4. Folder change event recorded with both AI suggestion and user selection
5. History queryable by user, date range, and approval type
6. Statistics endpoint created showing approval rate per user (GET /stats/approvals)
7. Database indexes added for efficient history queries
8. Privacy considerations documented (history retention policy)

**Prerequisites:** Story 2.7 (approval button handling)

---

### Story 2.11: Error Handling and Recovery

As a user,
I want the system to handle errors gracefully and allow me to retry failed actions,
So that temporary failures don't result in lost emails or stuck processing.

**Acceptance Criteria:**
1. Gmail API errors caught and logged with context (email_id, user_id, error type)
2. Telegram API errors caught and logged (message send failures, button callback failures)
3. Retry mechanism implemented for transient failures (max 3 retries with exponential backoff)
4. Failed emails moved to "error" status after max retries
5. Error notification sent to user via Telegram for persistent failures
6. Manual retry command implemented in Telegram (/retry [email_id])
7. Admin dashboard endpoint shows emails in error state (GET /admin/errors)
8. Dead letter queue implemented for emails that repeatedly fail processing
9. Health monitoring alerts configured for high error rates

**Prerequisites:** Story 2.7 (approval handling), Story 2.6 (Telegram messages)

---

### Story 2.12: Epic 2 Integration Testing

As a developer,
I want to create end-to-end tests for the AI sorting and approval workflow,
So that I can verify the complete user journey works as expected.

**Acceptance Criteria:**
1. Integration test simulates complete flow: new email → AI classification → Telegram proposal → user approval → Gmail label applied
2. Test mocks Gmail API, Grok API, and Telegram API
3. Test verifies email moves through all status states correctly
4. Test validates approval history is recorded accurately
5. Test covers rejection and folder change scenarios
6. Test validates batch notification logic
7. Test validates priority email immediate notification
8. Performance test ensures processing completes within 2 minutes (NFR001)
9. Documentation updated with Epic 2 architecture and flow diagrams

**Prerequisites:** All Epic 2 stories (2.1-2.11)

---

**Epic 2 Summary:**
- **Total Stories:** 12
- **Delivers:** Complete AI-powered email sorting with Telegram-based human approval workflow
- **User Value:** Automated email organization with full user control via mobile interface
- **Ready for:** Epic 3 (RAG response generation) and Epic 4 (Configuration UI)

---

## Epic 3: RAG System & Response Generation

**Expanded Goal:**

Build a Retrieval-Augmented Generation (RAG) system that indexes complete email conversation history and generates contextually appropriate, multilingual email responses. This epic delivers the second major value proposition: AI-generated draft responses that understand full conversation context across 4 languages, eliminating the need for manual thread review.

**Value Delivery:**

By the end of this epic, users receive AI-generated response drafts in Telegram that incorporate full conversation history, use the correct language and tone, and require minimal editing before sending. This demonstrates the power of RAG for context-aware communication automation.

**Estimated Stories:** 10 stories

---

### Story 3.1: Vector Database Setup

As a developer,
I want to set up a vector database for storing email embeddings,
So that I can perform semantic search for context retrieval.

**Acceptance Criteria:**
1. Vector database selected (ChromaDB for self-hosted or Pinecone free tier)
2. Vector database installed and configured (local or cloud)
3. Database connection code created with error handling
4. Collection created for email embeddings with metadata schema
5. Basic CRUD operations implemented (insert, query, delete embeddings)
6. Connection test endpoint created (GET /test/vector-db)
7. Database configuration documented (indexing parameters, distance metrics)
8. Data persistence configured (embeddings survive service restarts)

**Prerequisites:** Story 1.2 (backend service foundation)

---

### Story 3.2: Email Embedding Service

As a system,
I want to convert email content into vector embeddings,
So that I can store and retrieve emails semantically.

**Acceptance Criteria:**
1. Embedding model selected (OpenAI text-embedding-3-small or sentence-transformers)
2. Embedding API client integrated into backend
3. Email content preprocessing implemented (clean HTML, extract text, handle attachments metadata)
4. Method created to generate embedding vector from email text
5. Embedding dimensions validated (match vector DB configuration)
6. Batch embedding support for processing multiple emails efficiently
7. Error handling for embedding API failures (rate limits, timeouts)
8. Token usage tracking for monitoring free tier limits

**Prerequisites:** Story 3.1 (vector database setup)

---

### Story 3.3: Email History Indexing

As a system,
I want to index all existing emails from user's Gmail into the vector database,
So that I have complete conversation history available for context retrieval.

**Acceptance Criteria:**
1. Background job created to index user's email history on first setup
2. Job retrieves all emails from Gmail (paginated, handles large mailboxes)
3. Each email converted to embedding and stored in vector DB with metadata (message_id, thread_id, sender, date, subject)
4. Thread relationship metadata preserved (parent-child email linking)
5. Incremental indexing implemented (only new emails indexed after initial sync)
6. Progress tracking for long-running indexing jobs (stored in database)
7. Indexing job resumable after interruption (checkpoint mechanism)
8. User notified via Telegram when initial indexing completes

**Prerequisites:** Story 3.2 (embedding service), Story 1.5 (Gmail client)

---

### Story 3.4: Context Retrieval Service

As a system,
I want to retrieve relevant conversation context for an incoming email,
So that I can provide the AI with necessary background for response generation.

**Acceptance Criteria:**
1. Context retrieval method created that takes email message_id as input
2. Method retrieves thread history from Gmail using thread_id
3. Method performs semantic search in vector DB using email content as query
4. Top-k most relevant emails retrieved (k=5-10 configurable)
5. Results combined: thread history + semantically similar emails
6. Results ranked by relevance score and recency
7. Context window managed to stay within LLM token limits (e.g., 4000 tokens)
8. Context formatted as structured summary for LLM prompt
9. Query performance measured (target: <3 seconds per NFR001)

**Prerequisites:** Story 3.3 (email indexing)

---

### Story 3.5: Language Detection

As a system,
I want to detect the language of incoming emails accurately,
So that I can generate responses in the correct language.

**Acceptance Criteria:**
1. Language detection library integrated (langdetect or fasttext)
2. Detection method created that analyzes email body text
3. Supports 4 target languages: Russian (ru), Ukrainian (uk), English (en), German (de)
4. Confidence score calculated for language prediction
5. Mixed-language emails handled (use primary language)
6. Detection validated with test emails in all 4 languages
7. Language stored in EmailProcessingQueue for later use
8. Fallback to English if detection confidence is low (<0.7)

**Prerequisites:** Story 1.7 (email data model)

---

### Story 3.6: Response Generation Prompt Engineering

As a developer,
I want to create effective prompts for email response generation,
So that the AI generates appropriate, contextual responses.

**Acceptance Criteria:**
1. Response prompt template created with placeholders for email content, context, and language
2. Prompt includes: original email, conversation thread summary, relevant context from RAG
3. Prompt instructs LLM to generate response in specified language with appropriate tone
4. Tone detection logic implemented (formal for government, professional for business, casual for personal)
5. Prompt examples created showing expected output for different scenarios
6. Testing performed with sample emails across languages and tones
7. Prompt includes constraints (length, formality level, key points to address)
8. Prompt version stored in config for refinement

**Prerequisites:** Story 3.4 (context retrieval), Story 3.5 (language detection)

---

### Story 3.7: AI Response Generation Service

As a system,
I want to generate contextually appropriate email response drafts using RAG,
So that I can present quality drafts to users for approval.

**Acceptance Criteria:**
1. Response generation service created that processes emails needing replies
2. Service determines if email requires response (not all emails need replies)
3. Service retrieves conversation context using context retrieval service
4. Service detects email language and determines appropriate tone
5. Service constructs response prompt with all context
6. Service calls Grok LLM API and receives response draft
7. Generated response stored in EmailProcessingQueue (response_draft field)
8. Response quality validation (not empty, appropriate length, correct language)
9. Processing status updated to "awaiting_approval" with classification="needs_response" (differentiates from "sort_only" emails)

**Prerequisites:** Story 3.6 (response prompts), Story 2.1 (Grok integration)

---

### Story 3.8: Response Draft Telegram Messages

As a user,
I want to receive Telegram messages showing AI-generated response drafts with original email context,
So that I can review and approve responses before sending.

**Acceptance Criteria:**
1. Message template created for response draft proposals
2. Message includes: original sender, subject, email preview (first 100 chars)
3. Message includes AI-generated response draft (full text)
4. Message formatted with clear visual separation (original vs. draft)
5. Inline buttons added: [Send] [Edit] [Reject]
6. Language of response draft indicated (e.g., "Draft in German:")
7. Context summary shown if relevant ("Based on 3 previous emails in this thread")
8. Message respects Telegram length limits (split long drafts if needed)
9. Priority response drafts flagged with ⚠️ icon

**Prerequisites:** Story 3.7 (response generation), Story 2.6 (Telegram messaging)

---

### Story 3.9: Response Editing and Sending

As a user,
I want to edit AI-generated drafts directly in Telegram before sending,
So that I can quickly modify responses without leaving Telegram.

**Acceptance Criteria:**
1. [Edit] button handler implemented that prompts user for modified text
2. User can reply to bot message with edited response text
3. Edited text replaces AI-generated draft in database
4. [Send] button applies to both original draft and edited versions
5. [Send] handler retrieves response text and sends via Gmail API
6. Sent response properly threaded (In-Reply-To header set)
7. Confirmation message sent after successful send ("✅ Response sent to [recipient]")
8. Email status updated to "completed" after sending
9. Sent response indexed into vector DB for future context

**Prerequisites:** Story 3.8 (response draft messages), Story 1.9 (email sending)

---

### Story 3.10: Multilingual Response Quality Testing

As a developer,
I want to validate response quality across all 4 supported languages,
So that I can ensure the system generates appropriate responses in each language.

**Acceptance Criteria:**
1. Test suite created with sample emails in Russian, Ukrainian, English, German
2. Each test includes: original email, expected context retrieved, generated response
3. Response quality evaluated for: correct language, appropriate tone, context awareness
4. Formal German tested specifically (government email responses)
5. Edge cases tested (mixed languages, unclear context, no previous thread)
6. Performance benchmarks recorded (context retrieval + generation time)
7. Integration test covering full flow: email receipt → RAG retrieval → response generation → Telegram delivery → user approval → send
8. Documentation updated with Epic 3 architecture (RAG flow diagram, context retrieval logic)
9. Known limitations documented (prompt refinement needs, language quality variations)

**Prerequisites:** All Epic 3 stories (3.1-3.9)

---

### Story 3.11: Workflow Integration & Conditional Routing

As a system,
I want emails to be conditionally routed based on whether they need responses,
So that only relevant emails trigger response generation and users receive appropriate Telegram messages.

**Acceptance Criteria:**
1. Update `classify` node to call `ResponseGenerationService.should_generate_response()` and set `classification` field ("sort_only" or "needs_response")
2. Implement `route_by_classification()` conditional edge function that returns "draft_response" or "send_telegram"
3. Create `draft_response` node that calls `ResponseGenerationService.generate_response_draft()` and updates state
4. Add conditional edges in workflow graph: classify → route_by_classification → {needs_response: draft_response, sort_only: send_telegram}
5. Add edge: draft_response → send_telegram
6. Update `send_telegram` node to use response draft template when `state["draft_response"]` exists, sorting template otherwise
7. Integration test verifies "needs_response" path: email with question → classify → draft → telegram (shows draft)
8. Integration test verifies "sort_only" path: newsletter → classify → telegram (sorting only, no draft)
9. Update Epic 3 documentation marking workflow integration complete

**Prerequisites:** All Epic 3 stories (3.1-3.10)

---

**Epic 3 Summary:**
- **Total Stories:** 11
- **Delivers:** Complete RAG-powered response generation with multilingual support and context-aware drafting
- **User Value:** AI-generated responses that understand conversation history, eliminating manual context review
- **Technical Achievement:** Production RAG system with vector search, embedding, and multilingual generation
- **Ready for:** Epic 4 (Configuration UI and Onboarding)

---

## Epic 4: Configuration UI & Onboarding

**Expanded Goal:**

Create a user-friendly web-based configuration interface and guided onboarding experience that enables non-technical users to set up Mail Agent in under 10 minutes. This epic delivers the polished user-facing setup workflow that makes the system accessible to the target audience of multilingual professionals without technical expertise.

**Value Delivery:**

By the end of this epic, new users can complete the entire setup process through an intuitive web interface: connect Gmail, link Telegram, define folder categories, configure preferences, and test the system—all without technical knowledge. This removes onboarding friction and validates the "non-technical user" requirement.

**Estimated Stories:** 8 stories

---

### Story 4.1: Frontend Project Setup

As a developer,
I want to set up the Next.js frontend project with proper structure and tooling,
So that I have a foundation for building the configuration UI.

**Acceptance Criteria:**
1. Next.js project initialized with TypeScript support
2. Project structure created (pages, components, lib, styles folders)
3. Tailwind CSS configured for styling
4. Component library integrated (shadcn/ui or Material-UI)
5. API client configured to communicate with backend (fetch or axios)
6. Environment variables setup for backend API URL
7. Development server runs successfully on localhost:3000
8. Basic layout component created with header and navigation

**Prerequisites:** Story 1.1 (project infrastructure)

---

### Story 4.2: Gmail OAuth Connection Page

As a user,
I want to connect my Gmail account through a simple web interface,
So that I can authorize Mail Agent to access my email.

**Acceptance Criteria:**
1. Landing page created with clear value proposition and "Connect Gmail" CTA
2. Gmail connection page explains required permissions (read, write, labels)
3. "Connect Gmail" button triggers OAuth flow (calls backend /auth/gmail/login)
4. User redirected to Google OAuth consent screen
5. After approval, user redirected back to app with success confirmation
6. Connection status displayed (connected email address, last sync time)
7. Error handling for OAuth failures (user denies, network errors)
8. Reconnect option provided if connection fails or expires
9. Visual indicators (checkmarks, loading states) for connection progress

**Prerequisites:** Story 4.1 (frontend setup), Story 1.4 (Gmail OAuth backend)

---

### Story 4.3: Telegram Bot Linking Page

As a user,
I want to link my Telegram account with step-by-step guidance,
So that I can receive email notifications without confusion.

**Acceptance Criteria:**
1. Telegram linking page displays step-by-step instructions with visuals
2. Instructions include: "1. Open Telegram, 2. Search for @MailAgentBot, 3. Send /start [code]"
3. Unique linking code generated and displayed prominently (large font, copyable)
4. "Copy Code" button copies code to clipboard with confirmation
5. Link to open Telegram app directly (deep link: tg://resolve?domain=mailagentbot)
6. Real-time status checking (polls backend every 5 seconds to check if linked)
7. Success confirmation shown when Telegram account is linked
8. Timeout after 15 minutes with option to generate new code
9. Error handling for expired or invalid codes

**Prerequisites:** Story 4.1 (frontend setup), Story 2.5 (Telegram linking backend)

---

### Story 4.4: Folder Categories Configuration

As a user,
I want to create and manage my email folder categories through an intuitive interface,
So that I can organize emails according to my needs.

**Acceptance Criteria:**
1. Folder management page displays list of existing categories
2. "Add Category" button opens creation dialog
3. Creation dialog includes: category name input, optional keywords field, color picker
4. Category name validation (not empty, max 50 chars, no duplicates)
5. Keywords field allows comma-separated list (e.g., "finanzamt, tax, steuer")
6. Created categories displayed as cards with edit/delete actions
7. Edit functionality allows updating name and keywords
8. Delete confirmation dialog prevents accidental deletion
9. Default categories pre-populated (Important, Government, Clients, Newsletters)
10. Changes automatically sync with backend (create Gmail labels)
11. Visual feedback for save success/failure

**Prerequisites:** Story 4.1 (frontend setup), Story 1.8 (label management backend)

---

### Story 4.5: Notification Preferences Settings

As a user,
I want to configure when and how I receive Telegram notifications,
So that I can control interruptions and batch timing.

**Acceptance Criteria:**
1. Settings page created with notification preferences section
2. Batch notification toggle (enable/disable daily batching)
3. Batch timing selector (dropdown: end of day, morning, custom time)
4. Priority notification toggle (enable/disable immediate high-priority alerts)
5. Quiet hours configuration (start time, end time) to suppress notifications
6. Notification preview mode (test notification button)
7. Preferences saved to backend (NotificationPreferences table)
8. Real-time validation (e.g., quiet hours end must be after start)
9. Default settings pre-selected based on best practices
10. Changes take effect immediately after save

**Prerequisites:** Story 4.1 (frontend setup), Story 2.8 (batch notification backend)

---

### Story 4.6: Onboarding Wizard Flow

As a user,
I want to be guided through setup with a step-by-step wizard,
So that I complete all required configuration without getting lost.

**Acceptance Criteria:**
1. Wizard component created with progress indicator (Step 1 of 4, etc.)
2. Step 1: Welcome screen explaining Mail Agent benefits and what to expect
3. Step 2: Gmail connection (reuses Gmail OAuth page)
4. Step 3: Telegram linking (reuses Telegram linking page)
5. Step 4: Folder setup (simplified category creation, minimum 3 required)
6. Step 5: Test & Confirm (send test email notification, verify working)
7. Navigation buttons (Next, Back, Skip optional steps)
8. Steps cannot proceed until required actions completed (e.g., Gmail connected)
9. Progress saved (user can close and resume later from same step)
10. Completion celebration screen with "Start Using Mail Agent" button
11. First-time user automatically directed to wizard on login

**Prerequisites:** Stories 4.2, 4.3, 4.4 (all setup pages)

---

### Story 4.7: Dashboard Overview Page

As a user,
I want to see a dashboard showing my system status and recent activity,
So that I can quickly understand if everything is working correctly.

**Acceptance Criteria:**
1. Dashboard page created as default view after onboarding
2. Connection status cards showing Gmail and Telegram status (connected/disconnected)
3. Email processing statistics: emails processed today, approval rate, pending actions
4. Recent activity feed: last 10 email actions (sorted, sent, rejected)
5. Quick actions section: "Manage Folders", "Update Settings", "View Stats"
6. System health indicator (all systems operational, warnings if issues)
7. RAG indexing progress shown if initial indexing in progress
8. Helpful tips section for new users (getting started guidance)
9. Refresh button to update statistics in real-time
10. Responsive design (mobile and desktop layouts)

**Prerequisites:** Story 4.1 (frontend setup), Stories 1.6, 2.10 (backend data)

---

### Story 4.8: End-to-End Onboarding Testing and Polish

As a user,
I want the onboarding experience to be smooth, clear, and error-free,
So that I successfully complete setup on my first attempt.

**Acceptance Criteria:**
1. Usability testing conducted with 3-5 non-technical users
2. Onboarding completion time measured (target: <10 minutes per NFR005)
3. Success rate tracked (target: 90%+ complete successfully)
4. Pain points identified and addressed (confusing instructions, unclear errors)
5. Copy and messaging refined based on user feedback
6. Visual design polished (consistent spacing, colors, typography)
7. Loading states and error messages improved for clarity
8. Mobile responsiveness validated (works on phone browsers)
9. Browser compatibility tested (Chrome, Firefox, Safari, Edge)
10. Comprehensive documentation created for setup process
11. Video tutorial recorded showing complete onboarding flow (optional)
12. Help/support link added to every page with FAQ
13. WCAG 2.1 Level AA compliance validated for all pages
14. Screen reader compatibility tested (NVDA or VoiceOver)
15. Keyboard-only navigation tested for complete onboarding flow
16. Color contrast checked (minimum 4.5:1 for text)

**Prerequisites:** All Epic 4 stories (4.1-4.7)

---

**Epic 4 Summary:**
- **Total Stories:** 8
- **Delivers:** Complete web-based configuration UI with guided onboarding for non-technical users
- **User Value:** Accessible 10-minute setup process requiring zero technical knowledge
- **Success Criteria:** 90%+ onboarding completion rate within 10 minutes (NFR005)
- **Project Completion:** All 4 epics deliver complete MVP functionality

---

## Project Summary

**Total Stories Across All Epics:**
- Epic 1: 10 stories (Foundation & Gmail)
- Epic 2: 12 stories (AI Sorting & Telegram)
- Epic 3: 11 stories (RAG & Response Generation)
- Epic 4: 8 stories (Configuration UI)
- **Grand Total: 41 stories**

**Delivery Milestones:**
1. After Epic 1: Working Gmail integration and email monitoring
2. After Epic 2: AI-powered sorting with Telegram approval (first major user value)
3. After Epic 3: RAG-powered response generation (second major user value)
4. After Epic 4: Complete MVP ready for personal use and beta testing

**Alignment with PRD Goals:**
- ✅ Goal 1: Time reduction (60-75%) - Epics 2+3 deliver automation
- ✅ Goal 2: 95%+ accuracy - Epic 2 AI sorting, Epic 3 RAG quality
- ✅ Goal 3: Multilingual responses - Epic 3 language detection and generation
- ✅ Goal 4: User control - Epic 2 human-in-the-loop approval
- ✅ Goal 5: Zero-cost infrastructure - All epics designed for free-tier services

**Next Steps After Epic Completion:**
1. Personal dogfooding (use the system daily for 2-4 weeks)
2. Iterate based on personal usage patterns and pain points
3. Invite 5-10 beta users from trusted network
4. Gather feedback and refine (focus on approval rates and time savings)
5. Create portfolio case study with metrics and learnings

---

## Story Guidelines Reference

**Story Format:**

```
**Story [EPIC.N]: [Story Title]**

As a [user type],
I want [goal/desire],
So that [benefit/value].

**Acceptance Criteria:**
1. [Specific testable criterion]
2. [Another specific criterion]
3. [etc.]

**Prerequisites:** [Dependencies on previous stories, if any]
```

**Story Requirements:**

- **Vertical slices** - Complete, testable functionality delivery
- **Sequential ordering** - Logical progression within epic
- **No forward dependencies** - Only depend on previous work
- **AI-agent sized** - Completable in 2-4 hour focused session
- **Value-focused** - Integrate technical enablers into value-delivering stories

---

**For implementation:** Use the `create-story` workflow to generate individual story implementation plans from this epic breakdown.
