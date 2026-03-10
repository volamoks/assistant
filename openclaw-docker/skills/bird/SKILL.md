---
name: bird
description: X/Twitter CLI для чтения, поиска и постинга через Sweetistics API.
homepage: https://bird.fast
metadata: {"clawdbot":{"emoji":"🐦","requires":{"env":["SWEETISTICS_API_KEY"]}}}
---

# bird — X/Twitter интеграция

Использует **Sweetistics API** для доступа к X.com (Twitter).

## 🔑 Настройка

1. Зарегистрируйся на https://sweetistics.com
2. Dashboard → API Keys → Create Key
3. Добавь ключ в конфиг бота: `SWEETISTICS_API_KEY=your_key`

## Команды

**Чтение:**
- `bird whoami` — проверить авторизацию
- `bird read <url>` — прочитать твит
- `bird thread <url>` — прочитать тред
- `bird search "query" -n 5` — поиск (5 результатов)

**Постинг (только с подтверждением пользователя!):**
- `bird tweet "текст"` — новый твит
- `bird reply <url> "текст"` — ответ на твит

## Примеры использования

```bash
# Поиск по ключевым словам
bird search "OpenClaw AI" -n 10

# Прочитать конкретный твит
bird read https://x.com/user/status/123456

# Проверить аккаунт
bird whoami
```

## ⚠️ Важно

- **Не постишь без подтверждения!** Всегда спрашивай пользователя перед tweet/reply
- Для чтения/поиска подтверждение не нужно
- Лимиты API: 100 запросов/час (free tier)
