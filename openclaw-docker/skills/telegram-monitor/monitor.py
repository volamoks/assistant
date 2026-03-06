#!/usr/bin/env python3
"""
Telegram Channel Monitor

Monitors Telegram channels from a list in Obsidian and creates daily digests
with interesting posts based on AI, tech, and useful content.

Features:
    - Reads channel list from Obsidian vault
    - Fetches recent posts using Telegram MTProto API
    - Evaluates post interestingness using keyword matching
    - Creates daily digest markdown files
    - Sends summary notification via Telegram bot

Usage:
    python3 monitor.py [--channels PATH] [--output DIR] [--limit N] [--notify]

Environment Variables:
    TELEGRAM_API_ID: Telegram API ID (required for MTProto)
    TELEGRAM_API_HASH: Telegram API hash (required for MTProto)
    TELEGRAM_BOT_TOKEN: Bot token for notifications (optional)
    TELEGRAM_CHAT_ID: Chat ID for notifications (optional)
    OBSIDIAN_VAULT: Path to Obsidian vault (default: /data/obsidian/vault)
"""

import os
import sys
import re
import json
import argparse
import asyncio
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse


# Interesting content keywords
INTERESTING_KEYWORDS = {
    # AI/ML
    'ai', 'artificial intelligence', 'machine learning', 'deep learning',
    'neural network', 'llm', 'transformer', 'gpt', 'llama', 'qwen',
    'diffusion', 'stable diffusion', 'midjourney', 'copilot',
    'generative ai', 'agentic', 'agent', 'automation',
    
    # Tech/Programming
    'python', 'javascript', 'typescript', 'rust', 'go', 'kubernetes',
    'docker', 'cloud', 'aws', 'azure', 'gcp', 'devops', 'ci/cd',
    'api', 'microservice', 'serverless', 'frontend', 'backend',
    'react', 'vue', 'angular', 'nodejs', 'fastapi', 'django',
    'github', 'gitlab', 'opensource', 'repository',
    
    # Useful/Tech News
    'tutorial', 'guide', 'howto', 'how-to', 'tips', 'tricks',
    'release', 'update', 'new feature', 'announcement',
    'security', 'vulnerability', 'patch', 'exploit',
    'performance', 'optimization', 'benchmark',
    
    # Crypto/Finance (optional)
    'crypto', 'bitcoin', 'ethereum', 'defi', 'blockchain',
    'trading', 'market', 'analysis',
}

# Keywords to filter out (noise)
FILTER_KEYWORDS = {
    'ad', 'advertisement', 'sponsor', 'promo', 'promotion',
    'giveaway', 'contest', 'win', 'free', 'discount',
    'click here', 'subscribe', 'follow', 'share',
    '🎁', '🎉', '💰', '🚀', '📈',
}


class ChannelReader:
    """Reads channel list from Obsidian vault."""
    
    def __init__(self, vault_path: str = "/data/obsidian/vault"):
        self.vault_path = Path(vault_path)
        self.channels_file = self.vault_path / "Telegram" / "Channels" / "README.md"
    
    def read_channels(self) -> List[Dict[str, Any]]:
        """
        Read channel list from README.md.
        
        Expected format:
        # Telegram Channels
        
        | Channel | Description | Priority |
        |---------|-------------|----------|
        | @channel1 | Description | high |
        | @channel2 | Description | medium |
        
        Returns:
            List of channel dicts with username, description, priority.
        """
        if not self.channels_file.exists():
            print(f"Warning: Channels file not found: {self.channels_file}", file=sys.stderr)
            return []
        
        channels = []
        content = self.channels_file.read_text(encoding='utf-8')
        
        # Parse markdown table
        in_table = False
        header_parsed = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Detect table start
            if line.startswith('|') and not in_table:
                in_table = True
                continue
            
            # Skip separator line
            if in_table and not header_parsed:
                if re.match(r'^\|[\s\-:|]+\|$', line):
                    header_parsed = True
                continue
            
            # Parse table rows
            if in_table and header_parsed:
                if line.startswith('|'):
                    parts = line.split('|')
                    if len(parts) >= 3:
                        channel_name = parts[1].strip()
                        description = parts[2].strip() if len(parts) > 2 else ""
                        priority = parts[3].strip() if len(parts) > 3 else "medium"
                        
                        if channel_name and channel_name.startswith('@'):
                            channels.append({
                                'username': channel_name.lstrip('@'),
                                'description': description,
                                'priority': priority
                            })
                else:
                    # End of table
                    break
        
        return channels


class TelegramFetcher:
    """Fetches posts from Telegram channels using MTProto."""
    
    def __init__(self, api_id: str, api_hash: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = None
    
    async def __aenter__(self):
        """Initialize Telegram client."""
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            
            # Create client
            self.client = TelegramClient(
                StringSession(),
                self.api_id,
                self.api_hash
            )
            await self.client.start()
            return self
        except ImportError:
            print("Warning: telethon not installed. Install with: pip install telethon", file=sys.stderr)
            return None
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup Telegram client."""
        if self.client:
            await self.client.disconnect()
    
    async def fetch_posts(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch recent posts from a channel.
        
        Args:
            username: Channel username (without @).
            limit: Number of posts to fetch.
        
        Returns:
            List of post dicts with id, text, date, link, views.
        """
        if not self.client:
            return []
        
        try:
            from telethon import utils
            from telethon.tl.types import Message
            
            # Get channel entity
            entity = await self.client.get_entity(f"@{username}")
            
            posts = []
            async for message in self.client.iter_messages(entity, limit=limit):
                if not isinstance(message, Message):
                    continue
                
                # Skip messages without content
                if not message.message and not message.media:
                    continue
                
                # Extract post data
                post = {
                    'id': message.id,
                    'text': message.message or "",
                    'date': message.date.isoformat() if message.date else None,
                    'link': f"https://t.me/{username}/{message.id}",
                    'views': getattr(message, 'views', 0),
                    'forwards': getattr(message, 'forwards', 0),
                    'has_media': bool(message.media),
                    'channel': username,
                }
                posts.append(post)
            
            return posts
        
        except Exception as e:
            print(f"Error fetching posts from @{username}: {e}", file=sys.stderr)
            return []


class PostEvaluator:
    """Evaluates post interestingness."""
    
    def __init__(self):
        self.interesting_keywords = INTERESTING_KEYWORDS
        self.filter_keywords = FILTER_KEYWORDS
    
    def is_interesting(self, text: str) -> Tuple[bool, List[str]]:
        """
        Evaluate if a post is interesting.
        
        Args:
            text: Post text content.
        
        Returns:
            Tuple of (is_interesting, matched_keywords).
        """
        if not text:
            return False, []
        
        text_lower = text.lower()
        
        # Check for filter keywords (noise)
        for keyword in self.filter_keywords:
            if keyword.lower() in text_lower:
                return False, []
        
        # Find matching interesting keywords
        matched = []
        for keyword in self.interesting_keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)
        
        return len(matched) > 0, matched
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """
        Generate a brief summary of the post.
        
        Args:
            text: Full post text.
            max_length: Maximum summary length.
        
        Returns:
            Truncated summary text.
        """
        if not text:
            return "[No text content]"
        
        # Remove URLs for cleaner summary
        clean_text = re.sub(r'https?://\S+', '', text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        if len(clean_text) <= max_length:
            return clean_text
        
        # Truncate at word boundary
        truncated = clean_text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def extract_title(self, text: str) -> str:
        """
        Extract a title from post text.
        
        Args:
            text: Full post text.
        
        Returns:
            Title string.
        """
        if not text:
            return "[No title]"
        
        # Try to get first line as title
        first_line = text.split('\n')[0].strip()
        
        # Remove leading special characters
        first_line = re.sub(r'^[#*\-]+\s*', '', first_line)
        
        if len(first_line) > 100:
            first_line = first_line[:97] + "..."
        
        return first_line if first_line else "[No title]"


class DigestCreator:
    """Creates daily digest markdown files."""
    
    def __init__(self, output_dir: str = "/data/obsidian/vault/Telegram"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_digest(
        self,
        posts: List[Dict[str, Any]],
        channels_checked: int,
        digest_date: Optional[date] = None
    ) -> str:
        """
        Create a daily digest markdown file.
        
        Args:
            posts: List of interesting posts.
            channels_checked: Total number of channels checked.
            digest_date: Date for digest (default: today).
        
        Returns:
            Path to created digest file.
        """
        if digest_date is None:
            digest_date = date.today()
        
        filename = f"Digest_{digest_date.strftime('%Y-%m-%d')}.md"
        filepath = self.output_dir / filename
        
        # Group posts by channel
        posts_by_channel: Dict[str, List[Dict[str, Any]]] = {}
        for post in posts:
            channel = post.get('channel', 'unknown')
            if channel not in posts_by_channel:
                posts_by_channel[channel] = []
            posts_by_channel[channel].append(post)
        
        # Generate markdown content
        content = self._generate_markdown(
            posts_by_channel,
            channels_checked,
            digest_date
        )
        
        # Write file
        filepath.write_text(content, encoding='utf-8')
        
        return str(filepath)
    
    def _generate_markdown(
        self,
        posts_by_channel: Dict[str, List[Dict[str, Any]]],
        channels_checked: int,
        digest_date: date
    ) -> str:
        """Generate markdown content for digest."""
        lines = [
            f"# Дайджест Telegram — {digest_date.strftime('%Y-%m-%d')}",
            "",
            f"*Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Интересные посты",
            "",
        ]
        
        if not posts_by_channel:
            lines.append("*Нет интересных постов за сегодня.*")
            lines.append("")
        else:
            # Sort channels by name
            for channel in sorted(posts_by_channel.keys()):
                channel_posts = posts_by_channel[channel]
                lines.append(f"### Канал: @{channel}")
                lines.append("")
                
                for post in channel_posts:
                    title = post.get('title', '[No title]')
                    link = post.get('link', '')
                    summary = post.get('summary', '')
                    matched = post.get('matched_keywords', [])
                    views = post.get('views', 0)
                    
                    # Format: - [Title](link) — summary
                    line = f"- [{title}]({link}) — {summary}"
                    lines.append(line)
                    
                    # Add metadata
                    meta = []
                    if matched:
                        meta.append(f"🏷️ {', '.join(matched[:5])}")
                    if views:
                        meta.append(f"👁️ {views:,}")
                    if meta:
                        lines.append(f"  *{' | '.join(meta)}*")
                
                lines.append("")
        
        # Summary section
        lines.append("## Резюме")
        lines.append("")
        lines.append(f"- Всего проверено: {channels_checked} каналов")
        lines.append(f"- Интересных постов: {len(posts_by_channel)}")
        lines.append("")
        
        # Tags
        lines.append("---")
        lines.append("tags: [telegram, digest, daily]")
        lines.append(f"date: {digest_date.strftime('%Y-%m-%d')}")
        
        return '\n'.join(lines)


class TelegramMonitor:
    """Main monitor orchestrator."""
    
    def __init__(
        self,
        vault_path: str = "/data/obsidian/vault",
        output_dir: str = "/data/obsidian/vault/Telegram",
        api_id: Optional[str] = None,
        api_hash: Optional[str] = None,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        self.vault_path = vault_path
        self.output_dir = output_dir
        self.api_id = api_id or os.environ.get("TELEGRAM_API_ID")
        self.api_hash = api_hash or os.environ.get("TELEGRAM_API_HASH")
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        
        self.channel_reader = ChannelReader(vault_path)
        self.digest_creator = DigestCreator(output_dir)
        self.evaluator = PostEvaluator()
    
    async def run(
        self,
        limit: int = 10,
        send_notification: bool = True
    ) -> Dict[str, Any]:
        """
        Run the monitor.
        
        Args:
            limit: Posts to fetch per channel.
            send_notification: Whether to send summary notification.
        
        Returns:
            Result dict with stats and paths.
        """
        result = {
            'success': False,
            'channels_checked': 0,
            'posts_fetched': 0,
            'interesting_posts': 0,
            'digest_file': None,
            'notification_sent': False,
            'errors': []
        }
        
        # Read channel list
        channels = self.channel_reader.read_channels()
        if not channels:
            result['errors'].append("No channels found in channel list")
            return result
        
        result['channels_checked'] = len(channels)
        print(f"Found {len(channels)} channels to monitor")
        
        # Check API credentials
        if not self.api_id or not self.api_hash:
            result['errors'].append("TELEGRAM_API_ID and TELEGRAM_API_HASH required")
            return result
        
        # Fetch and evaluate posts
        interesting_posts = []
        
        async with TelegramFetcher(self.api_id, self.api_hash) as fetcher:
            if not fetcher:
                result['errors'].append("Failed to initialize Telegram client")
                return result
            
            for channel in channels:
                username = channel['username']
                print(f"Fetching posts from @{username}...")
                
                posts = await fetcher.fetch_posts(username, limit)
                result['posts_fetched'] += len(posts)
                
                # Evaluate each post
                for post in posts:
                    is_interesting, matched = self.evaluator.is_interesting(post['text'])
                    if is_interesting:
                        post['title'] = self.evaluator.extract_title(post['text'])
                        post['summary'] = self.evaluator.generate_summary(post['text'])
                        post['matched_keywords'] = matched
                        interesting_posts.append(post)
        
        result['interesting_posts'] = len(interesting_posts)
        print(f"Found {len(interesting_posts)} interesting posts")
        
        # Create digest
        if interesting_posts or True:  # Always create digest even if empty
            digest_path = self.digest_creator.create_digest(
                interesting_posts,
                result['channels_checked']
            )
            result['digest_file'] = digest_path
            print(f"Created digest: {digest_path}")
        
        # Send notification
        if send_notification and self.bot_token and self.chat_id:
            notification_sent = self._send_notification(result)
            result['notification_sent'] = notification_sent
        
        result['success'] = True
        return result
    
    def _send_notification(self, result: Dict[str, Any]) -> bool:
        """Send summary notification via Telegram bot."""
        try:
            # Import notify module
            sys.path.insert(0, str(Path(__file__).parent.parent / 'telegram'))
            from notify import TelegramNotifier
            
            notifier = TelegramNotifier(
                bot_token=self.bot_token,
                chat_id=self.chat_id
            )
            
            # Format summary
            emoji = "📊" if result['interesting_posts'] == 0 else "🔥"
            summary = (
                f"{emoji} *Telegram Digest*\n\n"
                f"Проверено {result['channels_checked']} каналов\n"
                f"Найдено {result['interesting_posts']} интересных постов\n\n"
                f"📁 Файл: `{Path(result['digest_file']).name}`"
            )
            
            response = notifier.send(summary)
            return response is not None and response.get('ok', False)
        
        except Exception as e:
            print(f"Failed to send notification: {e}", file=sys.stderr)
            return False


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Telegram Channel Monitor - Create daily digests from Telegram channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with default settings
    python3 monitor.py

    # Custom channel list and output
    python3 monitor.py --channels /path/to/channels.md --output /path/to/digests

    # Fetch more posts per channel
    python3 monitor.py --limit 20

    # Run without notification
    python3 monitor.py --no-notify

Environment Variables:
    TELEGRAM_API_ID: Telegram API ID (required)
    TELEGRAM_API_HASH: Telegram API hash (required)
    TELEGRAM_BOT_TOKEN: Bot token for notifications (optional)
    TELEGRAM_CHAT_ID: Chat ID for notifications (optional)
    OBSIDIAN_VAULT: Path to Obsidian vault (default: /data/obsidian/vault)
        """
    )
    
    parser.add_argument(
        "--channels", "-c",
        default="/data/obsidian/vault/Telegram/Channels/README.md",
        help="Path to channel list file"
    )
    parser.add_argument(
        "--output", "-o",
        default="/data/obsidian/vault/Telegram",
        help="Output directory for digest files"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Number of posts to fetch per channel"
    )
    parser.add_argument(
        "--vault", "-v",
        default="/data/obsidian/vault",
        help="Path to Obsidian vault"
    )
    parser.add_argument(
        "--api-id",
        help="Telegram API ID (overrides env)"
    )
    parser.add_argument(
        "--api-hash",
        help="Telegram API hash (overrides env)"
    )
    parser.add_argument(
        "--bot-token",
        help="Telegram bot token (overrides env)"
    )
    parser.add_argument(
        "--chat-id",
        help="Telegram chat ID for notifications (overrides env)"
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Disable notification sending"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON"
    )
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = TelegramMonitor(
        vault_path=args.vault,
        output_dir=args.output,
        api_id=args.api_id,
        api_hash=args.api_hash,
        bot_token=args.bot_token,
        chat_id=args.chat_id
    )
    
    # Run monitor
    result = asyncio.run(monitor.run(
        limit=args.limit,
        send_notification=not args.no_notify
    ))
    
    # Output result
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result['success']:
            print(f"\n✅ Monitor completed successfully")
            print(f"   Channels checked: {result['channels_checked']}")
            print(f"   Posts fetched: {result['posts_fetched']}")
            print(f"   Interesting posts: {result['interesting_posts']}")
            print(f"   Digest file: {result['digest_file']}")
            if result['notification_sent']:
                print(f"   Notification: sent")
        else:
            print(f"\n❌ Monitor failed")
            for error in result['errors']:
                print(f"   Error: {error}")
            sys.exit(1)


if __name__ == "__main__":
    main()
