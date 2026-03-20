#!/bin/bash
# Cron Health Monitor — checks for broken/slow/skipped cron jobs
# Runs as isolated cron every 30 min (not part of main watchdog)
# Sends Telegram only on real issues

JOBS_FILE="/home/node/.openclaw/cron/jobs.json"
TOKEN_FILE="/home/node/.openclaw/.gateway-token"
GATEWAY_PORT="18789"
CHAT_ID="6053956251"
NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
ALERT_FILE="/tmp/cron_health_alert.json"

# ── Helpers ──────────────────────────────────────────────────────────────────

get_token() {
    cat "$TOKEN_FILE" 2>/dev/null || echo ""
}

gateway_ok() {
    bash -c ">/dev/tcp/localhost/$GATEWAY_PORT" 2>/dev/null
}

# ── Main Check ───────────────────────────────────────────────────────────────

if ! gateway_ok; then
    exit 0  # Gateway down — skip, watchdog will handle
fi

# Parse jobs.json
BROKEN=$(python3 -c "
import json, sys
try:
    with open('$JOBS_FILE') as f:
        jobs = json.load(f)
except:
    print('PARSE_ERROR')
    sys.exit(0)

issues = []
for j in jobs.get('jobs', []):
    t = j.get('sessionTarget', '')
    k = j.get('payload', {}).get('kind', '')
    s = j.get('state', {}).get('lastRunStatus', '')
    err = j.get('state', {}).get('consecutiveErrors', 0)
    name = j['name']

    if t == 'main' and k == 'agentTurn':
        issues.append({'id': j['id'], 'name': name, 'type': 'BROKEN', 'msg': 'sessionTarget=main + agentTurn'})
    elif s == 'skipped':
        issues.append({'id': j['id'], 'name': name, 'type': 'SKIPPED', 'msg': j.get('state', {}).get('lastError', 'skipped')[:80]})
    elif err > 0:
        issues.append({'id': j['id'], 'name': name, 'type': 'ERROR', 'msg': f'{err} consecutive errors'})

print(json.dumps(issues, ensure_ascii=False))
" 2>/dev/null)

if [ "$BROKEN" = "PARSE_ERROR" ] || [ -z "$BROKEN" ]; then
    exit 0
fi

# Check if anything to report
COUNT=$(echo "$BROKEN" | python3 -c "import json,sys; print(len(json.loads(sys.stdin.read())))" 2>/dev/null || echo "0")
if [ "$COUNT" = "0" ] || [ "$COUNT" = "" ]; then
    exit 0  # No issues — silent
fi

# ── Auto-fix sessionTarget=main + agentTurn ──────────────────────────────────

TOKEN=$(get_token)
AUTO_FIXED=0

echo "$BROKEN" | python3 -c "
import json, sys, urllib.request

issues = json.loads(sys.stdin.read())
ids = [j['id'] for j in issues if j['type'] == 'BROKEN']
print(f'FIXING: {ids}')
for jid in ids:
    try:
        req = urllib.request.Request(
            f'http://localhost:$GATEWAY_PORT/cron/jobs/{jid}',
            data=json.dumps({'sessionTarget': 'isolated'}).encode(),
            headers={'Authorization': f'Bearer {$TOKEN}', 'Content-Type': 'application/json'},
            method='PATCH'
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f'  {jid}: {r.status}')
    except Exception as e:
        print(f'  {jid}: FIX_FAILED — {e}')
" 2>/dev/null

# ── Send Telegram alert ──────────────────────────────────────────────────────

echo "$BROKEN" | python3 -c "
import json, sys

issues = json.loads(sys.stdin.read())
lines = ['🔧 Cron Health Alert\n\n']
fixed = [j for j in issues if j['type'] == 'BROKEN']
skipped = [j for j in issues if j['type'] == 'SKIPPED']
errors = [j for j in issues if j['type'] == 'ERROR']

if fixed:
    lines.append(f'✅ Auto-fixed ({len(fixed)}):')
    for j in fixed:
        lines.append(f'  • {j[\"name\"]}')
    lines.append('')

if skipped:
    lines.append(f'⏭ Skipped ({len(skipped)}):')
    for j in skipped:
        lines.append(f'  • {j[\"name\"]}')
        lines.append(f'    Error: {j[\"msg\"]}')
    lines.append('')

if errors:
    lines.append(f'⚠️ Errors ({len(errors)}):')
    for j in errors:
        lines.append(f'  • {j[\"name\"]}: {j[\"msg\"]}')

print('\n'.join(lines))
" > "$ALERT_FILE"

if [ -s "$ALERT_FILE" ]; then
    python3 "$NOTIFY_SCRIPT" "$(cat "$ALERT_FILE")" --chat-id "$CHAT_ID" 2>/dev/null || true
fi

exit 0
