---
name: Agent Developer
description: Guidelines and standards for creating and configuring new Agents, Subagents, and Cron Jobs in the OpenClaw ecosystem. MUST follow these rules when user asks to add a new agent, subagent, or cron job.
triggers:
  - create agent
  - new agent
  - add agent
  - add cron
  - new cron job
  - create subagent
---

# Agent Developer Skill

When the user asks you to create a new Agent, Subagent, or Cron Job, you **MUST** follow these guidelines. Failure to do so creates duplicate configs, broken agents, and security risks.

> **Architecture Principle:** Separation of Concerns. Config in JSON, logic in shell scripts, prompts in `/prompts/`.

---

## 1. Creating a New Agent

### Step 1 — Create the system prompt

Save the agent's personality/instructions to:
```
/home/node/.openclaw/prompts/SOUL_<AGENTNAME>.md
```
This maps to the host path: `openclaw-docker/prompts/SOUL_<AGENTNAME>.md`

### Step 2 — Create the agent JSON

Save to `openclaw-docker/core/agents/<agentname>.json`:

```json
{
  "id": "agent_<agentname>",
  "name": "Display Name",
  "description": "One-line description of what the agent does.",
  "model": "litellm/fast",
  "systemPromptPath": "/home/node/.openclaw/prompts/SOUL_<AGENTNAME>.md",
  "contextFiles": [
    "/home/node/.openclaw/prompts/MEMORY.md"
  ],
  "tools": [],
  "temperature": 0.5
}
```

**Model aliases (use these — never hardcode versioned IDs):**
| Alias | Use case |
|---|---|
| `litellm/smart` | Complex reasoning, long tasks |
| `litellm/fast` | Routing, quick replies, light tasks |
| `litellm/thinking` | Deep analysis, DeepSeek R1 |
| `ollama/llama3.2:1b` | Silent background cron jobs |
| `ollama/qwen3:8b` | Nightly jobs needing reasoning |

**Available tools (reference real names):**
- `agent_router` — call the router
- `agent_coder`, `agent_research`, `agent_analyst` — specialist subagents
- `obsidian_search` — semantic Obsidian vault search (RAG)
- `web_search` — SearxNG web search
- `exec` — run bash commands

### Step 3 — Register in openclaw.json

Add to `openclaw-docker/core/openclaw.json` under `agents.list`:

```json
{
  "id": "agent_<agentname>",
  "name": "agent_<agentname>",
  "workspace": "/home/node/.openclaw/workspace",
  "agentDir": "/home/node/.openclaw/agents/<agentname>/agent"
}
```

**Also add the agent as a tool in `router.json` if it should be callable from the Router:**
```json
// In core/agents/router.json, add to "tools" array:
"agent_<agentname>"
```

### Step 4 — Restart openclaw

```bash
docker restart openclaw-latest
```

---

## 2. Creating a Cron Job

### Rules (non-negotiable):

1. **NO BASH IN JSON** — `cron/jobs.json` must NOT contain complex logic
2. **All logic in scripts** — write a `.sh` or `.py` file in `openclaw-docker/scripts/jobs/`
3. **Use env vars** — never hardcode `/data/obsidian`, `/data/bot` etc.

### Step 1 — Write the script

`openclaw-docker/scripts/jobs/<job_name>.sh`:

```bash
#!/bin/bash
# Job description
# Uses: $OBSIDIAN_VAULT_PATH, $BOT_PROJECT_PATH, $TELEGRAM_CHAT_ID

echo "[job-name] Starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ... logic here ...

echo "[job-name] Done"
```

Make executable:
```bash
chmod +x openclaw-docker/scripts/jobs/<job_name>.sh
```

### Step 2 — Add entry to cron/jobs.json

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
    "message": "SILENT TASK. Run the script and output nothing:\nbash: /data/bot/openclaw-docker/scripts/jobs/<job_name>.sh",
    "model": "ollama/llama3.2:1b"
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

**For jobs that should notify Telegram on completion:**
```json
"delivery": {
  "mode": "announce",
  "channel": "last",
  "to": "telegram:6053956251"
}
```

---

## 4. Creating a New Skill

Skills extend what agents know and can do. They are **markdown-only** — no code execution.

> **CRITICAL: JavaScript files (index.mjs, .js) are NOT supported by OpenClaw skills.**
> Skills work ONLY through `SKILL.md` instructions. If you need code execution, write a bash/python script and call it from `SKILL.md`.

### Skill folder structure

```
skills/<skill-name>/
  SKILL.md       ← Required: frontmatter + markdown instructions
  README.md      ← Required for tool-dispatch skills (OpenClaw reads this on invocation)
  scripts/       ← Optional: helper scripts referenced from SKILL.md
```

### SKILL.md format

```markdown
---
name: my_skill
description: "One line. When should agent use this skill."
triggers:
  - trigger phrase one
  - trigger phrase two
---

# Skill Title

Markdown instructions for the agent. Include exact bash commands to run.

## Usage

\`\`\`bash
bash /data/bot/openclaw-docker/scripts/my_script.sh "arg"
\`\`\`
```

### Real tool names (for agent JSON `tools` field)

| Tool | Purpose |
|---|---|
| `exec` | Run shell commands |
| `read` | Read files |
| `write` | Write files |
| `apply_patch` | Apply unified diffs |
| `web_search` | Web search via SearxNG |
| `web_fetch` | Fetch a URL |
| `browser` | Headless browser |
| `cron` | Manage cron jobs |
| `sessions_spawn` | Spawn subagent |

> Skills (`obsidian_search`, `web_search` skill) are injected via SKILL.md into the agent's system prompt — they are NOT listed in the `tools` JSON field.

---

## Checklist before finishing

- [ ] `SOUL_<AGENTNAME>.md` created in `prompts/`
- [ ] `<agentname>.json` created in `core/agents/` with **real tool names** (exec/read/write, not shell.execute/file.read)
- [ ] Agent registered in `core/openclaw.json > agents.list`
- [ ] Agent added to `router.json > tools` (if callable from Router)
- [ ] For cron: script in `scripts/jobs/`, entry in `cron/jobs.json`
- [ ] For skill: `SKILL.md` + `README.md` in `skills/<name>/`, logic in bash script
- [ ] `docker restart openclaw-latest` executed

