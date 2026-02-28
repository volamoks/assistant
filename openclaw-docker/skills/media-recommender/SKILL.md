---
name: media-recommender
description: "Recommend movies, series, books from your Ryot library"
triggers:
  - что посмотреть
  - что почитать
  - порекомендуй фильм
  - порекомендуй сериал
  - порекомендуй книгу
  - recommend movie
  - recommend series
  - recommend book
  - watch next
  - read next
  - добавь в список
  - я посмотрел
  - я прочитал
---

# Media Recommender — Рекомендации из Ryot

Использует Ryot API для получения персональных рекомендаций.

## Конфиг

- **URL:** `http://host:3014`
- **Token:** `openclaw-ryot-admin-token`

## Шаги

### 1. Что посмотреть / почитать

Используется скрипт `ryot_media.sh` (через Docker-контейнер):

```bash
docker exec openclaw-latest bash /data/bot/openclaw-docker/scripts/ryot_media.sh recommend MOVIE # или SHOW, BOOK
```

Скрипт:
1. Получает список "Want to watch" / "Want to read" (статус UNFINISHED)
2. Выбирает рандомный элемент
3. Возвращает краткое описание жанров и года

### 2. Добавить в список

Добавление кастомных медиа через API Key временно не поддерживается Ryot (ошибка `NO_USER_ID`), но скрипт может попытаться это сделать. Рекомендуется использовать Web UI:

```bash
docker exec openclaw-latest bash /data/bot/openclaw-docker/scripts/ryot_media.sh add MOVIE "Название" "Описание"
```

## Примеры ответов

**Что посмотреть:**
```
🎬 Рекомендую: "Inception"
📖 Описание: Коп влезает в сны...
⭐ Из твоего списка "Хочу смотреть"
```

**Что почитать:**
```
📚 Рекомендую: "Atomic Habits"
📖 Описание: Маленькие привычки, большие изменения...
```

## Notes

- Использует GraphQL API Ryot
- Для книг → `metadataTypes: [BOOK]`
- Для сериалов → `metadataTypes: [TV_SHOW]`
