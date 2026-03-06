#!/usr/bin/env python3
"""
User Feedback System for Crypto Signals

Handles user feedback on signals:
- Process feedback commands from Telegram
- Store user preferences
- Adjust signal thresholds based on feedback
- Learn from user reactions

Commands:
- /feedback [signal_id] [result] - Mark signal as positive/negative/neutral
- /stats - Show user statistics
- /signal [id] - Get details of a specific signal
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, '/home/node/.openclaw/skills')

from signal_tracker import SignalTracker, Signal


# ── Configuration ──────────────────────────────────────────────────────────────

USER_DATA_PATH = Path("/home/node/.openclaw/skills/crypto_monitor/data/user_feedback.json")
DEFAULT_THRESHOLD_ADJUSTMENT = 0.1  # 10% adjustment per feedback


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class UserPreference:
    """User preference for signal handling."""
    user_id: str
    preferred_signal_types: List[str] = field(default_factory=list)
    avoided_signal_types: List[str] = field(default_factory=list)
    threshold_adjustments: Dict[str, float] = field(default_factory=dict)  # signal_type -> adjustment
    notification_enabled: bool = True
    min_confidence: float = 0.3
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'preferred_signal_types': self.preferred_signal_types,
            'avoided_signal_types': self.avoided_signal_types,
            'threshold_adjustments': self.threshold_adjustments,
            'notification_enabled': self.notification_enabled,
            'min_confidence': self.min_confidence,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserPreference':
        return cls(**data)


@dataclass
class FeedbackRecord:
    """Record of user feedback on a signal."""
    id: str
    user_id: str
    signal_id: str
    reaction: str  # positive, negative, neutral
    timestamp: str
    note: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'signal_id': self.signal_id,
            'reaction': self.reaction,
            'timestamp': self.timestamp,
            'note': self.note
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FeedbackRecord':
        return cls(**data)


# ── User Feedback Class ───────────────────────────────────────────────────────

class UserFeedback:
    """
    User feedback processing system.
    
    Handles:
    - Processing feedback commands
    - Storing user preferences
    - Adjusting signal thresholds based on feedback
    - Providing personalized recommendations
    """
    
    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize user feedback system.
        
        Args:
            data_path: Path to user data storage
        """
        self.data_path = data_path or USER_DATA_PATH
        self.signal_tracker = SignalTracker()
        
        # User preferences: user_id -> UserPreference
        self.preferences: Dict[str, UserPreference] = {}
        
        # Feedback records
        self.feedback_records: List[FeedbackRecord] = []
        
        # Load existing data
        self._load_data()
    
    def _load_data(self):
        """Load user data from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    
                    self.preferences = {
                        uid: UserPreference.from_dict(p)
                        for uid, p in data.get('preferences', {}).items()
                    }
                    
                    self.feedback_records = [
                        FeedbackRecord.from_dict(r)
                        for r in data.get('feedback_records', [])
                    ]
            except (json.JSONDecodeError, IOError) as e:
                print(f"[UserFeedback] Could not load data: {e}")
    
    def _save_data(self):
        """Save user data to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.data_path, 'w') as f:
                json.dump({
                    'preferences': {
                        uid: p.to_dict()
                        for uid, p in self.preferences.items()
                    },
                    'feedback_records': [r.to_dict() for r in self.feedback_records],
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2)
        except IOError as e:
            print(f"[UserFeedback] Could not save data: {e}")
    
    # ── Core Methods ───────────────────────────────────────────────────────────
    
    def process_feedback(
        self,
        user_id: str,
        signal_id: str,
        result: str,
        note: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Process user feedback on a signal.
        
        Args:
            user_id: User ID
            signal_id: Signal ID
            result: Reaction (positive, negative, neutral)
            note: Optional note from user
        
        Returns:
            Tuple of (success, message)
        """
        # Validate reaction
        result = result.lower()
        if result not in ['positive', 'negative', 'neutral', 'success', 'failed', 'works', 'no work']:
            return (False, f"Invalid result: {result}. Use: positive/negative/neutral")
        
        # Normalize result
        if result in ['success', 'works']:
            result = 'positive'
        elif result in ['failed', 'no work']:
            result = 'negative'
        
        # Check if signal exists
        signal = self.signal_tracker.get_signal(signal_id)
        if not signal:
            return (False, f"Signal not found: {signal_id}")
        
        # Create feedback record
        feedback_id = f"fb_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id[:8]}"
        
        feedback = FeedbackRecord(
            id=feedback_id,
            user_id=user_id,
            signal_id=signal_id,
            reaction=result,
            timestamp=datetime.now().isoformat(),
            note=note
        )
        
        self.feedback_records.append(feedback)
        
        # Update signal's user reaction
        self.signal_tracker.set_user_reaction(signal_id, result)
        
        # Update user preferences based on feedback
        self._update_preferences_from_feedback(user_id, signal, result)
        
        self._save_data()
        
        return (True, f"Feedback recorded: {result} for signal {signal_id}")
    
    def _update_preferences_from_feedback(
        self,
        user_id: str,
        signal: Signal,
        reaction: str
    ):
        """Update user preferences based on feedback."""
        # Get or create user preference
        if user_id not in self.preferences:
            self.preferences[user_id] = UserPreference(user_id=user_id)
        
        pref = self.preferences[user_id]
        
        # Update based on reaction
        if reaction == 'positive':
            # Add to preferred if not already there
            if signal.type not in pref.preferred_signal_types:
                pref.preferred_signal_types.append(signal.type)
            
            # Remove from avoided
            if signal.type in pref.avoided_signal_types:
                pref.avoided_signal_types.remove(signal.type)
            
            # Adjust threshold positively
            current_adj = pref.threshold_adjustments.get(signal.type, 0.0)
            pref.threshold_adjustments[signal.type] = min(current_adj + 0.05, 0.5)
        
        elif reaction == 'negative':
            # Add to avoided if not already there
            if signal.type not in pref.avoided_signal_types:
                pref.avoided_signal_types.append(signal.type)
            
            # Remove from preferred
            if signal.type in pref.preferred_signal_types:
                pref.preferred_signal_types.remove(signal.type)
            
            # Adjust threshold negatively
            current_adj = pref.threshold_adjustments.get(signal.type, 0.0)
            pref.threshold_adjustments[signal.type] = max(current_adj - 0.05, -0.5)
        
        pref.updated_at = datetime.now().isoformat()
    
    def get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """
        Get user preferences.
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with preferences or None if user not found
        """
        if user_id not in self.preferences:
            return None
        
        return self.preferences[user_id].to_dict()
    
    def get_or_create_preferences(self, user_id: str) -> UserPreference:
        """Get or create user preferences."""
        if user_id not in self.preferences:
            self.preferences[user_id] = UserPreference(user_id=user_id)
            self._save_data()
        
        return self.preferences[user_id]
    
    def adjust_signal_thresholds(
        self,
        user_id: str,
        signal_type: str,
        adjustment: float
    ) -> float:
        """
        Adjust threshold for a signal type.
        
        Args:
            user_id: User ID
            signal_type: Signal type to adjust
            adjustment: Adjustment value (-0.5 to 0.5)
        
        Returns:
            New threshold adjustment
        """
        pref = self.get_or_create_preferences(user_id)
        
        # Clamp adjustment
        adjustment = max(-0.5, min(0.5, adjustment))
        
        pref.threshold_adjustments[signal_type] = adjustment
        pref.updated_at = datetime.now().isoformat()
        
        self._save_data()
        
        return adjustment
    
    def get_adjusted_confidence(
        self,
        user_id: str,
        signal: Signal
    ) -> float:
        """
        Get confidence adjusted for user preferences.
        
        Args:
            user_id: User ID
            signal: Signal to adjust
        
        Returns:
            Adjusted confidence value
        """
        pref = self.get_or_create_preferences(user_id)
        
        # Start with original confidence
        adjusted_confidence = signal.confidence
        
        # Apply threshold adjustment
        adjustment = pref.threshold_adjustments.get(signal.type, 0.0)
        adjusted_confidence += adjustment
        
        # Ensure within bounds
        return max(0.0, min(1.0, adjusted_confidence))
    
    def should_notify_user(
        self,
        user_id: str,
        signal: Signal
    ) -> Tuple[bool, str]:
        """
        Determine if user should be notified about a signal.
        
        Args:
            user_id: User ID
            signal: Signal to check
        
        Returns:
            Tuple of (should_notify, reason)
        """
        pref = self.get_or_create_preferences(user_id)
        
        # Check if notifications are enabled
        if not pref.notification_enabled:
            return (False, "Notifications disabled")
        
        # Check if signal type is avoided
        if signal.type in pref.avoided_signal_types:
            return (False, f"Signal type {signal.type} is in avoid list")
        
        # Check minimum confidence
        adjusted_confidence = self.get_adjusted_confidence(user_id, signal)
        if adjusted_confidence < pref.min_confidence:
            return (False, f"Confidence {adjusted_confidence:.2f} below minimum {pref.min_confidence}")
        
        # All checks passed
        return (True, "Signal passed all filters")
    
    # ── Telegram Command Processing ────────────────────────────────────────────
    
    def process_command(
        self,
        user_id: str,
        command: str,
        args: List[str]
    ) -> Tuple[str, bool]:
        """
        Process a Telegram command.
        
        Args:
            user_id: User ID
            command: Command name
            args: Command arguments
        
        Returns:
            Tuple of (response_message, is_error)
        """
        command = command.lower().strip()
        
        if command == '/feedback':
            return self._cmd_feedback(user_id, args)
        
        elif command in ['/stats', '/statistics']:
            return self._cmd_stats(user_id)
        
        elif command in ['/signal', '/sig']:
            return self._cmd_signal(user_id, args)
        
        elif command == '/preferences':
            return self._cmd_preferences(user_id)
        
        elif command == '/notify':
            return self._cmd_notify(user_id, args)
        
        elif command == '/minconfidence':
            return self._cmd_min_confidence(user_id, args)
        
        else:
            return (f"Unknown command: {command}\n\n"
                   "Available commands:\n"
                   "/feedback [signal_id] [result] - Mark signal as positive/negative\n"
                   "/stats - Your statistics\n"
                   "/signal [id] - Signal details\n"
                   "/preferences - Your preferences\n"
                   "/notify on|off - Toggle notifications\n"
                   "/minconfidence [0.0-1.0] - Set minimum confidence", True)
    
    def _cmd_feedback(
        self,
        user_id: str,
        args: List[str]
    ) -> Tuple[str, bool]:
        """Process /feedback command."""
        if len(args) < 2:
            return ("Usage: /feedback [signal_id] [result]\n\n"
                   "Example: /feedback sig_20240305_0815_BTC_SPIKE positive\n"
                   "Result options: positive, negative, neutral", True)
        
        signal_id = args[0]
        result = args[1]
        
        success, message = self.process_feedback(user_id, signal_id, result)
        
        return (message, not success)
    
    def _cmd_stats(self, user_id: str) -> Tuple[str, bool]:
        """Process /stats command."""
        # Get user's feedback
        user_feedback = [f for f in self.feedback_records if f.user_id == user_id]
        
        if not user_feedback:
            return ("No feedback yet. Use /feedback to rate signals!", False)
        
        # Count reactions
        reactions = {'positive': 0, 'negative': 0, 'neutral': 0}
        for fb in user_feedback:
            reactions[fb.reaction] = reactions.get(fb.reaction, 0) + 1
        
        total = len(user_feedback)
        positive_rate = reactions['positive'] / total * 100 if total > 0 else 0
        
        lines = [
            f"📊 *Your Feedback Stats*",
            "",
            f"Total feedback: {total}",
            f"✓ Positive: {reactions['positive']}",
            f"✗ Negative: {reactions['negative']"],
            f"➖ Neutral: {reactions['neutral']}",
            "",
            f"Positive rate: {positive_rate:.0f}%"
        ]
        
        # Get preference info
        pref = self.get_user_preferences(user_id)
        if pref:
            if pref.get('preferred_signal_types'):
                lines.extend([
                    "",
                    "⭐ Preferred types: " + ", ".join(pref['preferred_signal_types'][:5])
                ])
            if pref.get('avoided_signal_types'):
                lines.extend([
                    "",
                    "🚫 Avoided types: " + ", ".join(pref['avoided_signal_types'][:5])
                ])
        
        return ("\n".join(lines), False)
    
    def _cmd_signal(
        self,
        user_id: str,
        args: List[str]
    ) -> Tuple[str, bool]:
        """Process /signal command."""
        if not args:
            return ("Usage: /signal [signal_id]\n\n"
                   "Get details of a specific signal.", True)
        
        signal_id = args[0]
        signal = self.signal_tracker.get_signal(signal_id)
        
        if not signal:
            return (f"Signal not found: {signal_id}", True)
        
        # Format response
        emoji = "✓" if signal.status == "SUCCESS" else "✗" if signal.status == "FAILED" else "⏳"
        
        lines = [
            f"📡 *Signal: {signal.id}*",
            "",
            f"Type: {signal.type}",
            f"Symbol: {signal.symbol}",
            f"Direction: {signal.direction}",
            f"Price: ${signal.price:,.2f}",
            f"Confidence: {signal.confidence:.0%}",
            f"Status: {signal.status} {emoji}",
            f"Reason: {signal.reason[:100]}...",
            "",
            f"Source: {signal.source}",
            f"Time: {signal.timestamp}"
        ]
        
        # Add results if available
        if signal.result_24h is not None:
            lines.append(f"24h Result: {signal.result_24h:+.2f}%")
        if signal.result_7d is not None:
            lines.append(f"7d Result: {signal.result_7d:+.2f}%")
        if signal.result_30d is not None:
            lines.append(f"30d Result: {signal.result_30d:+.2f}%")
        
        # Add user reaction if available
        if signal.user_reaction:
            lines.append(f"Your reaction: {signal.user_reaction}")
        
        return ("\n".join(lines), False)
    
    def _cmd_preferences(self, user_id: str) -> Tuple[str, bool]:
        """Process /preferences command."""
        pref = self.get_user_preferences(user_id)
        
        if not pref:
            return ("No preferences set yet.", False)
        
        lines = [
            "⚙️ *Your Preferences*",
            "",
            f"Notifications: {'✅ On' if pref['notification_enabled'] else '❌ Off'}",
            f"Min Confidence: {pref['min_confidence']:.0%}"
        ]
        
        if pref.get('preferred_signal_types'):
            lines.extend([
                "",
                "⭐ Preferred: " + ", ".join(pref['preferred_signal_types'][:5])
            ])
        
        if pref.get('avoided_signal_types'):
            lines.extend([
                "",
                "🚫 Avoided: " + ", ".join(pref['avoided_signal_types'][:5])
            ])
        
        if pref.get('threshold_adjustments'):
            lines.extend([
                "",
                "📊 Threshold Adjustments:"
            ])
            for stype, adj in list(pref['threshold_adjustments'].items())[:5]:
                lines.append(f"  {stype}: {adj:+.0%}")
        
        return ("\n".join(lines), False)
    
    def _cmd_notify(
        self,
        user_id: str,
        args: List[str]
    ) -> Tuple[str, bool]:
        """Process /notify command."""
        if not args:
            pref = self.get_or_create_preferences(user_id)
            status = "on" if pref.notification_enabled else "off"
            return (f"Notifications are currently *{status}*", False)
        
        value = args[0].lower()
        if value not in ['on', 'off']:
            return ("Usage: /notify on|off", True)
        
        pref = self.get_or_create_preferences(user_id)
        pref.notification_enabled = (value == 'on')
        pref.updated_at = datetime.now().isoformat()
        
        self._save_data()
        
        return (f"Notifications {'enabled' if value == 'on' else 'disabled'}", False)
    
    def _cmd_min_confidence(
        self,
        user_id: str,
        args: List[str]
    ) -> Tuple[str, bool]:
        """Process /minconfidence command."""
        if not args:
            pref = self.get_or_create_preferences(user_id)
            return (f"Minimum confidence: {pref.min_confidence:.0%}", False)
        
        try:
            value = float(args[0])
            if value < 0 or value > 1:
                raise ValueError()
        except ValueError:
            return ("Usage: /minconfidence [0.0-1.0]", True)
        
        pref = self.get_or_create_preferences(user_id)
        pref.min_confidence = value
        pref.updated_at = datetime.now().isoformat()
        
        self._save_data()
        
        return (f"Minimum confidence set to {value:.0%}", False)
    
    # ── Analysis Methods ───────────────────────────────────────────────────────
    
    def get_popular_signal_types(self, min_count: int = 3) -> List[Tuple[str, int]]:
        """Get most popular signal types based on user feedback."""
        type_counts = {}
        
        for fb in self.feedback_records:
            signal = self.signal_tracker.get_signal(fb.signal_id)
            if signal:
                type_counts[signal.type] = type_counts.get(signal.type, 0) + 1
        
        return sorted(
            [(t, c) for t, c in type_counts.items() if c >= min_count],
            key=lambda x: x[1],
            reverse=True
        )
    
    def get_signal_type_reputation(self) -> Dict[str, Dict]:
        """Get reputation scores for all signal types."""
        type_stats = {}
        
        for fb in self.feedback_records:
            signal = self.signal_tracker.get_signal(fb.signal_id)
            if not signal:
                continue
            
            if signal.type not in type_stats:
                type_stats[signal.type] = {
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0,
                    'total': 0
                }
            
            type_stats[signal.type][fb.reaction] += 1
            type_stats[signal.type]['total'] += 1
        
        # Calculate scores
        for stype, stats in type_stats.items():
            if stats['total'] > 0:
                stats['score'] = (stats['positive'] - stats['negative']) / stats['total']
            else:
                stats['score'] = 0.0
        
        return type_stats


# ── CLI Interface ──────────────────────────────────────────────────────────────

def main():
    """CLI for user feedback."""
    import argparse
    
    parser = argparse.ArgumentParser(description="User Feedback")
    parser.add_argument("action", 
                        choices=["feedback", "stats", "preferences", "reputation"],
                        default="stats", help="Action to perform")
    parser.add_argument("--user-id", "-u", required=True, help="User ID")
    parser.add_argument("--signal-id", "-s", help="Signal ID")
    parser.add_argument("--result", "-r", choices=["positive", "negative", "neutral"],
                        help="Feedback result")
    parser.add_argument("--signal-type", "-t", help="Signal type")
    parser.add_argument("--adjustment", "-a", type=float, help="Threshold adjustment")
    
    args = parser.parse_args()
    
    feedback = UserFeedback()
    
    if args.action == "feedback":
        if not args.signal_id or not args.result:
            print("Error: --signal-id and --result required")
            sys.exit(1)
        
        success, message = feedback.process_feedback(
            args.user_id, args.signal_id, args.result
        )
        print(message)
    
    elif args.action == "stats":
        pref = feedback.get_user_preferences(args.user_id)
        if pref:
            print(json.dumps(pref, indent=2))
        else:
            print("No preferences found")
    
    elif args.action == "preferences":
        pref = feedback.get_or_create_preferences(args.user_id)
        print(json.dumps(pref.to_dict(), indent=2))
    
    elif args.action == "reputation":
        rep = feedback.get_signal_type_reputation()
        print(json.dumps(rep, indent=2))


if __name__ == '__main__':
    main()
