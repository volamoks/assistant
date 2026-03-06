---
name: telegram
description: Send Telegram notifications with optional inline keyboard buttons. Use for final notifications, alerts, and user communications. Supports Markdown formatting, button callbacks, thread/topic IDs, and silent mode.
triggers:
  - "notify"
  - "send message"
  - "telegram"
  - "alert"
  - "notification"
---

# Telegram Notifications

**Path:** `skills/telegram/`

Unified Telegram notification system with inline keyboard buttons and pluggable action handlers.

## Capabilities

- Send text notifications with Markdown/HTML formatting
- Inline keyboard buttons with callback data
- Pluggable action handlers for button presses
- Edit and delete existing messages
- Thread/topic support for group chats
- Silent mode for non-intrusive notifications

## Files

| File | Description |
|------|-------------|
| [`notify.py`](notify.py) | Main notification client with inline keyboard support |
| [`callback_handler.py`](callback_handler.py) | Callback query handler with pluggable actions |
| [`__init__.py`](__init__.py) | Module exports |
| [`README.md`](README.md) | Full documentation |

## Agent Usage

The `telegram` tool is available to agents for sending notifications directly to Telegram.

### For Agents

```bash
# Basic notification
python3 /home/node/.openclaw/skills/telegram/notify.py "Task completed successfully!"

# With inline keyboard buttons
python3 /home/node/.openclaw/skills/telegram/notify.py "Decision required" \
    --buttons "✅ Approve:approve:task1,❌ Reject:reject:task1"

# To specific chat
python3 /home/node/.openclaw/skills/telegram/notify.py "Alert!" --chat-id "-1001234567890"

# Silent notification
python3 /home/node/.openclaw/skills/telegram/notify.py "Background update" --silent
```

### Tool Selection

- **`telegram`**: Use for final notifications, alerts, and user-facing messages
- **`telegram_progress`**: Use for status updates during long-running tasks (edits existing message)

## Quick Usage

### Send Notification

```bash
python3 /data/bot/openclaw-docker/skills/telegram/notify.py \
    "Task #5: Fix bug" \
    --buttons "✅ Apply:apply:5,📋 Show:show:5,⏭️ Skip:skip:5"
```

### Run Callback Handler

```bash
python3 /data/bot/openclaw-docker/skills/telegram/callback_handler.py
```

### Python API

```python
from telegram.notify import TelegramNotifier

notifier = TelegramNotifier()
result = notifier.send(
    "Hello!",
    buttons="✅ Yes:confirm,No:cancel"
)
```

## Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="1234567890:ABCdef..."
export TELEGRAM_CHAT_ID="-1001234567890"
export VIKUNJA_URL="http://localhost:3456/api/v1"  # For Vikunja integration
export VIKUNJA_TOKEN="your-token"
```

## Integration Examples

### Vikunja Task Notification

```bash
/data/bot/openclaw-docker/skills/vikunja/vikunja_notify.sh \
    send-task-notification 123
```

### Agent Decision Request

```python
from telegram.notify import TelegramNotifier

notifier = TelegramNotifier(chat_id="-1001234567890")
notifier.send(
    "🤖 Decision Required\n\nDeploy to production?",
    buttons="✅ Approve:approve:deploy,❌ Reject:reject:deploy"
)
```

### Cron Job Integration

```bash
# Morning briefing
0 8 * * * python3 /data/bot/openclaw-docker/skills/telegram/notify.py \
    "☀️ Morning Briefing" \
    --buttons "📊 Report:report,🔧 Tasks:tasks"
```

## Related Skills

- [`vikunja/`](../vikunja/) - Task management integration
- [`agent-memory/`](../agent-memory/) - Agent memory for tracking decisions
