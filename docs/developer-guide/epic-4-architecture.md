# Epic 4: Frontend Architecture Documentation
**Mail Agent Onboarding & Dashboard Frontend**

## Table of Contents
1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Architecture Patterns](#architecture-patterns)
5. [Component Breakdown](#component-breakdown)
6. [State Management](#state-management)
7. [API Integration](#api-integration)
8. [Routing & Navigation](#routing--navigation)
9. [Testing Strategy](#testing-strategy)
10. [Deployment](#deployment)
11. [Development Workflow](#development-workflow)

---

## Overview

Epic 4 implements the complete Mail Agent frontend, including:
- **Onboarding Wizard**: 4-step setup flow (Gmail, Telegram, Folders, Preferences)
- **Dashboard**: Email statistics, connection status, recent activity
- **Settings Management**: Folder configuration, notification preferences

### Key Requirements
- **NFR005**: Onboarding completion <10 minutes, 90%+ success rate
- **Accessibility**: WCAG 2.1 Level AA compliance
- **Browser Support**: Chrome, Firefox, Safari, Edge (latest versions)
- **Mobile Responsive**: 320px minimum width
- **Performance**: Lighthouse score ≥90

---

## Technology Stack

### Core Framework
```json
{
  "next": "16.0.1",
  "react": "19.2.0",
  "react-dom": "19.2.0",
  "typescript": "^5"
}
```

### UI Components
- **shadcn/ui**: Accessible component library built on Radix UI
- **Tailwind CSS**: Utility-first styling
- **Lucide React**: Icon library

### Form Management
- **React Hook Form**: Form state and validation
- **Zod**: Schema validation

### HTTP Client
- **Axios**: API communication

### Testing
- **Playwright**: E2E testing (67 tests across 5 spec files)
- **Vitest**: Unit testing
- **Testing Library**: Component testing

### Development Tools
- **ESLint**: Code linting
- **TypeScript**: Type safety
- **PostCSS**: CSS processing

---

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js app router
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── onboarding/         # Onboarding wizard
│   │   │   └── page.tsx
│   │   └── dashboard/          # Dashboard
│   │       └── page.tsx
│   ├── components/             # React components
│   │   ├── ui/                 # shadcn/ui base components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── switch.tsx
│   │   │   └── ...
│   │   ├── onboarding/         # Onboarding-specific components
│   │   │   ├── OnboardingWizard.tsx
│   │   │   ├── GmailConnect.tsx
│   │   │   ├── TelegramLink.tsx
│   │   │   ├── FolderManager.tsx
│   │   │   └── NotificationPreferences.tsx
│   │   └── dashboard/          # Dashboard-specific components
│   │       ├── ConnectionStatus.tsx
│   │       ├── EmailStats.tsx
│   │       └── RecentActivity.tsx
│   ├── lib/                    # Utilities
│   │   ├── api.ts              # API client
│   │   └── utils.ts            # Helper functions
│   └── styles/
│       └── globals.css         # Global styles
├── tests/
│   ├── e2e/                    # E2E tests
│   │   ├── fixtures/           # Test fixtures
│   │   │   ├── auth.ts         # Auth utilities
│   │   │   └── data.ts         # Test data
│   │   ├── pages/              # Page objects
│   │   │   ├── OnboardingPage.ts
│   │   │   ├── DashboardPage.ts
│   │   │   ├── FoldersPage.ts
│   │   │   └── NotificationsPage.ts
│   │   ├── onboarding.spec.ts  # Onboarding E2E tests
│   │   ├── dashboard.spec.ts   # Dashboard E2E tests
│   │   ├── folders.spec.ts     # Folder CRUD tests
│   │   ├── notifications.spec.ts
│   │   └── errors.spec.ts      # Error scenario tests
│   └── unit/                   # Unit tests
├── public/                     # Static assets
├── playwright.config.ts        # Playwright configuration
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

---

## Architecture Patterns

### 1. Component Architecture

**Pattern**: Container/Presentation (Smart/Dumb Components)

**Container Components** (manage state, API calls):
```typescript
// Example: OnboardingWizard.tsx
export function OnboardingWizard() {
  const [currentStep, setCurrentStep] = useState(1);
  const [gmailConnected, setGmailConnected] = useState(false);

  // Business logic, state management, API calls
  const handleGmailConnect = async () => { ... };

  return (
    <WizardLayout step={currentStep}>
      <GmailConnect onConnect={handleGmailConnect} />
    </WizardLayout>
  );
}
```

**Presentation Components** (receive props, render UI):
```typescript
// Example: GmailConnect.tsx
interface GmailConnectProps {
  onConnect: () => Promise<void>;
  isConnected?: boolean;
}

export function GmailConnect({ onConnect, isConnected }: GmailConnectProps) {
  // Only UI logic, no API calls
  return (
    <Card>
      <Button onClick={onConnect}>Connect Gmail</Button>
    </Card>
  );
}
```

### 2. State Management

**Local State**: React `useState` for component-specific state
```typescript
const [isLoading, setIsLoading] = useState(false);
```

**Form State**: React Hook Form for complex forms
```typescript
const form = useForm<FolderFormData>({
  resolver: zodResolver(folderSchema),
  defaultValues: { name: '', keywords: '' }
});
```

**Persistent State**: `localStorage` for wizard progress
```typescript
// Save wizard progress
localStorage.setItem('onboarding_progress', JSON.stringify({
  step: currentStep,
  gmailConnected,
  telegramLinked,
  folders: folderList
}));

// Restore wizard progress on page reload
const savedProgress = localStorage.getItem('onboarding_progress');
if (savedProgress) {
  const { step, gmailConnected, telegramLinked, folders } = JSON.parse(savedProgress);
  setCurrentStep(step);
  // ...
}
```

**No Global State Library**: We intentionally avoid Redux/Zustand for Epic 4 because:
- Limited shared state needs
- Component tree is shallow
- Props drilling is manageable
- `localStorage` handles persistence

### 3. Error Handling

**Pattern**: Consistent error boundaries and user feedback

```typescript
try {
  await api.post('/gmail/connect', { code });
  toast.success('Gmail connected!');
  setGmailConnected(true);
} catch (error) {
  if (error.response?.status === 401) {
    toast.error('Permission denied. Click "Connect Gmail" to try again.');
  } else if (error.response?.status === 500) {
    toast.error('Something went wrong. Please try again in a few minutes.');
  } else {
    toast.error('Connection failed. Check your internet and try again.');
  }
}
```

**Error Display Patterns**:
- **Toast Notifications**: Transient errors (network, API failures)
- **Inline Alerts**: Persistent errors (validation, permission issues)
- **Modal Dialogs**: Critical errors requiring user action

### 4. Loading States

**Pattern**: Optimistic UI with loading indicators

```typescript
const [isLoading, setIsLoading] = useState(false);

const handleSubmit = async () => {
  setIsLoading(true);
  try {
    await api.post('/folders', folderData);
    toast.success('Folder created!');
  } catch (error) {
    toast.error('Failed to create folder');
  } finally {
    setIsLoading(false);
  }
};

return (
  <Button disabled={isLoading}>
    {isLoading ? (
      <>
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        Creating...
      </>
    ) : (
      'Create Folder'
    )}
  </Button>
);
```

---

## Component Breakdown

### Onboarding Wizard

#### 1. OnboardingWizard.tsx (Container)
**Responsibility**: Orchestrate 4-step wizard flow

**State**:
```typescript
const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);
const [gmailConnected, setGmailConnected] = useState(false);
const [telegramLinked, setTelegramLinked] = useState(false);
const [folders, setFolders] = useState<Folder[]>([]);
const [preferences, setPreferences] = useState<NotificationPreferences>({});
```

**Methods**:
- `handleGmailConnect()`: OAuth flow initiation
- `handleTelegramLink()`: Linking code generation
- `handleFolderCreate()`: Folder creation
- `handlePreferencesSave()`: Save notification settings
- `handleNext()`: Validate step and advance
- `handleBack()`: Return to previous step
- `saveProgress()`: Persist to localStorage
- `restoreProgress()`: Restore from localStorage

**Validation Rules**:
- Step 1 → 2: Gmail must be connected
- Step 2 → 3: Telegram must be linked
- Step 3 → 4: At least 1 folder created
- Step 4 → Complete: All preferences saved

#### 2. GmailConnect.tsx (Presentation)
**Responsibility**: Gmail OAuth UI

**Props**:
```typescript
interface GmailConnectProps {
  onConnect: () => Promise<void>;
  isConnected: boolean;
  isLoading: boolean;
  error?: string;
}
```

**UI Elements**:
- Card with title "Connect Your Gmail Account"
- Description explaining benefits
- Permissions list (read emails, send replies, add labels)
- "Connect Gmail" button (triggers OAuth)
- Success state with checkmark
- Error alert with retry action

**OAuth Flow**:
1. User clicks "Connect Gmail"
2. Frontend calls `GET /api/gmail/oauth-url`
3. Backend returns Google OAuth URL
4. Frontend redirects to OAuth URL
5. User grants permissions on Google
6. Google redirects to `/api/gmail/callback?code=...`
7. Backend exchanges code for tokens
8. Frontend receives success/error and updates UI

#### 3. TelegramLink.tsx (Presentation)
**Responsibility**: Telegram bot linking UI

**Props**:
```typescript
interface TelegramLinkProps {
  onGenerateCode: () => Promise<string>;
  onVerify: () => Promise<boolean>;
  isLinked: boolean;
  isLoading: boolean;
}
```

**UI Elements**:
- Instructions to find @MailAgentBot
- 6-digit linking code (tap to copy)
- "Waiting for confirmation..." spinner (polling)
- Success state with checkmark
- Error alert with retry/regenerate

**Linking Flow**:
1. Frontend calls `POST /api/telegram/generate-code`
2. Backend generates 6-digit code (10 min expiry)
3. User opens Telegram, finds @MailAgentBot
4. User sends code to bot
5. Bot verifies code, links user
6. Frontend polls `GET /api/telegram/verify-status` every 3 seconds
7. When verified, show success state

#### 4. FolderManager.tsx (Presentation)
**Responsibility**: Folder CRUD UI

**Props**:
```typescript
interface FolderManagerProps {
  folders: Folder[];
  onCreateFolder: (folder: FolderInput) => Promise<void>;
  onUpdateFolder: (id: string, folder: FolderInput) => Promise<void>;
  onDeleteFolder: (id: string) => Promise<void>;
  isLoading: boolean;
}
```

**UI Elements**:
- Folder list (name, keywords, color badge)
- "Create Folder" form (name, keywords, color picker)
- Edit/delete actions per folder
- Validation (name required, keywords comma-separated)
- Empty state ("No folders yet")

**Folder Schema**:
```typescript
interface Folder {
  id: string;
  name: string;
  keywords: string[]; // comma-separated in UI
  color?: string; // hex color
  createdAt: string;
}
```

#### 5. NotificationPreferences.tsx (Presentation)
**Responsibility**: Notification settings UI

**Props**:
```typescript
interface NotificationPreferencesProps {
  preferences: NotificationPreferences;
  onSave: (preferences: NotificationPreferences) => Promise<void>;
  onTestNotification: () => Promise<void>;
  isLoading: boolean;
}
```

**UI Elements**:
- Batch notifications toggle + frequency select
- Quiet hours toggle + time pickers (start/end)
- Priority immediate toggle
- "Send Test Notification" button

**Preferences Schema**:
```typescript
interface NotificationPreferences {
  batchEnabled: boolean;
  batchFrequency?: 15 | 30 | 60; // minutes
  quietHoursEnabled: boolean;
  quietHoursStart?: string; // HH:MM format
  quietHoursEnd?: string;
  priorityImmediate: boolean;
}
```

### Dashboard

#### 1. Dashboard.tsx (Container)
**Responsibility**: Aggregate dashboard data

**Data Sources**:
- `GET /api/dashboard/stats`: Email counts, folder stats
- `GET /api/dashboard/connections`: Gmail/Telegram status
- `GET /api/dashboard/activity`: Recent email activity

**Refresh Strategy**:
- Initial load on mount
- Auto-refresh every 30 seconds (SWR pattern)
- Manual refresh button

#### 2. ConnectionStatus.tsx (Presentation)
**Responsibility**: Display Gmail/Telegram connection status

**Props**:
```typescript
interface ConnectionStatusProps {
  gmailConnected: boolean;
  telegramConnected: boolean;
  onReconnect: (service: 'gmail' | 'telegram') => void;
}
```

**UI Elements**:
- Gmail status card (Connected/Not Connected)
- Telegram status card (Connected/Not Connected)
- "Reconnect" button for disconnected services
- Connection health indicator (green/red)

#### 3. EmailStats.tsx (Presentation)
**Responsibility**: Display email processing statistics

**Props**:
```typescript
interface EmailStatsProps {
  totalProcessed: number;
  todayProcessed: number;
  foldersCreated: number;
  avgSortingTime: number;
}
```

**UI Elements**:
- Stat cards in grid layout (4 columns desktop, 1 column mobile)
- Icons for visual hierarchy
- Trend indicators (if applicable)

#### 4. RecentActivity.tsx (Presentation)
**Responsibility**: Display recent email sorting activity

**Props**:
```typescript
interface RecentActivityProps {
  activities: Activity[];
  isLoading: boolean;
}

interface Activity {
  id: string;
  emailSubject: string;
  senderName: string;
  folderName: string;
  timestamp: string;
}
```

**UI Elements**:
- Activity feed (list of recent emails)
- Each item: subject, sender, folder, time ago
- Empty state if no activity
- Skeleton loading during fetch

---

## State Management

### Wizard State Persistence

**Why localStorage?**
- Users may close browser mid-onboarding
- Prevent re-doing completed steps
- Simple key-value storage sufficient

**Storage Schema**:
```typescript
interface OnboardingProgress {
  step: 1 | 2 | 3 | 4;
  gmailConnected: boolean;
  telegramLinked: boolean;
  folders: Folder[];
  preferences: NotificationPreferences;
  lastUpdated: string; // ISO timestamp
}

// Save
localStorage.setItem('onboarding_progress', JSON.stringify(progress));

// Load
const saved = localStorage.getItem('onboarding_progress');
const progress = saved ? JSON.parse(saved) : defaultProgress;

// Clear on completion
localStorage.removeItem('onboarding_progress');
```

**Expiration**: Progress expires after 7 days of inactivity

### Form State with React Hook Form

**Example: Folder Creation Form**
```typescript
const folderSchema = z.object({
  name: z.string().min(1, 'Folder name is required'),
  keywords: z.string().min(1, 'At least one keyword is required'),
  color: z.string().optional(),
});

const form = useForm<FolderInput>({
  resolver: zodResolver(folderSchema),
  defaultValues: {
    name: '',
    keywords: '',
    color: '#3b82f6',
  },
});

const onSubmit = form.handleSubmit(async (data) => {
  await onCreateFolder(data);
  form.reset();
  toast.success('Folder created!');
});
```

---

## API Integration

### API Client Setup

**lib/api.ts**:
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (add auth token)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor (handle errors)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### API Endpoints

#### Gmail Endpoints
```typescript
// Get OAuth URL
GET /api/gmail/oauth-url
Response: { url: string }

// OAuth callback (server-side redirect)
GET /api/gmail/callback?code=...&state=...
Response: Redirect to /onboarding?step=2&gmail_connected=true

// Check connection status
GET /api/gmail/status
Response: { connected: boolean }

// Disconnect Gmail
DELETE /api/gmail/disconnect
Response: { success: boolean }
```

#### Telegram Endpoints
```typescript
// Generate linking code
POST /api/telegram/generate-code
Response: { code: string, expiresAt: string }

// Verify linking status (polling)
GET /api/telegram/verify-status
Response: { linked: boolean }

// Send test notification
POST /api/telegram/test-notification
Response: { success: boolean }

// Disconnect Telegram
DELETE /api/telegram/disconnect
Response: { success: boolean }
```

#### Folder Endpoints
```typescript
// List folders
GET /api/folders
Response: { folders: Folder[] }

// Create folder
POST /api/folders
Body: { name: string, keywords: string[], color?: string }
Response: { folder: Folder }

// Update folder
PUT /api/folders/:id
Body: { name?: string, keywords?: string[], color?: string }
Response: { folder: Folder }

// Delete folder
DELETE /api/folders/:id
Response: { success: boolean }
```

#### Notification Endpoints
```typescript
// Get preferences
GET /api/notifications/preferences
Response: { preferences: NotificationPreferences }

// Update preferences
PUT /api/notifications/preferences
Body: NotificationPreferences
Response: { preferences: NotificationPreferences }
```

#### Dashboard Endpoints
```typescript
// Get stats
GET /api/dashboard/stats
Response: {
  totalProcessed: number,
  todayProcessed: number,
  foldersCreated: number,
  avgSortingTime: number
}

// Get connections
GET /api/dashboard/connections
Response: {
  gmail: { connected: boolean },
  telegram: { connected: boolean }
}

// Get recent activity
GET /api/dashboard/activity?limit=10
Response: { activities: Activity[] }
```

---

## Routing & Navigation

### Next.js App Router Structure

```
app/
├── layout.tsx              # Root layout (global styles, providers)
├── page.tsx                # Home/landing page
├── onboarding/
│   └── page.tsx            # /onboarding (wizard)
├── dashboard/
│   └── page.tsx            # /dashboard (main dashboard)
└── settings/
    ├── page.tsx            # /settings (settings overview)
    ├── folders/
    │   └── page.tsx        # /settings/folders
    └── notifications/
        └── page.tsx        # /settings/notifications
```

### Navigation Flow

```
/ (Home)
  ↓ [Get Started]
/onboarding?step=1 (Gmail)
  ↓ [Next]
/onboarding?step=2 (Telegram)
  ↓ [Next]
/onboarding?step=3 (Folders)
  ↓ [Next]
/onboarding?step=4 (Preferences)
  ↓ [Complete Setup]
/dashboard (Success!)
```

### Protected Routes

**Middleware** (middleware.ts):
```typescript
export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token');

  // Protect dashboard routes
  if (request.nextUrl.pathname.startsWith('/dashboard')) {
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/settings/:path*'],
};
```

---

## Testing Strategy

### Test Pyramid

```
     /\
    /  \  E2E Tests (67 tests, Playwright)
   /____\
  /      \  Integration Tests (Component + API mocks)
 /________\
/__________\ Unit Tests (Pure functions, utilities)
```

### E2E Testing with Playwright

**Configuration** (playwright.config.ts):
- 5 browser configurations (Chrome, Firefox, Safari, Mobile Chrome, Mobile Safari)
- Auto-start dev server (`npm run dev`)
- Screenshots on failure
- Video on failure
- HTML report

**Test Specs**:

1. **onboarding.spec.ts** (11 tests)
   - Complete 4-step wizard flow
   - Individual step completion
   - Step validation (can't proceed without completion)
   - Progress persistence (localStorage)
   - Performance (completion time <10 min)

2. **dashboard.spec.ts** (15 tests)
   - Data loading and display
   - Connection status accuracy
   - Email stats display
   - Activity feed
   - Auto-refresh (30s interval)
   - Manual refresh button

3. **folders.spec.ts** (12 tests)
   - Create folder (valid/invalid data)
   - Edit folder
   - Delete folder
   - Validation errors
   - Persistence after reload

4. **notifications.spec.ts** (13 tests)
   - Enable/disable batch notifications
   - Set quiet hours
   - Enable priority immediate
   - Send test notification
   - Persistence after reload

5. **errors.spec.ts** (16 tests)
   - API failures (500, 404, 401, 429)
   - Network offline/recovery
   - Timeout handling
   - Validation errors
   - Error message clarity

**Page Object Pattern**:
```typescript
// pages/OnboardingPage.ts
export class OnboardingPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/onboarding');
  }

  async completeGmailStep() {
    await this.page.click('[data-testid="connect-gmail"]');
    await this.page.waitForSelector('[data-testid="gmail-connected"]');
  }

  async completeTelegramStep() {
    const code = await this.page.textContent('[data-testid="linking-code"]');
    // Mock bot verification...
    await this.page.waitForSelector('[data-testid="telegram-linked"]');
  }

  async completeFoldersStep(folders: FolderInput[]) {
    for (const folder of folders) {
      await this.page.fill('[data-testid="folder-name"]', folder.name);
      await this.page.fill('[data-testid="folder-keywords"]', folder.keywords);
      await this.page.click('[data-testid="save-folder"]');
    }
    await this.page.click('[data-testid="next-button"]');
  }

  async completePreferencesStep(preferences: NotificationPreferences) {
    if (preferences.batchEnabled) {
      await this.page.click('[data-testid="batch-toggle"]');
    }
    // ...
    await this.page.click('[data-testid="complete-setup"]');
  }

  async verifyOnboardingComplete() {
    await this.page.waitForURL('/dashboard');
    await expect(this.page.locator('[data-testid="dashboard"]')).toBeVisible();
  }
}
```

**Running E2E Tests**:
```bash
# All tests (all browsers)
npm run test:e2e

# Chromium only (CI)
npm run test:e2e:chromium

# Headed mode (see browser)
npm run test:e2e:headed

# UI mode (interactive debugging)
npm run test:e2e:ui

# Debug mode (step through)
npm run test:e2e:debug

# View report
npm run test:e2e:report
```

### Unit Testing with Vitest

**Example: Utility function test**
```typescript
// lib/utils.test.ts
import { describe, it, expect } from 'vitest';
import { formatTimeAgo } from './utils';

describe('formatTimeAgo', () => {
  it('formats minutes correctly', () => {
    const now = new Date();
    const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
    expect(formatTimeAgo(fiveMinutesAgo.toISOString())).toBe('5 minutes ago');
  });

  it('formats hours correctly', () => {
    const now = new Date();
    const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000);
    expect(formatTimeAgo(twoHoursAgo.toISOString())).toBe('2 hours ago');
  });
});
```

### Component Testing with Testing Library

**Example: Button component test**
```typescript
// components/ui/button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './button';

describe('Button', () => {
  it('renders button text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click me</Button>);
    fireEvent.click(screen.getByText('Click me'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('disables button when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByText('Click me')).toBeDisabled();
  });
});
```

---

## Deployment

### Build Process

```bash
# Install dependencies
npm ci

# Run linter
npm run lint

# Run type check
npm run build

# Run tests
npm run test:e2e:chromium
```

### Environment Variables

**.env.local** (Development):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

**.env.production** (Production):
```env
NEXT_PUBLIC_API_URL=https://api.mailagent.app
```

### CI/CD Pipeline

**GitHub Actions** (.github/workflows/frontend-e2e.yml):
```yaml
name: Frontend E2E Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e:chromium
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

---

## Development Workflow

### Getting Started

1. **Clone repository**:
```bash
git clone <repo-url>
cd frontend
```

2. **Install dependencies**:
```bash
npm install
```

3. **Set up environment**:
```bash
cp .env.example .env.local
# Edit .env.local with local API URL
```

4. **Run development server**:
```bash
npm run dev
# Open http://localhost:3000
```

### Development Commands

```bash
# Development server (hot reload)
npm run dev

# Production build
npm run build

# Start production server
npm start

# Linting
npm run lint

# E2E tests (all browsers)
npm run test:e2e

# E2E tests (Chromium only, for CI)
npm run test:e2e:chromium

# E2E tests (headed mode, see browser)
npm run test:e2e:headed

# E2E tests (UI mode, interactive debugging)
npm run test:e2e:ui

# E2E tests (debug mode, step through with DevTools)
npm run test:e2e:debug

# View E2E test report
npm run test:e2e:report
```

### Code Quality

**Linting** (ESLint):
```bash
npm run lint
```

**Type Checking** (TypeScript):
```bash
npx tsc --noEmit
```

**Formatting** (Prettier - optional):
```bash
npx prettier --write .
```

### Git Workflow

1. Create feature branch:
```bash
git checkout -b feature/task-description
```

2. Make changes, commit:
```bash
git add .
git commit -m "feat: implement folder creation UI"
```

3. Push and create PR:
```bash
git push origin feature/task-description
```

4. CI runs E2E tests automatically

5. Merge after approval

---

## Performance Optimization

### Code Splitting

Next.js automatically code-splits by route. For heavy components, use dynamic imports:

```typescript
import dynamic from 'next/dynamic';

const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <p>Loading...</p>,
  ssr: false, // Disable server-side rendering if needed
});
```

### Image Optimization

Use Next.js `<Image>` component:

```typescript
import Image from 'next/image';

<Image
  src="/logo.png"
  alt="Mail Agent Logo"
  width={200}
  height={50}
  priority // For above-the-fold images
/>
```

### API Request Optimization

**Debounce user input**:
```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedSearch = useDebouncedCallback((query) => {
  api.get(`/search?q=${query}`);
}, 500);
```

**Cache API responses** (SWR pattern):
```typescript
const { data, error, isLoading } = useSWR('/api/dashboard/stats', fetcher, {
  refreshInterval: 30000, // Refresh every 30 seconds
  revalidateOnFocus: false,
});
```

---

## Security Considerations

### XSS Prevention

- Always sanitize user input before rendering
- Use React's built-in escaping (don't use `dangerouslySetInnerHTML`)
- Validate all form inputs with Zod schemas

### CSRF Protection

- API uses CSRF tokens for state-changing requests
- Tokens stored in HTTP-only cookies
- Frontend sends token in `X-CSRF-Token` header

### Secure Storage

- Never store sensitive data (passwords, tokens) in localStorage
- Use HTTP-only cookies for auth tokens
- Clear sensitive data on logout

---

## Accessibility (WCAG 2.1 Level AA)

### Key Requirements

1. **Color Contrast**: ≥4.5:1 for text, ≥3:1 for UI components
2. **Keyboard Navigation**: All functionality accessible via keyboard
3. **Focus Visible**: All interactive elements have visible focus indicator
4. **Screen Reader Support**: Proper ARIA labels and roles
5. **Form Labels**: All inputs have associated labels
6. **Error Identification**: Clear, descriptive error messages

### Implementation

**Semantic HTML**:
```typescript
<main>
  <h1>Dashboard</h1>
  <section aria-label="Email Statistics">
    <h2>Email Stats</h2>
    {/* ... */}
  </section>
</main>
```

**ARIA Labels**:
```typescript
<button aria-label="Connect Gmail account">
  <MailIcon />
</button>

<div role="alert" aria-live="polite">
  {errorMessage}
</div>
```

**Keyboard Navigation**:
```typescript
<div
  role="button"
  tabIndex={0}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick();
    }
  }}
>
  Custom Button
</div>
```

---

## Troubleshooting

### Common Issues

**Issue: "Module not found" error**
- Solution: Run `npm install` to install dependencies

**Issue: Port 3000 already in use**
- Solution: Kill existing process or use different port:
  ```bash
  PORT=3001 npm run dev
  ```

**Issue: API requests failing (CORS)**
- Solution: Check API URL in `.env.local`
- Ensure backend has CORS configured for frontend origin

**Issue: E2E tests failing locally**
- Solution: Ensure dev server is running (`npm run dev`)
- Install Playwright browsers: `npx playwright install`

**Issue: Build failing in CI**
- Solution: Check Node version matches (20.x)
- Check for type errors: `npx tsc --noEmit`

---

## Additional Resources

- **Next.js Documentation**: https://nextjs.org/docs
- **Playwright Documentation**: https://playwright.dev
- **shadcn/ui Documentation**: https://ui.shadcn.com
- **Tailwind CSS Documentation**: https://tailwindcss.com/docs
- **WCAG Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/

---

**Architecture Documentation Version:** 1.0
**Last Updated:** 2025-11-14
**Maintained By:** Epic 4 Team
**Questions?** Contact dev team or open GitHub issue
