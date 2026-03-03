#!/bin/bash
# gcal.sh — Google Calendar API wrapper for OpenClaw agents
#
# Usage:
#   gcal.sh status                       — check auth + list calendars
#   gcal.sh today                        — today's events (all calendars)
#   gcal.sh week                         — this week's events
#   gcal.sh upcoming [days=3]            — next N days
#   gcal.sh create "<title>" <date> <time> [duration_min] [description]
#   gcal.sh find "<query>"               — search events
#
# Date format: YYYY-MM-DD  Time format: HH:MM

TOKEN="${GOOGLE_TOKEN:-/home/node/.openclaw/shared/google_token.json}"
CMD="${1:-}"

check_auth() {
  if [ ! -f "$TOKEN" ]; then
    echo "❌ Not authorized. Run first:"
    echo "   python3 /data/bot/openclaw-docker/scripts/google_auth.py"
    exit 1
  fi
}

get_access_token() {
  python3 - <<'EOF'
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

token_file = os.environ.get("GOOGLE_TOKEN", "/home/node/.openclaw/shared/google_token.json")
creds = Credentials.from_authorized_user_file(token_file)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(token_file, "w") as f:
        f.write(creds.to_json())
print(creds.token)
EOF
}

gcal_api() {
  local endpoint="$1"
  local ACCESS_TOKEN
  ACCESS_TOKEN=$(get_access_token)
  curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
       "https://www.googleapis.com/calendar/v3/${endpoint}"
}

gcal_api_post() {
  local endpoint="$1"
  local body="$2"
  local ACCESS_TOKEN
  ACCESS_TOKEN=$(get_access_token)
  curl -s -X POST \
       -H "Authorization: Bearer $ACCESS_TOKEN" \
       -H "Content-Type: application/json" \
       -d "$body" \
       "https://www.googleapis.com/calendar/v3/${endpoint}"
}

format_events() {
  echo "$1" | python3 -c "
import json, sys
from datetime import datetime, timezone

data = json.load(sys.stdin)
items = data.get('items', [])
if not items:
    print('  (no events)')
    sys.exit(0)

# Sort by start time
def get_start(ev):
    s = ev.get('start', {})
    return s.get('dateTime', s.get('date', ''))

items.sort(key=get_start)

for ev in items:
    start = ev.get('start', {})
    end = ev.get('end', {})
    dt_str = start.get('dateTime', '')
    date_str = start.get('date', '')
    
    if dt_str:
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            dt_local = dt.astimezone()
            time_str = dt_local.strftime('%H:%M')
            date_display = dt_local.strftime('%a %d %b')
        except:
            time_str = dt_str[11:16]
            date_display = dt_str[:10]
    else:
        time_str = 'All day'
        date_display = date_str

    title = ev.get('summary', '(no title)')
    location = ev.get('location', '')
    cal_name = ev.get('organizer', {}).get('displayName', '')
    
    print(f'  📅 {date_display} {time_str}  {title}')
    if location:
        print(f'     📍 {location}')
    if cal_name and cal_name.lower() not in title.lower():
        print(f'     🗓  {cal_name}')
"
}

# ── Status / List calendars ───────────────────────────────────────────────────
if [ "$CMD" = "status" ]; then
  check_auth
  RESULT=$(gcal_api "users/me/calendarList")
  echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
cals = d.get('items', [])
print(f'✅ Google Calendar authorized — {len(cals)} calendar(s):')
for c in cals:
    primary = ' ← primary' if c.get('primary') else ''
    print(f'  • {c[\"summary\"]}{primary} (id: {c[\"id\"][:40]})')
"
  exit 0
fi

# ── Today ─────────────────────────────────────────────────────────────────────
if [ "$CMD" = "today" ]; then
  check_auth
  TODAY=$(date -u +%Y-%m-%d)
  TIME_MIN="${TODAY}T00:00:00Z"
  TIME_MAX="${TODAY}T23:59:59Z"
  echo "📅 Today — $TODAY:"
  RESULT=$(gcal_api "calendars/primary/events?timeMin=${TIME_MIN}&timeMax=${TIME_MAX}&singleEvents=true&orderBy=startTime&maxResults=20")
  format_events "$RESULT"
  exit 0
fi

# ── Week ──────────────────────────────────────────────────────────────────────
if [ "$CMD" = "week" ]; then
  check_auth
  TODAY=$(date -u +%Y-%m-%d)
  # 7 days from now
  NEXT_WEEK=$(date -d "+7 days" +%Y-%m-%d 2>/dev/null || date -v+7d +%Y-%m-%d 2>/dev/null)
  TIME_MIN="${TODAY}T00:00:00Z"
  TIME_MAX="${NEXT_WEEK}T23:59:59Z"
  echo "📅 This week ($TODAY → $NEXT_WEEK):"
  RESULT=$(gcal_api "calendars/primary/events?timeMin=${TIME_MIN}&timeMax=${TIME_MAX}&singleEvents=true&orderBy=startTime&maxResults=50")
  format_events "$RESULT"
  exit 0
fi

# ── Upcoming N days ───────────────────────────────────────────────────────────
if [ "$CMD" = "upcoming" ]; then
  check_auth
  DAYS="${2:-3}"
  TODAY=$(date -u +%Y-%m-%d)
  END_DATE=$(date -d "+${DAYS} days" +%Y-%m-%d 2>/dev/null || date -v+${DAYS}d +%Y-%m-%d 2>/dev/null)
  TIME_MIN="${TODAY}T00:00:00Z"
  TIME_MAX="${END_DATE}T23:59:59Z"
  echo "📅 Next $DAYS days ($TODAY → $END_DATE):"
  RESULT=$(gcal_api "calendars/primary/events?timeMin=${TIME_MIN}&timeMax=${TIME_MAX}&singleEvents=true&orderBy=startTime&maxResults=30")
  format_events "$RESULT"
  exit 0
fi

# ── Create event ──────────────────────────────────────────────────────────────
if [ "$CMD" = "create" ]; then
  check_auth
  TITLE="${2:-}"
  DATE="${3:-}"     # YYYY-MM-DD
  TIME="${4:-}"     # HH:MM
  DURATION="${5:-60}"  # minutes
  DESC="${6:-}"

  if [ -z "$TITLE" ] || [ -z "$DATE" ] || [ -z "$TIME" ]; then
    echo "Usage: gcal.sh create \"<title>\" <YYYY-MM-DD> <HH:MM> [duration_min=60] [description]"
    exit 1
  fi

  # Build ISO datetime (assume local timezone UTC+5 for Tashkent)
  TZ_OFFSET="+05:00"
  START="${DATE}T${TIME}:00${TZ_OFFSET}"
  END_TIME=$(python3 -c "
from datetime import datetime, timedelta
start = datetime.fromisoformat('${DATE}T${TIME}:00')
end = start + timedelta(minutes=${DURATION})
print(end.strftime('%H:%M'))
")
  END="${DATE}T${END_TIME}:00${TZ_OFFSET}"

  BODY=$(python3 -c "
import json
event = {
    'summary': '$TITLE',
    'description': '$DESC',
    'start': {'dateTime': '$START', 'timeZone': 'Asia/Tashkent'},
    'end': {'dateTime': '$END', 'timeZone': 'Asia/Tashkent'},
}
print(json.dumps(event))
")

  RESULT=$(gcal_api_post "calendars/primary/events" "$BODY")
  echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('id'):
    link = d.get('htmlLink','')
    print(f'✅ Event created: $TITLE')
    print(f'   $DATE $TIME ($DURATION min)')
    print(f'   Link: {link}')
else:
    print(f'❌ Error: {d}')
"
  exit 0
fi

# ── Find/search events ────────────────────────────────────────────────────────
if [ "$CMD" = "find" ]; then
  check_auth
  QUERY="${2:-}"
  if [ -z "$QUERY" ]; then echo "Usage: gcal.sh find \"<query>\""; exit 1; fi
  ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$QUERY'))")
  RESULT=$(gcal_api "calendars/primary/events?q=${ENCODED}&singleEvents=true&orderBy=startTime&maxResults=10")
  echo "🔍 Events matching \"$QUERY\":"
  echo "$RESULT" | format_events
  exit 0
fi

# ── Help ──────────────────────────────────────────────────────────────────────
echo "Google Calendar wrapper v1.0"
echo "Usage:"
echo "  gcal.sh status"
echo "  gcal.sh today"
echo "  gcal.sh week"
echo "  gcal.sh upcoming [days=3]"
echo "  gcal.sh create \"Meeting\" 2026-02-26 14:00 [60] [description]"
echo "  gcal.sh find \"standup\""
