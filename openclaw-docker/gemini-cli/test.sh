#!/bin/bash
#
# Quick test script for Gemini CLI Docker service
#

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Gemini CLI Docker Test ===${NC}"
echo ""

cd "$(dirname "$0")/.."

# Test 1: Check if container is running
echo -e "${YELLOW}Test 1: Checking if gemini-cli container is running...${NC}"
if docker compose ps | grep -q "gemini-cli"; then
    echo -e "${GREEN}✓ Container is running${NC}"
else
    echo -e "${RED}✗ Container not running, attempting to start...${NC}"
    docker compose up -d gemini-cli
    sleep 5
fi

# Test 2: Check Gemini CLI installation
echo -e "${YELLOW}Test 2: Verifying Gemini CLI installation...${NC}"
if docker compose exec gemini-cli gemini --version &> /dev/null; then
    echo -e "${GREEN}✓ Gemini CLI is installed${NC}"
else
    echo -e "${RED}✗ Gemini CLI not found${NC}"
fi

# Test 3: Check MCP configuration
echo -e "${YELLOW}Test 3: Checking MCP configuration...${NC}"
if docker compose exec gemini-cli test -f /home/gemini/.gemini/settings.json; then
    echo -e "${GREEN}✓ MCP configuration exists${NC}"
    echo -e "${BLUE}MCP Config:${NC}"
    docker compose exec gemini-cli cat /home/gemini/.gemini/settings.json | head -20
else
    echo -e "${RED}✗ MCP configuration not found${NC}"
fi

# Test 4: Check Composio
echo -e "${YELLOW}Test 4: Verifying Composio installation...${NC}"
if docker compose exec gemini-cli composio --version &> /dev/null; then
    echo -e "${GREEN}✓ Composio CLI is installed${NC}"
else
    echo -e "${YELLOW}⚠ Composio CLI not found (may need installation)${NC}"
fi

# Test 5: Run a simple Gemini command
echo -e "${YELLOW}Test 5: Testing Gemini CLI...${NC}"
if docker compose exec gemini-cli gemini "Say 'Hello from Docker!'" --max-tokens=10 2>/dev/null; then
    echo -e "${GREEN}✓ Gemini CLI is working${NC}"
else
    echo -e "${YELLOW}⚠ Gemini CLI command test incomplete (may need auth)${NC}"
fi

echo ""
echo -e "${GREEN}=== Test Complete ===${NC}"
echo ""
echo "To use Gemini CLI:"
echo "  docker compose exec -it gemini-cli gemini"
echo ""
