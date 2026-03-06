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

Ежедневно проверяет Telegram каналы из списка в Obsidian и создаёт дайджест с интересными постами.

## Installation

1. Install the Telethon library (required for MTProto API):
   ```bash
   pip install telethon
   ```

2. Set up environment variables in `.env`:
   ```bash
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_BOT_TOKEN=your_bot_token  # For notifications
   TELEGRAM_CHAT_ID=your_chat_id      # For notifications
   ```

## Usage

### Basic Usage

```bash
python3 openclaw-docker/skills/telegram-monitor/monitor.py
```

### Command Line Options

```bash
# Custom output directory
python3 monitor.py --output /path/to/digests

# Fetch more posts per channel
python3 monitor.py --limit 20

# Run without sending notification
python3 monitor.py --no-notify

# Output result as JSON
python3 monitor.py --json

# Full example
python3 monitor.py \
    --vault /data/obsidian/vault \
    --output /data/obsidian/vault/Telegram \
    --limit 15 \
    --api-id $TELEGRAM_API_ID \
    --api-hash $TELEGRAM_API_HASH
```

### As Python Module

```python
import asyncio
from telegram_monitor.monitor import TelegramMonitor

async def run_monitor():
    monitor = TelegramMonitor(
        vault_path="/data/obsidian/vault",
        output_dir="/data/obsidian/vault/Telegram"
    )
    result = await monitor.run(limit=10, send_notification=True)
    print(f"Checked {result['channels_checked']} channels")
    print(f"Found {result['interesting_posts']} interesting posts")

asyncio.run(run_monitor())
```

## Workflow

1. **Read channel list** from `/data/obsidian/vault/Telegram/Channels/README.md`

   Expected format (markdown table):
   ```markdown
   # Telegram Channels

   | Channel | Description | Priority |
   |---------|-------------|----------|
   | @channel1 | AI News | high |
   | @channel2 | Tech Blog | medium |
   ```

2. **For each channel:**
   - Fetch last N posts (default: 10) via Telegram MTProto API
   - Evaluate interestingness (AI, tech, useful content)
   - Filter out ads, promotions, and noise

3. **Create digest file** at `/data/obsidian/vault/Telegram/Digest_YYYY-MM-DD.md`

   Format:
   ```markdown
   # Дайджест Telegram — 2024-01-15

   *Создано: 2024-01-15 08:00:00*

   ## Интересные посты

   ### Канал: @channel_name
   - [Post Title](https://t.me/channel/123) — Brief summary...
     *🏷️ ai, machine learning | 👁️ 1,234*

   ## Резюме

   - Всего проверено: 10 каналов
   - Интересных постов: 5

   ---
   tags: [telegram, digest, daily]
   date: 2024-01-15
   ```

4. **Send summary notification** via Telegram bot:
   ```
   🔥 Telegram Digest

   Проверено 10 каналов
   Найдено 5 интересных постов

   📁 Файл: Digest_2024-01-15.md
   ```

## Interestingness Criteria

Posts are evaluated based on keyword matching:

### Interesting Topics (included)
- **AI/ML**: ai, machine learning, llm, neural network, gpt, llama, etc.
- **Tech/Programming**: python, javascript, docker, kubernetes, api, etc.
- **Useful Content**: tutorial, guide, tips, release, announcement, etc.
- **Crypto/Finance**: bitcoin, ethereum, defi, trading, analysis, etc.

### Filtered Out (noise)
- Advertisements, sponsors, promotions
- Giveaways, contests
- Clickbait ("click here", "subscribe")
- Excessive emoji spam

## Getting Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Click "API development tools"
4. Create a new application:
   - App title: Any name (e.g., "Telegram Monitor")
   - Short name: Short identifier
   - Platform: Desktop
5. Copy `API_ID` and `API_HASH` to your `.env`

**Note**: These credentials are for reading public channel posts only. No user account access needed.

## Scheduling

Add to your crontab for daily execution:
```bash
# Run daily at 8:00 AM
0 8 * * * cd /path/to/openclaw-docker && python3 skills/telegram-monitor/monitor.py --no-notify
```

Or use the existing job script at `scripts/jobs/telegram_monitor.sh`.

## Troubleshooting

### "telethon not installed"
```bash
pip install telethon
```

### "TELEGRAM_API_ID and TELEGRAM_API_HASH required"
Set the environment variables in your `.env` file or pass them via CLI flags.

### "No channels found"
Ensure the channel list file exists at `/data/obsidian/vault/Telegram/Channels/README.md` with proper markdown table format.

### "Failed to initialize Telegram client"
Check that your API credentials are valid and you have internet connectivity.
