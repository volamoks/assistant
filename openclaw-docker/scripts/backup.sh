#!/usr/bin/env bash
# Restic backup for openclaw-docker ecosystem
# Repo: ~/Backups/openclaw-restic  |  Password: RESTIC_PASSWORD env var
set -euo pipefail

REPO="${RESTIC_REPOSITORY:-$HOME/Backups/openclaw-restic}"
BOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$BOT_DIR/scripts/backup.log"
MAX_LOG_LINES=500

export RESTIC_REPOSITORY="$REPO"
# RESTIC_PASSWORD must be set in environment (e.g. from .env)

if [[ -z "${RESTIC_PASSWORD:-}" ]]; then
  echo "[backup] ERROR: RESTIC_PASSWORD not set" | tee -a "$LOG"
  exit 1
fi

# Init repo if not exists
if ! restic snapshots &>/dev/null; then
  echo "[backup] Initializing Restic repo at $REPO" | tee -a "$LOG"
  restic init
fi

echo "[backup] $(date '+%Y-%m-%d %H:%M:%S') — starting backup" | tee -a "$LOG"

restic backup \
  "$BOT_DIR/core" \
  "$BOT_DIR/cron" \
  "$BOT_DIR/prompts" \
  "$BOT_DIR/skills" \
  "$BOT_DIR/litellm" \
  "$BOT_DIR/scripts" \
  "$BOT_DIR/docker-compose.yml" \
  "$BOT_DIR/docker-compose.apps.yml" \
  "$BOT_DIR/.env" \
  --exclude="$BOT_DIR/core/agents/*/agent/sessions" \
  --exclude="$BOT_DIR/core/canvas" \
  --exclude="*.log" \
  --exclude="*.db-shm" \
  --exclude="*.db-wal" \
  2>&1 | tee -a "$LOG"

# Retention: 7 daily, 4 weekly, 3 monthly
restic forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 3 \
  --prune \
  2>&1 | tee -a "$LOG"

echo "[backup] $(date '+%Y-%m-%d %H:%M:%S') — done" | tee -a "$LOG"

# Trim log to last MAX_LOG_LINES lines
tail -n "$MAX_LOG_LINES" "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
