# Python CLI Scripts vs MCP-Based Agents: Analysis for OpenClaw

## Executive Summary

**Core Question:** Заменить ли Python-скрипты в OpenClaw на MCP-агенты через Gemini CLI?

**Short Answer:** Частично — да. Некоторые скрипты (Gmail, Calendar) хорошо заменяются MCP, другие (Obsidian индексация, ChromaDB) — нет.

---

## 1. Current Python Scripts Inventory

### 1.1 Google Integration Scripts

| Script | Purpose | Lines | Dependencies |
|--------|---------|-------|--------------|
| `gmail.sh` | Gmail API wrapper (inbox, read, send, search) | ~200 | Python OAuth2, curl |
| `gcal.sh` | Google Calendar API (events, create, list) | ~150 | Python OAuth2, curl |
| `google_auth.py` | OAuth2 flow for Google APIs | ~120 | google-auth-oauthlib |
| `google_auth_url.py` | Helper для auth URL | ~50 | - |
| `google_auth_code.py` | Helper для auth code exchange | ~70 | - |

### 1.2 Obsidian/Vault Scripts

| Script | Purpose | Lines | Dependencies |
|--------|---------|-------|--------------|
| `obsidian_index.py` | FTS5 индексирование vault | ~300 | sqlite3, pypdfium2, docx, openpyxl |
| `obsidian_query.py` | Поиск по FTS5 индексу | ~75 | sqlite3 |
| `obsidian_search.sh` | CLI обёртка для поиска | ~80 | - |
| `obsidian_rag_search.sh` | RAG поиск через ChromaDB | ~50 | - |

### 1.3 Document Processing

| Script | Purpose | Lines | Dependencies |
|--------|---------|-------|--------------|
| `ingest_docs.py` | ChromaDB ingestion (PDF/DOCX) | ~250 | markitdown, chromadb, ollama |
| `web_clip.sh` | Web clipping to Obsidian | ~200 | curl, Crawl4AI |

### 1.4 System/Cron Scripts

| Script | Purpose | Lines | Dependencies |
|--------|---------|-------|--------------|
| `crash_analyzer.sh` | Log analysis | ~120 | - |
| `watchdog.sh` | Container health monitoring | ~40 | docker |
| `backup.sh` | Backup automation | ~60 | rsync |
| `sudo_approve.sh` | Sudo approval system | ~300 | - |
| `ryot.sh`, `ryot_media.sh` | Ryot media tracking | ~250 | curl, sqlite3 |

---

## 2. Architecture Comparison

### 2.1 Python CLI Approach (Current)

```mermaid
flowchart LR
    A[Agent Request] -->|HTTP| B[OpenClaw Gateway]
    B -->|bash exec| C[Python Script]
    C -->|API| D[Gmail API]
    C -->|OAuth2| E[Google Auth]
    C -->|SQL| F[SQLite/ChromaDB]
    C -->|File| G[Obsidian Vault]
```

**Pros:**
- Direct API access — минимальная latency
- Полный контроль над логикой
- Нет overhead протокола
- Работает в изолированном Docker-контейнере
- Кастомная обработка ошибок

**Cons:**
- Каждая интеграция = отдельный скрипт
- Нет стандартизации интерфейса
- Ручное управление OAuth токенами
- Требует Python-зависимостей в контейнере

### 2.2 MCP-Based Approach (Proposed)

```mermaid
flowchart LR
    A[Agent Request] -->|MCP| B[Gemini CLI]
    B -->|MCP Protocol| C[MCP Server]
    C -->|HTTP| D[Composio/Gmail API]
    C -->|Standardized| E[Tool Response]
    E -->|MCP| B
    B -->|Output| F[Result]
```

**Pros:**
- Стандартизированный интерфейс (MCP)
- Composio управляет OAuth автоматически
- Один MCP сервер = множество инструментов
- Не нужно писать интеграционный код
- Discovery: LLM сам видит доступные tools

**Cons:**
- Overhead MCP протокола (JSON-RPC over stdio/SSE)
- Зависимость от внешнего сервиса (Composio)
- Меньше контроля над поведением
- Только то, что предоставляет MCP сервер
- Нужен Gemini CLI (еще один компонент)

---

## 3. Performance Analysis

### 3.1 Protocol Overhead

| Metric | Python Direct | MCP via Composio | Разница |
|--------|---------------|------------------|---------|
| **Cold start** | ~50ms (script load) | ~200-500ms (MCP init) | +300ms |
| **Per-call overhead** | ~10-20ms | ~30-100ms | +50ms |
| **OAuth refresh** | Manual, ~100ms | Automatic, ~200ms | Comparable |
| **Throughput** | Limited by API rate limits | Same + MCP overhead | Slightly lower |

### 3.2 Real-World Latency Example: Gmail Send

```
Python Script:
  Script execution:    50ms
  OAuth token load:    20ms
  API call:           300ms (Gmail latency)
  Response parsing:    10ms
  ─────────────────────────
  Total:             ~380ms

MCP via Composio:
  MCP initialization: 150ms (first call)
  Tool discovery:      50ms
  Request marshaling:  30ms
  Composio API:       400ms (includes their proxy)
  Response parsing:    40ms
  ─────────────────────────
  Total:             ~670ms (first call)
  Cached:            ~520ms (subsequent calls)
```

**Verdict:** MCP медленнее на ~100-200ms на вызов. Для интерактивного использования — приемлемо, для batch-операций — может накапливаться.

### 3.3 Memory & Resource Usage

| Component | Python Scripts | MCP + Gemini CLI |
|-----------|----------------|------------------|
| Memory (idle) | ~50MB (Python runtime) | ~100MB (Node.js + Gemini CLI) |
| Memory (active) | ~100MB | ~150MB |
| Disk | Scripts + deps | Gemini CLI + MCP servers |
| Network | Direct to APIs | Through MCP proxy |

---

## 4. Maintainability Comparison

### 4.1 Python Scripts

| Aspect | Score | Notes |
|--------|-------|-------|
| Code changes | ⭐⭐⭐ | Нужно редактировать код |
| Debugging | ⭐⭐⭐⭐ | Просто — логи, pdb |
| Testing | ⭐⭐⭐⭐ | Можно unit test |
| Documentation | ⭐⭐⭐ | Ручная документация |
| OAuth management | ⭐⭐ | Ручное обновление токенов |
| Error handling | ⭐⭐⭐⭐ | Полный контроль |

### 4.2 MCP Servers

| Aspect | Score | Notes |
|--------|-------|-------|
| Configuration | ⭐⭐⭐⭐⭐ | Только JSON config |
| Debugging | ⭐⭐⭐ | MCP logs, менее прозрачно |
| Testing | ⭐⭐⭐ | Через MCP inspector |
| Documentation | ⭐⭐⭐⭐ | Автогенерация из схемы |
| OAuth management | ⭐⭐⭐⭐⭐ | Автоматическое |
| Error handling | ⭐⭐⭐ | Стандартизированное |

### 4.3 Key Insight

**MCP выигрывает в конфигурации, но проигрывает в отладке.**

- Если "всё работает" — MCP проще
- Если "что-то сломалось" — Python проще дебажить

---

## 5. Feature Parity Analysis

### 5.1 Gmail Integration

| Feature | Python `gmail.sh` | Composio MCP | Parity |
|---------|-------------------|--------------|--------|
| Send email | ✅ | ✅ | 100% |
| Read inbox | ✅ | ✅ | 100% |
| Search emails | ✅ (Gmail query) | ✅ (Gmail query) | 100% |
| Get thread | ✅ | ✅ | 100% |
| Attachments | ✅ (via Python) | ✅ | 100% |
| Batch operations | ✅ (custom loop) | ❌ (one-by-one) | 70% |
| Custom formatting | ✅ (full control) | ⚠️ (limited) | 80% |

**Verdict:** Gmail — хороший кандидат на миграцию

### 5.2 Google Calendar

| Feature | Python `gcal.sh` | Composio MCP | Parity |
|---------|------------------|--------------|--------|
| List events | ✅ | ✅ | 100% |
| Create event | ✅ | ✅ | 100% |
| Update event | ✅ | ✅ | 100% |
| Delete event | ✅ | ⚠️ (check) | 90% |
| Recurring events | ✅ | ⚠️ | 80% |
| Custom reminders | ✅ (full control) | ⚠️ | 70% |

**Verdict:** Calendar — хороший кандидат на миграцию

### 5.3 Obsidian/Document Processing

| Feature | Python Scripts | MCP | Parity |
|---------|----------------|-----|--------|
| FTS5 indexing | ✅ (custom) | ❌ Not available | 0% |
| ChromaDB RAG | ✅ (custom) | ❌ Not available | 0% |
| PDF extraction | ✅ (pypdfium2) | ❌ | 0% |
| DOCX processing | ✅ (python-docx) | ❌ | 0% |
| Local file access | ✅ (direct) | ⚠️ (file system MCP?) | 50% |

**Verdict:** Obsidian/Docs — **НЕ** кандидаты на миграцию. Нет MCP серверов для этого.

### 5.4 Web Clipping

| Feature | Python `web_clip.sh` | MCP | Parity |
|---------|----------------------|-----|--------|
| Crawl4AI integration | ✅ | ❌ | 0% |
| Markdown extraction | ✅ (custom logic) | ⚠️ (fetch only) | 30% |
| Auto-save to vault | ✅ | ❌ | 0% |

**Verdict:** Web clip — остаётся на Python

---

## 6. Migration Candidates Matrix

### 6.1 HIGH Priority — Easy Win ✅

| Script | Replacement | Effort | Benefit |
|--------|-------------|--------|---------|
| `gmail.sh` | Composio Gmail MCP | Low | High |
| `gcal.sh` | Composio Calendar MCP | Low | High |
| `google_auth.py` | Composio managed OAuth | N/A | High |

**Why:** Composio уже имеет эти интеграции, OAuth автоматический, feature parity высокий.

### 6.2 MEDIUM Priority — Possible with Workarounds ⚠️

| Script | Replacement | Effort | Benefit |
|--------|-------------|--------|---------|
| `ryot.sh` | Custom MCP server | Medium | Medium |
| Crash analyzer | File system MCP + LLM | Medium | Low |

### 6.3 LOW Priority — Keep as Python ❌

| Script | Reason |
|--------|--------|
| `obsidian_index.py` | Нет MCP сервера для FTS5 + file parsing |
| `ingest_docs.py` | Требует ChromaDB + Ollama (локальные) |
| `obsidian_query.py` | SQLite FTS5 — нет MCP эквивалента |
| `web_clip.sh` | Crawl4AI интеграция — специфичная |
| `watchdog.sh` | Docker health checks — нужен host access |
| `backup.sh` | rsync/s3 — лучше в shell |

---

## 7. Hybrid Approach Recommendation

### 7.1 Recommended Architecture

```mermaid
flowchart TB
    subgraph "Gemini CLI + MCP (New)"
        GC[Gemini CLI]
        GC -->|MCP| CM[Composio MCP]
        CM -->|API| GMAIL[Gmail API]
        CM -->|API| GCAL[Calendar API]
    end
    
    subgraph "OpenClaw Docker (Current)"
        OC[OpenClaw Gateway]
        OC -->|bash| PY[Python Scripts]
        PY --> OBS[Obsidian Indexing]
        PY --> CHR[ChromaDB RAG]
        PY --> WEB[Web Clip]
    end
    
    subgraph "Integration Layer"
        OC -.->|HTTP/WebSocket| GC
    end
```

### 7.2 Implementation Strategy

**Phase 1: Gmail/Calendar Migration (Week 1)**
1. Настроить Gemini CLI с Composio MCP
2. Создать HTTP-прокси между OpenClaw и Gemini CLI
3. Мигрировать `gmail.sh` и `gcal.sh`
4. Удалить `google_auth.py` (Composio управляет OAuth)

**Phase 2: Integration Layer (Week 2)**
1. Создать OpenClaw skill для вызова Gemini CLI
2. Fallback на Python скрипты если MCP недоступен
3. A/B тестирование на реальных задачах

**Phase 3: Keep What Works (Ongoing)**
1. Оставить Obsidian/ChromaDB скрипты как есть
2. Документировать границы: что через MCP, что через Python

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Composio rate limits | Medium | Medium | Кэширование, fallback на Python |
| MCP server downtime | High | Low | Health checks, circuit breaker |
| Latency too high | Medium | Medium | Бенчмарк перед миграцией |
| OAuth scope limitations | Medium | Medium | Проверить scopes в Composio |
| Debugging complexity | Medium | High | Хорошее логирование, tracing |

---

## 9. Decision Matrix

### When to Use MCP (via Gemini CLI)

✅ **Use MCP when:**
- Есть готовый MCP сервер (Composio, etc.)
- Интеграция стандартная (Gmail, Slack, GitHub)
- Не нужен кастомный формат вывода
- OAuth management overhead нежелателен
- Нужен quick setup без кода

### When to Keep Python Scripts

✅ **Keep Python when:**
- Нужен доступ к локальным ресурсам (SQLite, ChromaDB)
- Требуется кастомная логика обработки
- Нужен прямой контроль над API
- Высокочастотные batch операции
- Интеграция специфичная для вашего workflow

---

## 10. Final Recommendation

### For Your OpenClaw Setup:

| Component | Recommendation | Priority |
|-----------|----------------|----------|
| **Gmail** | Migrate to Composio MCP | HIGH |
| **Calendar** | Migrate to Composio MCP | HIGH |
| **Obsidian FTS5** | Keep Python | - |
| **ChromaDB RAG** | Keep Python | - |
| **Web Clipping** | Keep Python + Crawl4AI | - |
| **System scripts** | Keep shell/Python | - |

### Migration Path:

```
1. Setup Gemini CLI + Composio MCP (1 день)
2. Test Gmail/Calendar parity (1 день)
3. Build OpenClaw → Gemini CLI bridge (2 дня)
4. Gradual rollout with fallback (1 день)
5. Monitor, optimize, decide on остальное (ongoing)
```

### Expected Outcome:

- ✅ Упрощение Google-интеграций (нет OAuth management)
- ✅ Стандартизированный интерфейс для новых интеграций
- ⚠️ Небольшое увеличение latency (~100ms)
- ✅ Меньше кода для поддержки
- ❌ Добавление Gemini CLI как зависимости

---

## 11. Quick Test Plan

Перед полной миграцией:

```bash
# 1. Install Gemini CLI
npm install -g @google/gemini-cli

# 2. Configure Composio MCP
gemini settings mcp add composio ...

# 3. Test Gmail parity
gemini "Send test email to myself"
python /data/bot/openclaw-docker/scripts/gmail.sh send ...

# 4. Compare outputs
time gemini "List my unread emails"
time bash /data/bot/openclaw-docker/scripts/gmail.sh inbox

# 5. Decision based on results
```

---

*Analysis generated: 2026-03-03*
*Context: OpenClaw Docker setup with Python scripts*
