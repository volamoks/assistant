---
name: alive
description: "Owner-only diagnostic. Reports bot health: container status, active model, last heartbeat, and any recent errors."
triggers:
  - /alive
  - bot alive
  - is the bot alive
  - bot health
---

# /alive — Bot Health Check

Owner-only status command. Perform a quick system health check and report back.

## Steps

1. **Container status:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}" | grep -E "openclaw|litellm|chromadb|searxng"
```

2. **Recent errors:**
```bash
docker logs openclaw-latest --tail 50 2>&1 | grep -iE "error|crash|SIGTERM|restart" | tail -5
```

3. **ChromaDB RAG status:**
```bash
curl -s http://chromadb:8000/api/v1/collections/32bf82ed-e3df-4120-9fd2-75625a05d140/count
```

4. **Summarize** in this format:

```
🟢 Bot is alive (or 🔴 issues detected)

Containers: <status of each>
Recent errors: <none / or list last 2-3>
RAG index: <N> chunks in ChromaDB
[ctx: ~Xk]
```

## Owner-Only

If invoked from a group chat or by someone other than the owner, refuse: "This command is owner-only."

