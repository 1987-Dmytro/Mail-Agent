# Telegram Bot API Guide for Epic 2
**Created:** 2025-11-06
**For:** Stories 2.4-2.7 (Bot Foundation, Linking, Proposals, Buttons)
**Bot:** @June_25_AMB_bot
**Token:** `7223802190:AAHCN-N0nmQIXS_J1StwX_urv2ddeSnCMjo`

---

## 📚 Overview

We'll use **python-telegram-bot** library (most popular, well-documented Python wrapper for Telegram Bot API).

**Our Use Cases:**
- ✅ Story 2.4: Bot foundation (send/receive messages, basic commands)
- ✅ Story 2.5: User-Telegram linking (generate codes, link accounts)
- ✅ Story 2.6: Email sorting proposals (messages with inline buttons)
- ✅ Story 2.7: Button callback handling (approve/reject/change folder)

---

## 🎯 Core Concepts

### 1. **Bot Basics**
A Telegram bot is controlled via HTTP API:
- **Bot Token** = Authentication credential (keep secret!)
- **Updates** = Messages, button clicks, commands from users
- **Methods** = Actions bot can perform (send message, edit message, etc.)

### 2. **Two Modes of Operation**

**Polling Mode** (simpler, good for development):
```python
# Bot actively checks for updates every few seconds
application.run_polling()
```

**Webhook Mode** (better for production):
```python
# Telegram sends updates to your server URL
application.run_webhook(
    listen="0.0.0.0",
    port=8443,
    url_path="telegram-webhook",
    webhook_url="https://yourdomain.com/telegram-webhook"
)
```

**For Epic 2:** Start with **polling mode** (Story 2.4), migrate to webhook later if needed.

---

### 3. **Message Types**
- **Text messages** - Simple text from/to user
- **Commands** - Special messages starting with `/` (e.g., `/start`, `/help`)
- **Inline buttons** - Clickable buttons attached to messages
- **Callback queries** - Events when user clicks inline button

---

### 4. **Inline Keyboards (Critical for Stories 2.6-2.7)**

Inline keyboards = buttons attached to messages:

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Create buttons
keyboard = [
    [
        InlineKeyboardButton("✅ Approve", callback_data="approve"),
        InlineKeyboardButton("❌ Reject", callback_data="reject")
    ],
    [
        InlineKeyboardButton("📁 Change Folder", callback_data="change_folder")
    ]
]

# Attach to message
reply_markup = InlineKeyboardMarkup(keyboard)
await context.bot.send_message(
    chat_id=user_telegram_id,
    text="Should I move this email to 'Government'?",
    reply_markup=reply_markup
)
```

**Callback Data:**
- Max 64 bytes
- Used to identify which button was clicked
- Can encode information (e.g., `"approve:email_123"`)

---

## 🛠️ Implementation Patterns

### Story 2.4: Bot Foundation

#### Setup Bot Application

```python
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import os

# Get bot token from environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # 7223802190:AAHCN-N0nmQIXS_J1StwX_urv2ddeSnCMjo

# Create application
application = Application.builder().token(BOT_TOKEN).build()

# Add handlers (commands, messages, callbacks)
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CallbackQueryHandler(button_callback))

# Start bot (polling mode)
await application.initialize()
await application.start()
await application.updater.start_polling()

# Keep running
await application.updater.idle()
```

---

#### Basic Command Handlers

```python
async def start_command(update: Update, context):
    """Handle /start command"""
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! 👋\n\n"
        "I'm your Mail Agent assistant. I'll help you sort emails!\n\n"
        "Use /help to see available commands."
    )

async def help_command(update: Update, context):
    """Handle /help command"""
    help_text = """
📧 *Mail Agent Bot Commands*

/start - Start the bot
/help - Show this help message
/link [code] - Link your Telegram account with Mail Agent
/status - Check your connection status
/settings - Configure notification preferences

Need help? Contact support@mailagent.com
    """
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown"
    )
```

---

#### Test Endpoint (Verify Bot Connectivity)

```python
async def test_send_message(user_telegram_id: int, bot_token: str):
    """Test function to verify bot can send messages"""
    from telegram import Bot

    bot = Bot(token=bot_token)

    try:
        message = await bot.send_message(
            chat_id=user_telegram_id,
            text="🤖 Test message from Mail Agent!\n\nBot is working correctly! ✅"
        )
        return {"success": True, "message_id": message.message_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

### Story 2.5: User-Telegram Account Linking

#### Generate Linking Code

```python
import secrets
import string
from datetime import datetime, timedelta

async def generate_linking_code(user_id: int, db_session) -> str:
    """Generate unique 6-digit linking code"""

    # Generate random code
    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

    # Set expiration (15 minutes)
    expires_at = datetime.now() + timedelta(minutes=15)

    # Save to database
    await db_session.execute(
        """
        INSERT INTO linking_codes (code, user_id, expires_at, used)
        VALUES (:code, :user_id, :expires_at, false)
        """,
        {"code": code, "user_id": user_id, "expires_at": expires_at}
    )
    await db_session.commit()

    return code
```

---

#### Link Command Handler

```python
async def link_command(update: Update, context):
    """Handle /start [code] command for account linking"""

    # Extract code from command args
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ No linking code provided!\n\n"
            "Usage: /start YOUR_CODE\n\n"
            "Get your linking code from Mail Agent web app."
        )
        return

    code = context.args[0].upper()
    telegram_user_id = update.effective_user.id
    telegram_username = update.effective_user.username

    # Validate code
    result = await db.validate_and_link_code(
        code=code,
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username
    )

    if result["success"]:
        await update.message.reply_text(
            "✅ *Account Linked Successfully!*\n\n"
            f"Your Telegram account is now connected to Mail Agent.\n\n"
            f"You'll receive email sorting proposals here. 📧\n\n"
            "Use /help to see available commands.",
            parse_mode="Markdown"
        )
    elif result["error"] == "expired":
        await update.message.reply_text(
            "❌ *Linking Code Expired*\n\n"
            "This code expired after 15 minutes.\n\n"
            "Please generate a new code in Mail Agent web app."
        )
    elif result["error"] == "already_used":
        await update.message.reply_text(
            "❌ *Code Already Used*\n\n"
            "This linking code has already been used.\n\n"
            "Please generate a new code if needed."
        )
    else:
        await update.message.reply_text(
            "❌ *Invalid Linking Code*\n\n"
            "Code not found. Please check and try again."
        )
```

---

#### Database Validation Logic

```python
async def validate_and_link_code(code: str, telegram_user_id: int, telegram_username: str, db_session):
    """Validate linking code and update user record"""

    # Find code in database
    result = await db_session.execute(
        """
        SELECT user_id, expires_at, used
        FROM linking_codes
        WHERE code = :code
        """,
        {"code": code}
    )
    row = result.fetchone()

    if not row:
        return {"success": False, "error": "invalid"}

    user_id, expires_at, used = row

    # Check if expired
    if datetime.now() > expires_at:
        return {"success": False, "error": "expired"}

    # Check if already used
    if used:
        return {"success": False, "error": "already_used"}

    # Mark code as used
    await db_session.execute(
        """
        UPDATE linking_codes
        SET used = true
        WHERE code = :code
        """,
        {"code": code}
    )

    # Update user record with telegram_id
    await db_session.execute(
        """
        UPDATE users
        SET telegram_id = :telegram_id, telegram_username = :telegram_username
        WHERE id = :user_id
        """,
        {
            "telegram_id": telegram_user_id,
            "telegram_username": telegram_username,
            "user_id": user_id
        }
    )

    await db_session.commit()

    return {"success": True, "user_id": user_id}
```

---

### Story 2.6: Email Sorting Proposal Messages

#### Send Proposal with Inline Buttons

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def send_sorting_proposal(
    bot_token: str,
    user_telegram_id: int,
    email_data: dict
) -> int:
    """
    Send email sorting proposal to user via Telegram

    Returns: telegram_message_id for tracking callbacks
    """
    from telegram import Bot

    bot = Bot(token=bot_token)

    # Format message text
    message_text = f"""
📧 *New Email to Sort*

*From:* {email_data['sender']}
*Subject:* {email_data['subject']}

_{email_data['body_preview'][:100]}..._

---

🤖 *AI Suggestion:* {email_data['suggested_folder']}
💡 *Reasoning:* {email_data['reasoning']}
    """

    # Create inline keyboard with buttons
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Approve",
                callback_data=f"approve:{email_data['email_id']}"
            ),
            InlineKeyboardButton(
                "❌ Reject",
                callback_data=f"reject:{email_data['email_id']}"
            )
        ],
        [
            InlineKeyboardButton(
                "📁 Change Folder",
                callback_data=f"change:{email_data['email_id']}"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send message
    message = await bot.send_message(
        chat_id=user_telegram_id,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

    return message.message_id
```

---

#### Priority Email with Special Icon

```python
async def send_priority_email_proposal(
    bot_token: str,
    user_telegram_id: int,
    email_data: dict
) -> int:
    """Send high-priority email proposal (immediate notification)"""
    from telegram import Bot

    bot = Bot(token=bot_token)

    # Add priority indicator
    message_text = f"""
⚠️ *PRIORITY EMAIL* ⚠️

📧 *New Email Needs Immediate Attention*

*From:* {email_data['sender']}
*Subject:* {email_data['subject']}

_{email_data['body_preview'][:100]}..._

---

🤖 *AI Suggestion:* {email_data['suggested_folder']}
💡 *Reasoning:* {email_data['reasoning']}
    """

    # Same buttons as regular proposal
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve:{email_data['email_id']}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject:{email_data['email_id']}")
        ],
        [
            InlineKeyboardButton("📁 Change Folder", callback_data=f"change:{email_data['email_id']}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send with notification (not silent)
    message = await bot.send_message(
        chat_id=user_telegram_id,
        text=message_text,
        parse_mode="Markdown",
        reply_markup=reply_markup,
        disable_notification=False  # Ensure notification sound
    )

    return message.message_id
```

---

### Story 2.7: Button Callback Handling

#### Register Callback Handler

```python
from telegram.ext import CallbackQueryHandler

# Add to application setup
application.add_handler(CallbackQueryHandler(handle_button_callback))
```

---

#### Main Callback Handler

```python
async def handle_button_callback(update: Update, context):
    """Handle all inline button clicks"""

    query = update.callback_query
    telegram_user_id = query.from_user.id
    callback_data = query.data  # e.g., "approve:123", "reject:456", "change:789"

    # Acknowledge callback (remove loading state)
    await query.answer()

    # Parse callback data
    action, email_id = callback_data.split(":", 1)
    email_id = int(email_id)

    # Verify user owns this email workflow
    workflow_mapping = await db.get_workflow_mapping(email_id=email_id)
    if not workflow_mapping or workflow_mapping["user_id"] != get_user_id_from_telegram(telegram_user_id):
        await query.answer("❌ Unauthorized", show_alert=True)
        return

    # Handle different actions
    if action == "approve":
        await handle_approve(query, email_id, workflow_mapping)
    elif action == "reject":
        await handle_reject(query, email_id, workflow_mapping)
    elif action == "change":
        await handle_change_folder(query, email_id, workflow_mapping)
    elif action.startswith("select_folder"):
        # Format: "select_folder:folder_name:email_id"
        _, folder_name, email_id = callback_data.split(":", 2)
        await handle_folder_selection(query, email_id, folder_name, workflow_mapping)
```

---

#### Approve Handler

```python
async def handle_approve(query, email_id: int, workflow_mapping: dict):
    """Handle approve button click"""

    # Resume LangGraph workflow with approval
    thread_id = workflow_mapping["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    await langgraph_app.ainvoke(
        {"user_action": "approve"},
        config=config
    )

    # Update button message to show approved
    await query.edit_message_text(
        text=query.message.text + "\n\n✅ *APPROVED* - Email sorted!",
        parse_mode="Markdown"
    )

    # Send confirmation
    suggested_folder = workflow_mapping["suggested_folder"]
    await query.message.reply_text(
        f"✅ Email sorted to *{suggested_folder}*!",
        parse_mode="Markdown"
    )
```

---

#### Reject Handler

```python
async def handle_reject(query, email_id: int, workflow_mapping: dict):
    """Handle reject button click"""

    # Resume LangGraph workflow with rejection
    thread_id = workflow_mapping["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    await langgraph_app.ainvoke(
        {"user_action": "reject"},
        config=config
    )

    # Update button message
    await query.edit_message_text(
        text=query.message.text + "\n\n❌ *REJECTED* - Email left in inbox",
        parse_mode="Markdown"
    )

    await query.message.reply_text(
        "❌ Sorting rejected. Email remains in inbox."
    )
```

---

#### Change Folder Handler (Show Folder List)

```python
async def handle_change_folder(query, email_id: int, workflow_mapping: dict):
    """Show folder selection menu"""

    # Get user's folder categories
    user_id = workflow_mapping["user_id"]
    folders = await db.get_user_folder_categories(user_id)

    # Create button for each folder
    keyboard = []
    for folder in folders:
        keyboard.append([
            InlineKeyboardButton(
                f"📁 {folder['name']}",
                callback_data=f"select_folder:{folder['name']}:{email_id}"
            )
        ])

    # Add cancel button
    keyboard.append([
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{email_id}")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Update message to show folder selection
    await query.edit_message_reply_markup(reply_markup=reply_markup)
    await query.answer("Select folder:")
```

---

#### Folder Selection Handler

```python
async def handle_folder_selection(query, email_id: int, folder_name: str, workflow_mapping: dict):
    """Handle folder selection from change menu"""

    # Resume LangGraph workflow with selected folder
    thread_id = workflow_mapping["thread_id"]
    config = {"configurable": {"thread_id": thread_id}}

    await langgraph_app.ainvoke(
        {
            "user_action": "change",
            "selected_folder": folder_name
        },
        config=config
    )

    # Update message
    await query.edit_message_text(
        text=query.message.text + f"\n\n📁 *MOVED* to {folder_name}",
        parse_mode="Markdown"
    )

    await query.message.reply_text(
        f"✅ Email moved to *{folder_name}*!",
        parse_mode="Markdown"
    )
```

---

## 📦 Dependencies

Add to `requirements.txt`:

```txt
python-telegram-bot>=20.0
```

**Note:** Version 20+ is async-native (uses `async`/`await`), perfect for FastAPI integration.

---

## 🧪 Testing Telegram Bot Locally

### 1. Test Bot Connectivity

```python
import asyncio
from telegram import Bot

async def test_bot():
    bot = Bot(token="7223802190:AAHCN-N0nmQIXS_J1StwX_urv2ddeSnCMjo")

    # Get bot info
    me = await bot.get_me()
    print(f"Bot username: @{me.username}")
    print(f"Bot ID: {me.id}")

    # Test sending message (replace with your Telegram ID)
    # Get your ID by messaging @userinfobot on Telegram
    your_telegram_id = 123456789  # Replace with your ID

    message = await bot.send_message(
        chat_id=your_telegram_id,
        text="🤖 Test message from Mail Agent bot!"
    )
    print(f"Message sent! ID: {message.message_id}")

asyncio.run(test_bot())
```

---

### 2. Test Inline Buttons

```python
async def test_buttons():
    bot = Bot(token="7223802190:AAHCN-N0nmQIXS_J1StwX_urv2ddeSnCMjo")
    your_telegram_id = 123456789  # Your Telegram ID

    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data="test_approve"),
            InlineKeyboardButton("❌ Reject", callback_data="test_reject")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(
        chat_id=your_telegram_id,
        text="Test email sorting proposal:\n\nFrom: test@example.com\nShould I sort to 'Government'?",
        reply_markup=reply_markup
    )
    print("Button test message sent!")

asyncio.run(test_buttons())
```

---

### 3. Run Bot with Polling (Development)

```python
from telegram.ext import Application, CommandHandler

async def start(update, context):
    await update.message.reply_text("Hello from Mail Agent! 👋")

async def main():
    app = Application.builder().token("7223802190:AAHCN-N0nmQIXS_J1StwX_urv2ddeSnCMjo").build()
    app.add_handler(CommandHandler("start", start))

    print("Bot starting... Press Ctrl+C to stop")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
```

Then open Telegram and send `/start` to @June_25_AMB_bot!

---

## ⚠️ Security Best Practices

1. **Never commit bot token to Git**
   - Store in `.env` file
   - Add `.env` to `.gitignore`

2. **Validate callback ownership**
   ```python
   # Always check user owns the email before processing callback
   if workflow_mapping["user_id"] != current_user_id:
       await query.answer("Unauthorized", show_alert=True)
       return
   ```

3. **Limit callback_data size**
   - Max 64 bytes
   - Use email IDs, not full data: `"approve:123"` not `"approve:user@example.com:subject:..."`

4. **Rate limiting**
   - Telegram has rate limits (30 messages/second to same user)
   - Don't spam users with notifications

---

## 📚 Key python-telegram-bot Patterns

### Sending Messages

```python
# Simple text
await bot.send_message(chat_id=user_id, text="Hello!")

# With markdown formatting
await bot.send_message(
    chat_id=user_id,
    text="*Bold* _italic_ `code`",
    parse_mode="Markdown"
)

# With buttons
await bot.send_message(
    chat_id=user_id,
    text="Choose action:",
    reply_markup=InlineKeyboardMarkup(keyboard)
)
```

---

### Editing Messages

```python
# Edit text
await bot.edit_message_text(
    chat_id=user_id,
    message_id=message_id,
    text="Updated text"
)

# Edit buttons only
await bot.edit_message_reply_markup(
    chat_id=user_id,
    message_id=message_id,
    reply_markup=new_keyboard
)
```

---

### Handling Errors

```python
from telegram.error import TelegramError, Forbidden

try:
    await bot.send_message(chat_id=user_id, text="Hello")
except Forbidden:
    # User blocked the bot
    print(f"User {user_id} blocked the bot")
    await db.mark_user_telegram_blocked(user_id)
except TelegramError as e:
    # Other Telegram API errors
    print(f"Telegram error: {e}")
```

---

## ✅ Key Takeaways for Stories 2.4-2.7

1. **python-telegram-bot v20+** = Async-native, perfect for FastAPI
2. **Polling mode** = Easy for development, start with this
3. **InlineKeyboardButton** = Clickable buttons for user actions
4. **callback_data** = Encodes action + email_id for routing
5. **CallbackQueryHandler** = Handles button click events
6. **Workflow reconnection** = Use thread_id from WorkflowMapping table
7. **Security** = Always validate user owns email before processing

---

## 🔗 Official Resources

- **python-telegram-bot Docs:** https://docs.python-telegram-bot.org/
- **Telegram Bot API Reference:** https://core.telegram.org/bots/api
- **Examples:** https://github.com/python-telegram-bot/python-telegram-bot/tree/master/examples

---

## 🎯 Next Steps

After understanding this guide:

1. ✅ Test bot connectivity locally (send test message)
2. ✅ Test inline buttons (create proposal mock)
3. ✅ Test callback handling (click buttons, see responses)
4. ✅ Ready to implement Stories 2.4-2.7!

---

**Status:** 📱 Telegram Bot guide complete - ready for Epic 2 implementation!
