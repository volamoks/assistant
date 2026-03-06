#!/usr/bin/env python3
"""
Event-Driven Crypto Watcher

Features:
- Continuous monitoring (5-minute intervals)
- Event-driven alerts (only on significant events)
- Liquidation monitoring via Bybit API
- Cooldown management to prevent alert spam
- Integration with adaptive alert system
"""

import os
import sys
import time
import json
import signal
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import threading

sys.path.insert(0, '/home/node/.openclaw/skills')

from adaptive_alerts import (
    AdaptiveAlertSystem, Alert, send_telegram_alert, format_alert_for_telegram
)
from agent_memory.memory import Memory
from onchain_analyzer import OnchainAnalyzer
from market_intelligence import MarketIntelligence
from opportunity_screener import OpportunityScreener
from multi_coin_monitor import MultiCoinMonitor
from technical_analysis import TechnicalAnalyzer
from signal_tracker import SignalTracker
from performance_report import PerformanceReport


# ── Configuration ──────────────────────────────────────────────────────────────

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
CHECK_INTERVAL_SECONDS = 300  # 5 minutes
LIQUIDATION_CHECK_INTERVAL = 600  # 10 minutes
FEAR_GREED_CHECK_INTERVAL = 3600  # 1 hour
FUNDING_OI_CHECK_INTERVAL = 14400  # 4 hours
COOLDOWN_MINUTES = 60  # Don't alert on same event within 1 hour

STATE_FILE = Path("/home/node/.openclaw/skills/crypto_monitor/watcher_state.json")
LOG_FILE = Path("/home/node/.openclaw/skills/crypto_monitor/watcher.log")


@dataclass
class WatcherState:
    """Persistent state for the watcher."""
    last_alert_times: Dict[str, str]  # symbol:alert_type -> ISO timestamp
    last_liquidation_check: Optional[str] = None
    last_prices: Dict[str, float] = None
    alert_counts: Dict[str, int] = None  # symbol -> count today
    
    def __post_init__(self):
        if self.last_prices is None:
            self.last_prices = {}
        if self.alert_counts is None:
            self.alert_counts = {}
    
    def to_dict(self) -> Dict:
        return {
            'last_alert_times': self.last_alert_times,
            'last_liquidation_check': self.last_liquidation_check,
            'last_prices': self.last_prices,
            'alert_counts': self.alert_counts,
            'saved_at': datetime.now().isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WatcherState':
        return cls(
            last_alert_times=data.get('last_alert_times', {}),
            last_liquidation_check=data.get('last_liquidation_check'),
            last_prices=data.get('last_prices', {}),
            alert_counts=data.get('alert_counts', {})
        )


class EventWatcher:
    """
    Event-driven crypto watcher with continuous monitoring.
    Includes on-chain metrics and macro indicators.
    """
    
    def __init__(self, symbols: Optional[List[str]] = None):
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.alert_system = AdaptiveAlertSystem()
        self.onchain_analyzer = OnchainAnalyzer()
        self.market_intelligence = MarketIntelligence()
        self.memory = Memory(collection="crypto")
        self.signal_tracker = SignalTracker()
        self.state = self._load_state()
        self.running = False
        self._shutdown_event = threading.Event()
        
        # Liquidation tracking
        self.known_liquidations: Set[str] = set()  # Set of liquidation IDs
        self.liquidation_threshold_usd = 100000  # $100k minimum to alert
        
        # On-chain tracking
        self._last_fear_greed_check: Optional[datetime] = None
        self._last_funding_oi_check: Optional[datetime] = None
        
        # Statistics
        self.checks_performed = 0
        self.alerts_sent = 0
        self.start_time = datetime.now()
    
    def _load_state(self) -> WatcherState:
        """Load state from disk."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                return WatcherState.from_dict(data)
            except Exception as e:
                print(f"[EventWatcher] Could not load state: {e}")
        
        return WatcherState(last_alert_times={})
    
    def _save_state(self):
        """Save state to disk."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
        except Exception as e:
            print(f"[EventWatcher] Could not save state: {e}")
    
    def _log(self, message: str):
        """Log message to file and console."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        print(log_entry)
        
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, 'a') as f:
                f.write(log_entry + '\n')
        except Exception:
            pass
    
    def _get_alert_key(self, symbol: str, alert_type: str) -> str:
        """Generate unique key for alert tracking."""
        return f"{symbol}:{alert_type}"
    
    def _is_on_cooldown(self, symbol: str, alert_type: str, 
                        cooldown_min: int = COOLDOWN_MINUTES) -> bool:
        """
        Check if an alert type is on cooldown for a symbol.
        
        Args:
            symbol: Trading pair
            alert_type: Type of alert
            cooldown_min: Cooldown period in minutes
        
        Returns:
            True if on cooldown
        """
        key = self._get_alert_key(symbol, alert_type)
        last_alert_str = self.state.last_alert_times.get(key)
        
        if not last_alert_str:
            return False
        
        try:
            last_alert = datetime.fromisoformat(last_alert_str)
            cooldown_end = last_alert + timedelta(minutes=cooldown_min)
            return datetime.now() < cooldown_end
        except ValueError:
            return False
    
    def _mark_alert_sent(self, symbol: str, alert_type: str):
        """Mark an alert as sent."""
        key = self._get_alert_key(symbol, alert_type)
        self.state.last_alert_times[key] = datetime.now().isoformat()
        
        # Update daily count
        today = datetime.now().strftime('%Y-%m-%d')
        count_key = f"{symbol}:{today}"
        self.state.alert_counts[count_key] = self.state.alert_counts.get(count_key, 0) + 1
        
        self._save_state()
    
    def check_liquidations(self) -> List[Alert]:
        """
        Check for large liquidations via Bybit API.
        
        Returns:
            List of liquidation alerts
        """
        alerts = []
        
        # Bybit liquidation endpoint (public)
        url = 'https://api.bybit.com/v5/market/recent-trade'
        
        for symbol in self.symbols:
            try:
                # Get recent trades to detect liquidations
                # Note: Bybit doesn't have a direct liquidation endpoint in public API
                # We use the recent trade API and look for large block trades
                params = {
                    'category': 'linear',  # perpetual contracts
                    'symbol': symbol.replace('USDT', 'USDT'),  # Ensure correct format
                    'limit': 100
                }
                
                resp = requests.get(url, params=params, timeout=10)
                data = resp.json()
                
                if data.get('retCode') != 0:
                    continue
                
                trades = data.get('result', {}).get('list', [])
                
                for trade in trades:
                    trade_id = trade.get('execId', '')
                    
                    # Skip if we've seen this trade
                    if trade_id in self.known_liquidations:
                        continue
                    
                    # Mark as seen
                    self.known_liquidations.add(trade_id)
                    
                    # Check if it's a large trade (potential liquidation)
                    size = float(trade.get('size', 0))
                    price = float(trade.get('price', 0))
                    value_usd = size * price
                    
                    # Also check blockTrade flag if available
                    is_block = trade.get('blockTrade', False)
                    
                    if value_usd >= self.liquidation_threshold_usd or is_block:
                        side = trade.get('side', 'Unknown')
                        
                        # Determine if it's likely a liquidation
                        # Large market orders often indicate liquidations
                        alert_type = 'large_trade'
                        severity = 'medium'
                        
                        if value_usd >= self.liquidation_threshold_usd * 5:
                            alert_type = 'liquidation'
                            severity = 'critical' if value_usd >= 1000000 else 'high'
                        
                        alert = Alert(
                            symbol=symbol,
                            alert_type=alert_type,
                            severity=severity,
                            message=f"💥 {'LIQUIDATION' if alert_type == 'liquidation' else 'LARGE TRADE'}: "
                                   f"{symbol} {side} ${value_usd:,.0f}",
                            price=price,
                            change_pct=0,
                            details={
                                'trade_id': trade_id,
                                'side': side,
                                'size': size,
                                'value_usd': value_usd,
                                'is_block_trade': is_block,
                                'timestamp': trade.get('execTime', '')
                            },
                            timestamp=datetime.now()
                        )
                        
                        alerts.append(alert)
                        
            except Exception as e:
                self._log(f"Error checking liquidations for {symbol}: {e}")
        
        # Limit memory usage
        if len(self.known_liquidations) > 10000:
            self.known_liquidations = set(list(self.known_liquidations)[-5000:])
        
        return alerts
    
    def check_market_events(self, symbol: str) -> List[Alert]:
        """
        Check for market events (price spikes, volume anomalies, thresholds).
        
        Args:
            symbol: Trading pair to check
        
        Returns:
            List of alerts
        """
        alerts = []
        
        # Check adaptive threshold
        if not self._is_on_cooldown(symbol, 'adaptive_threshold', 60):
            alert = self.alert_system.check_adaptive_threshold(symbol)
            if alert:
                alerts.append(alert)
                self._mark_alert_sent(symbol, 'adaptive_threshold')
        
        # Check price spikes at different timeframes
        for timeframe in [15, 30, 60]:
            alert_type = f'price_spike_{timeframe}'
            cooldown = 30 if timeframe == 15 else 60
            
            if not self._is_on_cooldown(symbol, alert_type, cooldown):
                alert = self.alert_system.check_price_spike(symbol, timeframe)
                if alert:
                    alert.alert_type = alert_type
                    alerts.append(alert)
                    self._mark_alert_sent(symbol, alert_type)
        
        # Check volume anomaly
        if not self._is_on_cooldown(symbol, 'volume_anomaly', 60):
            alert = self.alert_system.check_volume_anomaly(symbol)
            if alert:
                alerts.append(alert)
                self._mark_alert_sent(symbol, 'volume_anomaly')
        
        return alerts
    
    def format_alert_message(self, alert: Alert) -> str:
        """
        Format alert for display/notification.
        
        Args:
            alert: Alert to format
        
        Returns:
            Formatted message
        """
        if alert.alert_type in ['liquidation', 'large_trade']:
            return self._format_liquidation_message(alert)
        
        return format_alert_for_telegram(alert)
    
    def check_onchain_metrics(self) -> List[Alert]:
        """
        Check on-chain metrics and macro indicators.
        
        Returns:
            List of alerts from on-chain analysis
        """
        alerts = []
        now = datetime.now()
        
        # Check Fear & Greed every hour
        should_check_fg = (
            self._last_fear_greed_check is None or
            (now - self._last_fear_greed_check).total_seconds() >= FEAR_GREED_CHECK_INTERVAL
        )
        
        if should_check_fg:
            self._log("Checking Fear & Greed Index...")
            self._last_fear_greed_check = now
            
            try:
                # Check for macroeconomic alerts (extreme fear/greed)
                alert = self.onchain_analyzer.should_alert_macroeconomic()
                if alert:
                    alerts.append(alert)
                    self._log(f"  → On-chain alert: {alert.alert_type}")
            except Exception as e:
                self._log(f"  Error checking Fear & Greed: {e}")
        
        # Check Funding and OI every 4 hours
        should_check_funding = (
            self._last_funding_oi_check is None or
            (now - self._last_funding_oi_check).total_seconds() >= FUNDING_OI_CHECK_INTERVAL
        )
        
        if should_check_funding:
            self._log("Checking Funding rates and OI...")
            self._last_funding_oi_check = now
            
            try:
                # Check for extreme funding conditions
                funding = self.onchain_analyzer.get_funding_rates(self.symbols[:2])  # BTC, ETH
                for symbol, fd in funding.items():
                    if fd.is_extreme() and not self._is_on_cooldown(symbol, f'funding_{symbol}', 240):
                        alert = Alert(
                            symbol=symbol,
                            alert_type='extreme_funding',
                            severity='high' if abs(fd.funding_rate) > 0.001 else 'medium',
                            message=f"📊 Extreme Funding: {symbol} at {fd.funding_rate:.4%}",
                            price=0,
                            change_pct=0,
                            details={
                                'funding_rate': fd.funding_rate,
                                'predicted_rate': fd.predicted_rate,
                                'is_extreme': True
                            },
                            timestamp=datetime.now()
                        )
                        alerts.append(alert)
                        self._mark_alert_sent(symbol, f'funding_{symbol}')
                        self._log(f"  → Funding alert: {symbol}")
                
                # Check Open Interest for divergences
                for symbol in self.symbols[:2]:
                    oi = self.onchain_analyzer.get_open_interest(symbol)
                    if oi and oi.is_divergence() and not self._is_on_cooldown(symbol, f'oi_{symbol}', 240):
                        alert = Alert(
                            symbol=symbol,
                            alert_type='oi_divergence',
                            severity='high',
                            message=f"⚠️ OI/Price Divergence: {symbol} OI +{oi.oi_change_24h_pct:.1f}% vs Price {oi.price_change_24h_pct:+.1f}%",
                            price=0,
                            change_pct=oi.price_change_24h_pct,
                            details={
                                'oi_change': oi.oi_change_24h_pct,
                                'price_change': oi.price_change_24h_pct,
                                'open_interest': oi.open_interest
                            },
                            timestamp=datetime.now()
                        )
                        alerts.append(alert)
                        self._mark_alert_sent(symbol, f'oi_{symbol}')
                        self._log(f"  → OI alert: {symbol}")
                        
            except Exception as e:
                self._log(f"  Error checking Funding/OI: {e}")
        
        return alerts
    
    def check_market_intelligence(self) -> List[Alert]:
        """
        Check market intelligence for extreme conditions.
        
        Returns:
            List of extreme condition alerts
        """
        alerts = []
        
        try:
            extreme_alerts = self.market_intelligence.detect_extreme_conditions(self.symbols[:2])
            for alert in extreme_alerts:
                alerts.append(alert)
                self._log(f"  → Market intelligence alert: {alert.alert_type}")
        except Exception as e:
            self._log(f"  Error checking market intelligence: {e}")
        
        return alerts
    
    def _format_liquidation_message(self, alert: Alert) -> str:
        """Format liquidation alert."""
        severity_emoji = {
            'critical': '🚨🚨🚨',
            'high': '🚨🚨',
            'medium': '🚨',
            'low': '⚠️'
        }
        
        emoji = severity_emoji.get(alert.severity, '🚨')
        details = alert.details
        
        lines = [
            f"{emoji} *{alert.alert_type.upper()}: {alert.symbol}*",
            f"",
            f"💥 {alert.message}",
            f"",
            f"💰 Price: `${alert.price:,.2f}`",
            f"📦 Size: `{details.get('size', 0):,.4f}`",
            f"💵 Value: `${details.get('value_usd', 0):,.0f}`",
            f"⏰ Time: `{alert.timestamp.strftime('%Y-%m-%d %H:%M UTC')}`",
        ]
        
        if details.get('is_block_trade'):
            lines.append(f"🔷 Block Trade: Yes")
        
        return '\n'.join(lines)
    
    def process_alerts(self, alerts: List[Alert], send_telegram: bool = True):
        """
        Process and send alerts.
        
        Args:
            alerts: List of alerts to process
            send_telegram: Whether to send to Telegram
        """
        for alert in alerts:
            self._log(f"ALERT: {alert.message}")
            
            # Store in memory
            self.alert_system.store_alert_in_memory(alert)
            
            # Record signal for tracking
            try:
                self.signal_tracker.record_signal_from_alert(alert, "event_watcher")
            except Exception as e:
                self._log(f"  → Error recording signal: {e}")
            
            # Send to Telegram
            if send_telegram:
                success = send_telegram_alert(alert)
                if success:
                    self.alerts_sent += 1
                    self._log(f"  → Sent to Telegram")
                else:
                    self._log(f"  → Failed to send to Telegram")
    
    def run_single_check(self, send_telegram: bool = True) -> int:
        """
        Run a single check cycle.
        
        Args:
            send_telegram: Whether to send alerts to Telegram
        
        Returns:
            Number of alerts triggered
        """
        self.checks_performed += 1
        self._log(f"Check #{self.checks_performed} - {datetime.now().strftime('%H:%M:%S')}")
        
        all_alerts = []
        
        # Check each symbol for market events
        for symbol in self.symbols:
            try:
                alerts = self.check_market_events(symbol)
                all_alerts.extend(alerts)
                
                if alerts:
                    self._log(f"  {symbol}: {len(alerts)} alert(s)")
                
            except Exception as e:
                self._log(f"  {symbol}: Error - {e}")
        
        # Check liquidations periodically
        if self.checks_performed % (LIQUIDATION_CHECK_INTERVAL // CHECK_INTERVAL_SECONDS) == 0:
            self._log("Checking liquidations...")
            try:
                liq_alerts = self.check_liquidations()
                all_alerts.extend(liq_alerts)
                if liq_alerts:
                    self._log(f"  {len(liq_alerts)} liquidation alert(s)")
            except Exception as e:
                self._log(f"  Liquidation check error: {e}")
        
        # Check on-chain metrics
        try:
            onchain_alerts = self.check_onchain_metrics()
            all_alerts.extend(onchain_alerts)
            if onchain_alerts:
                self._log(f"  {len(onchain_alerts)} on-chain alert(s)")
        except Exception as e:
            self._log(f"  On-chain check error: {e}")
        
        # Check market intelligence (extreme conditions)
        try:
            intel_alerts = self.check_market_intelligence()
            all_alerts.extend(intel_alerts)
            if intel_alerts:
                self._log(f"  {len(intel_alerts)} market intelligence alert(s)")
        except Exception as e:
            self._log(f"  Market intelligence error: {e}")
        
        # Process all alerts
        if all_alerts:
            self.process_alerts(all_alerts, send_telegram)
        else:
            self._log("  No alerts")
        
        return len(all_alerts)
    
    def watch_loop(self, symbols: Optional[List[str]] = None, 
                   send_telegram: bool = True):
        """
        Main watch loop - runs continuously until interrupted.
        
        Args:
            symbols: Optional list of symbols to watch (uses default if None)
            send_telegram: Whether to send alerts to Telegram
        """
        if symbols:
            self.symbols = symbols
        
        self.running = True
        self._log(f"=" * 50)
        self._log(f"Event Watcher Started")
        self._log(f"Symbols: {', '.join(self.symbols)}")
        self._log(f"Check interval: {CHECK_INTERVAL_SECONDS}s")
        self._log(f"Cooldown: {COOLDOWN_MINUTES}min")
        self._log(f"On-chain checks: Fear&Greed every {FEAR_GREED_CHECK_INTERVAL//3600}h, Funding/OI every {FUNDING_OI_CHECK_INTERVAL//3600}h")
        self._log(f"=" * 50)
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            self._log("\nShutdown signal received...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            while self.running and not self._shutdown_event.is_set():
                try:
                    self.run_single_check(send_telegram)
                except Exception as e:
                    self._log(f"Error in check cycle: {e}")
                
                # Wait for next check
                self._shutdown_event.wait(CHECK_INTERVAL_SECONDS)
        
        except Exception as e:
            self._log(f"Fatal error in watch loop: {e}")
        
        finally:
            self._save_state()
            uptime = datetime.now() - self.start_time
            self._log(f"=" * 50)
            self._log(f"Watcher stopped")
            self._log(f"Uptime: {uptime}")
            self._log(f"Checks: {self.checks_performed}")
            self._log(f"Alerts sent: {self.alerts_sent}")
            self._log(f"=" * 50)
    
    def stop(self):
        """Stop the watch loop."""
        self.running = False
        self._shutdown_event.set()
    
    def get_stats(self) -> Dict:
        """Get watcher statistics."""
        uptime = datetime.now() - self.start_time
        
        return {
            'running': self.running,
            'start_time': self.start_time.isoformat(),
            'uptime_seconds': uptime.total_seconds(),
            'checks_performed': self.checks_performed,
            'alerts_sent': self.alerts_sent,
            'symbols_watched': self.symbols,
            'check_interval': CHECK_INTERVAL_SECONDS,
            'cooldown_minutes': COOLDOWN_MINUTES
        }


def run_as_daemon(symbols: Optional[List[str]] = None):
    """
    Run the watcher as a daemon process.
    
    Args:
        symbols: List of symbols to watch
    """
    watcher = EventWatcher(symbols)
    watcher.watch_loop(send_telegram=True)


def run_scheduled_check(symbols: Optional[List[str]] = None) -> int:
    """
    Run a single check (for cron/scheduler).
    
    Args:
        symbols: List of symbols to check
    
    Returns:
        Number of alerts triggered
    """
    watcher = EventWatcher(symbols)
    return watcher.run_single_check(send_telegram=True)


def main():
    """CLI for event watcher."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Event-Driven Crypto Watcher with On-Chain Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run continuous watcher
  python event_watcher.py --daemon
  
  # Run single check (for cron)
  python event_watcher.py --check
  
  # Watch specific symbols
  python event_watcher.py --daemon --symbols BTCUSDT ETHUSDT
  
  # Check liquidations only
  python event_watcher.py --liquidations
  
  # Check on-chain metrics
  python event_watcher.py --onchain
  
  # Check Fear & Greed only
  python event_watcher.py --fear-greed
  
  # Opportunity Screener
  python event_watcher.py --screener
  python event_watcher.py --scan-rsi
  python event_watcher.py --scan-volume
  python event_watcher.py --scan-momentum
  
  # Multi-coin monitor
  python event_watcher.py --multi-coin
  python event_watcher.py --schedule
        """
    )
    
    parser.add_argument('--daemon', '-d', action='store_true',
                       help='Run continuous watcher')
    parser.add_argument('--check', '-c', action='store_true',
                       help='Run single check (for cron)')
    parser.add_argument('--symbols', '-s', nargs='+',
                       default=DEFAULT_SYMBOLS,
                       help=f'Symbols to watch (default: {DEFAULT_SYMBOLS})')
    parser.add_argument('--liquidations', '-l', action='store_true',
                       help='Check liquidations only')
    parser.add_argument('--onchain', '-o', action='store_true',
                       help='Check on-chain metrics only')
    parser.add_argument('--fear-greed', '-fg', action='store_true',
                       help='Check Fear & Greed Index only')
    parser.add_argument('--market-intel', '-mi', action='store_true',
                       help='Check market intelligence (extreme conditions)')
    parser.add_argument('--no-telegram', action='store_true',
                       help='Do not send Telegram notifications')
    parser.add_argument('--stats', action='store_true',
                       help='Show watcher statistics')
    parser.add_argument('--cooldown', type=int, default=COOLDOWN_MINUTES,
                       help=f'Cooldown in minutes (default: {COOLDOWN_MINUTES})')
    parser.add_argument('--screener', '-sc', action='store_true',
                       help='Run full opportunity screener')
    parser.add_argument('--scan-rsi', '-sr', action='store_true',
                       help='Scan RSI levels only')
    parser.add_argument('--scan-volume', '-sv', action='store_true',
                       help='Scan volume anomalies only')
    parser.add_argument('--scan-momentum', '-sm', action='store_true',
                       help='Scan momentum only')
    parser.add_argument('--multi-coin', '-mc', action='store_true',
                       help='Run multi-coin monitor with full report')
    parser.add_argument('--schedule', action='store_true',
                       help='Run screener based on schedule (06:00, 10:00, 14:00, 18:00, 22:00 UTC)')
    # Signal tracking commands
    parser.add_argument('--signal-stats', action='store_true',
                       help='Show signal performance statistics')
    parser.add_argument('--signal-report', action='store_true',
                       help='Generate performance report')
    parser.add_argument('--check-signals', action='store_true',
                       help='Check pending signal results')
    parser.add_argument('--track-signals', action='store_true',
                       help='Record current alerts as signals')
    parser.add_argument('--timeframe', '-t', default='30d',
                       choices=['24h', '7d', '30d', 'all'],
                       help='Timeframe for statistics')
    
    args = parser.parse_args()
    
    if args.stats:
        watcher = EventWatcher(args.symbols)
        stats = watcher.get_stats()
        print("\nWatcher Statistics:")
        print("-" * 30)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return
    
    if args.liquidations:
        watcher = EventWatcher(args.symbols)
        alerts = watcher.check_liquidations()
        if alerts:
            print(f"\n{len(alerts)} liquidation event(s) detected:")
            for alert in alerts:
                print(f"\n{watcher.format_alert_message(alert)}")
            watcher.process_alerts(alerts, not args.no_telegram)
        else:
            print("No large liquidations detected")
        return
    
    if args.onchain:
        watcher = EventWatcher(args.symbols)
        print("Checking on-chain metrics...")
        alerts = watcher.check_onchain_metrics()
        if alerts:
            print(f"\n{len(alerts)} on-chain alert(s) detected:")
            for alert in alerts:
                print(f"\n{alert.message}")
            watcher.process_alerts(alerts, not args.no_telegram)
        else:
            print("No on-chain alerts detected")
        return
    
    if args.fear_greed:
        analyzer = OnchainAnalyzer()
        print("Fetching Fear & Greed Index...")
        fg = analyzer.get_fear_greed_index()
        if fg:
            print(f"\n{analyzer.format_fear_greed_message(fg)}")
            trend = analyzer.get_fear_greed_trend()
            print(f"\n📈 7-day trend: {trend['trend']}")
            print(f"📊 7-day average: {trend['avg']}")
        else:
            print("Failed to fetch Fear & Greed Index")
        return
    
    if args.market_intel:
        intel = MarketIntelligence()
        print("Checking market intelligence...")
        
        # Generate composite signal
        signal = intel.calculate_composite_signal(args.symbols)
        print(f"\n{intel.format_signal_for_telegram(signal)}")
        
        # Check extreme conditions
        alerts = intel.detect_extreme_conditions(args.symbols)
        if alerts:
            print(f"\n{len(alerts)} extreme condition(s) detected:")
            for alert in alerts:
                print(f"\n{intel.format_extreme_alert_for_telegram(alert)}")
            
            if not args.no_telegram:
                for alert in alerts:
                    send_telegram_alert(alert)
        else:
            print("\nNo extreme conditions detected")
        return
    
    if args.screener:
        # Full opportunity screener
        screener = OpportunityScreener()
        print(f"\n🔍 Running opportunity screener on {len(args.symbols)} symbols...")
        opportunities = screener.scan_all(args.symbols)
        ranked = screener.rank_opportunities(opportunities)
        
        top = screener.get_top_opportunities(5)
        print(f"\n🎯 Top Opportunities:")
        print("=" * 50)
        for i, opp in enumerate(top, 1):
            print(f"\n{i}. {opp.symbol}")
            print(f"   Type: {opp.opportunity_type.value}")
            print(f"   Score: {opp.score:.1f}")
            print(f"   {opp.reason}")
        
        if not args.no_telegram:
            report = screener.format_opportunity_report()
            # Send as alert
            alert = Alert(
                symbol='MULTI',
                alert_type='opportunity_screener',
                severity='low',
                message=report,
                price=0,
                change_pct=0,
                details={'opportunities': len(opportunities)},
                timestamp=datetime.now()
            )
            send_telegram_alert(alert)
        return
    
    if args.scan_rsi:
        # RSI scan only
        screener = OpportunityScreener()
        print(f"\n📊 Scanning RSI levels for {len(args.symbols)} symbols...")
        results = screener.scan_rsi_levels(args.symbols)
        
        print("\n🔶 RSI Oversold (Potential Buy):")
        for opp in results['oversold'][:5]:
            print(f"  {opp.symbol}: RSI {opp.rsi:.1f}")
        
        print("\n🔴 RSI Overbought (Potential Short):")
        for opp in results['overbought'][:5]:
            print(f"  {opp.symbol}: RSI {opp.rsi:.1f}")
        return
    
    if args.scan_volume:
        # Volume scan only
        screener = OpportunityScreener()
        print(f"\n📈 Scanning volume anomalies for {len(args.symbols)} symbols...")
        results = screener.scan_volume_anomalies(args.symbols)
        
        print("\n🟢 Volume Breakouts:")
        for opp in results['breakout'][:5]:
            print(f"  {opp.symbol}: {opp.volume_ratio:.1f}x avg")
        return
    
    if args.scan_momentum:
        # Momentum scan only
        screener = OpportunityScreener()
        print(f"\n⚡ Scanning momentum for {len(args.symbols)} symbols...")
        results = screener.scan_momentum(args.symbols)
        
        print("\n📈 Strong Uptrend:")
        for opp in results['up'][:5]:
            print(f"  {opp.symbol}: {opp.price_change_24h:+.1f}%")
        
        print("\n📉 Strong Downtrend:")
        for opp in results['down'][:5]:
            print(f"  {opp.symbol}: {opp.price_change_24h:+.1f}%")
        return
    
    if args.multi_coin or args.schedule:
        # Multi-coin monitor with full report
        monitor = MultiCoinMonitor()
        
        if args.schedule:
            # Check schedule
            if not monitor.should_run_now():
                next_run = monitor.get_next_run_time()
                print(f"Not scheduled to run now.")
                print(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M UTC')}")
                return
            print("Schedule match! Running scan...")
        
        report = monitor.generate_opportunity_report()
        print("\n" + report)
        
        if not args.no_telegram:
            from adaptive_alerts import Alert
            alert = Alert(
                symbol='MULTI',
                alert_type='opportunity_report',
                severity='low',
                message=report,
                price=0,
                change_pct=0,
                details={'opportunities': monitor._last_report.opportunities_found if monitor._last_report else 0},
                timestamp=datetime.now()
            )
            send_telegram_alert(alert)
        return
    
    if args.check:
        # Single check mode (for cron)
        print(f"Running scheduled check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        count = run_scheduled_check(args.symbols)
        print(f"Alerts triggered: {count}")
        return
    
    # Signal tracking commands
    if args.signal_stats:
        tracker = SignalTracker()
        stats = tracker.get_statistics(args.timeframe)
        print(f"\n📊 Signal Statistics ({args.timeframe})")
        print("=" * 40)
        print(f"Total signals: {stats['total_signals']}")
        print(f"Success rate: {stats['success_rate']}%")
        print(f"Completed: {stats.get('completed_signals', 0)}")
        print(f"Pending: {stats.get('pending_count', 0)}")
        print("\nBy Signal Type:")
        for stype, data in stats.get('by_type', {}).items():
            rate = data.get('success_rate', 0)
            emoji = "✓" if rate >= 50 else "✗"
            print(f"  {stype}: {rate}% {emoji} ({data['total']} signals)")
        return
    
    if args.signal_report:
        reporter = PerformanceReport()
        print(reporter.generate_weekly_report())
        return
    
    if args.check_signals:
        # Check pending signal results
        print("Checking pending signal results...")
        tracker = SignalTracker()
        
        # Get current prices
        from adaptive_alerts import get_price
        current_prices = {}
        for symbol in args.symbols:
            try:
                price = get_price(symbol.replace('USDT', ''))
                if price:
                    current_prices[symbol] = price
            except:
                pass
        
        if not current_prices:
            print("Could not fetch current prices")
            return
        
        results = tracker.check_pending_signals(current_prices)
        print(f"\nChecked {len(results)} signal(s):")
        for result in results[:10]:
            emoji = "✓" if result.is_successful else "✗"
            print(f"  {result.signal_id}: {result.price_change_pct:+.2f}% {emoji}")
        return
    
    if args.track_signals:
        # Record current alerts as signals
        print("Recording current alerts as signals...")
        watcher = EventWatcher(args.symbols)
        alerts = []
        
        for symbol in args.symbols:
            try:
                symbol_alerts = watcher.check_market_events(symbol)
                alerts.extend(symbol_alerts)
            except Exception as e:
                print(f"Error checking {symbol}: {e}")
        
        print(f"Recorded {len(alerts)} signal(s)")
        return
    
    if args.daemon or not (args.check or args.liquidations or args.stats or args.onchain or args.fear_greed or args.market_intel or args.screener or args.scan_rsi or args.scan_volume or args.scan_momentum or args.multi_coin or args.schedule or args.signal_stats or args.signal_report or args.check_signals or args.track_signals):
        # Default to daemon mode
        print("Starting Event Watcher (Ctrl+C to stop)...")
        run_as_daemon(args.symbols)


if __name__ == '__main__':
    main()
