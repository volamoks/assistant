#!/bin/bash
# refresh_vertex_token.sh — Auto-refresh Vertex AI OAuth token for LiteLLM
#
# Reads the fresh refresh_token from ~/.gemini/oauth_creds.json (managed by Gemini CLI),
# exchanges it for a new access_token, then updates litellm/.env and restarts litellm-proxy.
#
# Run automatically via launchd every 50 minutes. Install:
#   cp openclaw-docker/scripts/com.openclaw.vertex-token-refresh.plist ~/Library/LaunchAgents/
#   launchctl load ~/Library/LaunchAgents/com.openclaw.vertex-token-refresh.plist

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/litellm/.env"
LOG_FILE="$PROJECT_DIR/scripts/token_refresh.log"

# Gemini CLI's OAuth app credentials (public installed-app client — safe to commit)
# Source: @google/gemini-cli-core/dist/src/code_assist/oauth2.js
CLIENT_ID="681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
CLIENT_SECRET="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"

# The oauth_creds.json is managed by Gemini CLI auth — read refresh_token dynamically
OAUTH_CREDS="$HOME/.gemini/oauth_creds.json"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "🔄 Refreshing Vertex AI OAuth token..."

# --- Read refresh token from Gemini CLI's credential file ---
if [[ ! -f "$OAUTH_CREDS" ]]; then
  log "❌ Credentials file not found: $OAUTH_CREDS"
  exit 1
fi

REFRESH_TOKEN=$(python3 -c "import json; d=json.load(open('$OAUTH_CREDS')); print(d['refresh_token'])" 2>/dev/null)
if [[ -z "$REFRESH_TOKEN" ]]; then
  log "❌ Could not read refresh_token from $OAUTH_CREDS"
  exit 1
fi

# --- Request a new access token ---
RESPONSE=$(curl -s -X POST "https://oauth2.googleapis.com/token" \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "client_secret=$CLIENT_SECRET" \
  --data-urlencode "refresh_token=$REFRESH_TOKEN" \
  --data-urlencode "grant_type=refresh_token")

ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])" 2>/dev/null || true)

if [[ -z "$ACCESS_TOKEN" ]]; then
  ERROR=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error_description', d.get('error', 'unknown')))" 2>/dev/null || echo "$RESPONSE")
  log "❌ Failed to refresh token: $ERROR"
  exit 1
fi

log "✅ Got new access token (${ACCESS_TOKEN:0:20}...)"

# --- Update litellm/.env and write vertex_credentials.json ---
# Use python3 to handle symlinks correctly on macOS
python3 - <<PYEOF
import os, re, sys, json

env_file = "$ENV_FILE"
real_file = os.path.realpath(env_file)
token = "$ACCESS_TOKEN"
refresh = "$REFRESH_TOKEN"
client_id = "$CLIENT_ID"
client_secret = "$CLIENT_SECRET"

# 1. Write the vertex_credentials.json file in ADC format
creds_path = os.path.join(os.path.dirname(real_file), "vertex_credentials.json")
creds = {
    "client_id": client_id,
    "client_secret": client_secret,
    "refresh_token": refresh,
    "type": "authorized_user"
}
with open(creds_path, 'w') as f:
    json.dump(creds, f, indent=2)
print(f"Created: {creds_path}")

# 2. Update the .env file to point GOOGLE_APPLICATION_CREDENTIALS to the file
with open(real_file, 'r') as f:
    content = f.read()

# We set GOOGLE_APPLICATION_CREDENTIALS so litellm automatically picks it up for all vertex calls
if re.search(r'^GOOGLE_APPLICATION_CREDENTIALS=', content, re.MULTILINE):
    content = re.sub(r'^GOOGLE_APPLICATION_CREDENTIALS=.*', 'GOOGLE_APPLICATION_CREDENTIALS=/app/vertex_credentials.json', content, flags=re.MULTILINE)
else:
    content += '\nGOOGLE_APPLICATION_CREDENTIALS=/app/vertex_credentials.json\n'

with open(real_file, 'w') as f:
    f.write(content)

print(f"Updated: {real_file}")
PYEOF


log "✅ Updated $ENV_FILE and vertex_credentials.json"

# --- Re-create litellm container to pick up new env block and volume mounts ---
# Recreates only if necessary (if docker-compose.yml changed) or just restarts.
cd "$PROJECT_DIR"
docker compose up -d litellm >> "$LOG_FILE" 2>&1
# Do a hard restart to be safe
docker restart litellm-proxy >> "$LOG_FILE" 2>&1
log "✅ litellm-proxy restarted — Vertex AI cascade should be healthy"

# Keep log small (last 200 lines)
tail -200 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
