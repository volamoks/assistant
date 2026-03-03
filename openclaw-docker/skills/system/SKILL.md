---
name: terminal
description: "Execute basic shell commands inside the container: list files, read files, run scripts, check environment. For root/sudo operations use the sudo skill instead."
triggers:
  - выполни команду
  - запусти скрипт
  - terminal
  - exec command
  - run command
---

# /terminal — System Command Execution

## When to use
Agent needs to execute basic shell commands inside the container workspace:
- Exploring directories (`ls -la`)
- Reading files (`cat`, `head`, `tail`)
- Running local scripts (`node script.js`, `python script.py`)
- Checking environment (`env`, `pwd`, tool versions)

⚠️ **DO NOT use this for installation or root commands!** If you need `sudo`, `docker restart`, or `apt-get`, use the `/sudo` skill instead!

## Workflow

1. Call bash with the terminal script:
   ```bash
   bash /home/node/.openclaw/skills/system/terminal.sh "<command>"
   ```

2. The script will execute the command safely:
   - It runs as the non-root container user.
   - It has a 60-second execution timeout.
   - It truncates output to 4000 characters to prevent overwhelming your context.

3. Read the output and explain it to the user.

## Examples

### Example 1: Check Python packages
```bash
bash /home/node/.openclaw/skills/system/terminal.sh "pip list | grep requests"
```

### Example 2: Find a file
```bash
bash /home/node/.openclaw/skills/system/terminal.sh "find /home/node/.openclaw -name openclaw.json"
```

### Example 3: View log tail
```bash
bash /home/node/.openclaw/skills/system/terminal.sh "tail -n 20 /tmp/openclaw/openclaw-latest.log"
```

## Error Handling

If the command times out or returns an error code, analyze the stderr/stdout provided in the response and try to fix the command. If a command requires interaction (like answering "y/n"), it will likely timeout. Try to bypass prompts using flags like `-y` or `-f`.
