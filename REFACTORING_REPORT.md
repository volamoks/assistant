# 📊 Анализ и рефакторинг проекта openclaw-docker

## 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ (CRITICAL)

### 1. Массовое дублирование промптов в двух директориях

**Проблема:** Промпты определены в **ДВУХ** местах с **РАЗНЫМ** содержанием:

| Файл | `core/prompts/` | `prompts/` |
|------|-----------------|------------|
| `SOUL.md` | 51 строка | 53 строки |
| `AGENTS.md` | 87 строк | 102 строки |
| `SOUL_CODER.md` | **DeepSeek V3.2** | **Gemini 3 Flash** |
| `MEMORY.md` | `~/Documents/ObsidianVault/` | `/data/obsidian/` |

### 2. Два разных Identity (device ID)

| Расположение | Device ID |
|-------------|-----------|
| `core/identity/device.json` | `c314aa54...` |
| `identity/device.json` | `510600336...` |

### 3. Модели LLM определены в 4+ местах

1. `core/openclaw.json` — providers
2. `litellm/config.yaml` — LiteLLM конфиг
3. Agent JSONs — индивидуальные настройки
4. `prompts/AGENTS.md` — текстовые описания

---

## 🟠 СЕРЬЁЗНЫЕ ПРОБЛЕМЫ (HIGH)

- Пустые `shared/` директории
- 20+ Agent JSON без наследования
- Hardcoded пути в cron jobs
- Несколько `.env` файлов

---

## 🔢 ВЕРСИЯ OPENCLAW

| Параметр | Значение |
|----------|----------|
| **Текущая версия** | `2026.2.21` |
| **Последняя доступная** | `2026.2.23` |
| **Статус** | ⚠️ **2 версии позади** |

---

## ☁️ ИНТЕГРАЦИЯ С OBSIDIAN (уже настроена!)

**Монтирование в docker-compose:**
```yaml
- "/Users/abror_mac_mini/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs:/data/obsidian"
```

**Поддерживаемые фичи:**
- Semantic Search (RAG) — `skills/obsidian_search/`
- FTS5 Full-text Search — `scripts/obsidian_query.py`
- ChromaDB Embeddings

---

## 🗂️ СТРАТЕГИЯ: ПРОЕКТ vs OBSIDIAN

### Рекомендуемое разделение:

| Что | Где хранить | Причина |
|-----|-------------|---------|
| **Промпты агентов (SOUL_*.md)** | **Obsidian** | Часто меняешь, удобно |
| **Skills reference docs** | **Obsidian** | Большие файлы |
| **Agent registry (JSON)** | Проект | Структура данных |
| **Agent JSON definitions** | Проект | Инфраструктура |
| **docker-compose.yml** | Проект | Инфраструктура |
| **litellm/config.yaml** | Проект | Конфиг |
| **.env** | Проект | Секреты |

---

## ✅ ЧТО НУЖНО СДЕЛАТЬ

### Фаза 1: Очистка (выполнено ✅)
- [x] Удалить `core/prompts/`
- [x] Удалить `core/identity/`
- [x] Удалить пустые директории
- [x] Удалить orphan backups

### Фаза 2: LiteLLM aliases (выполнено ✅)
- [x] Добавить generic aliases в `litellm/config.yaml`
- [x] Обновить `openclaw.json`
- [x] Обновить agent JSONы

### Фаза 3: .env unification (выполнено ✅)
- [x] Создать symlink `litellm/.env` → `../.env`

### Фаза 4: Obsidian (опционально)
- [ ] Перенести `prompts/` в Obsidian
- [ ] Перенести reference docs в Obsidian
- [ ] Настроить монтирование

### Фаза 5: Обновление (отложено)
- [ ] Обновить OpenClaw до `2026.2.23` (нужна пересборка образа)

---

## 📊 ИТОГОВАЯ ОЦЕНКА

| Принцип | Оценка |
|---------|--------|
| **DRY** | ✅ 4/5 (после рефакторинга) |
| **SOLID** | 🟡 3/5 |
| **KISS** | 🟡 3/5 |
| **Архитектура** | 🟡 3/5 |

---

## 📝 ВЫПОЛНЕННЫЕ КОММИТЫ

```
7876dcd refactor: remove duplicate prompts and identity directories
ed918ad refactor: add generic LiteLLM aliases (smart, fast, thinking)
f92141b refactor: update main agents to use generic LiteLLM aliases
```

---

*Отчёт создан в рамках рефакторинга проекта openclaw-docker*
