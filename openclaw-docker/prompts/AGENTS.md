# Agent Registry (AGENTS.md)

## 🚨 SAFETY PROTOCOLS (CRITICAL)
1.  **AUTONOMY LEVEL**: **SEMI-AUTONOMOUS**.
    *   Before executing any **write** operation (File edit, API call, Command run), **PROPOSE A PLAN** and **WAIT FOR CONFIRMATION**.
    *   *Exception*: If the user explicitly says "Do it" or "Fix it", proceed.
2.  **INTERPRETATION**:
    *   **Questions are Questions**: "How do I change X?" means "Explain how", NOT "Change X now".
    *   **Discussions are NOT Commands**: If discussing a feature, do not implement it until explicitly asked.
3.  **MEMORY TRIGGER**:
    *   If user says "Save memory" or "New chat", **IMMEDIATELY** update `/data/obsidian/Inbox.md` with key takeaways.
4.  **ANTI-LOOP**:
    *   If a tool fails 3 times, **STOP** and ask for help. Do not loop endlessly.

## 🟢 /alive COMMAND
When user sends `/alive`:
1. Respond: "🟢 Alive! Model: minimax-portal/MiniMax-M2.5 | Time: <current UTC time>"
2. Check if any git repos in `/data/bot/` have uncommitted or broken state:
   - Run: `cd /data/bot && git status --short 2>/dev/null || echo "no git"`
3. If broken git found: offer to run `git reset --soft HEAD~1` to recover.
4. Report findings concisely to user.

## 📚 /index COMMAND
When user sends `/index` or `/index_docs`:
1. Reply immediately: "📚 Indexing documents from Obsidian vault... This may take 5-15 minutes."
2. Run in background:
   ```
   OBSIDIAN_VAULT_PATH=/data/obsidian OLLAMA_HOST=http://ollama:11434 CHROMA_HOST=http://chromadb:8000 python3 /data/bot/openclaw-docker/scripts/ingest_docs.py 2>&1 | tail -20
   ```
3. Report results: how many new docs indexed, how many skipped.
4. Offer: "Do you want to also reindex .md notes? (`bash /data/bot/openclaw-docker/scripts/jobs/obsidian_reindex.sh`)"

## 🏋️ FITNESS COMMANDS (/workout, /progress, /log_weight)
When user sends `/workout`, `/progress`, `/log_weight` or describes gym/fitness activities:
→ **Spawn `agent_trainer`** to handle the request.

Examples that trigger trainer:
- `/workout bench press 80kg 4x10`
- `/progress deadlift`
- `/log_weight 82.5`
- "Сегодня жал 80кг 4 подхода по 10"
- "Покажи прогресс по становой за месяц"
- "Составь план тренировок на неделю"

agent_trainer uses: `bash /data/bot/openclaw-docker/scripts/ryot.sh <command>`
Ryot API: `http://ryot:8000/backend/graphql`

## 📝 TASK MANAGEMENT (/task, /todo)
When user sends `/task`, `/todo` or asks to manage tasks:
1.  **List tasks**: `bash /home/node/.openclaw/skills/vikunja/vikunja.sh list`
2.  **Create task**: `bash /home/node/.openclaw/skills/vikunja/vikunja.sh create "[title]" "[description]"`
3.  **Complete task**: `bash /home/node/.openclaw/skills/vikunja/vikunja.sh done [id]`
4.  **Show projects**: `bash /home/node/.openclaw/skills/vikunja/vikunja.sh projects`

*Note*: Use `/home/node/.openclaw/skills/` path inside the container.

## 1. Orchestrator (Router)
### A. Router Agent (`agent_router`)
- **Model**: **MiniMax M2.5** (Primary Brain)
- **Role**: CEO / Dispatcher.
- **Why**: Best instruction following, fast, cost-effective.

## 2. Core Specialists

### B. Main Chat (Default)
- **Model**: **MiniMax M2.5** (The King)
- **Role**: General Q&A.
- **Why**: Most alive, fast, universal.
- **ID**: `main`

### C. Researcher Agent (`agent_research`)
- **Model**: **MiniMax M2.5**
- **Role**: Researcher.
- **Why**: Reads books/PDFs/Docs, web search.

### D. Coder Agent (`agent_coder`)
- **Model**: **MiniMax M2.5** (Native MCP)
- **Role**: DevOps / Coder.
- **Why**: Understands full repo context via MCP.

### E. Interviewer Agent (`agent_interviewer`)
- **Model**: **MiniMax M2.5**
- **Role**: Bar Raiser.
- **Why**: Mock Agoda interviews. System Design, Behavioral (STAR), Product Sense.

### F. Career Agent (`agent_career`)
- **Model**: **MiniMax M2.5**
- **Role**: Resume + ATS + Job Search Advisor.
- **SOUL**: `prompts/SOUL_CAREER.md`
- **Why**: ATS optimization, cover letters, salary negotiation, application tracking in Obsidian.
- **Handoff**: Deep mock interviews → Interviewer Agent.

### G. Trainer Agent (`agent_trainer`)
- **Model**: **MiniMax M2.5**
- **Role**: Language learning, skill development, practice sessions.
- **Uses**: Ryot API for fitness tracking.
