#!/usr/bin/env python3
"""
Adaptive Crypto Alert System

Features:
- ATR-based adaptive thresholds
- Price spike detection (15/30/60 min)
- Volume anomaly detection
- Integration with memory system

Uses Bybit public API (no auth required for market data)
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from collections import deque

sys.path.insert(0, '/home/node/.openclaw/skills')

from agent_memory.memory import Memory
from signal_tracker import SignalTracker
from telegram.notify import TelegramNotifier


@dataclass
class Alert:
    """Alert data structure."""
    symbol: str
    alert_type: str  # 'price_spike', 'volume_anomaly', 'adaptive_threshold'
    severity: str    # 'low', 'medium', 'high', 'critical'
    message: str
    price: float
    change_pct: float
    details: Dict
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'price': self.price,
            'change_pct': self.change_pct,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class PriceHistory:
    """In-memory price history for short-term analysis."""
    
    def __init__(self, max_points: int = 288):  # 24h of 5-min data
        self.prices: deque = deque(maxlen=max_points)
        self.volumes: deque = deque(maxlen=max_points)
        self.timestamps: deque = deque(maxlen=max_points)
    
    def add(self, price: float, volume: float, timestamp: Optional[datetime] = None):
        """Add a price point."""
        if timestamp is None:
            timestamp = datetime.now()
        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
    
    def get_price_change(self, minutes: int) -> Optional[Tuple[float, float]]:
        """
        Get price change over last N minutes.
        
        Returns:
            Tuple of (change_pct, current_price) or None if insufficient data
        """
        if len(self.prices) < 2:
            return None
        
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        # Find price at cutoff time
        historical_price = None
        for i, ts in enumerate(self.timestamps):
            if ts >= cutoff:
                if i > 0:
                    historical_price = self.prices[i]
                break
        
        if historical_price is None:
            # Use oldest available
            historical_price = self.prices[0]
        
        current_price = self.prices[-1]
        change_pct = ((current_price - historical_price) / historical_price) * 100
        
        return (change_pct, current_price)
    
    def get_average_volume(self, hours: int = 24) -> Optional[float]:
        """Get average volume over last N hours."""
        if not self.volumes:
            return None
        
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_volumes = [
            vol for ts, vol in zip(self.timestamps, self.volumes)
            if ts >= cutoff
        ]
        
        if not recent_volumes:
            return None
        
        return sum(recent_volumes) / len(recent_volumes)


class AdaptiveAlertSystem:
    """
    Adaptive alert system with ATR-based thresholds and anomaly detection.
    """
    
    # Default spike thresholds (will be adjusted by ATR)
    DEFAULT_SPIKE_THRESHOLDS = {
        15: 1.5,   # 1.5% in 15 min
        30: 2.5,   # 2.5% in 30 min
        60: 4.0,   # 4% in 60 min
    }
    
    VOLUME_ANOMALY_MULTIPLIER = 2.0  # 200% of average
    ATR_PERIOD = 14  # days for ATR calculation
    
    def __init__(self):
        self.memory = Memory(collection="crypto")
        self.signal_tracker = SignalTracker()
        self.price_histories: Dict[str, PriceHistory] = {}
        self.atr_cache: Dict[str, Tuple[float, datetime]] = {}  # symbol -> (atr, timestamp)
        self._klines_cache: Dict[str, Tuple[List, datetime]] = {}
    
    def _get_price_history(self, symbol: str) -> PriceHistory:
        """Get or create price history for symbol."""
        if symbol not in self.price_histories:
            self.price_histories[symbol] = PriceHistory()
        return self.price_histories[symbol]
    
    def fetch_klines(self, symbol: str, interval: str = "D", limit: int = 30) -> List[Dict]:
        """
        Fetch candlestick/kline data from Bybit.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (D=daily, 60=1h, etc.)
            limit: Number of candles to fetch
        
        Returns:
            List of kline data
        """
        cache_key = f"{symbol}_{interval}"
        now = datetime.now()
        
        # Check cache (5 min TTL for non-daily intervals)
        if cache_key in self._klines_cache:
            data, cached_at = self._klines_cache[cache_key]
            ttl = timedelta(hours=1) if interval == "D" else timedelta(minutes=5)
            if now - cached_at < ttl:
                return data
        
        url = 'https://api.bybit.com/v5/market/kline'
        params = {
            'category': 'spot',
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('retCode') == 0:
                klines = data['result']['list']
                # Parse klines: [timestamp, open, high, low, close, volume, turnover]
                parsed = []
                for k in klines:
                    parsed.append({
                        'timestamp': int(k[0]),
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5]),
                        'turnover': float(k[6])
                    })
                
                self._klines_cache[cache_key] = (parsed, now)
                return parsed
        except Exception as e:
            print(f"[AdaptiveAlerts] Error fetching klines for {symbol}: {e}")
        
        return []
    
    def calculate_atr(self, symbol: str, period: int = 14) -> Optional[float]:
        """
        Calculate Average True Range (ATR) for a symbol.
        
        ATR measures market volatility. Higher ATR = more volatile.
        
        Args:
            symbol: Trading pair
            period: ATR calculation period (default 14 days)
        
        Returns:
            ATR as percentage of price, or None if calculation fails
        """
        # Check cache (1 hour TTL)
        now = datetime.now()
        if symbol in self.atr_cache:
            atr, cached_at = self.atr_cache[symbol]
            if now - cached_at < timedelta(hours=1):
                return atr
        
        # Fetch daily klines
        klines = self.fetch_klines(symbol, interval="D", limit=period + 1)
        if len(klines) < period + 1:
            print(f"[AdaptiveAlerts] Insufficient data for ATR calculation: {symbol}")
            return None
        
        # Calculate True Range for each period
        true_ranges = []
        for i in range(1, len(klines)):
            current = klines[i]
            previous = klines[i - 1]
            
            high = current['high']
            low = current['low']
            prev_close = previous['close']
            
            # True Range = max(high-low, |high-prev_close|, |low-prev_close|)
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        if not true_ranges:
            return None
        
        # Calculate ATR (simple average for now, could use Wilder's smoothing)
        atr = sum(true_ranges) / len(true_ranges)
        
        # Convert to percentage of current price
        current_price = klines[-1]['close']
        atr_pct = (atr / current_price) * 100
        
        # Cache result
        self.atr_cache[symbol] = (atr_pct, now)
        
        return atr_pct
    
    def get_adaptive_threshold(self, symbol: str) -> float:
        """
        Calculate adaptive alert threshold based on ATR.
        
        Rules:
        - If ATR > 4%: threshold = 1.5x ATR
        - If ATR < 2%: threshold = 2x ATR  
        - Otherwise: threshold = 1.8x ATR
        
        Args:
            symbol: Trading pair
        
        Returns:
            Adaptive threshold percentage
        """
        atr = self.calculate_atr(symbol)
        
        if atr is None:
            # Fallback to default threshold
            return 5.0
        
        if atr > 4.0:
            threshold = atr * 1.5
        elif atr < 2.0:
            threshold = atr * 2.0
        else:
            threshold = atr * 1.8
        
        return round(threshold, 2)
    
    def fetch_current_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch current ticker data from Bybit.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
        
        Returns:
            Dict with price, volume, 24h change, etc.
        """
        url = 'https://api.bybit.com/v5/market/tickers'
        params = {'category': 'spot', 'symbol': symbol}
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('retCode') == 0:
                t = data['result']['list'][0]
                return {
                    'symbol': symbol,
                    'price': float(t['lastPrice']),
                    'pct_24h': float(t['price24hPcnt']) * 100,
                    'high_24h': float(t['highPrice24h']),
                    'low_24h': float(t['lowPrice24h']),
                    'volume_24h': float(t['volume24h']),
                    'turnover_24h': float(t['turnover24h']),
                    'bid': float(t.get('bid1Price', 0)),
                    'ask': float(t.get('ask1Price', 0)),
                }
        except Exception as e:
            print(f"[AdaptiveAlerts] Error fetching data for {symbol}: {e}")
        
        return None
    
    def update_price_history(self, symbol: str, data: Optional[Dict] = None):
        """
        Update price history with current data.
        
        Args:
            symbol: Trading pair
            data: Optional pre-fetched data (fetches if None)
        """
        if data is None:
            data = self.fetch_current_data(symbol)
        
        if data:
            history = self._get_price_history(symbol)
            history.add(
                price=data['price'],
                volume=data['volume_24h'],
                timestamp=datetime.now()
            )
    
    def check_price_spike(self, symbol: str, timeframe_min: int = 15) -> Optional[Alert]:
        """
        Check for price spike in given timeframe.
        
        Args:
            symbol: Trading pair
            timeframe_min: Timeframe in minutes (15, 30, or 60)
        
        Returns:
            Alert if spike detected, None otherwise
        """
        # Update history first
        self.update_price_history(symbol)
        
        history = self._get_price_history(symbol)
        change_data = history.get_price_change(timeframe_min)
        
        if change_data is None:
            return None
        
        change_pct, current_price = change_data
        
        # Get adaptive threshold
        adaptive_threshold = self.get_adaptive_threshold(symbol)
        
        # Calculate spike threshold for this timeframe
        base_threshold = self.DEFAULT_SPIKE_THRESHOLDS.get(timeframe_min, 1.5)
        
        # Adjust threshold based on ATR ratio
        atr = self.calculate_atr(symbol) or 3.0
        adjustment_factor = atr / 3.0  # Normalize to typical crypto volatility
        spike_threshold = base_threshold * adjustment_factor
        
        # Check for spike (both directions)
        if abs(change_pct) >= spike_threshold:
            severity = 'medium'
            if abs(change_pct) >= spike_threshold * 2:
                severity = 'critical'
            elif abs(change_pct) >= spike_threshold * 1.5:
                severity = 'high'
            
            direction = "📈 SPIKE UP" if change_pct > 0 else "📉 DROP ALERT"
            
            alert = Alert(
                symbol=symbol,
                alert_type='price_spike',
                severity=severity,
                message=f"{direction}: {symbol} moved {change_pct:+.2f}% in {timeframe_min}min",
                price=current_price,
                change_pct=change_pct,
                details={
                    'timeframe_min': timeframe_min,
                    'threshold_used': spike_threshold,
                    'atr_at_time': atr,
                    'adaptive_threshold_24h': adaptive_threshold
                },
                timestamp=datetime.now()
            )
            
            return alert
        
        return None
    
    def check_volume_anomaly(self, symbol: str) -> Optional[Alert]:
        """
        Check for volume anomaly (volume > 200% of 24h average).
        
        Args:
            symbol: Trading pair
        
        Returns:
            Alert if volume anomaly detected, None otherwise
        """
        # Update history
        self.update_price_history(symbol)
        
        history = self._get_price_history(symbol)
        avg_volume = history.get_average_volume(hours=24)
        
        if avg_volume is None or avg_volume == 0:
            # Not enough history, use 24h data point only
            data = self.fetch_current_data(symbol)
            if not data:
                return None
            
            # Single point comparison - check if volume is unusually high
            # This is a simplified check without history
            return None
        
        current_volume = history.volumes[-1] if history.volumes else 0
        
        if current_volume > avg_volume * self.VOLUME_ANOMALY_MULTIPLIER:
            volume_ratio = current_volume / avg_volume
            
            severity = 'high' if volume_ratio > 3.0 else 'medium'
            
            data = self.fetch_current_data(symbol)
            current_price = data['price'] if data else 0
            
            alert = Alert(
                symbol=symbol,
                alert_type='volume_anomaly',
                severity=severity,
                message=f"📊 VOLUME SPIKE: {symbol} volume is {volume_ratio:.1f}x average",
                price=current_price,
                change_pct=0,
                details={
                    'current_volume_24h': current_volume,
                    'average_volume_24h': avg_volume,
                    'volume_ratio': volume_ratio,
                    'threshold_multiplier': self.VOLUME_ANOMALY_MULTIPLIER
                },
                timestamp=datetime.now()
            )
            
            return alert
        
        return None
    
    def should_alert(self, symbol: str, change_pct: float) -> bool:
        """
        Check if price change should trigger an alert based on adaptive threshold.
        
        Args:
            symbol: Trading pair
            change_pct: 24h change percentage
        
        Returns:
            True if alert should be triggered
        """
        threshold = self.get_adaptive_threshold(symbol)
        return abs(change_pct) >= threshold
    
    def check_adaptive_threshold(self, symbol: str) -> Optional[Alert]:
        """
        Check if 24h change exceeds adaptive threshold.
        
        Args:
            symbol: Trading pair
        
        Returns:
            Alert if threshold exceeded, None otherwise
        """
        data = self.fetch_current_data(symbol)
        if not data:
            return None
        
        change_pct = data['pct_24h']
        
        if self.should_alert(symbol, change_pct):
            threshold = self.get_adaptive_threshold(symbol)
            
            if change_pct > 0:
                message = f"🚀 BREAKOUT: {symbol} up {change_pct:+.2f}% (threshold: ±{threshold}%)"
                severity = 'medium'
            else:
                message = f"🔥 DIP ALERT: {symbol} down {change_pct:.2f}% (threshold: ±{threshold}%)"
                severity = 'high' if change_pct < -threshold * 1.5 else 'medium'
            
            alert = Alert(
                symbol=symbol,
                alert_type='adaptive_threshold',
                severity=severity,
                message=message,
                price=data['price'],
                change_pct=change_pct,
                details={
                    'threshold_used': threshold,
                    'atr': self.calculate_atr(symbol),
                    'high_24h': data['high_24h'],
                    'low_24h': data['low_24h']
                },
                timestamp=datetime.now()
            )
            
            return alert
        
        return None
    
    def store_alert_in_memory(self, alert: Alert) -> str:
        """
        Store alert in memory system.
        
        Args:
            alert: Alert to store
        
        Returns:
            Memory ID
        """
        # Store in memory
        memory_id = self.memory.store(
            text=f"{alert.alert_type}: {alert.message} at ${alert.price:,.2f}",
            metadata={
                "category": "adaptive_alert",
                "symbol": alert.symbol,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "price": alert.price,
                "change_pct": alert.change_pct,
                "details": alert.details,
                "timestamp": alert.timestamp.isoformat()
            }
        )
        
        # Also record as signal for tracking
        try:
            self.signal_tracker.record_signal_from_alert(alert, "adaptive_alerts")
        except Exception as e:
            print(f"[AdaptiveAlertSystem] Error recording signal: {e}")
        
        return memory_id
    
    def get_recent_alerts(self, symbol: Optional[str] = None, 
                         hours: int = 24) -> List[Alert]:
        """
        Get recent alerts from memory.
        
        Args:
            symbol: Optional symbol filter
            hours: How many hours back to look
        
        Returns:
            List of recent alerts
        """
        # Get alerts from memory
        memories = self.memory.get_by_category("adaptive_alert", limit=50)
        
        alerts = []
        cutoff = datetime.now() - timedelta(hours=hours)
        
        for mem in memories:
            meta = mem.metadata
            ts_str = meta.get('timestamp', '')
            
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts < cutoff:
                    continue
                
                if symbol and meta.get('symbol') != symbol:
                    continue
                
                alerts.append(Alert(
                    symbol=meta.get('symbol', 'UNKNOWN'),
                    alert_type=meta.get('alert_type', 'unknown'),
                    severity=meta.get('severity', 'low'),
                    message=mem.text,
                    price=meta.get('price', 0),
                    change_pct=meta.get('change_pct', 0),
                    details=meta.get('details', {}),
                    timestamp=ts
                ))
            except (ValueError, TypeError):
                continue
        
        return alerts
    
    def check_cooldown(self, symbol: str, alert_type: str, 
                       cooldown_minutes: int = 60) -> bool:
        """
        Check if enough time has passed since last alert of this type.
        
        Args:
            symbol: Trading pair
            alert_type: Type of alert
            cooldown_minutes: Cooldown period
        
        Returns:
            True if can alert (cooldown passed), False otherwise
        """
        recent = self.get_recent_alerts(symbol=symbol, hours=24)
        
        cutoff = datetime.now() - timedelta(minutes=cooldown_minutes)
        
        for alert in recent:
            if alert.alert_type == alert_type and alert.timestamp > cutoff:
                return False
        
        return True
    
    def run_all_checks(self, symbol: str, 
                       with_cooldown: bool = True) -> List[Alert]:
        """
        Run all alert checks for a symbol.
        
        Args:
            symbol: Trading pair
            with_cooldown: Whether to respect cooldown periods
        
        Returns:
            List of triggered alerts
        """
        alerts = []
        
        # Check adaptive threshold
        if not with_cooldown or self.check_cooldown(symbol, 'adaptive_threshold', 60):
            alert = self.check_adaptive_threshold(symbol)
            if alert:
                alerts.append(alert)
        
        # Check price spikes at different timeframes
        for timeframe in [15, 30, 60]:
            alert_type = f'price_spike_{timeframe}'
            if not with_cooldown or self.check_cooldown(symbol, alert_type, 30):
                alert = self.check_price_spike(symbol, timeframe)
                if alert:
                    alert.alert_type = alert_type
                    alerts.append(alert)
        
        # Check volume anomaly
        if not with_cooldown or self.check_cooldown(symbol, 'volume_anomaly', 60):
            alert = self.check_volume_anomaly(symbol)
            if alert:
                alerts.append(alert)
        
        # Store alerts in memory
        for alert in alerts:
            self.store_alert_in_memory(alert)
        
        return alerts


def format_alert_for_telegram(alert: Alert) -> str:
    """
    Format alert for Telegram message.
    
    Args:
        alert: Alert to format
    
    Returns:
        Formatted message string
    """
    severity_emoji = {
        'low': '⚪',
        'medium': '🟡',
        'high': '🔴',
        'critical': '🚨'
    }
    
    emoji = severity_emoji.get(alert.severity, '⚪')
    
    lines = [
        f"{emoji} *Crypto Alert: {alert.symbol}*",
        f"",
        f"{alert.message}",
        f"",
        f"💰 Price: `${alert.price:,.2f}`",
        f"📊 24h Change: `{alert.change_pct:+.2f}%`",
        f"⏰ Time: `{alert.timestamp.strftime('%Y-%m-%d %H:%M UTC')}`",
    ]
    
    # Add details based on alert type
    if alert.alert_type == 'price_spike':
        lines.extend([
            f"",
            f"📈 Timeframe: `{alert.details.get('timeframe_min', 'N/A')} min`",
            f"🎯 Threshold: `{alert.details.get('threshold_used', 0):.2f}%`",
            f"📉 ATR: `{alert.details.get('atr_at_time', 0):.2f}%`",
        ])
    
    elif alert.alert_type == 'volume_anomaly':
        ratio = alert.details.get('volume_ratio', 0)
        lines.extend([
            f"",
            f"📊 Volume Ratio: `{ratio:.1f}x` average",
            f"💎 Current 24h Vol: `{alert.details.get('current_volume_24h', 0):,.0f}`",
        ])
    
    elif alert.alert_type == 'adaptive_threshold':
        lines.extend([
            f"",
            f"🎯 Adaptive Threshold: `±{alert.details.get('threshold_used', 0):.2f}%`",
            f"📉 ATR (14d): `{alert.details.get('atr', 0):.2f}%`",
            f"📈 24h High: `${alert.details.get('high_24h', 0):,.2f}`",
            f"📉 24h Low: `${alert.details.get('low_24h', 0):,.2f}`",
        ])
    
    return '\n'.join(lines)


def send_telegram_alert(alert: Alert, bot_token: Optional[str] = None,
                       chat_id: Optional[str] = None) -> bool:
    """
    Send alert via Telegram using TelegramNotifier.
    
    Args:
        alert: Alert to send
        bot_token: Telegram bot token (from env if not provided)
        chat_id: Telegram chat ID (from env if not provided)
    
    Returns:
        True if sent successfully
    """
    bot_token = bot_token or os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = chat_id or os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("[AdaptiveAlerts] Telegram credentials not configured")
        return False
    
    message = format_alert_for_telegram(alert)
    
    try:
        notifier = TelegramNotifier(
            bot_token=bot_token,
            chat_id=chat_id,
            parse_mode="Markdown"
        )
        
        # Use silent mode for low severity alerts
        silent = alert.severity == 'low'
        
        result = notifier.send(
            text=message,
            silent=silent
        )
        
        if result and result.get('ok'):
            print(f"[AdaptiveAlerts] Telegram alert sent for {alert.symbol}")
            return True
        else:
            print(f"[AdaptiveAlerts] Telegram error: {result}")
            return False
    except ValueError as e:
        print(f"[AdaptiveAlerts] Telegram configuration error: {e}")
        return False
    except Exception as e:
        print(f"[AdaptiveAlerts] Failed to send Telegram: {e}")
        return False


def main():
    """CLI for testing adaptive alerts."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Adaptive Crypto Alerts")
    parser.add_argument('--symbol', '-s', default='BTCUSDT', help='Trading pair')
    parser.add_argument('--check', '-c', action='store_true', help='Run all checks')
    parser.add_argument('--spike', action='store_true', help='Check price spikes')
    parser.add_argument('--volume', action='store_true', help='Check volume')
    parser.add_argument('--atr', action='store_true', help='Show ATR')
    parser.add_argument('--threshold', action='store_true', help='Show adaptive threshold')
    parser.add_argument('--telegram', '-t', action='store_true', help='Send to Telegram')
    parser.add_argument('--timeframe', type=int, default=15, choices=[15, 30, 60],
                       help='Spike detection timeframe')
    
    args = parser.parse_args()
    
    system = AdaptiveAlertSystem()
    
    if args.atr:
        atr = system.calculate_atr(args.symbol)
        if atr:
            print(f"ATR (14d) for {args.symbol}: {atr:.2f}%")
        else:
            print(f"Could not calculate ATR for {args.symbol}")
    
    if args.threshold:
        threshold = system.get_adaptive_threshold(args.symbol)
        atr = system.calculate_atr(args.symbol)
        print(f"Adaptive threshold for {args.symbol}: ±{threshold}%")
        print(f"  Based on ATR: {atr:.2f}%" if atr else "  Using default")
    
    alerts = []
    
    if args.spike:
        alert = system.check_price_spike(args.symbol, args.timeframe)
        if alert:
            alerts.append(alert)
            print(f"\nPrice spike detected!")
            print(format_alert_for_telegram(alert))
        else:
            print(f"No price spike in last {args.timeframe} min")
    
    if args.volume:
        alert = system.check_volume_anomaly(args.symbol)
        if alert:
            alerts.append(alert)
            print(f"\nVolume anomaly detected!")
            print(format_alert_for_telegram(alert))
        else:
            print("No volume anomaly")
    
    if args.check:
        print(f"Running all checks for {args.symbol}...")
        alerts = system.run_all_checks(args.symbol, with_cooldown=False)
        if alerts:
            print(f"\n{len(alerts)} alert(s) triggered:")
            for alert in alerts:
                print(f"\n{'='*50}")
                print(format_alert_for_telegram(alert))
        else:
            print("No alerts triggered")
    
    if args.telegram and alerts:
        for alert in alerts:
            send_telegram_alert(alert)


if __name__ == '__main__':
    main()
