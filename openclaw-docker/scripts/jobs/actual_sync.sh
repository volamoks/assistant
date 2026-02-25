#!/bin/bash
PROJ_PATH="${BOT_PROJECT_PATH:-/data/bot}"
export ACTUAL_URL="http://host.docker.internal:5006"
export ACTUAL_FILE="13ff18b4-1062-4238-ab67-416f1bbf0ce9"
# ACTUAL_PASSWORD is provided by container env var

python3 "$PROJ_PATH/pfm/sync_to_actual.py" 2>&1
