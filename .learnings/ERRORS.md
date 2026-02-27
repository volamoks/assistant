# Errors & Lessons - 2026-02-27

## Что сломалось

### 1. Бот упал и не восстановился сам
**Причина:** Не было watchdog/healthcheck
**Урок:** Нужна система самовосстановления
**Решение:** Добавили watchdog + healthcheck

### 2. Группа Telegram не работала
**Причина:** 
- groupPolicy: open (не allowlist)
- allowFrom: null
- requireMention: не настроено

**Урок:** Нужно правильно настроить конфиг для групп
**Решение:** 
- groupPolicy: allowlist
- allowFrom: добавить ID группы

### 3. Не было точки восстановления
**Причина:** Git не был настроен с базовым коммитом
**Урок:** Нужен baseline commit для восстановления
**Решение:** Сделали "recovery baseline" коммит

## Выводы

1. ✅ Watchdog каждые 5 минут - работает
2. ✅ Git backup в 3:00
3. ✅ Healthcheck в Docker
4. ✅ Coder должен коммитить перед изменениями
5. ✅ Записывать уроки в .learnings/

## Что проверить перед серьёзными изменениями

- [ ] Git baseline есть
- [ ] Watchdog работает
- [ ] Healthcheck настроен
- [ ] Конфиг закоммичен
