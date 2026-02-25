#!/bin/bash
# post_setup.sh — Run AFTER docker compose up to install extra tools in containers
# Run: bash openclaw-docker/scripts/post_setup.sh

set -e
echo "🔧 Post-setup: installing extra tools in openclaw-latest..."

# --- Gemini CLI ---
echo "📦 Installing @google/gemini-cli (gemini-3.1-pro access)..."
docker exec -u root openclaw-latest npm install -g @google/gemini-cli --loglevel=error
GEMINI_VER=$(docker exec openclaw-latest gemini --version 2>/dev/null || echo "unknown")
echo "✅ Gemini CLI installed: v${GEMINI_VER}"

# --- Python Google libs (for gmail.sh / gcal.sh) ---
echo "📦 Installing Google Python libs..."
docker exec openclaw-latest pip3 install \
  google-auth-oauthlib \
  google-auth-httplib2 \
  google-api-python-client \
  --break-system-packages --quiet 2>/dev/null || true
echo "✅ Google Python libs installed"

echo ""
echo "✅ Post-setup complete!"
echo ""
echo "🔑 Now authorize Gemini CLI (run in container):"
echo "   docker exec -it openclaw-latest gemini auth login"
echo ""
echo "🔑 Now authorize Google Gmail/Calendar:"
echo "   Place credentials.json at: openclaw-docker/shared/google_credentials.json"
echo "   Then run: python3 openclaw-docker/scripts/google_auth.py"
