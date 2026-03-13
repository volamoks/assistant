---
name: a2ui-auto
description: "Automatic UI mode selection for Claw responses. Automatically chooses between text, inline buttons, and WebApp forms based on content analysis."
triggers:
  - auto ui
  - claw ui
  - automatic buttons
  - inline buttons
  - webapp form
  - send with buttons
---

# A2UI Auto - Automatic UI Mode Selection

Automatically selects the best UI mode for Claw responses:
- **Text** — simple answers, information
- **Inline buttons** — 2-5 options, simple actions
- **WebApp form** — complex forms, data entry, lists

## Usage

### In Claw Router (SOUL.md)

```javascript
// Load the module
const { selectUIMode, createInlineButtons, createWebAppForm, sendWithAutoUI } = require('/data/bot/openclaw-docker/core/workspace-main/a2ui/claw_auto_ui');

// Auto-send with UI detection
await sendWithAutoUI("Ваше сообщение", {
  options: ['Option 1', 'Option 2'],  // Optional: explicit options
  formType: 'tasks',                   // Optional: form type for WebApp
  formData: { tasks: [...] }           // Optional: form data
});
```

### Manual Mode Selection

```javascript
const { mode, score, reasons } = selectUIMode("Какие задачи в работе?");
// → { mode: 'webapp', score: 50, reasons: ['Task/list query detected', ...] }
```

### Create Inline Buttons

```javascript
const buttons = createInlineButtons(['Да', 'Нет', 'Отмена'], { maxPerRow: 2 });
message({ text: 'Подтвердить?', buttons });
```

### Create WebApp Form

```javascript
const form = createWebAppForm('tasks', { tasks: [...] }, {
  buttonText: '📋 Открыть задачи'
});
message({ text: 'Ваши задачи:', buttons: [[form.button]] });
```

## Quick Helpers

```javascript
const { askYesNo, askSelect, showTaskList, showCalendar } = require('./claw_auto_ui');

// Yes/No question
const yesNo = askYesNo('Подтвердить действие?');
message(yesNo);

// Selection
const select = askSelect('Выберите приоритет:', ['Низкий', 'Средний', 'Высокий']);
message(select);

// Task list WebApp
const taskList = showTaskList(tasks, { buttonText: '📋 Задачи' });
message({ text: 'Задачи:', buttons: [[taskList.button]] });
```

## Mode Selection Logic

| Situation | UI Mode | Score |
|-----------|---------|-------|
| Simple text, no question | Text | 0-4 |
| Yes/No question | Inline | 10+ |
| 2-5 options | Inline | 15-25 |
| Task/list query | WebApp | 50+ |
| Form/scheduling | WebApp | 35+ |
| Complex data/report | WebApp | 40+ |
| Calendar/meeting | WebApp | 25+ |

## Thresholds

- **Text**: score < 5
- **Inline**: 5 ≤ score < 35
- **WebApp**: score ≥ 35

## Module Location

```
/data/bot/openclaw-docker/core/workspace-main/a2ui/claw_auto_ui.js
```

Run self-test:
```bash
node /data/bot/openclaw-docker/core/workspace-main/a2ui/claw_auto_ui.js
```
