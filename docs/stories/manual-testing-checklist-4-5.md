# Manual Testing Checklist - Story 4.5: Notification Preferences Settings

## Pre-requisites
- [ ] Backend API running on http://localhost:8000
- [ ] Frontend dev server running (`npm run dev`)
- [ ] User authenticated with JWT token
- [ ] Telegram bot connected to user account

## Test Environment Setup
```bash
cd frontend
npm run dev
# Navigate to http://localhost:3000/settings/notifications
```

## Acceptance Criteria Validation

### AC-1: Settings Page Route Exists
- [ ] Navigate to `/settings/notifications`
- [ ] Page loads without errors
- [ ] URL matches exactly: `http://localhost:3000/settings/notifications`
- [ ] Page title displays: "Notification Preferences"

**Expected Result**: Page loads successfully with heading "Notification Preferences"

---

### AC-2: Batch Notification Toggle
- [ ] Locate "Enable batch notifications" switch
- [ ] Toggle switch OFF
- [ ] Verify "Batch notification time" selector disappears
- [ ] Toggle switch back ON
- [ ] Verify "Batch notification time" selector reappears

**Expected Result**: Batch time selector visibility controlled by toggle state

---

### AC-3: Batch Time Selector Options
- [ ] Ensure batch toggle is ON
- [ ] Click "Batch notification time" dropdown
- [ ] Verify dropdown contains exactly 4 options:
  - Morning (08:00)
  - End of day (18:00)
  - Noon (12:00)
  - Evening (20:00)
- [ ] Select "Morning (08:00)"
- [ ] Verify selection updates to "Morning (08:00)"

**Expected Result**: Dropdown contains 4 time options, selection updates correctly

---

### AC-4: Priority Immediate Toggle
- [ ] Locate "Immediate priority notifications" switch
- [ ] Toggle switch OFF
- [ ] Verify warning appears: "⚠️ All emails will wait for batch notification time"
- [ ] Verify confidence threshold slider disappears
- [ ] Toggle switch back ON
- [ ] Verify warning disappears
- [ ] Verify confidence threshold slider reappears

**Expected Result**: Warning shows when disabled, confidence slider visibility controlled by toggle

---

### AC-5: Quiet Hours Toggle
- [ ] Locate "Enable quiet hours" switch
- [ ] Toggle switch OFF
- [ ] Verify quiet hours time pickers disappear
- [ ] Toggle switch back ON
- [ ] Verify quiet hours time pickers reappear (Start and End)

**Expected Result**: Time pickers visibility controlled by toggle state

---

### AC-6: Test Notification Button
- [ ] Ensure Telegram is connected
- [ ] Click "Send Test Notification" button
- [ ] Verify button shows "Sending..." during API call
- [ ] Verify toast notification appears with message: "Test notification sent! Check your Telegram. (Sent at HH:MM)"
- [ ] Check Telegram app for test notification message
- [ ] Verify button returns to "Send Test Notification" after completion

**Expected Result**: Button disabled during send, success toast appears, Telegram receives notification

---

### AC-7: Form Submission and Disable State
- [ ] Modify any setting (e.g., change batch time)
- [ ] Click "Save Preferences" button
- [ ] Verify both buttons disable during submission:
  - "Save Preferences" → "Saving..."
  - "Send Test Notification" → disabled
- [ ] Wait for API response
- [ ] Verify success toast: "Notification preferences updated!"
- [ ] Verify buttons re-enable after completion

**Expected Result**: Both buttons disable during save, success toast appears, buttons re-enable

---

### AC-8: Quiet Hours Validation
#### Test 1: Same Start and End Time (Invalid)
- [ ] Set quiet hours start: "10:00"
- [ ] Set quiet hours end: "10:00"
- [ ] Click "Save Preferences"
- [ ] Verify error message appears: "Quiet hours end time must be different from start time"
- [ ] Verify form does NOT submit

**Expected Result**: Validation error prevents submission

#### Test 2: Overnight Range (Valid)
- [ ] Set quiet hours start: "22:00"
- [ ] Set quiet hours end: "08:00"
- [ ] Click "Save Preferences"
- [ ] Verify NO validation error appears
- [ ] Verify form submits successfully
- [ ] Verify success toast appears

**Expected Result**: Overnight range accepted as valid, form submits

#### Test 3: Same-Day Range (Valid)
- [ ] Set quiet hours start: "08:00"
- [ ] Set quiet hours end: "22:00"
- [ ] Click "Save Preferences"
- [ ] Verify NO validation error appears
- [ ] Verify form submits successfully

**Expected Result**: Same-day range accepted as valid, form submits

---

### AC-9: Default Settings on First Load
- [ ] Clear browser localStorage (if applicable)
- [ ] Refresh page `/settings/notifications`
- [ ] Verify blue banner appears: "Default settings applied"
- [ ] Verify default values loaded:
  - [ ] Batch enabled: ON
  - [ ] Batch time: "End of day (18:00)"
  - [ ] Quiet hours enabled: ON
  - [ ] Quiet hours start: "22:00"
  - [ ] Quiet hours end: "08:00"
  - [ ] Priority immediate: ON
  - [ ] Confidence threshold: 70%

**Expected Result**: Default banner visible, all defaults pre-populated

---

### AC-10: Preferences Persistence
- [ ] Modify settings:
  - [ ] Change batch time to "Morning (08:00)"
  - [ ] Change quiet hours to "23:00 - 07:00"
  - [ ] Set confidence to 80%
- [ ] Click "Save Preferences"
- [ ] Wait for success toast
- [ ] Navigate away (e.g., to `/settings/folders`)
- [ ] Navigate back to `/settings/notifications`
- [ ] Verify all modified settings persisted:
  - [ ] Batch time: "Morning (08:00)"
  - [ ] Quiet hours: "23:00 - 07:00"
  - [ ] Confidence: 80%

**Expected Result**: Settings persist across navigation

---

### AC-11: Visual Consistency
- [ ] Verify all cards use consistent styling (border, rounded corners, shadow)
- [ ] Verify toggle switches match design system (blue when ON, gray when OFF)
- [ ] Verify buttons use consistent primary/secondary colors
- [ ] Verify typography matches other settings pages (folder management)
- [ ] Verify responsive layout (test at 1024px, 768px, 375px widths)
- [ ] Verify dark theme applies correctly (background, text, borders)

**Expected Result**: Visual design matches existing Mail Agent design system

---

## Error Handling Tests

### Network Error Handling
- [ ] Stop backend API server
- [ ] Click "Save Preferences"
- [ ] Verify error toast appears: "Failed to save preferences. Please try again."
- [ ] Verify buttons re-enable after error
- [ ] Restart backend API
- [ ] Click "Save Preferences" again
- [ ] Verify success toast appears

**Expected Result**: Network errors handled gracefully with user-friendly messages

---

### API 401 Error (Unauthorized)
- [ ] Remove JWT token from localStorage
- [ ] Click "Save Preferences"
- [ ] Verify redirect to login page OR error toast appears

**Expected Result**: Unauthorized state handled gracefully

---

## Accessibility Tests

### Keyboard Navigation
- [ ] Tab through all form controls
- [ ] Verify focus indicators visible on all elements
- [ ] Press Enter on "Save Preferences" button (should submit)
- [ ] Press Space on toggle switches (should toggle)

**Expected Result**: All controls accessible via keyboard

---

### Screen Reader Compatibility
- [ ] Enable screen reader (VoiceOver on Mac, NVDA on Windows)
- [ ] Navigate through form
- [ ] Verify labels announced correctly for all inputs
- [ ] Verify toggle states announced ("on" vs "off")
- [ ] Verify error messages announced when validation fails

**Expected Result**: All elements have proper ARIA labels and semantic HTML

---

## Performance Tests

### Initial Load Performance
- [ ] Open browser DevTools → Network tab
- [ ] Navigate to `/settings/notifications`
- [ ] Measure page load time (should be < 2 seconds)
- [ ] Verify API calls:
  - [ ] GET `/api/v1/settings/notifications` called once
  - [ ] Response time < 500ms

**Expected Result**: Page loads quickly, minimal API calls

---

### Form Submission Performance
- [ ] Click "Save Preferences"
- [ ] Measure API call duration (should be < 1 second)
- [ ] Verify UI remains responsive during submission

**Expected Result**: Form submission fast and responsive

---

## Browser Compatibility

Test in the following browsers:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

For each browser:
- [ ] Page renders correctly
- [ ] All form controls work
- [ ] Validation messages display
- [ ] Toast notifications appear
- [ ] No console errors

---

## Mobile Responsiveness

### Test on Mobile Viewports
- [ ] 375px width (iPhone SE)
- [ ] 768px width (iPad)
- [ ] 1024px width (iPad Pro)

For each viewport:
- [ ] Layout adapts correctly
- [ ] Cards stack vertically on narrow screens
- [ ] Buttons full-width on mobile
- [ ] Text remains readable
- [ ] Touch targets at least 44px × 44px

---

## Test Summary

**Total Tests**: 11 AC + 15 additional checks = 26 tests
**Estimated Testing Time**: 30-45 minutes
**Required Tools**: Browser DevTools, Telegram app

---

## Sign-Off

- [ ] All acceptance criteria validated
- [ ] All error states tested
- [ ] All edge cases covered
- [ ] Documentation reviewed
- [ ] Ready for code review

**Tester Name**: ___________________
**Date**: ___________________
**Status**: ☐ PASS  ☐ FAIL
**Notes**: _______________________________________
