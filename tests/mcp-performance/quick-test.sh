#!/bin/bash
#
# Quick test to verify Composio MCP setup with Gemini
# Run this before the full performance comparison
#

set -e

# Try to load environment from openclaw-docker/.env if exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../../openclaw-docker/.env"
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs) 2>/dev/null || true
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Quick Test: Gemini + Composio MCP ===${NC}"
echo ""

# 1. Check Gemini is available
echo -e "${YELLOW}1. Checking Gemini CLI...${NC}"
if command -v gemini &> /dev/null; then
    echo -e "${GREEN}✓ Gemini CLI found at: $(which gemini)${NC}"
else
    echo -e "${RED}✗ Gemini CLI not found${NC}"
    exit 1
fi

# 2. Check Composio API key
echo ""
echo -e "${YELLOW}2. Checking Composio API key...${NC}"
if [ -n "$COMPOSIO_API_KEY" ]; then
    echo -e "${GREEN}✓ COMPOSIO_API_KEY is set${NC}"
else
    echo -e "${RED}✗ COMPOSIO_API_KEY not set${NC}"
    echo "Run: export COMPOSIO_API_KEY='your-api-key'"
    exit 1
fi

# 3. Check Gemini settings
echo ""
echo -e "${YELLOW}3. Checking Gemini settings...${NC}"
if [ -f "$HOME/.gemini/settings.json" ]; then
    echo -e "${GREEN}✓ settings.json exists${NC}"
    if grep -q "composio" "$HOME/.gemini/settings.json"; then
        echo -e "${GREEN}✓ Composio MCP configured${NC}"
    else
        echo -e "${YELLOW}⚠ Composio MCP not configured${NC}"
        echo "Run: ./setup-gemini-mcp.sh"
    fi
else
    echo -e "${RED}✗ settings.json not found${NC}"
fi

# 4. Check Composio CLI
echo ""
echo -e "${YELLOW}4. Checking Composio CLI availability...${NC}"
if command -v composio &> /dev/null; then
    echo -e "${GREEN}✓ Composio CLI installed${NC}"
else
    echo -e "${YELLOW}⚠ Composio CLI not installed globally${NC}"
    echo "Will use npx composio-core@latest instead"
fi

# 5. Check Gmail connection
echo ""
echo -e "${YELLOW}5. Checking Gmail connection...${NC}"
CONNECTIONS_OUTPUT=$(npx -y composio-core@latest connected-accounts list 2>/dev/null || echo "")
if echo "$CONNECTIONS_OUTPUT" | grep -qi "gmail"; then
    echo -e "${GREEN}✓ Gmail account connected${NC}"
else
    echo -e "${YELLOW}⚠ No Gmail connection found${NC}"
    echo "You may need to connect Gmail via:"
    echo "  npx composio-core@latest connections add gmail"
fi

# 6. Test prompt for Gemini
echo ""
echo -e "${YELLOW}6. Test prompt ready${NC}"
echo ""
echo "You can now test Gemini with Composio using:"
echo ""
echo -e "${GREEN}  gemini 'List my recent Gmail messages'${NC}"
echo ""
echo "Or run the full comparison:"
echo -e "${GREEN}  node compare.mjs${NC}"
echo ""
