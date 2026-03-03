---
name: google-agent
description: "Access Gmail (read, search, send emails) and Google Calendar (view events, create meetings). Use for any email or calendar tasks."
triggers:
  - gmail
  - проверь почту
  - непрочитанные письма
  - inbox
  - отправь email
  - calendar
  - календарь
  - создай событие
  - встреча
  - события сегодня
---

# Google Agent — Gmail & Google Calendar Skill

**Skill ID:** google-agent  
**Location:** `~/.openclaw/skills/google-agent/`  
**Uses:** `/data/bot/openclaw-docker/scripts/gmail.sh`, `/data/bot/openclaw-docker/scripts/gcal.sh`

---

## Triggers (keywords)

Use this skill when user asks to:
- **Gmail:** "проверь почту", "непрочитанные письма", "найди письмо", "отправь email", "пошли письмо", "inbox", "unread"
- **Calendar:** "календарь", "события", "встреча", "создай событие", "сегодня", "на неделе", "events", "schedule"

---

## Quick Reference

### Gmail Commands

| Task | Command | Example |
|------|---------|---------|
| Check unread | `gmail.sh inbox [max]` | `gmail.sh inbox 10` |
| Read email | `gmail.sh read <id>` | `gmail.sh read 123abc...` |
| Search | `gmail.sh search "query"` | `gmail.sh search "from:agoda.com"` |
| Send | `gmail.sh send <to> <subject> <body>` | `gmail.sh send "test@test.com" "Hi" "Hello!"` |
| Status | `gmail.sh status` | — |

### Calendar Commands

| Task | Command | Example |
|------|---------|---------|
| Today | `gcal.sh today` | — |
| This week | `gcal.sh week` | — |
| Upcoming | `gcal.sh upcoming [days]` | `gcal.sh upcoming 3` |
| Create event | `gcal.sh create "<title>" <YYYY-MM-DD> <HH:MM> [duration] [desc]` | `gcal.sh create "Meeting" 2026-02-27 14:00 60 "Discuss project"` |
| Find event | `gcal.sh find "<query>"` | `gcal.sh find "standup"` |
| Status | `gcal.sh status` | — |

---

## Automated Tasks

### 1. Проверить непрочитанные письма
```bash
bash /data/bot/openclaw-docker/scripts/gmail.sh inbox 10
```

### 2. Найти письма от определённого отправителя
```bash
# Example: find emails from specific sender
bash /data/bot/openclaw-docker/scripts/gmail.sh search "from:company.com"
# or more specific
bash /data/bot/openclaw-docker/scripts/gmail.sh search "from:john@example.com subject:invoice"
```

### 3. Создать событие в календаре
```bash
# Basic: title, date, time
bash /data/bot/openclaw-docker/scripts/gcal.sh create "Встреча" 2026-02-27 14:00

# With duration (minutes) and description
bash /data/bot/openclaw-docker/scripts/gcal.sh create "Стендап" 2026-02-28 09:30 30 "Ежедневный синхрон"

# All day event (use 00:00 and full day)
bash /data/bot/openclaw-docker/scripts/gcal.sh create "День рождения" 2026-03-01 00:00 1440 "All day event"
```

### 4. Показать сегодняшние события
```bash
bash /data/bot/openclaw-docker/scripts/gcal.sh today
```

### 5. Отправить email
```bash
bash /data/bot/openclaw-docker/scripts/gmail.sh send "recipient@example.com" "Тема письма" "Текст письма"
```

---

## Common Search Queries

### Gmail
- `"from:agoda.com"` — from specific domain
- `"subject:interview"` — subject contains word
- `"is:unread category:primary"` — unread in primary
- `"after:2026/01/01"` — received after date
- `"label:work"` — specific label

### Calendar
- `"standup"` — find standup meetings
- `"1on1"` — find 1-on-1s
- `"review"` — find review meetings

---

## Notes

- Token location: `/home/node/.openclaw/shared/google_token.json`
- If auth error: run `python3 /data/bot/openclaw-docker/scripts/google_auth.py`
- Calendar timezone: Asia/Tashkent (UTC+5)
- Email body must be plain text (no HTML formatting via CLI)

---

## Error Handling

| Error | Solution |
|-------|----------|
| `❌ Not authorized` | Run auth script: `python3 /data/bot/openclaw-docker/scripts/google_auth.py` |
| `Token expired` | Script auto-refreshes; if fails, re-authenticate |
| `Error 403` | Check API scopes in token |
| `No results` | Query is valid but nothing found |

---

## Examples in Russian

**User:** "Проверь почту"  
**Agent:** runs `gmail.sh inbox`

**User:** "Есть ли письма от Amazon?"  
**Agent:** runs `gmail.sh search "from:amazon.com"`

**User:** "Что сегодня в календаре?"  
**Agent:** runs `gcal.sh today`

**User:** "Создай встречу завтра в 3 часа"  
**Agent:** runs `gcal.sh create "Встреча" 2026-02-27 15:00`

**User:** "Напомни Марине про завтрашний созвон"  
**Agent:** runs `gmail.sh send "marina@example.com" "Напоминание" "Привет! Напоминаю про созвон завтра в 15:00"`
