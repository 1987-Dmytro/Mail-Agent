# Mail Agent Product Requirements Document (PRD)

**Author:** Dimcheg
**Date:** 2025-11-03
**Project Level:** 3
**Target Scale:** 10,000 users

---

## Goals and Background Context

### Goals

1. Reduce daily email management time by 60-75% (from 20-60 min/day to 5-15 min/day)
2. Achieve 95%+ accuracy in identifying and processing important emails to eliminate missed communications
3. Deliver contextually appropriate multilingual responses across 4 languages (Russian, Ukrainian, English, German) without manual context review
4. Maintain complete user control through human-in-the-loop approval workflow via Telegram
5. Operate on zero-cost infrastructure using free-tier services while supporting variable email loads (5-50+ emails/day per user)

### Background Context

Multilingual professionals in Germany managing business and government communication across 4 languages spend 20-60 minutes daily on email management. This includes sorting incoming messages, reviewing full conversation threads for context, and composing appropriate responses in multiple languages. The problem becomes acute with German bureaucratic communications requiring timely, formal responses, where delays can have consequences. Existing solutions either automate without intelligence (Gmail filters) or assist without automation (Superhuman), leaving the core burden unsolved.

Mail Agent is an AI-powered Gmail automation assistant that intelligently sorts emails and generates contextually appropriate responses using RAG (Retrieval-Augmented Generation) to analyze full conversation history. All actions are proposed via Telegram for user approval before execution, ensuring trust and control. Built on free-tier infrastructure (Google Gemini 2.5 Flash LLM with unlimited free tier, free hosting), the system targets non-technical users with a mobile-first approval workflow that eliminates the need to open Gmail for daily email management.

---

## Requirements

### Functional Requirements

**Gmail Integration**
- FR001: System shall authenticate users via Gmail OAuth 2.0 and obtain read/write email access permissions
- FR002: System shall read incoming emails from user's Gmail inbox in real-time or near-real-time
- FR003: System shall create and manage Gmail labels (folders) based on user-defined categories
- FR004: System shall move emails to specified Gmail labels upon user approval
- FR005: System shall send email responses on behalf of the user upon approval
- FR006: System shall access full email thread history for context analysis

**Telegram Bot Integration**
- FR007: System shall allow users to link their Telegram account with their Gmail account
- FR008: System shall send email sorting proposals to users via Telegram with email preview and reasoning
- FR009: System shall send draft response proposals to users via Telegram with original email context
- FR010: System shall provide interactive approval buttons (Approve/Edit/Reject) for each proposal in Telegram
- FR011: System shall allow users to edit AI-generated drafts directly within Telegram before approval
- FR012: System shall send batch notifications summarizing daily email processing activity

**AI Email Sorting**
- FR013: System shall analyze incoming emails based on sender, subject, content, and thread history
- FR014: System shall classify emails into user-defined categories configured during setup
- FR015: System shall provide reasoning/rationale for each sorting proposal presented to users
- FR016: System shall execute approved sorting actions by applying Gmail labels

**RAG-Powered Response Generation**
- FR017: System shall index complete email conversation history in a vector database for context retrieval
- FR018: System shall detect the appropriate response language (Russian, Ukrainian, English, German) based on email context
- FR019: System shall generate contextually appropriate professional responses using RAG with full conversation history
- FR020: System shall maintain conversation tone and formality level consistent with email context
- FR021: System shall present AI-generated response drafts to users for approval via Telegram

**Configuration Web UI**
- FR022: System shall provide a web-based configuration interface for initial setup and settings management
- FR023: System shall guide users through Gmail OAuth connection with clear permission explanations
- FR024: System shall allow users to configure Telegram bot connection with step-by-step instructions
- FR025: System shall enable users to create and name custom email folder categories (Gmail labels)
- FR026: System shall allow users to define basic sorting rules using keywords or sender patterns
- FR027: System shall provide connection testing functionality to verify Gmail and Telegram integrations

### Non-Functional Requirements

- **NFR001: Performance** - Email processing latency shall not exceed 2 minutes from email receipt to Telegram notification delivery, and RAG context retrieval shall complete within 3 seconds for response generation

- **NFR002: Reliability** - System shall maintain 99.5% uptime during MVP phase with zero data loss or incorrect email sending (99.9%+ sending reliability)

- **NFR003: Scalability** - System shall support variable email loads of 5-50+ emails per day per user without performance degradation, and architecture shall accommodate growth from 1 to 100 users on free-tier infrastructure

- **NFR004: Security & Privacy** - System shall encrypt OAuth tokens at rest, use TLS/HTTPS for all communications, implement multi-tenant data isolation, and comply with basic GDPR requirements for EU user data handling

- **NFR005: Usability** - Non-technical users shall complete onboarding (Gmail OAuth + Telegram bot setup + folder configuration) within 10 minutes, achieving 90%+ successful completion rate

---

## User Journeys

**Journey 1: Initial Setup and Onboarding**

1. User visits Mail Agent web application
2. User clicks "Connect Gmail" and is redirected to Google OAuth consent screen
3. User reviews permissions (read/write email, manage labels) and grants access
4. System successfully connects to Gmail and confirms connection
5. User is guided to create Telegram bot connection:
   - Opens Telegram, searches for Mail Agent bot
   - Sends `/start` command to bot
   - Bot provides unique linking code
6. User enters linking code in web UI
7. System verifies Telegram connection
8. User is prompted to define email folders (categories):
   - Creates 3-5 folder categories (e.g., "Important", "Government", "Clients", "Newsletters")
   - Optionally adds basic keyword rules for each folder
9. User tests connection: System sends test message to Telegram
10. User confirms successful setup and completes onboarding
11. System begins monitoring Gmail inbox for new emails

**Journey 2: Daily Email Processing - Sorting and Response Approval**

1. User receives 8 new emails throughout the day
2. System analyzes each email using AI and RAG context
3. At end of day (or configured interval), user receives Telegram batch notification:
   - "8 emails processed: 3 proposals need your review"
4. User opens Telegram and sees first proposal:
   - Email preview (sender, subject, first 2 lines)
   - Proposed action: "Sort to 'Government' folder"
   - Reasoning: "Email from Finanzamt regarding tax documents"
   - Buttons: [Approve] [Change Folder] [Reject]
5. User taps [Approve] - System applies label in Gmail
6. User sees second proposal:
   - Email preview showing client inquiry
   - Proposed action: "Draft response ready"
   - AI-generated response shown (in German)
   - Buttons: [Send] [Edit] [Reject]
7. User taps [Edit], modifies one sentence in response
8. User taps [Send Modified] - System sends email from user's Gmail
9. User sees third proposal:
   - Newsletter email
   - Proposed action: "Sort to 'Newsletters' folder"
   - Reasoning: "Recurring sender, promotional content"
10. User taps [Approve] - System applies label
11. User receives summary: "3 emails sorted, 1 response sent, 4 auto-filed (no action needed)"
12. Total time spent: 5 minutes

**Journey 3: Handling Critical Government Email with Context**

1. User receives email from Ausländerbehörde (immigration office) requesting document submission
2. System detects email priority based on sender and content analysis
3. System uses RAG to retrieve full conversation history with Ausländerbehörde from past 6 months
4. User receives immediate Telegram notification (high-priority, not batched):
   - "⚠️ Important: Government email requires response"
   - Email preview with full context summary
   - AI-generated formal German response draft:
     - Acknowledges receipt of request
     - Confirms document submission timeline
     - Uses formal German tone appropriate for bureaucracy
5. User reviews response draft and context summary
6. User recognizes AI correctly understood the entire case history
7. User makes minor edit to submission date
8. User taps [Send Modified]
9. System sends email immediately from user's Gmail
10. User receives confirmation: "Response sent to Ausländerbehörde"
11. User feels confident: No manual context review needed, formal tone correct, deadline acknowledged
12. Time spent: 2 minutes (vs. 15 minutes manual review + drafting)

---

## UX Design Principles

1. **Trust Through Transparency** - Every AI action must show clear reasoning and allow user approval before execution. Users must understand what the system is doing and why.

2. **Mobile-First Control** - Primary interaction via Telegram enables email management from anywhere without opening Gmail. All approval workflows must work seamlessly on mobile devices.

3. **Minimize Cognitive Load** - Present information concisely (email previews, not full content), use visual hierarchy (buttons, formatting), and batch notifications to reduce interruptions.

4. **Non-Technical Accessibility** - Setup and daily usage must require zero technical knowledge. Use plain language, visual guides, and familiar patterns (Telegram interface).

5. **Multilingual Native Experience** - System must handle 4 languages (Russian, Ukrainian, English, German) transparently without requiring user language selection or translation steps.

---

## User Interface Design Goals

**Configuration Web UI:**
- **Platform:** Responsive web application (desktop and mobile browser compatible)
- **Design System:** Clean, modern interface using component library (e.g., shadcn/ui or Material-UI)
- **Key Screens:**
  - Onboarding wizard (Gmail connection → Telegram connection → Folder setup → Testing)
  - Dashboard showing connection status and basic statistics
  - Folder management interface with drag-drop category creation
  - Settings page for notification preferences and sorting rules
- **Design Constraints:**
  - Must work on modern browsers (Chrome, Firefox, Safari, Edge - last 2 versions)
  - Mobile-responsive for setup on any device
  - WCAG 2.1 Level AA accessibility compliance (basic)

**Telegram Bot Interface:**
- **Interaction Patterns:**
  - Rich message cards showing email previews with sender, subject, and snippet
  - Inline buttons for quick actions (Approve/Edit/Reject)
  - Inline editing capability for response modifications
  - Summary notifications with actionable counts
- **Visual Hierarchy:**
  - Priority indicators for urgent emails (⚠️ icons)
  - Clear separation between sorting proposals and response drafts
  - Action confirmation messages with undo capability (if feasible)
- **Notification Strategy:**
  - Batch processing summaries (daily or user-configured intervals)
  - Immediate notifications for high-priority/government emails
  - Quiet hours respect user preferences

---

## Epic List

**Epic 1: Foundation & Gmail Integration** (Est. 8-12 stories)
- Goal: Establish project infrastructure and Gmail connectivity foundation, enabling basic email reading capabilities
- Delivers: Working development environment, Gmail OAuth flow, basic email monitoring

**Epic 2: AI Sorting Engine & Telegram Approval** (Est. 10-15 stories)
- Goal: Implement AI-powered email classification and human-in-the-loop approval workflow via Telegram
- Delivers: Fully functional email sorting with Telegram-based user approval

**Epic 3: RAG System & Response Generation** (Est. 8-12 stories)
- Goal: Build RAG architecture for context-aware response generation with multilingual support
- Delivers: AI-generated email responses with full conversation context across 4 languages

**Epic 4: Configuration UI & Onboarding** (Est. 6-10 stories)
- Goal: Create web-based configuration interface and guided onboarding for non-technical users
- Delivers: Complete user-facing setup workflow and management interface

**Total Estimated Stories: 32-49** (within Level 3 target range of 15-40)

> **Note:** Detailed epic breakdown with full story specifications is available in [epics.md](./epics.md)

---

## Out of Scope

**Deferred to Post-MVP:**

1. **Adaptive Learning & AI Personalization**
   - Machine learning from user corrections and approval patterns
   - Automatic improvement of sorting/response accuracy over time
   - User-specific AI model fine-tuning

2. **Advanced Automation Features**
   - Complex conditional folder rules (if/then logic)
   - Time-based automated actions (auto-archive, scheduled responses)
   - Sender reputation scoring and VIP detection
   - Proactive email composition (non-reply emails)

3. **Team & Collaboration Features**
   - Shared mailboxes and team accounts
   - Multi-user approval workflows
   - Delegation capabilities
   - Role-based access control

4. **Analytics & Reporting**
   - Time saved tracking and visualization
   - AI accuracy metrics dashboard
   - Email volume trends and insights
   - Performance reports and statistics

5. **Extended Platform Support**
   - Email providers beyond Gmail (Outlook, Yahoo, ProtonMail)
   - Native mobile applications (iOS/Android)
   - Messaging platforms beyond Telegram (WhatsApp, Slack)

6. **Advanced Integrations**
   - Calendar integration for meeting scheduling and deadline tracking
   - CRM system integration
   - Document management systems
   - Invoice and attachment processing automation

7. **Enterprise Features**
   - SSO/SAML authentication
   - Advanced encryption and compliance certifications
   - On-premise deployment options
   - SLA guarantees and priority support

**Explicitly NOT Included:**

- Multi-language support beyond the 4 target languages (Russian, Ukrainian, English, German)
- Email volume limits or throttling (system must handle variable loads)
- Manual email sorting (all sorting is AI-powered with user approval)
- Email archiving or backup services
- Spam filtering (relies on Gmail's existing spam detection)
