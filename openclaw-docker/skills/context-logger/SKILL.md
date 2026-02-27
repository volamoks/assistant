---
name: context-logger
description: "Logs daily session context to Obsidian. Extracts key insights from the day's conversations and saves to daily diary."
triggers:
  - /log context
  - save context
  - daily log
---

# Context Logger — Daily Session Diary

Logs key insights from today's sessions to Obsidian diary.

## Steps

1. **Get today's sessions** (last 24h):
   - Use `sessions_list` with `activeMinutes: 1440`
   - Fetch each session's history with `sessions_history`

2. **Extract key insights** using the configured model (gemma-3-27b-it):
   - What tasks were worked on
   - What decisions were made
   - Any errors or learnings
   - Important context for tomorrow

3. **Write to Obsidian** at:
   `/data/obsidian/Inbox/Дневник_YYYY-MM-DD.md`

   Format:
   ```markdown
   # Дневник — YYYY-MM-DD

   ## Ключевые события
   - [event 1]
   - [event 2]

   ## Решения
   - [decision 1]

   ## Инсайты / Выводы
   - [insight 1]

   ## Ошибки / Грабли
   - [error 1]

   ## На завтра
   - [todo]
   ```

4. **Output** brief confirmation:
   ```
   ✅ Записал контекст в Дневник_YYYY-MM-DD.md
   [ctx: ~Xk]
   ```

## Notes

- If no sessions found → write "Сегодня активности не было"
- Keep entries concise but informative
- Use Russian language for the diary
