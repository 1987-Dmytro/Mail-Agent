# Visual Design Polish & Loading States Guide
**Story 4.8: End-to-End Onboarding Testing and Polish**
**Tasks 3.2 & 3.3: Visual Polish + Loading/Error Message Improvements (AC 6, 7)**
**Date:** 2025-11-14

## Overview

This document provides comprehensive guidelines for visual consistency, loading states, and error message improvements across the Mail Agent onboarding experience.

**Goals:**
- AC 6: Visual design polished (consistent spacing, colors, typography)
- AC 7: Loading states and error messages improved for clarity
- Ensure professional, cohesive visual experience
- Reduce user anxiety during async operations

---

## Part 1: Visual Design Polish (AC 6)

### 1.1 Spacing & Layout Consistency

**Card Spacing Standards:**
```css
/* Use Tailwind spacing tokens consistently */
- Card padding: p-6 (24px)
- Card gap between elements: space-y-4 (16px)
- Button spacing: space-x-2 (8px) for inline, space-y-3 (12px) for stacked
- Section margins: mb-6 (24px) between major sections
```

**Current Issues to Fix:**
| Component | Issue | Fix |
|---|---|---|
| GmailConnect | Inconsistent button padding | Use `size="lg"` prop consistently |
| TelegramLink | Card content padding varies | Standardize to `pt-6` |
| FolderManager | List item spacing inconsistent | Use `space-y-3` for all lists |
| Dashboard | Stat card gaps vary | Standardize to `gap-4` in grid |

**Layout Grid Standards:**
```typescript
// Desktop (≥768px)
- Main content: max-w-3xl mx-auto
- Cards: max-w-md mx-auto for single cards
- Grids: grid-cols-2 md:grid-cols-4 for stat cards

// Mobile (<768px)
- Single column layout
- Full width cards with p-4 padding
- Reduced vertical spacing (space-y-3 instead of space-y-4)
```

### 1.2 Color Consistency

**Primary Color Usage:**
```typescript
// Use design tokens from Tailwind config
Primary actions: bg-primary text-primary-foreground
Secondary actions: bg-secondary text-secondary-foreground
Destructive actions: bg-destructive text-destructive-foreground
```

**Semantic Colors:**
| State | Background | Text | Border | Use Case |
|---|---|---|---|---|
| Success | bg-green-50 | text-green-700 | border-green-200 | Success messages, checkmarks |
| Error | bg-destructive/10 | text-destructive | border-destructive/50 | Error alerts, validation |
| Warning | bg-yellow-50 | text-yellow-700 | border-yellow-200 | Warnings, cautions |
| Info | bg-blue-50 | text-blue-700 | border-blue-200 | Informational messages |
| Neutral | bg-muted | text-muted-foreground | border-border | Default states |

**Current Issues to Fix:**
- Gmail success checkmark: Ensure consistent green (`bg-green-500`)
- Error alerts: Use `bg-destructive/10` instead of `bg-red-100`
- Button states: Ensure `:hover` and `:active` states use design tokens
- Focus rings: Use `focus-visible:ring-2 focus-visible:ring-primary`

### 1.3 Typography Consistency

**Heading Hierarchy:**
```typescript
// Component card titles
<CardTitle className="text-xl font-semibold">Title</CardTitle>

// Section headings
<h2 className="text-2xl font-bold mb-4">Section</h2>

// Subsection headings
<h3 className="text-lg font-medium mb-2">Subsection</h3>

// Body text
<p className="text-base">Regular text</p>

// Helper text
<p className="text-sm text-muted-foreground">Helper text</p>

// Labels
<label className="text-sm font-medium">Label</label>
```

**Line Height Standards:**
- Headings: `leading-tight` (1.25)
- Body text: `leading-normal` (1.5)
- Buttons: `leading-none` (1)

**Current Issues to Fix:**
- Inconsistent font weights in card titles (some `font-semibold`, some `font-bold`)
- Missing `leading-*` classes on some text elements
- Helper text sometimes uses `text-gray-500` instead of `text-muted-foreground`

### 1.4 Button Consistency

**Button Variants:**
```typescript
// Primary action (main CTA)
<Button size="lg" className="w-full">Primary Action</Button>

// Secondary action
<Button variant="secondary" size="default">Secondary</Button>

// Destructive action
<Button variant="destructive">Delete</Button>

// Ghost/subtle action
<Button variant="ghost">Cancel</Button>

// Link-style action
<Button variant="link">Learn More</Button>
```

**Button Sizing:**
```typescript
size="sm" // 32px height, text-sm
size="default" // 40px height, text-base
size="lg" // 48px height, text-base
```

**Current Issues to Fix:**
- Mix of `size="lg"` and `size="default"` for primary actions
- Inconsistent button widths (`w-full` vs `w-auto`)
- Missing disabled states on some buttons

### 1.5 Icon Consistency

**Icon Sizing:**
```typescript
// In buttons
<Icon className="w-4 h-4 mr-2" />

// In cards/headers
<Icon className="w-6 h-6" />

// Large icons (loading, success states)
<Icon className="w-12 h-12" />
```

**Icon Colors:**
- Follow parent text color (inherit)
- Or use semantic colors (`text-green-500` for success)

**Current Issues to Fix:**
- Icon sizes vary (`w-5 h-5` vs `w-6 h-6`)
- Some icons missing `mr-2` spacing in buttons
- Inconsistent icon stroke width

### 1.6 Form Element Consistency

**Input Fields:**
```typescript
// Standard input
<Input
  type="text"
  placeholder="Enter..."
  className="w-full"
/>

// With label
<div className="space-y-2">
  <Label htmlFor="field">Label</Label>
  <Input id="field" />
</div>

// With error
<div className="space-y-2">
  <Input className="border-destructive" />
  <p className="text-sm text-destructive">Error message</p>
</div>
```

**Select/Dropdown:**
```typescript
<Select>
  <SelectTrigger className="w-full">
    <SelectValue placeholder="Select..." />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="option1">Option 1</SelectItem>
  </SelectContent>
</Select>
```

**Switches/Toggles:**
```typescript
<div className="flex items-center justify-between">
  <Label htmlFor="toggle">Setting</Label>
  <Switch id="toggle" />
</div>
```

### 1.7 Animation & Transitions

**Standard Transitions:**
```css
/* Button hover */
transition-colors duration-200

/* Card elevation */
transition-shadow duration-200

/* Slide-in */
transition-transform duration-300 ease-in-out

/* Fade-in */
transition-opacity duration-200
```

**Loading Spinner:**
```typescript
<Loader2 className="w-8 h-8 animate-spin text-primary" />
```

**Success Checkmark:**
```typescript
// Animated checkmark (using framer-motion or CSS)
<div className="animate-scale-in">
  <Check className="w-8 h-8 text-white" />
</div>
```

**Current Issues to Fix:**
- Some buttons missing `transition-colors`
- Wizard step transitions not smooth
- Toast notifications appear/disappear too abruptly

---

## Part 2: Loading States (AC 7)

### 2.1 Loading State Principles

**Guidelines:**
1. **Show loading immediately** (no delay)
2. **Indicate progress** when possible
3. **Set expectations** (what's happening, how long)
4. **Prevent user actions** during loading (disable buttons)
5. **Show skeleton loading** for content areas

### 2.2 Button Loading States

**Standard Button Loading:**
```typescript
<Button disabled={isLoading}>
  {isLoading ? (
    <>
      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
      Processing...
    </>
  ) : (
    'Submit'
  )}
</Button>
```

**Implementation Checklist:**
- [ ] Gmail "Connect" button shows spinner during OAuth
- [ ] Telegram "Generate Code" button shows spinner
- [ ] Folder "Save" button shows spinner during API call
- [ ] Preferences "Save" button shows spinner
- [ ] All submit buttons disabled during loading

### 2.3 Page/Card Loading States

**Full Page Loading:**
```typescript
<div className="flex items-center justify-center min-h-screen">
  <div className="text-center space-y-4">
    <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto" />
    <p className="text-muted-foreground">Loading your dashboard...</p>
  </div>
</div>
```

**Card Loading:**
```typescript
<Card>
  <CardContent className="pt-6 flex flex-col items-center justify-center space-y-4 min-h-[200px]">
    <Loader2 className="w-12 h-12 animate-spin text-primary" />
    <p className="text-muted-foreground">Connecting to Gmail...</p>
  </CardContent>
</Card>
```

**Skeleton Loading (Dashboard):**
```typescript
<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
  {[1, 2, 3, 4].map((i) => (
    <Card key={i}>
      <CardContent className="pt-6">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-muted rounded w-3/4"></div>
          <div className="h-8 bg-muted rounded w-1/2"></div>
        </div>
      </CardContent>
    </Card>
  ))}
</div>
```

### 2.4 Specific Loading States by Component

**Gmail OAuth Flow:**
```typescript
// Initial state
"Connect Gmail" button enabled

// After click (redirect starting)
<Loader2 className="w-4 h-4 mr-2 animate-spin" />
"Redirecting to Google..."

// After OAuth callback (processing code)
<Card loading state>
"Connecting your Gmail account..."

// Success state
<Check icon with green background>
"Gmail Connected!"
```

**Telegram Linking:**
```typescript
// Generating code
<Loader2 />
"Generating linking code..."

// Code displayed, waiting for verification
<Loader2 /> (subtle spinner)
"Waiting for confirmation from Telegram..."

// Success
<Check icon>
"Telegram linked!"
```

**Folder Creation:**
```typescript
// Saving folder
Button: <Loader2 /> "Saving..."

// After save
Toast: "Folder created!"
```

**Dashboard Data Loading:**
```typescript
// Initial load
<Skeleton cards>

// Refreshing (SWR)
<Subtle spinner in corner>
No full-page loading
```

### 2.5 Progress Indicators

**Wizard Progress Bar:**
```typescript
<div className="w-full bg-muted rounded-full h-2">
  <div
    className="bg-primary h-2 rounded-full transition-all duration-300"
    style={{ width: `${(currentStep / totalSteps) * 100}%` }}
  />
</div>
```

**Current Issues to Fix:**
- [ ] Gmail OAuth redirect has no loading indicator
- [ ] Telegram code generation shows no progress
- [ ] Folder save button doesn't show loading state
- [ ] Dashboard initial load has no skeleton

---

## Part 3: Error Message Improvements (AC 7)

### 3.1 Error Display Patterns

**Toast Error (Transient):**
```typescript
toast.error("Connection failed. Please try again.");
```

**Inline Error (Form Validation):**
```typescript
<div className="space-y-2">
  <Input className="border-destructive" />
  <p className="text-sm text-destructive">
    This field is required
  </p>
</div>
```

**Alert Error (Persistent):**
```typescript
<Alert variant="destructive">
  <AlertCircle className="h-4 w-4" />
  <AlertDescription>
    <strong>Connection Error</strong>
    <p className="mt-1">
      Unable to connect to Gmail. Check your internet and try again.
    </p>
    <Button variant="outline" size="sm" className="mt-2">
      Retry
    </Button>
  </AlertDescription>
</Alert>
```

### 3.2 Error Message Components

**Standard Error Alert:**
```typescript
interface ErrorAlertProps {
  title: string;
  message: string;
  onRetry?: () => void;
  recoveryHint?: string;
}

export function ErrorAlert({ title, message, onRetry, recoveryHint }: ErrorAlertProps) {
  return (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertDescription>
        <p className="font-semibold">{title}</p>
        <p className="mt-1 text-sm">{message}</p>
        {recoveryHint && (
          <p className="mt-2 text-sm text-muted-foreground">
            💡 {recoveryHint}
          </p>
        )}
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={onRetry}
          >
            Try Again
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}
```

**Usage:**
```typescript
<ErrorAlert
  title="Connection Failed"
  message="Unable to connect to Gmail."
  recoveryHint="Make sure you're connected to the internet"
  onRetry={() => retryOAuthFlow()}
/>
```

### 3.3 Error Recovery Actions

**All errors should provide:**
1. **Clear description** of what went wrong
2. **Likely cause** (if known)
3. **Next step** (retry button, troubleshooting link)

**Example Error States:**
```typescript
// Network error
<ErrorAlert
  title="No Internet Connection"
  message="Check your wifi or cellular data"
  onRetry={retryRequest}
/>

// API failure
<ErrorAlert
  title="Something Went Wrong"
  message="We're having trouble connecting to our servers"
  recoveryHint="Try again in a few minutes"
  onRetry={retryRequest}
/>

// Validation error
<p className="text-sm text-destructive">
  Folder name is required
</p>

// Timeout error
<ErrorAlert
  title="This is Taking Too Long"
  message="The connection timed out"
  recoveryHint="Check your internet speed"
  onRetry={retryRequest}
/>
```

### 3.4 Empty States

**No Data Yet:**
```typescript
<div className="text-center py-12 space-y-3">
  <div className="mx-auto w-16 h-16 rounded-full bg-muted flex items-center justify-center">
    <Icon className="w-8 h-8 text-muted-foreground" />
  </div>
  <p className="text-lg font-medium">No folders yet</p>
  <p className="text-sm text-muted-foreground">
    Create your first folder to get started
  </p>
  <Button onClick={openCreateDialog}>
    Create Folder
  </Button>
</div>
```

---

## Part 4: Implementation Checklist

### Visual Polish (AC 6)
- [ ] Audit all components for spacing consistency
- [ ] Ensure all colors use design tokens
- [ ] Fix typography hierarchy issues
- [ ] Standardize button sizes and variants
- [ ] Verify icon sizing across components
- [ ] Add smooth transitions to interactive elements
- [ ] Test visual consistency across all wizard steps
- [ ] Verify mobile responsive layout
- [ ] Check dark mode compatibility (if applicable)

### Loading States (AC 7)
- [ ] Add loading spinners to all async buttons
- [ ] Implement skeleton loading for dashboard
- [ ] Add progress indicators to wizard
- [ ] Show loading messages during OAuth
- [ ] Add loading state to Telegram verification
- [ ] Disable interactions during loading
- [ ] Add subtle loading for background refreshes
- [ ] Test loading states on slow connections

### Error Messages (AC 7)
- [ ] Replace technical error messages with user-friendly versions
- [ ] Add recovery actions to all errors
- [ ] Implement ErrorAlert component
- [ ] Add helpful hints to common errors
- [ ] Test error states for all API failures
- [ ] Verify validation errors are clear
- [ ] Add empty states for all lists
- [ ] Ensure errors don't break UI layout

---

## Part 5: Testing Validation

**Visual Consistency Check:**
```bash
# Run on all onboarding pages
1. Check spacing (measure with browser DevTools)
2. Check colors (verify they match design tokens)
3. Check typography (verify heading hierarchy)
4. Check buttons (verify sizes and variants)
5. Take screenshots for comparison
```

**Loading State Check:**
```bash
# Simulate slow network (Chrome DevTools: Slow 3G)
1. Navigate through wizard
2. Verify loading indicators appear
3. Verify they disappear when complete
4. Check no race conditions or flicker
```

**Error State Check:**
```bash
# Force errors (mock API failures)
1. Trigger each error type
2. Verify error message is clear
3. Verify recovery action works
4. Check error doesn't break layout
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-14
**Implementation Status:** Documented (ready for component updates)
