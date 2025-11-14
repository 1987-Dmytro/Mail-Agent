# Mail Agent Troubleshooting Guide
**Solutions for Common Issues**

## Table of Contents
1. [Gmail Connection Issues](#gmail-connection-issues)
2. [Telegram Linking Issues](#telegram-linking-issues)
3. [Folder and Sorting Issues](#folder-and-sorting-issues)
4. [Notification Issues](#notification-issues)
5. [Dashboard and UI Issues](#dashboard-and-ui-issues)
6. [Browser Compatibility Issues](#browser-compatibility-issues)
7. [Performance Issues](#performance-issues)
8. [Getting Additional Help](#getting-additional-help)

---

## Gmail Connection Issues

### Issue: "Permission denied" Error

**Symptoms:**
- Clicking "Connect Gmail" redirects to Google, but you see "Permission denied" back in Mail Agent

**Causes:**
- You clicked "Deny" on Google's permission page
- You closed the OAuth window before completing

**Solutions:**
1. Click **"Connect Gmail"** button again
2. When redirected to Google, make sure to click **"Allow"** (not "Deny")
3. Wait for the redirect back to Mail Agent
4. You should see a green checkmark: "Gmail Connected!"

**If still failing:**
- Try a different browser (Chrome recommended)
- Clear browser cache and cookies
- Make sure you're signed into the correct Gmail account

---

### Issue: "Connection error" or "OAuth configuration failed"

**Symptoms:**
- Error message: "Connection error. Please check your internet and try again."
- OAuth redirect fails immediately

**Causes:**
- No internet connection
- Firewall blocking Google OAuth
- Mail Agent backend server issue

**Solutions:**
1. **Check internet connection:**
   - Open a new tab and visit google.com to verify connectivity
   - Check wifi or cellular data connection

2. **Check firewall/VPN:**
   - Disable VPN temporarily and retry
   - Check corporate firewall settings (if on company network)
   - Whitelist `accounts.google.com` in firewall

3. **Try different network:**
   - Switch from wifi to mobile data (or vice versa)
   - Retry connection

4. **Clear browser data:**
   - Clear cache: Settings → Privacy → Clear Browsing Data
   - Clear cookies for `accounts.google.com` and Mail Agent domain
   - Retry connection

5. **Try different browser:**
   - Test in Chrome (recommended)
   - Test in Firefox or Safari
   - Disable browser extensions that might block OAuth

**If still failing:**
- Wait 5 minutes and try again (temporary server issue)
- Contact support with error details

---

### Issue: Redirected to Google but page hangs/never completes

**Symptoms:**
- OAuth popup opens, you sign in, but never redirected back
- Stuck on "Redirecting..." or blank page

**Causes:**
- Browser blocking popup redirect
- Cookie/session issue
- Slow internet connection

**Solutions:**
1. **Allow popups for Mail Agent:**
   - Check browser address bar for "Popup blocked" icon
   - Click icon and "Always allow popups from mailagent.app"
   - Retry connection

2. **Enable third-party cookies:**
   - Chrome: Settings → Privacy → Cookies → Allow all cookies (temporarily)
   - Firefox: Settings → Privacy → Custom → Cookies → Allow all
   - Retry connection

3. **Wait longer:**
   - On slow connections, OAuth can take 30-60 seconds
   - Don't close the window, wait for automatic redirect

4. **Manual retry:**
   - Close the OAuth window/tab
   - Return to Mail Agent
   - Click "Connect Gmail" again

**If still hanging:**
- Try incognito/private browsing mode
- Try different device
- Contact support

---

### Issue: "Failed to exchange authorization code"

**Symptoms:**
- You granted permissions on Google, but Mail Agent shows error on callback

**Causes:**
- OAuth callback URL mismatch
- Backend API issue
- Expired authorization code

**Solutions:**
1. **Retry immediately:**
   - Click "Connect Gmail" again
   - Complete the flow without delays

2. **Check URL:**
   - Verify you're on the correct Mail Agent domain (not localhost or staging)

3. **Clear session:**
   - Log out of Mail Agent (if logged in)
   - Clear browser cache
   - Log back in and retry

**If still failing:**
- This indicates a server-side issue
- Contact support with error message and timestamp

---

### Issue: Gmail disconnects randomly

**Symptoms:**
- Gmail was connected, but Dashboard shows "Not Connected"
- Notifications stopped working

**Causes:**
- You revoked access in Google Account settings
- OAuth refresh token expired
- Google security check

**Solutions:**
1. **Reconnect Gmail:**
   - Go to Dashboard → Settings → Connections
   - Click "Reconnect Gmail"
   - Complete OAuth flow again

2. **Check Google Account permissions:**
   - Visit [Google Account Permissions](https://myaccount.google.com/permissions)
   - Check if "Mail Agent" is listed
   - If not listed, reconnect in Mail Agent
   - If listed with warning, remove and reconnect

3. **Security verification:**
   - Check Gmail for "New sign-in" security alert
   - Confirm the sign-in if it's you
   - Reconnect in Mail Agent

**Prevention:**
- Don't manually revoke Mail Agent access in Google settings
- Use Mail Agent's dashboard to disconnect properly

---

## Telegram Linking Issues

### Issue: Can't find @MailAgentBot

**Symptoms:**
- Searching for @MailAgentBot in Telegram returns no results
- Bot doesn't appear in search

**Causes:**
- Wrong spelling
- Telegram search delay
- Bot not started

**Solutions:**
1. **Check spelling:**
   - Correct: `@MailAgentBot` (capital M and A)
   - Incorrect: `@mailagentbot`, `@mail_agent_bot`, `@MailAgent_Bot`

2. **Search by name:**
   - Instead of @username, search: "Mail Agent Bot"
   - Look for verified checkmark (if applicable)

3. **Direct link:**
   - Copy this link: `https://t.me/MailAgentBot`
   - Paste in browser or Telegram
   - Click "Open in Telegram"

4. **Check Telegram app version:**
   - Update Telegram to latest version
   - Restart Telegram app
   - Retry search

**If still not found:**
- Bot may be temporarily unavailable
- Contact support for direct bot link

---

### Issue: "Code expired" Error

**Symptoms:**
- Sending the 6-digit code to bot results in "Code expired" message

**Causes:**
- Took longer than 10 minutes to send code
- Code was already used

**Solutions:**
1. **Generate new code:**
   - In Mail Agent, click "Generate New Code"
   - Copy the new 6-digit code
   - Send to @MailAgentBot within 10 minutes

2. **Send code faster:**
   - Have Telegram open before generating code
   - Copy code immediately
   - Send within 1-2 minutes

**Prevention:**
- Don't navigate away from Mail Agent while linking
- Complete linking process in one session

---

### Issue: "Waiting for confirmation" never completes

**Symptoms:**
- Sent code to bot, but Mail Agent still shows "Waiting for confirmation..."
- Spinning loader doesn't stop

**Causes:**
- Sent code to wrong bot
- Bot didn't reply
- Network timeout
- Backend verification issue

**Solutions:**
1. **Verify bot name:**
   - Make sure you sent code to **@MailAgentBot** exactly
   - Check chat header shows "Mail Agent Bot"

2. **Check bot reply:**
   - The bot should reply immediately after you send the code
   - If no reply, you sent to wrong bot or bot is down

3. **Click "Retry":**
   - In Mail Agent, click "Retry" button
   - This forces a re-check of verification status

4. **Generate new code:**
   - Click "Generate New Code"
   - Start fresh linking process

5. **Check Telegram app:**
   - Make sure Telegram app is connected to internet
   - Restart Telegram app
   - Check if bot messages are being delivered

**If still waiting:**
- Check Mail Agent server status
- Try again in 5 minutes
- Contact support with linking code

---

### Issue: Bot says "Invalid code" or doesn't respond

**Symptoms:**
- Send code to bot, but bot replies "Invalid code" or nothing

**Causes:**
- Typo in code
- Code already used
- Code expired
- Sent to wrong bot

**Solutions:**
1. **Verify code:**
   - Make sure you copied the entire 6-digit code
   - Check for extra spaces or characters
   - Code should be exactly 6 digits (e.g., `123456`)

2. **Use copy button:**
   - In Mail Agent, click the code to auto-copy
   - Paste directly in Telegram (don't type manually)

3. **Generate new code:**
   - Old code may be expired or used
   - Click "Generate New Code" in Mail Agent
   - Send new code immediately

4. **Verify bot:**
   - Make absolutely sure you're chatting with @MailAgentBot
   - Check for verified badge (if applicable)
   - Don't use similar-named bots

**If bot doesn't respond at all:**
- Bot may be offline temporarily
- Check Telegram's @BotFather for bot status
- Contact support

---

### Issue: Telegram disconnects randomly

**Symptoms:**
- Was receiving notifications, now stopped
- Dashboard shows "Telegram Not Connected"

**Causes:**
- You blocked/deleted @MailAgentBot in Telegram
- Bot was restarted
- Backend lost connection

**Solutions:**
1. **Relink Telegram:**
   - Go to Dashboard → Settings → Connections
   - Click "Relink Telegram"
   - Follow linking process again

2. **Unblock bot (if blocked):**
   - In Telegram, search for @MailAgentBot
   - If blocked, tap "Unblock"
   - Relink in Mail Agent

3. **Check bot chat:**
   - Open chat with @MailAgentBot
   - Send `/start` command
   - Relink in Mail Agent

---

## Folder and Sorting Issues

### Issue: Emails not being sorted into folders

**Symptoms:**
- Created folders with keywords, but emails still arrive unsorted
- No labels appearing in Gmail

**Causes:**
- Keywords don't match email content
- Keywords are too specific
- Email processing delay
- Folder not active

**Solutions:**
1. **Check keywords:**
   - Review your keywords for typos
   - Add more keyword variations
   - Example: Instead of just "finanzamt", add: `finanzamt, tax, steuer, revenue`

2. **Use partial matches:**
   - Keywords match partial words
   - "bank" will match "banking", "banque", "bankhaus"

3. **Wait for processing:**
   - New folders take 1-2 minutes to activate
   - Existing emails won't be retroactively sorted (only new emails)
   - Send yourself a test email with keywords to verify

4. **Verify folder is active:**
   - Go to Dashboard → Folders
   - Check folder has status "Active"
   - If "Inactive", click to activate

5. **Check Gmail labels:**
   - Open Gmail
   - Look for labels on left sidebar matching your folder names
   - If labels don't exist, Mail Agent may have lost connection

**Testing:**
1. Send test email with keyword in subject
2. Wait 1-2 minutes
3. Check Gmail for label
4. Check Telegram for notification

**If still not working:**
- Reconnect Gmail in Dashboard → Settings
- Delete and recreate folder
- Contact support with folder/keyword details

---

### Issue: "Folder name is required" error when saving

**Symptoms:**
- Clicking "Save" shows validation error

**Causes:**
- Folder name field is empty
- Only whitespace entered

**Solutions:**
1. **Enter folder name:**
   - Type a clear name (e.g., "Banking", "Government")
   - Name must be at least 1 character

2. **Check for errors:**
   - Red border around input means error
   - Read error message below input

---

### Issue: Can't delete folder

**Symptoms:**
- Clicking delete doesn't work
- Error when trying to delete

**Causes:**
- Folder has processed emails
- API error

**Solutions:**
1. **Archive folder instead:**
   - Go to Dashboard → Folders
   - Click folder → "Archive"
   - Archived folders don't sort new emails but keep history

2. **Force delete:**
   - Click folder → "Delete"
   - Confirm deletion in popup
   - This removes folder and all sorting history

**If delete fails:**
- Refresh page and retry
- Check browser console for errors
- Contact support

---

## Notification Issues

### Issue: Not receiving any Telegram notifications

**Symptoms:**
- Gmail connected, Telegram linked, folders created, but no notifications

**Causes:**
- Telegram notifications disabled (phone settings)
- Quiet hours active
- Bot chat muted in Telegram
- No new emails matching folders

**Solutions:**
1. **Send test notification:**
   - Go to Dashboard → Settings → Notifications
   - Click "Send Test Notification"
   - Check Telegram for message
   - If received, notifications are working

2. **Check Telegram notification settings:**
   - Open Telegram app
   - Go to Settings → Notifications and Sounds
   - Make sure "Private Chats" notifications are enabled
   - Check @MailAgentBot chat isn't muted

3. **Check Telegram app notifications (Phone Settings):**
   - **iOS**: Settings → Telegram → Notifications → Allow Notifications
   - **Android**: Settings → Apps → Telegram → Notifications → Allowed

4. **Check quiet hours:**
   - Go to Dashboard → Settings → Notifications
   - Check if quiet hours are active right now
   - Temporarily disable quiet hours to test

5. **Verify folders:**
   - Make sure you have at least one active folder
   - Send yourself a test email with folder keywords

6. **Check Telegram chat:**
   - Open @MailAgentBot chat
   - Look for "Notifications enabled" message
   - If says "Notifications disabled", send `/start`

**If still not receiving:**
- Disconnect and reconnect Telegram
- Check Mail Agent server status
- Contact support

---

### Issue: Receiving too many notifications

**Symptoms:**
- Notification overload
- Notification for every single email

**Causes:**
- Batch notifications disabled
- Too many folders matching emails
- Priority settings too broad

**Solutions:**
1. **Enable batch notifications:**
   - Go to Dashboard → Settings → Notifications
   - Toggle "Group notifications together" to ON
   - Set batch frequency (15 min, 30 min, or 1 hour)

2. **Set quiet hours:**
   - Toggle "Quiet Hours" to ON
   - Set start time (e.g., 10 PM)
   - Set end time (e.g., 7 AM)
   - Notifications pause during these hours

3. **Adjust folder keywords:**
   - Review folders with overlapping keywords
   - Make keywords more specific
   - Reduce number of active folders

4. **Adjust priority settings:**
   - Go to Settings → Notifications
   - Review which emails are marked as "Priority"
   - Disable "Send priority emails instantly" temporarily

---

### Issue: Test notification not working

**Symptoms:**
- Clicking "Send Test Notification" does nothing or shows error

**Causes:**
- Telegram not linked
- Bot connection lost
- API error

**Solutions:**
1. **Verify Telegram linked:**
   - Check Dashboard shows "Telegram: Connected"
   - If not, relink Telegram

2. **Check bot chat:**
   - Open @MailAgentBot in Telegram
   - Send any message (e.g., "hi")
   - Bot should respond

3. **Retry:**
   - Wait 10 seconds
   - Click "Send Test Notification" again

**If still failing:**
- Disconnect and reconnect Telegram
- Contact support

---

## Dashboard and UI Issues

### Issue: Dashboard shows "Loading..." forever

**Symptoms:**
- Dashboard page stuck loading
- Spinner never stops

**Causes:**
- API timeout
- Network error
- Backend server down

**Solutions:**
1. **Refresh page:**
   - Press Ctrl+R (Windows) or Cmd+R (Mac)
   - Or click browser refresh button

2. **Check internet:**
   - Open new tab, visit google.com
   - Verify connectivity

3. **Clear cache:**
   - Clear browser cache and cookies
   - Reload Mail Agent

4. **Check browser console:**
   - Press F12 to open DevTools
   - Click "Console" tab
   - Look for red errors
   - Screenshot and send to support if errors present

**If still loading:**
- Try different browser
- Try incognito/private mode
- Check Mail Agent status page
- Contact support

---

### Issue: Dashboard shows old/stale data

**Symptoms:**
- Email counts not updating
- Recent activity not showing new emails
- Changes to folders not reflected

**Causes:**
- Cache issue
- Auto-refresh disabled
- Background sync failed

**Solutions:**
1. **Manual refresh:**
   - Click refresh icon on dashboard (if present)
   - Or refresh browser page

2. **Force reload:**
   - Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
   - This clears cache and reloads

3. **Check auto-refresh:**
   - Dashboard auto-refreshes every 30 seconds
   - Make sure browser tab is active (not in background)

---

### Issue: Can't click buttons or interact with UI

**Symptoms:**
- Buttons don't respond to clicks
- Forms can't be filled
- UI appears frozen

**Causes:**
- JavaScript error
- Browser compatibility issue
- Loading overlay stuck

**Solutions:**
1. **Refresh page:**
   - Press F5 or refresh button

2. **Check browser console:**
   - Press F12
   - Look for JavaScript errors (red text)
   - Screenshot and report to support

3. **Update browser:**
   - Make sure using latest version of Chrome, Firefox, Safari, or Edge
   - Update if outdated

4. **Disable browser extensions:**
   - Disable ad blockers, privacy extensions temporarily
   - Retry interaction

5. **Try different browser:**
   - Test in Chrome (recommended)
   - Test in incognito mode

---

## Browser Compatibility Issues

### Issue: Mail Agent not working in older browser

**Symptoms:**
- Layout broken
- Features not working
- Error messages about browser compatibility

**Supported Browsers:**
- ✅ Chrome 90+ (recommended)
- ✅ Firefox 88+
- ✅ Safari 15+
- ✅ Edge 90+

**Solutions:**
1. **Update browser:**
   - Check browser version: Settings → About
   - Update to latest version
   - Restart browser

2. **Switch browser:**
   - Download Chrome: [google.com/chrome](https://www.google.com/chrome)
   - Use Chrome for best experience

---

### Issue: Layout looks broken on mobile

**Symptoms:**
- Text cut off
- Buttons overlapping
- Horizontal scrolling required

**Causes:**
- Very old mobile browser
- Zoomed in browser
- Unsupported screen size

**Solutions:**
1. **Reset zoom:**
   - Pinch to zoom out to 100%
   - Or: Settings → Zoom → Reset

2. **Update mobile browser:**
   - Update Safari (iOS) or Chrome (Android)
   - Restart browser

3. **Try different orientation:**
   - Rotate device (portrait ↔ landscape)
   - Some features work better in portrait

---

## Performance Issues

### Issue: Mail Agent is slow/laggy

**Symptoms:**
- Pages take long to load
- Animations stuttering
- Typing has delay

**Causes:**
- Slow internet connection
- Too many browser tabs open
- Old device
- Backend server slow

**Solutions:**
1. **Check internet speed:**
   - Run speed test: [speedtest.net](https://www.speedtest.net)
   - Mail Agent needs at least 1 Mbps

2. **Close other tabs:**
   - Close unused browser tabs
   - Close other apps using internet

3. **Clear browser cache:**
   - Settings → Privacy → Clear Browsing Data
   - Select "Cached images and files"
   - Clear and reload

4. **Disable animations:**
   - Settings → Preferences → Disable animations (if available)

5. **Try different time:**
   - If server is slow, try during off-peak hours

---

## Getting Additional Help

### Before Contacting Support

Please gather the following information:

1. **What were you trying to do?**
   - Example: "Connect Gmail account"

2. **What happened instead?**
   - Example: "Got error message 'Connection failed'"

3. **Environment details:**
   - Browser: (Chrome, Firefox, Safari, Edge)
   - Browser version: (Check in Settings → About)
   - Operating System: (Windows, Mac, iOS, Android)
   - Device: (Desktop, phone, tablet)

4. **Screenshots:**
   - Screenshot of error message
   - Screenshot of browser console (F12 → Console tab)

5. **Steps to reproduce:**
   - List exact steps that caused the issue

### Contact Methods

**Email Support:**
- 📧 support@mailagent.app
- Response time: 24-48 hours

**Live Chat:**
- Available on Dashboard (bottom-right chat icon)
- Available Monday-Friday, 9 AM - 5 PM CET

**Community Forum:**
- [Link to forum/Discord]
- Get help from other users

**Bug Reports:**
- GitHub Issues: [Link]
- For technical users reporting bugs

### Emergency Issues

**If you need to immediately stop Mail Agent:**

1. **Disconnect Gmail:**
   - Visit [Google Account Permissions](https://myaccount.google.com/permissions)
   - Find "Mail Agent"
   - Click "Remove Access"

2. **Block Telegram Bot:**
   - Open @MailAgentBot in Telegram
   - Click bot name → Block

3. **Contact support:**
   - Explain the emergency
   - We'll help resolve immediately

---

**Troubleshooting Guide Version:** 1.0
**Last Updated:** 2025-11-14
**Need more help?** support@mailagent.app
