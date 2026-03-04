---
name: agent-memory
description: "Long-term memory layer for OpenClaw agents using ChromaDB. Store and retrieve facts, preferences, and context across sessions. Use when: remembering user preferences, storing skill state, persisting insights between sessions."
triggers:
  - memory
  - remember
  - сохрани в память
  - запомни
  - вспомни
  - memory get
  - memory store
---

# Agent Memory (mem0-style)

Long-term memory layer for OpenClaw agents using existing ChromaDB infrastructure.

## Usage

### Store a memory
```python
from agent_memory import Memory

m = Memory(collection="crypto")
m.store(
    text="Abror prefers P2P trades below 15% premium",
    metadata={"category": "preference", "source": "user_input"}
)
```

### Retrieve memories
```python
# Search by query
results = m.search("P2P premium", limit=3)

# Get all for a category
results = m.get_by_category("preference")
```

### Use in skills
```python
# In bybit_integration/bybit_read.py
from agent_memory import Memory

mem = Memory(collection="crypto")
context = mem.search("portfolio strategy", limit=2)
# Inject context into LLM prompt
```

## Collections

| Collection | Purpose | Skills Using |
|------------|---------|--------------|
| `crypto` | Crypto preferences, strategies, alerts | bybit_integration, crypto_monitor |
| `finance` | Budget patterns, goals, restrictions | actual-budget, personal-finance |
| `debate` | Past conclusions, reasoning patterns | debate |
| `general` | User preferences, comm style | all skills |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Skills (bybit, crypto, debate...)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ bybit_read  │  │ btc_alert   │  │ debate.py   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────┐           │
│  │   agent-memory/memory.py                    │           │
│  │   - store()                                 │           │
│  │   - search()                                │           │
│  │   - get_by_category()                       │           │
│  └────────────────────┬────────────────────────┘           │
│                       │                                     │
└───────────────────────┼─────────────────────────────────────┘
                        │
                        ▼ HTTP
              ┌──────────────────┐
              │   ChromaDB       │
              │   :8000          │
              │   collection:    │
              │   agent_memories │
              └──────────────────┘
```

## Auto-Update USER.md

When memory contains user fact → optionally update USER.md:

```python
m.store(
    text="New fact about user",
    metadata={"category": "preference", "update_user_md": True}
)
# Automatically appends to /data/obsidian/vault/Bot/USER.md
```

## Implementation Notes

- Uses existing ChromaDB (already running on port 8000)
- Embeddings via Ollama (nomic-embed-text)
- No additional containers needed
- Separate collections per domain for better retrieval