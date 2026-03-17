---
name: find-skills
description: "Search locally installed skills using semantic search (ChromaDB + bot_search.sh). Use when the user asks 'can you do X', 'is there a skill for X', 'what skills do you have', or you need to find a skill before invoking it."
triggers:
  - find skill
  - what skills
  - can you do
  - is there a skill
  - какие скилы
  - найди скил
  - список скилов
  - what can you do
  - какие у тебя возможности
---

# Find Skills — Local Skill Discovery

Searches locally installed skills via ChromaDB semantic index.

## Search by query (recommended)

```bash
bash /data/bot/openclaw-docker/scripts/bot_search.sh "QUERY" --only skills --limit 5
```

Example:
```bash
bash /data/bot/openclaw-docker/scripts/bot_search.sh "web search internet" --only skills --limit 3
bash /data/bot/openclaw-docker/scripts/bot_search.sh "debate decision analysis" --only skills --limit 3
```

## List all indexed skills

```bash
python3 - << 'EOF'
import requests
resp = requests.get("http://chromadb:8000/api/v1/collections/skills", timeout=5)
coll_id = resp.json()["id"]
items = requests.post(
    f"http://chromadb:8000/api/v1/collections/{coll_id}/get",
    json={"include": ["metadatas"]}, timeout=10
).json()
for m in sorted(items.get("metadatas", []), key=lambda x: x.get("name","")):
    print(f"- {m.get('name','?')}")
EOF
```

## Notes

- Skills are indexed nightly at 03:30 Tashkent via cron
- Force reindex: `docker exec openclaw-latest python3 /data/bot/openclaw-docker/scripts/jobs/skills_index.py --force`
- All skills live in `/data/bot/openclaw-docker/skills/<name>/SKILL.md`
- After finding a skill, read its SKILL.md for exact usage commands
