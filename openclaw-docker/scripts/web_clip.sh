#!/bin/bash
# web_clip.sh — Clip a web page to Obsidian vault as Markdown
# Usage: web_clip.sh <URL> [max_chars] [save_to_obsidian: true|false]
# Example: web_clip.sh "https://example.com/article" 3000 true

URL="${1:-}"
MAX_CHARS="${2:-4000}"
SAVE="${3:-true}"
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/data/obsidian/To claw}"
INBOX="${VAULT_PATH}/Inbox"
CLIPS_DIR="${VAULT_PATH}/Web Clips"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)

if [ -z "$URL" ]; then
    echo "Usage: web_clip.sh <URL> [max_chars] [save: true|false]"
    exit 1
fi

echo "🌐 Clipping: $URL"

# Fetch page and convert to markdown using python3
CONTENT=$(python3 - "$URL" "$MAX_CHARS" << 'PYEOF'
import sys, urllib.request, re, html

url = sys.argv[1]
max_chars = int(sys.argv[2])

try:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; ClawBot/1.0)'
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode('utf-8', errors='replace')
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

# Extract title
title_m = re.search(r'<title[^>]*>(.*?)</title>', raw, re.IGNORECASE | re.DOTALL)
title = html.unescape(title_m.group(1).strip()) if title_m else "Untitled"

# Remove scripts, styles, nav, header, footer
raw = re.sub(r'<(script|style|nav|header|footer|aside|form)[^>]*>.*?</\1>', '', raw, flags=re.IGNORECASE | re.DOTALL)

# Remove all HTML tags
text = re.sub(r'<[^>]+>', ' ', raw)

# Clean up whitespace
text = html.unescape(text)
text = re.sub(r'[ \t]+', ' ', text)
text = re.sub(r'\n{3,}', '\n\n', text)
text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())

# Trim to max_chars
if len(text) > max_chars:
    text = text[:max_chars] + f"\n\n...[clipped at {max_chars} chars]"

print(f"TITLE:{title}")
print(text)
PYEOF
)

if [ $? -ne 0 ]; then
    echo "❌ Failed to fetch $URL"
    exit 1
fi

# Extract title from output
TITLE=$(echo "$CONTENT" | head -1 | sed 's/^TITLE://')
BODY=$(echo "$CONTENT" | tail -n +2)

# Sanitize title for filename
SAFE_TITLE=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9а-яёА-ЯЁ ]/-/g' | sed 's/--*/-/g' | cut -c1-60)

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
    
    echo ""
    echo "✅ Saved to: $FILENAME"
    echo "📎 Title: $TITLE"
    echo "📝 $(echo "$BODY" | wc -w) words"
else
    # Just print to stdout for agent to summarize
    echo ""
    echo "## $TITLE"
    echo "> Source: $URL"
    echo ""
    echo "$BODY"
fi
