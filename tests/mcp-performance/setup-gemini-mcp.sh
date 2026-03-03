#!/bin/bash
#
# Setup script for Gemini CLI with Composio MCP server
# This configures Gemini to use Composio tools via MCP protocol
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GEMINI_CONFIG_DIR="$HOME/.gemini"
GEMINI_SETTINGS="$GEMINI_CONFIG_DIR/settings.json"
GEMINI_SETTINGS_BACKUP="$GEMINI_CONFIG_DIR/settings.json.backup.$(date +%Y%m%d_%H%M%S)"

echo -e "${BLUE}=== Gemini CLI + Composio MCP Setup ===${NC}"
echo ""

# Check if Gemini CLI is installed
echo -e "${YELLOW}Checking Gemini CLI installation...${NC}"
if command -v gemini &> /dev/null; then
    GEMINI_PATH=$(which gemini)
    echo -e "${GREEN}✓ Gemini CLI found at: $GEMINI_PATH${NC}"
    gemini --version 2>/dev/null || echo "Gemini CLI installed"
else
    echo -e "${RED}✗ Gemini CLI not found!${NC}"
    echo "Installing Gemini CLI..."
    npm install -g @google/gemini-cli
fi

# Check for Composio API key
echo ""
echo -e "${YELLOW}Checking Composio configuration...${NC}"
if [ -z "$COMPOSIO_API_KEY" ]; then
    echo -e "${RED}✗ COMPOSIO_API_KEY not set in environment${NC}"
    echo "Please set it with: export COMPOSIO_API_KEY='your-api-key'"
    exit 1
else
    echo -e "${GREEN}✓ COMPOSIO_API_KEY is set${NC}"
fi

# Create Gemini config directory if needed
if [ ! -d "$GEMINI_CONFIG_DIR" ]; then
    echo -e "${YELLOW}Creating Gemini config directory...${NC}"
    mkdir -p "$GEMINI_CONFIG_DIR"
fi

# Backup existing settings if present
if [ -f "$GEMINI_SETTINGS" ]; then
    echo -e "${YELLOW}Backing up existing settings to:${NC} $GEMINI_SETTINGS_BACKUP"
    cp "$GEMINI_SETTINGS" "$GEMINI_SETTINGS_BACKUP"
fi

# Check if npx is available
if ! command -v npx &> /dev/null; then
    echo -e "${RED}✗ npx not found. Please install Node.js${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}=== Configuration Options ===${NC}"
echo ""
echo "Composio MCP server can be started in two ways:"
echo "  1) Via npx (recommended for testing): npx -y composio-core@latest mcp start"
echo "  2) Via global install: composio mcp start"
echo ""

# Read current settings or create new
echo -e "${YELLOW}Configuring Gemini settings.json...${NC}"

# Get current settings or use defaults
if [ -f "$GEMINI_SETTINGS" ]; then
    CURRENT_SETTINGS=$(cat "$GEMINI_SETTINGS")
else
    CURRENT_SETTINGS='{}'
fi

# Create MCP configuration
MCP_CONFIG='{
  "mcp": {
    "servers": {
      "composio": {
        "command": "npx",
        "args": ["-y", "composio-core@latest", "mcp", "start"],
        "env": {
          "COMPOSIO_API_KEY": "'"$COMPOSIO_API_KEY"'"
        }
      }
    }
  }
}'

# Merge with existing settings (preserve other config)
MERGED_SETTINGS=$(node -e "
const current = $CURRENT_SETTINGS;
const mcpConfig = $MCP_CONFIG;
const merged = { ...current, ...mcpConfig, mcp: { ...(current.mcp || {}), ...mcpConfig.mcp } };
console.log(JSON.stringify(merged, null, 2));
")

# Write new settings
echo "$MERGED_SETTINGS" > "$GEMINI_SETTINGS"
echo -e "${GREEN}✓ Updated Gemini settings.json${NC}"

echo ""
echo -e "${BLUE}=== Configuration Complete ===${NC}"
echo ""
echo -e "${GREEN}Gemini CLI is now configured with Composio MCP!${NC}"
echo ""
echo "Settings file: $GEMINI_SETTINGS"
echo ""
echo "To test the MCP connection:"
echo "  1. Start a new Gemini session: gemini"
echo "  2. Ask: 'List my Gmail messages'"
echo "  3. Or run: gemini --mcp-test"
echo ""
echo "To compare performance, run:"
echo "  cd tests/mcp-performance && node compare.mjs"
echo ""

# Verify the configuration
echo -e "${YELLOW}Verifying configuration...${NC}"
if [ -f "$GEMINI_SETTINGS" ]; then
    echo -e "${GREEN}✓ Settings file exists${NC}"
    if grep -q "composio" "$GEMINI_SETTINGS"; then
        echo -e "${GREEN}✓ Composio MCP configuration found${NC}"
    else
        echo -e "${RED}✗ Composio MCP configuration not found${NC}"
    fi
fi

echo ""
echo -e "${BLUE}=== Backup Information ===${NC}"
if [ -f "$GEMINI_SETTINGS_BACKUP" ]; then
    echo "Original settings backed up to: $GEMINI_SETTINGS_BACKUP"
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
