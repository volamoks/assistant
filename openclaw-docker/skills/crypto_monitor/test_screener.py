#!/usr/bin/env python3
"""
Test Suite for Opportunity Screener

Tests the functionality of:
- technical_analysis.py
- opportunity_screener.py
- multi_coin_monitor.py
"""

import sys
import unittest
import time
from datetime import datetime

sys.path.insert(0, '/home/node/.openclaw/skills')

from technical_analysis import TechnicalAnalyzer
from opportunity_screener import OpportunityScreener, OpportunityType, OpportunityStrength
from multi_coin_monitor import MultiCoinMonitor


# ── Test Utilities ──────────────────────────────────────────────────────────────

def print_header(text: str):
    """Print test header."""
    print(f"\n{'='*60}")
    print(f" {text}")
    print('='*60)


def print_success(text: str):
    """Print success message."""
    print(f"✅ {text}")


def print_error(text: str):
    """Print error message."""
    print(f"❌ {text}")


def print_info(text: str):
    """Print info message."""
    print(f"ℹ️  {text}")


# ── Test Cases ────────────────────────────────────────────────────────────────

class TestTechnicalAnalyzer(unittest.TestCase):
    """Tests for TechnicalAnalyzer."""
    
    @classmethod
    def setUpClass(cls):
        cls.analyzer = TechnicalAnalyzer()
        cls.test_symbol = "BTCUSDT"
        cls.test_symbols = ["BTCUSDT", "ETHUSDT"]
    
    def test_klines_fetching(self):
        """Test fetching kline data."""
        print_header("TEST: Klines Fetching")
        
        klines = self.analyzer.fetch_klines(self.test_symbol, interval="D", limit=50)
        
        if not klines:
            print_error(f"Failed to fetch klines for {self.test_symbol}")
            self.fail("Could not fetch klines")
        
        print_success(f"Fetched {len(klines)} klines")
        
        # Check structure
        required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        kline = klines[0]
        for field in required_fields:
            if field in kline:
                print_success(f"Kline field '{field}' present")
            else:
                print_error(f"Missing kline field '{field}'")
                self.fail(f"Missing field: {field}")
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        print_header("TEST: RSI Calculation")
        
        # Test with sample data
        prices = [44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64, 46.37]
        
        rsi = self.analyzer.calculate_rsi(prices, period=14)
        
        if rsi is None:
            print_error("RSI calculation returned None")
            self.fail("RSI calculation failed")
        
        print_success(f"RSI calculated: {rsi:.2f}")
        
        # RSI should be reasonable (0-100)
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)
        print_success(f"RSI value in valid range: 0-100")
    
    def test_rsi_fetching(self):
        """Test fetching RSI for a symbol."""
        print_header("TEST: RSI Fetching")
        
        rsi = self.analyzer.fetch_rsi(self.test_symbol)
        
        if rsi is None:
            print_error("Failed to fetch RSI")
            self.fail("Could not fetch RSI")
        
        print_success(f"RSI for {self.test_symbol}: {rsi:.2f}")
        
        # RSI should be reasonable
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)
    
    def test_sma_calculation(self):
        """Test SMA calculation."""
        print_header("TEST: SMA Calculation")
        
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
        
        sma_5 = self.analyzer.calculate_sma(prices, 5)
        sma_10 = self.analyzer.calculate_sma(prices, 10)
        
        if sma_5 is None or sma_10 is None:
            print_error("SMA calculation returned None")
            self.fail("SMA calculation failed")
        
        print_success(f"SMA(5): {sma_5:.2f}")
        print_success(f"SMA(10): {sma_10:.2f}")
        
        # Verify calculation
        expected_sma_5 = sum(prices[-5:]) / 5
        self.assertAlmostEqual(sma_5, expected_sma_5, places=2)
    
    def test_sma_fetching(self):
        """Test fetching SMA for a symbol."""
        print_header("TEST: SMA Fetching")
        
        sma_20 = self.analyzer.fetch_sma(self.test_symbol, 20)
        
        if sma_20 is None:
            print_error("Failed to fetch SMA")
            self.fail("Could not fetch SMA")
        
        print_success(f"SMA(20) for {self.test_symbol}: ${sma_20:,.2f}")
    
    def test_trend_detection(self):
        """Test trend detection."""
        print_header("TEST: Trend Detection")
        
        # Uptrend
        up_prices = [100, 102, 104, 103, 106, 108, 107, 110, 112, 111, 114, 116, 115, 118, 120]
        
        trend = self.analyzer.detect_trend(up_prices)
        print_success(f"Detected trend (up): {trend}")
        
        # Downtrend
        down_prices = [120, 118, 116, 117, 114, 112, 113, 110, 108, 109, 106, 104, 105, 102, 100]
        
        trend = self.analyzer.detect_trend(down_prices)
        print_success(f"Detected trend (down): {trend}")
        
        # Sideways
        flat_prices = [100, 101, 99, 100, 102, 101, 99, 100, 101, 100, 99, 101, 100, 99, 100]
        
        trend = self.analyzer.detect_trend(flat_prices)
        print_success(f"Detected trend (sideways): {trend}")
    
    def test_market_data(self):
        """Test fetching market data."""
        print_header("TEST: Market Data Fetching")
        
        data = self.analyzer.fetch_market_data(self.test_symbol)
        
        if data is None:
            print_error("Failed to fetch market data")
            self.fail("Could not fetch market data")
        
        print_success(f"Price: ${data.price:,.2f}")
        print_success(f"24h Change: {data.price_change_24h:+.2f}%")
        print_success(f"24h Volume: {data.volume_24h:,.0f}")


class TestOpportunityScreener(unittest.TestCase):
    """Tests for OpportunityScreener."""
    
    @classmethod
    def setUpClass(cls):
        cls.screener = OpportunityScreener()
        cls.test_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    def test_rsi_scan(self):
        """Test RSI scanning."""
        print_header("TEST: RSI Level Scanning")
        
        results = self.screener.scan_rsi_levels(self.test_symbols)
        
        print_info(f"Oversold opportunities: {len(results['oversold'])}")
        print_info(f"Overbought opportunities: {len(results['overbought'])}")
        
        for opp in results['oversold'][:3]:
            print_success(f"  {opp.symbol}: RSI {opp.rsi:.1f}")
        
        for opp in results['overbought'][:3]:
            print_success(f"  {opp.symbol}: RSI {opp.rsi:.1f}")
    
    def test_volume_scan(self):
        """Test volume anomaly scanning."""
        print_header("TEST: Volume Anomaly Scanning")
        
        results = self.screener.scan_volume_anomalies(self.test_symbols)
        
        print_info(f"Breakout opportunities: {len(results['breakout'])}")
        print_info(f"Anomaly opportunities: {len(results['anomaly'])}")
        
        for opp in results['breakout'][:3]:
            print_success(f"  {opp.symbol}: {opp.volume_ratio:.1f}x avg volume")
    
    def test_momentum_scan(self):
        """Test momentum scanning."""
        print_header("TEST: Momentum Scanning")
        
        results = self.screener.scan_momentum(self.test_symbols)
        
        print_info(f"Upward momentum: {len(results['up'])}")
        print_info(f"Downward momentum: {len(results['down'])}")
        
        for opp in results['up'][:3]:
            print_success(f"  {opp.symbol}: {opp.price_change_24h:+.1f}%")
    
    def test_correlation(self):
        """Test correlation opportunity detection."""
        print_header("TEST: Correlation Opportunities")
        
        results = self.screener.find_correlation_opportunities("BTCUSDT", self.test_symbols)
        
        print_info(f"Lagging opportunities: {len(results['lagging'])}")
        print_info(f"Leading opportunities: {len(results['leading'])}")
    
    def test_full_scan(self):
        """Test full opportunity scan."""
        print_header("TEST: Full Opportunity Scan")
        
        opportunities = self.screener.scan_all(self.test_symbols)
        
        print_success(f"Found {len(opportunities)} total opportunities")
        
        top = self.screener.get_top_opportunities(5)
        print_info(f"Top 5 opportunities:")
        for i, opp in enumerate(top, 1):
            print(f"  {i}. {opp.symbol}: {opp.opportunity_type.value} (score: {opp.score:.1f})")
    
    def test_report_generation(self):
        """Test report generation."""
        print_header("TEST: Report Generation")
        
        # Run a scan first
        opportunities = self.screener.scan_all(self.test_symbols)
        
        report = self.screener.format_opportunity_report()
        
        if not report:
            print_error("Report is empty")
            self.fail("Report generation failed")
        
        print_success(f"Report generated ({len(report)} chars)")
        print_info("Report preview:")
        print("-" * 40)
        print(report[:500] + "..." if len(report) > 500 else report)


class TestMultiCoinMonitor(unittest.TestCase):
    """Tests for MultiCoinMonitor."""
    
    @classmethod
    def setUpClass(cls):
        cls.monitor = MultiCoinMonitor()
        # Use a smaller watchlist for faster tests
        cls.monitor.watchlist = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    def test_watchlist(self):
        """Test watchlist configuration."""
        print_header("TEST: Watchlist Configuration")
        
        print_success(f"Watchlist: {self.monitor.watchlist}")
        print_success(f"Number of coins: {len(self.monitor.watchlist)}")
    
    def test_coin_snapshots(self):
        """Test getting coin snapshots."""
        print_header("TEST: Coin Snapshots")
        
        snapshots = self.monitor.get_coin_snapshots()
        
        print_success(f"Retrieved {len(snapshots)} snapshots")
        
        for snap in snapshots:
            print(f"  {snap.symbol}: ${snap.price:,.2f} ({snap.price_change_24h:+.2f}%)")
    
    def test_scan_all(self):
        """Test scanning all coins."""
        print_header("TEST: Scan All Coins")
        
        opportunities = self.monitor.scan_all()
        
        print_success(f"Found {len(opportunities)} opportunities")
    
    def test_ranking(self):
        """Test opportunity ranking."""
        print_header("TEST: Opportunity Ranking")
        
        opportunities = self.monitor.scan_all()
        ranked = self.monitor.rank_opportunities(opportunities)
        
        print_success(f"Ranked {len(ranked)} opportunities")
        
        for i, opp in enumerate(ranked[:5], 1):
            print(f"  {i}. {opp.symbol}: score {opp.score:.1f}")
    
    def test_report(self):
        """Test full report generation."""
        print_header("TEST: Full Report Generation")
        
        report = self.monitor.generate_opportunity_report()
        
        if not report:
            print_error("Report is empty")
            self.fail("Report generation failed")
        
        print_success(f"Report generated ({len(report)} chars)")
        print_info("Report preview:")
        print("-" * 40)
        print(report[:800] + "..." if len(report) > 800 else report)
    
    def test_schedule(self):
        """Test schedule checking."""
        print_header("TEST: Schedule Check")
        
        should_run = self.monitor.should_run_now()
        next_run = self.monitor.get_next_run_time()
        
        print_info(f"Should run now: {should_run}")
        print_success(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M UTC')}")


# ── Main Runner ────────────────────────────────────────────────────────────────

def run_tests():
    """Run all tests."""
    print_header("OPPORTUNITY SCREENER TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTechnicalAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestOpportunityScreener))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiCoinMonitor))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print_success("All tests passed!")
    else:
        print_error("Some tests failed!")
    
    return result.wasSuccessful()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    """CLI for running tests."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test Suite for Opportunity Screener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_screener.py
  python test_screener.py --analyzer
  python test_screener.py --screener
  python test_screener.py --monitor
        """
    )
    
    parser.add_argument('--analyzer', action='store_true',
                       help='Run TechnicalAnalyzer tests only')
    parser.add_argument('--screener', action='store_true',
                       help='Run OpportunityScreener tests only')
    parser.add_argument('--monitor', action='store_true',
                       help='Run MultiCoinMonitor tests only')
    
    args = parser.parse_args()
    
    print_header("OPPORTUNITY SCREENER TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run specific tests
    if args.analyzer:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTechnicalAnalyzer)
    elif args.screener:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestOpportunityScreener)
    elif args.monitor:
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMultiCoinMonitor)
    else:
        # Run all
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        suite.addTests(loader.loadTestsFromTestCase(TestTechnicalAnalyzer))
        suite.addTests(loader.loadTestsFromTestCase(TestOpportunityScreener))
        suite.addTests(loader.loadTestsFromTestCase(TestMultiCoinMonitor))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print_header("TEST SUMMARY")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print_success("All tests passed!")
        return 0
    else:
        print_error("Some tests failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
