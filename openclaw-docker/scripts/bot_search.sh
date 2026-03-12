#!/bin/bash
# bot_search.sh — Unified semantic search across bot's own knowledge base.
#
# Searches: skills | bot_files (prompts + context + scripts) | obsidian_vault
# Returns: collection, type, name, path, relevance score, snippet
#
# Usage:
#   bash /data/bot/openclaw-docker/scripts/bot_search.sh "query"
#   bash /data/bot/openclaw-docker/scripts/bot_search.sh "query" --limit 3
#   bash /data/bot/openclaw-docker/scripts/bot_search.sh "query" --only skills
#   bash /data/bot/openclaw-docker/scripts/bot_search.sh "query" --only prompts
#   bash /data/bot/openclaw-docker/scripts/bot_search.sh "query" --only scripts
#   bash /data/bot/openclaw-docker/scripts/bot_search.sh "query" --only context
#   bash /data/bot/openclaw-docker/scripts/bot_search.sh "query" --only obsidian
#
# Examples:
#   bot_search.sh "finance monthly report"
#   bot_search.sh "obsidian sync notes"
#   bot_search.sh "reindex chromadb embeddings" --only scripts
#   bot_search.sh "crypto trading bybit" --limit 5

set -euo pipefail

QUERY="${1:-}"
CHROMA_HOST="${CHROMA_HOST:-http://chromadb:8000}"
EMBED_SH="${EMBED_SH:-/data/bot/openclaw-docker/scripts/embed.sh}"
LIMIT=3
ONLY=""

shift 2>/dev/null || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --limit|-n) LIMIT="${2:-3}"; shift 2 ;;
    --only)     ONLY="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done

if [ -z "$QUERY" ]; then
  cat <<'EOF'
Usage: bot_search.sh "query" [--limit N] [--only skills|prompts|scripts|context|obsidian]

Searches across:
  skills    — SKILL.md files (what can the bot do)
  prompts   — SOUL_*.md agent personas (which persona handles X)
  scripts   — automation scripts in scripts/
  context   — workspace docs: AGENTS.md, IDENTITY.md
  obsidian  — Obsidian vault notes (user context, preferences, history)

Examples:
  bot_search.sh "finance monthly report"
  bot_search.sh "telegram notification" --only skills
  bot_search.sh "user crypto preferences" --only obsidian
  bot_search.sh "reindex embeddings" --only scripts
EOF
  exit 1
fi

# ─── Get embedding via embed.sh (LiteLLM primary, Ollama fallback) ───────────
EMBEDDING=$(bash "$EMBED_SH" "$QUERY" 2>/dev/null) || true

if [ -z "$EMBEDDING" ] || [ "$EMBEDDING" = "null" ]; then
  echo "ERROR: Embedding failed. Check embed.sh and LiteLLM/Ollama status."
  exit 1
fi

# ─── Query collection (direct interpolation, type filtered in Python) ─────────
query_collection() {
  local COL_NAME="$1"
  local COL_LABEL="$2"
  local N_RESULTS="$3"
  local TYPE_FILTER="$4"  # empty = no filter, else filter post-query in Python

  # Fetch more candidates so keyword boost has enough to work with
  local FETCH=$(( N_RESULTS * 5 ))
  [ "$FETCH" -lt 15 ] && FETCH=15

  # Get collection UUID by name
  local COL_UUID
  COL_UUID=$(curl -sf --max-time 10 "${CHROMA_HOST}/api/v1/collections/${COL_NAME}" 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null) || return 0

  if [ -z "$COL_UUID" ]; then
    return 0
  fi

  # Query ChromaDB — direct embedding interpolation (same approach as obsidian_rag_search.sh)
  local RESP
  RESP=$(curl -sf --max-time 15 \
    -H "Content-Type: application/json" \
    -d "{\"query_embeddings\":[${EMBEDDING}],\"n_results\":${FETCH},\"include\":[\"documents\",\"metadatas\",\"distances\"]}" \
    "${CHROMA_HOST}/api/v1/collections/${COL_UUID}/query" 2>/dev/null) || return 0

  # Parse and display results (post-filter by type in Python)
  echo "$RESP" | python3 -c "
import json, sys

label = '$COL_LABEL'
type_filter = '$TYPE_FILTER'
max_show = $N_RESULTS
query_raw = '''$QUERY'''

# Keyword tokens for boosting (words 3+ chars)
q_tokens = [w.lower() for w in query_raw.split() if len(w) >= 3]

data = json.load(sys.stdin)
docs  = (data.get('documents')  or [[]])[0]
metas = (data.get('metadatas')  or [[]])[0]
dists = (data.get('distances')  or [[]])[0]

# Collect non-hash items first (for relative scoring)
items = []
for doc, meta, dist in zip(docs, metas, dists):
    if not isinstance(meta, dict):
        continue
    if meta.get('type') == 'hash':
        continue
    ftype = meta.get('type', '')
    if type_filter and ftype != type_filter:
        continue
    items.append((doc, meta, dist, ftype))

# Relative score: best result = 95%, linearly scaled
min_d = items[0][2] if items else 1
max_d = max(items[-1][2], min_d + 1) if items else 2

# Compute scores + keyword boost, then re-sort
scored = []
for doc, meta, dist, ftype in items:
    score = round(95 - ((dist - min_d) / (max_d - min_d)) * 40) if max_d > min_d else 95
    score = max(10, min(95, score))

    name  = meta.get('name', '?')
    path  = meta.get('path', meta.get('source', ''))
    desc  = meta.get('description', '')
    role  = meta.get('role', '')

    # Keyword boost: token match in name/path/description → +20 pts (re-ranks proper nouns)
    haystack = (name + ' ' + path + ' ' + desc + ' ' + role).lower()
    for tok in q_tokens:
        if tok in haystack:
            score = min(99, score + 20)
            break

    # Snippet
    lines = [l.strip() for l in doc.split('\n') if l.strip()]
    snippet = ''
    for l in lines[1:4]:
        if not l.startswith('[marker]') and len(l) > 10:
            snippet = l[:160]
            break

    scored.append((score, name, path, desc, role, ftype, snippet))

# Sort by final score descending, show top max_show
scored.sort(key=lambda x: -x[0])
for score, name, path, desc, role, ftype, snippet in scored[:max_show]:
    display_type = ftype or label
    print(f'[{display_type}] {name}  score={score}%')
    extra = role or desc
    if extra:
        print(f'  {extra[:110]}')
    if path:
        print(f'  path: {path}')
    if snippet:
        print(f'  > {snippet}')
    print()
" 2>/dev/null
}

# ─── Run searches ─────────────────────────────────────────────────────────────
echo "🔍 bot_search: \"${QUERY}\""
echo "────────────────────────────────────────────────────────"

case "$ONLY" in
  skills)
    query_collection "skills" "skill" "$LIMIT" ""
    ;;
  prompts)
    query_collection "bot_files" "bot_files" "$LIMIT" "prompt"
    ;;
  scripts)
    query_collection "bot_files" "bot_files" "$LIMIT" "script"
    ;;
  context)
    query_collection "bot_files" "bot_files" "$LIMIT" "context"
    ;;
  obsidian)
    query_collection "obsidian_vault" "obsidian" "$LIMIT" ""
    ;;
  "")
    EACH=$(( (LIMIT + 1) / 2 ))
    [ "$EACH" -lt 2 ] && EACH=2
    query_collection "skills"         "skill"    "$EACH" ""
    query_collection "bot_files"      "bot_files" "$EACH" "prompt"
    query_collection "bot_files"      "bot_files" "$EACH" "context"
    query_collection "bot_files"      "bot_files" "$EACH" "script"
    query_collection "obsidian_vault" "obsidian"  "$EACH" ""
    ;;
  *)
    echo "Unknown --only value: $ONLY. Use: skills|prompts|scripts|context|obsidian"
    exit 1
    ;;
esac

echo "────────────────────────────────────────────────────────"
echo "Tip: 'read path/to/file' to load only relevant content."
