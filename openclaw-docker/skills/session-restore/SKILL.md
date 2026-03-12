---
name: session-restore
description: "Restores session context from Obsidian daily diaries after /new. Reads recent Дневник_*.md files and injects key context."
triggers:
  - /restore
  - restore context
  - session restore
  - load context
---

# Session Restore — Cross-Session Context

Restores context from previous sessions by reading Obsidian daily diaries.
Use at session start (after /new) to recover continuity.

## Steps

### 1. Find recent diaries
Search for files matching:
- `/data/obsidian/Inbox/Дневник_YYYY-MM-DD.md`
- `/data/obsidian/vault/Daily/Дневник_YYYY-MM-DD.md`
- `/data/obsidian/vault/Bot/Дневник_YYYY-MM-DD.md`

Get last 1-2 days (today + yesterday if available).

### 2. Read diary content
Use `read` tool to fetch each diary file.

### 3. Extract key context
Parse markdown sections:
- **Ключевые события** → Active tasks/projects
- **Решения** → Decisions to remember
- **Инсайты / Выводы** → Important learnings
- **Ошибки / Грабли** → What to avoid
- **На завтра** → Pending todos

### 4. Present context summary
Output in Russian:

```
[🔄 Контекст восстановлен]

**Активные задачи:**
- [task 1]
- [task 2]

**Важные решения:**
- [decision 1]

**Ждущие задачи (на завтра):**
- [todo 1]

**Контекст:** [brief 1-2 line summary]

---
[ctx: ~Xk]
```

### 5. Optional: Save to session memory
If workspace has `MEMORY.md` or `memory/YYYY-MM-DD.md`, append key context there.

## Edge Cases

- **No diaries found**: "❌ Дневники не найдены — контекст не восстановлен"
- **Empty diaries**: "⚠️ Дневники пустые — нет контекста для восстановления"
- **Old diaries only (>7 days)**: Warn that context may be stale

## Notes

- Keep output concise (max 10-15 lines)
- Use Russian language
- Prioritize recent/active context over historical

## Auto-Run Configuration

**Enabled:**
- ✅ AGENTS.md: Runs at every session start
- ✅ HEARTBEAT.md: Runs on first heartbeat of day
- ✅ Cron: Daily at 05:00 UTC (`8d395650-cb86-4336-b074-7351b01209ba`)

**Manual triggers:** `/restore`, `restore context`, `session restore`, `load context`
