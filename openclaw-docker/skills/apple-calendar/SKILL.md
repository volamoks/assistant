---
name: apple-calendar
description: "View and manage Apple Calendar (iCloud) events. Use for checking schedule, upcoming meetings, creating events."
triggers:
  - apple calendar
  - icloud calendar
  - calendar
  - календарь
  - события
  - расписание
  - встреча
  - создай событие
  - что сегодня
  - schedule
  - events today
  - upcoming
---

# Apple Calendar (iCloud CalDAV) Skill

**Skill ID:** apple-calendar
**Script:** `/data/bot/openclaw-docker/scripts/caldav_apple.py`
**Account:** `komalov@me.com` (iCloud)
**Auth:** `EMAIL_PASS_MECOM` env var (App-Specific Password)

---

## Commands

| Task | Command | Example |
|------|---------|---------|
| List calendars | `caldav_apple.py calendars` | — |
| Today's events | `caldav_apple.py today` | — |
| This week | `caldav_apple.py week` | — |
| Upcoming N days | `caldav_apple.py upcoming [days]` | `caldav_apple.py upcoming 7` |
| Search events | `caldav_apple.py find "<query>"` | `caldav_apple.py find "meeting"` |
| Create event | `caldav_apple.py create "<title>" <YYYY-MM-DD> <HH:MM> [min] [desc]` | see below |

---

## Usage Examples

### Check today's schedule
```bash
python3 /data/bot/openclaw-docker/scripts/caldav_apple.py today
```

### Check this week
```bash
python3 /data/bot/openclaw-docker/scripts/caldav_apple.py week
```

### Next 7 days
```bash
python3 /data/bot/openclaw-docker/scripts/caldav_apple.py upcoming 7
```

### Create a 1-hour event
```bash
python3 /data/bot/openclaw-docker/scripts/caldav_apple.py create "Team Meeting" 2026-03-05 14:00 60 "Weekly sync"
```

### Create a 30-min event (no description)
```bash
python3 /data/bot/openclaw-docker/scripts/caldav_apple.py create "Call with Alex" 2026-03-06 11:00 30
```

### Find events by keyword
```bash
python3 /data/bot/openclaw-docker/scripts/caldav_apple.py find "dentist"
```

---

## Notes

- Default duration: 60 minutes
- Timezone: UTC+5 (Asia/Tashkent) — set via `CALDAV_TZ_OFFSET_HOURS`
- New events are created in the first available calendar ("Рабочий")
- No external dependencies — uses stdlib only (urllib, xml.etree)
- Auth: `komalov@me.com` + `EMAIL_PASS_MECOM` (already in `.env` and passed to container)

---

## Error Handling

| Error | Solution |
|-------|----------|
| `❌ Set EMAIL_PASS_MECOM` | Add `EMAIL_PASS_MECOM` to `.env` |
| `❌ Could not discover CalDAV principal` | Check email/password — wrong credentials |
| `❌ Failed to create event: 403` | App-Specific Password may have expired — regenerate at appleid.apple.com |
