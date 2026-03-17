---
name: session-restore
description: "Restores session context from Obsidian after /new. Reads recent memory files and injects key context."
triggers:
  - /restore
  - restore context
  - session restore
  - load context
---

# Session Restore — Cross-Session Context

Restores context from previous sessions by reading Obsidian daily memories.
Use at session start (after /new) to recover continuity.

## Steps

### 1. Find recent memory files
Search for files matching:
- `/data/obsidian/Claw/Memory/YYYY-MM-DD.md`
- `/data/obsidian/Claw/Bot/AgentMemory/**/*.md`

Get last 2-3 days (today + yesterday + day before if available).

### 2. Read memory content
Use `read` tool to fetch each memory file.

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
If workspace has `MEMORY.md` or memory files, append key context there.

## Edge Cases

- **No memories found**: "❌ Память не найдена — контекст не восстановлен"
- **Empty memories**: "⚠️ Память пустая — нет контекста для восстановления"
- **Old memories only (>7 days)**: Warn that context may be stale

## Notes

- Keep output concise (max 10-15 lines)
- Use Russian language
- Prioritize recent/active context over historical

## Auto-Run Configuration

**Enabled:**
- ✅ AGENTS.md: Runs at every session start
- ✅ HEARTBEAT.md: Runs on first heartbeat of day

**Manual triggers:** `/restore`, `restore context`, `session restore`, `load context`
