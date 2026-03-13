# Morning Digest Skill

A skill for generating and viewing morning digest reports.

## Files

- `morning_digest.py` - Main skill with A2UI button and report generation

## Usage

### From Cron (automatic)

The morning digest runs automatically at 9:00 AM Tashkent via cron:
- Creates full report in Obsidian: `/data/obsidian/vault/Bot/morning-reports/YYYY-MM-DD.md`
- Sends short summary (max 5 lines) to Telegram with "Подробнее" button

### From Telegram (manual)

```
🌅 Утренний дайджест
```

Shows the latest morning report in the WebApp with a "Подробнее" button to open the full Obsidian note.

## Report Contents

- Crypto Radar (portfolio, market, signals)
- System Status (Docker, disk, memory)
- Alerts (cron errors)
- Inbox summary
- Today's calendar

## A2UI Button

The skill creates a WebApp button with the URL to the Obsidian note:
- Text: "📖 Подробнее"
- URL: Opens the Obsidian note in Obsidian Web or copies link to clipboard
