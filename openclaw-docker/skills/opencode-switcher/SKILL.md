---
name: opencode-switcher
description: "Automatically switch between OpenCode Zen, KiloCode, and Paid MiniMax models when encountering 429 (Rate Limit) or other provider errors."
triggers:
  - 429 error
  - rate limit
  - switch opencode model
  - switch model
---

# /opencode-switcher — Auto-Failover for OpenCode Models

## When to use
Use this skill when you encounter a **429 Too Many Requests**, **503 Service Unavailable**, or **403 Forbidden** error while trying to use `opencode` models or other MiniMax-based models.

The goal is to ensure continuous operation by switching to a different provider (Free Zen, Free Kilo, or Paid).

## Workflow

1. Detect the error in the tool output (e.g., from `opencode run` or `litellm` response).
2. Choose the next provider based on the current state:
   - If **Zen (free)** fails -> Switch to **Kilo (free)**.
   - If **Kilo (free)** fails -> Switch to **Paid**.
   - If **Paid** fails (rare) -> Revert to **Zen** or report to user.
3. Execute the switcher script:
   ```bash
   bash /usr/local/bin/switch_opencode.sh [free|kilo|paid]
   ```
4. Verify the switch by checking the status:
   ```bash
   bash /usr/local/bin/switch_opencode.sh status
   ```
5. Retry your original task.

## Available Modes
- `free`: OpenCode Zen (Free tier).
- `kilo`: KiloCode (Free tier via LiteLLM).
- `paid`: Your primary MiniMax subscription (via LiteLLM).

## Examples

### Example: Switching after 429 Error
**Agent Logic**: "I received a 429 Rate Limit error from OpenCode Zen. I will now switch to KiloCode to continue the task."
**Action**:
```bash
/usr/local/bin/switch_opencode.sh kilo
```
**Verification**:
```bash
/usr/local/bin/switch_opencode.sh status
```
