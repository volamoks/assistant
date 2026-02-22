---
name: alive
description: "Owner-only diagnostic. Reports bot health: container status, active model, last heartbeat, and any recent errors."
---

# /alive — Bot Health Check

This is an owner-only status command. Perform a quick system health check and report back.

## Steps

1. **Container status** — Call sysadmin agent with: `docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}" | grep -E "openclaw|litellm|ollama"`

2. **Recent errors** — Call sysadmin agent with: `docker logs openclaw-latest --tail 30 2>&1 | grep -iE "error|crash|SIGTERM|restart" | tail -10`

3. **Summarize** — Report in this format:

```
🟢 Bot is alive (or 🔴 issues detected)

Container: <status>
Uptime: <running for>

Recent errors: <none / or list last 2-3 relevant lines>

Model: <current primary model from openclaw.json>
Heartbeat: every 15m via ollama/llama3.2:1b
```

## Owner-Only

If this command is invoked from a group chat or by someone other than the owner, refuse politely: "This command is owner-only."

Since this is a personal bot, the owner is the sole Telegram user who configured it.
