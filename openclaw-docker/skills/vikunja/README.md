# Vikunja Task Tracker Integration

## Overview

Интеграция Vikunja как центральной системы трекинга задач для ночных агентов OpenClaw.

**Проблема**: Ночные агенты (nightly-analysis, nightly-evolution, weekly-discovery) генерировали уведомления в файлы (improvement-ideas.md, pending-changes.md, discovery-proposals.md), но задачи терялись и не отслеживались.

**Решение**: Вместо файловых уведомлений агенты создают задачи в Vikunja с приоритетами и статусами.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Nightly Agents                           │
├─────────────────┬─────────────────┬─────────────────────────┤
│ nightly-analysis│ nightly-evolution│ weekly-discovery       │
│ (21:00 UTC)     │ (22:40 Tashkent) │ (23:00 Tashkent, Fri)  │
└────────┬────────┴────────┬─────────┴──────────┬──────────────┘
         │                 │                     │
         ▼                 ▼                     ▼
    ┌────────────────────────────────────────────────────────┐
    │              Vikunja CLI (vikunja.sh)                  │
    │  - create-bug                                          │
    │  - create-improvement                                  │
    │  - create-discovery                                    │
    │  - list-by-status                                      │
    │  - list-overdue                                        │
    │  - weekly-report                                       │
    └─────────────────────┬──────────────────────────────────┘
                          │
                          ▼
    ┌────────────────────────────────────────────────────────┐
    │              Vikunja Server                            │
    │  Project: OpenClaw Bot                                 │
    │  - [BUG] задачи (priority=3)                           │
    │  - [IMPROVE] задачи (priority=2)                       │
    │  - [IDEA] задачи (priority=1)                          │
    │  - [CONFIG] задачи (priority=2)                        │
    └────────────────────────────────────────────────────────┘
```

---

## Setup

### 1. Environment Variables

Добавьте в `.env`:
```bash
# Для запуска из Docker контейнера:
VIKUNJA_URL=http://vikunja:3456/api/v1
# Для запуска с хоста (локально):
# VIKUNJA_URL=http://localhost:3456/api/v1
VIKUNJA_TOKEN=your-api-token
```

### 2. Создание проектов

Запустите скрипт настройки:
```bash
bash /data/bot/openclaw-docker/skills/vikunja/setup_projects.sh
```

Это создаст:
- **OpenClaw Bot** — для задач от агентов
- **Personal** — для личных задач

### 3. Проверка подключения

```bash
bash /data/bot/openclaw-docker/skills/vikunja/vikunja.sh status
```

---

## Vikunja CLI Commands

### Базовые команды

```bash
# Список всех проектов
vikunja.sh projects

# Список всех задач
vikunja.sh list

# Список задач по проекту
vikunja.sh list-by-project <project_id>

# Получить задачу по ID
vikunja.sh get <task_id>

# Проверка API
vikunja.sh status
```

### Создание задач

```bash
# Создать задачу (общая)
vikunja.sh create "Заголовок" "Описание" "YYYY-MM-DD" priority

# Создать баг (priority=3, high)
vikunja.sh create-bug "Название бага" "Описание проблемы" "YYYY-MM-DD"

# Создать улучшение (priority=2, medium)
vikunja.sh create-improvement "Название" "Описание" "YYYY-MM-DD"

# Создать идею/discovery (priority=1, low)
vikunja.sh create-discovery "Название" "Описание" "YYYY-MM-DD"

# Создать для конкретного проекта
vikunja.sh create-for-project <project_id> "Заголовок" "Описание" "YYYY-MM-DD" priority
```

### Управление задачами

```bash
# Обновить задачу
vikunja.sh update <task_id> "Новый заголовок" "Новое описание"

# Пометить как выполненную
vikunja.sh done <task_id>

# Удалить задачу
vikunja.sh delete <task_id>

# Список по статусу
vikunja.sh list-by-status done     # выполненные
vikunja.sh list-by-status undone   # открытые

# Просроченные задачи
vikunja.sh list-overdue

# Недельный отчёт
vikunja.sh weekly-report

# Очистить кэш
vikunja.sh clear-cache
```

---

## Nightly Jobs Integration

### nightly-analysis (21:00 UTC)

**Было**: Запись ошибок в `improvement-ideas.md`
**Стало**: Создание задач Vikunja

```bash
# Для багов:
vikunja.sh create-bug "[Краткий заголовок]" "Описание: что, сессия, сколько раз" "YYYY-MM-DD"

# Для улучшений:
vikunja.sh create-improvement "[Заголовок]" "Рекомендация: [fix]" "YYYY-MM-DD"
```

### nightly-evolution (22:40 Tashkent)

**Было**: Анализ `improvement-ideas.md` и запись в `pending-changes.md`
**Стало**: Анализ задач Vikunja, создание [CONFIG] задач

```bash
# Получить открытые задачи
vikunja.sh list-by-status undone

# Обновить повторяющуюся задачу
vikunja.sh update <task_id> "[title]" "[description + note о повторении]"

# Создать config-change задачу
vikunja.sh create-for-project <id> "[CONFIG] Заголовок" "Описание" "YYYY-MM-DD" 2
```

### weekly-discovery (23:00 Tashkent, Fri)

**Было**: Запись идей в `discovery-proposals.md`
**Стало**: Создание [IDEA] задач в Vikunja

```bash
vikunja.sh create-discovery "[Название идеи]" "Что/Откуда/Зачем/Реализация/Сложность" "YYYY-MM-DD"
```

### weekly-review (12:00 Tashkent, Sat)

**Было**: Чтение файлов, отчёт из файлов
**Стало**: Отчёт из Vikunja

```bash
# Получить все открытые задачи
vikunja.sh weekly-report
```

Формат отчёта в Telegram:
```
🔧 Еженедельный ревью — DD MMM
Накопилось N задач в Vikunja:

📌 ФИКСЫ (баги):
1. [Заголовок] — Priority N
   Vikunja: #<task_id>

🔧 УЛУЧШЕНИЯ:
2. [Заголовок] — Priority N
   Vikunja: #<task_id>

🔍 НОВЫЕ ИДЕИ:
3. [Заголовок] — Low/Med
   Vikunja: #<task_id>

⚙️ CONFIG CHANGES:
4. [Заголовок] → [файл]
   Vikunja: #<task_id>
```

### morning-briefing (03:00 UTC)

**Было**: Чтение `improvement-ideas.md`
**Стало**: Отчёт из Vikunja (overdue + undone)

```bash
vikunja.sh list-overdue
vikunja.sh list-by-status undone
```

---

## Task Types and Priorities

| Тип | Префикс | Priority | Описание |
|-----|---------|----------|----------|
| Bug | `[BUG]` | 3 (high) | Критические ошибки |
| Improvement | `[IMPROVE]` | 2 (medium) | Улучшения |
| Discovery | `[IDEA]` | 1 (low) | Новые идеи |
| Config Change | `[CONFIG]` | 2 (medium) | Изменения конфигов |

---

## Mark-as-Done Protocol

После реализации задачи:

1. **Для Vikunja задач**:
```bash
vikunja.sh done <task_id>
```

2. **Для файловых записей** (pending-changes.md):
```markdown
- Статус: ✅ done YYYY-MM-DD
```

---

## Caching

CLI использует кэширование API ответов:
- Путь: `/tmp/vikunja_cache/`
- TTL: 5 минут
- Команда: `vikunja.sh clear-cache`

---

## Troubleshooting

### Ошибка: VIKUNJA_TOKEN not set
```bash
# Проверьте .env
echo $VIKUNJA_TOKEN

# Добавьте в .env если пусто
VIKUNJA_TOKEN=your-token
```

### Ошибка подключения к API
```bash
# Проверьте URL
echo $VIKUNJA_URL

# Для запуска внутри Docker: http://vikunja:3456/api/v1
# Для запуска с хоста: http://localhost:3456/api/v1
```

### CLI не создаёт задачи (пустой PROJECT_ID)
```bash
# Проверьте что Vikunja доступен
curl -H "Authorization: Bearer $VIKUNJA_TOKEN" "$VIKUNJA_URL/projects"

# Если пусто — проверьте что Vikunja запущен
docker ps | grep vikunja
```

### Задачи не создаются
```bash
# Проверьте статус API
vikunja.sh status

# Проверьте список проектов
vikunja.sh projects

# Если проектов нет — запустите setup
bash setup_projects.sh
```

---

## Files Reference

| Файл | Описание |
|------|----------|
| `vikunja.sh` | CLI скрипт для работы с API |
| `setup_projects.sh` | Скрипт настройки проектов |
| `SKILL.md` | Документация скилла |
| `README.md` | Этот файл |

---

## Next Steps

1. Запустить `setup_projects.sh` для создания структуры
2. Протестировать создание задач через CLI
3. Дождаться nightly run и проверить создание задач
4. Настроить уведомления из Vikunja (опционально)
