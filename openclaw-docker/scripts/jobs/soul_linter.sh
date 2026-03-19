#!/bin/bash
# Soul Linter — Script-First, no model
# Run by nightly cron to validate workspace SOUL integrity
# Exit 0 = all good, Exit 1 = issues found

set -e
WORKSPACES="/home/node/.openclaw"
REPORT_FILE="/home/node/.openclaw/memory/soul_linter.log"
ISSUES=0

log() { echo "[$(date '+%Y-%m-%d %H:%M')] $1" | tee -a "$REPORT_FILE"; }
warn() { echo "[$(date '+%Y-%m-%d %H:%M')] ⚠️  $1" | tee -a "$REPORT_FILE"; ISSUES=$((ISSUES+1)); }

log "=== SOUL Linter Run ==="

# 1. Check each workspace SOUL contains its agent identifier
check_soul() {
    local workspace="$1"
    local identifier="$2"
    local soul="$WORKSPACES/$workspace/SOUL.md"
    
    if [ ! -f "$soul" ]; then
        warn "Missing SOUL: $soul"
        return
    fi
    
    if ! grep -q "$identifier" "$soul"; then
        warn "$workspace SOUL missing identifier '$identifier'"
    fi
}

check_soul "workspace-architect" "ARCHITECT"
check_soul "workspace-coder" "CODER"
check_soul "workspace-researcher" "RESEARCH"
check_soul "workspace-analyst" "ANALYST"
check_soul "workspace-work" "WORK AGENT"
check_soul "workspace-main" "Router\|Orchestrator"

# 2. Check MEMORY.md doesn't exceed 100 lines (bloat guard)
if [ -f "$WORKSPACES/workspace-main/MEMORY.md" ]; then
    LINES=$(wc -l < "$WORKSPACES/workspace-main/MEMORY.md")
    if [ "$LINES" -gt 100 ]; then
        warn "MEMORY.md bloated: $LINES lines (limit: 100). Needs rotation."
    fi
fi

# 3. Session logs older than 30 days → list for cleanup
OLD_LOGS=$(find "$WORKSPACES/agents/main/sessions/" -name "*.jsonl" -mtime +30 2>/dev/null | wc -l)
if [ "$OLD_LOGS" -gt 50 ]; then
    warn "Old session logs: $OLD_LOGS files > 30 days. Consider cleanup."
fi

# 4. prompts/SOUL_*.md newer than workspace → possible drift
for prompt_soul in "$WORKSPACES"/prompts/SOUL_*.md; do
    [ -f "$prompt_soul" ] || continue
    agent=$(basename "$prompt_soul" .md | sed 's/SOUL_//' | tr '[:upper:]' '[:lower:]')
    workspace_soul="$WORKSPACES/workspace-$agent/SOUL.md"
    [ -f "$workspace_soul" ] || continue
    prompt_time=$(stat -c %Y "$prompt_soul" 2>/dev/null || stat -f %m "$prompt_soul" 2>/dev/null)
    ws_time=$(stat -c %Y "$workspace_soul" 2>/dev/null || stat -f %m "$workspace_soul" 2>/dev/null)
    if [ "$prompt_time" -gt "$((ws_time + 86400))" ]; then
        warn "prompts/SOUL_$agent.md newer than workspace — possible drift"
    fi
done

# 5. opencode routing documented?
if ! grep -q "opencode\|ACP.*runtime" "$WORKSPACES/workspace-main/AGENTS.md" 2>/dev/null; then
    warn "AGENTS.md missing opencode/ACP routing docs"
fi

log "=== Linter Done: $ISSUES issues ==="
[ "$ISSUES" -eq 0 ]
