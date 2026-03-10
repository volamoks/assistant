#!/bin/bash
# find_skill.sh — Semantic skill search using ChromaDB
# Usage: bash find_skill.sh "query"
# Example: bash find_skill.sh "bybit crypto"

set -e

QUERY="$1"
CHROMA_HOST="${CHROMA_HOST:-http://chromadb:8000}"
OLLAMA_HOST="${OLLAMA_HOST:-http://host.docker.internal:11434}"
COLLECTION_NAME="${COLLECTION_NAME:-skills}"
TOP_K="${TOP_K:-3}"

if [ -z "$QUERY" ]; then
  echo "Usage: bash find_skill.sh 'query'"
  echo "Example: bash find_skill.sh 'bybit crypto trading'"
  exit 1
fi

# Check if required tools are available
if ! command -v curl &> /dev/null; then
  echo "Error: curl is required but not installed"
  exit 1
fi

if ! command -v jq &> /dev/null; then
  echo "Error: jq is required but not installed"
  exit 1
fi

echo "🔍 Searching for: '$QUERY'"
echo ""

# Step 1: Get embedding from Ollama
echo "📊 Generating embedding..."
EMBEDDING_RESPONSE=$(curl -s -X POST "${OLLAMA_HOST}/api/embeddings" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"nomic-embed-text\", \"prompt\": \"${QUERY}\"}" 2>/dev/null) || {
  echo "Error: Failed to connect to Ollama at ${OLLAMA_HOST}"
  echo "Make sure Ollama is running and the embedding model is available."
  exit 1
}

# Extract embedding from response
EMBEDDING=$(echo "$EMBEDDING_RESPONSE" | jq -r '.embedding // empty')

if [ -z "$EMBEDDING" ] || [ "$EMBEDDING" = "null" ]; then
  echo "Error: Failed to generate embedding"
  echo "Response: $EMBEDDING_RESPONSE"
  exit 1
fi

# Step 2: Query ChromaDB for similar skills
echo "🔎 Querying ChromaDB..."

# Resolve collection UUID (ChromaDB v0.5+ requires UUID for query endpoint)
COLLECTION_UUID=$(curl -s "${CHROMA_HOST}/api/v1/collections/${COLLECTION_NAME}" 2>/dev/null | jq -r '.id // empty')

if [ -z "$COLLECTION_UUID" ] || [ "$COLLECTION_UUID" = "null" ]; then
  echo "Error: Could not find ChromaDB collection '${COLLECTION_NAME}'"
  echo "Make sure ChromaDB is running and skills are indexed (run skills_index.py)."
  exit 1
fi

# Build the query payload
QUERY_PAYLOAD=$(cat <<EOF
{
  "query_embeddings": [$EMBEDDING],
  "n_results": $TOP_K,
  "include": ["documents", "metadatas", "distances"]
}
EOF
)

SEARCH_RESPONSE=$(curl -s -X POST "${CHROMA_HOST}/api/v1/collections/${COLLECTION_UUID}/query" \
  -H "Content-Type: application/json" \
  -d "$QUERY_PAYLOAD" 2>/dev/null) || {
  echo "Error: Failed to query ChromaDB at ${CHROMA_HOST}"
  echo "Make sure ChromaDB is running and the 'skills' collection exists."
  exit 1
}

# Check if we got results
DOCUMENTS=$(echo "$SEARCH_RESPONSE" | jq -r '.documents[0] // empty')
METADATAS=$(echo "$SEARCH_RESPONSE" | jq -r '.metadatas[0] // empty')
DISTANCES=$(echo "$SEARCH_RESPONSE" | jq -r '.distances[0] // empty')

if [ -z "$DOCUMENTS" ] || [ "$DOCUMENTS" = "null" ] || [ "$DOCUMENTS" = "[]" ]; then
  echo "❌ No skills found matching: '$QUERY'"
  echo ""
  echo "Tips:"
  echo "  • Try broader search terms"
  echo "  • Use different keywords"
  echo "  • Check available skills: ls /home/node/.openclaw/skills/"
  echo "  • Skills may need to be indexed: run the obsidian_index.py script"
  exit 0
fi

# Step 3: Display results
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  FOUND SKILLS (top $TOP_K results)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Parse and display results
COUNT=$(echo "$DOCUMENTS" | jq 'length')

for i in $(seq 0 $(($COUNT - 1))); do
  DOCUMENT=$(echo "$DOCUMENTS" | jq -r ".[$i]")
  METADATA=$(echo "$METADATAS" | jq -r ".[$i]")
  DISTANCE=$(echo "$DISTANCES" | jq -r ".[$i]")

  # Extract metadata fields
  SKILL_NAME=$(echo "$METADATA" | jq -r '.name // "unknown"')
  SKILL_PATH=$(echo "$METADATA" | jq -r '.path // "unknown"')
  SKILL_TRIGGERS=$(echo "$METADATA" | jq -r '.triggers // "[]"')

  # Calculate similarity score (0-100%)
  # ChromaDB returns L2 distance, convert to similarity
  SIMILARITY=$(echo "scale=1; (1 - $DISTANCE) * 100" | bc 2>/dev/null || echo "N/A")

  echo "─────────────────────────────────────────────────────────────"
  echo "  📦 Skill: ${SKILL_NAME}"
  echo "     Match: ${SIMILARITY}%"
  echo ""

  # Display first few lines of the document (description)
  DESCRIPTION=$(echo "$DOCUMENT" | head -20)
  echo "  ${DESCRIPTION}"
  echo ""

  # Display triggers if available
  if [ -n "$SKILL_TRIGGERS" ] && [ "$SKILL_TRIGGERS" != "null" ] && [ "$SKILL_TRIGGERS" != "[]" ]; then
    TRIGGERS_LIST=$(echo "$SKILL_TRIGGERS" | jq -r '.[]' 2>/dev/null | tr '\n' ', ' | sed 's/, $//')
    if [ -n "$TRIGGERS_LIST" ]; then
      echo "  🏷️  Triggers: ${TRIGGERS_LIST}"
    fi
  fi

  echo "  📁 Path: ${SKILL_PATH}"
  echo ""
done

echo "═══════════════════════════════════════════════════════════════"
echo "  To use a skill, reference its SKILL.md file"
echo "═══════════════════════════════════════════════════════════════"
