#!/bin/bash
# git_backup.sh — commit and push openclaw-docker repo
# No LLM needed. Just git operations.

set -e
cd /data/bot/openclaw-docker

git add -A

if git diff --cached --quiet; then
    echo "No changes to commit"
    exit 0
fi

git commit -m "auto-backup $(date +%Y-%m-%d_%H:%M)"
git push origin main
echo "Backup complete"
