#!/bin/bash
# telegram_monitor.sh — Fetch posts from Telegram channels and create digest

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment (only valid vars)
if [ -f "/data/bot/openclaw-docker/.env" ]; then
    export TELEGRAM_API_ID=$(grep '^TELEGRAM_API_ID=' /data/bot/openclaw-docker/.env | cut -d'=' -f2)
    export TELEGRAM_API_HASH=$(grep '^TELEGRAM_API_HASH=' /data/bot/openclaw-docker/.env | cut -d'=' -f2)
fi

# Run Python script
python3 << 'PYEOF'
import os
import sys
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import Message

API_ID = int(os.environ.get('TELEGRAM_API_ID', 0))
API_HASH = os.environ.get('TELEGRAM_API_HASH', '')
# Reuse session from telegram_reader userbot (override with TELEGRAM_SESSION_PATH env var)
SESSION_NAME = os.environ.get('TELEGRAM_SESSION_PATH', '/data/bot/openclaw-docker/workspace/telegram/session')

# Channels to monitor (from README.md)
CHANNELS = [
    ('ainews', 'AI новости'),
    ('technews', 'Техно новости'),
    ('Theedinorogblog', 'AI/Tech блог'),
    ('fichism', 'Fichman blog'),
    ('productdo', 'Product do'),
    ('fanat_servisa', 'Fanat Servisa'),
    ('hardclient', 'Hard Client'),
]

# Auto-channels (новостные/автоматические каналы)
AUTO_CHANNELS = [
    ('Eng_Arzoni_Uz', 'Eng Arzoni'),
    ('humouz', 'HUMO Uz'),
]

OUTPUT_DIR = '/data/obsidian/vault/Telegram'
OUTPUT_FILE = f"{OUTPUT_DIR}/Digest_{datetime.now().strftime('%Y-%m-%d')}.md"

async def main():
    if not API_ID or not API_HASH:
        print("❌ TELEGRAM_API_ID or TELEGRAM_API_HASH not set")
        sys.exit(1)
    
    # Check if session file exists
    session_file = f"{SESSION_NAME}.session"
    if not os.path.exists(session_file):
        print(f"❌ Session file not found: {session_file}")
        print("   Run: docker compose exec openclaw python3 -m telethon.sync")
        sys.exit(1)
    
    print(f"✓ Using session: {SESSION_NAME}")
    print(f"✓ Session file exists: {session_file}")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Not authorized. Session invalid or expired.")
            sys.exit(1)
        print("✓ Connected and authorized")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    digest = f"# Дайджест Telegram — {datetime.now().strftime('%Y-%m-%d')}\n\n"
    digest += f"**Создан:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
    digest += "---\n\n"
    
    total_channels = 0
    total_posts = 0
    
    # Process main channels
    for channel_username, channel_desc in CHANNELS:
        try:
            channel = await client.get_entity(f'@{channel_username}')
            total_channels += 1
            
            # Get last 10 posts
            posts = await client.get_messages(channel, limit=10)
            
            channel_posts = []
            for msg in posts[:5]:  # Max 5 posts per channel
                if not msg.text or len(msg.text) < 20:
                    continue
                
                # Skip posts older than 24h
                if msg.date and msg.date.timestamp() < (datetime.now().timestamp() - 86400):
                    continue
                
                text = msg.text.replace('\n', ' ')[:200]
                link = f"https://t.me/{channel_username}/{msg.id}"
                channel_posts.append(f"- [{text[:100]}...]({link})")
            
            if channel_posts:
                digest += f"## 📢 {channel_desc} (@{channel_username})\n\n"
                digest += '\n'.join(channel_posts) + '\n\n'
                total_posts += len(channel_posts)
                
        except Exception as e:
            digest += f"## ❌ @{channel_username} — Error: {str(e)[:100]}\n\n"
    
    # Process auto-channels (новостные/автоматические)
    auto_channel_posts = 0
    for channel_username, channel_desc in AUTO_CHANNELS:
        try:
            channel = await client.get_entity(f'@{channel_username}')
            total_channels += 1
            
            # Get last 5 posts only for auto-channels
            posts = await client.get_messages(channel, limit=5)
            
            channel_posts = []
            for msg in posts[:3]:  # Max 3 posts per auto-channel
                if not msg.text or len(msg.text) < 10:
                    continue
                
                # Skip posts older than 24h
                if msg.date and msg.date.timestamp() < (datetime.now().timestamp() - 86400):
                    continue
                
                text = msg.text.replace('\n', ' ')[:150]
                link = f"https://t.me/{channel_username}/{msg.id}"
                channel_posts.append(f"- [{text[:80]}...]({link})")
            
            if channel_posts:
                if auto_channel_posts == 0:
                    digest += "## 📰 Авто-каналы\n\n"
                digest += f"### {channel_desc} (@{channel_username})\n\n"
                digest += '\n'.join(channel_posts) + '\n\n'
                auto_channel_posts += len(channel_posts)
                total_posts += len(channel_posts)
                
        except Exception as e:
            digest += f"### ❌ @{channel_username} — Error: {str(e)[:100]}\n\n"
    
    # Summary
    digest += "---\n\n"
    digest += f"**Итого:**\n"
    digest += f"- Проверено каналов: {total_channels}\n"
    digest += f"- Найдено постов: {total_posts}\n"
    
    # Write file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(digest)
    
    print(f"✅ Digest created: {OUTPUT_FILE}")
    print(f"   Channels: {total_channels}, Posts: {total_posts}")
    
    try:
        await client.disconnect()
        print("✓ Disconnected")
    except Exception as e:
        print(f"⚠️ Disconnect warning: {e}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
PYEOF
