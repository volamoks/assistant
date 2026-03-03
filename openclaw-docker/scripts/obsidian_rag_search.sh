#!/bin/bash
# obsidian_rag_search.sh — Semantic search in Obsidian vault via ChromaDB RAG
# Usage: obsidian_rag_search.sh "query" [limit]
# Example: obsidian_rag_search.sh "user budget preferences" 3

QUERY="${1:-}"
LIMIT="${2:-3}"
OLLAMA_HOST="${OLLAMA_HOST:-http://host.docker.internal:11434}"
CHROMA_HOST="${CHROMA_HOST:-http://chromadb:8000}"
COLLECTION_ID="32bf82ed-e3df-4120-9fd2-75625a05d140"

if [ -z "$QUERY" ]; then
    echo "Usage: obsidian_rag_search.sh <query> [limit]"
    exit 1
fi

# Step 1: Get embedding from Ollama
EMBEDDING=$(curl -s --max-time 30 "${OLLAMA_HOST}/api/embeddings" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"nomic-embed-text\",\"prompt\":$(echo "$QUERY" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')}" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d['embedding']))")

if [ -z "$EMBEDDING" ] || [ "$EMBEDDING" = "null" ]; then
    echo "Error: Failed to get embedding from Ollama"
    exit 1
fi

# Step 2: Query ChromaDB
RESULTS=$(curl -s --max-time 15 "${CHROMA_HOST}/api/v1/collections/${COLLECTION_ID}/query" \
    -H "Content-Type: application/json" \
    -d "{\"query_embeddings\":[${EMBEDDING}],\"n_results\":${LIMIT}}" \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
docs = data.get('documents', [[]])[0]
metas = data.get('metadatas', [[]])[0]
if not docs:
    print('No results found.')
    sys.exit(0)
for i, (doc, meta) in enumerate(zip(docs, metas)):
    source = meta.get('source', 'Unknown') if meta else 'Unknown'
    print(f'### [{i+1}] {source}')
    print(doc[:800])
    print()
")

echo "🔍 RAG results for: \"$QUERY\""
echo ""
echo "$RESULTS"
