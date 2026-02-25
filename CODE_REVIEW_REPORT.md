# 🔍 Детальный анализ проекта Bot

**Дата анализа:** 2026-02-25  
**Версия:** Comprehensive Code Review  
**Принципы:** DRY, SOLID, KISS, Архитектура

---

## 📊 Резюме

| Категория | Оценка | Комментарий |
|-----------|--------|-------------|
| **DRY** | 🔴 Critical | Множественные нарушения - модели определены в 4+ местах |
| **SOLID** | 🟡 Medium | Отсутствует OCP, LSP нарушен в нескольких местах |
| **KISS** | 🟢 Good | Код парсеров относительно прост |
| **Архитектура** | 🔴 Critical | Нет центрального определения моделей, дублирование конфигов |

---

## 🚨 CRITICAL - Немедленное исправление

### 1. Дублирование Моделей данных (DRY Violation)

**Проблема:** Transaction Model определена в **4 разных местах**:

| Файл | Строки | Проблема |
|------|--------|----------|
| [`pfm/sink.py:47-58`](pfm/sink.py:47) | dict structure | Требует specific fields: `date, time, amount, currency, category, merchant, payment_method, card_last4, transaction_type, source, raw_text` |
| [`pfm/sync_to_actual.py:47-58`](pfm/sync_to_actual.py:47) | dict structure | Дублирует те же поля |
| [`pfm/parsers/humo.py:53-64`](pfm/parsers/humo.py:53) | dict structure | Возвращает ту же структуру |
| [`pfm/parsers/kapital.py:93-104`](pfm/parsers/kapital.py:93) | dict structure | Возвращает ту же структуру |
| [`pfm/parsers/uzum.py:59-70`](pfm/parsers/uzum.py:59) | dict structure | Возвращает ту же структуру |

**Рекомендация:** Создать единый файл `pfm/models.py`:

```python
# pfm/models.py
from dataclasses import dataclass
from datetime import date, time as dt_time
from typing import Optional
from enum import Enum

class TransactionType(Enum):
    DEBIT = "debit"
    CREDIT = "credit"

@dataclass
class Transaction:
    date: str          # YYYY-MM-DD
    time: str          # HH:MM:SS
    amount: float
    currency: str       # UZS
    category: str       # FOOD, TRANSPORT, etc.
    merchant: str
    payment_method: str
    card_last4: Optional[str]
    transaction_type: TransactionType
    source: str         # HUMO, KAPITAL, UZUM
    raw_text: str
```

---

### 2. Дублирование CATEGORY_MAP (DRY)

**Проблема:** [`CATEGORY_MAP`](pfm/sink.py:35) определен в **2 местах**:

```python
# pfm/sink.py:35
CATEGORY_MAP = {
    "FOOD":      "Food",
    "TRANSPORT": "Transport",
    ...
}

# pfm/sync_to_actual.py:31  
CATEGORY_MAP = {
    "FOOD":       "Food",
    "TRANSPORT":  "Transport",
    ...
}
```

**Решение:** Вынести в `pfm/models.py` или создать `pfm/constants.py`

---

### 3. Дублирование конфигурации - openclaw.json

**КРИТИЧЕСКАЯ ПРОБЛЕМА:** Два **РАЗНЫХ** файла конфигурации:

| Путь | Назначение | Проблема |
|------|------------|----------|
| [`openclaw-docker/core/openclaw.json`](openclaw-docker/core/openclaw.json) | Docker production | Использует litellm, ollama |
| [`deployment/core/openclaw.json`](deployment/core/openclaw.json) | Local development | Использует hardcoded paths: `/Users/abror/.gemini/antigravity/brain/...` |

**Оба содержат:**
- Model definitions (разные!)
- Agent configurations (разные!)
- API keys (разные!)

**Это ведет к:**
- Конфликтам при деплое
- Невозможности воспроизвести окружение
- Утечкам API ключей (deployment/core/openclaw.json содержит реальный OPENROUTER_API_KEY)

---

### 4. Дублирование Prompts

**Проблема:** Один и тот же контент в **3 местах**:

| Файл 1 | Файл 2 | Файл 3 |
|--------|--------|--------|
| [`deployment/prompts/SOUL_*.md`](deployment/prompts/) | [`deployment/core/prompts/SOUL_*.md`](deployment/core/prompts/) | [`openclaw-docker/prompts/SOUL_*.md`](openclaw-docker/prompts/) |
| [`deployment/prompts/AGENTS.md`](deployment/prompts/AGENTS.md) | [`deployment/core/prompts/AGENTS.md`](deployment/core/prompts/AGENTS.md) | [`openclaw-docker/prompts/AGENTS.md`](openclaw-docker/prompts/AGENTS.md) |

**Обнаружено 24+ дублированных prompt файла!**

---

### 5. Дублирование Agent Definitions

**Проблема:** Agent definitions в **2 местах**:

| [`deployment/agents/*.json`](deployment/agents/) | [`openclaw-docker/core/agents/*.json`](openclaw-docker/core/agents/) |
|---|---|
| automator.json | automator.json |
| browser.json | browser.json |
| ... (20+ файлов) | ... |

---

## 🟡 MEDIUM - Требует внимания

### 6. Нарушение DRY - категоризация

**Проблема:** [`categorize()`](pfm/parsers/_shared.py:5) и [`_detect_category()`](pfm/parsers/humo.py:12) делают одно и то же!

```python
# pfm/parsers/_shared.py
def categorize(text_lower: str, merchant: Optional[str]) -> str:
    rules = [
        (["korzinka", "makro", "havas", ...], "FOOD"),
        (["taxi", "yandex", "uber", ...], "TRANSPORT"),
        ...

# pfm/parsers/humo.py
CATEGORY_KEYWORDS = {
    'TRANSPORT': ['transport', 'tolov>m', ...],
    'FOOD': ['food', 'korzinka', ...],
    ...
}
def _detect_category(merchant: str) -> str:
    # Снова проверяет те же ключевые слова
```

**Решение:** Использовать единую функцию `categorize()` во всех парсерах.

---

### 7. SOLID: Open/Closed Principle (OCP)

**Проблема:** Добавление нового банка требует изменения нескольких файлов:

- [`pfm/sms_watcher.py:35-38`](pfm/sms_watcher.py:35) - добавить sender в `SENDERS`
- [`pfm/sms_watcher.py:113-118`](pfm/sms_watcher.py:113) - добавить parser в `_pick_parser()`
- Создать новый файл парсера

**Рефакторинг:** Создать registry паттерн:
```python
# pfm/parsers/registry.py
BANK_PARSERS = {
    'kapital': parse_kapital,
    'uzum': parse_uzum,
    'humo': parse_humo,
}
```

---

### 8. SOLID: Single Responsibility (SRP)

**Проблема:** [`sink.py`](pfm/sink.py) делает слишком много:

1. Загружает .env файлы ⚠️
2. Определяет конфиги (CATEGORY_MAP) ⚠️
3. Создает аккаунты в Actual ⚠️
4. Обрабатывает дедупликацию ⚠️
5. Создает транзакции ⚠️
6. Обрабатывает ошибки и retry ⚠️

**Рефакторинг:** Разделить на:
- `pfm/config.py` - конфигурация
- `pfm/actual_client.py` - работа с Actual API
- `pfm/sink.py` - только логика записи

---

### 9. Дублирование DB_PATH конфигурации

**Проблема:** Пути к БД продублированы:

```python
# pfm/dashboard.py:25
DB_PATHS = [
    Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/...",
    Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/...",
    Path("/data/obsidian/..."),
    Path(__file__).parent / "finance.db",
]

# pfm/sync_to_actual.py:24
DB_PATHS = [
    Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/...",
    Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/...",
    Path("/data/obsidian/..."),
]
```

---

## 🟢 MINOR - К улучшению

### 10. KISS: Избыточная сложность в benchmark_router.py

```python
# benchmark_router.py:6
SYSTEM_PROMPT = """## SAFETY & BEHAVIOR
1.  **Ask First**: Don't edit configs or install tools just because they were mentioned...
...
"""
```

**Проблема:** Hardcoded system prompt на 20+ строк внутри Python файла.  
**Рефакторинг:** Вынести в отдельный файл prompts/router_system.md

---

### 11. Environment Loading Duplication

**Проблема:** Загрузка .env повторяется:

```python
# pfm/sink.py:14
ENV_PATHS = [Path(__file__).parent / ".env", ...]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)

# pfm/humo_watcher.py:20
ENV_PATHS = [Path(__file__).parent / ".env", ...]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
```

**Решение:** Создать `pfm/config.py` с единой функцией `load_config()`

---

## 📈 Архитектурные проблемы

### 12. Нет центрального хранилища данных

**Текущее состояние:**
```
pfm/
├── finance.db (iCloud Obsidian)
├── .sms_state.json (локально)
└── sink.py → Actual Budget (remote)
```

**Проблемы:**
- Нет единого интерфейса для доступа к данным
- Зависимость от 3 разных источников (iCloud, local, Actual)
- Нет версионирования схемы БД

---

### 13. Backup файлы засоряют репозиторий

**Обнаружено:**
- `openclaw-docker/core/openclaw.json.bak`
- `openclaw-docker/core/openclaw.json.bak.1`
- `openclaw-docker/core/openclaw.json.bak.2`
- ... (7 backup файлов!)

**Решение:** Добавить в .gitignore или удалить

---

## 🎯 Рекомендации по приоритету

### P0 - Critical (Немедленно)
1. ✅ Создать `pfm/models.py` с единым `Transaction` dataclass
2. ✅ Вынести `CATEGORY_MAP` в константы
3. ✅ Удалить дублированные openclaw.json (или создать симлинк)
4. ✅ Удалить deployment/core/prompts/ дубликаты

### P1 - High (На этой неделе)
5. Унифицировать `categorize()` функцию
6. Создать registry для банковских парсеров
7. Вынести config в отдельный модуль

### P2 - Medium (На следующей неделе)
8. Разделить sink.py по SRP
9. Удалить backup файлы
10. Создать единый .env loading

---

## 📊 Метрики

| Метрика | Значение |
|---------|----------|
| Python файлов | ~15 |
| Дублированных моделей | 4+ |
| Дублированных конфигов | 6+ |
| Дублированных prompts | 24+ |
| DRY violations | 11 |
| Строк кода (pfm/) | ~1500 |

---

*Анализ проведен 2026-02-25*
