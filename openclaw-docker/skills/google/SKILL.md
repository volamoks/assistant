---
name: google-workspace
description: "Access Gmail (read inbox, read emails, search, send) and Google Calendar (view today/week events, create events). Use for checking work email, job application responses, scheduling, and calendar updates."
triggers:
  - gmail
  - calendar
  - email
  - inbox
  - почта
  - письмо
  - встреча
  - собес
  - interview schedule
  - check my email
  - "/mail"
  - "/calendar"
---

# Google Workspace Skill

Requires one-time setup: `python3 /data/bot/openclaw-docker/scripts/google_auth.py`

## Gmail

```bash
# Check unread inbox
bash /data/bot/openclaw-docker/scripts/gmail.sh inbox [max=10]

# Read a specific email (use ID from inbox)
bash /data/bot/openclaw-docker/scripts/gmail.sh read <message_id>

# Search emails
bash /data/bot/openclaw-docker/scripts/gmail.sh search "from:agoda.com" 5
bash /data/bot/openclaw-docker/scripts/gmail.sh search "subject:interview" 5
bash /data/bot/openclaw-docker/scripts/gmail.sh search "is:unread category:primary" 10

# Send email
bash /data/bot/openclaw-docker/scripts/gmail.sh send "hr@company.com" "Re: Interview" "Thank you for..."

# Check auth status
bash /data/bot/openclaw-docker/scripts/gmail.sh status
```

### Career Agent: check job application replies
```bash
bash /data/bot/openclaw-docker/scripts/gmail.sh search "subject:application OR subject:interview OR subject:offer" 10
```

After found → save to Obsidian:
```bash
echo "## [Company] - [Date]\n- Status: Reply received\n- Subject: ...\n" >> "/data/obsidian/vault/Career/applications.md"
```

## Google Calendar

```bash
# View today's events (all calendars including work iCal)
bash /data/bot/openclaw-docker/scripts/gcal.sh today

# View this week
bash /data/bot/openclaw-docker/scripts/gcal.sh week

# Next N days
bash /data/bot/openclaw-docker/scripts/gcal.sh upcoming 3

# Create event
bash /data/bot/openclaw-docker/scripts/gcal.sh create "Interview with Grab" 2026-02-27 14:00 60 "Zoom interview"

# Find event
bash /data/bot/openclaw-docker/scripts/gcal.sh find "standup"

# Check auth + list calendars
bash /data/bot/openclaw-docker/scripts/gcal.sh status
```

## Workflow: Interview Invite via Email

When user asks to "schedule interview from email":
1. `gmail.sh read <id>` — get email details
2. Extract: company, date, time, location/zoom
3. `gcal.sh create "Interview at [Company]" <date> <time> 60 <zoom_link>`
4. Update Obsidian: `Career/applications.md` → Status: Interview scheduled
5. Confirm to user with event link

## Setup (one-time)

If not authorized:
```bash
docker exec -it openclaw-latest python3 /data/bot/openclaw-docker/scripts/google_auth.py
```
Follow the browser link, grant access, done.

## Environment

- `GOOGLE_TOKEN` — path to token.json (default: `/home/node/.openclaw/shared/google_token.json`)
- `GOOGLE_CREDENTIALS` — path to credentials.json (default: `/home/node/.openclaw/shared/google_credentials.json`)
