---
name: skill-development
description: "How to create new skills for the OpenClaw ecosystem. Covers SKILL.md format with YAML frontmatter, required file structure, ChromaDB indexing requirements, and how to make skills discoverable by the agent. Use when creating, modifying, or debugging skills."
triggers:
  - create skill
  - new skill
  - skill development
  - add skill
  - make skill
  - index skill
  - skill not found
---

# Skill Development Guide

How to create and register new skills in the OpenClaw ecosystem.

## Quick Start

1. Create folder: `skills/<skill-name>/`
2. Create `SKILL.md` with YAML frontmatter
3. **Index the skill in ChromaDB** (critical — skills won't be found otherwise)

## Required File Structure

```
skills/
└── <skill-name>/
    └── SKILL.md           # Required: skill definition
    └── <script>.py        # Optional: Python implementation
    └── <script>.sh        # Optional: Shell implementation
    └── references/        # Optional: reference materials
```

Example from [`debate/`](openclaw-docker/skills/debate/debate.py:1):

```
skills/debate/
├── SKILL.md              # Skill definition with triggers
└── debate.py             # Python implementation
```

## SKILL.md Format

Every skill MUST have a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-name
description: "Clear description of what this skill does and when to use it"
triggers:
  - keyword1
  - keyword2
  - phrase match
  - another trigger
---

# Skill Title

Detailed documentation here...
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Unique skill identifier (lowercase, hyphens) |
| `description` | ✅ | What the skill does — this is embedded and searched |
| `triggers` | ✅ | List of keywords/phrases that activate this skill |

### Real Examples

From [`debate/SKILL.md`](openclaw-docker/skills/debate/SKILL.md:1):

```yaml
---
name: debate
description: "Multi-agent debate system: two agents (Proposer + Critic) debate a complex topic, then a Moderator synthesizes a final decision. Use for investment decisions, architectural choices, complex tradeoffs, counterfactual analysis. Both agents run in parallel per round. RAG context auto-injected from Obsidian."
triggers:
  - debate
  - дебаты
  - два агента
  - проанализируй с двух сторон
  - взвесь за и против
  - pair analysis
  - counterfactual
---
```

From [`index/SKILL.md`](openclaw-docker/skills/index/SKILL.md:1):

```yaml
---
name: index
description: "Re-index the Obsidian vault into ChromaDB for semantic RAG search. Use after adding many new notes. Also re-runs nightly via cron automatically."
triggers:
  - reindex obsidian
  - rebuild index
  - update obsidian index
  - index vault
---
```

## ⚠️ Critical: Skill Indexing Required

**Skills MUST be indexed in ChromaDB or they will NOT be found by the agent.** The agent uses semantic search over the `skills` collection to find relevant skills based on user queries. If your skill isn't indexed, it effectively doesn't exist.

---

## 📋 WHEN to Index

| Scenario | Action Required |
|----------|-----------------|
| **Created a NEW skill** | ✅ **MUST index** — First time only |
| **Modified SKILL.md** | ✅ **MUST re-index** — Description, triggers, or content changed |
| **Modified skill scripts** | ✅ **MUST re-index** — Script paths or logic changed |
| **Just running/using a skill** | ❌ **NO indexing needed** — Already indexed |

### Quick Check: Do I Need to Index?

Ask yourself: *"Did I create or modify any files in the skill folder?"*
- **Yes** → Index now
- **No, just using it** → Skip indexing

---

## 🚀 HOW to Index

### Option 1: Index a Single Skill (Recommended for Development)

Run this Python script after creating or modifying a skill:

```python
#!/usr/bin/env python3
"""Index a single skill into ChromaDB. Run this after creating/modifying a skill."""

import requests
import sys
from pathlib import Path

# Configuration
CHROMA_HOST = "http://chromadb:8000"
OLLAMA_HOST = "http://host.docker.internal:11434"
SKILL_NAME = "your-skill-name"  # ← CHANGE THIS
SKILL_PATH = f"/data/bot/openclaw-docker/skills/{SKILL_NAME}/SKILL.md"

def index_skill():
    # Read SKILL.md content
    skill_file = Path(SKILL_PATH)
    if not skill_file.exists():
        print(f"❌ Skill file not found: {SKILL_PATH}")
        sys.exit(1)
    
    skill_content = skill_file.read_text()
    
    # Extract frontmatter for embedding text
    lines = skill_content.split('\n')
    in_frontmatter = False
    frontmatter_lines = []
    
    for line in lines:
        if line.strip() == '---':
            in_frontmatter = not in_frontmatter
            if not in_frontmatter:
                break
        elif in_frontmatter:
            frontmatter_lines.append(line)
    
    # Use frontmatter + first 500 chars of content for embedding
    embedding_text = '\n'.join(frontmatter_lines) + '\n' + skill_content[:500]
    
    # Get embedding from Ollama
    print(f"🔄 Getting embedding for skill: {SKILL_NAME}")
    emb_resp = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": embedding_text},
        timeout=30
    )
    emb_resp.raise_for_status()
    embedding = emb_resp.json()["embedding"]
    
    # Get or create skills collection
    coll_resp = requests.post(
        f"{CHROMA_HOST}/api/v1/collections",
        json={"name": "skills", "metadata": {}},
        timeout=10
    )
    
    # Get collection ID
    coll_id = requests.get(
        f"{CHROMA_HOST}/api/v1/collections/skills", timeout=5
    ).json()["id"]
    
    # Upsert (add or update) skill to ChromaDB
    print(f"💾 Saving to ChromaDB...")
    upsert_resp = requests.post(
        f"{CHROMA_HOST}/api/v1/collections/{coll_id}/upsert",
        json={
            "ids": [SKILL_NAME],
            "embeddings": [embedding],
            "metadatas": [{"name": SKILL_NAME, "path": f"skills/{SKILL_NAME}/SKILL.md"}],
            "documents": [skill_content]
        },
        timeout=10
    )
    upsert_resp.raise_for_status()
    
    print(f"✅ Skill '{SKILL_NAME}' indexed successfully!")

if __name__ == "__main__":
    index_skill()
```

**Save and run:**
```bash
# Save the script as index_single_skill.py, then:
python3 index_single_skill.py
```

### Option 2: Quick Command-Line Indexing

For quick indexing without creating a file:

```bash
# Set your skill name
SKILL_NAME="your-skill-name"

# Get skill content and create embedding
python3 << 'EOF'
import requests
import sys

skill_name = "${SKILL_NAME}"
chroma_host = "http://chromadb:8000"
ollama_host = "http://host.docker.internal:11434"

# Read skill file
with open(f"/data/bot/openclaw-docker/skills/{skill_name}/SKILL.md") as f:
    content = f.read()

# Get embedding
emb = requests.post(f"{ollama_host}/api/embeddings",
    json={"model": "nomic-embed-text", "prompt": content[:1000]},
    timeout=30).json()["embedding"]

# Get collection ID
coll_id = requests.get(f"{chroma_host}/api/v1/collections/skills").json()["id"]

# Upsert to ChromaDB
requests.post(f"{chroma_host}/api/v1/collections/{coll_id}/upsert",
    json={"ids": [skill_name], "embeddings": [emb],
          "metadatas": [{"name": skill_name}], "documents": [content]})

print(f"✅ Indexed: {skill_name}")
EOF
```

### Option 3: Re-index All Skills (System Admin)

To re-index the entire skills collection (use with caution):

```bash
# Re-index all skills from the skills directory
python3 << 'EOF'
import requests
import os
from pathlib import Path

CHROMA_HOST = "http://chromadb:8000"
OLLAMA_HOST = "http://host.docker.internal:11434"
SKILLS_DIR = "/data/bot/openclaw-docker/skills"

def index_all_skills():
    skills_path = Path(SKILLS_DIR)
    
    # Get collection ID
    coll_id = requests.get(f"{CHROMA_HOST}/api/v1/collections/skills").json()["id"]
    
    for skill_dir in skills_path.iterdir():
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            skill_name = skill_dir.name
            content = skill_md.read_text()
            
            # Get embedding
            emb = requests.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": content[:1000]},
                timeout=30
            ).json()["embedding"]
            
            # Upsert
            requests.post(
                f"{CHROMA_HOST}/api/v1/collections/{coll_id}/upsert",
                json={
                    "ids": [skill_name],
                    "embeddings": [emb],
                    "metadatas": [{"name": skill_name, "path": f"skills/{skill_name}/SKILL.md"}],
                    "documents": [content]
                }
            )
            print(f"✅ Indexed: {skill_name}")

index_all_skills()
EOF
```

---

## ✅ VERIFY Indexing Worked

### Method 1: Check ChromaDB Collection

```bash
# List all indexed skills
curl -s http://chromadb:8000/api/v1/collections/skills | python3 -m json.tool
```

**Expected output:**
```json
{
    "id": "...",
    "name": "skills",
    "metadata": {}
}
```

### Method 2: Query for Your Specific Skill

```bash
# Check if your skill exists in the collection
SKILL_NAME="your-skill-name"
curl -s "http://chromadb:8000/api/v1/collections/skills/get?ids=${SKILL_NAME}" | python3 -m json.tool
```

**Expected output if found:**
```json
{
    "ids": ["your-skill-name"],
    "documents": ["---\nname: your-skill-name..."],
    "metadatas": [{"name": "your-skill-name", "path": "..."}]
}
```

### Method 3: Semantic Search Test

Test if the skill can be found via semantic search:

```python
import requests

# Search for your skill using a trigger phrase
query = "your trigger phrase here"

# Get embedding for query
emb_resp = requests.post(
    "http://host.docker.internal:11434/api/embeddings",
    json={"model": "nomic-embed-text", "prompt": query},
    timeout=30
)
embedding = emb_resp.json()["embedding"]

# Search ChromaDB
coll_id = requests.get("http://chromadb:8000/api/v1/collections/skills").json()["id"]
search_resp = requests.post(
    f"http://chromadb:8000/api/v1/collections/{coll_id}/query",
    json={
        "query_embeddings": [embedding],
        "n_results": 5
    }
)

results = search_resp.json()
print("Top matches:")
for i, (id, doc) in enumerate(zip(results['ids'][0], results['documents'][0])):
    print(f"  {i+1}. {id}")
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Skill not found in ChromaDB | Re-run indexing script |
| Embedding timeout | Check Ollama is running: `curl http://host.docker.internal:11434/api/tags` |
| ChromaDB connection error | Verify ChromaDB container is healthy: `docker ps \| grep chroma` |
| Skill found but not triggered | Add more trigger keywords to SKILL.md and re-index |

---

## Python Scripts Location

Python scripts go in the same folder as `SKILL.md`:

```
skills/my-skill/
├── SKILL.md
└── my_skill.py          # ← Same directory
```

Reference the script path in SKILL.md:

```markdown
## Usage

```bash
python3 /data/bot/openclaw-docker/skills/my-skill/my_skill.py "argument"
```
```

## Best Practices

### 1. Clear, Actionable Descriptions

The `description` field is used for semantic matching. Make it clear what the skill does and when to use it.

✅ Good: `"Re-index the Obsidian vault into ChromaDB for semantic RAG search. Use after adding many new notes."`

❌ Bad: `"Handles indexing stuff"`

### 2. Comprehensive Triggers

Include multiple trigger phrases users might say:

```yaml
triggers:
  - reindex obsidian
  - rebuild index
  - update obsidian index
  - index vault
  - refresh search index
  - обнови индекс
```

### 3. Document Usage Examples

Always include usage examples in the SKILL.md body:

```markdown
## Usage

```bash
python3 /data/bot/openclaw-docker/skills/debate/debate.py "Topic to debate"
python3 /data/bot/openclaw-docker/skills/debate/debate.py "Invest $10k in crypto?" --rounds 2
```
```

### 4. Reference Real Code

Use relative paths to reference actual code in the codebase:

```markdown
See [`debate.py`](openclaw-docker/skills/debate/debate.py:1) for the implementation.
```

## Testing New Skills

1. **Create the skill files** following the structure above
2. **Index the skill** using [Option 1: Single Skill Indexing](#option-1-index-a-single-skill-recommended-for-development) above
3. **Verify indexing** using [Method 2: Query for Your Skill](#method-2-query-for-your-specific-skill)
4. **Test triggering** — say one of the trigger phrases to the agent
5. **Debug if needed** using the troubleshooting table below

### Quick Test Checklist

- [ ] SKILL.md created with proper YAML frontmatter
- [ ] Skill indexed in ChromaDB (verify with curl)
- [ ] Trigger phrase matches one in `triggers:` list
- [ ] Description clearly describes what the skill does

### Debugging Tips

If the skill isn't being found:

1. **Check ChromaDB has the skill** (see [Verification section](#-verify-indexing-worked)):
   ```bash
   curl -s "http://chromadb:8000/api/v1/collections/skills/get?ids=your-skill-name" | python3 -m json.tool
   ```

2. **Verify the embedding was created successfully** — Check Ollama logs for errors

3. **Check the skill description** is clear and matches likely user queries

4. **Add more trigger keywords** to the `triggers:` list in SKILL.md, then re-index

## Example: Complete New Skill

### Step 1: Create Directory and Files

```bash
mkdir -p openclaw-docker/skills/my-analyzer
```

### Step 2: Create SKILL.md

```markdown
---
name: my-analyzer
description: "Analyze code complexity and provide refactoring suggestions. Use when reviewing code quality, identifying technical debt, or suggesting improvements."
triggers:
  - analyze code
  - code review
  - refactoring suggestions
  - complexity analysis
---

# My Analyzer

Analyzes code and suggests improvements.

## Usage

```bash
python3 /data/bot/openclaw-docker/skills/my-analyzer/analyzer.py /path/to/code
```
```

### Step 3: Create Python Script (if needed)

`skills/my-analyzer/analyzer.py`:

```python
#!/usr/bin/env python3
"""Code analyzer with complexity metrics."""

import argparse
import os
from pathlib import Path

# Follow python-coding standards...
```

### Step 4: Index the Skill

Save the [single skill indexing script](#option-1-index-a-single-skill-recommended-for-development) as `index_my_analyzer.py` and run:

```bash
# Update SKILL_NAME in the script to "my-analyzer", then:
python3 index_my_analyzer.py
```

Or use the [quick command-line indexing](#option-2-quick-command-line-indexing) method.

### Step 5: Verify Indexing

```bash
# Check if your skill is in ChromaDB
curl -s "http://chromadb:8000/api/v1/collections/skills/get?ids=my-analyzer" | python3 -m json.tool
```

### Step 6: Test

Say to the agent: `"analyze this code"` — it should find and use your skill.

## References

- [`debate/SKILL.md`](openclaw-docker/skills/debate/SKILL.md:1) — Complex skill with Python implementation
- [`index/SKILL.md`](openclaw-docker/skills/index/SKILL.md:1) — Simple skill example
- [`obsidian_index.py`](openclaw-docker/scripts/obsidian_index.py:1) — ChromaDB indexing pattern
- [`find-skills/SKILL.md`](openclaw-docker/skills/find-skills/SKILL.md:1) — How skill discovery works
