#!/bin/bash
# PinchTab browser automation helper
# Usage:
#   pinchtab.sh navigate <url>
#   pinchtab.sh snapshot
#   pinchtab.sh text
#   pinchtab.sh action <type> <element> [value]
#   pinchtab.sh screenshot   (saves to /tmp/pinchtab-screenshot.png)

set -euo pipefail

BASE="http://pinchtab:9867"
CMD="${1:-}"
MAX_OUTPUT=6000

truncate_output() {
    local input="$1"
    if [ ${#input} -gt $MAX_OUTPUT ]; then
        echo "${input:0:$MAX_OUTPUT}"
        echo "... [truncated, ${#input} chars total]"
    else
        echo "$input"
    fi
}

case "$CMD" in
    navigate)
        URL="${2:?Usage: pinchtab.sh navigate <url>}"
        RESULT=$(curl -sf -X POST "$BASE/navigate" \
            -H "Content-Type: application/json" \
            -d "{\"url\":\"$URL\"}" 2>&1) || { echo "ERROR: PinchTab navigate failed: $RESULT"; exit 1; }
        echo "Navigated to: $URL"
        ;;

    snapshot)
        RESULT=$(curl -sf "$BASE/snapshot" 2>&1) || { echo "ERROR: PinchTab snapshot failed: $RESULT"; exit 1; }
        truncate_output "$RESULT"
        ;;

    text)
        RESULT=$(curl -sf "$BASE/text" 2>&1) || { echo "ERROR: PinchTab text failed: $RESULT"; exit 1; }
        truncate_output "$RESULT"
        ;;

    action)
        TYPE="${2:?Usage: pinchtab.sh action <type> <element> [value]}"
        ELEMENT="${3:?Missing element (e.g. e5)}"
        VALUE="${4:-}"

        if [ -n "$VALUE" ]; then
            PAYLOAD="{\"type\":\"$TYPE\",\"element\":\"$ELEMENT\",\"value\":\"$VALUE\"}"
        else
            PAYLOAD="{\"type\":\"$TYPE\",\"element\":\"$ELEMENT\"}"
        fi

        RESULT=$(curl -sf -X POST "$BASE/action" \
            -H "Content-Type: application/json" \
            -d "$PAYLOAD" 2>&1) || { echo "ERROR: PinchTab action failed: $RESULT"; exit 1; }
        echo "Action $TYPE on $ELEMENT: OK"
        ;;

    screenshot)
        OUT="${2:-/tmp/pinchtab-screenshot.png}"
        curl -sf "$BASE/screenshot" -o "$OUT" 2>&1 || { echo "ERROR: screenshot failed"; exit 1; }
        echo "Screenshot saved to: $OUT"
        ;;

    instances)
        curl -sf "$BASE/instances" 2>&1 | python3 -m json.tool 2>/dev/null || echo "[]"
        ;;

    *)
        echo "Usage: pinchtab.sh <navigate|snapshot|text|action|screenshot|instances>"
        echo "  navigate <url>              — open URL"
        echo "  snapshot                    — get accessibility tree"
        echo "  text                        — get page text content"
        echo "  action <type> <el> [value]  — click/fill/press element"
        echo "  screenshot [path]           — save screenshot"
        echo "  instances                   — list active instances"
        exit 1
        ;;
esac
