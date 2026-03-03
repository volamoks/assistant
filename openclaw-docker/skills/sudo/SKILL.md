---
name: sudo
description: "Execute commands requiring elevated privileges: install pip/apt packages, restart Docker containers. ALWAYS explain what you're about to run and wait for user confirmation before executing."
triggers:
  - sudo
  - установи пакет
  - pip install
  - apt-get install
  - docker restart
---

# /sudo — Elevated Command Execution

## When to use
Agent needs root/elevated privileges:
- Install pip packages (`pip install`)
- Install apt packages (`apt-get install`)
- Restart Docker containers (`docker restart`)
- Modify system files requiring root

## How to use

The container runs as `hostuser` with full `sudo NOPASSWD` access — no tokens or approval scripts needed.

**Just use sudo directly via terminal.sh:**
```bash
bash /home/node/.openclaw/skills/system/terminal.sh "sudo pip install <package>"
bash /home/node/.openclaw/skills/system/terminal.sh "sudo apt-get install -y <package>"
bash /home/node/.openclaw/skills/system/terminal.sh "sudo docker restart <container>"
```

## IMPORTANT: Always ask before executing

Even though sudo works without a password, you MUST:
1. Tell the user WHAT you're about to install/run and WHY
2. Wait for explicit "yes" / "да" / "давай" in the conversation
3. Then execute

## Examples

```
Agent: "Нужно установить telethon для работы с Telegram API. Запускаю: sudo pip install telethon. Разрешаешь?"
User: "да"
Agent: bash terminal.sh "sudo pip install telethon"  → ✅
```

```
Agent: "Перезапускаю контейнер openclaw-latest чтобы применить изменения config. Ок?"
User: "давай"
Agent: bash terminal.sh "sudo docker restart openclaw-latest"  → ✅
```
