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

**GraphQL запрос к Ryot:**

```bash
curl -s -X POST http://host:3014/backend/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer openclaw-ryot-admin-token" \
  -d '{
    "query": "query { me { listOfAllMedia(limit: 20, metadataTypes: [MOVIE]) { items { name details { metadata { ... on MovieDetails { overview } } } } } } }"
  }'
```

### 2. Рандомная рекомендация

1. Получить список "Want to watch" / "Want to read"
2. Выбрать рандомный элемент
3. Вернуть с кратким описанием

### 3. Добавить в список

```bash
curl -s -X POST http://host:3014/backend/graphql \
  -H "Authorization: Bearer openclaw-ryot-admin-token" \
  -d '{"query":"mutation { addToList(mediaName: \"$TITLE\", metadataType: MOVIE, list: WANT_TO_WATCH) { success } }"}'
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
