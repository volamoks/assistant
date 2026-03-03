---
name: status
description: "Check what's currently running: active sub-agents and their tasks, container health. Use when user asks about system status or what the bot is doing."
triggers:
  - /status
  - что сейчас делается
  - ты занят
  - что за задачи
  - sub-agents running
  - статус системы
---

# /status — What's Running Right Now

## When to use
User types `/status` or asks "что сейчас делается?", "ты занят?", "что за задачи?", "sub-agents running?"

## Steps

1. Call `subagents` tool with `{"action": "list", "recentMinutes": 30}` to get active sessions

2. Call bash: `docker ps --format '{{.Names}}\t{{.Status}}' | grep -v "Up [0-9]* [hd]"` to see recently restarted containers

3. Format and reply:

```
[🦀 Claw]
📊 Статус системы:

**Sub-agents (последние 30 мин):**
• [agent]: [статус/задача] — [время]
• (пусто если нет активных)

**Контейнеры (внимание):**
• [container]: [статус] — только если что-то не Up >1h

**Cron последний запуск:**
— нет инструмента, пропустить

Время: [UTC+5]
[ctx: ~Xk]
```

If no sub-agents running and all containers healthy:
```
[🦀 Claw]
✅ Всё тихо. Нет активных задач, все контейнеры работают.
[ctx: ~Xk]
```
