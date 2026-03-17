#!/bin/bash
# Failure Analysis — called after watchdog rollback or manual /recover
# Reads crash state, asks LLM why it failed, writes lesson to .learnings/ERRORS.md
#
# Usage: bash analyze_failure.sh [crash_file] [trigger]
#   crash_file: path to Obsidian crash-config md file (optional)
#   trigger:    "watchdog" | "manual" (default: "watchdog")

set -e

CRASH_FILE="${1:-}"
TRIGGER="${2:-watchdog}"
LEARNINGS_FILE="/data/bot/openclaw-docker/.learnings/ERRORS.md"
LITELLM_URL="http://litellm:4000/v1/chat/completions"
LITELLM_KEY="${LITELLM_MASTER_KEY:-}"
NOTIFY_SCRIPT="/data/bot/openclaw-docker/skills/telegram/notify.py"
CHAT_ID="6053956251"

TIMESTAMP=$(date +"%Y-%m-%d %H:%M")

echo "[analyze_failure] Starting failure analysis at $TIMESTAMP"

# ── Gather context ──────────────────────────────────────────────────────────

# Recent gateway errors
GATEWAY_ERRORS=$(tail -200 /home/node/.openclaw/gateway.log 2>/dev/null \
    | grep -iE "error|warn|fatal|crash|exception|unhandled" \
    | tail -30 \
    || echo "No gateway log found")

# Git diff at time of crash (what the bot changed)
GIT_ROOT="/data/bot"
RECENT_DIFF=$(cd "$GIT_ROOT" 2>/dev/null && git log --oneline -5 openclaw-docker/ 2>/dev/null || echo "No git log available")

# Crash file content
CRASH_CONTENT=""
if [ -n "$CRASH_FILE" ] && [ -f "$CRASH_FILE" ]; then
    CRASH_CONTENT=$(cat "$CRASH_FILE" | head -80)
fi

# Previous lessons (so LLM can avoid repeating advice)
PREV_LESSONS=$(tail -60 "$LEARNINGS_FILE" 2>/dev/null || echo "")

# ── Ask LLM to analyze ──────────────────────────────────────────────────────

PROMPT="You are an AI bot that just crashed and was rolled back. Analyze the failure and write a concise lesson.

## Crash Info
Trigger: $TRIGGER
Time: $TIMESTAMP

## Recent Gateway Errors
$GATEWAY_ERRORS

## Recent Git Log (what was changed)
$RECENT_DIFF

## Crash Config Snapshot
$CRASH_CONTENT

## Previous Lessons (don't repeat these)
$PREV_LESSONS

---
Write a lesson entry in this exact format (Markdown):
### 🔴 Failure — $TIMESTAMP
**Trigger:** $TRIGGER
**Root cause:** (1 sentence: what went wrong)
**Pattern:** (is this a repeat? reference previous lesson if yes)
**Lesson:** (what to do differently next time)
**Checklist before next change:**
- [ ] (specific check to prevent recurrence)
- [ ] (another check if needed)

Be concise. Max 10 lines total."

# Build JSON payload
PAYLOAD=$(python3 -c "
import json, sys
payload = {
    'model': 'claw-cron-smart',
    'messages': [{'role': 'user', 'content': sys.argv[1]}],
    'max_tokens': 400,
    'temperature': 0.3
}
print(json.dumps(payload))
" "$PROMPT")

LESSON=$(curl -s "$LITELLM_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $LITELLM_KEY" \
    -d "$PAYLOAD" \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
print(content)
" 2>/dev/null)

if [ -z "$LESSON" ]; then
    # Fallback: write minimal entry without LLM
    LESSON="### 🔴 Failure — $TIMESTAMP
**Trigger:** $TRIGGER
**Root cause:** Unknown — LLM analysis unavailable
**Lesson:** Review gateway.log and git diff manually.
"
fi

# ── Append to .learnings/ERRORS.md ─────────────────────────────────────────

echo "" >> "$LEARNINGS_FILE"
echo "$LESSON" >> "$LEARNINGS_FILE"
echo "" >> "$LEARNINGS_FILE"

echo "[analyze_failure] Lesson written to .learnings/ERRORS.md"

# ── Commit the lesson to git ────────────────────────────────────────────────
(cd "$GIT_ROOT" && git add openclaw-docker/.learnings/ERRORS.md 2>/dev/null && \
    git commit -m "lesson: failure analysis $TIMESTAMP (trigger: $TRIGGER)" 2>/dev/null && \
    echo "[analyze_failure] Lesson committed to git") || \
    echo "[analyze_failure] Git commit skipped (no changes or git unavailable)"

# ── Notify Telegram ─────────────────────────────────────────────────────────
SHORT_LESSON=$(echo "$LESSON" | head -6)
python3 "$NOTIFY_SCRIPT" "🧠 Failure analyzed & lesson saved:

$SHORT_LESSON

Full lesson: .learnings/ERRORS.md" --chat-id "$CHAT_ID" 2>/dev/null || true

echo "[analyze_failure] Done."
