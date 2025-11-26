# Full Local Validation Checklist

**Purpose**: Comprehensive local testing before production deployment
**Estimated Time**: 2-4 hours
**Status**: ⏳ **IN PROGRESS**
**Date**: 2025-11-26

---

## Prerequisites

Before starting validation, ensure:

- [ ] Backend is running: `cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- [ ] Frontend is running: `cd frontend && npm run dev`
- [ ] PostgreSQL is running (Docker or local)
- [ ] Redis is running (Docker or local): `docker ps | grep redis`
- [ ] `.env` files configured correctly in both `/backend` and `/frontend`

---

## Phase 1: Backend Health Check (15 min)

### 1.1 API Health

| # | Test | Command/Action | Expected Result | Status |
|---|------|----------------|-----------------|--------|
| 1 | Health endpoint | `curl http://localhost:8000/health` | `{"status":"healthy","version":"1.0.0"}` | ☐ |
| 2 | API docs load | Visit `http://localhost:8000/docs` | Swagger UI loads | ☐ |
| 3 | No startup errors | Check terminal logs | No tracebacks or errors | ☐ |

### 1.2 Database Connectivity

| # | Test | Command/Action | Expected Result | Status |
|---|------|----------------|-----------------|--------|
| 4 | DB connection | Check backend logs | "Connected to database" or no DB errors | ☐ |
| 5 | Tables exist | `alembic current` in backend | Shows current migration head | ☐ |

### 1.3 Redis Connectivity

| # | Test | Command/Action | Expected Result | Status |
|---|------|----------------|-----------------|--------|
| 6 | Redis ping | `redis-cli ping` | `PONG` | ☐ |
| 7 | Celery connection | Check celery worker logs (if running) | No connection errors | ☐ |

---

## Phase 2: Frontend Health Check (15 min)

### 2.1 App Loading

| # | Test | Command/Action | Expected Result | Status |
|---|------|----------------|-----------------|--------|
| 8 | Homepage loads | Visit `http://localhost:3000` | Landing page renders | ☐ |
| 9 | No console errors | Open DevTools → Console | No red errors | ☐ |
| 10 | API URL configured | Check Network tab for API calls | Calls go to `localhost:8000` | ☐ |

### 2.2 Build Verification

| # | Test | Command/Action | Expected Result | Status |
|---|------|----------------|-----------------|--------|
| 11 | TypeScript compiles | `npx tsc --noEmit` | 0 errors | ☐ |
| 12 | Build succeeds | `npm run build` | Build completes | ☐ |
| 13 | No lint errors | `npm run lint` | 0 errors | ☐ |

---

## Phase 3: Full Onboarding Flow - Manual (45-60 min)

### 3.1 Welcome Step

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 14 | Welcome page | Visit `/onboarding` | Welcome step displays | ☐ |
| 15 | Progress indicator | Check wizard progress | Shows step 1 of 4 | ☐ |
| 16 | Get Started button | Click "Get Started" | Navigates to Gmail step | ☐ |

### 3.2 Gmail OAuth Step (CRITICAL)

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 17 | Gmail step loads | Observe Gmail step | Connect Gmail button visible | ☐ |
| 18 | OAuth redirect | Click "Connect Gmail" | Redirects to Google OAuth | ☐ |
| 19 | Google consent | Grant permissions | Redirected back to app | ☐ |
| 20 | Callback handled | After redirect | No errors, success message | ☐ |
| 21 | Token stored | Check backend logs | Gmail token saved | ☐ |
| 22 | Continue button | Click Continue | Navigates to Telegram step | ☐ |

**Gmail OAuth Troubleshooting**:
- If `redirect_uri_mismatch`: Check Google Cloud Console has `http://localhost:3000/onboarding/gmail`
- If CORS error: Check `ALLOWED_ORIGINS` in backend `.env`
- If token error: Check backend logs for detailed error

### 3.3 Telegram Linking Step (CRITICAL)

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 23 | Telegram step loads | Observe Telegram step | Link instructions visible | ☐ |
| 24 | Link code generated | Check for code display | 6-digit code shown | ☐ |
| 25 | Bot link works | Click bot link | Opens Telegram app/web | ☐ |
| 26 | Send code to bot | Send code in Telegram | Bot acknowledges | ☐ |
| 27 | Polling success | Wait for verification | UI shows "linked" | ☐ |
| 28 | Continue button | Click Continue | Navigates to Folder step | ☐ |

**Telegram Troubleshooting**:
- If bot doesn't respond: Check `TELEGRAM_BOT_TOKEN` in backend `.env`
- If linking times out: Check backend logs for Telegram API errors
- If code invalid: Verify code matches exactly

### 3.4 Folder Setup Step

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 29 | Folder step loads | Observe Folder step | Folder setup UI visible | ☐ |
| 30 | Create folder | Add new folder | Folder appears in list | ☐ |
| 31 | Edit keywords | Modify folder keywords | Keywords saved | ☐ |
| 32 | Reorder folders | Drag/change priority | Order updates | ☐ |
| 33 | Delete folder | Remove a folder | Folder removed | ☐ |
| 34 | Validation works | Try empty folder name | Error message shown | ☐ |
| 35 | Continue button | Click Continue | Navigates to Completion | ☐ |

### 3.5 Completion Step

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 36 | Completion displays | Observe completion step | Success message visible | ☐ |
| 37 | Dashboard button | Click "Go to Dashboard" | Navigates to `/dashboard` | ☐ |

---

## Phase 4: Dashboard Verification (20 min)

### 4.1 Dashboard Loading

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 38 | Dashboard loads | Visit `/dashboard` | Dashboard renders | ☐ |
| 39 | User data shows | Check stats cards | Shows user info | ☐ |
| 40 | No errors | Check console | No red errors | ☐ |

### 4.2 Settings Pages

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 41 | Folders page | Visit `/settings/folders` | Folder list renders | ☐ |
| 42 | Notifications page | Visit `/settings/notifications` | Preferences form renders | ☐ |

---

## Phase 5: API Integration Validation (20 min)

### 5.1 Auth Endpoints

| # | Test | Command | Expected Result | Status |
|---|------|---------|-----------------|--------|
| 43 | Auth status | `curl localhost:8000/api/v1/auth/status` | Returns auth info | ☐ |

### 5.2 Folder Endpoints

| # | Test | Command | Expected Result | Status |
|---|------|---------|-----------------|--------|
| 44 | Get folders | `curl localhost:8000/api/v1/folders` | Returns folder list | ☐ |
| 45 | Create folder | POST to `/api/v1/folders` | Returns new folder | ☐ |

### 5.3 Telegram Endpoints

| # | Test | Command | Expected Result | Status |
|---|------|---------|-----------------|--------|
| 46 | Link status | `curl localhost:8000/api/v1/telegram/status` | Returns link status | ☐ |

---

## Phase 6: E2E Test Suite (15 min)

| # | Test | Command | Expected Result | Status |
|---|------|---------|-----------------|--------|
| 47 | Run E2E tests | `npm run test:e2e:chromium` | All tests pass | ☐ |
| 48 | Unit tests | `npm run test:run` | All tests pass | ☐ |

---

## Phase 7: Edge Cases & Error Handling (30 min)

### 7.1 Authentication Edge Cases

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 49 | Unauthenticated access | Visit `/dashboard` without login | Redirect to login/onboarding | ☐ |
| 50 | Expired token | Simulate expired token | Graceful re-auth prompt | ☐ |
| 51 | Cancel OAuth | Cancel at Google consent | Handles gracefully | ☐ |

### 7.2 Network Error Handling

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 52 | Backend down | Stop backend, use frontend | Shows error message | ☐ |
| 53 | Slow network | Throttle network (DevTools) | Loading states work | ☐ |

### 7.3 Validation Edge Cases

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 54 | Empty folder name | Submit empty name | Validation error shown | ☐ |
| 55 | Invalid keywords | Submit invalid format | Validation error shown | ☐ |

---

## Phase 8: Mobile Responsiveness (15 min)

| # | Test | Action | Expected Result | Status |
|---|------|--------|-----------------|--------|
| 56 | Mobile viewport | DevTools → Toggle device toolbar | Layout responsive | ☐ |
| 57 | Touch targets | Check button sizes | ≥44x44px | ☐ |
| 58 | No horizontal scroll | Scroll horizontally | No overflow | ☐ |
| 59 | Text readable | Check font sizes | Readable without zoom | ☐ |

---

## Validation Summary

### Results

| Phase | Tests | Passed | Failed | Status |
|-------|-------|--------|--------|--------|
| 1. Backend Health | 7 | | | ☐ |
| 2. Frontend Health | 6 | | | ☐ |
| 3. Onboarding Flow | 24 | | | ☐ |
| 4. Dashboard | 5 | | | ☐ |
| 5. API Integration | 4 | | | ☐ |
| 6. E2E Tests | 2 | | | ☐ |
| 7. Edge Cases | 7 | | | ☐ |
| 8. Mobile | 4 | | | ☐ |
| **TOTAL** | **59** | | | |

### Pass Criteria

- **PASS**: 55+/59 tests pass (93%+), no CRITICAL failures
- **CONDITIONAL PASS**: 50-54/59 tests pass (85-93%), document issues for post-deploy fix
- **FAIL**: <50/59 tests pass (<85%) OR any CRITICAL test fails

### Critical Tests (Must Pass)

1. ☐ Gmail OAuth flow works end-to-end
2. ☐ Telegram linking completes successfully
3. ☐ Folder CRUD operations work
4. ☐ Dashboard loads after onboarding
5. ☐ E2E tests pass

---

## Issues Found

| # | Issue | Severity | Phase | Notes |
|---|-------|----------|-------|-------|
| 1 | **useAuthStatus response parsing** | CRITICAL | 3,4 | **FIXED** - Hook checked `response.data` but backend returns unwrapped response |
| 2 | Dashboard stats endpoint 404 | LOW | 4 | Expected - `/api/v1/dashboard/stats` not implemented yet. Non-blocking. |
| 3 | Gmail/Telegram shows "Disconnected" on dashboard | LOW | 4 | Cosmetic - related to missing stats endpoint. Auth status shows correct data. |

---

## Critical Bug Fix Details

### BUG-1: useAuthStatus Response Parsing (CRITICAL - FIXED)

**File**: `frontend/src/hooks/useAuthStatus.ts`

**Root Cause**:
The `useAuthStatus` hook was checking `response.data` but the backend `/api/v1/auth/status` endpoint returns data directly without a `data` wrapper.

**Symptoms**:
- Dashboard always redirected to `/onboarding` even for authenticated users
- Console showed: `response: {authenticated: true, user: Object}` followed by `No response.data, setting authenticated=false`

**Fix Applied**:
```typescript
// Before (broken):
if (response.data) {
  setIsAuthenticated(response.data.authenticated);
  setUser(response.data.user || null);
}

// After (fixed):
const authData = 'data' in response && response.data ? response.data : response;
if (authData && 'authenticated' in authData) {
  setIsAuthenticated(authData.authenticated);
  setUser(authData.user || null);
}
```

**Verification**: Dashboard now loads correctly after onboarding completion.

---

## Final Decision

After completing validation:

- [ ] **READY FOR DEPLOYMENT**: All critical tests pass, 55+/59 total
- [ ] **NEEDS FIXES**: Document issues, fix before deploy
- [ ] **BLOCKED**: Critical failures, cannot proceed

---

**Validation Started**: ____-__-__ __:__
**Validation Completed**: ____-__-__ __:__
**Total Time**: __ hours __ min
**Final Status**: ☐ PASS / ☐ FAIL

---

*Created by Bob (Scrum Master)*
*Mail Agent - Post-MVP Preparation Sprint*
*Full Local Validation Checklist*
