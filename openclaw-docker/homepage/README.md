# Homepage Dashboard

## Запуск

```bash
cd openclaw-docker
docker-compose -f docker-compose.apps.yml up -d homepage
```

## Доступ

- **URL:** http://home.volamoks.store (через Cloudflare Tunnel)
- **Порт:** http://localhost:3000

## Конфигурация

Основной конфиг: `openclaw-docker/homepage/settings.yaml`

### Структура конфига

```yaml
# Основные настройки
title: Jarvis Home Dashboard      # Заголовок
headerStyle: floating            # Стиль хедера
background: URL                  # Фон

# Цветовая схема
theme: primary
color:
  primary: '#6366f1'
  secondary: '#8b5cf6'
  text: '#f8fafc'
  background: '#0f172a'

# Закладки (bookmarks) - группы ссылок
bookmarks:
  - name: AI Services            # Название группы
    icon: robot                  # Иконка
    items:
      - name: OpenClaw          # Название ссылки
        href: http://...         # URL
        icon: robot             # Иконка

# Сервисы с виджетами
services:
  - name: Docker
    icon: docker
    href: http://host.docker.internal:3000
    widget:
      type: docker              # Тип виджета
      url: http://host.docker.internal
```

### Доступные иконки

- robot, cpu, server, workflow, database, search
- home, shield, folder, tv, download
- activity, monitor, docker, file-text, book, trello

### Типы виджетов

- `docker` - статус контейнеров
- `homeassistant` - датчики Home Assistant
- `adguard` - статистика AdGuard
- `n8n` - статус n8n
- `uptimekuma` - мониторинг
- `clock` - часы
- `weather` - погода
- `search` - поиск

## Добавление новых сервисов

1. Откройте `homepage/settings.yaml`
2. Добавьте в секцию `services:`:
```yaml
- name: My Service
  icon: star
  href: http://service.url
  widget:
    type: widget_type
    url: http://service.internal.url
```

3. Перезапустите контейнер:
```bash
docker-compose -f docker-compose.apps.yml restart homepage
```

## Просмотр логов

```bash
docker logs homepage
```

## Widget API Key

Для некоторых виджетов (AdGuard, Home Assistant) может потребоваться API key в переменных окружения.
