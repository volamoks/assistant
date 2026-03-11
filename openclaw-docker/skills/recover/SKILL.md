---
name: recover
description: "Rollback bot to last git commit (auto-healing)"
triggers:
  - /recover
  - rollback
  - откати бота
  - сделай recover
---

# /recover — Rollback to Last Git Commit

**What it does:**
1. Runs `/data/bot/openclaw-docker/recover.sh`
2. Saves broken config to Obsidian (done by recover.sh)
3. Restarts Gateway
4. Reports result to user

**Usage:**
- `/recover` — manual rollback via native command
- `/skill recover` — alternative via skill command

**Command:**
```bash
bash /data/bot/openclaw-docker/skills/recover/run.sh
```

**Notes:**
- Only for authorized users
- Rolls back to last git commit
- Use when bot is broken after bad config/code change
