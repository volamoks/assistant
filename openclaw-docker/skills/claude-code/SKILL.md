---
name: claude-code
description: "Invoke Claude Code CLI (Anthropic Claude) for complex tasks that require deep reasoning, large context analysis, or architectural decisions beyond Nemotron/MiniMax capabilities. Use sparingly — consumes Claude subscription quota. Best for: multi-file codebase analysis, complex refactoring plans, architecture reviews, hard debugging sessions."
triggers:
  - claude code
  - вызови клода
  - спроси клода
  - claude analyze
  - deep analysis
  - complex architecture
  - hard task claude
  - claude review
---

# Claude Code CLI Skill

Invokes Claude Code CLI (`claude`) as a powerful sub-agent for tasks requiring
deep reasoning or large context. Uses the user's Claude subscription (no API key needed).

---

## When to use (must meet at least one)

- Codebase analysis spanning **5+ files** or **complex interdependencies**
- Architecture decisions with significant **trade-offs and risks**
- Debugging a **hard bug** that Nemotron/MiniMax failed to solve after 2 attempts
- Code review of a **full feature** (not single file)
- Tasks requiring **100k+ token context**

## When NOT to use

- Routine coding tasks → use coder agent (MiniMax)
- Simple research → use researcher agent (Nemotron)
- Config changes → use coder agent directly
- Anything that fits in a single agent turn

---

## Usage

### Basic task
```bash
claude -p "TASK DESCRIPTION" --output-format text
```

### Analyze a file or directory
```bash
claude -p "Analyze this codebase and identify the top 3 architectural risks: $(find /data/bot/openclaw-docker -name '*.py' | head -20 | xargs ls -la)" \
  --output-format text
```

### With file context
```bash
claude -p "$(cat << 'EOF'
Review this code for security issues and performance problems:

$(cat /data/bot/openclaw-docker/skills/crypto_assistant/bybit_read.py)

Be specific, list exact line numbers.
EOF
)" --output-format text
```

### Complex multi-file analysis
```bash
# Pass file contents inline for full context
claude -p "$(echo 'Analyze these files and create a refactoring plan:'; \
  for f in /data/bot/openclaw-docker/core/agents/*.json; do \
    echo "=== $f ==="; cat "$f"; echo; \
  done)" --output-format text
```

---

## Check auth status
```bash
claude auth status
```

If not logged in:
```bash
claude auth login
# Follow the OAuth flow in browser
```

---

## Output formats

| Flag | Use when |
|------|----------|
| `--output-format text` | Default — plain text response |
| `--output-format json` | Structured output needed |
| `--output-format stream-json` | Streaming (not needed for one-shot) |

---

## Limits & best practices

- **One task per call** — don't chain multiple questions in one prompt
- **Be specific** — the more context in the prompt, the better the result
- **Check auth first** — `claude auth status` before running
- **Timeout**: complex analysis can take 60-120s — that's normal
- **Quota**: each call uses your Claude subscription. Use for genuinely hard problems only.

---

## Integration with agent workflow

The main agent or architect should call this skill via `exec` tool:

```
[Agent decides Claude is needed]
→ exec: claude -p "task" --output-format text
→ Receives result
→ Formats and returns to user
```

Do NOT spawn a sub-agent just to run Claude CLI — call it directly with exec.
