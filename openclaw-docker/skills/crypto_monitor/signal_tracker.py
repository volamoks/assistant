#!/usr/bin/env python3
"""
Signal Tracking System for Crypto Agent

Features:
- Record every signal with full context
- Check signal results at 24h, 7d, 30d intervals
- Calculate statistics by signal type
- User feedback integration
- Performance reporting

Uses JSON file storage (simple, no external DB required)
"""

import os
import sys
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path

sys.path.insert(0, '/home/node/.openclaw/skills')

from adaptive_alerts import Alert


# ── Configuration ──────────────────────────────────────────────────────────────

SIGNAL_STORAGE_PATH = Path("/home/node/.openclaw/skills/crypto_monitor/data/signal_history.json")
CHECK_INTERVALS = {
    '24h': timedelta(hours=24),
    '7d': timedelta(days=7),
    '30d': timedelta(days=30)
}


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class Signal:
    """
    Complete signal record for tracking.
    
    Attributes:
        id: Unique signal identifier (e.g., sig_20240305_0815_BTC_SPIKE)
        timestamp: When signal was generated
        type: Signal type (PRICE_SPIKE, FEAR_GREED, RSI_OVERSOLD, etc.)
        symbol: Trading symbol (BTCUSDT, ETHUSDT, etc.)
        price: Price at signal generation
        direction: UP, DOWN, or NEUTRAL
        reason: Human-readable reason for signal
        confidence: Confidence level 0.0-1.0
        source: Source module (adaptive_alerts, onchain_analyzer, opportunity_screener)
        status: PENDING, SUCCESS, FAILED, CANCELLED
        result_24h: Result after 24 hours (price change %)
        result_7d: Result after 7 days (price change %)
        result_30d: Result after 30 days (price change %)
        user_reaction: User feedback (positive, negative, neutral)
    """
    id: str
    timestamp: str
    type: str
    symbol: str
    price: float
    direction: str
    reason: str
    confidence: float
    source: str
    status: str = "PENDING"
    result_24h: Optional[float] = None
    result_7d: Optional[float] = None
    result_30d: Optional[float] = None
    user_reaction: Optional[str] = None
    details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage."""
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'type': self.type,
            'symbol': self.symbol,
            'price': self.price,
            'direction': self.direction,
            'reason': self.reason,
            'confidence': self.confidence,
            'source': self.source,
            'status': self.status,
            'result_24h': self.result_24h,
            'result_7d': self.result_7d,
            'result_30d': self.result_30d,
            'user_reaction': self.user_reaction,
            'details': self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Signal':
        """Create Signal from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_alert(cls, alert: Alert, source: str) -> 'Signal':
        """
        Create Signal from Alert.
        
        Args:
            alert: Alert from adaptive_alerts or other modules
            source: Source module name
        
        Returns:
            Signal instance
        """
        # Generate unique ID
        ts = alert.timestamp
        signal_id = f"sig_{ts.strftime('%Y%m%d_%H%M')}_{alert.symbol}_{alert.alert_type.upper()}"
        
        # Determine direction from message/details
        direction = "NEUTRAL"
        if "UP" in alert.message.upper() or "SPIKE" in alert.message.upper():
            direction = "UP"
        elif "DOWN" in alert.message.upper() or "DROP" in alert.message.upper():
            direction = "DOWN"
        
        # Extract type from alert_type
        signal_type = alert.alert_type.upper()
        if "spike" in signal_type:
            signal_type = "PRICE_SPIKE"
        elif "volume" in signal_type:
            signal_type = "VOLUME_ANOMALY"
        elif "adaptive" in signal_type:
            signal_type = "ADAPTIVE_THRESHOLD"
        
        return cls(
            id=signal_id,
            timestamp=ts.isoformat(),
            type=signal_type,
            symbol=alert.symbol,
            price=alert.price,
            direction=direction,
            reason=alert.message,
            confidence=cls._estimate_confidence(alert),
            source=source,
            status="PENDING",
            details=alert.details or {}
        )
    
    @staticmethod
    def _estimate_confidence(alert: Alert) -> float:
        """Estimate confidence based on alert severity and details."""
        severity_weights = {
            'critical': 0.9,
            'high': 0.75,
            'medium': 0.6,
            'low': 0.4
        }
        base_confidence = severity_weights.get(alert.severity, 0.5)
        
        # Adjust based on price change magnitude
        if alert.change_pct:
            change_factor = min(abs(alert.change_pct) / 10.0, 1.0)
            base_confidence = (base_confidence + change_factor) / 2
        
        return round(base_confidence, 2)


@dataclass
class SignalResult:
    """Result of checking a signal's prediction."""
    signal_id: str
    check_timeframe: str  # 24h, 7d, 30d
    price_at_check: float
    price_change_pct: float
    is_successful: bool
    direction_correct: bool
    timestamp: str


# ── Signal Tracker Class ──────────────────────────────────────────────────────

class SignalTracker:
    """
    Main signal tracking system.
    
    Tracks all signals, checks results, and provides statistics.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize signal tracker.
        
        Args:
            storage_path: Path to JSON storage file
        """
        self.storage_path = storage_path or SIGNAL_STORAGE_PATH
        self.signals: List[Signal] = []
        self._load_signals()
    
    def _load_signals(self):
        """Load signals from JSON file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.signals = [Signal.from_dict(s) for s in data.get('signals', [])]
            except (json.JSONDecodeError, IOError) as e:
                print(f"[SignalTracker] Could not load signals: {e}")
                self.signals = []
        else:
            self.signals = []
    
    def _save_signals(self):
        """Save signals to JSON file."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.storage_path, 'w') as f:
                json.dump({
                    'signals': [s.to_dict() for s in self.signals],
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2)
        except IOError as e:
            print(f"[SignalTracker] Could not save signals: {e}")
    
    def _generate_signal_id(self, signal_type: str, symbol: str) -> str:
        """Generate unique signal ID."""
        ts = datetime.now()
        unique_id = str(uuid.uuid4())[:8]
        return f"sig_{ts.strftime('%Y%m%d_%H%M')}_{symbol}_{signal_type}_{unique_id}"
    
    # ── Core Methods ─────────────────────────────────────────────────────────────
    
    def record_signal(
        self,
        signal_type: str,
        symbol: str,
        price: float,
        direction: str,
        reason: str,
        confidence: float = 0.5,
        source: str = "unknown",
        details: Optional[Dict] = None
    ) -> Signal:
        """
        Record a new signal.
        
        Args:
            signal_type: Type of signal (PRICE_SPIKE, FEAR_GREED, etc.)
            symbol: Trading symbol
            price: Current price
            direction: UP, DOWN, or NEUTRAL
            reason: Human-readable reason
            confidence: Confidence level 0.0-1.0
            source: Source module name
            details: Additional details
        
        Returns:
            Created Signal instance
        """
        signal_id = self._generate_signal_id(signal_type, symbol)
        
        signal = Signal(
            id=signal_id,
            timestamp=datetime.now().isoformat(),
            type=signal_type.upper(),
            symbol=symbol,
            price=price,
            direction=direction.upper(),
            reason=reason,
            confidence=confidence,
            source=source,
            status="PENDING",
            details=details or {}
        )
        
        self.signals.append(signal)
        self._save_signals()
        
        print(f"[SignalTracker] Recorded signal: {signal_id} ({signal_type} {symbol})")
        return signal
    
    def record_signal_from_alert(self, alert: Alert, source: str) -> Signal:
        """
        Record signal from Alert object.
        
        Args:
            alert: Alert from adaptive_alerts
            source: Source module name
        
        Returns:
            Created Signal instance
        """
        signal = Signal.from_alert(alert, source)
        self.signals.append(signal)
        self._save_signals()
        
        print(f"[SignalTracker] Recorded signal from alert: {signal.id}")
        return signal
    
    def get_signal(self, signal_id: str) -> Optional[Signal]:
        """Get signal by ID."""
        for signal in self.signals:
            if signal.id == signal_id:
                return signal
        return None
    
    def get_pending_signals(self) -> List[Signal]:
        """Get all pending signals."""
        return [s for s in self.signals if s.status == "PENDING"]
    
    def get_signals_by_type(self, signal_type: str) -> List[Signal]:
        """Get all signals of a specific type."""
        return [s for s in self.signals if s.type == signal_type.upper()]
    
    def get_signals_by_symbol(self, symbol: str) -> List[Signal]:
        """Get all signals for a specific symbol."""
        return [s for s in self.signals if s.symbol == symbol.upper()]
    
    def get_signals_by_status(self, status: str) -> List[Signal]:
        """Get all signals with a specific status."""
        return [s for s in self.signals if s.status == status.upper()]
    
    def get_signals_by_source(self, source: str) -> List[Signal]:
        """Get all signals from a specific source."""
        return [s for s in self.signals if s.source == source]
    
    def get_signals_by_date_range(
        self,
        start: datetime,
        end: datetime
    ) -> List[Signal]:
        """Get signals within a date range."""
        result = []
        for signal in self.signals:
            try:
                signal_time = datetime.fromisoformat(signal.timestamp)
                if start <= signal_time <= end:
                    result.append(signal)
            except ValueError:
                continue
        return result
    
    # ── Result Checking ───────────────────────────────────────────────────────
    
    def check_signal_result(
        self,
        signal_id: str,
        current_price: float
    ) -> Optional[SignalResult]:
        """
        Check the result of a signal against current price.
        
        Args:
            signal_id: Signal ID to check
            current_price: Current price of the asset
        
        Returns:
            SignalResult if successful, None if signal not found
        """
        signal = self.get_signal(signal_id)
        if not signal:
            return None
        
        # Calculate price change
        price_change_pct = ((current_price - signal.price) / signal.price) * 100
        
        # Determine timeframe
        signal_time = datetime.fromisoformat(signal.timestamp)
        elapsed = datetime.now() - signal_time
        
        timeframe = None
        result_field = None
        
        if elapsed >= CHECK_INTERVALS['30d']:
            timeframe = '30d'
            result_field = 'result_30d'
            signal.result_30d = price_change_pct
        elif elapsed >= CHECK_INTERVALS['7d']:
            timeframe = '7d'
            result_field = 'result_7d'
            signal.result_7d = price_change_pct
        elif elapsed >= CHECK_INTERVALS['24h']:
            timeframe = '24h'
            result_field = 'result_24h'
            signal.result_24h = price_change_pct
        
        if timeframe is None:
            return None  # Not enough time has passed
        
        # Determine if successful
        direction_correct = False
        if signal.direction == "UP" and price_change_pct > 0:
            direction_correct = True
        elif signal.direction == "DOWN" and price_change_pct < 0:
            direction_correct = True
        elif signal.direction == "NEUTRAL":
            direction_correct = abs(price_change_pct) < 2.0  # Small movement
        
        # Consider successful if price moved in predicted direction by at least 1%
        is_successful = direction_correct and abs(price_change_pct) >= 1.0
        
        # Update signal status
        if timeframe == '30d' or (timeframe == '7d' and not signal.result_30d):
            signal.status = "SUCCESS" if is_successful else "FAILED"
        
        # Update result field
        if result_field:
            setattr(signal, result_field, price_change_pct)
        
        self._save_signals()
        
        return SignalResult(
            signal_id=signal_id,
            check_timeframe=timeframe,
            price_at_check=current_price,
            price_change_pct=price_change_pct,
            is_successful=is_successful,
            direction_correct=direction_correct,
            timestamp=datetime.now().isoformat()
        )
    
    def check_pending_signals(self, current_prices: Dict[str, float]) -> List[SignalResult]:
        """
        Check all pending signals against current prices.
        
        Args:
            current_prices: Dict of symbol -> current price
        
        Returns:
            List of SignalResult objects
        """
        results = []
        pending = self.get_pending_signals()
        
        for signal in pending:
            if signal.symbol in current_prices:
                result = self.check_signal_result(signal.id, current_prices[signal.symbol])
                if result:
                    results.append(result)
        
        return results
    
    def check_all_signals_for_timeframe(self, timeframe: str = "24h") -> int:
        """
        Check all signals that are due for a specific timeframe.
        
        This should be run periodically (e.g., daily for 24h checks).
        
        Args:
            timeframe: Timeframe to check (24h, 7d, 30d)
        
        Returns:
            Number of signals checked
        """
        if timeframe not in CHECK_INTERVALS:
            raise ValueError(f"Invalid timeframe: {timeframe}")
        
        # For now, return 0 as we need external price data
        # This will be called by event_watcher which has access to prices
        return 0
    
    # ── Statistics ─────────────────────────────────────────────────────────────
    
    def get_statistics(self, timeframe: str = "30d") -> Dict:
        """
        Get overall signal statistics.
        
        Args:
            timeframe: Time period for statistics (24h, 7d, 30d, all)
        
        Returns:
            Dictionary with statistics
        """
        # Filter signals by timeframe
        if timeframe != "all":
            cutoff = datetime.now() - CHECK_INTERVALS.get(timeframe, timedelta(days=30))
            signals = [s for s in self.signals if datetime.fromisoformat(s.timestamp) >= cutoff]
        else:
            signals = self.signals
        
        if not signals:
            return {
                'total_signals': 0,
                'success_rate': 0.0,
                'by_type': {},
                'by_source': {},
                'pending_count': 0
            }
        
        # Calculate overall stats
        completed = [s for s in signals if s.status in ["SUCCESS", "FAILED"]]
        success_count = sum(1 for s in completed if s.status == "SUCCESS")
        success_rate = (success_count / len(completed) * 100) if completed else 0.0
        
        # Stats by type
        by_type = {}
        for signal in signals:
            if signal.type not in by_type:
                by_type[signal.type] = {'total': 0, 'success': 0, 'pending': 0}
            by_type[signal.type]['total'] += 1
            if signal.status == "SUCCESS":
                by_type[signal.type]['success'] += 1
            elif signal.status == "PENDING":
                by_type[signal.type]['pending'] += 1
        
        for t in by_type:
            completed_type = by_type[t]['total'] - by_type[t]['pending']
            if completed_type > 0:
                by_type[t]['success_rate'] = round(by_type[t]['success'] / completed_type * 100, 1)
            else:
                by_type[t]['success_rate'] = 0.0
        
        # Stats by source
        by_source = {}
        for signal in signals:
            if signal.source not in by_source:
                by_source[signal.source] = {'total': 0, 'success': 0, 'pending': 0}
            by_source[signal.source]['total'] += 1
            if signal.status == "SUCCESS":
                by_source[signal.source]['success'] += 1
            elif signal.status == "PENDING":
                by_source[signal.source]['pending'] += 1
        
        for src in by_source:
            completed_src = by_source[src]['total'] - by_source[src]['pending']
            if completed_src > 0:
                by_source[src]['success_rate'] = round(by_source[src]['success'] / completed_src * 100, 1)
            else:
                by_source[src]['success_rate'] = 0.0
        
        return {
            'total_signals': len(signals),
            'completed_signals': len(completed),
            'success_count': success_count,
            'failed_count': len(completed) - success_count,
            'pending_count': len(signals) - len(completed),
            'success_rate': round(success_rate, 1),
            'by_type': by_type,
            'by_source': by_source,
            'timeframe': timeframe
        }
    
    def get_best_signals(self, min_count: int = 3) -> List[Tuple[str, float, int]]:
        """
        Get signal types with best performance.
        
        Args:
            min_count: Minimum number of signals to consider
        
        Returns:
            List of (signal_type, success_rate, count) tuples sorted by success rate
        """
        stats = self.get_statistics("all")
        results = []
        
        for signal_type, data in stats.get('by_type', {}).items():
            if data['total'] >= min_count:
                results.append((signal_type, data['success_rate'], data['total']))
        
        return sorted(results, key=lambda x: x[1], reverse=True)
    
    def get_worst_signals(self, min_count: int = 3) -> List[Tuple[str, float, int]]:
        """
        Get signal types with worst performance.
        
        Args:
            min_count: Minimum number of signals to consider
        
        Returns:
            List of (signal_type, success_rate, count) tuples sorted by success rate
        """
        best = self.get_best_signals(min_count)
        return list(reversed(best))
    
    def get_current_streak(self) -> Tuple[int, str]:
        """
        Get current winning/losing streak.
        
        Returns:
            Tuple of (streak_length, streak_type: 'win' or 'loss')
        """
        # Get signals sorted by time
        sorted_signals = sorted(
            [s for s in self.signals if s.status in ["SUCCESS", "FAILED"]],
            key=lambda x: x.timestamp,
            reverse=True
        )
        
        if not sorted_signals:
            return (0, "none")
        
        streak = 0
        streak_type = "win" if sorted_signals[0].status == "SUCCESS" else "loss"
        
        for signal in sorted_signals:
            if (streak_type == "win" and signal.status == "SUCCESS") or \
               (streak_type == "loss" and signal.status == "FAILED"):
                streak += 1
            else:
                break
        
        return (streak, streak_type)
    
    # ── Performance Report ────────────────────────────────────────────────────
    
    def generate_performance_report(self) -> str:
        """
        Generate a performance report for Telegram.
        
        Returns:
            Formatted string report
        """
        stats = self.get_statistics("30d")
        best = self.get_best_signals(2)
        worst = self.get_worst_signals(2)
        streak, streak_type = self.get_current_streak()
        
        lines = [
            "📊 *SIGNAL PERFORMANCE*",
            "",
            f"📈 *Overall Accuracy: {stats['success_rate']}%*",
            "",
            "🎯 *By Signal Type:*"
        ]
        
        # Add by type stats
        for signal_type, data in sorted(stats.get('by_type', {}).items(), 
                                         key=lambda x: x[1].get('total', 0), 
                                         reverse=True):
            emoji = "✓" if data.get('success_rate', 0) >= 50 else "✗"
            lines.append(
                f"• {signal_type}: {data.get('success_rate', 0)}% {emoji} "
                f"({data['total']} signals)"
            )
        
        if best:
            lines.extend([
                "",
                "🏆 *Best Performing:*"
            ])
            for i, (signal_type, rate, count) in enumerate(best, 1):
                lines.append(f"{i}. {signal_type} → {rate}% success ({count} signals)")
        
        if worst:
            lines.extend([
                "",
                "⚠️ *Needs Improvement:*"
            ])
            for i, (signal_type, rate, count) in enumerate(worst, 1):
                lines.append(f"{i}. {signal_type} → {rate}% success ({count} signals)")
        
        # Add streak info
        if streak > 0:
            streak_emoji = "🔥" if streak_type == "win" else "📉"
            lines.extend([
                "",
                f"🎲 *Current Streak:* {streak_emoji} {streak} {'wins' if streak_type == 'win' else 'losses'} in a row"
            ])
        
        # Add weekly summary
        week_stats = self.get_statistics("7d")
        lines.extend([
            "",
            "📅 *This Week:*",
            f"• Signals: {week_stats['total_signals']}",
            f"• Success: {week_stats.get('success_count', 0)}",
            f"• Pending: {week_stats.get('pending_count', 0)}"
        ])
        
        return "\n".join(lines)
    
    # ── User Feedback ─────────────────────────────────────────────────────────
    
    def set_user_reaction(self, signal_id: str, reaction: str) -> bool:
        """
        Set user reaction to a signal.
        
        Args:
            signal_id: Signal ID
            reaction: Reaction (positive, negative, neutral)
        
        Returns:
            True if successful
        """
        signal = self.get_signal(signal_id)
        if not signal:
            return False
        
        signal.user_reaction = reaction.lower()
        self._save_signals()
        return True
    
    def get_user_reaction_stats(self) -> Dict:
        """Get statistics on user reactions."""
        reactions = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for signal in self.signals:
            if signal.user_reaction:
                reactions[signal.user_reaction] = reactions.get(signal.user_reaction, 0) + 1
        
        return reactions


# ── CLI Interface ──────────────────────────────────────────────────────────────

def main():
    """CLI for signal tracking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Signal Tracker")
    parser.add_argument("action", choices=["record", "stats", "report", "check"], 
                        default="stats", help="Action to perform")
    parser.add_argument("--type", "-t", help="Signal type")
    parser.add_argument("--symbol", "-s", help="Trading symbol")
    parser.add_argument("--price", "-p", type=float, help="Price")
    parser.add_argument("--direction", "-d", choices=["UP", "DOWN", "NEUTRAL"],
                        help="Signal direction")
    parser.add_argument("--reason", "-r", help="Signal reason")
    parser.add_argument("--confidence", "-c", type=float, default=0.5,
                        help="Confidence 0.0-1.0")
    parser.add_argument("--source", help="Source module")
    parser.add_argument("--signal-id", help="Signal ID for checking")
    parser.add_argument("--timeframe", default="30d", help="Timeframe for stats")
    
    args = parser.parse_args()
    
    tracker = SignalTracker()
    
    if args.action == "record":
        if not all([args.type, args.symbol, args.price, args.direction, args.reason]):
            print("Error: --type, --symbol, --price, --direction, --reason required")
            sys.exit(1)
        
        signal = tracker.record_signal(
            signal_type=args.type,
            symbol=args.symbol,
            price=args.price,
            direction=args.direction,
            reason=args.reason,
            confidence=args.confidence,
            source=args.source or "cli"
        )
        print(f"Recorded signal: {signal.id}")
    
    elif args.action == "stats":
        stats = tracker.get_statistics(args.timeframe)
        print(json.dumps(stats, indent=2))
    
    elif args.action == "report":
        print(tracker.generate_performance_report())
    
    elif args.action == "check":
        if not args.signal_id:
            print("Error: --signal-id required")
            sys.exit(1)
        print("Use event_watcher with --check-signals to check results")


if __name__ == '__main__':
    main()
