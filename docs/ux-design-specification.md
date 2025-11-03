# Mail Agent UX Design Specification

_Created on 2025-11-03 by Dimcheg_
_Generated using BMad Method - Create UX Design Workflow v1.0_

---

## Executive Summary

**Vision:** Mail Agent is an AI-powered email automation assistant that reduces daily email management time by 60-75% through intelligent sorting and RAG-powered multilingual response generation, with complete user control via Telegram approval workflow.

**Target Users:** Multilingual professionals in Germany managing business and government communication across 4 languages (Russian, Ukrainian, English, German), currently spending 20-60 minutes daily on email management.

**Core Experience:** "Tap to approve AI proposals in Telegram" - users review email sorting/responses and approve/reject in seconds, achieving that "success" feeling of inbox conquered in 5 minutes.

**Desired Emotional Response:** **SUCCESS** - users should feel accomplished, confident, and victorious when they complete their email review. Clear completion states, progress indicators, speed feedback, and accuracy reinforcement drive this emotion.

**Platform:**
- **Primary Interface:** Telegram bot (mobile-first approval workflow with iOS-style inline keyboards)
- **Secondary Interface:** Next.js 15 web-based configuration UI (one-time setup and settings)

**Inspiration:** iOS native patterns (clarity, instant feedback, smart notifications) + N26 banking UX (card-based design, 2-tap maximum, real-time updates, minimal aesthetics, dark mode).

---

## 1. Design System Foundation

### 1.1 Design System Choice

**Selected Design System: shadcn/ui**

**Decision:** shadcn/ui with Next.js 15 and Tailwind CSS v4 for the web configuration UI. Telegram's native inline keyboards for the bot interface.

**Rationale:**
- ✅ Modern, copy-paste component library built on Radix UI primitives
- ✅ WCAG 2.1 Level AA accessibility compliance built-in
- ✅ Perfect alignment with Next.js 15 + React 19 architecture
- ✅ Tailwind CSS v4 support for rapid customization
- ✅ Dark mode support (essential for evening email review sessions)
- ✅ Minimal aesthetic achievable (N26-inspired design)
- ✅ You own the code (no npm dependency lock-in)
- ✅ 50+ accessible components ready to use

**Version:** Latest (2025) - Compatible with Next.js 15 and React 19

**Components Provided by shadcn/ui:**

**Forms & Inputs:** button, input, textarea, checkbox, radio-group, select, switch, slider, calendar, input-otp, form

**Navigation:** navigation-menu, menubar, breadcrumb, pagination, sidebar, tabs

**Feedback:** alert, alert-dialog, dialog, drawer, sheet, toast (sonner), progress, skeleton

**Data Display:** card, table, badge, avatar, separator, aspect-ratio, accordion, collapsible

**Overlays:** popover, tooltip, dropdown-menu, context-menu, hover-card, command

**Layout:** scroll-area, resizable, carousel

**Customization Needs:**
- Email preview card (custom component)
- Folder category card with drag-drop (custom component)
- OAuth connection status indicator (custom component)
- Telegram linking code display (custom component)

**For Telegram Bot Interface:**
- **Native Telegram Components:** Inline keyboards, Markdown formatting, message cards
- **No custom design system needed** - Telegram handles all UI rendering
- **Focus:** Content structure and button hierarchy within Telegram's constraints

---

## 2. Core User Experience

### 2.1 Defining Experience

**Core User Statement:** "AI proposes, I approve in one tap"

**Full Description:** "My AI reads all my emails and sends me quick decisions to approve in Telegram - I tap approve and it's done"

**The Defining Interaction:**

When someone asks "What's Mail Agent?", users will say: **"It's an AI that sorts my emails and drafts responses - I just approve them in Telegram in seconds"**

**Why This Experience Matters:**

This single interaction appears multiple times daily and delivers the core value proposition:
- **Time savings:** 20-60 min/day → 5 min/day
- **Success feeling:** Tap approve → Inbox conquered
- **Trust through control:** AI proposes, human decides
- **Mobile-first:** Works anywhere via Telegram

**Core Experience Flow:**

1. 📧 **AI analyzes** → Emails classified, responses drafted, context extracted via RAG
2. 📱 **Telegram notification** → "8 emails processed: 3 proposals need your review"
3. 🎴 **Proposal card** → Email preview + AI reasoning + Action buttons
4. ✅ **One tap approval** → [Approve] button → Done!
5. 🎉 **Instant feedback** → "✅ Email sorted to Government folder"

**Established UX Pattern:**

This is a **Review & Approve workflow** - users already understand this from:
- Banking apps (N26, Revolut): "Approve this payment?"
- Expense apps (Expensify): "Approve this expense?"
- Task managers: "Mark as done?"
- Social moderation: "Approve this post?"

**Standard Pattern Elements:**
- ✅ Card showing item to review
- ✅ Clear context and reasoning
- ✅ Binary or tri-state action (Approve/Reject/Edit)
- ✅ Instant feedback on action
- ✅ Progress through queue

**Mail Agent's Implementation:**
- **Telegram inline keyboard cards** (iOS-style native buttons)
- **Two interaction modes:**
  - **Sorting proposals:** [Approve] [Change Folder] [Reject]
  - **Response drafts:** [Send] [Edit] [Reject]
- **AI reasoning displayed** to build trust
- **Batch notifications** for normal emails, **immediate** for high-priority

### 2.2 Core Experience Principles

These principles guide every UX decision across Mail Agent:

#### **Speed: Instant (<1 second perceived)**

Users review 3-8 proposals per session. Each tap must feel instant or they'll lose the "efficiency" feeling.

**Implementation:**
- Optimistic UI updates (show ✅ immediately, sync in background)
- No loading spinners for approve/reject actions
- Batch operations complete in background
- Target: <500ms perceived latency for all user actions

**Inspiration:** N26 - every transaction confirmation is immediate

---

#### **Guidance: Contextual clarity without clutter**

Users need to understand *why* the AI made each decision (build trust), but don't need tutorials (interaction is self-explanatory).

**Implementation:**
- AI reasoning shown in every proposal: "Email from Finanzamt regarding tax documents"
- No onboarding tutorial for Telegram bot (cards are self-explanatory)
- Web UI has guided setup wizard (one-time, more complex OAuth flow)
- Inline help text where needed, tooltips for advanced features

**Inspiration:** iOS - clarity through simplicity, context where needed

---

#### **Flexibility: Simple default, power available**

95% accuracy means most proposals are correct (one-tap approve). 5% need editing or folder changes (power users get options).

**Implementation:**
- **Default path:** [Approve] is the primary action (largest, most prominent button)
- **Power options:** [Change Folder] [Edit] available but visually secondary
- **Advanced settings:** Web UI for notification timing, folder rules, sorting keywords
- **Progressive disclosure:** Advanced features don't clutter the simple path

**Principle:** Make the common case effortless, the edge case possible

---

#### **Feedback: Celebratory progress, subtle confirmations**

The "success" emotion needs reinforcement, but per-action feedback can't be overwhelming (3-8 actions per session).

**Implementation:**

**Per-action (Subtle):**
- "✅ Email sorted to Government"
- "📤 Response sent to client@example.com"
- Brief, confirmation-focused

**Session summary (Celebratory):**
- "🎉 3 emails sorted, 1 response sent, 4 auto-filed"
- "⚡ Saved 15 minutes today!"
- Progress and impact highlighted

**Progress indicators:**
- "Reviewing 3 of 8 emails" (builds momentum)
- Visual progress bar in batch notifications

**Inspiration:** N26 - real-time transaction confirmations + weekly summaries

---

## 3. Visual Foundation

### 3.1 Color System

**Selected Theme: Sophisticated Dark (Theme 4)**

**Decision Rationale:**
- ✅ **Evening-friendly:** Users review emails in the evening (batch notifications) - dark mode reduces eye strain
- ✅ **Premium feel:** Dark themes convey sophistication and modernity
- ✅ **Focus enhancement:** Dark background makes content pop, reduces distraction
- ✅ **Vibrant accents:** Blue/purple accents provide energy without overwhelming
- ✅ **Perfect for success emotion:** Dark mode with bright success indicators feels accomplishment-focused
- ✅ **N26 alignment:** Many fintech apps offer dark mode as premium experience
- ✅ **Mobile-first:** Telegram users often review in various lighting conditions

**Color Palette:**

**Primary Colors:**
- Primary: `#3b82f6` (Blue 500) - Main actions, key elements
- Primary Light: `#60a5fa` (Blue 400) - Hover states, highlights
- Secondary: `#8b5cf6` (Purple 500) - Accent elements
- Accent: `#06b6d4` (Cyan 500) - Special highlights

**Semantic Colors:**
- Success: `#34d399` (Green 400) - Email sorted, action completed
- Warning: `#fbbf24` (Amber 400) - Needs attention
- Error: `#f87171` (Red 400) - Failed actions
- Info: `#60a5fa` (Blue 400) - Informational messages

**Dark Mode Palette:**
- Background: `#0f172a` (Slate 900) - Main background
- Background Alt: `#1e293b` (Slate 800) - Cards, elevated surfaces
- Text Primary: `#f8fafc` (Slate 50) - Main text
- Text Secondary: `#cbd5e1` (Slate 300) - Secondary text, labels
- Border: `#334155` (Slate 700) - Dividers, borders

**Typography System:**

**Font Families:**
- **Headings:** System font stack (-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)
- **Body:** Same as headings (consistency, native feel)
- **Monospace:** 'Courier New', monospace (for email IDs, technical data)

**Type Scale:**
- H1: 2.5rem / 40px (bold) - Page titles
- H2: 2rem / 32px (bold) - Section headers
- H3: 1.5rem / 24px (semibold) - Subsection headers
- H4: 1.25rem / 20px (semibold) - Card titles
- Body: 1rem / 16px (normal) - Main content
- Small: 0.875rem / 14px (normal) - Secondary text
- Tiny: 0.75rem / 12px (normal) - Labels, captions

**Font Weights:**
- Normal: 400 (body text, descriptions)
- Medium: 500 (labels, emphasized text)
- Semibold: 600 (subheadings, button text)
- Bold: 700 (headings, important CTAs)

**Line Heights:**
- Tight: 1.25 (headings)
- Normal: 1.5 (body text)
- Relaxed: 1.75 (long-form content)

**Spacing & Layout Foundation:**

**Base Unit:** 4px (0.25rem) - All spacing follows 4px grid

**Spacing Scale:**
- xs: 4px (0.25rem)
- sm: 8px (0.5rem)
- md: 16px (1rem)
- lg: 24px (1.5rem)
- xl: 32px (2rem)
- 2xl: 48px (3rem)
- 3xl: 64px (4rem)

**Layout Grid:**
- **Web UI:** 12-column grid (shadcn/ui default)
- **Container widths:**
  - Mobile: 100% (< 640px)
  - Tablet: 640px (sm breakpoint)
  - Desktop: 1024px (lg breakpoint)
  - Wide: 1280px (xl breakpoint)

**Border Radius:**
- sm: 4px (small elements, badges)
- md: 8px (buttons, inputs)
- lg: 12px (cards)
- xl: 16px (modals, major containers)
- full: 9999px (pills, avatars)

**Shadows (for depth in dark mode):**
- sm: 0 1px 2px rgba(0,0,0,0.3)
- md: 0 4px 6px rgba(0,0,0,0.4)
- lg: 0 10px 15px rgba(0,0,0,0.5)
- xl: 0 20px 25px rgba(0,0,0,0.6)

**Interactive Visualizations:**

- Color Theme Explorer: [ux-color-themes.html](./ux-color-themes.html)
- **Selected:** Theme 4 - Sophisticated Dark

---

## 4. Design Direction

### 4.1 Chosen Design Approach

**Design Direction: Card-Based Dark Mode with Telegram Native Patterns**

**Core Layout Philosophy:**
- **Telegram Bot:** Native inline keyboard cards (iOS-style) - users already know this pattern
- **Web Configuration UI:** Clean, card-based layout with sidebar navigation (shadcn/ui patterns)

**Visual Hierarchy:**
- **Dense but scannable:** Show essential info compactly, hide details in accordions
- **Bold CTAs:** Primary action buttons (Approve, Send) are prominent and colorful
- **Subtle reasoning:** AI explanations visible but visually secondary

**Key Design Decisions:**

**For Telegram Proposal Cards:**
```
┌─────────────────────────────────┐
│ 📧 Email Proposal               │
│                                 │
│ From: sender@example.com        │
│ Subject: Tax documents needed   │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ AI Reasoning:               │ │
│ │ Email from Finanzamt        │ │
│ │ regarding tax documents     │ │
│ └─────────────────────────────┘ │
│                                 │
│ Suggested: Government folder   │
│                                 │
│ [✓ Approve] [📁 Change] [✕ Reject]
└─────────────────────────────────┘
```

**For Web Configuration UI:**
- Sidebar navigation (Settings, Folders, OAuth connections)
- Main content area with cards for each configuration section
- Wizard-style onboarding with progress indicators
- Dark background (#0f172a) with elevated cards (#1e293b)

---

## 5. User Journey Flows

### 5.1 Critical User Paths

**Journey 1: Initial Setup and Onboarding (Web UI)**

**Goal:** Connect Gmail + Telegram, configure folders in <10 minutes

**Flow:**
1. **Landing Page** → [Get Started] button
2. **Step 1: Connect Gmail**
   - OAuth explanation
   - [Connect Gmail] → Google consent screen
   - Return with success confirmation ✓
3. **Step 2: Link Telegram**
   - Instructions to open Telegram bot
   - Display 6-digit linking code (large, copyable)
   - Wait for bot confirmation
   - Success ✓
4. **Step 3: Configure Folders**
   - Default folders suggested (Government, Clients, Newsletters)
   - [+ Add Folder] with name + keywords
   - Optional: Basic sorting rules
5. **Step 4: Test & Complete**
   - Send test Telegram message
   - Confirm receipt
   - [Start Processing] → Dashboard

**UX Patterns:**
- Progress bar at top (1/4 → 2/4 → 3/4 → 4/4)
- Can't skip steps (linear wizard)
- Each step has clear success indicator
- [Back] and [Continue] buttons always visible

---

**Journey 2: Daily Email Review (Telegram Bot)**

**Goal:** Review 3-8 proposals in 5 minutes, feel accomplished

**Flow:**
1. **Batch Notification** (evening, 18:00)
   - "📬 8 emails processed: 3 need your review"
2. **Proposal Card 1** (Sorting)
   - Email preview + AI reasoning
   - [✓ Approve] → Instant feedback "✅ Sorted to Government"
3. **Proposal Card 2** (Response Draft)
   - Email preview + drafted response
   - [📤 Send] → Instant feedback "✅ Response sent"
4. **Proposal Card 3** (Sorting with edit)
   - User taps [📁 Change Folder]
   - Inline folder picker appears
   - Select "Clients" → "✅ Sorted to Clients"
5. **Completion Summary**
   - "🎉 3 emails sorted, 1 response sent, 4 auto-filed"
   - "⚡ Saved 15 minutes today!"

**UX Patterns:**
- Optimistic UI (instant feedback, sync in background)
- Progress indicator "Reviewing 2 of 3"
- Undo available for 5 seconds after action
- Celebratory summary at end

---

**Journey 3: High-Priority Government Email (Telegram Bot)**

**Goal:** Handle critical email immediately with full context

**Flow:**
1. **Immediate Notification** (not batched)
   - "⚠️ Important: Government email requires response"
2. **Detailed Proposal Card**
   - Full context summary (RAG retrieved)
   - Drafted formal German response
   - Shows conversation history (collapsed, expandable)
3. **User Reviews**
   - Expands conversation history (taps to view)
   - Sees AI understood entire case
   - Makes minor date edit
4. **Send with Confidence**
   - [📤 Send Modified] → "✅ Response sent to Ausländerbehörde"
   - Time saved: 13 minutes (vs. manual review)

**UX Patterns:**
- High-priority visual indicator (⚠️ icon, different color)
- Expandable context sections (progressive disclosure)
- Inline editing for quick tweaks
- Confidence-building confirmations

---

## 6. Component Library

### 6.1 Component Strategy

**From shadcn/ui (Web UI):**

**Forms:** button, input, textarea, select, checkbox, switch, form
**Navigation:** sidebar (new in shadcn/ui), tabs, breadcrumb
**Feedback:** alert, dialog, toast (sonner), progress, skeleton
**Data Display:** card, table, badge, avatar, accordion
**Overlays:** popover, tooltip, dropdown-menu

**Custom Components Needed (Web UI):**

1. **EmailPreviewCard** - Shows email metadata for testing
   - Props: sender, subject, snippet, timestamp
   - States: default, loading
   - Styling: Dark card with border, subtle shadow

2. **FolderCategoryCard** - Manages folder configuration
   - Props: name, keywords[], color, isDefault
   - Actions: edit, delete, set as default
   - Features: Drag-to-reorder, inline keyword editing

3. **OAuthStatusIndicator** - Shows connection status
   - States: connected, disconnected, error, refreshing
   - Visual: Green checkmark / Red X / Loading spinner
   - Actions: [Reconnect] button if disconnected

4. **TelegramLinkingCodeDisplay** - Shows 6-digit code
   - Large, monospace font (code readability)
   - Copy button with instant feedback
   - Auto-refresh after 10 minutes (expiry)

**For Telegram Bot Interface:**

All components are **native Telegram elements** (no custom components needed):

1. **Inline Keyboards** - Button arrays
   - 1-3 buttons per row
   - Max 3 rows for readability
   - Callback data format: `{action}_{email_id}`

2. **Message Cards** - Formatted text with Markdown
   - **Bold** for headers
   - `Code` for email addresses
   - _Italic_ for AI reasoning
   - Line breaks for structure

3. **Progress Indicators** - Text-based
   - "Reviewing 2 of 3 emails"
   - Percentage or fraction format

---

## 7. UX Pattern Decisions

### 7.1 Consistency Rules

**Button Hierarchy:**
- **Primary:** Blue background (#3b82f6), white text, semibold - main actions (Approve, Send, Connect)
- **Secondary:** Dark background (#1e293b), blue border/text, semibold - alternative actions (Edit, Change Folder)
- **Tertiary:** Minimal styling, gray text (#cbd5e1) - less important actions (Reject, Cancel)
- **Destructive:** Red background (#f87171), white text - delete/permanent actions

**Feedback Patterns:**
- **Success:** Green left border (#34d399) + icon ✓ + message - toast auto-dismiss 3s
- **Error:** Red left border (#f87171) + icon ✕ + message + [Retry] - stays until dismissed
- **Warning:** Amber left border (#fbbf24) + icon ⚠ + message - stays until dismissed
- **Info:** Blue left border (#60a5fa) + icon ⓘ + message - auto-dismiss 5s
- **Loading:** Skeleton screens (no spinners) for content, small spinner for actions

**Form Patterns:**
- **Label position:** Above input (stacked, mobile-friendly)
- **Required fields:** Asterisk (*) in label
- **Validation timing:** onBlur (not onChange - too aggressive)
- **Error display:** Below input, red text (#f87171), icon ✕
- **Help text:** Below label, small gray text (#cbd5e1), icon ⓘ on hover for tooltips

**Modal Patterns:**
- **Sizes:** sm (400px), md (600px), lg (800px)
- **Dismiss:** Click outside OR Escape key OR explicit [X] button
- **Focus:** Auto-focus first input or primary action
- **Backdrop:** Semi-transparent black (rgba(0,0,0,0.8))

**Navigation Patterns:**
- **Active state:** Sidebar item with blue left border + blue text
- **Breadcrumbs:** Only for deep navigation (>2 levels)
- **Back button:** Browser back in web, Telegram handles in bot
- **Deep linking:** All settings pages support direct URLs

**Empty State Patterns:**
- **First use:** Large icon + friendly message + primary CTA ("No folders yet. Add your first folder!")
- **No results:** Helpful suggestion + alternative action ("No emails match. Try adjusting filters.")
- **Cleared/Deleted:** Confirmation + undo option (5s) + neutral CTA

**Confirmation Patterns:**
- **Delete folder:** Modal confirmation with folder name highlighted
- **Disconnect OAuth:** Alert dialog explaining consequences + [Confirm] button
- **Leave unsaved:** Alert on navigation attempt, offer [Save Draft] [Discard] [Cancel]

**Notification Patterns (Telegram Bot):**
- **Placement:** Telegram controls (system notifications)
- **Batching:** Normal emails batched at configured time (default 18:00)
- **Immediate:** High-priority emails sent instantly
- **Quiet hours:** Respect user's quiet hours setting (default 22:00-08:00)

---

## 8. Responsive Design & Accessibility

### 8.1 Responsive Strategy

**Target Devices:**
- **Primary:** Mobile (Telegram bot on iOS/Android)
- **Secondary:** Desktop (Web configuration UI)
- **Tertiary:** Tablet (Web UI, responsive layout)

**Breakpoints:**
- **Mobile:** < 640px - Single column, bottom nav if needed, touch-optimized
- **Tablet:** 640px - 1024px - Adapt to 2-column where appropriate
- **Desktop:** 1024px+ - Sidebar navigation, multi-column layouts

**Responsive Adaptation:**

**Web Configuration UI:**
- **Mobile:** Hamburger menu → slide-out sidebar, single column forms, full-width cards
- **Tablet:** Persistent sidebar (collapsible), 2-column grids for folder cards
- **Desktop:** Full sidebar always visible, 3-column grids, wider modals

**Telegram Bot Interface:**
- No responsive design needed (Telegram handles native rendering)
- Always mobile-optimized by default

**Touch Targets:**
- Minimum 44x44px for all interactive elements (iOS HIG standard)
- Spacing between buttons: minimum 8px
- Telegram inline keyboard buttons: automatically sized by Telegram

---

### 8.2 Accessibility Strategy

**Compliance Target: WCAG 2.1 Level AA**

**Rationale:**
- Not legally required (private productivity tool)
- Level AA is industry best practice
- shadcn/ui provides AA compliance out-of-box
- Minimal additional effort for significant usability gains

**Key Requirements:**

**Color Contrast:**
- Text vs background: 4.5:1 minimum (body text)
- Large text vs background: 3:1 minimum (18px+ or 14px+ bold)
- Dark theme colors chosen to meet contrast ratios
- Test with WebAIM Contrast Checker

**Keyboard Navigation:**
- All interactive elements accessible via Tab
- Logical tab order (top-to-bottom, left-to-right)
- Visible focus indicators (2px blue outline #3b82f6)
- Escape key closes modals/dropdowns
- Enter key activates buttons

**Screen Reader Support:**
- ARIA labels on all icon-only buttons
- Form labels properly associated with inputs
- Error messages announced via aria-live
- Loading states communicated ("Loading..." text for screen readers)
- shadcn/ui components have ARIA built-in (Radix UI primitives)

**Visual Accessibility:**
- Never rely on color alone (use icons + text)
- Error states: red color + X icon + text message
- Success states: green color + ✓ icon + text message
- Alt text for any images (none in core UI except logos)

**Touch Target Sizes:**
- Minimum 44x44px (exceeds WCAG 2.5.5 requirement of 24x24px)
- Adequate spacing prevents mis-taps

**Testing Strategy:**
- **Automated:** Lighthouse accessibility audit (target 95+ score)
- **Manual:** Keyboard-only navigation testing
- **Screen reader:** VoiceOver (macOS/iOS) spot-checking on key flows

---

## 9. Implementation Guidance

### 9.1 Completion Summary

**✅ UX Design Specification Complete!**

**What We've Created:**

1. **Design System Foundation**
   - shadcn/ui with Next.js 15 + Tailwind CSS v4
   - Telegram native inline keyboards for bot interface
   - 50+ accessible components ready to use

2. **Visual Foundation**
   - Sophisticated Dark color theme (evening-friendly, premium feel)
   - Complete color palette with semantic meanings
   - Typography system with native font stack
   - 4px grid-based spacing system

3. **Core Experience Definition**
   - "AI proposes, I approve in one tap"
   - Review & Approve workflow pattern
   - SUCCESS emotional goal with instant feedback

4. **Experience Principles**
   - Speed: Instant (<500ms perceived)
   - Guidance: Contextual clarity without clutter
   - Flexibility: Simple default, power available
   - Feedback: Celebratory progress, subtle confirmations

5. **User Journey Flows**
   - 10-minute onboarding wizard (Web UI)
   - 5-minute daily email review (Telegram bot)
   - Immediate high-priority email handling

6. **Component Strategy**
   - shadcn/ui components for Web UI
   - 4 custom components identified
   - Native Telegram components for bot

7. **UX Pattern Consistency**
   - Button hierarchy defined
   - Feedback patterns standardized
   - Form, modal, navigation patterns established
   - Empty states and confirmations specified

8. **Responsive & Accessibility**
   - Mobile-first approach (Telegram primary)
   - WCAG 2.1 Level AA compliance
   - Keyboard navigation and screen reader support

---

### 9.2 Key Deliverables

**Completed:**
- ✅ UX Design Specification (this document)
- ✅ Interactive Color Theme Visualizer ([ux-color-themes.html](./ux-color-themes.html))

**Ready for Next Phase:**
- Implementation can begin immediately using this specification
- Developers have clear UX guidance and rationale
- All design decisions documented with reasoning

---

### 9.3 Implementation Priorities

**Phase 1: Web Configuration UI (Epic 4 from PRD)**

Using shadcn/ui components + Sophisticated Dark theme:
1. Onboarding wizard (4 steps)
2. Dashboard with connection status
3. Folder management interface
4. Settings page

**Phase 2: Telegram Bot Interface (Epic 2 from PRD)**

Using native Telegram inline keyboards:
1. Proposal card formatting (Markdown)
2. Inline keyboard button layout
3. Batch vs immediate notification logic
4. Feedback messages (success/error)

**Phase 3: Refinement**

Based on user testing:
1. Adjust color contrast if needed
2. Optimize button sizing for real usage
3. Refine AI reasoning presentation
4. Polish micro-interactions

---

### 9.4 Design Handoff Notes for Developers

**For Web UI Implementation:**

```bash
# Install shadcn/ui in Next.js 15 project
npx shadcn@latest init

# Add required components
npx shadcn@latest add button card input dialog sidebar toast

# Configure dark mode in tailwind.config
# Use color tokens from this specification
```

**Color Tokens (Tailwind CSS v4):**
```css
:root {
  --background: 15 23 42;        /* #0f172a */
  --background-alt: 30 41 59;    /* #1e293b */
  --primary: 59 130 246;         /* #3b82f6 */
  --success: 52 211 153;         /* #34d399 */
  --error: 248 113 113;          /* #f87171 */
  /* ... see section 3.1 for full palette */
}
```

**For Telegram Bot Implementation:**

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Proposal card template
message_text = f"""
📧 **Email Proposal**

From: {sender}
Subject: {subject}

**AI Reasoning:**
_{reasoning}_

**Suggested Folder:** {folder}
"""

buttons = [
    [InlineKeyboardButton("✓ Approve", callback_data=f"approve_{email_id}")],
    [InlineKeyboardButton("📁 Change Folder", callback_data=f"change_{email_id}"),
     InlineKeyboardButton("✕ Reject", callback_data=f"reject_{email_id}")]
]

keyboard = InlineKeyboardMarkup(buttons)
```

---

### 9.5 Success Metrics

**UX Goals to Measure:**

1. **Onboarding Completion:** 90%+ of users complete setup in <10 minutes
2. **Daily Usage Time:** Average 5 minutes per session (down from 20-60 min baseline)
3. **Approval Rate:** 95%+ proposals approved without modification (validates AI accuracy)
4. **User Sentiment:** "SUCCESS" emotion validated through user interviews
5. **Accessibility:** Lighthouse accessibility score 95+

**Analytics to Track:**

- Time to complete onboarding (per step)
- Proposals shown vs approved vs rejected vs edited
- Average session time in Telegram bot
- High-priority email response time
- Feature usage (folder management, notification settings)

---

## Appendix

### Related Documents

- Product Requirements: `docs/PRD.md`
- Architecture: `docs/architecture.md`
- Product Brief: `docs/product-brief-Mail Agent-2025-11-03.md`

### Core Interactive Deliverables

This UX Design Specification was created through visual collaboration:

- **Color Theme Visualizer**: {{color_themes_html}}
  - Interactive HTML showing all color theme options explored
  - Live UI component examples in each theme
  - Side-by-side comparison and semantic color usage

- **Design Direction Mockups**: {{design_directions_html}}
  - Interactive HTML with 6-8 complete design approaches
  - Full-screen mockups of key screens
  - Design philosophy and rationale for each direction

### Optional Enhancement Deliverables

_This section will be populated if additional UX artifacts are generated through follow-up workflows._

<!-- Additional deliverables added here by other workflows -->

### Next Steps & Follow-Up Workflows

This UX Design Specification can serve as input to:

- **Wireframe Generation Workflow** - Create detailed wireframes from user flows
- **Figma Design Workflow** - Generate Figma files via MCP integration
- **Interactive Prototype Workflow** - Build clickable HTML prototypes
- **Component Showcase Workflow** - Create interactive component library
- **AI Frontend Prompt Workflow** - Generate prompts for v0, Lovable, Bolt, etc.
- **Solution Architecture Workflow** - Define technical architecture with UX context

### Version History

| Date     | Version | Changes                         | Author        |
| -------- | ------- | ------------------------------- | ------------- |
| 2025-11-03 | 1.0     | Initial UX Design Specification | Dimcheg |

---

_This UX Design Specification was created through collaborative design facilitation, not template generation. All decisions were made with user input and are documented with rationale._
