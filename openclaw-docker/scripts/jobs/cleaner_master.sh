#!/bin/bash
# Cleaner Agent — Master Cleanup Script
# Script-First: no model needed for mechanical cleanup
# Run by nightly cron at 04:00 Asia/Tashkent
# Output: /home/node/.openclaw/memory/cleanup/YYYY-MM-DD.md

set -euo pipefail

REPORT_DIR="/home/node/.openclaw/memory/cleanup"
VAULT_PATH="${USER_VAULT_PATH:-/data/obsidian}"
BOT_PATH="/data/bot/openclaw-docker"
TODAY=$(date '+%Y-%m-%d')
REPORT_FILE="$REPORT_DIR/$TODAY.md"
OPENCLAW_PATH="/home/node/.openclaw"
ISSUES=0
WARNINGS=()

mkdir -p "$REPORT_DIR"

report() { echo "$1" >> "$REPORT_FILE"; }
warn() { WARNINGS+=("$1"); report "⚠️ $1"; ISSUES=$((ISSUES+1)); }
info() { report "  $1"; }

report "# Cleanup Report — $TODAY"
report ""
report "Generated: $(date '+%Y-%m-%d %H:%M:%S %Z')"
report ""

# ──────────────────────────────────────────────────────────────
# 1. DISK SPACE
# ──────────────────────────────────────────────────────────────
report "## Disk Space"
DF_PCT=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
info "Root /: ${DF_PCT}%"
if [ "${DF_PCT}" -ge 85 ]; then
    warn "Disk usage at ${DF_PCT}% — above threshold"
    df -h / >> "$REPORT_FILE"
else
    info "OK"
fi
report ""

# ──────────────────────────────────────────────────────────────
# 2. DOCKER STATE
# ──────────────────────────────────────────────────────────────
report "## Docker Containers"
STOPPED=$(docker ps -a --filter 'status=exited' --format '{{.Names}} ({{.Status}})' 2>/dev/null | wc -l)
STOPPED_LIST=$(docker ps -a --filter 'status=exited' --format '{{.Names}}' 2>/dev/null | tr '\n' ' ')

if [ "${STOPPED}" -gt 0 ]; then
    info "Stopped containers: ${STOPPED}"
    for c in $(docker ps -a --filter 'status=exited' --format '{{.Names}}' 2>/dev/null); do
        info "  - $c"
    done
    # Clean exited containers that are notvikunja (already removed)
    docker container prune -f --filter "until=168h" 2>/dev/null || true
    info "(cleaned stopped containers > 7 days)"
else
    info "No stopped containers"
fi
report ""

# ──────────────────────────────────────────────────────────────
# 3. OBSIDIAN VAULT — Empty Files
# ──────────────────────────────────────────────────────────────
report "## Obsidian Vault"
EMPTY_COUNT=0
while IFS= read -r f; do
    [ -z "$f" ] && continue
    EMPTY_COUNT=$((EMPTY_COUNT+1))
    # Keep Tasks-Dashboard.md and index files
    basename_f=$(basename "$f")
    if [[ "$basename_f" == "Tasks-Dashboard.md" || "$basename_f" == "index.md" ]]; then
        info "SKIP (protected): $f"
    else
        # Don't auto-delete, just flag
        info "Empty: ${f#$VAULT_PATH/}"
    fi
done < <(find "$VAULT_PATH" -name '*.md' -empty 2>/dev/null)

if [ "$EMPTY_COUNT" -eq 0 ]; then
    info "Empty files: 0"
else
    info "Empty files: $EMPTY_COUNT (flagged, not auto-deleted)"
fi

# ──────────────────────────────────────────────────────────────
# 4. OBSIDIAN — Broken Wikilinks
# ──────────────────────────────────────────────────────────────
BROKEN_LINKS=()
KNOWN_STEMS=$(find "$VAULT_PATH" -name '*.md' -exec basename {} .md \; 2>/dev/null | tr '[:upper:]' '[:lower:]')

BROKEN_COUNT=0
while IFS= read -r f; do
    [ -z "$f" ] && continue
    while IFS= read -r line; do
        link=$(echo "$line" | sed 's/.*\[\[\([^]]*\)\]\].*/\1/' | cut -d'|' -f1 | cut -d'#' -f1 | xargs)
        [ -z "$link" ] && continue
        link_lower=$(echo "$link" | tr '[:upper:]' '[:lower:]')
        if ! echo "$KNOWN_STEMS" | grep -qi "^${link_lower}$"; then
            BROKEN_COUNT=$((BROKEN_COUNT+1))
            [ ${#BROKEN_LINKS[@]} -lt 20 ] && BROKEN_LINKS+=("  [[${link}]] → not found in ${f#$VAULT_PATH/}")
        fi
    done < <(grep -on '\[\[[^]]*\]\]' "$f" 2>/dev/null)
done < <(find "$VAULT_PATH" -name '*.md' -not -path '*/.git/*' -not -path '*/.obsidian/*' 2>/dev/null)

if [ "$BROKEN_COUNT" -eq 0 ]; then
    info "Broken wikilinks: 0 ✅"
else
    info "Broken wikilinks: $BROKEN_COUNT"
    for bl in "${BROKEN_LINKS[@]:0:10}"; do info "$bl"; done
    [ $BROKEN_COUNT -gt 10 ] && info "  ... and $((BROKEN_COUNT - 10)) more"
fi
report ""

# ──────────────────────────────────────────────────────────────
# 5. OBSIDIAN — Inbox Bloat
# ──────────────────────────────────────────────────────────────
INBOX_COUNT=$(find "$VAULT_PATH/Inbox" -name '*.md' 2>/dev/null | wc -l)
if [ "$INBOX_COUNT" -gt 50 ]; then
    warn "Inbox bloat: $INBOX_COUNT files (> 50)"
elif [ "$INBOX_COUNT" -gt 0 ]; then
    info "Inbox files: $INBOX_COUNT"
fi
report ""

# ──────────────────────────────────────────────────────────────
# 6. OPENCLAW — Old Session Logs
# ──────────────────────────────────────────────────────────────
report "## OpenClaw Sessions"
OLD_LOGS=$(find "$OPENCLAW_PATH/agents/main/sessions/" -name '*.jsonl' -mtime +30 2>/dev/null | wc -l)
if [ "$OLD_LOGS" -gt 0 ]; then
    info "Session logs > 30 days: $OLD_LOGS"
    # Archive old session logs (compress + delete original)
    find "$OPENCLAW_PATH/agents/main/sessions/" -name '*.jsonl' -mtime +30 2>/dev/null \
        | while read -r log; do
            gzip "$log" 2>/dev/null && info "  Archived: ${log#$OPENCLAW_PATH/}.gz"
        done
    info "(compressed originals)"
else
    info "Old session logs: 0"
fi

# Error logs
ERROR_COUNT=$(find "$OPENCLAW_PATH" -name '*.log' -path '*/log*' -mtime -1 2>/dev/null \
    | xargs grep -l 'ERROR\|CRITICAL' 2>/dev/null | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    info "Log files with errors (24h): $ERROR_COUNT"
else
    info "Error logs (24h): 0 ✅"
fi
report ""

# ──────────────────────────────────────────────────────────────
# 7. CRON — Skipped Jobs
# ──────────────────────────────────────────────────────────────
report "## Cron Jobs"
SKIPPED=$(openclaw cron list 2>/dev/null | grep -c "skipped" || echo "0")
if [ "$SKIPPED" -gt 0 ]; then
    warn "Skipped cron jobs: $SKIPPED"
    openclaw cron list 2>/dev/null | grep "skipped" | while read -r line; do
        info "  $line"
    done
else
    info "Skipped cron jobs: 0 ✅"
fi
report ""

# ──────────────────────────────────────────────────────────────
# 8. ORPHANED SCRIPTS
# ──────────────────────────────────────────────────────────────
report "## Orphaned Scripts"
KNOWN_CRONS=$(openclaw cron list 2>/dev/null | grep -oP 'scripts/jobs/\K[a-z_]+\.(sh|py)' | sort -u)
ALL_SCRIPTS=$(find "$BOT_PATH/scripts/jobs/" -maxdepth 1 \( -name '*.sh' -o -name '*.py' \) -printf '%f\n' 2>/dev/null)

ORPHAN_COUNT=0
for script in $ALL_SCRIPTS; do
    if ! echo "$KNOWN_CRONS" | grep -q "^${script}$"; then
        # Known orphans (old morning scripts that should be removed)
        case "$script" in
        morning_digest.sh|morning_system_status.sh|morning_task_briefing.sh|task_briefing.py|daily_report.py)
            # These are confirmed orphans — remove
            rm -f "$BOT_PATH/scripts/jobs/$script"
            info "Removed orphan: $script"
            ORPHAN_COUNT=$((ORPHAN_COUNT+1))
            ;;
        *)
            # Unknown orphan — flag only
            info "Orphan (unclear): $script"
            ;;
        esac
    fi
done
if [ "$ORPHAN_COUNT" -eq 0 ]; then
    info "No orphaned scripts"
fi
report ""

# ──────────────────────────────────────────────────────────────
# 9. MEMORY — MEMORY.md bloat
# ──────────────────────────────────────────────────────────────
report "## MEMORY.md"
MEM_LINES=$(wc -l < "$OPENCLAW_PATH/workspace-main/MEMORY.md" 2>/dev/null || echo "0")
info "MEMORY.md: $MEM_LINES lines"
if [ "${MEM_LINES:-0}" -gt 100 ]; then
    warn "MEMORY.md bloated ($MEM_LINES lines) — needs archive"
    # Archive oldest entries (keep last 50 lines)
    tail -n 50 "$OPENCLAW_PATH/workspace-main/MEMORY.md" > "/tmp/memory_trimmed.md"
    mv "/tmp/memory_trimmed.md" "$OPENCLAW_PATH/workspace-main/MEMORY.md"
    info "(trimmed to 50 lines)"
else
    info "OK"
fi
report ""

# ──────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────
report "## Summary"
report "- Issues: $ISSUES"
report "- Warnings: ${#WARNINGS[@]}"
report "- Disk: ${DF_PCT}%"
report "- Empty vault files: ${EMPTY_COUNT:-0}"
report "- Broken wikilinks: ${BROKEN_COUNT:-0}"
report "- Old session logs: ${OLD_LOGS:-0}"
report "- Orphaned scripts removed: ${ORPHAN_COUNT:-0}"
report ""
report "_Generated by Cleaner Agent (script-first, no model)_"

echo "[$(date)] Cleanup done. Issues: $ISSUES. Report: $REPORT_FILE"

# ──────────────────────────────────────────────────────────────
# CRITICAL? Send to Telegram
# ──────────────────────────────────────────────────────────────
if [ "$ISSUES" -gt 0 ] || [ "${DF_PCT:-0}" -ge 85 ]; then
    CRITICAL_MSG="[🧹 Claw/Cleaner — $TODAY]
⚠️ $ISSUES issue(s) found
📊 Disk: ${DF_PCT}%
📋 Full report: cleaner log"
    
    # Send via notify.py if available
    if [ -f "$BOT_PATH/skills/telegram/notify.py" ]; then
        python3 "$BOT_PATH/skills/telegram/notify.py" \
            --message "$CRITICAL_MSG" \
            --chat-id 6053956251 2>/dev/null || true
    fi
fi

[ "$ISSUES" -eq 0 ] && [ "${DF_PCT:-0}" -lt 85 ]
