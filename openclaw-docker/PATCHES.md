# OpenClaw Patches

## ⚠️ Патчи переживают рестарты контейнера, но НЕ переживают обновления образа

---

## 1. `buildInlineKeyboard` — Поддержка `web_app` и `url` кнопок

**Статус**: ❌ НЕ ПРИМЕНЁН (невозможно — /app в read-only overlay)

**Файл**: `/app/dist/auth-profiles-C_YAZ4fH.js`

**Проблема**: OpenClaw's `buildInlineKeyboard` пропускает только кнопки с `callback_data`.
Кнопки с `web_app` или `url` silently удаляются.

**Решение**: Использовать прямые вызовы Telegram Bot API вместо OpenClaw message tool.

```javascript
// БЫЛО (строка ~133390):
const rows = buttons.map((row) => row.filter(
  (button) => button?.text && button?.callback_data  // ← только callback_data
))

// СТАЛО (нужно заменить на):
const rows = buttons.map((row) => row.filter(
  (button) => button?.text && (
    button?.callback_data ||
    button?.url ||
    button?.web_app
  )
)).map((button) => {
  const base = { text: button.text };
  if (button.callback_data) return { ...base, callback_data: button.callback_data };
  if (button.web_app) return { ...base, web_app: button.web_app };
  if (button.url) return { ...base, url: button.url };
  return null;
})
```

**Как применить**: 
```bash
# Найти строку:
grep -n "button?.callback_data" /app/dist/auth-profiles-C_YAZ4fH.js

# Заменить filter predicate и map function
```

**Обходной путь (рекомендуется)**: Используйте `crypto_signal_helpers.py` для Python скриптов
или `claw_auto_ui.js` для Node.js — они используют прямой Telegram Bot API.

---

## 2. A2UI System — что было сделано

**Дата**: 2026-03-19

### Проблема
- `claw_auto_ui.js` — никогда не существовал (SKILL.md ссылался на несуществующий файл)
- `a2ui.bundle.js` — Shiki syntax highlighter, не WebApp UI библиотека
- SKILL.md — устаревший, описывает несуществующий функционал

### Что создано

1. **`/data/bot/openclaw-docker/core/workspace-main/a2ui/claw_auto_ui.js`**
   - Node.js модуль для создания WebApp кнопок и inline кнопок
   - Экспорты: `createWebAppForm`, `createInlineButtons`, `selectUIMode`, `sendWithAutoUI`

2. **`/data/bot/openclaw-docker/crypto_signal_helpers.py`**
   - Python аналог для Python скриптов (crypto_signal.py)
   - Использует прямой Telegram Bot API (обходит buildInlineKeyboard)

3. **`/data/bot/openclaw-docker/vault-viewer/server.py`** (обновлён)
   - Добавлен route `/a2ui/<formType>` для WebApp форм
   - Поддержка `?id=<formId>` для загрузки данных из кэша

4. **`/data/bot/openclaw-docker/vault-viewer/webapp/`** (новое)
   - `crypto-signal.html` — форма для крипто сигналов
   - `tasks.html` — форма для задач
   - `report.html` — generic отчёт

5. **`/home/node/.openclaw/skills/skills/a2ui-auto/SKILL.md`** (обновлён)
   - Документирует реальный API

---

## 3. Как пересобрать vault-viewer после изменений

```bash
# server.py уже изменён на host filesystem:
/data/bot/openclaw-docker/vault-viewer/server.py

# Перезапустить контейнер:
docker restart vault-viewer

# Проверить:
curl https://vault.volamoks.store/a2ui/crypto-signal?id=test
```

---

## 4. Как использовать WebApp кнопки

### Python (crypto_signal.py и др.):
```python
from crypto_signal_helpers import create_webapp_button, create_inline_buttons, send_telegram_message

btn = create_webapp_button('crypto-signal', {
    'type': 'crypto_signal',
    'symbol': 'BTC',
    'direction': 'BUY',
    'price': '$97,430',
    'price_change_pct': 5.2,
    'timestamp': '2026-03-19T06:50:00Z'
}, button_text='📊 Open Signal')

rows = create_inline_buttons([
    {'text': '📈 Buy', 'callback_data': 'buy_btc'},
    {'text': '⏭ Skip', 'callback_data': 'skip_btc'}
])

send_telegram_message(
    text='🟢 BTC Signal!',
    buttons=[[btn]] + rows
)
```

### Node.js (agents):
```javascript
const { createWebAppForm, createInlineButtons } = require('/data/bot/openclaw-docker/core/workspace-main/a2ui/claw_auto_ui.js');

const form = createWebAppForm('report', { type: 'crypto_signal', symbol: 'BTC' });
const rows = createInlineButtons([
    {text: '📈 Buy BTC', callback_data: 'buy_btc'},
    {text: '⏭ Skip', callback_data: 'skip_btc'}
]);

// Send via message tool with buttons parameter
message({
    action: 'send',
    target: '6053956251',
    text: 'BTC Signal!',
    buttons: [[form.button], ...rows]
});
```

---

## 5. OpenClaw Upgrade Procedure

При обновлении OpenClaw образа:
1. Проверить `/app/dist/auth-profiles-C_YAZ4fH.js` на наличие `buildInlineKeyboard`
2. Если изменился — проверить поддержку `web_app`/`url` кнопок
3. Все кастомные файлы (`claw_auto_ui.js`, `crypto_signal_helpers.py`, `vault-viewer/server.py`, webapp/) — на host filesystem, не затрагиваются
