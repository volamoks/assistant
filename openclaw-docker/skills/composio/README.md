# Composio Skill 🚀

Универсальная интеграция с Composio MCP для подключения 100+ инструментов к вашему боту.

## Быстрый старт

### 1. Установка зависимостей

```bash
cd openclaw-docker/skills/composio
npm install
```

### 2. Настройка API ключа

Уже добавлено в `.env`:
```bash
COMPOSIO_API_KEY=ak_kVZicK4rWhwoksfTyVJg
```

### 3. Тестирование

```bash
# Просмотр доступных сервисов
node index.mjs list

# Подробности о Gmail
node index.mjs details gmail

# Отправка тестового письма
node index.mjs run gmail SEND_EMAIL '{"to":["s7abror@gmail.com"],"subject":"Test","body":"Hello!"}'

# Запрос к Claude с инструментами
node index.mjs query "Send email to s7abror@gmail.com saying hello"
```

## Как добавить новый сервис

**Всё делается через `config.json` — код менять не нужно!**

### Пример: включение Notion

1. Откройте `config.json`
2. Найдите секцию `notion`
3. Измените `"enabled": false` → `"enabled": true`

```json
{
  "services": {
    "notion": {
      "enabled": true,  // ← поменяйте здесь
      "actions": { ... }
    }
  }
}
```

4. Готово! Можно использовать:

```javascript
await skill.run({
  service: "notion",
  action: "CREATE_PAGE",
  params: { ... }
});
```

## Архитектура

```
skills/composio/
├── index.mjs        # Основной модуль (не трогать)
├── config.json      # Конфигурация сервисов (редактировать здесь)
├── SKILL.md         # Документация для агентов
├── package.json     # Зависимости
├── example.mjs      # Примеры использования
└── README.md        # Этот файл
```

## API

### Простое выполнение действия

```javascript
import { run } from "./index.mjs";

// Отправка email
await run({
  service: "gmail",
  action: "SEND_EMAIL",
  params: {
    to: ["test@example.com"],
    subject: "Hello",
    body: "World"
  }
});
```

### Запрос к Claude с MCP

```javascript
// Claude сам решает какие инструменты использовать
await run({
  mode: "query",
  prompt: "Send an email to test@example.com with a greeting",
  service: "gmail"  // или не указывать — будет доступно всё
});
```

### Batch операции

```javascript
await run({
  mode: "batch",
  actions: [
    { service: "gmail", action: "SEARCH_EMAILS", params: {...} },
    { service: "slack", action: "SEND_MESSAGE", params: {...} },
    { service: "github", action: "CREATE_ISSUE", params: {...} }
  ]
});
```

## Доступные сервисы

| Сервис | Статус | Действия |
|--------|--------|----------|
| Gmail | ✅ Включён | SEND_EMAIL, SEARCH_EMAILS, GET_THREAD |
| Notion | ❌ | CREATE_PAGE, UPDATE_PAGE, QUERY_DATABASE |
| Slack | ❌ | SEND_MESSAGE, GET_MESSAGES, CREATE_CHANNEL |
| GitHub | ❌ | CREATE_ISSUE, GET_ISSUE, LIST_ISSUES |
| Linear | ❌ | CREATE_ISSUE, UPDATE_ISSUE |
| Trello | ❌ | CREATE_CARD, MOVE_CARD |

Для включения сервиса установите `"enabled": true` в `config.json`.

## Добавление кастомного сервиса

1. Добавьте в `config.json`:

```json
{
  "services": {
    "my-service": {
      "enabled": true,
      "description": "My custom integration",
      "actions": {
        "MY_ACTION": {
          "description": "Does something cool",
          "requiredParams": ["param1"],
          "optionalParams": ["param2"]
        }
      }
    }
  }
}
```

2. Используйте:

```javascript
await run({
  service: "my-service",
  action: "MY_ACTION",
  params: { param1: "value" }
});
```

## Переменные окружения

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `COMPOSIO_API_KEY` | API ключ из Composio Dashboard | ✅ Да |
| `COMPOSIO_BASE_URL` | Базовый URL API | Нет |
| `CLAUDE_API_KEY` | Для Claude Agent SDK | Нет |

## Примеры из кода пользователя

Ваш исходный код автоматически поддерживается:

```javascript
import { query } from "@anthropic-ai/claude-agent-sdk";
import { Composio } from "@composio/core";

// Это работает через наш skill:
const composio = new Composio({ apiKey: process.env.COMPOSIO_API_KEY });
const session = await composio.create("user-id");

const stream = await query({
  prompt: "Send an email to s7abror@gmail.com...",
  options: {
    model: "claude-sonnet-4-5-20250929",
    permissionMode: "bypassPermissions",
    mcpServers: { composio: session.mcp }
  }
});
```

## Полезные ссылки

- [Composio Dashboard](https://app.composio.dev)
- [Composio Documentation](https://docs.composio.dev)
- [Available Tools](https://app.composio.dev/apps)
- [MCP Protocol](https://modelcontextprotocol.io)

---

**Совет:** Все сервисы настраиваются через `config.json`. Код в `index.mjs` менять не нужно!
