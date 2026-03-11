#!/bin/bash
# Auto-refresh Gemini OAuth token in openclaw container
# Runs every 50 minutes via LaunchAgent

DOCKER="/usr/local/bin/docker"
CONTAINER="openclaw-latest"
CREDS_PATH="/home/node/.openclaw/gemini-config/oauth_creds.json"
LOG="/Users/abror_mac_mini/Projects/bot/openclaw-docker/scripts/gemini-token-refresh.log"
CLIENT_ID="681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com"
CLIENT_SECRET="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"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

# Check if container is running
if ! $DOCKER ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  log "Container $CONTAINER not running, skipping"
  exit 0
fi

# Check if token needs refresh (refresh if < 10 min remaining)
NEEDS_REFRESH=$($DOCKER exec "$CONTAINER" node -e "
  const fs = require('fs');
  try {
    const c = JSON.parse(fs.readFileSync('$CREDS_PATH'));
    const remaining = c.expiry_date - Date.now();
    console.log(remaining < 600000 ? 'yes' : 'no');
  } catch(e) { console.log('yes'); }
" 2>/dev/null)

if [ "$NEEDS_REFRESH" != "yes" ]; then
  exit 0
fi

log "Refreshing Gemini OAuth token..."

RESULT=$($DOCKER exec "$CONTAINER" node -e "
const https = require('https');
const fs = require('fs');
const creds = JSON.parse(fs.readFileSync('$CREDS_PATH'));
const data = new URLSearchParams({
  grant_type: 'refresh_token',
  client_id: '$CLIENT_ID',
  client_secret: '$CLIENT_SECRET',
  refresh_token: creds.refresh_token
}).toString();
const req = https.request({
  hostname: 'oauth2.googleapis.com', path: '/token', method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
}, (res) => {
  let body = '';
  res.on('data', d => body += d);
  res.on('end', () => {
    const j = JSON.parse(body);
    if (j.access_token) {
      const updated = {...creds, access_token: j.access_token, expiry_date: Date.now() + j.expires_in * 1000};
      fs.writeFileSync('$CREDS_PATH', JSON.stringify(updated, null, 2));
      console.log('ok');
    } else { console.log('error: ' + JSON.stringify(j)); }
  });
});
req.write(data); req.end();
" 2>/dev/null)

if [ "$RESULT" = "ok" ]; then
  log "Token refreshed successfully"
else
  log "Token refresh failed: $RESULT"
fi
