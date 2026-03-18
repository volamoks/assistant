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

## Bootstrap Budget Rules (CRITICAL)

Every agent workspace has hard limits:
- **Per file**: max **5,000 chars** (file gets truncated if over)
- **Total workspace**: max **10,000 chars** (excess files ignored)

**SOUL.md design rules:**
- Keep SOUL.md under 4,000 chars — role, paths, key directives only
- Move detailed content (workflows, formulas, checklists, reference tables) → `vault/Agents/<Name>/`
- clawvault will surface vault files automatically when relevant (semantic search, up to 4 results)
- **Never leave generated output files in workspace** — agents must save work to vault or /tmp, not workspace

**What to put in vault vs SOUL.md:**

| In SOUL.md | In vault/Agents/<Name>/ |
|------------|------------------------|
| Role definition (1 para) | Step-by-step workflows |
| Key file paths | Detailed checklists |
| Tools list | Response format templates |
| Critical directives | Domain knowledge tables |
| Pointers to vault files | Evaluation criteria |

---

## 1. Creating a New Agent

### Step 1 — SOUL file

Create `openclaw-docker/core/workspace-<name>/SOUL.md`:

```markdown
# SOUL.md — Claw <Name>

You are the **<NAME> AGENT** — [one-line purpose].

## Role

[2-3 sentences max. What it does, for whom, in what context.]

Detailed playbooks in vault — clawvault will surface automatically:
- `vault/Agents/<Name>/<topic>.md`

## Key Paths

[Only paths the agent uses constantly]

## Tools

- [tool]: [when to use]

*CRITICAL: Every response MUST start with `[🦀 Claw/<id>]` and end with `(~Xk)`.*

## ⚡ File Discovery (MANDATORY)

\`\`\`bash
bash /data/bot/openclaw-docker/scripts/bot_search.sh "what you need"
\`\`\`
```

### Step 2 — Vault detail files

Create `vault/Agents/<Name>/` with reference files (workflows, domain knowledge):

```
vault/Agents/<Name>/
  <topic>-workflow.md      ← step-by-step processes
  <topic>-reference.md     ← domain knowledge, tables, formulas
```

These are surfaced by clawvault when relevant — no bootstrap cost.

### Step 3 — Workspace directory

```bash
cp -r openclaw-docker/core/workspace-analyst/ openclaw-docker/core/workspace-<name>/
# Then replace SOUL.md. Delete BOOTSTRAP.md (only keep for genuinely new first-run agents).
# Check total: wc -c core/workspace-<name>/*.md | tail -1  → must be < 10000
```

Files to keep: `SOUL.md`, `TOOLS.md`, `AGENTS.md`, `USER.md`, `MEMORY.md`, `IDENTITY.md`, `HEARTBEAT.md`

### Step 4 — Register in openclaw.json

Add to `openclaw-docker/core/openclaw.json` under `agents.list`:

```json
{
  "id": "<name>",
  "name": "<name>",
  "workspace": "/home/node/.openclaw/workspace-<name>",
  "agentDir": "/home/node/.openclaw/agents/<name>/agent",
  "model": {
    "primary": "litellm/claw-main"
  }
}
```

**Model choices (all go through litellm proxy at `litellm:4000`):**

| Alias | Use case |
|-------|----------|
| `litellm/claw-main` | Default — premium MiniMax M2.5 |
| `litellm/claw-coder` | Code tasks |
| `litellm/claw-researcher` | Research + web search |
| `litellm/claw-architect` | Architecture decisions |
| `litellm/claw-free-smart` | Free quota, smart tasks |
| `litellm/local-small` | Silent cron jobs (qwen2.5-coder:3b) |
| `litellm/local-medium` | Heavier offline tasks (qwen3.5:9b) |

**To make agent callable from main**, add to `main` entry's `subagents.allowAgents`:
```json
{ "id": "main", "subagents": { "allowAgents": ["coder", "researcher", ..., "<name>"] } }
```

### Step 5 — Index and restart

```bash
docker exec openclaw-latest python3 /data/bot/openclaw-docker/scripts/jobs/bot_files_index.py --force
docker restart openclaw-latest
```

### Step 6 — Verify bootstrap budget

```bash
wc -c /data/bot/openclaw-docker/core/workspace-<name>/*.md | sort -rn
# Total must be < 10000, no file > 5000
```

---

## 2. Creating a New Skill

Skills are **markdown-only** — the agent reads `SKILL.md` and follows its instructions.

> **CRITICAL: `.js`/`.mjs` files are NOT executed by OpenClaw skills.**
> Use bash/python scripts referenced from `SKILL.md`.

### Step 1 — Create skill folder

```
openclaw-docker/skills/<skill-name>/
  SKILL.md        ← Required: frontmatter + instructions
  scripts/        ← Optional: bash/python scripts
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

Instructions for the agent.

## Usage

\`\`\`bash
bash /data/bot/openclaw-docker/skills/<skill-name>/scripts/main.sh "arg"
\`\`\`
```

### Step 3 — Index

```bash
docker exec openclaw-latest python3 /data/bot/openclaw-docker/scripts/jobs/skills_index.py --force
# Or wait for nightly cron (03:30 Tashkent)
```

---

## 3. Creating a Cron Job

### Rules:
1. **NO complex logic in `cron/jobs.json`** — only metadata + command
2. **All logic in scripts** — `scripts/jobs/<job>.sh` or `.py`
3. **Use `kind: agentTurn`** (not `systemEvent`) — systemEvent only works on `main` agent

### Step 1 — Write the script

`openclaw-docker/scripts/jobs/<job_name>.sh`:
```bash
#!/bin/bash
echo "[job-name] Starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
# ... logic here ...
echo "[job-name] Done"
```
```bash
chmod +x openclaw-docker/scripts/jobs/<job_name>.sh
```

### Step 2 — Add to cron/jobs.json

```json
{
  "id": "<unique-job-id>",
  "name": "Human Readable Name",
  "enabled": true,
  "agentId": "main",
  "schedule": {
    "kind": "cron",
    "expr": "0 3 * * *",
    "tz": "Asia/Tashkent"
  },
  "sessionTarget": "isolated",
  "wakeMode": "now",
  "payload": {
    "kind": "agentTurn",
    "message": "SILENT. bash: /data/bot/openclaw-docker/scripts/jobs/<job_name>.sh",
    "model": "litellm/local-small",
    "timeoutSeconds": 120
  },
  "delivery": {
    "mode": "none"
  },
  "state": { "consecutiveErrors": 0 },
  "updatedAtMs": 0
}
```

**With Telegram notification:**
```json
"delivery": { "mode": "announce", "channel": "telegram", "to": "telegram:6053956251" }
```

### Step 3 — Re-index

```bash
docker exec openclaw-latest python3 /data/bot/openclaw-docker/scripts/jobs/bot_files_index.py --force
```

---

## ✅ Full Checklist

### New Agent
- [ ] `core/workspace-<name>/SOUL.md` — minimal: role + paths + vault pointers + directives
- [ ] `vault/Agents/<Name>/` — detail files (workflows, domain knowledge)
- [ ] Other workspace files: TOOLS.md, AGENTS.md, USER.md, MEMORY.md, IDENTITY.md, HEARTBEAT.md
- [ ] Bootstrap budget: `wc -c core/workspace-<name>/*.md` → total < 10000, no file > 5000
- [ ] Entry in `core/openclaw.json > agents.list` (id + workspace + agentDir + model only)
- [ ] Added to `main` agent's `subagents.allowAgents` (if callable from router)
- [ ] `bot_files_index.py --force` + `docker restart openclaw-latest`

### New Skill
- [ ] `skills/<name>/SKILL.md` with frontmatter (name + description + triggers)
- [ ] Logic in `skills/<name>/scripts/` (not inline JS)
- [ ] `skills_index.py --force`
- [ ] Test: `bot_search.sh "trigger phrase" --only skills`

### New Cron Job
- [ ] Script in `scripts/jobs/<name>.sh` (chmod +x)
- [ ] Entry in `cron/jobs.json` — `kind: agentTurn`, `agentId: main` or known agent
- [ ] `bot_files_index.py --force`
- [ ] Test: `docker exec openclaw-latest bash /data/bot/openclaw-docker/scripts/jobs/<name>.sh`
