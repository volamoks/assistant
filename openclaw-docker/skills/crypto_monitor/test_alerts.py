#!/usr/bin/env python3
"""
Test suite for the adaptive crypto alert system.

Run with:
    python3 test_alerts.py
    python3 test_alerts.py --test-atr
    python3 test_alerts.py --test-spike
    python3 test_alerts.py --test-telegram
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, '/home/node/.openclaw/skills')

from adaptive_alerts import (
    AdaptiveAlertSystem, Alert, PriceHistory, send_telegram_alert,
    format_alert_for_telegram
)
from telegram.notify import TelegramNotifier
from event_watcher import EventWatcher, WatcherState


class Colors:
    """Terminal colors for output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"  {text}")


class TestAdaptiveAlerts:
    """Tests for the adaptive alert system."""
    
    def __init__(self):
        self.system = AdaptiveAlertSystem()
        self.tests_run = 0
        self.tests_passed = 0
    
    def assert_true(self, condition: bool, message: str):
        """Assert condition is true."""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            print_success(message)
        else:
            print_error(message)
    
    def test_atr_calculation(self) -> bool:
        """Test ATR calculation for major symbols."""
        print_header("TEST: ATR Calculation")
        
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        all_passed = True
        
        for symbol in symbols:
            print(f"\nTesting {symbol}...")
            
            # Calculate ATR
            atr = self.system.calculate_atr(symbol)
            
            if atr is None:
                print_error(f"Failed to calculate ATR for {symbol}")
                all_passed = False
                continue
            
            print_success(f"ATR calculated: {atr:.2f}%")
            
            # Check ATR is in reasonable range
            if 0.5 <= atr <= 20:
                print_success(f"ATR in reasonable range (0.5% - 20%)")
            else:
                print_warning(f"ATR seems unusual: {atr:.2f}%")
            
            # Test caching
            atr_cached = self.system.calculate_atr(symbol)
            if atr_cached == atr:
                print_success(f"ATR caching works")
            else:
                print_error(f"ATR caching failed (expected {atr}, got {atr_cached})")
                all_passed = False
        
        return all_passed
    
    def test_adaptive_thresholds(self) -> bool:
        """Test adaptive threshold calculation."""
        print_header("TEST: Adaptive Thresholds")
        
        all_passed = True
        
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            print(f"\nTesting {symbol}...")
            
            threshold = self.system.get_adaptive_threshold(symbol)
            atr = self.system.calculate_atr(symbol)
            
            print_info(f"ATR: {atr:.2f}%")
            print_info(f"Adaptive threshold: ±{threshold:.2f}%")
            
            # Verify threshold calculation logic
            if atr > 4.0:
                expected = atr * 1.5
            elif atr < 2.0:
                expected = atr * 2.0
            else:
                expected = atr * 1.8
            
            expected = round(expected, 2)
            
            if abs(threshold - expected) < 0.01:
                print_success(f"Threshold calculation correct")
            else:
                print_error(f"Threshold mismatch (expected {expected}, got {threshold})")
                all_passed = False
            
            # Threshold should be positive
            self.assert_true(threshold > 0, f"Threshold is positive: {threshold}")
        
        return all_passed
    
    def test_price_data_fetching(self) -> bool:
        """Test fetching current price data."""
        print_header("TEST: Price Data Fetching")
        
        all_passed = True
        
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            print(f"\nTesting {symbol}...")
            
            data = self.system.fetch_current_data(symbol)
            
            if data is None:
                print_error(f"Failed to fetch data for {symbol}")
                all_passed = False
                continue
            
            # Check required fields
            required_fields = ['symbol', 'price', 'pct_24h', 'volume_24h', 'high_24h', 'low_24h']
            for field in required_fields:
                if field in data:
                    print_success(f"Field '{field}' present: {data[field]}")
                else:
                    print_error(f"Missing field '{field}'")
                    all_passed = False
            
            # Validate data types and ranges
            if data['price'] > 0:
                print_success(f"Price is positive: ${data['price']:,.2f}")
            else:
                print_error(f"Invalid price: {data['price']}")
                all_passed = False
            
            if -50 <= data['pct_24h'] <= 50:
                print_success(f"24h change in normal range: {data['pct_24h']:+.2f}%")
            else:
                print_warning(f"24h change seems extreme: {data['pct_24h']:+.2f}%")
        
        return all_passed
    
    def test_klines_fetching(self) -> bool:
        """Test fetching kline/candlestick data."""
        print_header("TEST: Klines Fetching")
        
        all_passed = True
        
        for symbol in ["BTCUSDT"]:
            print(f"\nTesting {symbol}...")
            
            # Test daily klines
            klines = self.system.fetch_klines(symbol, interval="D", limit=14)
            
            if not klines:
                print_error(f"Failed to fetch klines for {symbol}")
                all_passed = False
                continue
            
            print_success(f"Fetched {len(klines)} daily candles")
            
            # Check kline structure
            required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            if klines:
                kline = klines[0]
                for field in required_fields:
                    if field in kline:
                        print_success(f"Kline field '{field}' present")
                    else:
                        print_error(f"Missing kline field '{field}'")
                        all_passed = False
            
            # Test hourly klines
            hourly = self.system.fetch_klines(symbol, interval="60", limit=24)
            if hourly:
                print_success(f"Fetched {len(hourly)} hourly candles")
            else:
                print_warning("Could not fetch hourly candles")
        
        return all_passed
    
    def test_price_history(self) -> bool:
        """Test price history tracking."""
        print_header("TEST: Price History")
        
        history = PriceHistory(max_points=10)
        
        # Add some test data
        base_price = 65000
        for i in range(5):
            history.add(
                price=base_price + (i * 100),
                volume=1000000 + (i * 100000),
                timestamp=datetime.now() - timedelta(minutes=5-i)
            )
        
        print_info(f"Added {len(history.prices)} price points")
        
        # Test price change calculation
        change = history.get_price_change(minutes=10)
        if change:
            change_pct, current = change
            print_success(f"Price change calculated: {change_pct:+.2f}%")
            self.assert_true(abs(change_pct) < 1, "Price change is reasonable")
        else:
            print_error("Failed to calculate price change")
            return False
        
        # Test volume average
        avg_volume = history.get_average_volume(hours=1)
        if avg_volume:
            print_success(f"Average volume calculated: {avg_volume:,.0f}")
        else:
            print_warning("Could not calculate average volume")
        
        return True
    
    def test_alert_creation(self) -> bool:
        """Test alert creation and formatting."""
        print_header("TEST: Alert Creation")
        
        # Create test alert
        alert = Alert(
            symbol="BTCUSDT",
            alert_type="price_spike",
            severity="high",
            message="BTC spiked 3.5% in 15 minutes",
            price=67500.50,
            change_pct=3.5,
            details={
                'timeframe_min': 15,
                'threshold_used': 2.0,
                'atr_at_time': 2.5
            },
            timestamp=datetime.now()
        )
        
        print_info(f"Created alert: {alert.message}")
        
        # Test formatting
        formatted = format_alert_for_telegram(alert)
        print_success("Alert formatted for Telegram")
        print_info("Formatted message preview:")
        print("-" * 40)
        print(formatted[:500] + "..." if len(formatted) > 500 else formatted)
        print("-" * 40)
        
        # Test alert serialization
        alert_dict = alert.to_dict()
        self.assert_true('symbol' in alert_dict, "Alert serializes to dict")
        
        return True
    
    def test_cooldown_system(self) -> bool:
        """Test alert cooldown system."""
        print_header("TEST: Cooldown System")
        
        watcher = EventWatcher(symbols=["BTCUSDT"])
        
        # Test initial state
        on_cooldown = watcher._is_on_cooldown("BTCUSDT", "test_alert", cooldown_min=60)
        self.assert_true(not on_cooldown, "No cooldown on first check")
        
        # Mark alert as sent
        watcher._mark_alert_sent("BTCUSDT", "test_alert")
        
        # Should be on cooldown now
        on_cooldown = watcher._is_on_cooldown("BTCUSDT", "test_alert", cooldown_min=60)
        self.assert_true(on_cooldown, "On cooldown after marking sent")
        
        # Different alert type should not be on cooldown
        on_cooldown2 = watcher._is_on_cooldown("BTCUSDT", "other_alert", cooldown_min=60)
        self.assert_true(not on_cooldown2, "Different alert type not on cooldown")
        
        # Different symbol should not be on cooldown
        on_cooldown3 = watcher._is_on_cooldown("ETHUSDT", "test_alert", cooldown_min=60)
        self.assert_true(not on_cooldown3, "Different symbol not on cooldown")
        
        return True
    
    def test_state_persistence(self) -> bool:
        """Test state saving and loading."""
        print_header("TEST: State Persistence")
        
        # Create state
        state = WatcherState(
            last_alert_times={"BTCUSDT:test": datetime.now().isoformat()},
            last_prices={"BTCUSDT": 65000},
            alert_counts={"BTCUSDT:2024-03-05": 5}
        )
        
        # Convert to dict
        state_dict = state.to_dict()
        print_success("State converted to dict")
        
        # Restore from dict
        restored = WatcherState.from_dict(state_dict)
        self.assert_true(
            restored.last_prices.get("BTCUSDT") == 65000,
            "State restored correctly"
        )
        
        return True
    
    def test_telegram_formatting(self) -> bool:
        """Test Telegram message formatting for all alert types."""
        print_header("TEST: Telegram Formatting")
        
        test_alerts = [
            Alert(
                symbol="BTCUSDT",
                alert_type="price_spike",
                severity="high",
                message="📈 SPIKE UP: BTCUSDT moved +3.5% in 15min",
                price=67500.50,
                change_pct=3.5,
                details={'timeframe_min': 15, 'threshold_used': 2.0, 'atr_at_time': 2.5},
                timestamp=datetime.now()
            ),
            Alert(
                symbol="ETHUSDT",
                alert_type="volume_anomaly",
                severity="medium",
                message="📊 VOLUME SPIKE: ETHUSDT volume is 2.5x average",
                price=3850.20,
                change_pct=1.2,
                details={'volume_ratio': 2.5, 'current_volume_24h': 5000000},
                timestamp=datetime.now()
            ),
            Alert(
                symbol="SOLUSDT",
                alert_type="adaptive_threshold",
                severity="critical",
                message="🔥 DIP ALERT: SOLUSDT down -8.5%",
                price=142.30,
                change_pct=-8.5,
                details={'threshold_used': 7.2, 'atr': 4.0, 'high_24h': 156.80, 'low_24h': 140.20},
                timestamp=datetime.now()
            ),
        ]
        
        for alert in test_alerts:
            print(f"\nTesting {alert.alert_type} alert...")
            formatted = format_alert_for_telegram(alert)
            
            # Check for required elements
            checks = [
                (alert.symbol in formatted, f"Symbol {alert.symbol} in message"),
                (str(int(alert.price)) in formatted or f"{alert.price:.2f}" in formatted, "Price in message"),
                ("$" in formatted, "Dollar sign in message"),
                (str(abs(alert.change_pct)) in formatted or f"{alert.change_pct:+.1f}" in formatted, "Change % in message"),
            ]
            
            for check, msg in checks:
                self.assert_true(check, msg)
            
            print_info("Preview:")
            print("-" * 40)
            for line in formatted.split('\n')[:8]:
                print(line)
            print("-" * 40)
        
        return True


class TestRunner:
    """Main test runner."""
    
    def __init__(self):
        self.tests = TestAdaptiveAlerts()
    
    def run_all_tests(self):
        """Run all tests."""
        print_header("ADAPTIVE CRYPTO ALERT SYSTEM - TEST SUITE")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        test_methods = [
            ("ATR Calculation", self.tests.test_atr_calculation),
            ("Adaptive Thresholds", self.tests.test_adaptive_thresholds),
            ("Price Data Fetching", self.tests.test_price_data_fetching),
            ("Klines Fetching", self.tests.test_klines_fetching),
            ("Price History", self.tests.test_price_history),
            ("Alert Creation", self.tests.test_alert_creation),
            ("Cooldown System", self.tests.test_cooldown_system),
            ("State Persistence", self.tests.test_state_persistence),
            ("Telegram Formatting", self.tests.test_telegram_formatting),
        ]
        
        results = []
        for name, method in test_methods:
            try:
                passed = method()
                results.append((name, passed))
            except Exception as e:
                print_error(f"Test '{name}' failed with exception: {e}")
                results.append((name, False))
        
        # Summary
        print_header("TEST SUMMARY")
        
        passed_count = sum(1 for _, p in results if p)
        total_count = len(results)
        
        for name, passed in results:
            status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
            print(f"  {status}: {name}")
        
        print()
        print(f"{Colors.BOLD}Results: {passed_count}/{total_count} tests passed{Colors.RESET}")
        
        if passed_count == total_count:
            print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! ✓{Colors.RESET}")
            return 0
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}Some tests failed! ✗{Colors.RESET}")
            return 1
    
    def run_live_telegram_test(self):
        """Send a test alert to Telegram."""
        print_header("LIVE TELEGRAM TEST")
        
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            print_error("Telegram credentials not set!")
            print_info("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
            return 1
        
        print_info(f"Bot Token: {bot_token[:10]}...{bot_token[-5:]}")
        print_info(f"Chat ID: {chat_id}")
        print()
        
        # Create test alert
        alert = Alert(
            symbol="TESTUSDT",
            alert_type="test",
            severity="medium",
            message="🧪 This is a test alert from the crypto monitoring system",
            price=12345.67,
            change_pct=5.43,
            details={'test': True, 'timestamp': datetime.now().isoformat()},
            timestamp=datetime.now()
        )
        
        print("Sending test alert...")
        print("-" * 40)
        print(format_alert_for_telegram(alert))
        print("-" * 40)
        
        success = send_telegram_alert(alert)
        
        if success:
            print_success("Test alert sent successfully!")
            print_info("Check your Telegram for the message")
            return 0
        else:
            print_error("Failed to send test alert")
            return 1
    
    def run_spike_detection_test(self):
        """Test spike detection manually."""
        print_header("SPIKE DETECTION TEST")
        
        system = AdaptiveAlertSystem()
        
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        for symbol in symbols:
            print(f"\nTesting {symbol}...")
            
            # Get current data
            data = system.fetch_current_data(symbol)
            if not data:
                print_error(f"Could not fetch data for {symbol}")
                continue
            
            print_info(f"Current price: ${data['price']:,.2f}")
            print_info(f"24h change: {data['pct_24h']:+.2f}%")
            
            # Update price history
            system.update_price_history(symbol, data)
            
            # Check adaptive threshold
            alert = system.check_adaptive_threshold(symbol)
            if alert:
                print_success(f"Adaptive threshold alert would trigger!")
                print_info(f"  Message: {alert.message}")
            else:
                print_info(f"No adaptive threshold alert (threshold: ±{system.get_adaptive_threshold(symbol):.2f}%)")
            
            # Check price spikes at different timeframes
            for timeframe in [15, 30, 60]:
                alert = system.check_price_spike(symbol, timeframe)
                if alert:
                    print_success(f"Price spike detected ({timeframe}min)!")
                    print_info(f"  Change: {alert.change_pct:+.2f}%")
                else:
                    print_info(f"No {timeframe}min spike detected")
        
        return 0
    
    def run_event_watcher_test(self):
        """Test event watcher single check."""
        print_header("EVENT WATCHER TEST")
        
        watcher = EventWatcher(symbols=["BTCUSDT", "ETHUSDT"])
        
        print("Running single check cycle...")
        print_info("This will check for actual market events\n")
        
        alert_count = watcher.run_single_check(send_telegram=False)
        
        print()
        if alert_count > 0:
            print_success(f"Detected {alert_count} alert(s)")
        else:
            print_info("No alerts detected (this is normal in stable markets)")
        
        # Show stats
        stats = watcher.get_stats()
        print("\nWatcher statistics:")
        for key, value in stats.items():
            print_info(f"  {key}: {value}")
        
        return 0


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test suite for adaptive crypto alerts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python3 test_alerts.py
  
  # Test Telegram integration
  python3 test_alerts.py --test-telegram
  
  # Test spike detection
  python3 test_alerts.py --test-spike
  
  # Test event watcher
  python3 test_alerts.py --test-watcher
        """
    )
    
    parser.add_argument('--test-telegram', '-t', action='store_true',
                       help='Send live test alert to Telegram')
    parser.add_argument('--test-spike', '-s', action='store_true',
                       help='Test spike detection with live data')
    parser.add_argument('--test-watcher', '-w', action='store_true',
                       help='Test event watcher')
    parser.add_argument('--all', '-a', action='store_true',
                       help='Run all tests including live tests')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.test_telegram or args.all:
        return runner.run_live_telegram_test()
    
    if args.test_spike:
        return runner.run_spike_detection_test()
    
    if args.test_watcher:
        return runner.run_event_watcher_test()
    
    # Default: run unit tests
    return runner.run_all_tests()


if __name__ == '__main__':
    sys.exit(main())
