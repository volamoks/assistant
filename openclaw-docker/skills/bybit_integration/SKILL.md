---
name: bybit_integration
description: "Bybit portfolio read — баланс, P&L, позиции, история транзакций. Use when: bybit, крипто портфель, p&l, баланс bybit, позиции, сколько монет."
triggers:
  - bybit
  - крипто портфель
  - p&l
  - баланс bybit
  - позиции bybit
  - сколько монет
---

# Bybit Integration Skill

**Версия:** 1.1
**Статус:** Active
**API:** Bybit V5 (read-only)

---

## Как использовать (ТОЧНЫЕ команды)

### Быстрый способ — bybit_read.py (рекомендуется)

```bash
# Полный портфель с P&L
cd ~/.openclaw/skills/crypto_assistant && python3 bybit_read.py

# Только баланс в JSON
cd ~/.openclaw/skills/crypto_assistant && python3 bybit_read.py --json
```

Переменные окружения уже установлены в контейнере: `BYBIT_API`, `BYBIT_API_SECRET`.

---

### Python клиент (bybit_integration)

**ВАЖНО:** Конструктор НЕ принимает позиционных аргументов — читает API ключи из env автоматически.

```python
import sys
sys.path.insert(0, '/home/node/.openclaw/skills')
from bybit_integration.src.client import BybitClient

client = BybitClient()  # БЕЗ аргументов — ключи из env

# Баланс кошелька (account_type, НЕ accountType)
balance = client.get_wallet_balance(account_type='UNIFIED')
coins = balance['list'][0]['coin']

# Каждая монета содержит:
# coin['coin']           — тикер (ETH, BTC...)
# coin['walletBalance']  — количество
# coin['usdValue']       — стоимость в USD
# coin['avgCostPrice']   — средняя цена покупки (используется в P&L)
# coin['unrealisedPnl']  — нереализованный P&L в USD
# coin['cumRealisedPnl'] — накопленный реализованный P&L

# Текущие цены (рыночные данные, без auth)
tickers = client.get_tickers(category='spot', symbol='ETHUSDT')
price = tickers['list'][0]['lastPrice']

# История транзакций
txlog = client.get_transaction_log(account_type='UNIFIED', limit=50)
```

---

## P&L данные

Bybit V5 **отдаёт P&L прямо в wallet-balance** — не нужно считать из истории ордеров:

| Поле | Описание |
|------|----------|
| `avgCostPrice` | Средняя цена покупки (то что показывает приложение) |
| `unrealisedPnl` | Нереализованный P&L = (текущая цена - avgCostPrice) × qty |
| `cumRealisedPnl` | Накопленный реализованный P&L по закрытым позициям |

Эти поля пустые если монета не была куплена через Bybit (напр. пришла с другого кошелька).

---

## API Endpoints (прямые HTTP вызовы)

```bash
# Баланс (приватный)
curl -H "X-BAPI-API-KEY: $BYBIT_API" https://api.bybit.com/v5/account/wallet-balance?accountType=UNIFIED

# Текущие цены (публичный, без auth)
curl https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT
```

- Base URL: `https://api.bybit.com`
- Rate limit: 120 requests/min

---

## Конфигурация

API ключи в env контейнера:
```
BYBIT_API=...
BYBIT_API_SECRET=...
```
