# Copy & Messaging Improvements
**Story 4.8: End-to-End Onboarding Testing and Polish**
**Task 3.1: Refine Copy and Messaging Based on Feedback (AC 5)**
**Date:** 2025-11-14

## Overview

This document outlines improvements to user-facing text across the Mail Agent onboarding experience, based on usability testing insights. All improvements prioritize clarity, friendliness, and actionability for non-technical users.

**Guiding Principles:**
- **Clear, not clever:** Direct language over jargon
- **Friendly, not formal:** Conversational but professional tone
- **Actionable, not vague:** Tell users exactly what to do
- **Reassuring, not alarming:** Reduce anxiety around permissions and setup

---

## 1. Gmail OAuth Connection Step

### Current vs. Improved Copy

**Card Title**
- ❌ Current: "Connect Gmail Account"
- ✅ Improved: "Connect Your Gmail Account"
- **Rationale:** Personal pronouns create connection and ownership

**Card Description**
- ❌ Current: "Authorize Mail Agent to access your Gmail account"
- ✅ Improved: "Let Mail Agent organize your inbox automatically"
- **Rationale:** Focus on benefit (organize inbox) rather than technical action (authorize/access)

**Permissions List Header**
- ❌ Current: "Required Permissions:"
- ✅ Improved: "What Mail Agent will do:"
- **Rationale:** Action-oriented language is less technical and more understandable

**Permissions List Items**
- ❌ Current:
  - "Read your emails to categorize them"
  - "Send emails on your behalf (with your approval)"
  - "Manage Gmail labels for organization"

- ✅ Improved:
  - "Read your emails to sort them into folders"
  - "Send replies you approve via Telegram"
  - "Add labels to keep your inbox organized"

- **Rationale:**
  - "Categorize" → "sort into folders" (more concrete)
  - "on your behalf (with your approval)" → "you approve via Telegram" (emphasizes control)
  - "Manage" → "Add" (less invasive-sounding)

**Button Text**
- ❌ Current: "Connect Gmail"
- ✅ Improved: "Connect Gmail" (Keep - clear and action-oriented)

**Sub-text**
- ❌ Current: "You'll be redirected to Google to grant permissions"
- ✅ Improved: "Next, you'll securely sign in with Google"
- **Rationale:**
  - "Securely sign in" is more familiar than "grant permissions"
  - Removes "redirected" which can sound disorienting

---

## 2. Telegram Bot Linking Step

### Current vs. Improved Copy

**Instructions for Finding Bot**
- ❌ Current: "Open Telegram and search for @MailAgentBot"
- ✅ Improved:
  ```
  1. Open Telegram on your phone
  2. Search for @MailAgentBot
  3. Tap "Start" to begin chatting
  ```
- **Rationale:** Step-by-step numbered list is clearer than single sentence

**Code Instructions**
- ❌ Current: "Copy the code below and send it to the bot"
- ✅ Improved: "Send this code to @MailAgentBot (tap to copy)"
- **Rationale:**
  - Direct action ("Send") before object ("this code")
  - Indicate tap-to-copy functionality
  - Repeat bot name for clarity

**Verification Message**
- ❌ Current: "Waiting for verification..."
- ✅ Improved: "Waiting for confirmation from Telegram..."
- **Rationale:** "Confirmation" is friendlier than "verification"

**Success Message**
- ❌ Current: "Telegram Connected!"
- ✅ Improved: "Telegram Connected! You'll receive notifications here."
- **Rationale:** Clarify what Telegram connection means

---

## 3. Folder Configuration Step

### Current vs. Improved Copy

**Step Title**
- ❌ Current: "Setup Folders"
- ✅ Improved: "Create Your First Folders"
- **Rationale:**
  - "Your First" implies more can be added later
  - Less technical than "Setup"

**Description**
- ❌ Current: "Create categories to organize your emails"
- ✅ Improved: "Create folders to automatically sort your emails"
- **Rationale:**
  - "Folders" is more concrete than "categories"
  - "Automatically sort" emphasizes the benefit

**Folder Name Label**
- ❌ Current: "Folder Name"
- ✅ Improved: "Folder Name (e.g., Government, Banking, Work)"
- **Rationale:** Examples help users understand what to enter

**Keywords Label**
- ❌ Current: "Keywords (comma-separated)"
- ✅ Improved: "Keywords to match (e.g., finanzamt, tax, bürgeramt)"
- **Rationale:**
  - "to match" explains purpose
  - Examples guide users

**Keywords Help Text**
- **Add:** "Mail Agent will move emails containing these words to this folder"
- **Rationale:** Explicitly explain how keywords work

**Minimum Folders Validation**
- ❌ Current: "Please create at least 1 folder category before proceeding."
- ✅ Improved: "Create at least one folder to continue. You can add more anytime."
- **Rationale:**
  - Shorter, more conversational
  - Reassures users they can add more later

---

## 4. Notification Preferences Step

### Current vs. Improved Copy

**Batch Notifications**
- ❌ Current: "Batch Notifications"
- ✅ Improved: "Group notifications together"
- **Rationale:** "Batch" is technical jargon; "group" is clearer

**Batch Notifications Description**
- **Add:** "Get one notification with multiple emails, instead of separate notifications"
- **Rationale:** Explain the benefit clearly

**Quiet Hours**
- ❌ Current: "Quiet Hours"
- ✅ Improved: "Quiet Hours" (Keep - widely understood term)

**Quiet Hours Description**
- **Add:** "Pause notifications during these hours (great for sleeping!)"
- **Rationale:**
  - Explain purpose
  - Friendly parenthetical adds personality

**Priority Immediate**
- ❌ Current: "Priority Immediate"
- ✅ Improved: "Send priority emails instantly"
- **Rationale:**
  - Full sentence is clearer
  - "Instantly" conveys urgency

**Priority Immediate Description**
- **Add:** "Important emails bypass quiet hours and batching"
- **Rationale:** Explain interaction with other settings

**Test Notification Button**
- ❌ Current: "Test Notification"
- ✅ Improved: "Send Test Notification to Telegram"
- **Rationale:** Clarify where test will appear

---

## 5. Validation Error Messages

### Current vs. Improved

**Gmail Not Connected**
- ❌ Current: "Please connect your Gmail account before proceeding."
- ✅ Improved: "Connect your Gmail account to continue."
- **Rationale:** Shorter, more direct

**Telegram Not Linked**
- ❌ Current: "Please link your Telegram account before proceeding."
- ✅ Improved: "Link your Telegram account to continue."
- **Rationale:** Consistent with Gmail message

**No Folders Created**
- ❌ Current: "Please create at least 1 folder category before proceeding."
- ✅ Improved: "Create at least one folder to continue."
- **Rationale:** Shorter, removes jargon ("category")

---

## 6. Error Messages

### OAuth Errors

**User Denied Permission**
- ❌ Current: "Permission denied. Please grant access to continue."
- ✅ Improved: "Permission needed. Click 'Connect Gmail' to try again."
- **Rationale:**
  - "Permission needed" is less negative than "denied"
  - Provide specific next step

**OAuth Configuration Failed**
- ❌ Current: "Cannot load OAuth configuration. Please try again."
- ✅ Improved: "Connection error. Please check your internet and try again."
- **Rationale:**
  - Avoid technical term "OAuth configuration"
  - Suggest likely cause (internet)

**Callback Failed**
- ❌ Current: "Failed to exchange authorization code. Please try again."
- ✅ Improved: "Connection failed. Click 'Connect Gmail' to retry."
- **Rationale:**
  - Avoid technical term "authorization code"
  - Provide specific action

### Telegram Errors

**Code Expired**
- ❌ Current: "Verification code expired. Please generate a new code."
- ✅ Improved: "Code expired. Click 'Generate New Code' to try again."
- **Rationale:** Direct user to specific button

**Verification Timeout**
- ❌ Current: "Verification timed out. Please try again."
- ✅ Improved: "Taking longer than expected. Make sure you sent the code to @MailAgentBot, then click 'Retry'."
- **Rationale:**
  - Troubleshoot common issue (wrong bot)
  - Provide specific action

### Network Errors

**API Failure (500)**
- ❌ Current: "Internal Server Error. Please try again."
- ✅ Improved: "Something went wrong. Please try again in a few minutes."
- **Rationale:**
  - Avoid technical term "Internal Server Error"
  - Set expectation for retry timing

**Network Offline**
- ❌ Current: "Network unavailable. Please check your connection."
- ✅ Improved: "No internet connection. Check your wifi or cellular data."
- **Rationale:**
  - More specific terms (wifi/cellular)
  - Friendlier tone

**Timeout**
- ❌ Current: "Request timed out. Please try again."
- ✅ Improved: "This is taking too long. Check your internet and try again."
- **Rationale:**
  - Conversational language
  - Suggest likely cause

---

## 7. Success Messages (Toast Notifications)

**Gmail Connected**
- ❌ Current: "Gmail connected successfully"
- ✅ Improved: "Gmail connected! Moving to Telegram setup..."
- **Rationale:**
  - Exclamation adds positive energy
  - Preview next step

**Telegram Linked**
- ❌ Current: "Telegram account linked successfully"
- ✅ Improved: "Telegram linked! You'll receive notifications here."
- **Rationale:**
  - Confirm what Telegram will be used for

**Folder Created**
- ❌ Current: "Folder created successfully"
- ✅ Improved: "Folder created! Emails matching '[keywords]' will go here."
- **Rationale:**
  - Confirm how folder works
  - Show keywords user entered

**Preferences Saved**
- ❌ Current: "Preferences saved successfully"
- ✅ Improved: "Preferences saved! You'll receive notifications [based on settings]."
- **Rationale:**
  - Confirm current notification schedule

**Test Notification Sent**
- ❌ Current: "Test notification sent successfully"
- ✅ Improved: "Check Telegram! Test notification sent."
- **Rationale:**
  - Tell user where to look
  - More exciting tone

---

## 8. Loading States

**General Loading**
- ❌ Current: "Loading..."
- ✅ Improved: "Loading..." (Keep - universally understood)

**OAuth Redirect**
- ❌ Current: "Connecting your Gmail account..."
- ✅ Improved: "Redirecting to Google..."
- **Rationale:** Set expectation for redirect

**Telegram Verification Polling**
- ❌ Current: "Waiting for verification..."
- ✅ Improved: "Waiting for confirmation... (Check Telegram)"
- **Rationale:** Remind user to check Telegram

**Folder Creation**
- ❌ Current: "Creating folder..."
- ✅ Improved: "Creating folder..." (Keep - clear and concise)

**Dashboard Data Load**
- ❌ Current: (Skeleton loading)
- ✅ Improved: (Skeleton loading) with "Loading your dashboard..." text
- **Rationale:** Reassure user during longer loads

---

## 9. Help Text / Tooltips (New Additions)

**Gmail Permissions Help**
- **Add button:** "Why does Mail Agent need these permissions?"
- **Tooltip/Expandable:**
  ```
  Mail Agent needs to:
  - Read emails to understand their content
  - Apply labels for organization
  - Send replies you approve via Telegram

  Your privacy is protected:
  - We never share your data
  - You can revoke access anytime
  - All connections are encrypted
  ```

**Telegram Code Help**
- **Add button:** "Can't find @MailAgentBot?"
- **Tooltip:**
  ```
  1. Open Telegram app
  2. Tap the search icon
  3. Type: @MailAgentBot
  4. Tap the bot name
  5. Tap "Start"
  ```

**Keywords Help**
- **Add button:** "What are good keywords?"
- **Tooltip:**
  ```
  Think about words that appear in emails you want sorted:
  - Banking: bank, sparkasse, n26, transfer
  - Government: finanzamt, steuer, tax, bürgeramt
  - Work: project, meeting, deadline, team

  Tip: Include both German and English terms!
  ```

**Quiet Hours Help**
- **Add button:** "How do quiet hours work?"
- **Tooltip:**
  ```
  During quiet hours:
  - Regular emails won't trigger notifications
  - Priority emails still come through immediately
  - You'll get batched updates after quiet hours end
  ```

---

## 10. Onboarding Completion Summary

**Success Message**
- ❌ Current: "Setup Complete! Welcome to Mail Agent."
- ✅ Improved:
  ```
  You're all set! 🎉

  Mail Agent is now:
  - Watching your Gmail inbox
  - Sorting emails into your folders
  - Sending notifications to Telegram
  ```
- **Rationale:**
  - Emoji adds celebration
  - Bullet points summarize what's happening
  - Sets expectations

**Next Steps**
- **Add:**
  ```
  What happens next?
  1. You'll receive a Telegram notification when new emails arrive
  2. Review and approve sorting suggestions
  3. Mail Agent learns your preferences over time

  Need help? Visit our Help Center
  ```
- **Rationale:** Guide users on what to expect immediately after setup

---

## 11. Implementation Priority

### High Priority (Must Fix Before Release)
1. Error messages (more user-friendly)
2. Validation messages (shorter, clearer)
3. Permissions list (less technical)
4. Keywords help text (explain how they work)

### Medium Priority (Should Fix Before Release)
5. Card titles and descriptions (benefit-focused)
6. Success messages (more enthusiastic)
7. Loading state messages (set expectations)
8. Completion summary (set expectations)

### Low Priority (Nice to Have)
9. Help tooltips (for advanced users)
10. Extended documentation links

---

## 12. Tone Guidelines

**DO:**
- Use "you" and "your" (personal)
- Use contractions ("you'll" instead of "you will")
- Use simple, everyday words
- Break complex instructions into steps
- Celebrate success with exclamation points
- Reassure users ("Don't worry," "You can change this later")

**DON'T:**
- Use technical jargon ("OAuth," "authorization code," "verification")
- Use passive voice ("Permission was denied" → "Permission needed")
- Use corporate language ("Please be advised")
- Stack multiple instructions in one sentence
- Use only negative language in errors

**Examples:**

✅ Good: "Check Telegram! Test notification sent."
❌ Bad: "Test notification has been successfully transmitted to your Telegram client."

✅ Good: "Create at least one folder to continue."
❌ Bad: "A minimum of one folder category must be created before proceeding to the next step."

✅ Good: "Connection failed. Click 'Connect Gmail' to retry."
❌ Bad: "The OAuth authorization flow encountered an error during the callback phase. Please reinitiate the flow."

---

## 13. Review Checklist

Before marking Task 3.1 complete, verify:

- [ ] All error messages are user-friendly (no technical jargon)
- [ ] All validation messages are concise (<10 words)
- [ ] All card titles focus on benefits, not technical actions
- [ ] All permissions use everyday language
- [ ] All success messages include positive reinforcement
- [ ] All loading states set clear expectations
- [ ] All instructions are broken into numbered steps where appropriate
- [ ] All help text is easily discoverable
- [ ] Tone is consistent across all components (friendly, encouraging)
- [ ] Non-technical users can understand all text without external help

---

**Document Version:** 1.0
**Last Updated:** 2025-11-14
**Approved By:** Epic 4 Team
**Implementation Status:** Documented (ready for component updates)
