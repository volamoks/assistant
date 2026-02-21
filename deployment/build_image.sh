#!/bin/bash
set -e

# Usage: ./build_image.sh
# Builds the 'openclaw' docker image from the current directory context.

echo "🐳 Building OpenClaw Docker Image..."

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop for Mac."
    exit 1
fi

# Build
docker build -t openclaw:latest .

echo "✅ Image 'openclaw:latest' built successfully."
echo "👉 Now run: docker-compose up -d"
