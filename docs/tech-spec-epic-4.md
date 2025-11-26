# Epic Technical Specification: Configuration UI & Onboarding

Date: 2025-11-11
Author: Dimcheg
Epic ID: 4
Status: In Progress

## Implementation Status

**Last Updated:** 2025-11-11

| Story | Status | Completion Date | Notes |
|-------|--------|-----------------|-------|
| Story 4.1: Frontend Project Setup | ✅ Complete | 2025-11-11 | Next.js 16.0.1 + React 19.2.0 project with TypeScript strict mode, Tailwind CSS v4, shadcn/ui, Axios 1.7.9 API client with token refresh, comprehensive test suite (17/17 tests passing), 0 vulnerabilities |
| Story 4.2: Gmail OAuth Connection | 📋 Pending | - | - |
| Story 4.3: Telegram Bot Linking | 📋 Pending | - | - |
| Story 4.4: Folder Configuration | 📋 Pending | - | - |
| Story 4.5: Notification Settings | 📋 Pending | - | - |
| Story 4.6: Onboarding Wizard | 📋 Pending | - | - |
| Story 4.7: Dashboard Overview | 📋 Pending | - | - |
| Story 4.8: Epic 4 Testing | 📋 Pending | - | - |

## Technology Version Decisions

**Version Variance from Original Specification:**

During Story 4.1 implementation, the following technology versions were selected, which differ from the original technical specification:

| Technology | Original Spec | Implemented | Rationale | Status |
|-----------|---------------|-------------|-----------|--------|
| **Next.js** | 15.5 | 16.0.1 | Latest stable version with improved App Router performance, React 19 support, and security patches. Next.js 16 is production-ready and backward compatible with 15.x patterns. | ✅ Approved |
| **React** | 18.x | 19.2.0 | Latest stable with improved hooks, concurrent rendering, and compiler optimizations. Required for Next.js 16 compatibility. All shadcn/ui components tested and compatible. | ✅ Approved |
| **Axios** | 1.7.0+ | 1.7.9 | Latest stable in 1.7.x branch with security patches and bug fixes. | ✅ Approved |

**Impact Assessment:**
- ✅ **Positive**: Access to latest security patches, performance improvements, and React 19 compiler optimizations
- ✅ **Positive**: Better TypeScript support in React 19 with improved type inference
- ⚠️ **Consideration**: React 19 has breaking changes from 18.x (primarily in Suspense behavior), but shadcn/ui components are fully compatible
- ⚠️ **Consideration**: Third-party libraries may not yet support React 19 (monitored during testing - no issues found)

**Testing Status**: All 17 tests passing (5 test files, 100% pass rate). No compatibility issues detected with Next.js 16 + React 19 combination.

**Recommendation**: Continue with Next.js 16.0.1 and React 19.2.0 for Epic 4. Monitor third-party library compatibility in subsequent stories. Fallback plan: Downgrade to Next.js 15.5 + React 18.x if blocking issues arise.

---

## Overview

Epic 4 implements the user-facing configuration web application for Mail Agent, delivering the final piece required for end-to-end system usability. This epic introduces a modern Next.js 15 frontend with TypeScript, shadcn/ui component library, and Tailwind CSS v4 for a professional dark-themed interface. The implementation focuses on guided onboarding (Gmail OAuth connection, Telegram bot linking, folder category configuration) and ongoing settings management (notification preferences, folder rules, connection status monitoring). By completing this epic, non-technical users can complete full system setup in under 10 minutes through a wizard-style interface, achieve 90%+ onboarding completion rate, and manage their email automation settings without technical knowledge—delivering on NFR005 usability goals and enabling the complete Mail Agent value proposition of "AI proposes, I approve in one tap" through seamless Telegram integration.

## Objectives and Scope

**In Scope:**
- Next.js 15 project initialization with App Router, TypeScript, and Tailwind CSS v4
- shadcn/ui component library integration with dark mode theming
- Gmail OAuth 2.0 connection flow with clear permission explanations
- Telegram bot linking page with 6-digit code display and connection verification
- Folder categories configuration interface with drag-drop, keywords, and color customization
- Notification preferences settings (batch timing, quiet hours, priority thresholds)
- 4-step guided onboarding wizard with progress indicators and validation
- Dashboard overview page showing connection status, processing statistics, and system health
- Responsive design (mobile, tablet, desktop) with WCAG 2.1 Level AA accessibility
- Integration testing across entire onboarding flow
- Dark mode UI following UX specification (Sophisticated Dark theme)
- API client layer for backend FastAPI integration
- Error handling and user feedback (toasts, alerts, validation messages)

**Out of Scope:**
- Email browsing/search interface - deferred to post-MVP (users interact via Gmail directly)
- Analytics dashboard with charts/graphs - deferred to post-MVP
- Multi-user/team features - MVP targets single-user accounts
- Mobile native apps (iOS/Android) - web UI is mobile-responsive for setup only
- Advanced folder rule builder (complex if/then logic) - MVP uses simple keyword matching
- Telegram bot configuration within web UI - bot commands handle settings
- Real-time email preview in UI - not needed (Telegram is primary interface)
- User profile management (avatar, bio, etc.) - minimal MVP user model
- Dark/light mode toggle - dark mode only for MVP (evening-optimized per UX spec)
- Localization/i18n - English only for MVP (multilingual emails handled by AI, not UI)

## System Architecture Alignment

This epic implements the frontend layer of the Mail Agent architecture as defined in `architecture.md`, completing the user-facing components that enable system configuration and monitoring. Key alignment points:

**Next.js 15 Frontend Architecture:**
- **Framework:** Next.js 15.5 with App Router (server-side rendering, React Server Components)
- **Language:** TypeScript 5.x for type safety across all components
- **Styling:** Tailwind CSS v4 with custom design tokens from UX specification
- **Component Library:** shadcn/ui (Radix UI primitives) for WCAG 2.1 AA compliance
- **State Management:** React hooks (useState, useContext) + SWR for API data caching
- **API Layer:** Axios-based client with interceptors for auth/error handling
- **Deployment:** Vercel (zero-cost for MVP, optimal Next.js hosting)

**Backend Integration Points:**
Epic 4 consumes the FastAPI backend (Epics 1-3) via RESTful JSON APIs:

| Frontend Feature | Backend API Endpoint | Epic Dependency |
|-----------------|----------------------|-----------------|
| Gmail OAuth Flow | `POST /api/v1/auth/gmail/callback` | Epic 1 |
| OAuth Connection Status | `GET /api/v1/auth/status` | Epic 1 |
| Telegram Bot Linking | `POST /api/v1/telegram/link` | Epic 2 |
| Telegram Link Verification | `GET /api/v1/telegram/verify/{code}` | Epic 2 |
| Folder CRUD | `GET/POST/PUT/DELETE /api/v1/folders` | Epic 1 |
| Notification Preferences | `GET/PUT /api/v1/settings/notifications` | Epic 2 |
| Dashboard Statistics | `GET /api/v1/dashboard/stats` | Epics 1-3 |
| User Profile | `GET/PUT /api/v1/users/me` | Epic 1 |

**JWT Authentication Flow:**
- Backend issues JWT access token after Gmail OAuth success (Epic 1)
- Frontend stores JWT in httpOnly cookie (XSS protection)
- All API requests include JWT in Authorization header
- Token refresh handled automatically via axios interceptor
- 7-day token expiration with sliding refresh window

**Project Structure Alignment:**
```
frontend/                           # Next.js 15 App (Epic 4)
├── src/
│   ├── app/                        # App Router pages
│   │   ├── layout.tsx              # Root layout with dark theme
│   │   ├── page.tsx                # Landing page
│   │   ├── onboarding/             # 4-step wizard (Story 4.6)
│   │   │   ├── page.tsx            # Wizard container
│   │   │   ├── gmail/page.tsx      # Step 1: Gmail OAuth (Story 4.2)
│   │   │   ├── telegram/page.tsx   # Step 2: Telegram (Story 4.3)
│   │   │   ├── folders/page.tsx    # Step 3: Folders (Story 4.4)
│   │   │   └── complete/page.tsx   # Step 4: Complete
│   │   ├── dashboard/page.tsx      # Dashboard (Story 4.7)
│   │   └── settings/
│   │       ├── folders/page.tsx    # Folder management (Story 4.4)
│   │       └── notifications/page.tsx  # Notification prefs (Story 4.5)
│   │
│   ├── components/                 # React components
│   │   ├── ui/                     # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ... (50+ components)
│   │   │
│   │   ├── onboarding/             # Onboarding-specific
│   │   │   ├── WizardProgress.tsx
│   │   │   ├── GmailConnect.tsx
│   │   │   ├── TelegramLinking.tsx
│   │   │   └── FolderSetup.tsx
│   │   │
│   │   ├── dashboard/              # Dashboard components
│   │   │   ├── ConnectionStatus.tsx
│   │   │   ├── StatsCard.tsx
│   │   │   └── RecentActivity.tsx
│   │   │
│   │   └── shared/                 # Shared components
│   │       ├── Navbar.tsx
│   │       ├── Sidebar.tsx
│   │       └── ErrorBoundary.tsx
│   │
│   ├── lib/                        # Utilities
│   │   ├── api-client.ts           # Backend API wrapper
│   │   ├── auth.ts                 # Auth helpers
│   │   └── utils.ts                # General utilities
│   │
│   └── types/                      # TypeScript types
│       ├── api.ts                  # API response types
│       ├── folder.ts               # Folder models
│       └── user.ts                 # User models
│
├── public/                         # Static assets
│   ├── logo.svg
│   └── favicon.ico
│
├── package.json                    # Dependencies
├── tailwind.config.ts              # Tailwind + design tokens
├── tsconfig.json                   # TypeScript config
└── next.config.js                  # Next.js config
```

**Design System Integration:**
- **Color Tokens:** Imported from UX spec (Sophisticated Dark theme)
  - Primary: `#3b82f6` (Blue 500)
  - Background: `#0f172a` (Slate 900)
  - Success: `#34d399` (Green 400)
  - Error: `#f87171` (Red 400)
- **Typography:** System font stack for native feel
- **Spacing:** 4px grid system (Tailwind spacing scale)
- **Components:** shadcn/ui provides 50+ accessible components (button, card, dialog, toast, etc.)

**Responsive Breakpoints:**
- Mobile: < 640px (single column, touch-optimized)
- Tablet: 640px - 1024px (2-column grids)
- Desktop: 1024px+ (sidebar navigation, 3-column grids)

**NFR Alignment:**
- **NFR005 (Usability):** 10-minute onboarding wizard with 90%+ completion rate target
- **NFR004 (Security):** httpOnly cookies for JWT, HTTPS-only, CSRF protection via SameSite cookies
- **NFR002 (Reliability):** Error boundaries, offline detection, retry logic for failed API calls
- **NFR001 (Performance):** SWR for API caching, React Server Components for reduced JavaScript, optimistic UI updates

**Epic Dependencies:**
Epic 4 is the final epic and depends on all previous epics for backend APIs:
- **Epic 1:** Gmail OAuth endpoints, folder management API, user model
- **Epic 2:** Telegram linking API, notification preferences API
- **Epic 3:** Dashboard statistics API (email counts, response metrics)

## Detailed Design

### Services and Modules

| Module/Component | Responsibility | Inputs | Outputs | Location |
|-----------------|----------------|--------|---------|----------|
| **ApiClient** | Backend API communication with auth, retries, error handling | API requests (method, endpoint, data) | Typed responses or errors | `src/lib/api-client.ts` |
| **AuthService** | JWT management, OAuth flow coordination, session handling | User credentials, OAuth callbacks | Auth state, JWT tokens | `src/lib/auth.ts` |
| **GmailConnectComponent** | Gmail OAuth initiation and callback handling | OAuth config from backend | Connection status, error messages | `src/components/onboarding/GmailConnect.tsx` |
| **TelegramLinkingComponent** | Display linking code, poll verification status | Backend-generated 6-digit code | Link success/failure status | `src/components/onboarding/TelegramLinking.tsx` |
| **FolderManagementComponent** | CRUD operations for folder categories with drag-drop | User folder configurations | Updated folder list | `src/components/onboarding/FolderSetup.tsx`, `src/app/settings/folders/page.tsx` |
| **NotificationPrefsComponent** | Edit notification timing, quiet hours, batch settings | User preferences | Updated preferences | `src/app/settings/notifications/page.tsx` |
| **OnboardingWizard** | Multi-step wizard orchestration with progress tracking | Step navigation events | Wizard completion state | `src/app/onboarding/page.tsx` |
| **DashboardStats** | Display connection status, email counts, system health | Backend statistics API | Rendered stat cards | `src/app/dashboard/page.tsx` |
| **ErrorBoundary** | Catch React errors, display fallback UI, log to backend | Component errors | Error UI with retry | `src/components/shared/ErrorBoundary.tsx` |
| **ToastNotification** | User feedback for actions (success, error, info) | Toast messages | Rendered toasts (sonner) | Via shadcn/ui toast |

### Data Models and Contracts

#### TypeScript Type Definitions

**User Model (`src/types/user.ts`):**

```typescript
export interface User {
  id: number;
  email: string;
  gmail_connected: boolean;
  telegram_connected: boolean;
  telegram_id?: string;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
}
```

**Folder Category Model (`src/types/folder.ts`):**

```typescript
export interface FolderCategory {
  id: number;
  user_id: number;
  name: string;
  gmail_label_id: string;
  keywords: string[];
  color: string;  // Hex color code
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateFolderRequest {
  name: string;
  keywords?: string[];
  color?: string;
}

export interface UpdateFolderRequest {
  name?: string;
  keywords?: string[];
  color?: string;
  is_default?: boolean;
}
```

**Notification Preferences Model (`src/types/settings.ts`):**

```typescript
export interface NotificationPreferences {
  id: number;
  user_id: number;
  batch_enabled: boolean;
  batch_time: string;  // HH:MM format (e.g., "18:00")
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;  // HH:MM format
  quiet_hours_end: string;    // HH:MM format
  priority_immediate: boolean;
  min_confidence_threshold: number;  // 0.0 - 1.0
  created_at: string;
  updated_at: string;
}

export interface UpdateNotificationPrefsRequest {
  batch_enabled?: boolean;
  batch_time?: string;
  quiet_hours_enabled?: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  priority_immediate?: boolean;
  min_confidence_threshold?: number;
}
```

**Dashboard Statistics Model (`src/types/dashboard.ts`):**

```typescript
export interface DashboardStats {
  connections: {
    gmail: ConnectionStatus;
    telegram: ConnectionStatus;
  };
  email_stats: {
    total_processed: number;
    pending_approval: number;
    auto_sorted: number;
    responses_sent: number;
  };
  time_saved: {
    today_minutes: number;
    total_minutes: number;
  };
  recent_activity: ActivityItem[];
}

export interface ConnectionStatus {
  connected: boolean;
  last_sync?: string;
  error?: string;
}

export interface ActivityItem {
  id: number;
  type: 'sorted' | 'response_sent' | 'rejected';
  email_subject: string;
  timestamp: string;
  folder_name?: string;
}
```

**API Response Wrappers (`src/types/api.ts`):**

```typescript
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface ApiError {
  message: string;
  details?: Record<string, string[]>;
  status: number;
  code?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
```

**OAuth Flow Models (`src/types/auth.ts`):**

```typescript
export interface GmailOAuthConfig {
  auth_url: string;
  client_id: string;
  scopes: string[];
}

export interface OAuthCallbackParams {
  code: string;
  state: string;
  scope: string;
}

export interface TelegramLinkingCode {
  code: string;
  expires_at: string;
  verified: boolean;
}

export interface TelegramVerificationStatus {
  verified: boolean;
  telegram_id?: string;
  telegram_username?: string;
}
```

#### Frontend-Backend API Contract

All API responses follow this structure:

**Success Response:**
```json
{
  "data": { /* resource data */ },
  "message": "Optional success message",
  "status": 200
}
```

**Error Response:**
```json
{
  "message": "Error description",
  "details": {
    "field_name": ["Validation error 1", "Validation error 2"]
  },
  "status": 400,
  "code": "VALIDATION_ERROR"
}
```

**Authentication:**
- JWT token in `Authorization: Bearer <token>` header
- Token stored in httpOnly cookie for security
- 401 response triggers automatic token refresh
- 403 response redirects to login

### APIs and Interfaces

#### Backend API Endpoints (Consumed by Epic 4 Frontend)

**Authentication Endpoints:**

```typescript
// GET /api/v1/auth/gmail/config
// Returns Gmail OAuth configuration
Response: GmailOAuthConfig

// POST /api/v1/auth/gmail/callback
// Handle Gmail OAuth callback with authorization code
Request: { code: string, state: string }
Response: { user: User, token: string }

// GET /api/v1/auth/status
// Get current authentication status
Response: { authenticated: boolean, user?: User }

// POST /api/v1/auth/logout
// Logout user and invalidate token
Response: { message: string }
```

**Telegram Linking Endpoints:**

```typescript
// POST /api/v1/telegram/link
// Generate new linking code
Response: TelegramLinkingCode

// GET /api/v1/telegram/verify/{code}
// Check if linking code has been verified
Response: TelegramVerificationStatus

// DELETE /api/v1/telegram/unlink
// Disconnect Telegram account
Response: { message: string }
```

**Folder Management Endpoints:**

```typescript
// GET /api/v1/folders
// List all folder categories for current user
Response: FolderCategory[]

// POST /api/v1/folders
// Create new folder category
Request: CreateFolderRequest
Response: FolderCategory

// PUT /api/v1/folders/{id}
// Update existing folder category
Request: UpdateFolderRequest
Response: FolderCategory

// DELETE /api/v1/folders/{id}
// Delete folder category (also removes Gmail label)
Response: { message: string }

// POST /api/v1/folders/reorder
// Update folder display order
Request: { folder_ids: number[] }
Response: { message: string }
```

**Notification Preferences Endpoints:**

```typescript
// GET /api/v1/settings/notifications
// Get user notification preferences
Response: NotificationPreferences

// PUT /api/v1/settings/notifications
// Update notification preferences
Request: UpdateNotificationPrefsRequest
Response: NotificationPreferences

// POST /api/v1/settings/notifications/test
// Send test notification to Telegram
Response: { message: string, success: boolean }
```

**Dashboard Endpoints:**

```typescript
// GET /api/v1/dashboard/stats
// Get dashboard statistics
Response: DashboardStats

// GET /api/v1/dashboard/activity?limit=10
// Get recent activity items
Query: { limit?: number }
Response: ActivityItem[]
```

**User Profile Endpoints:**

```typescript
// GET /api/v1/users/me
// Get current user profile
Response: User

// PUT /api/v1/users/me
// Update user profile
Request: { email?: string }
Response: User
```

#### ApiClient Implementation (`src/lib/api-client.ts`)

```typescript
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      timeout: 30000,
      withCredentials: true, // Send cookies
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor: Add JWT token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor: Handle errors, refresh token
    this.client.interceptors.response.use(
      (response) => response.data,
      async (error) => {
        if (error.response?.status === 401) {
          // Token expired, attempt refresh
          await this.refreshToken();
          return this.client.request(error.config);
        }
        return Promise.reject(this.formatError(error));
      }
    );
  }

  // Auth methods
  async gmailOAuthConfig() {
    return this.client.get<GmailOAuthConfig>('/api/v1/auth/gmail/config');
  }

  async gmailCallback(code: string, state: string) {
    return this.client.post('/api/v1/auth/gmail/callback', { code, state });
  }

  // Telegram methods
  async generateTelegramLink() {
    return this.client.post<TelegramLinkingCode>('/api/v1/telegram/link');
  }

  async verifyTelegramLink(code: string) {
    return this.client.get<TelegramVerificationStatus>(`/api/v1/telegram/verify/${code}`);
  }

  // Folder methods
  async getFolders() {
    return this.client.get<FolderCategory[]>('/api/v1/folders');
  }

  async createFolder(data: CreateFolderRequest) {
    return this.client.post<FolderCategory>('/api/v1/folders', data);
  }

  async updateFolder(id: number, data: UpdateFolderRequest) {
    return this.client.put<FolderCategory>(`/api/v1/folders/${id}`, data);
  }

  async deleteFolder(id: number) {
    return this.client.delete(`/api/v1/folders/${id}`);
  }

  // Settings methods
  async getNotificationPrefs() {
    return this.client.get<NotificationPreferences>('/api/v1/settings/notifications');
  }

  async updateNotificationPrefs(data: UpdateNotificationPrefsRequest) {
    return this.client.put<NotificationPreferences>('/api/v1/settings/notifications', data);
  }

  // Dashboard methods
  async getDashboardStats() {
    return this.client.get<DashboardStats>('/api/v1/dashboard/stats');
  }

  // Helper methods
  private getToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  private async refreshToken() {
    // Token refresh implementation
  }

  private formatError(error: any): ApiError {
    return {
      message: error.response?.data?.message || 'An error occurred',
      details: error.response?.data?.details,
      status: error.response?.status || 500,
      code: error.response?.data?.code,
    };
  }
}

export const apiClient = new ApiClient();
```

### Workflows and Sequencing

#### Onboarding Wizard Flow (4 Steps)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Onboarding Wizard Sequence                       │
└─────────────────────────────────────────────────────────────────────┘

User visits /onboarding
    │
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1: Welcome & Gmail Connection (Story 4.2)                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Show welcome message and OAuth explanation                │  │
│  │ 2. Display "Connect Gmail" button                            │  │
│  │ 3. On click: GET /api/v1/auth/gmail/config                   │  │
│  │ 4. Redirect to Google OAuth consent screen                   │  │
│  │ 5. User grants permissions                                   │  │
│  │ 6. Google redirects to /onboarding/gmail?code=xxx            │  │
│  │ 7. POST /api/v1/auth/gmail/callback { code, state }          │  │
│  │ 8. Backend returns JWT token + user object                   │  │
│  │ 9. Store token in localStorage                               │  │
│  │ 10. Show success checkmark ✓                                 │  │
│  │ 11. Enable "Continue" button                                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ User clicks "Continue"
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 2: Telegram Bot Linking (Story 4.3)                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. POST /api/v1/telegram/link → Generate 6-digit code       │  │
│  │ 2. Display code in large font (e.g., "A3F7B2")              │  │
│  │ 3. Show instructions:                                         │  │
│  │    - "Open Telegram and search for @MailAgentBot"           │  │
│  │    - "Send /start command"                                   │  │
│  │    - "Enter this code: A3F7B2"                               │  │
│  │ 4. Start polling: GET /api/v1/telegram/verify/A3F7B2        │  │
│  │    - Poll every 3 seconds                                    │  │
│  │    - Max 10 minutes before code expires                      │  │
│  │ 5. When verified=true returned:                              │  │
│  │    - Show success checkmark ✓                                │  │
│  │    - Display Telegram username                               │  │
│  │    - Enable "Continue" button                                │  │
│  │ 6. If code expires:                                           │  │
│  │    - Show "Code expired" error                               │  │
│  │    - Offer "Generate new code" button                        │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ User clicks "Continue"
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 3: Folder Configuration (Story 4.4)                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Show default folder suggestions:                          │  │
│  │    - "Government" (keywords: finanzamt, tax, visa)           │  │
│  │    - "Clients" (keywords: meeting, project)                  │  │
│  │    - "Newsletters" (keywords: unsubscribe, newsletter)       │  │
│  │ 2. User can:                                                  │  │
│  │    - Add new folder: Click "+ Add Folder"                    │  │
│  │      → Dialog with name, keywords, color picker              │  │
│  │      → POST /api/v1/folders { name, keywords, color }        │  │
│  │    - Edit folder: Click pencil icon                          │  │
│  │      → PUT /api/v1/folders/{id} { updated fields }           │  │
│  │    - Delete folder: Click trash icon                         │  │
│  │      → Confirmation dialog                                   │  │
│  │      → DELETE /api/v1/folders/{id}                           │  │
│  │    - Reorder folders: Drag and drop                          │  │
│  │      → POST /api/v1/folders/reorder { folder_ids }           │  │
│  │ 3. Validation:                                                │  │
│  │    - At least 1 folder required                              │  │
│  │    - Folder names must be unique                             │  │
│  │    - Name length: 1-100 characters                           │  │
│  │ 4. Enable "Continue" when ≥1 folder exists                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ User clicks "Continue"
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 4: Notification Preferences & Complete (Story 4.5 + 4.6)      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Show notification settings form:                          │  │
│  │    - Batch notifications: Toggle (default: ON)               │  │
│  │    - Batch time: Time picker (default: 18:00)                │  │
│  │    - Quiet hours: Toggle (default: ON)                       │  │
│  │    - Quiet hours: Start time (default: 22:00)                │  │
│  │                   End time (default: 08:00)                   │  │
│  │    - Priority immediate: Toggle (default: ON)                │  │
│  │ 2. User adjusts settings                                      │  │
│  │ 3. Click "Test Notification" (optional):                     │  │
│  │    - POST /api/v1/settings/notifications/test                │  │
│  │    - Backend sends test message to Telegram                  │  │
│  │    - Show "Test sent! Check Telegram" toast                  │  │
│  │ 4. Click "Complete Setup":                                    │  │
│  │    - PUT /api/v1/settings/notifications { all prefs }        │  │
│  │    - PUT /api/v1/users/me { onboarding_completed: true }     │  │
│  │    - Show success animation                                  │  │
│  │    - Display summary:                                         │  │
│  │      ✓ Gmail connected                                        │  │
│  │      ✓ Telegram linked                                        │  │
│  │      ✓ 3 folders configured                                   │  │
│  │      ✓ Notifications configured                               │  │
│  │ 5. Redirect to /dashboard                                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
    │
    │ Onboarding complete
    ↓
Dashboard page
```

#### Dashboard Page Load Sequence (Story 4.7)

```
User visits /dashboard
    │
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Dashboard Rendering Flow                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. Check authentication:                                      │  │
│  │    - If no token → Redirect to /onboarding                   │  │
│  │    - If token exists → Continue                              │  │
│  │                                                                │  │
│  │ 2. Show skeleton loading UI (shadcn/ui Skeleton components)  │  │
│  │                                                                │  │
│  │ 3. Parallel API calls:                                        │  │
│  │    - GET /api/v1/dashboard/stats                             │  │
│  │    - GET /api/v1/dashboard/activity?limit=10                 │  │
│  │    - GET /api/v1/users/me                                    │  │
│  │                                                                │  │
│  │ 4. When data arrives, render:                                 │  │
│  │                                                                │  │
│  │    ┌─────────────────────────────────────────────────────┐  │  │
│  │    │ Connection Status Cards                             │  │  │
│  │    │  ┌──────────────┐  ┌──────────────┐                │  │  │
│  │    │  │ Gmail        │  │ Telegram     │                │  │  │
│  │    │  │ ✓ Connected  │  │ ✓ Connected  │                │  │  │
│  │    │  │ Last: 2m ago │  │ @username    │                │  │  │
│  │    │  └──────────────┘  └──────────────┘                │  │  │
│  │    └─────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │    ┌─────────────────────────────────────────────────────┐  │  │
│  │    │ Email Processing Statistics                         │  │  │
│  │    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │  │  │
│  │    │  │ Total   │ │ Pending │ │ Sorted  │ │Responses│  │  │  │
│  │    │  │  127    │ │   3     │ │  104    │ │   20    │  │  │  │
│  │    │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │  │  │
│  │    └─────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │    ┌─────────────────────────────────────────────────────┐  │  │
│  │    │ Time Saved                                          │  │  │
│  │    │  Today: 15 minutes                                  │  │  │
│  │    │  Total: 420 minutes (7 hours)                       │  │  │
│  │    └─────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │    ┌─────────────────────────────────────────────────────┐  │  │
│  │    │ Recent Activity (last 10 actions)                   │  │  │
│  │    │  • Sorted to Government: "Tax documents" (2m ago)   │  │  │
│  │    │  • Response sent: "Re: Meeting request" (15m ago)   │  │  │
│  │    │  • Rejected: "Newsletter spam" (1h ago)             │  │  │
│  │    └─────────────────────────────────────────────────────┘  │  │
│  │                                                                │  │
│  │ 5. Error handling:                                            │  │
│  │    - If API call fails → Show error toast                    │  │
│  │    - If connection status error → Show reconnect buttons     │  │
│  │    - Network offline → Show offline banner                   │  │
│  │                                                                │  │
│  │ 6. Auto-refresh stats every 30 seconds (SWR polling)          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

#### Folder Management Flow (Story 4.4)

```
User navigates to /settings/folders
    │
    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Folder Management Page                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 1. GET /api/v1/folders → Load all folders                   │  │
│  │                                                                │  │
│  │ 2. Render folder list with drag-drop:                        │  │
│  │    ┌────────────────────────────────────────────────┐        │  │
│  │    │ ⋮⋮ Government [Edit] [Delete]                 │        │  │
│  │    │    Keywords: finanzamt, tax, visa              │        │  │
│  │    │    Color: 🔴                                   │        │  │
│  │    └────────────────────────────────────────────────┘        │  │
│  │    ┌────────────────────────────────────────────────┐        │  │
│  │    │ ⋮⋮ Clients [Edit] [Delete]                    │        │  │
│  │    │    Keywords: meeting, project, contract        │        │  │
│  │    │    Color: 🔵                                   │        │  │
│  │    └────────────────────────────────────────────────┘        │  │
│  │                                                                │  │
│  │ 3. User actions:                                              │  │
│  │                                                                │  │
│  │    A. Add Folder:                                             │  │
│  │       - Click "+ Add Folder"                                  │  │
│  │       - Dialog opens with form:                               │  │
│  │         • Folder name (required, 1-100 chars)                │  │
│  │         • Keywords (comma-separated, optional)                │  │
│  │         • Color picker (default random)                       │  │
│  │       - Submit → POST /api/v1/folders                        │  │
│  │       - Success → Add to list + show toast                   │  │
│  │       - Error → Show validation errors inline                │  │
│  │                                                                │  │
│  │    B. Edit Folder:                                            │  │
│  │       - Click [Edit] button                                   │  │
│  │       - Dialog opens pre-filled with current values          │  │
│  │       - User modifies fields                                  │  │
│  │       - Submit → PUT /api/v1/folders/{id}                    │  │
│  │       - Success → Update list + show toast                   │  │
│  │                                                                │  │
│  │    C. Delete Folder:                                          │  │
│  │       - Click [Delete] button                                 │  │
│  │       - Confirmation dialog:                                  │  │
│  │         "Delete 'Government' folder? This will also          │  │
│  │          remove the Gmail label. This action cannot be       │  │
│  │          undone."                                             │  │
│  │       - Confirm → DELETE /api/v1/folders/{id}                │  │
│  │       - Success → Remove from list + show toast              │  │
│  │       - Error → Show error toast                              │  │
│  │                                                                │  │
│  │    D. Reorder Folders:                                        │  │
│  │       - User drags folder up/down                             │  │
│  │       - On drop → POST /api/v1/folders/reorder               │  │
│  │       - Optimistic UI update (show new order immediately)    │  │
│  │       - If API fails → Revert order + show error toast       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Non-Functional Requirements

### Performance

**NFR001 Target: Onboarding completion in <10 minutes (NFR005 alignment)**

**Performance Budget:**
```
Onboarding Wizard End-to-End:
├── Step 1 (Gmail OAuth): ~2-3 minutes
│   ├── OAuth redirect: <2s
│   ├── Google consent screen: 30-60s (user action)
│   ├── Callback processing: <3s
│   └── Token storage: <500ms
│
├── Step 2 (Telegram linking): ~2-3 minutes
│   ├── Generate code: <1s
│   ├── User opens Telegram: 30s (user action)
│   ├── User sends /start + code: 30s (user action)
│   ├── Verification polling: 1-2 minutes (3s intervals)
│   └── Display username: <500ms
│
├── Step 3 (Folder setup): ~2-3 minutes
│   ├── Load default suggestions: <1s
│   ├── User creates 3 folders: 2 minutes (user action)
│   ├── Each folder creation API call: <1s
│   └── Total API time for 3 folders: <3s
│
├── Step 4 (Notification prefs): ~1-2 minutes
│   ├── Load default preferences: <1s
│   ├── User adjusts settings: 1 minute (user action)
│   ├── Save preferences: <1s
│   └── Complete onboarding: <1s
────────────────────────────────────────────────
Total: 7-11 minutes (Target: <10 min average)
```

**Page Load Performance Targets:**
- **Initial page load (First Contentful Paint):** <1.5s
- **Time to Interactive:** <3s
- **Dashboard data load:** <2s (parallel API calls)
- **Folder list render:** <500ms for 50 folders
- **Settings page load:** <1s

**Optimization Strategies:**
1. **Next.js Server Components:** Pre-render static content, reduce client-side JavaScript
2. **SWR for data fetching:** Automatic caching, revalidation, optimistic updates
3. **Image optimization:** Next.js Image component with WebP format
4. **Code splitting:** Lazy load non-critical components (settings pages)
5. **Parallel API calls:** Dashboard loads stats + activity + user concurrently

**Performance Monitoring:**
- Lighthouse CI integration in GitHub Actions (target score: 90+)
- Web Vitals tracking (Core Web Vitals: LCP, FID, CLS)
- Sentry performance monitoring for slow API calls (>3s threshold)

### Security

**NFR004 Alignment: Security & Privacy for user data and OAuth tokens**

**Authentication Security:**
- **JWT Storage:** httpOnly cookies (prevents XSS attacks)
- **CSRF Protection:** SameSite=Strict cookie attribute
- **Token Expiration:** 7-day access token, automatic refresh on 401
- **Secure Transmission:** HTTPS-only (HTTP redirects to HTTPS)
- **OAuth State Parameter:** CSRF protection during Gmail OAuth flow

**API Security:**
- **Authorization Header:** `Bearer <token>` for all authenticated requests
- **CORS Configuration:** Whitelist backend API domain only
- **Rate Limiting:** Client-side throttling (max 10 req/s per endpoint)
- **Input Validation:** TypeScript types + runtime validation (Zod schemas)
- **XSS Prevention:** React's built-in escaping + DOMPurify for user input

**Data Privacy:**
- **No Local Storage of Sensitive Data:** Only JWT token stored
- **No Client-Side Email Content:** Email data only displayed from backend
- **Secure Cookie Flags:** httpOnly, Secure, SameSite=Strict
- **No Analytics Tracking:** Privacy-first (no Google Analytics, no third-party trackers)

**Dependency Security:**
- **npm audit:** Run on every build, fail on high/critical vulnerabilities
- **Dependabot:** Automatic security updates for npm packages
- **Minimal dependencies:** Reduce attack surface (shadcn/ui copies code, not installed as package)

**Environment Variables:**
- **Never commit secrets:** .env.local in .gitignore
- **Vercel Environment Variables:** Secure storage for NEXT_PUBLIC_API_URL
- **No API keys in frontend:** All sensitive operations via backend

### Reliability/Availability

**NFR002 Alignment: 99.5% uptime target during MVP**

**Error Handling:**
- **Error Boundaries:** Catch React errors, display fallback UI, prevent white screen
- **API Error Recovery:** Automatic retry with exponential backoff (max 3 retries)
- **Network Offline Detection:** Display offline banner, queue actions for retry
- **Validation Errors:** Clear inline error messages with actionable guidance

**Resilience Patterns:**
```typescript
// Example: Retry logic with exponential backoff
async function apiCallWithRetry(fn: () => Promise<any>, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(2 ** i * 1000); // 1s, 2s, 4s
    }
  }
}
```

**State Management Reliability:**
- **Optimistic UI Updates:** Show success immediately, rollback on API failure
- **SWR Automatic Revalidation:** Refetch stale data on window focus
- **Local State Persistence:** Save wizard progress to localStorage (resume on refresh)

**Deployment Reliability:**
- **Zero-Downtime Deployments:** Vercel preview deployments + atomic production deploys
- **Rollback Capability:** Instant rollback to previous deployment via Vercel dashboard
- **Health Checks:** /api/health endpoint monitored by Vercel
- **Error Tracking:** Sentry for real-time error monitoring and alerting

**Availability Targets:**
- **Frontend Uptime:** 99.9% (Vercel SLA)
- **Backend API Dependency:** 99.5% (Epic 1-3 target)
- **Combined Availability:** 99.4% (dependent on backend)

### Observability

**Logging:**
- **Client-Side Logging:** Sentry for errors, warnings, performance issues
- **Structured Logs:** Include user_id, action, timestamp, error details
- **Log Levels:** ERROR (unhandled errors), WARN (recoverable issues), INFO (user actions)
- **Privacy:** Never log email content, only metadata (subject, sender obfuscated)

**Metrics to Track:**
- **User Journey Metrics:**
  - Onboarding completion rate (target: 90%+)
  - Time spent per onboarding step (identify bottlenecks)
  - Step abandonment rate (where users drop off)
  - Dashboard load time (target: <2s)

- **Performance Metrics:**
  - Core Web Vitals (LCP, FID, CLS)
  - API response times (P50, P95, P99)
  - Time to First Byte (TTFB)
  - JavaScript bundle size (target: <200KB gzipped)

- **User Engagement Metrics:**
  - Daily active users (DAU)
  - Feature usage (folder creation, notification prefs changes)
  - Dashboard visits per day
  - Settings page visits

**Monitoring Tools:**
- **Sentry:** Error tracking, performance monitoring, user feedback
- **Vercel Analytics:** Web Vitals, page views, user sessions
- **Custom Events:** Track key user actions (onboarding completed, folder created, etc.)

**Alerting Thresholds:**
- Error rate > 5% of requests → Immediate Sentry alert
- API response time > 5s → Warning alert
- Onboarding completion rate < 80% → Weekly report
- JavaScript bundle size > 250KB → Build warning

## Dependencies and Integrations

### NPM Dependencies (`package.json`)

**Core Framework:**
```json
{
  "dependencies": {
    "next": "^15.5.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "typescript": "^5.0.0"
  }
}
```

**UI & Styling:**
```json
{
  "dependencies": {
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "@radix-ui/react-slot": "^1.0.2",
    "@radix-ui/react-toast": "^1.1.5",
    "@radix-ui/react-switch": "^1.0.3",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "tailwindcss": "^4.0.0",
    "tailwindcss-animate": "^1.0.7"
  }
}
```
*Note: shadcn/ui components are copied into src/components/ui/, not installed as npm package*

**API & Data Fetching:**
```json
{
  "dependencies": {
    "axios": "^1.6.5",
    "swr": "^2.2.4",
    "zod": "^3.22.4"
  }
}
```

**Forms & Validation:**
```json
{
  "dependencies": {
    "react-hook-form": "^7.50.0",
    "@hookform/resolvers": "^3.3.4"
  }
}
```

**Drag and Drop:**
```json
{
  "dependencies": {
    "@dnd-kit/core": "^6.1.0",
    "@dnd-kit/sortable": "^8.0.0"
  }
}
```

**Utilities:**
```json
{
  "dependencies": {
    "date-fns": "^3.0.0",
    "lucide-react": "^0.320.0"
  }
}
```

**Development Dependencies:**
```json
{
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "eslint": "^8.56.0",
    "eslint-config-next": "^15.5.0",
    "prettier": "^3.2.0",
    "@sentry/nextjs": "^7.100.0"
  }
}
```

**Monitoring & Analytics:**
```json
{
  "dependencies": {
    "@sentry/nextjs": "^7.100.0",
    "@vercel/analytics": "^1.1.0"
  }
}
```

### Backend API Integration

**Epic Dependencies:**

| Backend Feature | Epic | Status | Required For |
|----------------|------|--------|--------------|
| Gmail OAuth endpoints | Epic 1 | ✅ Complete | Story 4.2 (Gmail connection) |
| Folder CRUD APIs | Epic 1 | ✅ Complete | Story 4.4 (Folder management) |
| User model & auth | Epic 1 | ✅ Complete | All stories (authentication) |
| Telegram linking API | Epic 2 | ✅ Complete | Story 4.3 (Telegram linking) |
| Notification preferences API | Epic 2 | ✅ Complete | Story 4.5 (Notification settings) |
| Dashboard statistics API | Epics 1-3 | ✅ Complete | Story 4.7 (Dashboard) |

**API Contract Assumptions:**
- All endpoints return JSON with `{ data, message, status }` structure
- Authentication via JWT in Authorization header
- Standard HTTP status codes (200, 201, 400, 401, 403, 404, 500)
- Error responses include `{ message, details, status, code }`

**API Version:** v1 (all endpoints prefixed with `/api/v1/`)

### External Services

**Vercel (Deployment & Hosting):**
- **Free Tier:** 100GB bandwidth, unlimited sites, automatic HTTPS
- **Features Used:** Zero-downtime deployments, preview URLs, edge network CDN
- **Environment Variables:** NEXT_PUBLIC_API_URL stored securely
- **Custom Domain:** mail-agent.vercel.app (or custom domain if configured)

**Sentry (Error Monitoring):**
- **Free Tier:** 5K events/month, 1 project
- **Features Used:** Error tracking, performance monitoring, source maps upload
- **Integration:** @sentry/nextjs for automatic Next.js error capture
- **Configuration:** Sentry DSN stored in environment variable

**Backend Dependency (FastAPI):**
- **Deployment:** Separate service (not managed by Epic 4)
- **URL:** Configured via NEXT_PUBLIC_API_URL environment variable
- **Fallback:** localhost:8000 for local development
- **CORS:** Backend must whitelist frontend domain

### Development Environment

**Local Development Setup:**
```bash
# Prerequisites
- Node.js 18+ (LTS)
- npm 10+

# Clone and setup
git clone <repo-url> mail-agent-frontend
cd mail-agent-frontend
npm install

# Environment configuration
cp .env.example .env.local
# Edit .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Run development server
npm run dev
# Visit http://localhost:3000

# Build for production
npm run build
npm run start
```

**shadcn/ui Setup:**
```bash
# Initialize shadcn/ui
npx shadcn@latest init

# Add required components
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add input
npx shadcn@latest add dialog
npx shadcn@latest add toast
npx shadcn@latest add form
npx shadcn@latest add switch
npx shadcn@latest add select
npx shadcn@latest add skeleton
npx shadcn@latest add alert
```

### CI/CD Pipeline

**GitHub Actions Workflow (`.github/workflows/frontend.yml`):**
```yaml
name: Frontend CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run lint
      - run: npm run type-check
      - run: npm run build

  lighthouse:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: treosh/lighthouse-ci-action@v10
        with:
          urls: https://preview-url.vercel.app
          budgetPath: ./lighthouse-budget.json
          uploadArtifacts: true

  deploy:
    needs: [test, lighthouse]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: vercel/action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
```

**Quality Gates:**
- ESLint: No errors allowed (warnings ok)
- TypeScript: Strict mode, no `any` types
- Lighthouse: Score >90 for Performance, Accessibility, Best Practices
- Bundle size: <250KB gzipped

### Integration Testing Strategy

**End-to-End Testing (Story 4.8):**
- **Tool:** Playwright (already used in Epic 3)
- **Test Scenarios:**
  1. Complete onboarding flow (Gmail → Telegram → Folders → Prefs)
  2. Dashboard data loading and display
  3. Folder CRUD operations
  4. Notification preferences update
  5. Error handling (API failures, network offline)

**Component Testing:**
- **Tool:** React Testing Library + Vitest
- **Scope:** Unit tests for isolated components
- **Coverage Target:** 70%+ for UI components

**API Integration Testing:**
- **Mock Backend:** MSW (Mock Service Worker) for API mocking
- **Test Data:** Predefined test fixtures for all API responses
- **Scenarios:** Success, validation errors, network errors, timeout

## Acceptance Criteria (Authoritative)

These acceptance criteria define the completion requirements for Epic 4. All criteria must be met before marking the epic as complete.

### AC-4.1: Next.js Project Setup
- [x] Next.js 15 project initialized with App Router
- [x] TypeScript configured with strict mode
- [x] Tailwind CSS v4 installed and configured
- [x] shadcn/ui initialized with dark theme
- [x] Project structure follows architecture specification
- [x] ESLint and Prettier configured
- [x] Development server runs without errors

### AC-4.2: Gmail OAuth Connection
- [ ] User can click "Connect Gmail" button and be redirected to Google OAuth consent screen
- [ ] OAuth callback successfully processes authorization code and returns JWT token
- [ ] Success state displays green checkmark and enables "Continue" button
- [ ] Error states display actionable error messages (e.g., "Permission denied", "Network error")
- [ ] OAuth state parameter prevents CSRF attacks
- [ ] Connection status persists across page refreshes

### AC-4.3: Telegram Bot Linking
- [ ] System generates 6-digit alphanumeric linking code
- [ ] Code displayed in large, copyable format with clear instructions
- [ ] Frontend polls verification endpoint every 3 seconds
- [ ] Success state displays Telegram username and enables "Continue" button
- [ ] Code expires after 10 minutes with option to generate new code
- [ ] Linking status persists across page refreshes

### AC-4.4: Folder Configuration
- [ ] User can create new folder with name, keywords (optional), and color (optional)
- [ ] User can edit existing folder (name, keywords, color)
- [ ] User can delete folder with confirmation dialog warning about Gmail label removal
- [ ] User can reorder folders via drag-and-drop
- [ ] Validation prevents duplicate folder names (case-insensitive)
- [ ] Validation requires at least 1 folder before proceeding
- [ ] Optimistic UI updates with rollback on API failure
- [ ] Default folder suggestions displayed (Government, Clients, Newsletters)

### AC-4.5: Notification Preferences
- [ ] User can toggle batch notifications on/off
- [ ] User can set batch time (time picker, default 18:00)
- [ ] User can toggle quiet hours on/off
- [ ] User can set quiet hours start/end times (default 22:00-08:00)
- [ ] User can toggle priority immediate notifications on/off
- [ ] "Test Notification" button sends test message to Telegram
- [ ] Preferences saved successfully with confirmation toast
- [ ] Form validation prevents invalid time ranges

### AC-4.6: Onboarding Wizard Flow
- [ ] Wizard displays progress indicator (Step 1 of 4, 2 of 4, etc.)
- [ ] Each step can only proceed when required actions are completed
- [ ] User can navigate back to previous steps
- [ ] Wizard progress persists in localStorage (resume on refresh)
- [ ] Final step displays success summary with all checkmarks
- [ ] Completion redirects to /dashboard and marks user.onboarding_completed = true
- [ ] Average onboarding time <10 minutes (measured via analytics)
- [ ] Onboarding completion rate ≥90% (measured via analytics)

### AC-4.7: Dashboard Page
- [ ] Dashboard displays Gmail connection status (connected/disconnected, last sync time)
- [ ] Dashboard displays Telegram connection status (connected/disconnected, username)
- [ ] Dashboard displays email processing statistics (total, pending, sorted, responses)
- [ ] Dashboard displays time saved today and total
- [ ] Dashboard displays recent activity list (last 10 actions)
- [ ] Statistics auto-refresh every 30 seconds via SWR
- [ ] Skeleton loading states display while data loads
- [ ] Error states display with retry option for failed API calls
- [ ] Reconnect buttons available if connections are broken

### AC-4.8: End-to-End Integration Testing
- [ ] Playwright test covers complete onboarding flow (all 4 steps)
- [ ] Playwright test covers dashboard page load and data display
- [ ] Playwright test covers folder CRUD operations
- [ ] Playwright test covers notification preferences update
- [ ] Playwright test covers error scenarios (API failure, network offline)
- [ ] All E2E tests pass consistently (≥95% pass rate over 10 runs)
- [ ] Test execution time <5 minutes for full suite

### AC-4.9: Responsive Design
- [ ] All pages render correctly on mobile (< 640px)
- [ ] All pages render correctly on tablet (640px - 1024px)
- [ ] All pages render correctly on desktop (1024px+)
- [ ] Touch targets are ≥44x44px on mobile
- [ ] No horizontal scrolling on any screen size
- [ ] Navigation adapts appropriately (hamburger menu on mobile, sidebar on desktop)

### AC-4.10: Accessibility (WCAG 2.1 Level AA)
- [ ] Lighthouse accessibility score ≥95
- [ ] All interactive elements keyboard-accessible (Tab navigation)
- [ ] Visible focus indicators on all interactive elements
- [ ] ARIA labels present on all icon-only buttons
- [ ] Form labels properly associated with inputs
- [ ] Error messages announced to screen readers (aria-live)
- [ ] Color contrast ratios meet AA standards (4.5:1 for body text)
- [ ] Manual screen reader testing passes (VoiceOver spot-check)

### AC-4.11: Performance
- [ ] Lighthouse performance score ≥90
- [ ] First Contentful Paint (FCP) <1.5s
- [ ] Time to Interactive (TTI) <3s
- [ ] Largest Contentful Paint (LCP) <2.5s
- [ ] Cumulative Layout Shift (CLS) <0.1
- [ ] JavaScript bundle size <250KB gzipped
- [ ] Dashboard loads within 2 seconds (P95)

### AC-4.12: Security
- [ ] JWT token stored in httpOnly cookie
- [ ] CSRF protection via SameSite=Strict cookie
- [ ] All API requests use HTTPS
- [ ] No secrets committed to repository (.env.local in .gitignore)
- [ ] npm audit shows zero high/critical vulnerabilities
- [ ] Input validation prevents XSS attacks
- [ ] OAuth state parameter validated on callback

### AC-4.13: Production Deployment
- [ ] Frontend deployed to Vercel with automatic HTTPS
- [ ] Environment variables configured in Vercel
- [ ] Sentry error tracking active and receiving events
- [ ] Vercel Analytics tracking page views
- [ ] GitHub Actions CI/CD pipeline passing
- [ ] Zero-downtime deployment verified
- [ ] Rollback procedure tested and documented

## Traceability Mapping

| Acceptance Criteria | PRD Requirements | Tech Spec Sections | Components/APIs | Test Coverage |
|---------------------|------------------|---------------------|----------------|---------------|
| AC-4.1: Project Setup | NFR005 (Usability), FR022 (Web UI) | System Architecture Alignment, Dependencies | Project structure, package.json | Story 4.1 setup validation |
| AC-4.2: Gmail OAuth | FR001 (Gmail OAuth), FR023 (OAuth connection) | APIs: `/api/v1/auth/gmail/*`, Workflows: Gmail OAuth flow | GmailConnectComponent, ApiClient | Story 4.2: OAuth flow test, E2E: Onboarding |
| AC-4.3: Telegram Linking | FR007 (Telegram linking), FR024 (Telegram setup) | APIs: `/api/v1/telegram/*`, Workflows: Telegram linking flow | TelegramLinkingComponent, polling logic | Story 4.3: Linking test, E2E: Onboarding |
| AC-4.4: Folder Config | FR025 (Folder creation), FR026 (Sorting rules), FR003 (Gmail labels) | APIs: `/api/v1/folders/*`, Workflows: Folder management, Data Models: FolderCategory | FolderManagementComponent, drag-drop | Story 4.4: CRUD tests, E2E: Folder ops |
| AC-4.5: Notification Prefs | FR012 (Batch notifications), Notification timing | APIs: `/api/v1/settings/notifications`, Data Models: NotificationPreferences | NotificationPrefsComponent | Story 4.5: Prefs update test, E2E: Settings |
| AC-4.6: Onboarding Wizard | NFR005 (10-min onboarding, 90% completion), FR027 (Testing) | Workflows: 4-step wizard, NFR Performance: Onboarding budget | OnboardingWizard, wizard navigation | Story 4.6: Wizard flow test, E2E: Full onboarding |
| AC-4.7: Dashboard | Dashboard overview, connection status | APIs: `/api/v1/dashboard/*`, Data Models: DashboardStats | DashboardStats, ConnectionStatus cards | Story 4.7: Dashboard test, E2E: Dashboard load |
| AC-4.8: E2E Testing | Quality assurance | Integration Testing Strategy | All components | Story 4.8: Playwright suite |
| AC-4.9: Responsive | NFR005 (Mobile-responsive) | Responsive Design section, UX breakpoints | All pages | Story 4.8: Responsive tests |
| AC-4.10: Accessibility | NFR005 (WCAG 2.1 AA) | Accessibility Strategy, shadcn/ui compliance | All interactive elements | Story 4.8: Accessibility audit |
| AC-4.11: Performance | NFR001 (Performance), NFR005 (<10 min onboarding) | NFR Performance section, optimization strategies | SWR, Next.js optimization | Story 4.8: Lighthouse CI |
| AC-4.12: Security | NFR004 (Security & Privacy) | NFR Security section, JWT auth | ApiClient, cookie handling | Story 4.8: Security audit |
| AC-4.13: Deployment | NFR002 (Reliability, 99.5% uptime) | CI/CD Pipeline, Vercel deployment | GitHub Actions, Vercel config | Story 4.8: Deployment test |

**PRD to Epic 4 Mapping:**

| PRD Functional Requirement | Epic 4 Implementation | Test Verification |
|----------------------------|----------------------|-------------------|
| FR022: Web-based configuration interface | Next.js 15 frontend with shadcn/ui | AC-4.1, AC-4.6, AC-4.7 |
| FR023: Gmail OAuth connection with explanations | GmailConnectComponent with clear permission UI | AC-4.2 |
| FR024: Telegram bot connection with instructions | TelegramLinkingComponent with step-by-step guide | AC-4.3 |
| FR025: Folder creation and naming | FolderManagementComponent with CRUD operations | AC-4.4 |
| FR026: Sorting rules via keywords | Folder keywords field in creation/edit | AC-4.4 |
| FR027: Connection testing functionality | "Test Notification" button in notification prefs | AC-4.5 |

**NFR to Epic 4 Mapping:**

| Non-Functional Requirement | Epic 4 Implementation | Measurement |
|---------------------------|----------------------|-------------|
| NFR001: <2 min email processing | Dashboard shows real-time stats | AC-4.7: Stats auto-refresh |
| NFR002: 99.5% uptime | Vercel 99.9% SLA, error boundaries | AC-4.13: Deployment reliability |
| NFR004: Security (JWT, TLS) | httpOnly cookies, HTTPS-only, CSRF protection | AC-4.12: Security audit |
| NFR005: <10 min onboarding, 90% completion | 4-step wizard optimized, analytics tracking | AC-4.6: Onboarding metrics |

## Risks, Assumptions, Open Questions

### Risks

**Risk 1: Backend API Availability**
- **Description:** Epic 4 frontend depends entirely on Epic 1-3 backend APIs. If backend is unstable or incomplete, frontend development blocked.
- **Probability:** Medium
- **Impact:** High (blocks all stories)
- **Mitigation:**
  - Use MSW (Mock Service Worker) to mock all backend APIs during development
  - Contract testing to verify API compatibility
  - Early integration testing in Story 4.1 to identify issues
  - Fallback: Build frontend with mocks, integrate later
- **Owner:** Backend team (Epics 1-3), Frontend developer (Story 4.1)

**Risk 2: OAuth Redirect URI Configuration**
- **Description:** Gmail OAuth requires exact redirect URI match. Misconfiguration causes "redirect_uri_mismatch" error and blocks onboarding.
- **Probability:** Medium
- **Impact:** High (blocks Story 4.2, core onboarding)
- **Mitigation:**
  - Document exact redirect URI format in Story 4.2
  - Test with multiple environments (localhost, Vercel preview, production)
  - Clear error messages guide user to check OAuth configuration
  - Provide troubleshooting guide in docs
- **Owner:** Story 4.2 developer

**Risk 3: Vercel Free Tier Limits**
- **Description:** Vercel free tier has 100GB bandwidth/month. If exceeded, site becomes unavailable or incurs costs.
- **Probability:** Low (MVP with few users)
- **Impact:** Medium (temporary unavailability)
- **Mitigation:**
  - Monitor bandwidth usage via Vercel dashboard
  - Optimize images and assets (WebP, lazy loading)
  - Implement CDN caching headers
  - Upgrade plan if traffic increases
- **Owner:** DevOps, Product Manager

**Risk 4: Browser Compatibility Issues**
- **Description:** Advanced features (async/await, CSS Grid) may not work in older browsers, breaking UI.
- **Probability:** Low (target modern browsers)
- **Impact:** Medium (degraded UX for some users)
- **Mitigation:**
  - Next.js automatically polyfills for target browsers
  - Define browser support policy: Chrome/Firefox/Safari/Edge last 2 versions
  - Test in BrowserStack or similar cross-browser testing tool
  - Display "Update browser" banner for unsupported browsers
- **Owner:** Story 4.8 testing

**Risk 5: Third-Party Dependency Vulnerabilities**
- **Description:** NPM packages (React, Next.js, shadcn/ui dependencies) may have security vulnerabilities.
- **Probability:** Medium (common in JavaScript ecosystem)
- **Impact:** Medium (security exposure)
- **Mitigation:**
  - Run `npm audit` on every build (GitHub Actions)
  - Enable Dependabot for automatic security updates
  - Review and update dependencies monthly
  - Fail build on high/critical vulnerabilities
- **Owner:** DevOps, Story 4.1 setup

### Assumptions

**Assumption 1: Backend API Contract Stability**
- **Description:** Assume Epic 1-3 backend APIs will not change significantly during Epic 4 development.
- **Validation:** Confirm with backend team, use API versioning (v1)
- **Impact if False:** Requires frontend code changes, API client updates, regression testing

**Assumption 2: Vercel Deployment Access**
- **Description:** Assume team has access to Vercel account with appropriate permissions for deployment.
- **Validation:** Verify Vercel account setup in Story 4.1
- **Impact if False:** Cannot deploy, must find alternative hosting (Netlify, Railway, etc.)

**Assumption 3: User Has Gmail and Telegram**
- **Description:** Assume all users have Gmail accounts and Telegram installed before starting onboarding.
- **Validation:** Display prerequisites on landing page before onboarding
- **Impact if False:** Cannot complete onboarding, must provide clear instructions

**Assumption 4: Users Access from Desktop/Tablet**
- **Description:** Assume primary onboarding happens on desktop or tablet (not mobile phone), as OAuth and Telegram setup easier on larger screens.
- **Validation:** Analytics tracking of device types during onboarding
- **Impact if False:** Mobile onboarding may have lower completion rate, need mobile-optimized wizard

**Assumption 5: English-Only UI for MVP**
- **Description:** Assume all users comfortable with English interface (multilingual email handling is separate from UI language).
- **Validation:** Confirmed in PRD (Out of Scope: Localization/i18n)
- **Impact if False:** Need to add i18n library (next-i18next), translate all UI strings

### Open Questions

**Q1: Should onboarding wizard allow skipping steps?**
- **Context:** Some users may want to set up Gmail first, then Telegram later.
- **Options:**
  - A) Require all steps in order (current design)
  - B) Allow skipping Telegram, mark as "Incomplete" on dashboard
  - C) Allow full flexibility, but require completion before email processing starts
- **Decision Needed By:** Story 4.6 implementation
- **Assigned To:** Product Manager (John)

**Q2: What happens if user closes browser mid-onboarding?**
- **Context:** localStorage can save progress, but partial onboarding may leave system in inconsistent state.
- **Options:**
  - A) Resume from last completed step (save progress in localStorage)
  - B) Start over from Step 1 (simpler, but worse UX)
  - C) Save progress to backend, resume from any device
- **Decision:** Option A (localStorage resume) for MVP
- **Implementation:** Story 4.6

**Q3: Should dashboard be accessible before onboarding completes?**
- **Context:** User may complete Gmail OAuth (Step 1) then navigate to dashboard without finishing other steps.
- **Options:**
  - A) Block dashboard access until onboarding complete (redirect to /onboarding)
  - B) Show partial dashboard with "Complete setup" banner
  - C) Allow access, but show warnings for incomplete steps
- **Decision Needed By:** Story 4.7 implementation
- **Assigned To:** UX Designer (Amelia)

**Q4: How to handle backend API downtime during onboarding?**
- **Context:** If backend is down, frontend cannot complete onboarding, but user already granted Gmail OAuth.
- **Options:**
  - A) Display "Service temporarily unavailable, try again later" error
  - B) Implement retry queue with exponential backoff (auto-retry)
  - C) Save state, send email notification when service restored
- **Decision:** Option A for MVP, B for post-MVP enhancement
- **Implementation:** Story 4.2-4.6 error handling

**Q5: Should folder colors be user-selectable or auto-generated?**
- **Context:** UX spec shows color picker, but may add complexity.
- **Options:**
  - A) User selects color from palette (current UX spec)
  - B) Auto-generate colors from predefined palette (simpler)
  - C) No colors (text-only folder names)
- **Decision:** Option A (color picker) per UX spec
- **Implementation:** Story 4.4

## Test Strategy Summary

### Testing Pyramid

```
        /\
       /E2E\          ← Story 4.8: 5 Playwright tests (Onboarding, Dashboard, Folders, Prefs, Errors)
      /------\
     /Integra-\       ← Each Story: API integration tests with MSW mocks
    /tion Tests\
   /------------\
  /  Component  \     ← Each Story: React Testing Library unit tests (70%+ coverage)
 /     Tests      \
/------------------\
```

### Test Levels

**1. Unit Tests (Component Level)**
- **Tool:** Vitest + React Testing Library
- **Scope:** Isolated component behavior
- **Coverage Target:** 70%+ for UI components
- **Examples:**
  - GmailConnectComponent renders button and handles click
  - TelegramLinkingComponent displays code and polls correctly
  - FolderManagementComponent validates form inputs
  - ErrorBoundary catches errors and displays fallback UI

**2. Integration Tests (API Integration)**
- **Tool:** MSW (Mock Service Worker) + Vitest
- **Scope:** Component + API interaction
- **Coverage:** All API calls mocked with realistic responses
- **Examples:**
  - Gmail OAuth flow: callback processes code, stores token, updates UI
  - Telegram linking: generates code, polls verification, updates on success
  - Folder creation: POST request succeeds, folder added to list
  - Dashboard load: parallel API calls fetch stats, activity, user data

**3. End-to-End Tests (User Journeys)**
- **Tool:** Playwright (already used in Epic 3)
- **Scope:** Complete user flows across multiple pages
- **Test Count:** 5 critical scenarios
- **Execution:** GitHub Actions on every PR + pre-deployment
- **Test Scenarios:**
  1. **Complete Onboarding Flow** (Story 4.8)
     - Navigate through all 4 wizard steps
     - Verify success checkmarks at each step
     - Confirm redirect to dashboard
     - Validate user.onboarding_completed = true

  2. **Dashboard Data Display** (Story 4.8)
     - Load dashboard with authenticated user
     - Verify connection status cards render
     - Verify email statistics display
     - Verify recent activity list populates

  3. **Folder CRUD Operations** (Story 4.8)
     - Create new folder with name, keywords, color
     - Edit folder name
     - Reorder folders via drag-drop
     - Delete folder with confirmation

  4. **Notification Preferences Update** (Story 4.8)
     - Toggle batch notifications
     - Change batch time
     - Enable quiet hours
     - Save preferences and verify toast

  5. **Error Handling** (Story 4.8)
     - Simulate API failure (500 error)
     - Verify error toast displays
     - Verify retry button works
     - Simulate network offline
     - Verify offline banner displays

### Test Data Strategy

**Mocked Backend Responses (MSW):**
```typescript
// Example: Mock successful Gmail OAuth callback
const handlers = [
  rest.post('/api/v1/auth/gmail/callback', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        data: {
          user: { id: 1, email: 'test@example.com', gmail_connected: true },
          token: 'mock-jwt-token'
        }
      })
    );
  }),

  rest.get('/api/v1/dashboard/stats', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        data: {
          connections: { gmail: { connected: true }, telegram: { connected: true } },
          email_stats: { total_processed: 127, pending_approval: 3 },
          time_saved: { today_minutes: 15, total_minutes: 420 }
        }
      })
    );
  })
];
```

### Quality Gates

**Automated Checks (GitHub Actions):**
1. **Linting:** ESLint must pass (zero errors)
2. **Type Checking:** TypeScript strict mode (no `any` types)
3. **Unit Tests:** All tests pass, coverage ≥70%
4. **Build:** Next.js build succeeds without errors
5. **Lighthouse CI:** Performance ≥90, Accessibility ≥95
6. **Bundle Size:** JavaScript <250KB gzipped
7. **E2E Tests:** All Playwright tests pass (≥95% pass rate)

**Manual Testing Checklist (Story 4.8):**
- [ ] Test onboarding on Chrome, Firefox, Safari
- [ ] Test responsive design on mobile, tablet, desktop
- [ ] Test keyboard navigation (Tab, Enter, Escape)
- [ ] Test screen reader (VoiceOver spot-check)
- [ ] Test error scenarios (API down, network offline)
- [ ] Test OAuth with real Google account
- [ ] Test Telegram linking with real bot
- [ ] Verify Sentry captures errors
- [ ] Verify Vercel Analytics tracks page views

### Performance Testing

**Lighthouse CI Configuration:**
```json
{
  "ci": {
    "collect": {
      "url": ["https://preview-url.vercel.app/onboarding", "https://preview-url.vercel.app/dashboard"],
      "numberOfRuns": 3
    },
    "assert": {
      "assertions": {
        "categories:performance": ["error", { "minScore": 0.9 }],
        "categories:accessibility": ["error", { "minScore": 0.95 }],
        "resource-summary:script:size": ["error", { "maxNumericValue": 250000 }]
      }
    }
  }
}
```

**Load Testing (Optional, Post-MVP):**
- Tool: k6 or Artillery
- Simulate 100 concurrent users completing onboarding
- Verify API response times <2s under load
- Verify no memory leaks in long-running sessions

### Test Execution Timeline

| Phase | Tests | When | Owner |
|-------|-------|------|-------|
| **Development** | Unit + Integration tests | Every code commit | Developer |
| **PR Review** | All automated checks + E2E | Every pull request | GitHub Actions |
| **Pre-Deployment** | Full E2E suite + manual checklist | Before production deploy | QA / Developer |
| **Post-Deployment** | Smoke tests (login, dashboard load) | After production deploy | Automated (Playwright) |
| **Regression** | Full test suite | Weekly | Automated (GitHub Actions) |

### Test Maintenance

- **Update Frequency:** Tests updated alongside feature changes
- **Flaky Test Policy:** Flaky tests (failing <95% of time) must be fixed or disabled within 48 hours
- **Test Documentation:** Each E2E test includes comment explaining user journey
- **Mock Data Updates:** Update MSW mocks when backend API contract changes

---

## Post-Review Follow-ups

This section tracks technical debt and improvements identified during code reviews for Epic 4 stories.

### Story 4.9: Fix OAuth Configuration Error

**Date:** 2025-11-18
**Reviewer:** Dimcheg (Senior Developer Review - AI)

**Follow-up Items:**

1. **[Medium] Update OAuth Test State Handling**
   - **File:** `tests/components/gmail-connect.test.tsx:143-182`
   - **Issue:** Test `test_oauth_initiation_constructs_url` expects frontend to generate state via `crypto.randomUUID()` but implementation correctly extracts state from backend-provided auth_url (GmailConnect.tsx:240-249)
   - **Action:** Update test to match current OAuth flow - backend provides state in auth_url, frontend extracts it
   - **Story Reference:** Story 4-9

2. **[Medium] Update AC 4 Documentation**
   - **File:** `docs/stories/story-4-9-fix-oauth-error.md:66`
   - **Issue:** AC text says "Check response.data.client_id" but implementation correctly checks "auth_url" per root cause analysis
   - **Action:** Update AC 4 text from "client_id" to "auth_url" to match implementation and root cause analysis
   - **Story Reference:** Story 4-9

3. **[Low] Update Package Version Documentation**
   - **File:** `docs/stories/story-4-9-fix-oauth-error.md:312`
   - **Issue:** Story says "react-error-boundary@^4.1.2" but actual installed version is "6.0.0"
   - **Action:** Update story Dev Agent Record to reflect actual version installed
   - **Story Reference:** Story 4-9
