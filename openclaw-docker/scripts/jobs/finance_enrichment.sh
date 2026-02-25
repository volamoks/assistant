#!/bin/bash
PROJ_PATH="${BOT_PROJECT_PATH:-/data/bot}"
cd "$PROJ_PATH/openclaw-docker/workspace/telegram" || exit 1
python3 enrichment.py --model qwen3:8b 2>&1
