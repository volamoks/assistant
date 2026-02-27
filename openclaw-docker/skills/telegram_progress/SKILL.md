---
name: telegram_progress
description: Updates an active status message in Telegram to show what the agent or subagents are currently doing without spamming the chat. Use this BEFORE starting a long-running subagent or task, and AFTER it finishes.
triggers:
  - "*"
  - "use subagent"
  - "coder"
  - "researcher"
  - "analyst"
  - "task"
  - "report progress"
  - "update status"
---

# Telegram Progress Tracker

Use this tool to keep the user informed about what you are currently working on. It edits a single "Status" message in Telegram, ensuring the chat stays clean.

**IMPORTANT:** Always use this tool *before* starting a `subagents` call, or *before* starting a slow script or long research task.

### How to use

Run the tracker script with your current status action.

```bash
# General format
python3 /home/node/.openclaw/skills/telegram_progress/tracker.py "Your status message here"

# Examples
python3 /home/node/.openclaw/skills/telegram_progress/tracker.py "⏳ Launching Coder subagent to refactor auth.py..."
python3 /home/node/.openclaw/skills/telegram_progress/tracker.py "✅ Coder finished. ⏳ Analyst reviewing changes..."
python3 /home/node/.openclaw/skills/telegram_progress/tracker.py "✅ Task complete. Formatting final answer."
```

If you want to clear the status message state (start a new fresh status message next time), you can pass `--clear`:
```bash
python3 /home/node/.openclaw/skills/telegram_progress/tracker.py --clear
```
