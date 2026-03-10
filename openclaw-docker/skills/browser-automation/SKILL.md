---
name: browser-automation
description: Автоматизация браузера через accessibility tree (дёшево и быстро) или скриншоты (для визуальных задач). Primary tool: PinchTab. Fallback: browserless.
triggers:
  - зайди на сайт
  - открой страницу
  - спарси
  - скриншот
  - заполни форму
  - кликни
  - browser
  - navigate
---

# Browser Automation

## Инструменты

| Инструмент | Адрес | Когда использовать |
|---|---|---|
| **PinchTab** | `http://pinchtab:9867` | 90% задач — парсинг, клики, формы (~800 токенов/страница) |
| **Browserless** | `http://browserless:3000` | Скриншоты, сложные JS-сайты, визуальные задачи |

## PinchTab (основной)

### Навигация и чтение
```bash
bash /home/node/.openclaw/skills/browser-automation/pinchtab.sh navigate "https://example.com"
bash /home/node/.openclaw/skills/browser-automation/pinchtab.sh snapshot
bash /home/node/.openclaw/skills/browser-automation/pinchtab.sh text
```

### Действия
```bash
# Клик по элементу из снапшота (e0, e1, e2...)
bash /home/node/.openclaw/skills/browser-automation/pinchtab.sh action click e5

# Ввод текста
bash /home/node/.openclaw/skills/browser-automation/pinchtab.sh action fill e3 "текст"

# Нажатие клавиши
bash /home/node/.openclaw/skills/browser-automation/pinchtab.sh action press e0 Enter
```

### Типичный workflow
1. `navigate` → открыть страницу
2. `snapshot` → получить accessibility tree (элементы e0, e1, e2...)
3. `action click eN` → кликнуть нужный элемент
4. `snapshot` / `text` → проверить результат

## Browserless (скриншоты и fallback)

```bash
# Скриншот через CDP
curl -s http://browserless:3000/screenshot \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}' -o /tmp/screenshot.png
```

## Примеры задач

```
# Парсинг цен
navigate → snapshot → найти элементы с ценами → text

# Логин на сайт
navigate login page → snapshot → action fill email/password → action click submit

# Скачать таблицу
navigate → action click "Export" → text
```
