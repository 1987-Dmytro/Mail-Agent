# WCAG 2.1 Level AA Validation Checklist
**Story 4.8: End-to-End Onboarding Testing and Polish**
**AC 8, 13, 14, 15, 16: Accessibility Compliance**
**Date:** 2025-11-14

## Overview

This checklist ensures Mail Agent onboarding meets WCAG 2.1 Level AA accessibility standards. All critical criteria (A) and enhanced criteria (AA) must be validated.

**Target:** Lighthouse Accessibility Score ≥95

---

## 1. Perceivable (Users must be able to perceive the information)

### 1.1 Text Alternatives (Level A)

**Criterion 1.1.1: Non-text Content**

| Element | Requirement | Validation | Status |
|---|---|---|---|
| Logo images | Alt text describes purpose | `alt="Mail Agent Logo"` | ☐ Pass ☐ Fail |
| Icon buttons | aria-label describes action | `aria-label="Connect Gmail"` | ☐ Pass ☐ Fail |
| Decorative images | Empty alt or aria-hidden | `alt=""` or `aria-hidden="true"` | ☐ Pass ☐ Fail |
| Loading spinners | Descriptive aria-label | `aria-label="Loading..."` | ☐ Pass ☐ Fail |
| Success checkmarks | aria-label explains meaning | `aria-label="Successfully connected"` | ☐ Pass ☐ Fail |

**Test Method:** Inspect elements in browser DevTools, verify alt/aria-label present

### 1.3 Adaptable (Level A)

**Criterion 1.3.1: Info and Relationships**

| Element | Requirement | Validation | Status |
|---|---|---|---|
| Form labels | Associated with inputs via htmlFor | `<Label htmlFor="name">` + `<Input id="name">` | ☐ Pass ☐ Fail |
| Headings | Proper hierarchy (h1 → h2 → h3) | No skipped levels | ☐ Pass ☐ Fail |
| Lists | Use semantic `<ul>`/`<ol>` tags | Not `<div>` styled as lists | ☐ Pass ☐ Fail |
| Tables | Use `<th>`, `scope`, `<caption>` | Proper table structure | ☐ Pass ☐ Fail |

**Test Method:** Run axe DevTools extension, check for structural issues

**Criterion 1.3.2: Meaningful Sequence**

| Page | Requirement | Validation | Status |
|---|---|---|---|
| Onboarding | Content order makes sense when CSS disabled | Read top-to-bottom logically | ☐ Pass ☐ Fail |
| Dashboard | Stat cards readable in source order | Cards ordered logically in HTML | ☐ Pass ☐ Fail |

**Test Method:** Disable CSS in browser, verify content order

**Criterion 1.3.4: Orientation** (Level AA)

| Device | Requirement | Validation | Status |
|---|---|---|---|
| Mobile | Works in both portrait and landscape | Test rotation | ☐ Pass ☐ Fail |

**Test Method:** Test on physical device, rotate screen

### 1.4 Distinguishable (Level AA)

**Criterion 1.4.3: Contrast (Minimum)** ⭐ CRITICAL

| Element | Requirement | Tool | Status |
|---|---|---|---|
| Body text | 4.5:1 contrast ratio | Chrome DevTools / WebAIM | ☐ Pass ☐ Fail |
| Large text (18pt+) | 3:1 contrast ratio | Chrome DevTools / WebAIM | ☐ Pass ☐ Fail |
| UI components (buttons, inputs) | 3:1 contrast ratio | Chrome DevTools / WebAIM | ☐ Pass ☐ Fail |
| Focus indicators | 3:1 contrast against background | Chrome DevTools | ☐ Pass ☐ Fail |

**Specific Elements to Check:**
- [ ] Primary button text on primary background: ___:1 (need ≥4.5:1)
- [ ] Muted text (`text-muted-foreground`): ___:1 (need ≥4.5:1)
- [ ] Link text: ___:1 (need ≥4.5:1)
- [ ] Placeholder text: ___:1 (need ≥4.5:1)
- [ ] Error text: ___:1 (need ≥4.5:1)

**Test Method:** Use Chrome DevTools Accessibility panel, WebAIM Contrast Checker

**Criterion 1.4.10: Reflow** (Level AA)

| Viewport | Requirement | Validation | Status |
|---|---|---|---|
| 320px width | No horizontal scrolling | Test at 400% zoom | ☐ Pass ☐ Fail |

**Test Method:** Set browser zoom to 400%, verify no horizontal scroll

**Criterion 1.4.11: Non-text Contrast** (Level AA)

| Element | Requirement | Validation | Status |
|---|---|---|---|
| Button borders | 3:1 contrast | WebAIM checker | ☐ Pass ☐ Fail |
| Input borders | 3:1 contrast | WebAIM checker | ☐ Pass ☐ Fail |
| Focus indicators | 3:1 contrast | WebAIM checker | ☐ Pass ☐ Fail |

---

## 2. Operable (Users must be able to operate the interface)

### 2.1 Keyboard Accessible (Level A)

**Criterion 2.1.1: Keyboard** ⭐ CRITICAL

| Page | Requirement | Validation | Status |
|---|---|---|---|
| Onboarding | All functionality available via keyboard | Tab through all controls | ☐ Pass ☐ Fail |
| Dashboard | All interactions keyboard-accessible | No mouse-only features | ☐ Pass ☐ Fail |
| Folders | Create, edit, delete via keyboard | Test all CRUD operations | ☐ Pass ☐ Fail |

**Test Method:** Disconnect mouse, navigate entire app with keyboard only

**Criterion 2.1.2: No Keyboard Trap** ⭐ CRITICAL

| Component | Requirement | Validation | Status |
|---|---|---|---|
| Modal dialogs | Can exit with Escape key | Press Escape to close | ☐ Pass ☐ Fail |
| Dropdowns | Can close with Escape | Press Escape | ☐ Pass ☐ Fail |
| All interactive elements | Focus moves naturally | Tab through, verify no traps | ☐ Pass ☐ Fail |

**Test Method:** Tab through all components, ensure focus can always escape

### 2.4 Navigable (Level AA)

**Criterion 2.4.3: Focus Order** ⭐ CRITICAL

| Page | Requirement | Validation | Status |
|---|---|---|---|
| Onboarding Step 1 | Focus order: Title → Description → Button | Tab through, verify order | ☐ Pass ☐ Fail |
| Onboarding Step 2 | Focus order logical | Tab through | ☐ Pass ☐ Fail |
| Folder form | Focus: Name → Keywords → Color → Save → Cancel | Tab through | ☐ Pass ☐ Fail |

**Test Method:** Tab through page, verify focus order matches visual order

**Criterion 2.4.7: Focus Visible** (Level AA) ⭐ CRITICAL

| Element | Requirement | Validation | Status |
|---|---|---|---|
| Buttons | Visible focus ring | Tab to buttons, verify ring visible | ☐ Pass ☐ Fail |
| Links | Visible focus ring | Tab to links | ☐ Pass ☐ Fail |
| Inputs | Visible focus ring | Tab to inputs | ☐ Pass ☐ Fail |
| Custom components | Visible focus indicator | Tab to all interactive elements | ☐ Pass ☐ Fail |

**Test Method:** Tab through all interactive elements, verify visible focus indicator

**Criterion 2.4.1: Bypass Blocks** (Level A)

| Page | Requirement | Validation | Status |
|---|---|---|---|
| All pages | "Skip to main content" link | Tab first, verify skip link appears | ☐ Pass ☐ Fail ☐ N/A |

**Note:** Skip link may not be needed for single-step pages

---

## 3. Understandable (Information must be understandable)

### 3.1 Readable (Level A)

**Criterion 3.1.1: Language of Page**

| Page | Requirement | Validation | Status |
|---|---|---|---|
| All pages | `<html lang="en">` or `lang="de"` | Inspect HTML element | ☐ Pass ☐ Fail |

**Test Method:** View page source, check `<html>` tag

### 3.2 Predictable (Level A)

**Criterion 3.2.1: On Focus**

| Element | Requirement | Validation | Status |
|---|---|---|---|
| All inputs | Focus doesn't trigger auto-submit | Tab to inputs, verify no auto-submit | ☐ Pass ☐ Fail |
| All buttons | Focus doesn't trigger click | Tab to buttons | ☐ Pass ☐ Fail |

**Test Method:** Tab through form, verify focus alone doesn't trigger actions

### 3.3 Input Assistance (Level AA)

**Criterion 3.3.1: Error Identification** ⭐ CRITICAL

| Form | Requirement | Validation | Status |
|---|---|---|---|
| Folder creation | Required field errors shown | Submit empty, verify error message | ☐ Pass ☐ Fail |
| All forms | Error messages descriptive | Read error messages | ☐ Pass ☐ Fail |

**Criterion 3.3.2: Labels or Instructions** ⭐ CRITICAL

| Form Field | Requirement | Validation | Status |
|---|---|---|---|
| Folder name | Label present | `<Label htmlFor="name">` | ☐ Pass ☐ Fail |
| Keywords | Label + example provided | Label + help text | ☐ Pass ☐ Fail |
| All inputs | Labels or aria-label present | Inspect all inputs | ☐ Pass ☐ Fail |

**Test Method:** Inspect all form fields, verify labels present

**Criterion 3.3.3: Error Suggestion** (Level AA)

| Error | Requirement | Validation | Status |
|---|---|---|---|
| Invalid input | Suggestion provided | Test with invalid data | ☐ Pass ☐ Fail |

---

## 4. Robust (Content must be robust enough for assistive technologies)

### 4.1 Compatible (Level A)

**Criterion 4.1.2: Name, Role, Value** ⭐ CRITICAL

| Element | Requirement | Validation | Status |
|---|---|---|---|
| Custom buttons | `role="button"` + `aria-label` | Inspect custom buttons | ☐ Pass ☐ Fail |
| Toggle switches | `role="switch"` + `aria-checked` | Inspect switches | ☐ Pass ☐ Fail |
| Dialogs | `role="dialog"` + `aria-labelledby` | Inspect modals | ☐ Pass ☐ Fail |
| Alerts | `role="alert"` or `aria-live="polite"` | Inspect error messages | ☐ Pass ☐ Fail |

**Test Method:** Use axe DevTools, check for ARIA role issues

**Criterion 4.1.3: Status Messages** (Level AA)

| Message Type | Requirement | Validation | Status |
|---|---|---|---|
| Success toasts | `role="status"` or `aria-live="polite"` | Inspect toast component | ☐ Pass ☐ Fail |
| Error toasts | `role="alert"` or `aria-live="assertive"` | Inspect error toasts | ☐ Pass ☐ Fail |

---

## 5. Screen Reader Testing (AC 14)

**Test with:** VoiceOver (macOS) or NVDA (Windows)

### Onboarding Flow Test

| Step | Expected Announcement | Actual | Status |
|---|---|---|---|
| Page load | "Mail Agent Onboarding, Step 1 of 5" | | ☐ Pass ☐ Fail |
| Gmail button focus | "Connect Gmail, button" | | ☐ Pass ☐ Fail |
| Gmail success | "Gmail connected successfully" (auto-announced) | | ☐ Pass ☐ Fail |
| Telegram code | "Linking code: 123456" | | ☐ Pass ☐ Fail |
| Folder name input | "Folder name, edit text" | | ☐ Pass ☐ Fail |
| Save button | "Save folder, button" | | ☐ Pass ☐ Fail |
| Error message | "Error: Folder name is required" (auto-announced) | | ☐ Pass ☐ Fail |

### Dashboard Test

| Element | Expected Announcement | Actual | Status |
|---|---|---|---|
| Page load | "Dashboard, main content" | | ☐ Pass ☐ Fail |
| Gmail stat card | "Gmail: Connected, 127 emails processed" | | ☐ Pass ☐ Fail |
| Activity item | "Tax Return Documents sorted to Government, 1 hour ago" | | ☐ Pass ☐ Fail |

**Test Method:**
1. Enable screen reader (VoiceOver: Cmd+F5, NVDA: Ctrl+Alt+N)
2. Navigate using screen reader commands only
3. Verify all content is announced correctly
4. Check interactive elements announce their purpose

---

## 6. Keyboard-Only Navigation Testing (AC 15)

**Test:** Complete onboarding using only keyboard (no mouse)

| Action | Keys | Expected Behavior | Status |
|---|---|---|---|
| Navigate forward | Tab | Focus moves to next element | ☐ Pass ☐ Fail |
| Navigate backward | Shift+Tab | Focus moves to previous element | ☐ Pass ☐ Fail |
| Activate button | Enter or Space | Button activated | ☐ Pass ☐ Fail |
| Close dialog | Escape | Dialog closes | ☐ Pass ☐ Fail |
| Submit form | Enter (in input) | Form submitted | ☐ Pass ☐ Fail |
| Select dropdown | Arrow keys | Options navigated | ☐ Pass ☐ Fail |
| Toggle switch | Space | Switch toggled | ☐ Pass ☐ Fail |

**Full Flow Test:**
1. Load `/onboarding` page
2. Tab to "Connect Gmail" button
3. Press Enter to activate
4. (Simulate OAuth success)
5. Tab to "Next" button, press Enter
6. Tab through Telegram step
7. Tab to folder form, fill with keyboard only
8. Tab to "Save", press Enter
9. Complete entire wizard without touching mouse

**Success Criteria:**
- [ ] All interactive elements reachable via Tab
- [ ] Focus order is logical
- [ ] All elements have visible focus indicator
- [ ] All actions work with Enter/Space
- [ ] No keyboard traps
- [ ] Can complete entire onboarding with keyboard only

---

## 7. Mobile Responsiveness Testing (AC 8)

**Test Devices:**
- iPhone SE (375px width)
- iPhone 12 (390px width)
- Samsung Galaxy S21 (360px width)
- iPad (768px width)

### Touch Target Size

| Element | Minimum Size | Actual | Status |
|---|---|---|---|
| Buttons | 44x44px | | ☐ Pass ☐ Fail |
| Links | 44x44px | | ☐ Pass ☐ Fail |
| Inputs | 44px height | | ☐ Pass ☐ Fail |
| Icons | 24x24px (with 44x44px tap area) | | ☐ Pass ☐ Fail |

**Test Method:** Use browser DevTools device emulation, measure elements

### Layout Tests

| Viewport | Test | Expected | Status |
|---|---|---|---|
| < 640px | Single column layout | Cards stack vertically | ☐ Pass ☐ Fail |
| < 640px | No horizontal scroll | `overflow-x: hidden` | ☐ Pass ☐ Fail |
| < 640px | Text readable | Font size ≥16px | ☐ Pass ☐ Fail |
| < 640px | Forms usable | Inputs full-width | ☐ Pass ☐ Fail |
| 768px+ | Grid layout | 2+ columns | ☐ Pass ☐ Fail |

---

## 8. Browser Compatibility Testing (AC 9)

**Test Browsers:**

| Browser | Version | Platform | Critical Features | Status |
|---|---|---|---|---|
| Chrome | Latest | macOS/Windows | OAuth, Forms, Buttons | ☐ Pass ☐ Fail |
| Firefox | Latest | macOS/Windows | OAuth, Forms, Buttons | ☐ Pass ☐ Fail |
| Safari | 15+ | macOS/iOS | OAuth, Forms, Buttons | ☐ Pass ☐ Fail |
| Edge | Latest | Windows | OAuth, Forms, Buttons | ☐ Pass ☐ Fail |

**Test Checklist Per Browser:**
- [ ] OAuth redirect works
- [ ] Forms submit correctly
- [ ] Buttons respond to clicks
- [ ] Toasts/notifications display
- [ ] Drag-drop works (folder reorder)
- [ ] CSS layout renders correctly
- [ ] No console errors

---

## 9. Automated Testing Tools

**Run These Tools:**

### Lighthouse (Chrome DevTools)
```bash
Target: Accessibility Score ≥95

1. Open Chrome DevTools (F12)
2. Navigate to Lighthouse tab
3. Select "Accessibility" category
4. Run audit
5. Fix all issues with "serious" or "critical" severity
```

**Expected Results:**
- Accessibility score: ≥95
- Contrast issues: 0
- ARIA issues: 0
- Form issues: 0

### axe DevTools Extension
```bash
1. Install axe DevTools extension
2. Navigate to each onboarding page
3. Click "Scan ALL of my page"
4. Fix all "Critical" and "Serious" issues
```

### WAVE Extension
```bash
1. Install WAVE extension
2. Navigate to each page
3. Review errors (red icons)
4. Fix all errors
```

---

## 10. Final Validation Checklist

Before marking AC 8, 13, 14, 15, 16 complete:

- [ ] Lighthouse accessibility score ≥95 on all pages
- [ ] All color contrast ratios meet WCAG AA (≥4.5:1 text, ≥3:1 UI)
- [ ] All form inputs have proper labels
- [ ] All images have alt text
- [ ] All icons have aria-labels
- [ ] Complete onboarding with keyboard only (no mouse)
- [ ] Complete onboarding with screen reader only
- [ ] Touch targets ≥44x44px on mobile
- [ ] No horizontal scrolling on mobile (320px width)
- [ ] Tested on Chrome, Firefox, Safari, Edge
- [ ] All automated tools (Lighthouse, axe, WAVE) show no critical issues
- [ ] Documented all accessibility features in user guide

---

**Validation Completed By:** _________________
**Date:** _________________
**Lighthouse Score:** _____ / 100
**Critical Issues Found:** _____
**All Issues Resolved:** ☐ Yes ☐ No
