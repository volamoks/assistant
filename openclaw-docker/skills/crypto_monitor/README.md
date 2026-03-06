# Crypto Monitor & Portfolio Tracker

Комплексная система мониторинга криптовалют и управления портфелем с интеграцией Bybit API.

## Компоненты

### 1. BTC Alert Monitor ([`btc_alert.py`](btc_alert.py))

Мониторинг цены BTC с динамическими порогами для алертов:

| Алерт | Порог | Описание |
|-------|-------|----------|
| `hot_buy` | -5% | Сильное падение — горячая покупка |
| `mild_dip` | -3% | Умеренное падение |
| `correction` | -10% | Коррекция рынка |
| `rally` | +5% | Рост рынка |

**Автоматический запуск:** Cron каждые 5 минут
```bash
*/5 * * * * /bin/bash /Users/abror_mac_mini/Projects/bot/openclaw-docker/scripts/crypto_monitor.sh
```

**Логирование:** `~/Library/Logs/crypto_monitor.log`

### 2. Portfolio Tracker ([`portfolio_tracker.py`](portfolio_tracker.py))

Трекинг портфеля с автоматической синхронизацией из Bybit.

#### Команды CLI

```bash
# Синхронизация с Bybit (загрузка позиций и баланса)
python3 portfolio_tracker.py sync

# Показать портфель
python3 portfolio_tracker.py show

# Детальный P&L расчет
python3 portfolio_tracker.py pnl

# DCA калькулятор (план усреднения)
python3 portfolio_tracker.py dca BTC 1000 --drop 5

# Рекомендации по ребалансировке
python3 portfolio_tracker.py rebalance

# История транзакций
python3 portfolio_tracker.py history

# Ручное добавление транзакции
python3 portfolio_tracker.py add BTC buy 0.5 95000 --fee 2.5 --notes "DCA buy"
```

#### Функции

- **Автосинхронизация с Bybit** — загрузка spot holdings и derivatives позиций
- **P&L расчет** — реализованный и нереализованный P&L по каждой позиции
- **DCA калькулятор** — пирамидальная стратегия усреднения (5 уровней)
- **Ребалансировка** — рекомендации при отклонении >5% от целевой аллокации
- **Telegram уведомления** — интеграция через `telegram.notify.TelegramNotifier`

### 3. Утренний Дайджест ([`morning_digest.sh`](../scripts/jobs/morning_digest.sh))

Ежедневный отчет включает:
- 💰 Crypto Portfolio (live данные из Bybit)
- 🪙 Crypto Radar
- 📱 Telegram Monitor
- 🖥️ System Status
- 📬 Inbox Router
- 📅 Calendar

## Интеграция с Bybit

### Настройка API

1. Создайте API ключи в Bybit:
   - Permissions: **Read-only** (для мониторинга)
   - IP whitelist: опционально

2. Добавьте в `.env` контейнера:
```bash
BYBIT_API=your_api_key
BYBIT_API_SECRET=your_api_secret
```

### Архитектура

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  portfolio_tracker  │────▶│  bybit_memory.py     │────▶│  Bybit API V5       │
│      .py            │     │  (Memory layer)      │     │  (wallet/positions) │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  TelegramNotifier   │
│  (уведомления)      │
└─────────────────────┘
```

## State Management

Состояние алертов хранится в [`state.json`](state.json):
```json
{
  "2026-03-06_mild_dip": true,
  "2026-03-06_hot_buy": true
}
```

Предотвращает дублирование алертов в течение одного дня.

## Хранение данных

| Файл | Описание |
|------|----------|
| `~/.openclaw/skills/crypto_monitor/portfolio.json` | Текущие holdings |
| `~/.openclaw/skills/crypto_monitor/transactions.json` | История транзакций |
| `~/.openclaw/skills/crypto_monitor/state.json` | State алертов |

## Примеры использования

### 1. Быстрая проверка портфеля

```bash
python3 portfolio_tracker.py sync && python3 portfolio_tracker.py show
```

### 2. DCA стратегия для BTC

```bash
# План на $1000 с шагами 5%
python3 portfolio_tracker.py dca BTC 1000 --drop 5
```

Вывод:
```
📊 *DCA PLAN for BTC*
Current Price: $95,000.00
Current Holding: 0.5
Target Investment: $1,000.00
Projected Avg Buy: $91,234.56

Buy Levels:
  Level 1: $90,250.00 (-5%) → 0.001662 (alloc: $150.00)
  Level 2: $85,500.00 (-10%) → 0.002339 (alloc: $200.00)
  Level 3: $80,750.00 (-15%) → 0.003096 (alloc: $250.00)
  Level 4: $76,000.00 (-20%) → 0.003289 (alloc: $250.00)
  Level 5: $71,250.00 (-25%) → 0.002105 (alloc: $150.00)
```

### 3. Ребалансировка портфеля

```bash
python3 portfolio_tracker.py rebalance
```

## Troubleshooting

### Ошибка синхронизации с Bybit

```
❌ Sync failed: Bybit API error: Invalid api key
```

**Решение:** Проверьте `BYBIT_API` и `BYBIT_API_SECRET` в `.env`

### Алерты не отправляются

1. Проверьте лог: `tail -f ~/Library/Logs/crypto_monitor.log`
2. Убедитесь что cron запущен: `crontab -l | grep crypto_monitor`
3. Проверьте Telegram bot token: `echo $TELEGRAM_BOT_TOKEN`

### Portfolio показывает пустые значения

```bash
# Проверьте синхронизацию
python3 portfolio_tracker.py sync

# Проверьте файл портфеля
cat ~/.openclaw/skills/crypto_monitor/portfolio.json
```

## Расширение

### Добавление новых алертов

Откройте [`btc_alert.py`](btc_alert.py) и добавьте в `ALERT_THRESHOLDS`:

```python
ALERT_THRESHOLDS = {
    # ... существующие алерты
    "new_alert": {
        "pct": -7.5,  # порог
        "label": "Deep Dip",  # название
        "direction": "🔻"  # эмодзи
    }
}
```

### Кастомные DCA стратегии

Измените `calculate_dca()` в [`portfolio_tracker.py`](portfolio_tracker.py):

```python
# Pyramid allocation (modify as needed)
allocation_percents = [0.10, 0.15, 0.25, 0.25, 0.25]  # 100% total
```
