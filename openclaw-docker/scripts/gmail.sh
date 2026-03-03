#!/bin/bash
# gmail.sh — Gmail API wrapper for OpenClaw agents
#
# Usage:
#   gmail.sh inbox [max=10]             — list unread emails
#   gmail.sh read <message_id>          — read full email
#   gmail.sh search "<query>" [max=10]  — search emails
#   gmail.sh send <to> <subject> <body> — send email
#   gmail.sh status                     — check auth status

TOKEN="${GOOGLE_TOKEN:-/home/node/.openclaw/shared/google_token.json}"
CMD="${1:-}"

# ── Check auth ───────────────────────────────────────────────────────────────
check_auth() {
  if [ ! -f "$TOKEN" ]; then
    echo "❌ Not authorized. Run first:"
    echo "   python3 /data/bot/openclaw-docker/scripts/google_auth.py"
    exit 1
  fi
}

# ── Get access token from token.json ────────────────────────────────────────
get_access_token() {
  python3 - <<'EOF'
import json, sys, os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

token_file = os.environ.get("GOOGLE_TOKEN", "/home/node/.openclaw/shared/google_token.json")
try:
    creds = Credentials.from_authorized_user_file(token_file)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    print(creds.token)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

gmail_api() {
  local endpoint="$1"
  local ACCESS_TOKEN
  ACCESS_TOKEN=$(get_access_token)
  curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
       -H "Accept: application/json" \
       "https://gmail.googleapis.com/gmail/v1/users/me/${endpoint}"
}

gmail_api_post() {
  local endpoint="$1"
  local body="$2"
  local ACCESS_TOKEN
  ACCESS_TOKEN=$(get_access_token)
  curl -s -X POST \
       -H "Authorization: Bearer $ACCESS_TOKEN" \
       -H "Content-Type: application/json" \
       -d "$body" \
       "https://gmail.googleapis.com/gmail/v1/users/me/${endpoint}"
}

# ── Status ───────────────────────────────────────────────────────────────────
if [ "$CMD" = "status" ]; then
  check_auth
  ACCESS_TOKEN=$(get_access_token)
  PROFILE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
    "https://gmail.googleapis.com/gmail/v1/users/me/profile")
  EMAIL=$(echo "$PROFILE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('emailAddress','unknown'))" 2>/dev/null)
  echo "✅ Gmail authorized as: $EMAIL"
  exit 0
fi

# ── Inbox ─────────────────────────────────────────────────────────────────────
if [ "$CMD" = "inbox" ]; then
  check_auth
  MAX="${2:-10}"
  RESULT=$(gmail_api "messages?labelIds=INBOX&q=is:unread&maxResults=${MAX}")
  python3 -c "
import json, sys, os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import urllib.request

result = '''$RESULT'''
data = json.loads(result)
messages = data.get('messages', [])
if not messages:
    print('📭 Inbox is empty (no unread messages)')
    sys.exit(0)

print(f'📬 {len(messages)} unread email(s):\n')
token_file = os.environ.get('GOOGLE_TOKEN', '/home/node/.openclaw/shared/google_token.json')

creds = Credentials.from_authorized_user_file(token_file)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

for msg in messages:
    mid = msg['id']
    req = urllib.request.Request(
        f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date',
        headers={'Authorization': f'Bearer {creds.token}'}
    )
    with urllib.request.urlopen(req) as r:
        m = json.loads(r.read())
    headers = {h['name']: h['value'] for h in m.get('payload', {}).get('headers', [])}
    subject = headers.get('Subject', '(no subject)')[:60]
    sender = headers.get('From', 'unknown')[:40]
    date = headers.get('Date', '')[:16]
    snippet = m.get('snippet', '')[:80]
    print(f'  ID: {mid}')
    print(f'  From: {sender}')
    print(f'  Subject: {subject}')
    print(f'  Date: {date}')
    print(f'  Preview: {snippet}...')
    print()
"
  exit 0
fi

# ── Read email ────────────────────────────────────────────────────────────────
if [ "$CMD" = "read" ]; then
  check_auth
  MID="${2:-}"
  if [ -z "$MID" ]; then echo "Usage: gmail.sh read <message_id>"; exit 1; fi
  RESULT=$(gmail_api "messages/${MID}?format=full")
  echo "$RESULT" | python3 - <<'PYEOF'
import json, sys, base64, re

data = json.load(sys.stdin)
headers = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
print(f"From: {headers.get('From','')}")
print(f"To: {headers.get('To','')}")
print(f"Date: {headers.get('Date','')}")
print(f"Subject: {headers.get('Subject','')}")
print("-" * 50)

def get_body(payload):
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []):
        if part.get("mimeType") in ("text/plain", "text/html"):
            data = part.get("body", {}).get("data", "")
            if data:
                text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                # Strip HTML tags
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text
    return "(no body)"

body = get_body(data.get("payload", {}))
print(body[:3000])
if len(body) > 3000:
    print(f"\n... [truncated, {len(body)} chars total]")
PYEOF
  exit 0
fi

# ── Search ────────────────────────────────────────────────────────────────────
if [ "$CMD" = "search" ]; then
  check_auth
  QUERY="${2:-}"
  MAX="${3:-10}"
  if [ -z "$QUERY" ]; then echo "Usage: gmail.sh search \"<query>\" [max]"; exit 1; fi
  ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$QUERY'))")
  RESULT=$(gmail_api "messages?q=${ENCODED}&maxResults=${MAX}")
  echo "$RESULT" | python3 - <<'PYEOF'
import json, sys, os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import urllib.request

data = json.load(sys.stdin)
messages = data.get("messages", [])
if not messages:
    print(f"No results found.")
    sys.exit(0)

print(f"Found {len(messages)} result(s):\n")
token_file = os.environ.get("GOOGLE_TOKEN", "/home/node/.openclaw/shared/google_token.json")
creds = Credentials.from_authorized_user_file(token_file)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

for msg in messages[:5]:
    mid = msg["id"]
    req = urllib.request.Request(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date",
        headers={"Authorization": f"Bearer {creds.token}"}
    )
    with urllib.request.urlopen(req) as r:
        m = json.loads(r.read())
    h = {hdr["name"]: hdr["value"] for hdr in m.get("payload", {}).get("headers", [])}
    print(f"  ID: {mid} | {h.get('Date','')[:16]}")
    print(f"  From: {h.get('From','')[:50]}")
    print(f"  Subject: {h.get('Subject','')[:60]}")
    print(f"  Preview: {m.get('snippet','')[:80]}...")
    print()
PYEOF
  exit 0
fi

# ── Send email ────────────────────────────────────────────────────────────────
if [ "$CMD" = "send" ]; then
  check_auth
  TO="${2:-}"
  SUBJECT="${3:-}"
  BODY="${4:-}"
  if [ -z "$TO" ] || [ -z "$SUBJECT" ] || [ -z "$BODY" ]; then
    echo "Usage: gmail.sh send <to@email.com> <subject> <body_text>"
    exit 1
  fi

  # Build RFC 2822 message
  RAW=$(python3 - <<PYEOF
import base64
from email.mime.text import MIMEText

msg = MIMEText("""$BODY""")
msg['To'] = "$TO"
msg['Subject'] = "$SUBJECT"
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
print(raw)
PYEOF
)

  RESULT=$(gmail_api_post "messages/send" "{\"raw\": \"${RAW}\"}")
  echo "$RESULT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
if d.get('id'):
    print(f'✅ Email sent to $TO (id: {d[\"id\"]})')
else:
    print(f'❌ Error: {d}')
"
  exit 0
fi

# ── Help ─────────────────────────────────────────────────────────────────────
echo "Gmail wrapper v1.0"
echo "Usage:"
echo "  gmail.sh status"
echo "  gmail.sh inbox [max=10]"
echo "  gmail.sh read <message_id>"
echo "  gmail.sh search \"<query>\" [max=10]"
echo "  gmail.sh send <to> <subject> <body>"
echo ""
echo "Common searches:"
echo "  gmail.sh search \"from:agoda.com\" 5"
echo "  gmail.sh search \"subject:interview\" 5"
echo "  gmail.sh search \"is:unread category:primary\" 10"
