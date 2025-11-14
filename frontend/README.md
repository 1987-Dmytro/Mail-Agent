# Mail Agent Frontend

AI-powered email management system frontend built with Next.js 15, TypeScript, and Tailwind CSS.

## Overview

This is the frontend application for the Mail Agent project, providing a modern web interface for AI-powered email classification, Gmail integration, and Telegram approval workflows.

## Tech Stack

- **Framework**: Next.js 16.0.1 (Next.js 15 features)
- **Language**: TypeScript 5 with strict mode
- **Styling**: Tailwind CSS v4 with CSS-based configuration
- **UI Components**: shadcn/ui with Radix UI primitives
- **HTTP Client**: Axios with interceptors
- **Testing**: Vitest + React Testing Library + MSW
- **Icons**: Lucide React
- **Themes**: next-themes for dark mode support
- **Notifications**: Sonner for toast messages

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Set up environment
cp .env.example .env.local

# 3. Start development server
npm run dev

# 4. Run E2E tests (optional)
npm run test:e2e:chromium
```

The application will be available at http://localhost:3000

## Prerequisites

- **Node.js**: 18.x or higher (20.x recommended)
- **npm**: 10.x or higher
- **Backend API**: Running on http://localhost:8000 (configurable via environment variables)
- **Browsers** (for E2E testing):
  - Chrome 90+ (recommended)
  - Firefox 88+
  - Safari 15+
  - Edge 90+

## Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.example .env.local
```

4. Configure your `.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

Start the development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

### Other Commands

- **Type checking**: `npm run type-check`
- **Linting**: `npm run lint`
- **Build for production**: `npm run build`
- **Start production server**: `npm start`

## Testing

### End-to-End Testing (Playwright)

The project includes **67 comprehensive E2E tests** covering all user journeys, error scenarios, and accessibility requirements.

**Run E2E tests:**
```bash
# All browsers (Chrome, Firefox, Safari, Mobile)
npm run test:e2e

# Chromium only (fastest, used in CI)
npm run test:e2e:chromium

# Headed mode (see browser actions)
npm run test:e2e:headed

# UI mode (interactive debugging)
npm run test:e2e:ui

# Debug mode (step through with DevTools)
npm run test:e2e:debug

# View test report
npm run test:e2e:report
```

**E2E Test Coverage:**
- **onboarding.spec.ts** (11 tests): Complete 4-step wizard, validation, performance
- **dashboard.spec.ts** (15 tests): Data loading, stats, activity feed, auto-refresh
- **folders.spec.ts** (12 tests): CRUD operations, validation, persistence
- **notifications.spec.ts** (13 tests): Batch settings, quiet hours, test notification
- **errors.spec.ts** (16 tests): API failures, network offline, timeouts, validation

**Page Object Pattern:**
- `tests/e2e/pages/OnboardingPage.ts` - Onboarding wizard interactions
- `tests/e2e/pages/DashboardPage.ts` - Dashboard page interactions
- `tests/e2e/pages/FoldersPage.ts` - Folder management interactions
- `tests/e2e/pages/NotificationsPage.ts` - Notification settings interactions

**Test Fixtures:**
- `tests/e2e/fixtures/auth.ts` - Authentication utilities and mock OAuth
- `tests/e2e/fixtures/data.ts` - Test data (users, folders, preferences)

### Unit Testing (Vitest)

**Run unit tests:**
```bash
# All unit tests
npm test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage
```

**Unit Test Coverage:**
- `tests/project-setup.test.ts` - Project configuration tests
- `tests/styling.test.tsx` - Tailwind CSS and shadcn/ui tests
- `tests/api-and-auth.test.ts` - API client and authentication tests
- `tests/layout.test.tsx` - Layout and navigation component tests
- `tests/integration/integration.test.tsx` - Integration tests

All unit tests use Vitest as the test runner and Mock Service Worker (MSW) for API mocking.

### CI/CD Testing

GitHub Actions automatically runs E2E tests on every push and pull request:
- **Pull Requests**: Chromium tests only (fast feedback)
- **Main Branch**: Full browser suite (Chrome, Firefox, Safari, Mobile)
- **Artifacts**: Playwright reports and videos uploaded on failure

See `.github/workflows/frontend-e2e.yml` for CI configuration.

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx         # Root layout with dark theme
│   │   ├── page.tsx           # Landing page
│   │   └── globals.css        # Global styles and design tokens
│   ├── components/
│   │   ├── ui/                # shadcn/ui components (11 components)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── toaster.tsx
│   │   │   ├── form.tsx
│   │   │   ├── label.tsx
│   │   │   ├── switch.tsx
│   │   │   ├── select.tsx
│   │   │   ├── skeleton.tsx
│   │   │   └── alert.tsx
│   │   ├── shared/            # Shared components
│   │   │   ├── Navbar.tsx    # Navigation bar
│   │   │   ├── Sidebar.tsx   # Sidebar navigation
│   │   │   └── ErrorBoundary.tsx  # Error boundary
│   │   ├── onboarding/        # Onboarding flow components
│   │   └── dashboard/         # Dashboard components
│   ├── lib/
│   │   ├── api-client.ts      # Axios-based API client with interceptors
│   │   ├── auth.ts            # JWT authentication utilities
│   │   └── utils.ts           # Utility functions (cn for className merging)
│   └── types/
│       ├── api.ts             # API response types
│       ├── user.ts            # User and auth types
│       └── folder.ts          # Folder category types
├── tests/
│   ├── setup.ts               # Vitest setup with MSW
│   ├── mocks/
│   │   ├── server.ts          # MSW server configuration
│   │   └── handlers.ts        # API request handlers
│   ├── project-setup.test.ts
│   ├── styling.test.tsx
│   ├── api-and-auth.test.ts
│   ├── layout.test.tsx
│   └── integration/
│       └── integration.test.tsx
├── public/                     # Static assets
├── .env.example               # Environment variable template
├── .env.local                 # Local environment variables (gitignored)
├── components.json            # shadcn/ui configuration
├── tsconfig.json              # TypeScript configuration
├── vitest.config.ts           # Vitest configuration
└── package.json               # Dependencies and scripts
```

## Design System

### Theme Configuration

The application uses a **Sophisticated Dark** theme with the following design tokens:

- **Background**: Slate 900 (#0f172a)
- **Foreground**: Slate 50 (#f8fafc)
- **Primary**: Blue 500 (#3b82f6)
- **Success**: Green 400 (#34d399)
- **Error**: Red 400 (#f87171)

All design tokens are defined in `src/app/globals.css` using CSS variables.

### Component Library

The project uses shadcn/ui components built on Radix UI primitives. Components are located in `src/components/ui/` and can be customized via the `cn()` utility function.

## API Client

The API client (`src/lib/api-client.ts`) provides:

- **Axios-based singleton** for consistent backend communication
- **Request interceptor** to automatically add JWT tokens
- **Response interceptor** with:
  - 401 handling (token refresh/redirect to login)
  - 403 handling (redirect to login)
  - Network error retry with exponential backoff (max 3 attempts)
- **Type-safe methods**: `get<T>()`, `post<T>()`, `put<T>()`, `delete<T>()`, `patch<T>()`

### Usage Example

```typescript
import { apiClient } from '@/lib/api-client';

// GET request
const response = await apiClient.get<{ status: string }>('/health');
console.log(response.data.status); // Type-safe

// POST request
const user = await apiClient.post<User>('/api/v1/auth/login', {
  email: 'user@example.com',
  password: 'password123'
});
```

## Authentication

JWT-based authentication utilities are provided in `src/lib/auth.ts`:

- `getToken()` - Retrieve JWT token from storage
- `setToken(token, remember?)` - Save JWT token to localStorage or sessionStorage
- `removeToken()` - Clear JWT token from storage
- `isAuthenticated()` - Check if user has valid token
- `isTokenExpired(token)` - Check if JWT token is expired
- `decodeToken(token)` - Decode JWT payload
- `getUserFromToken()` - Extract user info from stored token

## Onboarding Wizard

The onboarding wizard guides new users through a 5-step setup process to configure Mail Agent (Story 4.6). First-time users are automatically redirected to `/onboarding` on login.

### Wizard Flow

1. **Step 1 - Welcome**: Introduction to Mail Agent benefits and setup preview
2. **Step 2 - Gmail Connection**: OAuth flow to connect Gmail account (reuses Story 4.2 component)
3. **Step 3 - Telegram Linking**: 6-digit code linking to Telegram bot (reuses Story 4.3 component)
4. **Step 4 - Folder Setup**: Create at least 1 folder category with suggested defaults
5. **Step 5 - Completion**: Success screen with summary and "Go to Dashboard" button

### Key Features

- **Progress Indicator**: Visual step tracker showing "Step X of 5" with completed/current/future states
- **Validation Enforcement**: Next button disabled until step requirements met (Gmail connected, Telegram linked, folders created)
- **localStorage Persistence**: Progress saved automatically - users can close browser and resume later
- **Automatic Redirect**: First-time users (`user.onboarding_completed = false`) redirected to `/onboarding`
- **Completion Tracking**: Wizard updates `user.onboarding_completed = true` on completion
- **Mobile Responsive**: Works on all screen sizes with adaptive progress indicator

### Component Architecture

```typescript
// Wizard container (main orchestrator)
OnboardingWizard.tsx - State management, step validation, navigation
  └── WizardProgress.tsx - Visual progress indicator
  └── WelcomeStep.tsx - Step 1: Introduction
  └── GmailStep.tsx - Step 2: Wraps GmailConnect component
  └── TelegramStep.tsx - Step 3: Wraps TelegramLink component
  └── FolderSetupStep.tsx - Step 4: Simplified folder creation
  └── CompletionStep.tsx - Step 5: Summary and completion

// Redirect handler
OnboardingRedirect.tsx - Checks user.onboarding_completed and redirects if false
```

### Wizard State Management

The wizard uses React useState + localStorage for state persistence:

```typescript
interface OnboardingState {
  currentStep: number;           // 1-5
  gmailConnected: boolean;       // Step 2 validation
  telegramConnected: boolean;    // Step 3 validation
  folders: FolderCategory[];     // Step 4 validation
  gmailEmail?: string;           // Optional summary data
  telegramUsername?: string;     // Optional summary data
  lastUpdated: string;           // ISO timestamp
}
```

**localStorage Key**: `"onboarding_progress"`
- **Storage Format**: JSON string (use `JSON.parse()` to read, `JSON.stringify()` to write)
- **When Saved**: Automatically on every step change (via `useOnboardingProgress` hook)
- **When Loaded**: On component mount to resume progress from previous session
- **When Cleared**:
  - Successfully completing onboarding (reaching Step 5 and clicking "Go to Dashboard")
  - Data corruption detected (invalid JSON or missing required fields)
  - Manual clearing via browser DevTools (user action)
- **Stale Progress Detection**: Progress older than 7 days triggers console warning
- **Edge Cases Handled**:
  - Corrupted data: Falls back to Step 1 with clean state
  - Missing fields: Uses default values (currentStep: 1, all booleans: false, folders: [])
  - Browser private mode: Works normally (localStorage available in private mode)

**Example localStorage Value**:
```json
{
  "currentStep": 3,
  "gmailConnected": true,
  "telegramConnected": false,
  "folders": [
    {"id": 1, "name": "Important", "keywords": ["urgent"], "color": "red"}
  ],
  "gmailEmail": "user@example.com",
  "telegramUsername": null,
  "lastUpdated": "2025-11-12T15:30:00.000Z"
}
```

**Security Note**: Only wizard progress is stored - no sensitive data like JWT tokens, passwords, or API keys. All authentication credentials remain in memory or httpOnly cookies.

### Step Validation Rules

Each step has specific requirements before allowing Next navigation:

| Step | Requirement | Validation |
|------|-------------|-----------|
| Step 1 (Welcome) | None | Always can proceed |
| Step 2 (Gmail) | Gmail connected | `gmailConnected === true` |
| Step 3 (Telegram) | Telegram linked | `telegramConnected === true` |
| Step 4 (Folders) | At least 1 folder | `folders.length >= 1` |
| Step 5 (Complete) | None | Navigate to dashboard |

### Usage

The wizard is automatically triggered for first-time users:

```typescript
// OnboardingRedirect checks user status on authenticated routes
if (user && !user.onboarding_completed) {
  router.push('/onboarding'); // Auto-redirect to wizard
}
```

### Testing

**Unit Tests** (8 tests): `tests/components/onboarding-wizard.test.tsx`
- Wizard renders with progress indicator
- Next/Back navigation
- Validation prevents skipping required steps
- localStorage persistence and restore

**Integration Tests** (6 tests): `tests/integration/onboarding-flow.test.tsx`
- Complete wizard flow end-to-end
- Resume from localStorage after browser refresh
- First-time user redirect
- Completion updates backend (`user.onboarding_completed = true`)

## Gmail OAuth Setup

The application uses Gmail OAuth 2.0 for secure email access. The OAuth flow is implemented in the onboarding wizard (Story 4.2).

### OAuth Flow Overview

1. **User Initiation**: User clicks "Connect Gmail" button on `/onboarding/gmail`
2. **Config Fetch**: Frontend fetches OAuth configuration from backend (`GET /api/v1/auth/gmail/config`)
3. **CSRF Protection**: Generate cryptographic state token using `crypto.randomUUID()`
4. **Redirect**: User redirected to Google OAuth consent screen with state parameter
5. **Callback**: Google redirects back with authorization code and state
6. **Validation**: State parameter validated against stored value (CSRF protection)
7. **Token Exchange**: Authorization code exchanged for JWT token (`POST /api/v1/auth/gmail/callback`)
8. **Storage**: JWT token stored in localStorage for persistence
9. **Success**: User shown success state with email address

### OAuth Component Usage

```typescript
import { GmailConnect } from '@/components/onboarding/GmailConnect';

export default function OnboardingPage() {
  return (
    <GmailConnect
      onSuccess={() => console.log('OAuth complete!')}
      onError={(error) => console.error('OAuth failed:', error)}
    />
  );
}
```

### OAuth Security Features

- **CSRF Protection**: State parameter prevents cross-site request forgery attacks
- **Token Validation**: State token validated on callback before exchanging code
- **Secure Storage**: JWT token stored in localStorage (MVP-acceptable, httpOnly cookies planned for production)
- **Connection Persistence**: Auth status checked on page load to skip OAuth if already connected
- **Error Handling**: Comprehensive error messages for all failure scenarios

### OAuth API Methods

The API client provides three OAuth-specific methods:

```typescript
// Get OAuth configuration
const config = await apiClient.gmailOAuthConfig();
// Returns: { auth_url, client_id, scopes }

// Exchange authorization code for token
const auth = await apiClient.gmailCallback(code, state);
// Returns: { user, token }

// Check authentication status
const status = await apiClient.authStatus();
// Returns: { authenticated, user? }
```

### Connection Persistence Hook

Use the `useAuthStatus` hook to check authentication status:

```typescript
import { useAuthStatus } from '@/hooks/useAuthStatus';

function MyComponent() {
  const { isAuthenticated, isLoading, user, refresh } = useAuthStatus();

  if (isLoading) return <Spinner />;
  if (isAuthenticated) return <Dashboard user={user} />;
  return <LoginPage />;
}
```

### Testing OAuth Flow

OAuth tests are located in `tests/components/gmail-connect.test.tsx` (unit tests) and `tests/integration/oauth-flow.test.tsx` (integration tests).

Run OAuth tests:
```bash
# All tests
npm test

# OAuth unit tests only
npm test gmail-connect

# OAuth integration tests only
npm test oauth-flow
```

The tests use MSW (Mock Service Worker) to mock Google OAuth endpoints and backend APIs.

## Telegram Bot Linking

The application allows users to link their Telegram account to receive email notifications. The linking flow is implemented in the onboarding wizard (Story 4.3).

### Telegram Linking Flow Overview

1. **Code Generation**: User navigates to `/onboarding/telegram` and a 6-digit alphanumeric code is generated
2. **Instructions Display**: Step-by-step instructions shown with prominent code display
3. **Copy Code**: User clicks "Copy Code" button to copy linking code to clipboard
4. **Open Telegram**: User clicks "Open Telegram" button (deep link) or manually opens Telegram app
5. **Send Command**: User searches for `@MailAgentBot` and sends `/start [CODE]`
6. **Polling**: Frontend polls backend every 3 seconds to check if code has been verified
7. **Verification**: Backend detects user's /start command and verifies the linking code
8. **Success**: Success state displays Telegram username and checkmark
9. **Persistence**: Connection status persists across page refreshes

### Telegram Component Usage

```typescript
import { TelegramLink } from '@/components/onboarding/TelegramLink';

export default function TelegramOnboardingPage() {
  return (
    <TelegramLink
      onSuccess={() => console.log('Telegram linked!')}
      onError={(error) => console.error('Telegram linking failed:', error)}
    />
  );
}
```

### Telegram Security Features

- **No Secrets in Frontend**: Only public bot username (@MailAgentBot) exposed, no bot tokens
- **Code Expiration**: Linking codes expire after 10 minutes with countdown timer
- **Component State Only**: Code stored in component state (not localStorage) for security
- **Polling Cleanup**: Polling stops on success, error, or component unmount (prevents memory leaks)
- **Connection Persistence**: Telegram status checked on page load to skip linking if already connected
- **Error Handling**: Comprehensive error messages for expired codes, network failures, and invalid codes

### Telegram API Methods

The API client provides three Telegram-specific methods:

```typescript
// Generate new linking code
const linkingCode = await apiClient.generateTelegramLink();
// Returns: { code, expires_at, verified }

// Verify linking code (called via polling)
const verification = await apiClient.verifyTelegramLink(code);
// Returns: { verified, telegram_id?, telegram_username? }

// Check Telegram connection status
const status = await apiClient.telegramStatus();
// Returns: { connected, telegram_id?, telegram_username? }
```

### Connection Persistence Hook

Use the `useTelegramStatus` hook to check Telegram connection status:

```typescript
import { useTelegramStatus } from '@/hooks/useTelegramStatus';

function MyComponent() {
  const { isLinked, isLoading, telegramUsername, refresh } = useTelegramStatus();

  if (isLoading) return <Spinner />;
  if (isLinked) return <div>Connected to {telegramUsername}</div>;
  return <TelegramLink />;
}
```

### Testing Telegram Linking Flow

Telegram tests are located in `tests/components/telegram-link.test.tsx` (unit tests) and `tests/integration/telegram-linking-flow.test.tsx` (integration tests).

Run Telegram tests:
```bash
# All tests
npm test

# Telegram unit tests only
npm test telegram-link

# Telegram integration tests only
npm test telegram-linking-flow
```

The tests use vi.mock() to mock API client methods and timer functions (setInterval) for polling simulation.

## Folder Categories Management

The application allows users to create and manage custom email folder categories (Gmail labels). The folder management interface is implemented in `/settings/folders` (Story 4.4).

### Folder Management Overview

1. **View Folders**: Display all user's folder categories in a responsive grid layout
2. **Create Folder**: Add new folder with custom name, keywords, and color
3. **Edit Folder**: Update existing folder's name, keywords, and color
4. **Delete Folder**: Remove folder with confirmation dialog (also removes Gmail label)
5. **Default Suggestions**: First-time users see 4 pre-configured category suggestions
6. **Color Picker**: Choose from 10 predefined colors or enter custom hex code
7. **Keyword Management**: Add comma-separated keywords for email classification

### Folder Component Usage

```typescript
import FolderManager from '@/components/settings/FolderManager';

export default function FoldersPage() {
  return (
    <div className="container">
      <h1>Email Folders</h1>
      <FolderManager />
    </div>
  );
}
```

### Form Validation Rules

The folder creation/edit form enforces the following validation rules:

- **Folder Name**:
  - Required field (cannot be empty)
  - Length: 1-50 characters
  - Uniqueness: Must not match existing folder names (case-insensitive)
  - Trimmed whitespace from input

- **Keywords**:
  - Optional field
  - Format: Comma-separated list (e.g., "urgent, deadline, важный")
  - Trimmed whitespace from each keyword
  - No minimum/maximum count for MVP

- **Color**:
  - Optional field (defaults to random from palette)
  - Format: Hex color code (#RRGGBB) or selected from predefined palette
  - Validation: Regex pattern `/^#[0-9A-Fa-f]{6}$/`

### Default Category Suggestions

When a user has no folders, the following default categories are suggested:

1. **Important** - Keywords: urgent, deadline, wichtig (Red: #ef4444)
2. **Government** - Keywords: finanzamt, tax, visa, behörde (Orange: #f97316)
3. **Clients** - Keywords: meeting, project, contract, client (Blue: #3b82f6)
4. **Newsletters** - Keywords: unsubscribe, newsletter, marketing (Gray: #64748b)

Users can quickly add these defaults with one click or create custom categories from scratch.

### Folder API Methods

The API client provides four folder-specific methods:

```typescript
// Get all folders for authenticated user
const folders = await apiClient.getFolders();
// Returns: FolderCategory[]

// Create new folder
const newFolder = await apiClient.createFolder({
  name: 'Work',
  keywords: ['urgent', 'deadline'],
  color: '#ef4444'
});
// Returns: FolderCategory

// Update existing folder
const updatedFolder = await apiClient.updateFolder(folderId, {
  name: 'Updated Work',
  keywords: ['urgent', 'important'],
  color: '#3b82f6'
});
// Returns: FolderCategory

// Delete folder (also removes Gmail label)
await apiClient.deleteFolder(folderId);
// Returns: void
```

### Folder State Management

The `FolderManager` component uses:

- **React State** (`useState`) for folders list, dialog visibility, and form state
- **React Hook Form** + **Zod** for form validation and submission
- **Optimistic UI Updates**: Folders appear immediately, with rollback on API errors
- **Toast Notifications** (Sonner): Success/error messages for all CRUD operations

### Folder Security Features

- **Input Sanitization**: All user inputs validated and sanitized before submission
- **XSS Prevention**: React's built-in escaping prevents script injection via folder names
- **No Hardcoded Credentials**: All API calls use JWT authentication from API client
- **HTTPS Communication**: API_URL configured for secure backend communication
- **Duplicate Prevention**: Case-insensitive name uniqueness validation

### Testing Folder Management

Folder tests are located in:
- `tests/components/folder-manager.test.tsx` - 8 unit tests covering all CRUD operations
- `tests/integration/folder-crud-flow.test.tsx` - 5 integration tests covering complete workflows

Run folder tests:
```bash
# All tests
npm test

# Folder unit tests only
npm test folder-manager

# Folder integration tests only
npm test folder-crud-flow
```

The tests use `vi.mock()` to mock API client methods and verify component behavior, form validation, and error handling.

## Notification Preferences Settings

The application allows users to configure when and how they receive Telegram notifications for email activity. The notification preferences interface is implemented in `/settings/notifications` (Story 4.5).

### Notification Preferences Overview

1. **Batch Notifications**: Group email notifications and send once per day at a specified time
2. **Priority Alerts**: Receive high-priority emails immediately, bypassing batch timing
3. **Quiet Hours**: Suppress all notifications during specified hours (supports overnight ranges)
4. **Test Notification**: Send a test message to Telegram to verify settings
5. **Default Settings**: Best-practice defaults pre-selected for optimal user experience

### Notification Settings Component Usage

```typescript
import NotificationSettings from '@/components/settings/NotificationSettings';

export default function NotificationsPage() {
  return (
    <div className="container max-w-4xl">
      <h1>Notification Preferences</h1>
      <p>Configure when and how you receive Telegram notifications</p>
      <NotificationSettings />
    </div>
  );
}
```

### Default Notification Preferences

When a user first accesses notification settings, the following defaults are applied:

- **Batch Notifications**: Enabled (batch_enabled: true)
- **Batch Time**: End of day - 18:00 (6 PM)
- **Quiet Hours**: Enabled (quiet_hours_enabled: true)
- **Quiet Hours Range**: 22:00 - 08:00 (overnight range)
- **Priority Immediate**: Enabled (high-priority emails sent immediately)
- **Confidence Threshold**: 70% (min_confidence_threshold: 0.7)

These defaults optimize for work-life balance while ensuring urgent matters receive immediate attention.

### Form Validation Rules

The notification preferences form enforces the following validation rules:

- **Batch Time**:
  - Format: HH:MM (24-hour format, e.g., "18:00")
  - Valid range: 00:00 - 23:59
  - Regex validation: `/^([01]\d|2[0-3]):([0-5]\d)$/`

- **Quiet Hours Start/End**:
  - Format: HH:MM (24-hour format)
  - Valid range: 00:00 - 23:59
  - Cross-field validation: End time must be different from start time
  - Overnight ranges supported: 22:00 (start) - 08:00 (end) is VALID
  - Same-day ranges supported: 08:00 (start) - 22:00 (end) is VALID
  - Invalid example: 10:00 (start) - 10:00 (end) - same time not allowed

- **Confidence Threshold**:
  - Type: Number (float)
  - Range: 0.5 - 1.0 (displayed as 50% - 100%)
  - Default: 0.7 (70%)
  - Higher values = fewer interruptions, but may miss urgent emails

### Notification API Methods

The API client provides three notification-specific methods:

```typescript
// Get user notification preferences
const prefs = await apiClient.getNotificationPrefs();
// Returns: NotificationPreferences

// Update notification preferences (all fields optional)
const updated = await apiClient.updateNotificationPrefs({
  batch_enabled: true,
  batch_time: '18:00',
  quiet_hours_enabled: true,
  quiet_hours_start: '22:00',
  quiet_hours_end: '08:00',
  priority_immediate: true,
  min_confidence_threshold: 0.7
});
// Returns: NotificationPreferences

// Send test notification to user's Telegram
const result = await apiClient.testNotification();
// Returns: { message: string, success: boolean }
```

### Notification State Management

The `NotificationSettings` component uses:

- **React State** (`useState`) for preferences object, loading states, and form submission state
- **React Hook Form** + **Controller** + **Zod** for form validation and submission
- **Form Reset**: `reset()` method for atomic form updates (avoids race conditions)
- **Toast Notifications** (Sonner): Success/error messages for save and test operations
- **Real-time Validation**: Client-side validation prevents submission of invalid data
- **Optimistic UI**: Settings take effect immediately after successful save

### Notification Security Features

- **No Sensitive Data**: No sensitive information stored in notification preferences
- **Time Input Sanitization**: Time strings validated with regex to prevent XSS injection
- **HTTPS Communication**: API_URL configured for secure backend communication
- **Input Validation**: Client-side validation matches backend expectations
- **Zero Vulnerabilities**: npm audit shows 0 vulnerabilities (verified)

### Testing Notification Preferences

Notification tests are located in:
- `tests/components/notification-settings.test.tsx` - 8 unit tests covering form rendering, toggles, validation, save, test notification
- `tests/integration/notification-prefs-flow.test.tsx` - 5 integration tests covering complete workflows including overnight ranges and persistence

Run notification tests:
```bash
# All tests
npm test

# Notification unit tests only
npm test notification-settings

# Notification integration tests only
npm test notification-prefs-flow
```

The tests use `vi.mock()` to mock API client methods and `fireEvent.submit()` for form submission testing. All 13 tests pass with 100% success rate.

### Overnight Quiet Hours Logic

The notification settings support overnight quiet hours ranges (e.g., 22:00 - 08:00):

```typescript
// Validation logic
function isValidQuietHoursRange(start: string, end: string): boolean {
  // If start === end, invalid (same time not allowed)
  if (start === end) {
    return false;
  }

  // Both overnight and same-day ranges are valid
  // Examples:
  // - 22:00 - 08:00 (overnight, crosses midnight) - VALID
  // - 08:00 - 22:00 (same day, normal range) - VALID

  return true;
}
```

This allows users to set quiet hours that span midnight without triggering validation errors.

## Dashboard Overview

The Dashboard provides a real-time overview of email processing activity, connection status, and system health. The dashboard is implemented in `/dashboard` (Story 4.7) and serves as the default view after onboarding completion.

### Dashboard Features

1. **Connection Status Cards**: Visual indicators for Gmail and Telegram connections with reconnect buttons
2. **Email Processing Statistics**: 4 cards showing Total Processed, Pending Approval, Auto-Sorted, and Responses Sent
3. **Time Saved Metrics**: Display minutes saved today and total hours/minutes saved overall
4. **Recent Activity Feed**: Last 10 email actions (sorted, sent, rejected) with timestamps
5. **System Health Indicator**: Green/Yellow/Red alerts based on connection status
6. **RAG Indexing Progress**: Progress bar shown when email history indexing is in progress
7. **Quick Actions**: Navigation buttons to Manage Folders, Update Settings, View Full Stats
8. **Helpful Tips**: Onboarding tips for new users (< 7 days since registration)
9. **Auto-Refresh**: Statistics update every 30 seconds via SWR polling
10. **Manual Refresh**: Refresh button to force immediate data reload

### Dashboard Component Architecture

```typescript
// Main dashboard page orchestrates all sub-components
frontend/src/app/dashboard/page.tsx
  ├── Uses SWR for data fetching:
  │   - useSWR('/api/v1/dashboard/stats', apiClient.getDashboardStats, { refreshInterval: 30000 })
  │   - Automatic caching, revalidation, and 30-second polling
  ├── Renders layout with inline components:
  │   - SystemHealthBanner (top alert banner)
  │   - ConnectionStatus (Gmail + Telegram cards with reconnect buttons)
  │   - StatsCard × 4 (Total, Pending, Sorted, Responses)
  │   - TimeSavedCard (Today + Total metrics)
  │   - RecentActivity (Last 10 actions feed)
  │   - QuickActions (3 navigation buttons)
  │   - HelpfulTips (For new users < 7 days)
  └── Loading state: DashboardSkeleton component
      Error state: Toast notification with retry button
```

### Dashboard Data Models

The dashboard consumes two API endpoints:

```typescript
// GET /api/v1/dashboard/stats
interface DashboardStats {
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
  rag_indexing_in_progress?: boolean;  // Optional (Epic 3)
  rag_indexing_progress?: number;       // Optional 0-100 percentage
}

interface ConnectionStatus {
  connected: boolean;
  last_sync?: string;  // ISO timestamp
  error?: string;
}

interface ActivityItem {
  id: number;
  type: 'sorted' | 'response_sent' | 'rejected';
  email_subject: string;
  timestamp: string;  // ISO timestamp
  folder_name?: string;  // Only for type='sorted'
}
```

### Dashboard API Methods

The API client provides two dashboard-specific methods:

```typescript
// Get complete dashboard statistics
const stats = await apiClient.getDashboardStats();
// Returns: DashboardStats (connections, email_stats, time_saved, recent_activity)

// Get recent email activity feed (optional limit parameter)
const activity = await apiClient.getRecentActivity(10);
// Returns: ActivityItem[] (last N email actions)
```

### SWR Configuration

The dashboard uses **SWR (Stale-While-Revalidate)** for automatic data fetching, caching, and real-time updates:

```typescript
import useSWR from 'swr';

// Auto-refresh every 30 seconds
const { data: statsResponse, error, isLoading, mutate } = useSWR(
  '/api/v1/dashboard/stats',
  apiClient.getDashboardStats,
  {
    refreshInterval: 30000,      // 30 seconds (AC: 11)
    revalidateOnFocus: true,     // Refresh when tab gains focus
    revalidateOnReconnect: true, // Refresh when network reconnects
  }
);

// Manual refresh via mutate()
<Button onClick={() => mutate()}>Refresh</Button>
```

**SWR Benefits:**
- **Automatic Caching**: Reduces redundant API calls
- **Background Revalidation**: Data stays fresh without full page reloads
- **Optimistic UI**: Instant feedback on manual refresh
- **Network Resilience**: Auto-retries on network errors
- **Deduplication**: Multiple components can use same SWR key without duplicate requests

### Dashboard State Management

The dashboard uses:

- **SWR** for API data fetching and caching (no global state needed)
- **React State** (`useState`) for manual refresh loading indicator
- **useRouter** for navigation to settings pages
- **Toast Notifications** (Sonner) for error handling and refresh confirmations

No Redux, Zustand, or global state - SWR handles all data synchronization.

### Responsive Design Breakpoints

The dashboard layout adapts to different screen sizes:

- **Mobile (< 640px)**: Single column layout, all cards stacked vertically
- **Tablet (640px - 1024px)**: 2-column grid, connection cards side-by-side
- **Desktop (1024px+)**: 3-column grid for stats, 2-column for other sections

All interactive elements (buttons, links) have ≥44x44px touch targets on mobile for accessibility.

### Dashboard Security Features

- **Authentication Required**: OnboardingRedirect enforces JWT token presence
- **No Sensitive Data in Logs**: Dashboard does not log email content, only IDs and counts
- **XSS Prevention**: React's built-in escaping prevents script injection via email subjects
- **HTTPS Communication**: API_URL configured for secure backend communication
- **Zero Vulnerabilities**: npm audit shows 0 vulnerabilities (verified)

### Dashboard Performance

- **Initial Load Time**: < 2 seconds (NFR requirement)
- **Parallel API Calls**: Stats and activity fetched concurrently
- **Skeleton Loading**: Prevents layout shift during data fetch
- **SWR Caching**: Reduces redundant API calls on navigation back to dashboard
- **Auto-Refresh**: 30-second polling with minimal network overhead

### Testing Dashboard

Dashboard tests are located in:
- `tests/components/dashboard.test.tsx` - 2 unit tests covering connection status display (connected/disconnected states)
- `tests/integration/dashboard-page.test.tsx` - 4 integration tests covering data loading, activity feed, skeleton, error handling

Run dashboard tests:
```bash
# All tests
npm test

# Dashboard unit tests only
npm test dashboard.test

# Dashboard integration tests only
npm test dashboard-page.test
```

The tests use `vi.mock()` to mock useAuthStatus, useSWR, and API client methods. All 6 tests (2 unit + 4 integration) pass with 100% success rate.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |

All environment variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.

## Documentation

For comprehensive guides and reference documentation, see:

### User Documentation
- **[Setup Guide](../docs/user-guide/setup.md)** - Complete step-by-step setup instructions for new users
- **[Troubleshooting Guide](../docs/user-guide/troubleshooting.md)** - Solutions for common issues (Gmail, Telegram, folders, notifications)

### Developer Documentation
- **[Epic 4 Architecture](../docs/developer-guide/epic-4-architecture.md)** - Complete technical documentation:
  - Technology stack and dependencies
  - Component architecture (Container/Presentation pattern)
  - State management (localStorage, React Hook Form, SWR)
  - API integration and endpoints
  - Testing strategy (E2E, unit, integration)
  - Deployment and CI/CD
  - Performance optimization
  - Security best practices
  - Accessibility compliance (WCAG 2.1 Level AA)

### Accessibility Documentation
- **[WCAG Validation Checklist](../docs/accessibility/wcag-validation-checklist.md)** - Complete WCAG 2.1 Level AA validation procedures

### Polish & Refinement Guides
- **[Copy & Messaging Improvements](../docs/copy-messaging-improvements.md)** - 170+ copy improvements for clarity and friendliness
- **[Visual Polish Guide](../docs/visual-polish-guide.md)** - Visual consistency standards, loading states, error patterns

### Usability Testing
- **[Test Protocol](../docs/usability-testing/test-protocol.md)** - Facilitator guide for conducting usability tests
- **[Observation Checklist](../docs/usability-testing/observation-checklist.md)** - Step-by-step observation form
- **[Consent Form](../docs/usability-testing/consent-form.md)** - GDPR-compliant participant consent
- **[Results Report Template](../docs/usability-testing/results-report-template.md)** - Analysis and reporting template

## Troubleshooting

### Issue: API requests fail with CORS errors

**Solution**: Ensure the backend API is running and has CORS configured to allow requests from http://localhost:3000

### Issue: Tests fail with "Cannot find module" errors

**Solution**: Run `npm install` to ensure all dependencies are installed, including devDependencies

### Issue: TypeScript errors in strict mode

**Solution**: The project uses strict TypeScript settings. Ensure all variables are properly typed and handle potential `undefined` values with optional chaining or type guards.

### Issue: Dark theme not applying

**Solution**: Verify that `globals.css` is imported in `app/layout.tsx` and the `<html>` tag has the `dark` class applied.

### Issue: Environment variables not loaded

**Solution**:
1. Ensure `.env.local` exists (copy from `.env.example`)
2. Restart the dev server after changing environment variables
3. Verify the variable is prefixed with `NEXT_PUBLIC_` for client-side access

## Security Best Practices

1. **Never commit `.env.local`** - Contains sensitive configuration
2. **Use HTTPS in production** - Configure `NEXT_PUBLIC_API_URL` with https:// in production
3. **JWT token storage** - Tokens are stored in localStorage by default; use sessionStorage for sensitive contexts
4. **XSS prevention** - React automatically escapes values; avoid dangerouslySetInnerHTML
5. **CSRF protection** - Backend should implement CSRF tokens for state-changing operations
6. **Input validation** - Always validate user input on both client and server side

## Contributing

When adding new features:

1. Follow the existing project structure
2. Write tests for new components and utilities (unit + integration)
3. Use TypeScript strict mode (no `any` types)
4. Follow shadcn/ui patterns for new UI components
5. Update this README with new environment variables or setup steps

## License

See the project root for license information.
