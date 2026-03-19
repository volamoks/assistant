#!/bin/bash
# Obsidian Tasks CLI wrapper — replaces vikunja.sh
# Usage: bash /data/bot/openclaw-docker/skills/obsidian_tasks/obsidian_task.sh <command> [args...]

python3 /data/bot/openclaw-docker/skills/obsidian_tasks/obsidian_tasks.py "$@"
