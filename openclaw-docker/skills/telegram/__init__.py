"""
Telegram Notification Module for OpenClaw

Unified, isolated Telegram notification system with inline keyboard support.
Can be used by any tool, agent, cron job, or script.

Components:
    - notify.py: Main notification client
    - callback_handler.py: Callback query handler with pluggable actions

Example:
    from telegram.notify import TelegramNotifier
    
    notifier = TelegramNotifier()
    notifier.send(
        "Hello!",
        buttons="✅ Yes:confirm,No:cancel"
    )
"""

from .notify import TelegramNotifier
from .callback_handler import CallbackHandler

__all__ = ["TelegramNotifier", "CallbackHandler"]
