#!/bin/bash
PROJ_PATH="${BOT_PROJECT_PATH:-/data/bot}"
cd "$PROJ_PATH/openclaw-docker/workspace/telegram" || exit 1

# Read MiniMax OAuth token from openclaw's auth-profiles (auto-refreshed by openclaw)
AUTH_PROFILES="/home/node/.openclaw/agents/main/agent/auth-profiles.json"
MINIMAX_TOKEN=$(python3 -c "
import json, sys
try:
    d = json.load(open('$AUTH_PROFILES'))
    print(d['profiles']['minimax-portal:default']['access'])
except Exception as e:
    sys.exit(1)
" 2>/dev/null)

if [ -z "$MINIMAX_TOKEN" ]; then
    echo "ERROR: Could not read MiniMax OAuth token from $AUTH_PROFILES" >&2
    exit 1
fi

export LLM_BASE_URL="https://api.minimax.io/v1"
export LLM_API_KEY="$MINIMAX_TOKEN"
export ENRICH_MODEL="MiniMax-M2.5"

python3 enrichment.py --model "$ENRICH_MODEL" 2>&1
