# Mail Agent - Frequently Asked Questions (FAQ)

## Table of Contents
1. [General Questions](#general-questions)
2. [Setup & Getting Started](#setup--getting-started)
3. [Gmail Integration](#gmail-integration)
4. [Telegram Notifications](#telegram-notifications)
5. [Folder Management](#folder-management)
6. [Notification Settings](#notification-settings)
7. [Privacy & Security](#privacy--security)
8. [Troubleshooting](#troubleshooting)
9. [Billing & Plans](#billing--plans)
10. [Technical Questions](#technical-questions)

---

## General Questions

### What is Mail Agent?

Mail Agent is an AI-powered email management system that automatically sorts your Gmail inbox into custom folders, sends notifications to Telegram, and helps you respond to emails faster. It uses machine learning to understand your email patterns and save you time.

### How does Mail Agent work?

1. **Connect Gmail**: Mail Agent reads your incoming emails
2. **AI Classification**: Our AI analyzes each email and matches it to your folders based on keywords and patterns
3. **Telegram Notifications**: You receive a notification on Telegram for sorted emails
4. **Approve/Respond**: You can approve sorting, respond to emails, or take other actions directly from Telegram

### How much time can Mail Agent save me?

On average, users save **15-30 minutes per day** on email management. Mail Agent eliminates manual sorting, reduces inbox clutter, and provides instant notifications for important emails.

### Is Mail Agent free?

[Update with your pricing model]
- **Beta**: Free during beta testing period
- **Free Tier**: [If applicable] Basic features for personal use
- **Pro Tier**: [If applicable] Advanced features, more folders, priority support

### Who is Mail Agent for?

Mail Agent is ideal for:
- 📧 **Professionals** managing high email volumes
- 🏢 **Freelancers** juggling client communications
- 🇩🇪 **International users** (especially German speakers) receiving emails in multiple languages
- 👨‍💼 **Anyone** who wants a cleaner, more organized inbox

### What languages does Mail Agent support?

- **Interface**: English (German coming soon)
- **Email Classification**: All languages (AI understands German, English, Spanish, French, and more)
- **Keywords**: Use any language in folder keywords

---

## Setup & Getting Started

### How long does setup take?

Onboarding takes **5-10 minutes** on average. You'll connect Gmail, link Telegram, create folders, and configure notifications.

### Do I need technical skills to use Mail Agent?

No! Mail Agent is designed for non-technical users. If you can use Gmail and Telegram, you can use Mail Agent.

### Can I skip steps during onboarding?

No, all steps are required:
1. Gmail connection (required for email access)
2. Telegram linking (required for notifications)
3. At least 1 folder (required for sorting)
4. Notification preferences (configurable, but required to complete)

You can adjust settings anytime after onboarding.

### What if I close the browser during onboarding?

No problem! Mail Agent saves your progress automatically. When you return, you'll resume from where you left off. Progress is saved for 7 days.

### Can I change settings after onboarding?

Yes! Go to Dashboard → Settings to:
- Add/edit/delete folders
- Adjust notification preferences
- Reconnect Gmail or Telegram
- Update your profile

---

## Gmail Integration

### What Gmail permissions does Mail Agent need?

Mail Agent requests the following permissions:

1. **Read emails** (`gmail.readonly`): To analyze and sort incoming emails
2. **Manage labels** (`gmail.labels`): To create and apply Gmail labels (folders)
3. **Send emails** (optional) (`gmail.send`): To send replies you approve via Telegram

All permissions are standard OAuth 2.0 permissions approved by Google.

### Is my Gmail password shared with Mail Agent?

**No.** Mail Agent uses OAuth 2.0, which means:
- You sign in directly on Google's website (not Mail Agent)
- Mail Agent never sees or stores your Gmail password
- You grant temporary access that can be revoked anytime

### Can Mail Agent read all my emails?

Mail Agent only reads:
- **Incoming emails** to sort them
- **Email metadata**: Subject, sender, date, snippet (first few lines)
- **Not full content**: Unless you approve a suggested reply (Epic 3 feature)

Mail Agent **does not**:
- Read old emails (only new emails after setup)
- Store email content permanently
- Share your emails with third parties

### How do I revoke Mail Agent's access to Gmail?

1. Visit [Google Account Permissions](https://myaccount.google.com/permissions)
2. Find "Mail Agent" in the list
3. Click "Remove Access"

Your emails remain untouched, but Mail Agent will stop sorting new emails.

### Can I use multiple Gmail accounts?

Currently, Mail Agent supports **one Gmail account per user**. Multiple account support is planned for a future release.

### What happens if I disconnect Gmail?

- Mail Agent stops sorting new emails
- Existing Gmail labels (folders) remain
- Telegram notifications stop
- You can reconnect anytime from Dashboard → Settings

---

## Telegram Notifications

### Why Telegram instead of email or SMS?

Telegram offers several advantages:
- **Instant delivery**: Notifications arrive faster than email
- **Interactive actions**: Approve, reject, or respond directly from Telegram
- **Rich formatting**: View email previews with sender, subject, and snippet
- **Free**: No SMS fees
- **Privacy**: Telegram has strong encryption and privacy features

### How do I find @MailAgentBot?

1. Open Telegram app
2. Tap the **search icon** (magnifying glass)
3. Type: `@MailAgentBot`
4. Tap the bot name
5. Tap **"Start"**

**Still can't find it?** Try this direct link: [https://t.me/MailAgentBot](https://t.me/MailAgentBot)

### What if I never received the linking code?

The linking code should appear instantly after clicking "Generate Code" in Mail Agent. If you don't see it:
1. Refresh the page
2. Check your internet connection
3. Try a different browser
4. Contact support if the issue persists

### Can I change which Telegram account receives notifications?

Yes:
1. Go to Dashboard → Settings → Connections
2. Click "Disconnect Telegram"
3. Click "Link Telegram"
4. Follow the linking process with your new Telegram account

### What notifications will I receive?

You'll receive Telegram notifications for:
- ✅ **New emails sorted** into your folders
- ⚠️ **Emails needing approval** (if Mail Agent isn't sure which folder)
- 📨 **Emails requiring response** (high-priority emails)
- ✉️ **Batch summaries** (if batch notifications enabled)

You control notification timing via Settings → Notifications.

### Can I turn off notifications temporarily?

Yes! Enable **Quiet Hours** in Settings → Notifications:
- Set start time (e.g., 10 PM)
- Set end time (e.g., 7 AM)
- During quiet hours, only priority emails notify you
- Regular emails are batched and sent after quiet hours end

### Can I mute @MailAgentBot in Telegram?

Yes, but you won't receive any notifications. Instead, use Mail Agent's **Quiet Hours** or **Batch Notifications** to reduce notification frequency while staying connected.

---

## Folder Management

### What are folders?

Folders are custom email categories you create. Mail Agent automatically sorts incoming emails into these folders based on keywords you define.

**Example:**
- Folder: "Banking"
- Keywords: `bank, n26, sparkasse, payment, transfer`
- Result: Emails from your bank are automatically moved to "Banking" folder

### How do keywords work?

Keywords are words or phrases that trigger email sorting. Mail Agent checks if an email contains any of your keywords in:
- Email subject
- Sender name/email address
- Email preview text

**Matching Rules:**
- **Case-insensitive**: "bank" matches "Bank", "BANK", "banking"
- **Partial matching**: "tax" matches "taxes", "taxation", "taxable"
- **Multiple keywords**: Email only needs to match ONE keyword to be sorted
- **Multiple languages**: Use German and English keywords together

**Example:**
```
Keywords: finanzamt, tax, steuer, revenue
✅ Matches: "Finanzamt Berlin", "tax return", "Steuer 2024"
❌ Doesn't match: "pizza delivery", "meeting reminder"
```

### How many folders can I create?

**Unlimited** (with fair use). We recommend **5-10 folders** for optimal organization. Too many folders can make management difficult.

### Can I have the same keyword in multiple folders?

Yes, but if an email matches multiple folders, Mail Agent will ask you which folder to use. To avoid this:
- Use unique keywords per folder
- Or let Mail Agent learn your preferences over time (Epic 3 feature)

### What happens if an email doesn't match any folder?

Emails that don't match any folder keywords:
- Remain in your Gmail inbox (unsorted)
- Don't trigger a Telegram notification
- Can be manually sorted later

**Tip:** Create a "Misc" or "Other" folder with broad keywords as a catch-all.

### Can I rename or delete folders?

**Yes:**
- **Rename**: Go to Dashboard → Folders → Edit folder
- **Delete**: Go to Dashboard → Folders → Delete folder (requires confirmation)

**Warning:** Deleting a folder:
- Removes the Gmail label
- Stops future sorting for those keywords
- Does NOT delete the emails (they remain in Gmail)

### Do folders work with Gmail labels?

Yes! Mail Agent creates a Gmail label for each folder. When an email is sorted:
- Gmail label is applied
- Email appears under that label in Gmail
- Email is still in your inbox (unless you set up Gmail filters)

---

## Notification Settings

### What is "Batch Notifications"?

Batch notifications group multiple emails into a single Telegram message instead of sending one notification per email.

**Example:**
- **Without batching**: 5 emails = 5 separate notifications (annoying!)
- **With batching**: 5 emails = 1 notification with 5 email summaries

You choose the batch frequency:
- Every 15 minutes
- Every 30 minutes
- Every hour
- End of day (e.g., 6 PM)

### What are "Quiet Hours"?

Quiet Hours pause all notifications during specified hours (great for sleeping or focused work).

**Example:**
- Quiet Hours: 10 PM - 7 AM
- During this time: No notifications (except priority emails)
- After quiet hours: You receive a summary of overnight emails

**Tip:** Combine with batch notifications for maximum peace of mind.

### What are "Priority Emails"?

Priority emails are high-importance emails that bypass batching and quiet hours. Mail Agent learns which emails are priority based on:
- Sender (e.g., your boss, important clients)
- Keywords (e.g., "urgent", "deadline")
- Your past behavior (emails you open/respond to quickly)

You can manually mark senders as priority in Settings.

### Can I test notifications before saving?

Yes! Click **"Send Test Notification"** in Settings → Notifications. You'll receive a test message in Telegram to verify settings work.

### How do I stop receiving too many notifications?

1. **Enable Batch Notifications**: Reduces frequency to once per hour (or custom)
2. **Set Quiet Hours**: Pauses notifications during specific times
3. **Reduce Folders**: Fewer folders = fewer emails trigger notifications
4. **Adjust Keywords**: Make keywords more specific to reduce false matches

---

## Privacy & Security

### Is Mail Agent secure?

**Yes.** Mail Agent follows industry-standard security practices:

1. **OAuth 2.0**: Secure Gmail authentication (no password storage)
2. **HTTPS Encryption**: All data transmitted over secure connections
3. **JWT Tokens**: Secure session management
4. **Database Encryption**: User data encrypted at rest
5. **No Third-Party Sharing**: Your data is never sold or shared

### What data does Mail Agent store?

Mail Agent stores:
- ✅ Your email address (Gmail)
- ✅ Your Telegram username/ID
- ✅ Folder names and keywords you create
- ✅ Notification preferences
- ✅ Email metadata (subject, sender, date) for sorting history
- ✅ Authentication tokens (encrypted)

Mail Agent **does not** store:
- ❌ Your Gmail password
- ❌ Full email content (only metadata)
- ❌ Attachments
- ❌ Sensitive personal information

### Can Mail Agent developers read my emails?

**No.** Mail Agent's AI processes emails automatically. Human developers:
- Cannot access individual user emails
- Cannot see email content
- May see anonymized aggregate statistics (e.g., "1000 emails sorted today")

### Is Mail Agent GDPR compliant?

**Yes.** Mail Agent complies with GDPR (General Data Protection Regulation). You have the right to:
- ✅ **Access** your data (export all data)
- ✅ **Rectify** incorrect data (edit settings)
- ✅ **Erase** your data (delete account)
- ✅ **Restrict** processing (disconnect services)
- ✅ **Port** your data (download in JSON format)
- ✅ **Object** to processing (opt-out anytime)

To exercise these rights, visit Settings → Privacy or contact support@mailagent.app.

### How do I delete my account?

1. Go to Settings → Account → Delete Account
2. Confirm deletion (this is permanent!)
3. All your data is deleted within 30 days

**What happens:**
- Mail Agent access revoked from Gmail
- Telegram bot disconnected
- All folders, preferences, and history deleted
- Gmail labels remain (you can delete manually)

### Can I export my data?

Yes! Go to Settings → Privacy → Export Data. You'll receive a JSON file with:
- All folders and keywords
- Notification preferences
- Email sorting history (metadata only)
- Account information

---

## Troubleshooting

### Quick Fixes

**Gmail not connecting?**
- Check internet connection
- Try a different browser (Chrome recommended)
- Clear browser cache and cookies
- Make sure you clicked "Allow" on Google's permission page

**Telegram not linking?**
- Make sure you're using @MailAgentBot (correct spelling)
- Check that you tapped "Start" in the bot chat
- Generate a new code if expired (codes expire after 10 minutes)

**Not receiving notifications?**
- Check Telegram app notification settings (phone settings)
- Make sure @MailAgentBot isn't muted
- Verify quiet hours aren't active
- Send a test notification from Settings

**Emails not being sorted?**
- Check folder keywords are correct (no typos)
- Add more keyword variations (e.g., "bank" + "sparkasse" + "banking")
- Give Mail Agent 1-2 minutes to process new emails
- Verify Gmail connection is active (Dashboard → Connections)

For detailed troubleshooting, see: [Troubleshooting Guide](../user-guide/troubleshooting.md)

---

## Billing & Plans

### Is there a free trial?

[Update based on your pricing model]
- Yes, Mail Agent offers a **14-day free trial** with full access to all features
- No credit card required
- Cancel anytime

### What happens if I cancel my subscription?

- Mail Agent stops sorting new emails
- Telegram notifications stop
- Existing Gmail labels remain
- You can resubscribe anytime without losing data (data retained for 90 days)

### Can I change plans later?

Yes! Go to Settings → Billing → Change Plan. Changes take effect immediately:
- **Upgrade**: New features available instantly
- **Downgrade**: Keeps current features until next billing cycle

### Do you offer refunds?

[Update based on your refund policy]
- Yes, we offer a **30-day money-back guarantee**
- No questions asked
- Contact support@mailagent.app to request a refund

---

## Technical Questions

### What browsers are supported?

**Desktop:**
- ✅ Chrome 90+ (recommended)
- ✅ Firefox 88+
- ✅ Safari 15+
- ✅ Edge 90+

**Mobile:**
- ✅ Safari (iOS 13+)
- ✅ Chrome (Android 8+)

Older browsers may work but are not officially supported.

### Does Mail Agent work on mobile?

Yes! Mail Agent is fully responsive and works on:
- 📱 Mobile phones (320px minimum width)
- 📱 Tablets (768px+)
- 💻 Desktop (1024px+)

However, initial setup is easier on desktop due to OAuth flows.

### Can I use Mail Agent offline?

No. Mail Agent requires an internet connection to:
- Fetch emails from Gmail
- Process AI classification
- Send Telegram notifications

Your settings are cached locally, so you can view the Dashboard offline, but no new emails will be sorted.

### What is the API rate limit?

For normal usage, you won't hit any limits. Mail Agent is designed to handle:
- Up to **500 emails per day** (free tier)
- Up to **5,000 emails per day** (pro tier)

If you consistently receive more, contact us for enterprise plans.

### Can I integrate Mail Agent with other tools?

Not yet, but we're planning integrations with:
- Slack (notifications)
- Microsoft Outlook (alternative to Gmail)
- Zapier (automation workflows)
- API access for developers

Join our beta program to get early access!

---

## Still Have Questions?

Can't find the answer you're looking for?

- **📧 Email Support**: support@mailagent.app
- **💬 Live Chat**: Available on Dashboard (bottom-right chat icon)
- **📚 Documentation**: [Full Setup Guide](../user-guide/setup.md)
- **🐛 Report Bug**: [GitHub Issues](https://github.com/mailagent/issues)
- **💡 Feature Request**: [Community Forum](https://community.mailagent.app)

**Response Times:**
- Email: 24-48 hours
- Live Chat: Monday-Friday, 9 AM - 5 PM CET
- Community Forum: Responses from other users within hours

---

**FAQ Version:** 1.0
**Last Updated:** 2025-11-14
**Next Review:** 2025-12-14
