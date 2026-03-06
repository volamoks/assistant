"""
Telegram Monitor Skill

Monitors Telegram channels from a list in Obsidian and creates daily digests
with interesting posts based on AI, tech, and useful content.
"""

from .monitor import (
    TelegramMonitor,
    ChannelReader,
    TelegramFetcher,
    PostEvaluator,
    DigestCreator,
    INTERESTING_KEYWORDS,
    FILTER_KEYWORDS,
)

__all__ = [
    "TelegramMonitor",
    "ChannelReader",
    "TelegramFetcher",
    "PostEvaluator",
    "DigestCreator",
    "INTERESTING_KEYWORDS",
    "FILTER_KEYWORDS",
]
