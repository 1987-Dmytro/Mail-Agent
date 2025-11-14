# Mail Agent Setup Guide
**Complete Step-by-Step Instructions for Setting Up Mail Agent**

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Getting Started](#getting-started)
3. [Step 1: Connect Gmail](#step-1-connect-gmail)
4. [Step 2: Link Telegram](#step-2-link-telegram)
5. [Step 3: Create Folders](#step-3-create-folders)
6. [Step 4: Configure Notifications](#step-4-configure-notifications)
7. [Completion & Next Steps](#completion--next-steps)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Prerequisites

Before you begin, make sure you have:

### Required Accounts
- ✅ **Gmail Account**: An active Gmail account (personal or G Suite)
- ✅ **Telegram Account**: Telegram installed on your phone or desktop
- ✅ **Internet Connection**: Stable internet connection

### System Requirements
- **Browser**: Chrome, Firefox, Safari, or Edge (latest version recommended)
- **Mobile**: iOS 13+ or Android 8+ (optional, for Telegram notifications)
- **Screen Size**: Minimum 320px width (works on all modern devices)

### What You'll Need
- ⏱️ **Time**: Approximately 5-10 minutes
- 📱 **Phone**: To access Telegram for linking
- 🔐 **Gmail Password**: To authorize Mail Agent

---

## Getting Started

### Step 0: Access Mail Agent

1. Navigate to Mail Agent in your browser: `https://mailagent.app` (or your deployment URL)
2. You'll see the welcome screen with "Get Started" button
3. Click **"Get Started"** to begin the onboarding wizard

![Welcome Screen](../screenshots/welcome-screen.png)

---

## Step 1: Connect Gmail

### Why Connect Gmail?

Mail Agent needs access to your Gmail account to:
- Read your emails to sort them into folders
- Send replies you approve via Telegram
- Add labels to keep your inbox organized

**Privacy Note:** Mail Agent never shares your data. You can revoke access anytime. All connections are encrypted.

### How to Connect

1. On the **"Connect Your Gmail Account"** page, review the permissions:
   - ✅ Read your emails to sort them into folders
   - ✅ Send replies you approve via Telegram
   - ✅ Add labels to keep your inbox organized

2. Click the **"Connect Gmail"** button

3. You'll be redirected to Google's secure sign-in page

4. **Sign in with your Google account**:
   - Enter your Gmail address
   - Enter your password
   - Complete 2-factor authentication if enabled

5. **Grant Permissions**:
   - Google will show you the permissions Mail Agent is requesting
   - Review the permissions carefully
   - Click **"Allow"** to grant access

6. **Wait for Confirmation**:
   - You'll be redirected back to Mail Agent
   - You should see a green checkmark: "Gmail Connected!"

![Gmail OAuth Flow](../screenshots/gmail-oauth.png)

### Troubleshooting Gmail Connection

**If you see "Permission denied":**
- Click "Connect Gmail" to try again
- Make sure you click "Allow" on Google's permission page

**If you see "Connection error":**
- Check your internet connection
- Try refreshing the page and clicking "Connect Gmail" again

**If redirected but no success message:**
- Wait a few seconds for processing
- Refresh the page
- If still stuck, see [Troubleshooting Guide](troubleshooting.md#gmail-connection-issues)

---

## Step 2: Link Telegram

### Why Link Telegram?

Telegram is where you'll receive notifications about:
- New emails sorted into your folders
- Emails needing your response
- Emails requiring your approval

### How to Link Telegram

#### 2.1 Find the Mail Agent Bot

1. Open **Telegram** on your phone or desktop

2. Tap the **search icon** (magnifying glass) at the top

3. Type: `@MailAgentBot`

4. Tap the bot name in search results

5. Tap **"Start"** to begin chatting with the bot

![Find Telegram Bot](../screenshots/telegram-search.png)

#### 2.2 Generate Linking Code

1. Back in Mail Agent, you'll see a 6-digit linking code (e.g., `123456`)

2. **Tap the code to copy it** (or copy manually)

3. The code expires in **10 minutes**, so complete linking promptly

![Linking Code Display](../screenshots/telegram-code.png)

#### 2.3 Send Code to Bot

1. In Telegram, **send the 6-digit code** to @MailAgentBot

2. The bot will reply with a confirmation message

3. Back in Mail Agent, you'll see:
   - ✅ Green checkmark
   - "Telegram Connected! You'll receive notifications here."

![Telegram Linked Success](../screenshots/telegram-success.png)

### Troubleshooting Telegram Linking

**Can't find @MailAgentBot?**
- Make sure you're searching in Telegram (not WhatsApp or other apps)
- Check spelling: @MailAgentBot (with capital M and A)
- Try searching by bot name: "Mail Agent Bot"

**Code expired?**
- Click "Generate New Code" in Mail Agent
- Send the new code to @MailAgentBot within 10 minutes

**Code not working?**
- Make sure you sent the code to @MailAgentBot (check the bot name)
- Check that you copied the entire 6-digit code
- Try generating a new code

**Waiting too long for confirmation?**
- Make sure you tapped "Start" in the bot chat
- Check that the bot replied to your code
- Click "Retry" in Mail Agent

---

## Step 3: Create Folders

### Why Create Folders?

Folders automatically sort your emails based on keywords. For example:
- **Government** folder: Catches emails about taxes, permits, official documents
- **Banking** folder: Catches emails from your banks, payment confirmations
- **Work** folder: Catches emails about projects, meetings, deadlines

### How to Create Folders

#### 3.1 Create Your First Folder

1. You'll see a form with two fields:
   - **Folder Name**: The name of your category (e.g., "Government")
   - **Keywords**: Words that trigger this folder (e.g., "finanzamt, tax, bürgeramt")

2. **Enter a Folder Name**:
   - Choose a clear, descriptive name
   - Examples: Government, Banking, Work, Family, Shopping, Travel

3. **Enter Keywords** (comma-separated):
   - Think about words that appear in emails you want sorted
   - Include both German and English terms if applicable
   - Examples:
     - Banking: `bank, sparkasse, n26, transfer, payment`
     - Government: `finanzamt, tax, steuer, bürgeramt, finanzamt`
     - Work: `project, meeting, deadline, team, report`

4. **Choose a Color** (optional):
   - Select a color to help identify this folder visually

5. Click **"Save"** to create the folder

![Create Folder Form](../screenshots/folder-create.png)

#### 3.2 How Keywords Work

**Mail Agent will:**
- Check each incoming email for your keywords
- If an email contains any of your keywords, it's moved to that folder
- If multiple folders match, Mail Agent will ask you which one to use

**Example:**
- Folder: "Banking"
- Keywords: `bank, n26, sparkasse, payment`
- Email subject: "Your N26 payment was successful"
- **Result:** Email automatically goes to "Banking" folder ✅

#### 3.3 Add More Folders (Recommended)

1. After creating your first folder, click **"Add Another Folder"**

2. Create at least **3-5 folders** to cover your main email categories

3. Common folder ideas:
   - 📋 Government (official documents)
   - 💰 Banking (financial emails)
   - 💼 Work (job-related)
   - 🛒 Shopping (receipts, orders)
   - ✈️ Travel (bookings, confirmations)
   - 👨‍👩‍👧 Family (personal)
   - 📰 Newsletters (subscriptions)

#### 3.4 Complete This Step

1. Once you've created at least **1 folder**, the "Next" button will activate

2. Click **"Next"** to proceed to notification preferences

**Tip:** You can add more folders anytime from the Dashboard!

![Folder List](../screenshots/folder-list.png)

### Troubleshooting Folder Creation

**"Folder name is required" error:**
- Make sure you entered a name before clicking Save

**Keywords not working as expected:**
- Check spelling of keywords
- Include common variations (e.g., "tax" and "steuer")
- Use lowercase (Mail Agent is case-insensitive)

**Can't save folder:**
- Check your internet connection
- Try again in a few seconds
- If error persists, see [Troubleshooting Guide](troubleshooting.md#folder-creation-issues)

---

## Step 4: Configure Notifications

### Why Configure Notifications?

Customize when and how you receive Telegram notifications to avoid notification overload.

### Notification Options

#### 4.1 Group Notifications Together

**What it does:** Instead of one notification per email, you'll receive one notification with multiple emails.

**Example:**
- ❌ Without batching: 5 emails = 5 notifications (annoying!)
- ✅ With batching: 5 emails = 1 notification with 5 email summaries

**How to enable:**
- Toggle **"Group notifications together"** to ON
- Choose batch frequency:
  - Every 15 minutes
  - Every 30 minutes
  - Every hour

![Batch Notifications](../screenshots/batch-notifications.png)

#### 4.2 Quiet Hours

**What it does:** Pause notifications during specific hours (great for sleeping or focusing).

**Example:**
- Set quiet hours: 10 PM - 7 AM
- During this time: No notifications (unless priority)
- After quiet hours: You'll get a summary of emails received overnight

**How to enable:**
- Toggle **"Quiet Hours"** to ON
- Set start time (e.g., 10:00 PM)
- Set end time (e.g., 7:00 AM)

![Quiet Hours](../screenshots/quiet-hours.png)

#### 4.3 Send Priority Emails Instantly

**What it does:** Important emails bypass batching and quiet hours.

**Example:**
- Regular email during quiet hours: Waits until morning ⏰
- Priority email during quiet hours: Notifies immediately 🔔

**How to enable:**
- Toggle **"Send priority emails instantly"** to ON
- Mail Agent will learn which senders/keywords are priority over time

![Priority Notifications](../screenshots/priority-notifications.png)

#### 4.4 Test Notification

**Try it out:**
1. Click **"Send Test Notification to Telegram"**
2. Check your Telegram for the test message
3. If you received it, you're all set! ✅

### Complete Setup

1. Review your notification settings

2. Click **"Complete Setup"** to finish onboarding

3. You'll be redirected to your Dashboard! 🎉

![Setup Complete](../screenshots/setup-complete.png)

---

## Completion & Next Steps

### You're All Set! 🎉

**Mail Agent is now:**
- ✅ Watching your Gmail inbox
- ✅ Sorting emails into your folders
- ✅ Sending notifications to Telegram

### What Happens Next?

#### 1. You'll Receive Telegram Notifications

When new emails arrive, you'll receive a Telegram notification like:

```
📧 New Email: Tax Return Documents

From: Finanzamt Berlin
Subject: Your 2024 tax return is ready

📂 Sorted to: Government

[View Email] [Mark as Read]
```

#### 2. Review and Approve Sorting

If Mail Agent isn't sure which folder an email belongs to, it will ask:

```
❓ Where should this email go?

From: booking.com
Subject: Your Berlin hotel confirmation

Suggested Folder: Travel
Other Options: Personal, Shopping

[Confirm] [Change Folder]
```

#### 3. Mail Agent Learns Your Preferences

Over time, Mail Agent learns:
- Which senders are priority
- Which keywords matter most
- How you prefer emails organized

### Your Dashboard

Your dashboard shows:
- 📊 **Email Statistics**: Total emails processed, folders created
- 📥 **Recent Activity**: Latest emails sorted
- ⚙️ **Quick Settings**: Manage folders, adjust notifications
- 🔗 **Connection Status**: Gmail and Telegram status

![Dashboard Overview](../screenshots/dashboard.png)

### Managing Mail Agent

**Add More Folders:**
1. Go to Dashboard
2. Click "Folders" in sidebar
3. Click "Create Folder"

**Adjust Notification Settings:**
1. Go to Dashboard
2. Click "Settings" in sidebar
3. Adjust preferences

**View Sorted Emails:**
1. Open Gmail
2. Look for labels matching your folder names
3. All sorted emails have Mail Agent labels

---

## Troubleshooting

For detailed troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).

### Quick Fixes

**Gmail not connecting?**
- Check internet connection
- Try a different browser
- Clear browser cache and cookies

**Telegram not linking?**
- Make sure you're using @MailAgentBot (correct spelling)
- Generate a new code if expired
- Check that you tapped "Start" in the bot

**Not receiving notifications?**
- Send a test notification from Settings
- Check Telegram notification settings (phone settings)
- Make sure you're not in quiet hours

**Folders not working?**
- Check keyword spelling
- Add more keyword variations
- Give Mail Agent a few minutes to process new emails

---

## FAQ

### General Questions

**Q: Is Mail Agent secure?**
A: Yes. Mail Agent uses OAuth 2.0 for Gmail (industry standard), encrypted connections, and never stores your Gmail password. You can revoke access anytime from Google Account settings.

**Q: How much does Mail Agent cost?**
A: [Insert pricing information or "Mail Agent is free during beta"]

**Q: Can I use Mail Agent with multiple Gmail accounts?**
A: Currently, Mail Agent supports one Gmail account per user. Multiple account support is planned.

**Q: Does Mail Agent read all my emails?**
A: Mail Agent only reads email metadata (sender, subject, snippet) to categorize emails. Full email content is only accessed if you approve a suggested reply.

### Gmail Questions

**Q: What Gmail permissions does Mail Agent need?**
A: Mail Agent needs:
- `gmail.readonly`: To read email metadata for sorting
- `gmail.labels`: To create and apply labels
- `gmail.send`: To send replies you approve (optional)

**Q: Can I revoke Mail Agent's access to Gmail?**
A: Yes. Visit [Google Account Permissions](https://myaccount.google.com/permissions) and remove "Mail Agent".

**Q: Will Mail Agent delete my emails?**
A: No. Mail Agent only adds labels and moves emails to folders. It never deletes emails.

### Telegram Questions

**Q: Why Telegram and not WhatsApp or email?**
A: Telegram offers a powerful bot API that allows interactive notifications (approve/reject actions). We may add other platforms in the future.

**Q: Can I use Telegram Desktop instead of mobile?**
A: Yes! Telegram works on desktop, mobile, and web.

**Q: What if I don't want Telegram notifications?**
A: You can disable notifications entirely and just use Mail Agent's web dashboard.

### Folder Questions

**Q: How many folders can I create?**
A: Unlimited. However, we recommend 5-10 folders for best organization.

**Q: Can I rename or delete folders?**
A: Yes. Go to Dashboard → Folders → Edit or Delete.

**Q: What happens if an email matches multiple folders?**
A: Mail Agent will ask you which folder to use via Telegram.

**Q: Can I use wildcards in keywords?**
A: Not yet, but partial matching works (e.g., "bank" matches "banking", "banks").

### Notification Questions

**Q: Can I turn off notifications for specific folders?**
A: Yes. Go to Settings → Notifications → Folder Preferences.

**Q: What's the difference between batching and quiet hours?**
A: Batching groups notifications together. Quiet hours completely pauses notifications during set times (except priority emails).

**Q: How do I mark emails as priority?**
A: Mail Agent learns priority over time. You can also manually mark senders as priority in Settings.

---

## Need More Help?

- 📧 **Email Support**: support@mailagent.app
- 💬 **Community**: [Discord/Forum Link]
- 📚 **Full Documentation**: [Link to docs]
- 🐛 **Report a Bug**: [GitHub Issues Link]

---

**Setup Guide Version:** 1.0
**Last Updated:** 2025-11-14
**Compatible with:** Mail Agent v1.0+
