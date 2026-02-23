---
name: telegram_reader
description: Monitor Telegram chats/bots as a userbot and dispatch messages to pluggable handlers. Handlers live in workspace/telegram/handlers/. Currently supports HUMO Card finance tracking (humo_pfm handler).
triggers:
  - telegram monitor
  - read telegram
  - watch telegram
  - telegram listener
  - humo finance
  - finance tracker
  - pfm
---

# Telegram Reader — Generic Listener Skill

Runs a persistent Telethon userbot that monitors specified Telegram sources and dispatches messages to pluggable handlers.

## Setup (first time only)

```bash
# Install dependencies on host
pip3 install telethon python-dotenv

# Interactive auth (requires phone + Telegram code)
cd /data/bot/openclaw-docker/workspace/telegram
python3 listener.py --auth
```

## Manage the daemon

```bash
cd /data/bot/openclaw-docker/workspace/telegram
./run.sh start    # start in background
./run.sh stop     # stop
./run.sh restart  # restart
./run.sh status   # check if running + active handlers
./run.sh logs     # tail live logs
```

## Check status

```bash
./run.sh status
cat /data/bot/openclaw-docker/workspace/telegram/listener.log | tail -20
```

## Available handlers

| Handler | Watches | Output |
|---|---|---|
| `humo_pfm` | @HUMOcardbot | `/data/obsidian/Attachments/finance.db` |

## Add a new handler

1. Create `workspace/telegram/handlers/my_handler.py` with class `MyHandler(BaseHandler)`
2. Register in `workspace/telegram/handlers.yaml`:
   ```yaml
   my_handler:
     enabled: true
     watch: ["@somebot"]
   ```
3. `./run.sh restart`

## Query HUMO finances (SQLite)

```bash
# Last 10 transactions
sqlite3 "/data/obsidian/Attachments/finance.db" \
  "SELECT date, time, amount, currency, category, raw_text FROM expenses ORDER BY created_at DESC LIMIT 10;"

# Total by category this month
sqlite3 "/data/obsidian/Attachments/finance.db" \
  "SELECT category, SUM(amount) as total FROM expenses WHERE date >= date('now','start of month') GROUP BY category ORDER BY total DESC;"

# Today's spending
sqlite3 "/data/obsidian/Attachments/finance.db" \
  "SELECT SUM(amount), currency FROM expenses WHERE date = date('now') AND transaction_type = 'debit' GROUP BY currency;"
```

## Notes

- Session file: `workspace/telegram/session.session`
- Userbot runs as your personal Telegram account — can read messages from any bot/chat
- Add multiple usernames to `watch` array to monitor several sources at once
