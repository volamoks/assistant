#!/bin/bash
# Auto-refresh Google Vertex AI OAuth token
# Called via cron/launchagent every ~50 minutes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SCRIPT_DIR/token_refresh.log"
CREDS_FILE="$SCRIPT_DIR/vertex_credentials.json"
LITELLM_ENV="$SCRIPT_DIR/litellm/.env"
DOCKER="/usr/local/bin/docker"
CONTAINER="openclaw-docker-litellm-proxy-1"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

# Check if credentials file exists
if [ ! -f "$CREDS_FILE" ]; then
    log "❌ Vertex credentials file not found: $CREDS_FILE"
    exit 1
fi

log "🔄 Refreshing Vertex AI OAuth token..."

# Extract credentials using Python
TOKEN_DATA=$($DOCKER exec openclaw-latest python3 -c "
import json
import requests
import os

creds = json.load(open('$CREDS_FILE'))

# Refresh the token
data = {
    'grant_type': 'refresh_token',
    'client_id': creds['client_id'],
    'client_secret': creds['client_secret'],
    'refresh_token': creds['refresh_token']
}

response = requests.post('https://oauth2.googleapis.com/token', data=data)
if response.status_code == 200:
    j = response.json()
    print(json.dumps({
        'access_token': j['access_token'],
        'expires_in': j.get('expires_in', 3600)
    }))
else:
    print(json.dumps({'error': response.text}))
" 2>/dev/null)

if echo "$TOKEN_DATA" | grep -q "error"; then
    log "❌ Token refresh failed: $TOKEN_DATA"
    exit 1
fi

ACCESS_TOKEN=$(echo "$TOKEN_DATA" | $DOCKER exec openclaw-latest python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
EXPIRES_IN=$(echo "$TOKEN_DATA" | $DOCKER exec openclaw-latest python3 -c "import json,sys; print(json.load(sys.stdin)['expires_in'])")

log "✅ Got new access token (${ACCESS_TOKEN:0:20}...)"

# Update the vertex_credentials.json file inside the container
$DOCKER exec openclaw-latest python3 -c "
import json

creds = json.load(open('$CREDS_FILE'))
creds['access_token'] = '$ACCESS_TOKEN'
creds['expiry_date'] = $(date +%s)000 + $EXPIRES_IN * 1000

with open('$CREDS_FILE', 'w') as f:
    json.dump(creds, f, indent=2)
"

# Update litellm .env file
$DOCKER exec openclaw-latest bash -c "
export GOOGLE APPLICATION_CREDENTIALS='$CREDS_FILE'
echo 'GOOGLE_VERTEXAI_KEY=$ACCESS_TOKEN' >> $LITELLM_ENV
echo 'GOOGLE_API_KEY=$ACCESS_TOKEN' >> $LITELLM_ENV
# Remove duplicates keeping last
grep -v '^GOOGLE_VERTEXAI_KEY=' $LITELLM_ENV | grep -v '^GOOGLE_API_KEY=' > /tmp/env.new
echo 'GOOGLE_VERTEXAI_KEY=$ACCESS_TOKEN' >> /tmp/env.new
echo 'GOOGLE_API_KEY=$ACCESS_TOKEN' >> /tmp/env.new
mv /tmp/env.new $LITELLM_ENV
"

log "✅ Updated $LITELLM_ENV"

# Restart litellm-proxy to pick up new credentials
$DOCKER restart $CONTAINER 2>/dev/null || true

log "✅ Token refresh complete, litellm-proxy restarted"
