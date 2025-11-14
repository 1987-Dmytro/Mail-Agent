# Manual Testing Checklist - Story 4-7: Dashboard Overview Page

**Story**: 4-7-dashboard-overview-page
**Date**: 2025-11-12
**Tester**: [Pending Manual Verification]

## Prerequisites

- ✅ Backend API running on http://localhost:8000
- ✅ Frontend running on http://localhost:3000
- ✅ User account created with onboarding completed
- ✅ Gmail and Telegram connected
- ✅ At least 1 email processed for testing activity feed

## Test Scenarios

### 1. Dashboard Loads and Displays Stats (AC: 3, 12)

**Steps:**
1. Navigate to http://localhost:3000/dashboard after login
2. Observe loading skeleton appears briefly
3. Wait for data to load

**Expected Results:**
- [ ] Dashboard skeleton displays during loading (gray placeholders)
- [ ] All 4 email statistics cards render:
  - [ ] "Total Processed" card with number
  - [ ] "Pending Approval" card with number
  - [ ] "Auto-Sorted" card with number
  - [ ] "Responses Sent" card with number
- [ ] Time Saved card displays:
  - [ ] Today's minutes saved (e.g., "25 min")
  - [ ] Total time saved in hours/minutes (e.g., "2h 30m")
- [ ] Page loads in < 2 seconds

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

### 2. Connection Status Display (AC: 2, 14)

**Steps:**
1. View the Gmail and Telegram connection status cards
2. Verify green "Connected" badges appear
3. Disconnect Gmail via backend (optional)
4. Refresh dashboard

**Expected Results:**
- [ ] Gmail connection card shows "Connected" with green indicator
- [ ] Telegram connection card shows "Connected" with green indicator
- [ ] Last sync time displays for Gmail (e.g., "2 minutes ago")
- [ ] When disconnected, red "Disconnected" badge appears
- [ ] "Reconnect Gmail" button appears when Gmail disconnected
- [ ] "Reconnect Telegram" button appears when Telegram disconnected

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

### 3. Recent Activity Feed (AC: 4)

**Steps:**
1. Scroll to "Recent Activity" section
2. Verify activity items display correctly
3. Check timestamps and icons

**Expected Results:**
- [ ] Recent Activity card shows last 10 email actions
- [ ] Each activity item shows:
  - [ ] Icon (blue folder for sorted, green arrow for sent, red X for rejected)
  - [ ] Email subject (truncated if > 50 chars with "...")
  - [ ] Folder name badge (for sorted items only)
  - [ ] Relative timestamp (e.g., "5 minutes ago")
- [ ] If no activity, displays "No recent activity" message
- [ ] Activity items are sorted by timestamp (newest first)

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

### 4. Auto-Refresh Functionality (AC: 11)

**Steps:**
1. Open dashboard and note current "Total Processed" count
2. Wait 30 seconds without any interaction
3. Observe if data refreshes automatically
4. Manually click "Refresh" button

**Expected Results:**
- [ ] Data automatically refreshes every 30 seconds
- [ ] No full page reload occurs during auto-refresh
- [ ] Stats update smoothly without layout shift
- [ ] Manual "Refresh" button triggers immediate data reload
- [ ] Toast notification "Dashboard refreshed" appears on manual refresh

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

### 5. System Health Indicator (AC: 5)

**Steps:**
1. View the alert banner at top of dashboard
2. Test different connection states:
   - Both Gmail and Telegram connected
   - Only Gmail connected
   - Both disconnected

**Expected Results:**
- [ ] **All Connected**: Green alert with "All systems operational" message
- [ ] **One Disconnected**: Yellow alert with "Minor issues detected" message
- [ ] **Both Disconnected**: Red alert with "Service disruption" message
- [ ] Alert includes reconnection instructions

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

### 6. Quick Actions Section (AC: 8, 9)

**Steps:**
1. Scroll to "Quick Actions" card
2. Click each button to verify navigation

**Expected Results:**
- [ ] "Manage Folders" button navigates to `/settings/folders`
- [ ] "Update Settings" button navigates to `/settings/notifications`
- [ ] "View Full Stats" button is disabled with "Coming soon" tooltip
- [ ] All buttons have clear icons and labels

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

### 7. Helpful Tips for New Users (AC: 10)

**Steps:**
1. Create a new test user account
2. Complete onboarding
3. Navigate to dashboard
4. Click "Dismiss" button on tips card

**Expected Results:**
- [ ] Tips card displays for new users (< 7 days since registration)
- [ ] Tips include:
  - [ ] "Your first email will arrive soon!" message
  - [ ] Link to customize folder categories
  - [ ] Link to documentation
- [ ] "Dismiss" button hides the tips card
- [ ] Toast "Tips dismissed" appears on dismiss

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

### 8. Error Handling (AC: 13)

**Steps:**
1. Stop backend API server
2. Refresh dashboard
3. Observe error handling
4. Restart backend
5. Click "Retry" in error toast

**Expected Results:**
- [ ] Error toast appears: "Failed to load dashboard stats"
- [ ] Toast includes "Retry" button
- [ ] Clicking "Retry" attempts to reload data
- [ ] Dashboard remains functional (no crashes)
- [ ] When backend restored, retry successfully loads data

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

### 9. Responsive Design (AC: 7)

**Steps:**
1. Resize browser window to different widths:
   - Desktop (1200px+)
   - Tablet (768px-1199px)
   - Mobile (< 768px)

**Expected Results:**
- [ ] **Desktop**: 3-column grid for stats, 2-column for other sections
- [ ] **Tablet**: 2-column grid for most sections
- [ ] **Mobile**: Single column layout, all cards stacked vertically
- [ ] All text remains readable at all sizes
- [ ] No horizontal scrolling
- [ ] Touch targets ≥ 44x44px on mobile

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

### 10. Authentication & Security (AC: 1, 15)

**Steps:**
1. Log out of application
2. Attempt to navigate to `/dashboard` directly
3. Log back in
4. Complete onboarding if required
5. Check browser console for sensitive data

**Expected Results:**
- [ ] Unauthenticated users redirected to `/login`
- [ ] Users with incomplete onboarding redirected to `/onboarding`
- [ ] No JWT tokens visible in browser console logs
- [ ] No email content logged to console (only IDs)
- [ ] Dashboard only accessible after authentication

**Result**: ☐ Pass ☐ Fail
**Notes**: _____________________

---

## Cross-Browser Testing

Test on the following browsers:

- [ ] Chrome/Chromium (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

**Notes**: _____________________

---

## Performance Testing

- [ ] Dashboard loads in < 2 seconds on average connection
- [ ] Auto-refresh does not cause performance degradation
- [ ] No memory leaks after 5+ minutes of usage
- [ ] Smooth scrolling on mobile devices

**Notes**: _____________________

---

## Accessibility Testing

- [ ] All interactive elements keyboard accessible (Tab navigation)
- [ ] Screen reader announces all card titles and values
- [ ] Color contrast meets WCAG AA standards
- [ ] Focus indicators visible on all interactive elements

**Notes**: _____________________

---

## Overall Assessment

**Total Tests**: 10 scenarios
**Passed**: ___
**Failed**: ___
**Blocked**: ___

**Overall Result**: ☐ Pass ☐ Fail

**Summary**:
_____________________

**Recommendations**:
_____________________

**Tested By**: _____________________
**Date**: _____________________
