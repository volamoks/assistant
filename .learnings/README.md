# Coder Learning System

## Правило: Коммит ПЕРЕД изменениями

**Перед любой серьёзной задачей (код, конфиг):**

1. **Запиши что будешь делать:**
   ```
   # В файле .learnings/TODO_YYYY-MM-DD.md
   ## Задача: [описание]
   - [ ] что сделаю
   - [ ] почему
   - [ ] что может пойти не так
   ```

2. **Закоммить текущее состояние:**
   ```bash
   cd /data/bot/openclaw-docker
   git add -A
   git commit -m "snapshot before [задача]"
   ```

3. **После выполнения:**
   - Обнови статус задачи
   - Если упало/сломалось — запиши в `.learnings/ERRORS.md`
   - Закоммить с описанием что сделал

## Файлы

| Файл | Что |
|------|-----|
| `.learnings/TODO.md` | Предстоящие задачи |
| `.learnings/ERRORS.md` | Ошибки и грабли |
| `.learnings/FEATURES.md` | Новые фичи |
| `.learnings/LESSONS.md` | Выводы |

## Пример

```markdown
## 2026-02-27: Добавить watchdog

- [x] Создал watchdog.sh
- [x] Добавил в cron
- [x] Добавил healthcheck в docker

### Вывод
- watchdog нужен для self-healing
- Проверять каждые 5 минут
```
