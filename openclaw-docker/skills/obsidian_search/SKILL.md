---
name: obsidian_search
description: "Semantic search in the local Obsidian vault using OpenViking RAG (hierarchical L0/L1/L2 context). Use when you need user preferences, historical context, past decisions, personal notes, or any knowledge from the vault. Understands meaning — not just keywords."
triggers:
  - search obsidian
  - find in obsidian
  - obsidian search
  - search notes
  - what does the user prefer
  - user context
  - look in vault
  - найди в заметках
  - поищи в обсидиан
  - контекст пользователя
---

# Obsidian Semantic Search (Viking RAG)

Searches the Obsidian vault via OpenViking (hierarchical, 91% token reduction).

## Primary search — Viking (markdown, semantic)

```bash
curl -s http://viking-bridge:8100/api/v1/search/search \
  -X POST -H "Content-Type: application/json" -H "X-API-Key: viking-local-key-12345" \
  -d '{"query": "QUERY HERE", "limit": 5}' \
  | python3 -c "
import json, sys, urllib.request, urllib.parse
data = json.load(sys.stdin)
VIKING='http://viking-bridge:8100'
KEY='viking-local-key-12345'
for r in data['result']['resources']:
    uri = r['uri']
    score = round(r['score'], 3)
    path = uri.replace('viking://resources/obsidian/', '')
    if r.get('level', 0) >= 2:
        req = urllib.request.Request(
            f'{VIKING}/api/v1/content/read?uri={urllib.parse.quote(uri)}',
            headers={'X-API-Key': KEY}
        )
        content = json.loads(urllib.request.urlopen(req, timeout=5).read()).get('result','')
        print(f'\n=== {path} (score: {score}) ===')
        print(content[:600])
    else:
        print(f'\n[dir] {path} (score: {score})')
"
```

## Fallback — ChromaDB (binary docs: PDF, DOCX, XLSX)

```bash
bash /data/bot/openclaw-docker/scripts/obsidian_rag_search.sh "QUERY" 3
```

## Notes

- Viking covers all markdown (4654+ chunks), hierarchical L0/L1/L2 scoring
- ChromaDB fallback covers binary documents (PDF/DOCX/XLSX)
- Force reindex ChromaDB: `bash /data/bot/openclaw-docker/scripts/jobs/obsidian_reindex.sh`
