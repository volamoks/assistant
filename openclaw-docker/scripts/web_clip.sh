#!/bin/bash
# web_clip.sh — Clip a web page to Obsidian vault as clean Markdown
# Priority: PinchTab (fast, ~800 tokens) → Crawl4AI (JS-heavy) → urllib (fallback)
#
# Usage: web_clip.sh <URL> [max_chars] [save: true|false]
# Example: web_clip.sh "https://example.com" 4000 true

URL="${1:-}"
MAX_CHARS="${2:-4000}"
SAVE="${3:-true}"
VAULT_PATH="${USER_VAULT_PATH:-/data/abror_vault}"
CLIPS_DIR="${VAULT_PATH}/Web Clips"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
PINCHTAB_HOST="${PINCHTAB_HOST:-http://pinchtab:9867}"
CRAWL4AI_HOST="${CRAWL4AI_HOST:-http://crawl4ai:11235}"
CRAWL4AI_TOKEN="${CRAWL4AI_API_TOKEN:-crawl4ai-local-secret}"
PINCHTAB_SH="/data/bot/openclaw-docker/skills/browser-automation/pinchtab.sh"

if [ -z "$URL" ]; then
    echo "Usage: web_clip.sh <URL> [max_chars] [save: true|false]"
    exit 1
fi

echo "🌐 Clipping: $URL"

# ─── Primary: PinchTab (fast, accessibility tree, ~800 tokens) ───────────────
PINCHTAB_RUNNING=$(curl -s --max-time 3 "${PINCHTAB_HOST}/health" 2>/dev/null | grep -c "ok\|healthy\|alive" || echo "0")

if [ "$PINCHTAB_RUNNING" != "0" ] && [ -f "$PINCHTAB_SH" ]; then
    echo "⚡ Using PinchTab (fast)"
    NAV_OK=$(bash "$PINCHTAB_SH" navigate "$URL" 2>&1)
    if echo "$NAV_OK" | grep -qi "error\|failed"; then
        echo "⚠️  PinchTab navigate failed, trying next..."
    else
        TITLE=$(bash "$PINCHTAB_SH" snapshot 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get('title','Untitled'))
except:
    print('Untitled')
" 2>/dev/null || echo "Untitled")
        BODY=$(bash "$PINCHTAB_SH" text 2>/dev/null | head -c "$MAX_CHARS")
        if [ -n "$BODY" ] && [ ${#BODY} -gt 100 ]; then
            echo "✅ Using PinchTab"
            # skip to save
            TITLE="${TITLE:-Untitled}"
            SAFE_TITLE=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9 -]/-/g' | sed 's/--*/-/g' | tr ' ' '-' | cut -c1-60)
            if [ "$SAVE" = "true" ]; then
                mkdir -p "$CLIPS_DIR"
                FILENAME="${CLIPS_DIR}/${DATE}-${SAFE_TITLE}.md"
                printf -- "---\nsource: %s\nclipped: %s\ntags: [web-clip]\n---\n\n# %s\n\n> Clipped from [%s](%s) on %s at %s\n\n---\n\n%s\n" \
                    "$URL" "$TIMESTAMP" "$TITLE" "$URL" "$URL" "$DATE" "$TIME" "$BODY" > "$FILENAME"
                echo ""; echo "✅ Saved: $FILENAME"; echo "📎 Title: $TITLE"
            else
                echo ""; echo "## $TITLE"; echo "> Source: $URL"; echo ""; echo "$BODY"
            fi
            exit 0
        fi
    fi
fi

# ─── Secondary: Crawl4AI (JS-heavy pages) ────────────────────────────────────
# --- Auto-start Crawl4AI if not running ---
COMPOSE_FILE="/data/bot/openclaw-docker/docker-compose.yml"
CRAWL4AI_RUNNING=$(curl -s --max-time 3 "${CRAWL4AI_HOST}/health" 2>/dev/null | grep -c '"status":"ok"' || echo "0")

if [ "$CRAWL4AI_RUNNING" = "0" ]; then
    echo "⏳ Starting Crawl4AI..."
    docker compose -f "$COMPOSE_FILE" --profile crawl up -d crawl4ai 2>/dev/null
    for i in $(seq 1 10); do
        sleep 3
        READY=$(curl -s --max-time 3 "${CRAWL4AI_HOST}/health" 2>/dev/null | grep -c '"status":"ok"' || echo "0")
        if [ "$READY" != "0" ]; then echo "✅ Crawl4AI ready"; break; fi
        [ $i -eq 10 ] && echo "⚠️  Crawl4AI slow, proceeding anyway..."
    done
fi

# --- Try Crawl4AI ---
CRAWL_RESPONSE=$(curl -s --max-time 30 \
    -X POST "${CRAWL4AI_HOST}/crawl" \
    -H "Authorization: Bearer ${CRAWL4AI_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
        \"urls\": [\"${URL}\"],
        \"word_count_threshold\": 10,
        \"excluded_tags\": [\"nav\", \"header\", \"footer\", \"aside\", \"script\", \"style\"],
        \"remove_overlay_elements\": true
    }" 2>/dev/null)


CRAWL4AI_OK=$(echo "$CRAWL_RESPONSE" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    results = d.get('results', [])
    if results and results[0].get('success'):
        print('OK')
    else:
        print('FAIL')
except:
    print('FAIL')
" 2>/dev/null | head -1)

if [ "$CRAWL4AI_OK" = "OK" ]; then
    echo "✅ Using Crawl4AI"
    TITLE=$(echo "$CRAWL_RESPONSE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
r = d['results'][0]
md = r.get('metadata', {}) or {}
print(md.get('title', 'Untitled'))
" 2>/dev/null)
    BODY=$(echo "$CRAWL_RESPONSE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
r = d['results'][0]
# Try fit_markdown first (cleaner), then raw_markdown, then top-level markdown
mk = r.get('markdown', {})
if isinstance(mk, dict):
    md = mk.get('fit_markdown') or mk.get('raw_markdown', '')
elif isinstance(mk, str):
    md = mk
else:
    md = r.get('fit_markdown') or r.get('markdown_v2', {}).get('raw_markdown', '')
max_c = int('${MAX_CHARS}')
if len(md) > max_c:
    md = md[:max_c] + f'\n\n...[clipped at {max_c} chars]'
print(md)
" 2>/dev/null)

else
    # --- Fallback: urllib python3 ---
    echo "⚠️  Crawl4AI unavailable, falling back to urllib"
    RESULT=$(python3 - "$URL" "$MAX_CHARS" << 'PYEOF'
import sys, urllib.request, re, html

url = sys.argv[1]
max_chars = int(sys.argv[2])

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; ClawBot/1.0)'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode('utf-8', errors='replace')
except Exception as e:
    print(f"TITLE:Error")
    print(f"Could not fetch URL: {e}")
    sys.exit(0)

title_m = re.search(r'<title[^>]*>(.*?)</title>', raw, re.IGNORECASE | re.DOTALL)
title = html.unescape(title_m.group(1).strip()) if title_m else "Untitled"

raw = re.sub(r'<(script|style|nav|header|footer|aside|form)[^>]*>.*?</\1>', '', raw, flags=re.IGNORECASE | re.DOTALL)
text = re.sub(r'<[^>]+>', ' ', raw)
text = html.unescape(text)
text = re.sub(r'[ \t]+', ' ', text)
text = re.sub(r'\n{3,}', '\n\n', text)
text = '\n'.join(l.strip() for l in text.splitlines() if l.strip())
if len(text) > max_chars:
    text = text[:max_chars] + f'\n\n...[clipped at {max_chars} chars]'

print(f"TITLE:{title}")
print(text)
PYEOF
)
    TITLE=$(echo "$RESULT" | head -1 | sed 's/^TITLE://')
    BODY=$(echo "$RESULT" | tail -n +2)
fi

# Sanitize title for filename
SAFE_TITLE=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9 -]/-/g' | sed 's/--*/-/g' | sed 's/^ *//;s/ *$//' | tr ' ' '-' | cut -c1-60)

if [ "$SAVE" = "true" ]; then
    mkdir -p "$CLIPS_DIR"
    FILENAME="${CLIPS_DIR}/${DATE}-${SAFE_TITLE}.md"
    cat > "$FILENAME" << EOF
---
source: $URL
clipped: $TIMESTAMP
tags: [web-clip]
---

# $TITLE

> Clipped from [$URL]($URL) on $DATE at $TIME

---

$BODY
EOF
    WORD_COUNT=$(echo "$BODY" | wc -w | tr -d ' ')
    echo ""
    echo "✅ Saved: ${CLIPS_DIR}/${DATE}-${SAFE_TITLE}.md"
    echo "📎 Title: $TITLE"
    echo "📝 ${WORD_COUNT} words"
    echo "💡 Run 'bash obsidian_reindex.sh' to add to RAG search"
else
    echo ""
    echo "## $TITLE"
    echo "> Source: $URL"
    echo ""
    echo "$BODY"
fi
