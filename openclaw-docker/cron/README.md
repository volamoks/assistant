# Cron Jobs — OpenClaw

Расписание автоматических задач для всех агентов.

## Vault Reporting Pattern (для job'ов с отчётами)

Если cron job создаёт отчёт — используй этот паттерн:

### 3-шаговый протокол

```
ШАГ 1: Делай работу (сбор данных, анализ)
    ↓
ШАГ 2: Пиши отчёт в vault (OVERWRITE)
    ↓
ШАГ 3: Отправляй краткий бриф + кнопку WebApp
```

### Template для инструкции job'а

```markdown
## ШАГ 1: Сделай работу
[Сбор данных, анализ, etc.]

## ШАГ 2: Запиши отчёт в vault
Запиши полный отчёт в /data/obsidian/vault/Bot/DailyReports/<report-name>.md

Формат:
- Дата: YYYY-MM-DD в заголовке
- Секции по темам
- Ключевые выводы
- Детали/таблицы/ссылки

ВАЖНО: ЗАМЕНИ файл полностью (не дописывай).

## ШАГ 3: Отправь краткий бриф + кнопку
Отправь сообщение через Telegram (2-4 строки):
- Главный вывод/инсайт
- Ключевая метрика (если есть)
- Статус/сигнал

Добавь кнопку WebApp:
{"text": "📊 Открыть отчёт", "web_app": {"url": "https://vault.volamoks.store/report/<report-name>"}}

Используй tools: bash, message.
```

### Примеры report-name

- `crypto-report` — ежедневный крипто-отчёт
- `morning-briefing` — утренний бриф
- `system-status` — статус системы
- `telegram-digest` — дайджест каналов
- `error-log` — лог ошибок (APPEND, не overwrite!)

### Почему это работает

1. **Нет ошибок доставки** — Telegram лимит 4096 символов, vault без лимита
2. **Лучший UX** — пользователь видит сразу краткую сводку, открывает детали по кнопке
3. **История в Obsidian** — все отчёты доступны для поиска
4. **Чистый чат** — нет стен текста в Telegram

## Утренние job'ы (распределены по времени)

| Время (TZ) | Job | Агент |
|------------|-----|-------|
| 08:00 | Morning Task Briefing | analyst |
| 08:05 UTC (03:05) | morning-briefing | main |
| 08:10 | Intraday Snapshot | coder |
| 08:15 | Crypto Daily Report | investor |
| 08:20 | Crypto Radar | investor |
| 08:25 | Docker Analyzer | coder |
| 08:30 | System Status | analyst |
| 08:35 | Telegram Monitor | researcher |
| 08:40 | Inbox Router | coder |

## Команды

```bash
# Просмотр списка job'ов
python3 -c "import json; data=json.load(open('jobs.json')); [print(f\"{j.get('id','?')[:8]} | {j.get('name','?')[:30]} | {j.get('schedule',{}).get('expr','?')} | enabled={j.get('enabled',True)}\") for j in data['jobs']]"

# Проверка статуса
python3 -c "import json; data=json.load(open('jobs.json')); [print(f\"{j.get('name','?')}: errors={j.get('state',{}).get('consecutiveErrors',0)}, status={j.get('state',{}).get('lastStatus','?')}\") for j in data['jobs'] if j.get('state',{}).get('consecutiveErrors',0) > 0]"
```

## Файлы

- `jobs.json` — основной конфиг
- `jobs.json.bak` — резервная копия
- `runs/` — логи выполнений
- `README.md` — этот файл
