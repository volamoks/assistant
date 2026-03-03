#!/bin/bash
#
# Entrypoint script for Gemini CLI Docker service
# Configures MCP and initializes Gemini CLI
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Gemini CLI Docker Service ===${NC}"
echo ""

# Create config directory if not exists
mkdir -p "$GEMINI_CONFIG_DIR"

# Generate MCP configuration from template
if [ -f "$GEMINI_CONFIG_DIR/settings.json.template" ]; then
    echo -e "${YELLOW}Generating MCP configuration...${NC}"
    
    # Replace COMPOSIO_API_KEY in template
    if [ -n "$COMPOSIO_API_KEY" ]; then
        sed "s/\${COMPOSIO_API_KEY}/$COMPOSIO_API_KEY/g" \
            "$GEMINI_CONFIG_DIR/settings.json.template" > \
            "$GEMINI_CONFIG_DIR/settings.json"
        echo -e "${GREEN}✓ MCP configuration created with Composio API key${NC}"
    else
        echo -e "${YELLOW}⚠ COMPOSIO_API_KEY not set, using default config${NC}"
        cp "$GEMINI_CONFIG_DIR/settings.json.template" "$GEMINI_CONFIG_DIR/settings.json"
    fi
fi

# Check if settings.json exists, create default if not
if [ ! -f "$GEMINI_CONFIG_DIR/settings.json" ]; then
    echo -e "${YELLOW}Creating default Gemini settings...${NC}"
    cat > "$GEMINI_CONFIG_DIR/settings.json" << 'EOF'
{
  "mcp": {
    "servers": {}
  }
}
EOF
fi

# Add Composio MCP server if API key is available
if [ -n "$COMPOSIO_API_KEY" ] && command -v jq &> /dev/null; then
    echo -e "${YELLOW}Configuring Composio MCP server...${NC}"

    # Inject composio server into existing settings (deep set, preserves other servers)
    # Gemini CLI uses mcpServers at top level (not mcp.servers)
    NEW_SETTINGS=$(jq --arg key "$COMPOSIO_API_KEY" '
    .mcpServers.composio = {
      command: "mcp",
      args: ["start"],
      env: { COMPOSIO_API_KEY: $key },
      trust: true
    }' "$GEMINI_CONFIG_DIR/settings.json"
    )

    echo "$NEW_SETTINGS" > "$GEMINI_CONFIG_DIR/settings.json"
    echo -e "${GREEN}✓ Composio MCP server configured${NC}"
fi

# Display configuration
echo ""
echo -e "${BLUE}=== Configuration ===${NC}"
echo "Gemini config dir: $GEMINI_CONFIG_DIR"
echo "Composio API key: ${COMPOSIO_API_KEY:+****${COMPOSIO_API_KEY: -4}}"
echo ""

# Show available tools
echo -e "${BLUE}=== Available Commands ===${NC}"
echo "  gemini          - Start interactive Gemini CLI"
echo "  gemini --help   - Show help"
echo "  composio        - Composio CLI"
echo ""

# Check Gemini CLI
echo -e "${YELLOW}Verifying Gemini CLI installation...${NC}"
if gemini --version &> /dev/null; then
    echo -e "${GREEN}✓ Gemini CLI is ready${NC}"
else
    echo -e "${RED}✗ Gemini CLI not found${NC}"
fi

# Check Composio
echo -e "${YELLOW}Verifying Composio installation...${NC}"
if composio --version &> /dev/null; then
    echo -e "${GREEN}✓ Composio CLI is ready${NC}"
else
    echo -e "${YELLOW}⚠ Composio CLI not found (may need npm install)${NC}"
fi

echo ""
echo -e "${GREEN}=== Gemini CLI Docker Service Ready ===${NC}"
echo ""

# Execute the provided command
exec "$@"
