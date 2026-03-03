---
name: obsidian-sync
description: Двусторонняя синхронизация OpenClaw ↔ Obsidian vault. Use when: нужно сохранить ответ в заметку, прочитать заметку из чата, найти информацию в vault.
---

# Obsidian Sync Skill

## Что делает
- Сохраняет ответы бота в Obsidian заметки
- Читает заметки по запросу
- Поиск по vault (семантический + keyword)
- Поддержка wikilinks [[Link]]

## Команды

### Сохранить
```
сохрани это в заметку "Meeting notes"
запиши в Inbox
```

### Прочитать
```
прочитай заметку "Project X"
найди заметки про SmartVista
```

### Поиск
```
найди в Obsidian про BNPL
покажи связанные заметки
```

## Зависимости
- Obsidian vault путь: /data/obsidian/
- ChromaDB для семантического поиска (опционально)

## Настройка
Скилл работает из коробки. Путь к vault берётся из openclaw.json.
