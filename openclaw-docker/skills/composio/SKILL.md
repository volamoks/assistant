---
name: composio
alias:
  - composio-tools
  - mcp-tools
  - gmail-send
  - notion
  - slack
  - github
description: "Universal tool integration via Composio MCP. Send emails via Gmail, manage Notion pages, Slack messages, GitHub issues, and 100+ other integrations. Configure services via config.json."
triggers:
  - composio
  - gmail
  - notion
  - slack
  - github
  - linear
  - trello
  - asana
  - discord
  - "send email via"
  - "create notion"
  - "slack message"
  - "github issue"
---

# Composio Universal Tools Skill

Интеграция с [Composio](https://composio.dev) - платформой для подключения 100+ инструментов к AI агентам через MCP (Model Context Protocol).

## Quick Start

### 1. Настройка API ключа

Добавьте в `.env`:
```bash
COMPOSIO_API_KEY=your_api_key_here
```

Получить API ключ: https://app.composio.dev

### 2. Конфигурация сервисов

Отредактируйте `config.json` для включения нужных сервисов:

```json
{
  "services": {
    "gmail": {
      "enabled": true,
      "actions": ["SEND_EMAIL", "GET_THREAD", "SEARCH_EMAILS"]
    },
    "notion": {
      "enabled": false,
      "actions": ["CREATE_PAGE", "UPDATE_PAGE", "QUERY_DATABASE"]
    },
    "slack": {
      "enabled": false,
      "actions": ["SEND_MESSAGE", "GET_MESSAGES", "CREATE_CHANNEL"]
    }
  }
}
```

### 3. Использование

#### Отправка email через Gmail
```javascript
// Через skill API
await skill.run({
  service: "gmail",
  action: "SEND_EMAIL",
  params: {
    to: ["recipient@example.com"],
    subject: "Hello from Composio",
    body: "This is a test email"
  }
});
```

#### Или через Claude с MCP
```javascript
await skill.queryClaude({
  prompt: "Send an email to test@example.com saying hello",
  service: "gmail"
});
```

## Доступные сервисы

| Сервис | Действия | Описание |
|--------|----------|----------|
| `gmail` | SEND_EMAIL, SEARCH_EMAILS, GET_THREAD | Отправка и поиск писем |
| `notion` | CREATE_PAGE, UPDATE_PAGE, QUERY_DATABASE | Управление страницами |
| `slack` | SEND_MESSAGE, GET_MESSAGES | Отправка сообщений |
| `github` | CREATE_ISSUE, GET_ISSUE, LIST_ISSUES | Работа с issues |
| `linear` | CREATE_ISSUE, UPDATE_ISSUE | Трекер задач |
| `trello` | CREATE_CARD, MOVE_CARD | Kanban доски |

## Добавление нового сервиса

1. Включите сервис в Composio Dashboard
2. Добавьте в `config.json`:
```json
{
  "services": {
    "your-service": {
      "enabled": true,
      "actions": ["ACTION_1", "ACTION_2"]
    }
  }
}
```
3. Используйте без изменения кода!

## Примеры использования

### Email рассылка
```javascript
await skill.run({
  service: "gmail",
  action: "SEND_EMAIL",
  params: {
    to: ["user1@test.com", "user2@test.com"],
    subject: "Weekly Update",
    body: "Here is this week's summary..."
  }
});
```

### Создание страницы в Notion
```javascript
await skill.run({
  service: "notion",
  action: "CREATE_PAGE",
  params: {
    parent: { database_id: "your-db-id" },
    properties: {
      title: { title: [{ text: { content: "New Task" } }] }
    }
  }
});
```

### Отправка в Slack
```javascript
await skill.run({
  service: "slack",
  action: "SEND_MESSAGE",
  params: {
    channel: "#general",
    text: "Hello team!"
  }
});
```

## Архитектура

```
skills/composio/
├── SKILL.md          # Документация
├── index.mjs         # Основной модуль
├── config.json       # Конфигурация сервисов
└── package.json      # Зависимости
```

### Расширение функциональности

Для добавления кастомной логики создайте `custom-actions.mjs`:

```javascript
export const customActions = {
  gmail: {
    SEND_BULK_EMAILS: async (composio, params) => {
      // Ваша кастомная логика
      for (const recipient of params.recipients) {
        await composio.executeAction("gmail", "SEND_EMAIL", { ... });
      }
    }
  }
};
```

## Environment Variables

| Variable | Описание | Обязательная |
|----------|----------|--------------|
| `COMPOSIO_API_KEY` | API ключ Composio | Да |
| `COMPOSIO_BASE_URL` | Кастомный endpoint | Нет |
| `CLAUDE_API_KEY` | Для Claude Agent SDK | Нет |

## Troubleshooting

### Ошибка авторизации
- Проверьте API ключ в `.env`
- Убедитесь что сервис подключен в Composio Dashboard

### Сервис не найден
- Проверьте что сервис включен в `config.json`
- Проверьте правильность названия сервиса

### Rate limiting
- Composio имеет лимиты на бесплатном плане
- Используйте задержки между запросами

## Links

- [Composio Docs](https://docs.composio.dev)
- [Available Tools](https://app.composio.dev/apps)
- [MCP Protocol](https://modelcontextprotocol.io)
