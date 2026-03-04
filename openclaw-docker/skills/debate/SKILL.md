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

# Debate Skill

Two-agent structured debate with a Moderator synthesis.

## Usage

```bash
python3 /data/bot/openclaw-docker/skills/debate/debate.py "Topic or question"
python3 /data/bot/openclaw-docker/skills/debate/debate.py "Invest $10k in crypto vs stocks?" --rounds 2
python3 /data/bot/openclaw-docker/skills/debate/debate.py "Microservices vs Monolith?" --model kimi-k2.5
```

## How It Works

1. **Round 1** — Proposer and Critic state positions independently (**parallel**)
2. **Round 2** — Each responds to the other's summarized points (**parallel**)
3. **Moderator** — Evaluates arguments, scores them 1-10, gives final recommendation

**Context optimization:**
- **Round Summarization**: After each round, responses are compressed from ~2000 tokens to ~150 tokens using `qwen3.5-plus` (cheaper/faster model)
- Summaries preserve key arguments while reducing context size for subsequent rounds
- **RAG Injection**: 2 relevant chunks from Obsidian vault are fetched before debates start and injected into both agents' system prompts in Round 1

**Execution Flow:**
- Round 1 runs both agents in parallel (no dependencies)
- Round 2+ uses summarized context from previous round (sequential dependency on summaries)
- Summarization runs in parallel for both agents' responses

## Output

- Latest: `/home/node/.openclaw/workspace-main/skills/debate-agents/debate-output.md`
- Timestamped: `debate-YYYYMMDD-HHMM.md` in the same dir

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        DEBATE SYSTEM                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. RAG FETCH (Pre-debate)                                  │
│     └── Query ChromaDB (obsidian_vault) for 2 chunks        │
│                                                              │
│  2. ROUND 1 (Parallel)                                      │
│     ├── Proposer ──→ Full Response (~300-400 words)         │
│     └── Critic ────→ Full Response (~300-400 words)         │
│         [Both run simultaneously via ThreadPoolExecutor]    │
│                                                              │
│  3. SUMMARIZATION (Parallel)                                │
│     ├── Proposer Response ──→ Summary (~150 tokens)         │
│     └── Critic Response ────→ Summary (~150 tokens)         │
│         [Uses qwen3.5-plus - cheaper/faster model]          │
│                                                              │
│  4. ROUND 2+ (Parallel with context)                        │
│     ├── Proposer ──→ Responds to Critic summary             │
│     └── Critic ────→ Evaluates Proposer summary             │
│         [Uses summarized context from previous round]       │
│                                                              │
│  5. MODERATOR SYNTHESIS                                     │
│     └── Evaluates all rounds, scores 1-10, recommendation   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Configuration

| Component | Endpoint | Environment Variable |
|-----------|----------|---------------------|
| LiteLLM Proxy | `http://litellm-proxy:4000/chat/completions` | `LITELLM_BASE` |
| ChromaDB | `http://chromadb:8000` | `CHROMA_HOST` |
| Ollama (embeddings) | `http://host.docker.internal:11434` | `OLLAMA_HOST` |

### Available Models

- **Main Debate**: `minimax/MiniMax-M2.5` (default)
- **Summarization**: `qwen3.5-plus` (cheap/fast)
- **Alternatives**: `deepseek/deepseek-chat`, `moonshotai/kimi-k2.5:free`
