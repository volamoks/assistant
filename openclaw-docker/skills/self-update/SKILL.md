---
name: self-update
description: "Restart or rebuild the OpenClaw bot itself. Writes a sentinel file that the host watchdog picks up within 30 seconds and executes the requested action."
triggers:
  - обнови бота
  - перезапусти себя
  - rebuild openclaw
  - restart bot
  - self update
  - обнови себя
  - перезапустись
---

# /self-update — Bot Self-Update & Restart

## When to use
- User asks to restart or update OpenClaw
- After Dockerfile changes that need to be applied
- After config changes that require a full restart
- When a new OpenClaw version should be applied

## Actions

| Action | What it does | When to use |
|--------|-------------|-------------|
| `restart` | `docker compose up -d openclaw` | Config changes, minor fixes |
| `rebuild` | `docker compose build` + restart | Dockerfile changes, new packages |
| `pull` | Pull new base image + rebuild + restart | New OpenClaw version available |

## Workflow

1. Write sentinel file:
   ```bash
   bash /home/node/.openclaw/skills/self-update/trigger.sh "<action>" "<reason>"
   ```

2. Confirm to user that the update is triggered (bot will restart in ~30 sec)

3. ⚠️ Connection will be lost during restart (~15-30 seconds). Tell user to wait.

## Examples

### Restart only
```bash
bash /home/node/.openclaw/skills/self-update/trigger.sh "restart" "User requested restart"
```

### Rebuild (after Dockerfile changes)
```bash
bash /home/node/.openclaw/skills/self-update/trigger.sh "rebuild" "New Python packages added to Dockerfile"
```

### Pull latest version + rebuild
```bash
bash /home/node/.openclaw/skills/self-update/trigger.sh "pull" "Updating to latest OpenClaw release"
```

## Important notes

- The bot WILL disconnect during restart — this is normal
- Host watchdog runs every 30 seconds, so update starts within 30s
- Rebuild takes 2-5 minutes (pip packages, apt installs)
- Pull+rebuild takes 5-10 minutes
- After restart, pending Telegram messages are recovered automatically
