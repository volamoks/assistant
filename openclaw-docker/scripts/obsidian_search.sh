#!/bin/bash
# Obsidian Section Search — returns only the relevant markdown section, not the whole file
# Usage: obsidian_search.sh "query" [--limit N] [--vault /path]
# Example: obsidian_search.sh "POST /users" --limit 3
#
# Output: up to N sections (header + content), max 150 lines each
# Designed to be called by sysadmin agent to save tokens on large docs

QUERY="$1"
LIMIT=3
VAULT="/data/obsidian"
MAX_LINES=150

shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --limit) LIMIT="$2"; shift 2 ;;
        --vault) VAULT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

if [ -z "$QUERY" ]; then
    echo "Usage: obsidian_search.sh <query> [--limit N] [--vault /path]"
    exit 1
fi

# Find files containing the query (case insensitive)
MATCHING_FILES=$(grep -rl --include="*.md" -i "$QUERY" "$VAULT" 2>/dev/null | head -20)

if [ -z "$MATCHING_FILES" ]; then
    echo "No results for: $QUERY"
    exit 0
fi

COUNT=0
echo "🔍 Results for: \"$QUERY\""
echo ""

for FILE in $MATCHING_FILES; do
    [ $COUNT -ge $LIMIT ] && break

    RELPATH="${FILE#$VAULT/}"

    # Extract sections containing the query using awk
    # Splits file by headers (##, ###), returns section where query appears
    RESULT=$(awk -v q="$QUERY" -v max="$MAX_LINES" '
    BEGIN { IGNORECASE=1; buf=""; header=""; found=0; lines=0 }
    /^#{1,4} / {
        if (found && lines > 0) {
            print buf
            found=0; buf=""; lines=0
        }
        header=$0; buf=header"\n"; found=0; lines=0
    }
    !/^#{1,4} / {
        buf = buf $0 "\n"
        lines++
        if (tolower($0) ~ tolower(q)) found=1
        if (lines > max) {
            if (found) buf = buf "... (section truncated at " max " lines)\n"
            if (found) { print buf }
            buf=""; lines=0; found=0
        }
    }
    END {
        if (found && lines > 0) print buf
    }
    ' "$FILE")

    if [ -n "$RESULT" ]; then
        echo "📄 $RELPATH"
        echo "────────────────────────────────"
        echo "$RESULT"
        echo ""
        COUNT=$((COUNT + 1))
    fi
done

# If no sections extracted (query in frontmatter/inline), fallback to grep context
if [ $COUNT -eq 0 ]; then
    echo "Found in (grep context):"
    for FILE in $MATCHING_FILES; do
        [ $COUNT -ge $LIMIT ] && break
        RELPATH="${FILE#$VAULT/}"
        echo "📄 $RELPATH"
        echo "────────────────────────────────"
        grep -n -i -A 5 -B 2 "$QUERY" "$FILE" | head -40
        echo ""
        COUNT=$((COUNT + 1))
    done
fi

echo "[$COUNT result(s) shown, limit=$LIMIT]"
