---
name: telegram-monitor
description: "Monitor Telegram channels from list in Obsidian and create daily digests with interesting posts"
triggers:
  - monitor telegram
  - telegram digest
  - каналы тг
  - check channels
---

# Telegram Channel Monitor

Ежедневно проверяет Telegram каналы из списка в Obsidian и создаёт дайджест.

## Workflow

1. **Прочитай список каналов** из `/data/obsidian/To claw/Telegram/Channels/README.md`

2. **Для каждого канала:**
   - Получи последние 10 постов через Telegram API
   - Оцени интересность (AI, tech, полезное)
   - Если интересно → добав в дайджест

3. **Создай файл** `/data/obsidian/To claw/Telegram/Digest_YYYY-MM-DD.md`

   Формат:
   ```markdown
   # Дайджест Telegram — YYYY-MM-DD

   ## Интересные посты

   ### Канал: @channel_name
   - [Название поста](link) — краткое описание
   - [Название поста](link) — краткое описание

   ## Резюме
   - Всего проверено: N каналов
   - Интересных постов: M
   ```

4. **Отправь в TG** краткое резюме:
   ```
   📱 Telegram Digest
   Проверено N каналов, M интересных постов
   ```

## Notes

- Использует Telegram API (не userbot)
- Требует API_ID и API_HASH в.env
- Запускать ежедневно в удобное время
