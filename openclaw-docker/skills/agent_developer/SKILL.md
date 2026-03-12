---
name: Agent Developer
description: >
  Authoritative guide for creating new Agents, Skills, and Cron Jobs in this OpenClaw instance.
  MUST follow these rules — wrong structure causes crash loops or silent failures.
triggers:
  - create agent
  - new agent
  - add agent
  - add cron
  - new cron job
  - create skill
  - new skill
  - add skill
  - create subagent
---

# Agent Developer Skill

> **Read this fully before starting.** Wrong config = crash loop or agent that never runs.

---

## ⚡ CRITICAL RULES (non-negotiable)

1. **Named agent configs in `openclaw.json` → crash loop.** Never add `systemPromptPath`, `contextFiles`, `tools`, `temperature` to agent entries.
2. **`agents.defaults.models`** — only: `{ "model-id": { "streaming": bool } }`. Nothing else.
3. **`subagents.allowAgents`** — valid ONLY inside `agents.list[].subagents`, NOT in defaults.
4. **`gateway.bind`** — only `"lan"` or `"loopback"`. Nothing else.
5. **Single-file volume mounts → EACCES**. Always mount full directories.

---

## 1. Creating a New Agent

### Step 1 — SOUL file (source template)

Create the agent persona in git:
```
openclaw-docker/prompts/SOUL_<NAME>.md
```

Minimal structure:
```markdown
# SOUL.md — Claw <Name>

You are the **<NAME> AGENT** — [one-line purpose].

---

## Objective

[What this agent does. Be specific.]

## ⚡ File Discovery (MANDATORY)

Before reading files or guessing paths — search first:

\`\`\`bash
bash /data/bot/openclaw-docker/scripts/bot_search.sh "what you need"
# --only skills|prompts|scripts|context|obsidian  |  --limit N
\`\`\`

Returns ranked file paths. Read only what's relevant. **Never `ls skills/` blindly.**

---

## Rules

- [Agent-specific rules]
- See `TOOLS.md` for exact paths, skill commands, and protocols.

*Every response MUST start with `[🦀 Claw/<agentid>]` and end with context estimate `(~Xk)`.*
```

### Step 2 — Agent workspace directory

Create on the **host** (mounted via `./core` → `/home/node/.openclaw`):
```
openclaw-docker/core/workspace-<name>/
  SOUL.md       ← COPY of prompts/SOUL_<NAME>.md (or enhanced version)
  AGENTS.md     ← symlink or copy from core/workspace/AGENTS.md
  TOOLS.md      ← symlink or copy from core/workspace/TOOLS.md
  USER.md       ← symlink or copy from core/workspace/USER.md
  HEARTBEAT.md  ← empty file (agent writes here)
  IDENTITY.md   ← optional, agent-specific identity
```

Fastest way — copy from existing agent and edit SOUL.md:
```bash
cp -r openclaw-docker/core/workspace-analyst/ openclaw-docker/core/workspace-<name>/
# Then edit: core/workspace-<name>/SOUL.md
```

### Step 3 — Register in openclaw.json

Add to `openclaw-docker/core/openclaw.json` under `agents.list`:

```json
{
  "id": "<name>",
  "name": "<name>",
  "workspace": "/home/node/.openclaw/workspace-<name>",
  "agentDir": "/home/node/.openclaw/agents/<name>/agent",
  "model": {
    "primary": "bailian/kimi-k2.5"
  }
}
```

**Model choices:**
| Model | Use case |
|-------|----------|
| `bailian/kimi-k2.5` | Default — fast, capable |
| `bailian/qwen3.5-plus` | Routing, structured tasks |
| `bailian/qwen3-max-2026-01-23` | Analysis, research |
| `ollama/qwen3.5:0.8b` | Silent background cron jobs |
| `ollama/qwen3.5:9b` | Heavier offline tasks |

**To make the agent callable from main:**

In the `main` agent entry, add to `subagents.allowAgents`:
```json
{
  "id": "main",
  "subagents": {
    "allowAgents": ["coder", "researcher", ..., "<name>"]
  }
}
```

### Step 4 — Index the new SOUL file into ChromaDB

```bash
docker exec openclaw-latest python3 /data/bot/openclaw-docker/scripts/jobs/bot_files_index.py --force
```

This ensures `bot_search.sh "what agent handles X"` returns the new agent.

### Step 5 — Restart

```bash
docker restart openclaw-latest
```

---

## 2. Creating a New Skill

Skills are **markdown-only** — the agent reads `SKILL.md` and follows its instructions.

> **CRITICAL: `.js`/`.mjs` files are NOT executed by OpenClaw skills.**
> If you need code execution, write a bash/python script and reference it from `SKILL.md`.

### Step 1 — Create skill folder

```
openclaw-docker/skills/<skill-name>/
  SKILL.md    ← Required: frontmatter + instructions
  scripts/    ← Optional: bash/python scripts called from SKILL.md
```

### Step 2 — SKILL.md format

```markdown
---
name: skill_name
description: "One line. Exactly when the agent should use this skill."
triggers:
  - trigger phrase one
  - trigger phrase two
---

# Skill Title

Instructions for the agent. Use exact bash commands.

## Usage

\`\`\`bash
bash /data/bot/openclaw-docker/skills/<skill-name>/scripts/main.sh "arg"
\`\`\`
```

### Step 3 — Index the new skill into ChromaDB

```bash
docker exec openclaw-latest python3 /data/bot/openclaw-docker/scripts/jobs/skills_index.py --force
```

This ensures `bot_search.sh "X"` returns the skill.

Or wait for nightly cron (03:30 Tashkent).

---

## 3. Creating a Cron Job

### Rules:

1. **NO complex logic in `cron/jobs.json`** — only metadata and a command to run the script
2. **All logic in scripts** — `openclaw-docker/scripts/jobs/<job>.sh` or `.py`
3. **Use env vars** — never hardcode paths

### Step 1 — Write the script

`openclaw-docker/scripts/jobs/<job_name>.sh`:
```bash
#!/bin/bash
# Description of what this does
# Uses: $OBSIDIAN_VAULT_PATH, $BOT_PROJECT_PATH

echo "[job-name] Starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ... logic here ...

echo "[job-name] Done"
```

Make executable: `chmod +x openclaw-docker/scripts/jobs/<job_name>.sh`

### Step 2 — Add to cron/jobs.json

```json
{
  "id": "<unique-job-id>",
  "name": "Human Readable Name",
  "enabled": true,
  "schedule": {
    "kind": "cron",
    "expr": "0 3 * * *",
    "tz": "Asia/Tashkent"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "SILENT TASK. Run script, output nothing:\nbash: /data/bot/openclaw-docker/scripts/jobs/<job_name>.sh",
    "model": "ollama/qwen3.5:0.8b"
  },
  "delivery": {
    "mode": "none"
  },
  "state": {
    "consecutiveErrors": 0
  },
  "updatedAtMs": 0
}
```

**With Telegram notification:**
```json
"delivery": {
  "mode": "announce",
  "channel": "last",
  "to": "telegram:6053956251"
}
```

### Step 3 — Re-index scripts

```bash
docker exec openclaw-latest python3 /data/bot/openclaw-docker/scripts/jobs/bot_files_index.py --force
```

---

## ✅ Full Checklist

### New Agent
- [ ] `prompts/SOUL_<NAME>.md` created with bot_search rule included
- [ ] `core/workspace-<name>/` created with SOUL.md + AGENTS.md + TOOLS.md + USER.md + HEARTBEAT.md
- [ ] Entry added to `core/openclaw.json > agents.list` (minimal: id + workspace + agentDir + model)
- [ ] Added to `main` agent's `subagents.allowAgents` (if callable from router)
- [ ] `bot_files_index.py --force` run to index new SOUL file
- [ ] `docker restart openclaw-latest`

### New Skill
- [ ] `skills/<name>/SKILL.md` created with frontmatter (name + description + triggers)
- [ ] Logic in `skills/<name>/scripts/` (not inline JS)
- [ ] `skills_index.py --force` run to index new skill
- [ ] Skill tested: `bot_search.sh "trigger phrase" --only skills`

### New Cron Job
- [ ] Script in `scripts/jobs/<name>.sh` (chmod +x)
- [ ] Entry in `cron/jobs.json` (no complex bash, just script call)
- [ ] Script re-indexed: `bot_files_index.py --force`
- [ ] Tested manually: `docker exec openclaw-latest bash /data/bot/openclaw-docker/scripts/jobs/<name>.sh`
