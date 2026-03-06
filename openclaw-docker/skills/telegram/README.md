# Telegram Notification Module

Unified, isolated Telegram notification system for the OpenClaw ecosystem. Can be used by any tool, agent, cron job, or script.

## Features

- **Send notifications** with Markdown/HTML formatting
- **Inline keyboard buttons** with callback data
- **Pluggable action handlers** for button presses
- **Edit and delete** existing messages
- **Thread/topic support** for group chats
- **Silent mode** for non-intrusive notifications
- **State persistence** for callback handler
- **Environment-based configuration**

## Components

| File | Description |
|------|-------------|
| [`notify.py`](notify.py) | Main notification client with inline keyboard support |
| [`callback_handler.py`](callback_handler.py) | Callback query handler with pluggable actions |
| [`telegram_send.py`](telegram_send.py) | Legacy CLI wrapper (deprecated, use notify.py) |
| [`telegram_callback_handler.py`](telegram_callback_handler.py) | Legacy handler (deprecated, use callback_handler.py) |

## Quick Start

### 1. Set Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="-1001234567890"  # Optional, can specify per-message
```

### 2. Send a Notification

```bash
# Basic message
python3 /data/bot/openclaw-docker/skills/telegram/notify.py "Hello, World!"

# With buttons
python3 /data/bot/openclaw-docker/skills/telegram/notify.py \
    "Task #5: Fix bug" \
    --buttons "✅ Apply:apply:5,📋 Show:show:5,⏭️ Skip:skip:5"

# To specific chat
python3 /data/bot/openclaw-docker/skills/telegram/notify.py \
    "Alert!" \
    --chat-id "-1001234567890"
```

### 3. Run Callback Handler

```bash
# Start polling for button presses
python3 /data/bot/openclaw-docker/skills/telegram/callback_handler.py
```

## Usage: notify.py

### CLI Options

```
usage: notify.py [-h] [--buttons BUTTONS] [--chat-id CHAT_ID] [--thread-id THREAD_ID]
                 [--silent] [--parse-mode {Markdown,HTML,None}] [--edit-chat EDIT_CHAT]
                 [--edit-msg EDIT_MSG] [--delete-chat DELETE_CHAT] [--delete-msg DELETE_MSG]
                 [--callback-id CALLBACK_ID] [--callback-text CALLBACK_TEXT] [--callback-alert]
                 [text]

Examples:
    # Basic message
    python3 notify.py "Hello, World!"

    # With inline keyboard buttons
    python3 notify.py "Task #5" --buttons "✅ Apply:apply:5,⏭️ Skip:skip:5"

    # Send to specific chat
    python3 notify.py "Alert" --chat-id "-1001234567890"

    # Send in a topic/thread
    python3 notify.py "Update" --thread-id "123"

    # Edit existing message
    python3 notify.py "Updated" --edit-chat "-1001234567890" --edit-msg "456"

    # Delete message
    python3 notify.py "" --delete-chat "-1001234567890" --delete-msg "789"
```

### Button Format

```
"Btn1:callback1,Btn2:callback2|Row2Btn1:cb3,Row2Btn2:cb4"
```

- **Comma (,)** separates buttons within a row
- **Pipe (|)** separates rows
- **Callback data** max 64 bytes (Telegram limit)

Examples:
```bash
# Single row
--buttons "✅ Yes:confirm,No:cancel"

# Multiple rows
--buttons "Apply:apply:1,Show:show:1|Skip:skip,Delete:delete:1"

# Complex layout
--buttons "📊 Stats:stats,🔍 Details:details:1|✅ Done:done:1,❌ Reject:reject:1"
```

### Python API

```python
from telegram.notify import TelegramNotifier

# Initialize
notifier = TelegramNotifier(
    bot_token="1234567890:ABCdef...",  # Or set TELEGRAM_BOT_TOKEN
    chat_id="-1001234567890",          # Or set TELEGRAM_CHAT_ID
    thread_id=123,                      # Optional: topic/thread ID
    parse_mode="Markdown"
)

# Send basic message
result = notifier.send("Hello, World!")

# Send with buttons
result = notifier.send(
    "Task #5: Fix bug",
    buttons="✅ Apply:apply:5,📋 Show:show:5,⏭️ Skip:skip:5"
)

# Send with buttons (programmatic)
result = notifier.send(
    "Choose action:",
    buttons="Btn1:cb1,Btn2:cb2|Btn3:cb3"
)

# Edit message
notifier.edit(
    chat_id="-1001234567890",
    message_id=123,
    text="Updated text",
    buttons="New:button:1"
)

# Edit only buttons (remove keyboard)
notifier.edit_reply_markup(
    chat_id="-1001234567890",
    message_id=123,
    buttons=None  # Remove keyboard
)

# Delete message
notifier.delete(chat_id="-1001234567890", message_id=123)

# Answer callback query
notifier.answer_callback(
    callback_query_id="abc123",
    text="Processing...",
    show_alert=False  # True for popup alert
)
```

## Usage: callback_handler.py

### CLI

```bash
# Run in polling mode
python3 /data/bot/openclaw-docker/skills/telegram/callback_handler.py

# Custom poll interval
TELEGRAM_POLL_INTERVAL=5 python3 callback_handler.py

# Test configuration
python3 callback_handler.py --test
```

### Python API with Custom Handlers

```python
from telegram.callback_handler import CallbackHandler

# Initialize
handler = CallbackHandler()

# Register custom handler
def my_custom_handler(target, chat_id, msg_id, user):
    """
    Custom action handler.
    
    Args:
        target: The target data from callback (e.g., "5" from "myaction:5")
        chat_id: Chat ID where button was pressed
        msg_id: Message ID that was clicked
        user: Dict with user info (username, id, etc.)
    
    Returns:
        Tuple of (response_text, show_alert)
        - response_text: Text to show user
        - show_alert: True for popup, False for toast notification
    """
    # Your logic here
    print(f"User {user.get('username')} clicked {target}")
    return f"Handled: {target}", False

handler.register("myaction", my_custom_handler)

# Run polling
handler.run_polling()
```

### Built-in Handlers

| Action | Description | Callback Format |
|--------|-------------|-----------------|
| `apply` | Apply/implement something | `apply:target_id` |
| `show` | Show details | `show:target_id` |
| `skip` | Skip item | `skip:target_id` |
| `vikunja` | Vikunja task management | `vikunja:done:12`, `vikunja:delete:12` |

### Vikunja Integration

The `vikunja` handler requires additional environment variables:

```bash
export VIKUNJA_URL="http://localhost:3456/api/v1"
export VIKUNJA_TOKEN="your-vikunja-api-token"
```

## Integration Examples

### 1. Nightly Analysis Report

```bash
#!/bin/bash
# Send nightly analysis results with action buttons

TASKS=$(cat /tmp/nightly_issues.json | jq -r '.issues[]')
BUTTONS=""

for task in $TASKS; do
    ID=$(echo "$task" | jq -r '.id')
    TITLE=$(echo "$task" | jq -r '.title')
    BUTTONS="$BUTTONS#$ID:apply:$ID,"
done

python3 /data/bot/openclaw-docker/skills/telegram/notify.py \
    "🔧 Nightly Analysis Results\n\n$TASKS" \
    --buttons "${BUTTONS}|⏭️ Skip All:skip_all"
```

### 2. Vikunja Task Notification

```python
from telegram.notify import TelegramNotifier

notifier = TelegramNotifier()

# Send task notification
result = notifier.send(
    "🔴 **HIGH PRIORITY**\n\n"
    "**Task #123:** Fix authentication bug\n\n"
    "The OAuth token expires prematurely.",
    buttons="✅ Apply:apply:123,📋 Details:show:123|⏭️ Skip:skip:123"
)

print(f"Sent message ID: {result['result']['message_id']}")
```

### 3. Custom Agent Integration

```python
from telegram.notify import TelegramNotifier

class AgentNotifier:
    def __init__(self, chat_id: str):
        self.notifier = TelegramNotifier(chat_id=chat_id)
    
    def send_decision_request(self, decision: dict):
        """Send decision request to human operator."""
        buttons = (
            f"✅ Approve:approve:{decision['id']},"
            f"❌ Reject:reject:{decision['id']}|"
            f"📋 Details:details:{decision['id']}"
        )
        return self.notifier.send(
            f"🤖 Agent Decision Required\n\n"
            f"**Decision #{decision['id']}**\n"
            f"{decision['description']}\n\n"
            f"Confidence: {decision['confidence']:.0%}",
            buttons=buttons
        )
    
    def send_status_update(self, status: str, details: str = ""):
        """Send status update (no buttons)."""
        return self.notifier.send(f"📊 **Status Update**\n\n{status}\n{details}")

# Usage
agent = AgentNotifier(chat_id="-1001234567890")
agent.send_decision_request({
    "id": "42",
    "description": "Deploy to production",
    "confidence": 0.95
})
```

### 4. Cron Job Integration

```bash
# In crontab or docker-compose cron

# Morning briefing with interactive buttons
0 8 * * * python3 /data/bot/openclaw-docker/skills/telegram/notify.py \
    "☀️ Morning Briefing\n\n$(/data/bot/openclaw-docker/scripts/morning_briefing.sh)" \
    --buttons "📊 Full Report:report,🔧 Tasks:tasks|⏭️ Skip:skip"

# Vikunja weekly review
0 9 * * 1 python3 /data/bot/openclaw-docker/skills/telegram/notify.py \
    "📋 Weekly Review\n\n$(/data/bot/openclaw-docker/skills/vikunja/vikunja.sh weekly-report)" \
    --buttons "✅ Done:vikunja:done:all,🗑️ Cleanup:vikunja:delete:old"
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | (required) |
| `TELEGRAM_CHAT_ID` | Default chat ID for messages | (optional) |
| `TELEGRAM_THREAD_ID` | Default thread/topic ID | 0 |
| `TELEGRAM_POLL_INTERVAL` | Callback handler poll interval | 2 |
| `TELEGRAM_STATE_FILE` | State file for offset persistence | /tmp/telegram_callback_offset.txt |
| `VIKUNJA_URL` | Vikunja API URL | http://localhost:3456/api/v1 |
| `VIKUNJA_TOKEN` | Vikunja API token | (required for vikunja actions) |

## Getting Chat ID

1. Add your bot to a group/channel
2. Send a message in the group
3. Get updates: `curl "https://api.telegram.org/bot<TOKEN>/getUpdates"`
4. Find `"chat":{"id":-1001234567890,...}` in the response

For private chats, just message the bot and check the update.

## Error Handling

The module handles common errors:

- **HTTP 400**: Bad request (invalid chat_id, message_id, etc.)
- **HTTP 401**: Unauthorized (invalid bot token)
- **HTTP 403**: Forbidden (bot not in chat, no permissions)
- **HTTP 429**: Rate limited (too many requests)

Check return values:

```python
result = notifier.send("Hello!")
if result and result.get("ok"):
    print("Sent successfully")
else:
    print(f"Failed: {result}")
```

## Migration from Legacy Modules

### From telegram_send.py

**Old:**
```bash
python3 telegram_send.py "Message" "Btn1:cb1,Btn2:cb2"
```

**New:**
```bash
python3 notify.py "Message" --buttons "Btn1:cb1,Btn2:cb2"
```

### From telegram_callback_handler.py

The new `callback_handler.py` is a drop-in replacement with better structure:

```bash
# Just replace the import
python3 callback_handler.py  # Instead of telegram_callback_handler.py
```

## Best Practices

1. **Keep callback data short** - Max 64 bytes
2. **Use meaningful prefixes** - `vikunja:done:12` not `a:b:12`
3. **Handle errors gracefully** - Check return values
4. **Remove keyboards after action** - Use `edit_reply_markup(..., buttons=None)`
5. **Use silent mode for non-urgent** - `--silent` flag or `silent=True`
6. **Persist state** - Don't lose callback offset on restart
