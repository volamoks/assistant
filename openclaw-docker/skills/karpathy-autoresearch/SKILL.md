---
name: karpathy-autoresearch
description: "Autonomous self-improvement cycle for OpenClaw agents. Analyzes session logs, identifies success/failure patterns, generates hypotheses for improvement, tests them via A/B experiments, and applies successful changes. Inspired by Andrej Karpathy's autoresearch concept."
triggers:
  - autoresearch
  - karpathy
  - самоулучшение
  - self-improvement
  - analyze my performance
  - agent research
  - улучши себя
  - запусти autoresearch
---

# Karpathy Autoresearch 🔄

**Autonomous self-improvement cycle for OpenClaw agents.**

Inspired by Andrej Karpathy's concept: agents that analyze their own performance, learn from patterns, and continuously improve without human intervention.

## Concept

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Analyze    │───→│   Generate  │───→│    Test     │───→│    Apply    │───→│   Report    │
│    Logs     │    │ Hypotheses  │    │   A/B Test  │    │  Changes    │    │  Results    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Components

| Component | Script | Purpose | Priority |
|-----------|--------|---------|----------|
| **Log Analyzer** | `analyzer.py` | Reads session logs, extracts patterns | P0 |
| **Hypothesis Generator** | `hypothesis.py` | Generates improvement ideas | P0 |
| **A/B Tester** | `tester.py` | Tests hypotheses via simulation (legacy) | P0 |
| **A/B Test Harness** | `test_harness.py` | Tests hypotheses on real session data | P0 |
| **Change Applier** | `applier.py` | Applies successful changes | P0 |
| **Reporter** | `reporter.py` | Sends Telegram reports | P0 |
| **RAG Integration** | `rag_integration.py` | ChromaDB + obsidian search for context | P1 |
| **Prompt Patch** | `prompt_patch.py` | Apply changes to SKILL.md with validation | P1 |
| **Feedback Loop** | `feedback_loop.py` | Track patch effectiveness over time | P1 |

## Usage

### Manual Run

```bash
# Full autoresearch cycle (uses real A/B test harness by default)
python3 ~/.openclaw/skills/karpathy-autoresearch/run.py

# Full cycle with legacy simulation-based tester
python3 ~/.openclaw/skills/karpathy-autoresearch/run.py --use-simulation

# Individual components
python3 ~/.openclaw/skills/karpathy-autoresearch/analyzer.py --days 7
python3 ~/.openclaw/skills/karpathy-autoresearch/hypothesis.py --patterns-file /tmp/patterns.json
python3 ~/.openclaw/skills/karpathy-autoresearch/test_harness.py --hypotheses-file /tmp/hypotheses.json
python3 ~/.openclaw/skills/karpathy-autoresearch/tester.py --hypotheses-file /tmp/hypotheses.json
python3 ~/.openclaw/skills/karpathy-autoresearch/applier.py --test-results /tmp/test_results.json
```

### Cron Schedule

Runs daily at 02:00 UTC (07:00 Tashkent) — night mode for extended analysis.

## Configuration

Edit `~/.openclaw/skills/karpathy-autoresearch/config.yaml`:

```yaml
# Analysis settings
analysis:
  days_back: 7                    # How many days of logs to analyze
  min_sessions: 3                 # Minimum sessions to analyze
  error_patterns:
    - "error"
    - "failed"
    - "timeout"
    - "❌"
  success_patterns:
    - "✅"
    - "success"
    - "completed"

# Hypothesis generation
hypothesis:
  max_hypotheses: 5               # Max hypotheses to generate
  min_confidence: 0.6             # Minimum confidence threshold
  categories:
    - prompt_improvement
    - tool_optimization
    - workflow_enhancement

# A/B Testing
testing:
  iterations: 5                   # Test iterations per hypothesis
  success_threshold: 0.8          # 80% success rate to apply
  test_timeout: 60                # Seconds per test iteration
  use_real_harness: true          # Use real A/B test harness (not simulation)
  min_samples: 10                 # Minimum sessions per group for real tests

# Application
application:
  backup_before_apply: true
  auto_apply: false               # Require manual approval
  max_changes_per_run: 3

# Reporting
reporting:
  telegram: true
  chat_id: "${TELEGRAM_CHAT_ID}"
  include_raw_logs: false
```

## Output Files

| File | Location | Content |
|------|----------|---------|
| Patterns | `/tmp/karpathy_patterns.json` | Extracted success/failure patterns |
| Hypotheses | `/tmp/karpathy_hypotheses.json` | Generated improvement hypotheses |
| Test Results | `/tmp/karpathy_test_results.json` | A/B test outcomes |
| Applied Changes | `~/.openclaw/skills/karpathy-autoresearch/applied_changes.yaml` | History of changes |

## How It Works

### 1. Log Analysis (`analyzer.py`)

- Reads `memory/YYYY-MM-DD.md` files for the last N days
- Uses `sessions_list` and `sessions_history` for detailed session data
- Extracts:
  - Error patterns (timeouts, failures, exceptions)
  - Success patterns (completions, optimizations)
  - Tool usage statistics
  - Response time metrics

### 2. Hypothesis Generation (`hypothesis.py`)

- Analyzes patterns using LLM
- Generates specific, testable hypotheses:
  - "Adding timeout to X tool reduces failures by Y%"
  - "Reordering prompts improves Z metric"
  - "New pattern for A reduces token usage"

### 3. A/B Testing (`tester.py` / `test_harness.py`)

Two options available:

#### Legacy: Simulation-based (`tester.py`)
- Creates control (current) and variant (hypothesis) versions
- Uses simulated metrics (not real data)
- Runs 5-50 iterations depending on mode
- Measures:
  - Success rate
  - Response time
  - Token usage
  - Error rate

#### NEW: Real A/B Testing (`test_harness.py`)
- Loads actual sessions from memory files
- Extracts real metrics: success rate, latency, tokens
- Runs statistical tests with p-values
- Compares control vs variant groups
- More accurate but requires sufficient session data

### 4. Change Application (`applier.py`)

- For hypotheses with >80% success rate:
  - Backs up original files
  - Applies changes to skills/prompts
  - Records change in history
- Requires manual approval if `auto_apply: false`

### 5. Reporting (`reporter.py`)

- Sends Telegram summary:
  - Patterns found
  - Hypotheses generated
  - Tests run
  - Changes applied
  - Recommendations

### 6. RAG Integration (`rag_integration.py`) — P1

**ChromaDB and Obsidian search integration for semantic context.**

- Connects to ChromaDB for semantic search of past sessions
- Uses `sessions_history` for historical context
- Searches Obsidian FTS5 index for similar patterns
- Builds RAG context for hypothesis generation
- Indexes sessions for future semantic search

```bash
# Search for similar patterns
python3 rag_integration.py --query "timeout error" --category coding

# Index sessions to ChromaDB
python3 rag_integration.py --index-sessions --days 14
```

### 7. Prompt Patch (`prompt_patch.py`) — P1

**Apply changes to SKILL.md with validation and backups.**

- Creates timestamped backups before any changes
- Validates YAML/markdown syntax after changes
- Supports multiple patch types:
  - `append` — Add content to sections
  - `replace` — Replace section content
  - `add_tool` — Add new tool definitions
  - `improve_prompt` — Update prompt sections
- Full rollback capability
- Records all applied patches

```bash
# Apply a patch
python3 prompt_patch.py --file /path/to/SKILL.md --hypothesis '{"id": "hyp_001", "proposed_change": "...", "change_type": "append"}'

# Validate file syntax
python3 prompt_patch.py --validate /path/to/SKILL.md

# Rollback a patch
python3 prompt_patch.py --rollback patch_20260310_120000

# List applied patches
python3 prompt_patch.py --list-patches
```

### 8. Feedback Loop (`feedback_loop.py`) — P1

**Track effectiveness of applied patches over time.**

- Compares metrics BEFORE and AFTER patch application:
  - Success rate
  - Latency
  - Token usage
  - Error rate
- Calculates statistical deltas
- Determines verdict: improved / degraded / neutral / insufficient_data
- Logs all feedback for analysis
- Provides recommendations: keep / rollback / investigate

```bash
# Take current metrics snapshot
python3 feedback_loop.py --snapshot --days 7

# Analyze a specific patch
python3 feedback_loop.py --patch-id patch_001 --file /path/to/SKILL.md --timestamp 2026-03-01T00:00:00

# Analyze all patches
python3 feedback_loop.py --analyze-all

# View feedback history
python3 feedback_loop.py --history
```

## Safety Guardrails

1. **Backup First** — All changes backed up before application
2. **Threshold-Based** — Only changes with >80% success rate applied
3. **Manual Override** — `auto_apply: false` by default
4. **Change Limit** — Max 3 changes per run to prevent cascade failures
5. **Rollback Ready** — Applied changes tracked with full rollback capability

## References

- [Karpathy's Autoresearch Concept](https://karpathy.ai)
- [`analyzer.py`](karpathy-autoresearch/analyzer.py) — Log analysis implementation
- [`hypothesis.py`](karpathy-autoresearch/hypothesis.py) — Hypothesis generation
- [`tester.py`](karpathy-autoresearch/tester.py) — A/B testing framework (simulation-based)
- [`test_harness.py`](karpathy-autoresearch/test_harness.py) — Real A/B testing harness
- [`applier.py`](karpathy-autoresearch/applier.py) — Change application
- [`reporter.py`](karpathy-autoresearch/reporter.py) — Telegram reporting
