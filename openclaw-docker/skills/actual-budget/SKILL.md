---
name: actual-budget
description: Интеграция с Actual Budget server для управления финансами. Use when: нужно запросить транзакции, синхронизировать с банком, управлять категориями, экспортировать данные из Actual Budget.
---

# Actual Budget Skill

## Что делает
Интеграция с Actual Budget API для:
- Запроса транзакций по счетам
- Синхронизации с банками
- Управления категориями расходов
- Экспорта данных (CSV, JSON)

## Команды

### Получить транзакции
```
покажи транзакции за март
сколько потратил на еду в этом месяце
```

### Синхронизация
```
синхронизируй Actual Budget с банком
обнови счета
```

### Категории
```
покажи категории расходов
создай категорию "Такси"
```

## Зависимости
- Actual Budget server (локально или по сети)
- API endpoint: обычно http://localhost:5006
- API token (из настроек Actual Budget)

## Настройка
1. Убедись что Actual Budget запущен
2. Получи API token в настройках (Settings → API)
3. Добавь в openclaw.json:
```json
{
  "actualBudget": {
    "baseUrl": "http://localhost:5006",
    "apiToken": "YOUR_TOKEN"
  }
}
```
