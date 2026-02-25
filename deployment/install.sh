#!/bin/bash
set -e

# Jarvis Installer (Clean Edition)
# Run this on the destination Mac Mini.

echo "🚀 Installing Jarvis (Samurai 3.5)..."

# 1. Setup Directories
OPENCLAW_DIR="$HOME/.openclaw"
mkdir -p "$OPENCLAW_DIR"/{agents,prompts,docs,skills}

echo "📂 Copying files..."
# Copy from current directory (we assume we are inside the deployment package)
cp core/openclaw.json "$OPENCLAW_DIR/"
cp agents/*.json "$OPENCLAW_DIR/agents/"
cp prompts/*.md "$OPENCLAW_DIR/prompts/"
cp docs/*.md "$OPENCLAW_DIR/docs/"
cp -r skills/* "$OPENCLAW_DIR/skills/"

# 2. Fix Paths
echo "🔧 Fixing paths..."
PROMPTS_DIR="$OPENCLAW_DIR/prompts"
# The default path used in your configs (customize if different)
ARTIFACT_PATH="${ARTIFACT_PATH:-/Users/abror/.gemini/antigravity/brain/b4934c14-3c8c-4e86-af31-5c0e83614148}"
ESCAPED_ARTIFACT_PATH=$(echo "$ARTIFACT_PATH" | sed 's/\//\\\//g')
ESCAPED_PROMPTS_DIR=$(echo "$PROMPTS_DIR" | sed 's/\//\\\//g')

if [ -f "$OPENCLAW_DIR/openclaw.json" ]; then
    sed -i '' "s/$ESCAPED_ARTIFACT_PATH/$ESCAPED_PROMPTS_DIR/g" "$OPENCLAW_DIR/openclaw.json"
fi

for file in "$OPENCLAW_DIR/agents"/*.json; do
    if [ -f "$file" ]; then
        sed -i '' "s/$ESCAPED_ARTIFACT_PATH/$ESCAPED_PROMPTS_DIR/g" "$file"
    fi
done

# 3. Install Skills
echo "📦 Installing Skill Dependencies..."
SKILLS_DIR="$OPENCLAW_DIR/skills"
if [ -d "$SKILLS_DIR" ]; then
    # Install root dependencies if any
    if [ -f "$SKILLS_DIR/package.json" ]; then
        cd "$SKILLS_DIR" && npm install --silent
    fi
    
    # Iterate through each skill folder and install dependencies if package.json exists
    for skill in "$SKILLS_DIR"/*; do
        if [ -d "$skill" ] && [ -f "$skill/package.json" ]; then
            echo "   🔹 Installing deps for $(basename "$skill")..."
            cd "$skill" && npm install --silent
        fi
    done
else
    echo "⚠️  Skills directory not found."
fi

# 4. Obsidian Export
if command -v obsidian-cli &> /dev/null; then
    echo "📝 Exporting Master Plan..."
    DEFAULT_VAULT="Obsidian Vault"
    read -p "Enter your Obsidian Vault Name [$DEFAULT_VAULT]: " VAULT_NAME
    VAULT_NAME=${VAULT_NAME:-$DEFAULT_VAULT}
    
    if [ -f "$OPENCLAW_DIR/docs/implementation_plan.md" ]; then
        obsidian-cli create "Inbox/Jarvis Master Plan" --content "$(cat $OPENCLAW_DIR/docs/implementation_plan.md)" --vault "$VAULT_NAME" --overwrite
    fi

    if [ -f "$OPENCLAW_DIR/docs/task.md" ]; then
        obsidian-cli create "Inbox/Jarvis Tasks" --content "$(cat $OPENCLAW_DIR/docs/task.md)" --vault "$VAULT_NAME" --overwrite
    fi
fi

# 5. Install PM2 for Server Mode
if command -v npm &> /dev/null; then
    echo "⚙️  Installing PM2 (Process Manager)..."
    npm install -g pm2
    pm2 startup || true
fi

echo "✅ Standard Install Complete!"
echo ""
echo "🐳 DOCKER MODE (Recommended for Isolation):"
echo "1. Run: ./build_image.sh"
echo "2. Run: docker-compose up -d"
echo ""
echo "🖥️  STANDARD MODE:"
echo "Run: openclaw --profile default"
