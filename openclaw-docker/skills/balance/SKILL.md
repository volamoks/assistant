---
name: balance
description: "Check MiniMax API usage and remaining credits"
triggers:
  - /balance
  - usage
  - remaining credits
  - check balance
---

# /balance — MiniMax Usage Check

Check remaining API credits for MiniMax coding plan.

## Steps

1. **Check usage** via API:
```bash
curl -s --location 'https://platform.minimax.io/v1/api/openplatform/coding_plan/remains' \
  --header 'Authorization: Bearer sk-api-0dKQ7dvtRETqduqhHeQ-rdk65DyiPd-ZbQ0vuO8Y97pbxFTH0qi97aDNKG_9EdwG15pL_idG0m_qCAFENHFOl9hgkqr19XvXtswxnr2G079z5z78-BFu36g' \
  --header 'accept: application/json, text/plain, */*' \
  --header 'referer: https://platform.minimax.io/user-center/payment/coding-plan' \
  --header 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
```

2. **Format output:**
```
💳 MiniMax Coding Plan

| Model      | Used   | Remaining | Reset in   |
|------------|--------|-----------|------------|
| MiniMax-M2 | 1420   | 80        | ~1h        |
| MiniMax-M2.1| 1419  | 81        | ~1h        |
| MiniMax-M2.5| 1419  | 81        | ~1h        |

Total used: ~1420 / 1500 (95%)
```

3. **If low** (< 20 remaining) → warn: "⚠️ Low credits, consider top-up"

## Notes

- API key is hardcoded in the curl command
- Reset window: ~5 hours
- 1500 requests per window
