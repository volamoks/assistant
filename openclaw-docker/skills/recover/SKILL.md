---
name: recover
description: "OWNER-ONLY. Emergency config recovery and full deploy safety cycle. Use for: emergency rollback (/recover), pre-deploy checkpoint, post-deploy health test, failure analysis. The complete cycle is: checkpoint → make changes → test → if failed: auto-rollback + analyze + learn."
triggers:
  - /recover
  - recover
  - rollback
  - emergency restore
  - bot broken
  - checkpoint
  - deploy test
  - deploy cycle
  - health test
  - восстановление
  - откат
---

# Recover & Deploy Cycle

**OWNER-ONLY.** Emergency recovery and safe deployment for self-modifications.

---

## 🚨 Emergency Recovery (bot broken NOW)

```bash
bash /data/bot/openclaw-docker/recover.sh
```

This: saves broken config → Obsidian crash log, restores last git commit, notifies Telegram, restarts container.

---

## 🔄 Full Deploy Safety Cycle

Use this whenever making config changes (openclaw.json, agents, cron, litellm, etc):

### Step 1 — Checkpoint (before making changes)
```bash
bash /data/bot/openclaw-docker/scripts/deploy_cycle.sh checkpoint
```
Commits current state as recovery baseline. Safe to skip if already clean (`git status` shows nothing).

### Step 2 — Make your changes
Edit files normally. The checkpoint is your rollback point.

### Step 3 — Test (after changes)
```bash
bash /data/bot/openclaw-docker/scripts/deploy_cycle.sh test
```
Restarts container and waits for gateway on port 18789.
- ✅ Healthy → continue to Step 4
- ❌ Unhealthy → **auto-rollback** + saves crash config + runs failure analysis + writes lesson to `.learnings/ERRORS.md` + Telegram notification

### Step 4 — Commit new baseline (after successful test)
```bash
bash /data/bot/openclaw-docker/scripts/deploy_cycle.sh commit "what you changed"
```

---

## 🔍 Status Check
```bash
bash /data/bot/openclaw-docker/scripts/deploy_cycle.sh status
```
Shows: modified files, last 5 commits, gateway health, watchdog failure count.

---

## 🧠 Failure Analysis (manual)
```bash
bash /data/bot/openclaw-docker/scripts/analyze_failure.sh [crash_file] [trigger]
```
Reads crash state → asks LLM why it failed → writes lesson to `.learnings/ERRORS.md` → commits → notifies Telegram.

Runs automatically after watchdog rollback and deploy_cycle test failure.

---

## 📚 Lessons Learned
```bash
cat /data/bot/openclaw-docker/.learnings/ERRORS.md
```
Each rollback adds a structured lesson. Before making a similar change, check if a relevant lesson exists.

---

## 🤖 Watchdog (automatic)

`scripts/watchdog.sh` runs via cron every 5 minutes. If gateway fails:
- 1st failure → simple restart
- 2nd+ failures → rollback + `analyze_failure.sh` + Telegram

---

## Owner Check

If `/recover` comes from a group chat or unrecognized context: **refuse** — "Owner-only emergency command. Access denied."

---

## What this does NOT do
- Does not clear session history
- Does not roll back Obsidian notes
- Does not affect Docker volumes (ChromaDB, Redis, Postgres data)
