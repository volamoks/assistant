#!/bin/bash
# Start Ollama with Docker access on macOS
# This script starts Ollama listening on all interfaces so Docker can connect

echo "🦙 Starting Ollama for OpenClaw..."
echo "   Models needed: qwen3.5:0.8b, qwen3.5:9b"
echo ""

# Check if Ollama is already running
if pgrep -x "ollama" > /dev/null; then
    echo "⚠️  Ollama is already running. Stopping it first..."
    killall ollama
    sleep 2
fi

# Start Ollama with host binding for Docker access
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_ORIGINS="*"

echo "🚀 Starting Ollama on 0.0.0.0:11434 (accessible from Docker)..."
nohup ollama serve > /tmp/ollama.log 2>&1 &

sleep 3

# Check if started
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama is running!"
    echo ""
    echo "📦 Checking models..."
    
    # Pull required models if not present
    if ! ollama list | grep -q "qwen3.5:0.8b"; then
        echo "   Downloading qwen3.5:0.8b..."
        ollama pull qwen3.5:0.8b
    else
        echo "   ✓ qwen3.5:0.8b already present"
    fi
    
    if ! ollama list | grep -q "qwen3.5:9b"; then
        echo "   Downloading qwen3.5:9b..."
        ollama pull qwen3.5:9b
    else
        echo "   ✓ qwen3.5:9b already present"
    fi
    
    echo ""
    echo "🎉 Ollama is ready for OpenClaw!"
    echo "   Models: local-small (0.8b), local-medium (9b)"
    echo ""
    echo "   Test from Docker:"
    echo "   docker exec litellm-proxy curl http://host.docker.internal:11434/api/tags"
else
    echo "❌ Failed to start Ollama. Check /tmp/ollama.log"
    exit 1
fi
