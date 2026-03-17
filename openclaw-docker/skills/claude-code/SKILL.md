---
name: claude-code
description: "Invoke Claude (full Claude Code on host Mac) for complex tasks requiring deep reasoning, large context analysis, or architectural decisions. Uses claude-bridge HTTP proxy. Use sparingly — consumes Claude subscription quota. Best for: multi-file codebase analysis, hard debugging, architecture reviews."
triggers:
  - claude code
  - вызови клода
  - спроси клода
  - claude analyze
  - deep analysis
  - complex architecture
  - hard task claude
  - claude review
  - claude думай
---

# Claude Code Skill (via Bridge)

Invokes full Claude Code CLI on the host Mac via HTTP bridge at `host.docker.internal:18791`.
Uses the user's Claude subscription — no API key needed.

---

## When to use (must meet at least one)

- Codebase analysis spanning **5+ files** or **complex interdependencies**
- Architecture decisions with significant **trade-offs and risks**
- Debugging a **hard bug** that Nemotron/MiniMax failed after 2 attempts
- Code review of a **full feature** (not a single file)
- Tasks requiring **100k+ token context**
- User explicitly says "спроси клода" / "claude analyze"

## When NOT to use

- Routine coding → coder agent (MiniMax)
- Simple research → researcher (Nemotron)
- Config changes → coder directly
- Anything that fits in a normal agent turn

---

## Usage

### Basic call
```bash
curl -s http://host.docker.internal:18791/claude \
  -H "Authorization: Bearer claude-bridge-local-token" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "YOUR TASK HERE", "timeout": 120}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result'] if d['ok'] else 'ERROR: '+d['error'])"
```

### With file context
```bash
PROMPT=$(python3 -c "
import json, sys
content = open('/data/bot/openclaw-docker/skills/crypto_assistant/bybit_read.py').read()
task = f'''Review this Python file for security issues and bugs:

{content}

List issues with line numbers. Be specific.'''
print(json.dumps({'prompt': task, 'timeout': 120}))
")

curl -s http://host.docker.internal:18791/claude \
  -H "Authorization: Bearer claude-bridge-local-token" \
  -H "Content-Type: application/json" \
  -d "$PROMPT" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('result','ERROR: '+d.get('error','?')))"
```

### Multi-file analysis
```bash
python3 << 'EOF'
import json, subprocess, os

files = {}
for f in ['/data/bot/openclaw-docker/core/openclaw.json',
          '/data/bot/openclaw-docker/litellm/config.yaml']:
    if os.path.exists(f):
        files[f] = open(f).read()[:3000]  # truncate large files

task = "Analyze these config files and identify risks:\n\n"
for path, content in files.items():
    task += f"=== {path} ===\n{content}\n\n"

payload = json.dumps({"prompt": task, "timeout": 120})
result = subprocess.run(
    ['curl', '-s', 'http://host.docker.internal:18791/claude',
     '-H', 'Authorization: Bearer claude-bridge-local-token',
     '-H', 'Content-Type: application/json',
     '-d', payload],
    capture_output=True, text=True, timeout=130
)
d = json.loads(result.stdout)
print(d.get('result', 'ERROR: ' + d.get('error', '?')))
EOF
```

---

## Health check
```bash
curl -s http://host.docker.internal:18791/health
# → {"ok": true, "version": "2.1.47 (Claude Code)"}
```

---

## Optional: specify model
```json
{"prompt": "...", "model": "claude-opus-4-5", "timeout": 180}
```
Default: whatever `claude --print` uses (Sonnet by default).

---

## Limits
- Each call uses Claude subscription quota
- Timeout default: 120s (complex tasks can take 60-90s)
- Bridge runs on Mac port 18791, auto-starts on login
- Log: `tail -f /tmp/claude-bridge.log`
