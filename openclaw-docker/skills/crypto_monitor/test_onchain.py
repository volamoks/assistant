#!/usr/bin/env python3
"""
Test Suite for On-Chain Analytics

Tests all on-chain data sources:
- Fear & Greed API (alternative.me)
- Bybit Funding Rates
- Bybit Open Interest
- Bybit Liquidations
- Market Intelligence composite signals

Usage:
    python3 test_onchain.py              # Run all tests
    python3 test_onchain.py --fear-greed # Test Fear & Greed only
    python3 test_onchain.py --funding    # Test Funding only
    python3 test_onchain.py --oi         # Test OI only
    python3 test_onchain.py --composite  # Test composite signal
"""

import sys
import os
import unittest
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.insert(0, '/home/node/.openclaw/skills')

from onchain_analyzer import (
    OnchainAnalyzer, FearGreedData, FundingRateData, 
    OpenInterestData, LiquidationData,
    EXTREME_FEAR_THRESHOLD, EXTREME_GREED_THRESHOLD,
    EXTREME_FUNDING_NEGATIVE, EXTREME_FUNDING_POSITIVE
)
from market_intelligence import MarketIntelligence, SignalType


class TestFearGreedAPI(unittest.TestCase):
    """Tests for Fear & Greed API."""
    
    def setUp(self):
        self.analyzer = OnchainAnalyzer()
    
    def test_fear_greed_fetch(self):
        """Test Fear & Greed index fetch."""
        print("\n🧪 Testing Fear & Greed API...")
        
        fg = self.analyzer.get_fear_greed_index()
        
        self.assertIsNotNone(fg, "Failed to fetch Fear & Greed index")
        self.assertIsInstance(fg, FearGreedData)
        self.assertIsInstance(fg.value, int)
        self.assertGreaterEqual(fg.value, 0)
        self.assertLessEqual(fg.value, 100)
        self.assertIsNotNone(fg.value_classification)
        self.assertIsNotNone(fg.timestamp)
        
        print(f"  ✅ Fear & Greed: {fg.value} ({fg.value_classification})")
        print(f"  ⏰ Timestamp: {fg.timestamp}")
        
        if fg.change_24h is not None:
            print(f"  📈 24h Change: {fg.change_24h:+d}")
    
    def test_fear_greed_trend(self):
        """Test Fear & Greed trend calculation."""
        print("\n🧪 Testing Fear & Greed Trend...")
        
        trend = self.analyzer.get_fear_greed_trend(days=7)
        
        self.assertIsInstance(trend, dict)
        self.assertIn('trend', trend)
        self.assertIn('avg', trend)
        self.assertIn('change', trend)
        
        print(f"  📊 Trend: {trend['trend']}")
        if trend['avg'] is not None:
            print(f"  📈 7-day Avg: {trend['avg']:.1f}")
        if trend['change'] is not None:
            print(f"  📉 Change: {trend['change']:+d}")
        print("  ✅ Trend analysis working")


class TestFundingRatesAPI(unittest.TestCase):
    """Tests for Bybit Funding Rates API."""
    
    def setUp(self):
        self.analyzer = OnchainAnalyzer()
    
    def test_funding_fetch_btc(self):
        """Test funding rate fetch for BTC."""
        print("\n🧪 Testing BTC Funding Rate...")
        
        funding = self.analyzer.get_funding_rates(['BTCUSDT'])
        
        self.assertIn('BTCUSDT', funding)
        fd = funding['BTCUSDT']
        
        self.assertIsInstance(fd, FundingRateData)
        self.assertEqual(fd.symbol, 'BTCUSDT')
        self.assertIsInstance(fd.funding_rate, float)
        # Funding rate typically between -1% and +1%
        self.assertGreater(fd.funding_rate, -0.01)
        self.assertLess(fd.funding_rate, 0.01)
        
        print(f"  💰 BTC Funding: {fd.funding_rate:.4%}")
        if fd.predicted_rate is not None:
            print(f"  🔮 Predicted: {fd.predicted_rate:.4%}")
        print(f"  ⚠️  Is Extreme: {fd.is_extreme()}")
        print("  ✅ BTC Funding fetch successful")
    
    def test_funding_fetch_eth(self):
        """Test funding rate fetch for ETH."""
        print("\n🧪 Testing ETH Funding Rate...")
        
        funding = self.analyzer.get_funding_rates(['ETHUSDT'])
        
        self.assertIn('ETHUSDT', funding)
        fd = funding['ETHUSDT']
        
        self.assertIsInstance(fd, FundingRateData)
        self.assertEqual(fd.symbol, 'ETHUSDT')
        
        print(f"  💰 ETH Funding: {fd.funding_rate:.4%}")
        print("  ✅ ETH Funding fetch successful")
    
    def test_funding_multiple(self):
        """Test fetching multiple symbols at once."""
        print("\n🧪 Testing Multiple Funding Rates...")
        
        symbols = ['BTCUSDT', 'ETHUSDT']
        funding = self.analyzer.get_funding_rates(symbols)
        
        self.assertEqual(len(funding), len(symbols))
        
        for symbol in symbols:
            self.assertIn(symbol, funding)
        
        print(f"  ✅ Fetched funding for {len(funding)} symbols")


class TestOpenInterestAPI(unittest.TestCase):
    """Tests for Bybit Open Interest API."""
    
    def setUp(self):
        self.analyzer = OnchainAnalyzer()
    
    def test_oi_fetch_btc(self):
        """Test OI fetch for BTC."""
        print("\n🧪 Testing BTC Open Interest...")
        
        oi = self.analyzer.get_open_interest('BTCUSDT')
        
        self.assertIsNotNone(oi, "Failed to fetch OI")
        self.assertIsInstance(oi, OpenInterestData)
        self.assertEqual(oi.symbol, 'BTCUSDT')
        self.assertIsInstance(oi.open_interest, float)
        self.assertGreater(oi.open_interest, 0)
        self.assertIsInstance(oi.oi_change_24h_pct, float)
        
        print(f"  💎 BTC OI: {oi.open_interest:,.2f}")
        print(f"  💰 OI Value: ${oi.open_interest_value:,.0f}")
        print(f"  📈 24h Change: {oi.oi_change_24h_pct:+.2f}%")
        print(f"  📉 Price Change: {oi.price_change_24h_pct:+.2f}%")
        print(f"  ⚠️  Is Divergence: {oi.is_divergence()}")
        print("  ✅ BTC OI fetch successful")
    
    def test_oi_fetch_eth(self):
        """Test OI fetch for ETH."""
        print("\n🧪 Testing ETH Open Interest...")
        
        oi = self.analyzer.get_open_interest('ETHUSDT')
        
        self.assertIsNotNone(oi)
        self.assertIsInstance(oi, OpenInterestData)
        
        print(f"  💎 ETH OI: {oi.open_interest:,.2f}")
        print(f"  📈 24h Change: {oi.oi_change_24h_pct:+.2f}%")
        print("  ✅ ETH OI fetch successful")


class TestLiquidationsAPI(unittest.TestCase):
    """Tests for liquidation data estimation."""
    
    def setUp(self):
        self.analyzer = OnchainAnalyzer()
    
    def test_liquidations_fetch(self):
        """Test liquidation data fetch."""
        print("\n🧪 Testing Liquidation Data...")
        
        liq = self.analyzer.get_liquidation_data('BTCUSDT')
        
        self.assertIsNotNone(liq, "Failed to fetch liquidation data")
        self.assertIsInstance(liq, LiquidationData)
        self.assertEqual(liq.symbol, 'BTCUSDT')
        self.assertIsInstance(liq.total_usd, float)
        self.assertGreaterEqual(liq.total_usd, 0)
        
        print(f"  💥 Total Liquidations: ${liq.total_usd:,.0f}")
        print(f"  📉 Long Liqs: ${liq.long_liquidations_usd:,.0f}")
        print(f"  📈 Short Liqs: ${liq.short_liquidations_usd:,.0f}")
        if liq.short_liquidations_usd > 0:
            print(f"  ⚖️  L/S Ratio: {liq.long_short_ratio:.2f}")
        print("  ✅ Liquidation data fetch successful")


class TestMarketSentiment(unittest.TestCase):
    """Tests for market sentiment analysis."""
    
    def setUp(self):
        self.analyzer = OnchainAnalyzer()
    
    def test_sentiment_analysis(self):
        """Test market sentiment calculation."""
        print("\n🧪 Testing Market Sentiment Analysis...")
        
        sentiment = self.analyzer.analyze_market_sentiment()
        
        self.assertIsInstance(sentiment, dict)
        self.assertIn('overall', sentiment)
        self.assertIn('score', sentiment)
        self.assertIn('components', sentiment)
        
        valid_sentiments = ['bullish', 'bearish', 'neutral', 'slightly_bullish', 'slightly_bearish']
        self.assertIn(sentiment['overall'], valid_sentiments)
        self.assertIsInstance(sentiment['score'], int)
        self.assertGreaterEqual(sentiment['score'], 0)
        self.assertLessEqual(sentiment['score'], 100)
        
        print(f"  🎯 Overall: {sentiment['overall'].upper()}")
        print(f"  📊 Score: {sentiment['score']}/100")
        print(f"  📋 Components: {list(sentiment['components'].keys())}")
        print("  ✅ Sentiment analysis working")


class TestMarketIntelligence(unittest.TestCase):
    """Tests for Market Intelligence system."""
    
    def setUp(self):
        self.intel = MarketIntelligence()
    
    def test_composite_signal(self):
        """Test composite signal generation."""
        print("\n🧪 Testing Composite Signal...")
        
        signal = self.intel.calculate_composite_signal(['BTCUSDT'])
        
        self.assertIsNotNone(signal)
        self.assertIn(signal.signal, SignalType)
        self.assertIsInstance(signal.confidence, float)
        self.assertGreaterEqual(signal.confidence, 0)
        self.assertLessEqual(signal.confidence, 1)
        self.assertIsInstance(signal.score, int)
        self.assertGreaterEqual(signal.score, -100)
        self.assertLessEqual(signal.score, 100)
        
        print(f"  🚦 Signal: {signal.signal.value}")
        print(f"  📈 Confidence: {signal.confidence:.0%}")
        print(f"  📊 Score: {signal.score}/100")
        print(f"  💡 Reasoning: {len(signal.reasoning)} factors")
        print("  ✅ Composite signal generated")
    
    def test_extreme_conditions(self):
        """Test extreme condition detection."""
        print("\n🧪 Testing Extreme Condition Detection...")
        
        alerts = self.intel.detect_extreme_conditions(['BTCUSDT'])
        
        self.assertIsInstance(alerts, list)
        
        print(f"  ⚠️  Extreme conditions detected: {len(alerts)}")
        for alert in alerts:
            print(f"    - {alert.alert_type}: {alert.severity}")
        print("  ✅ Extreme condition detection working")
    
    def test_daily_report(self):
        """Test daily intelligence report generation."""
        print("\n🧪 Testing Daily Intelligence Report...")
        
        report = self.intel.generate_daily_intelligence(['BTCUSDT'])
        
        self.assertIsInstance(report, str)
        self.assertIn('DAILY MARKET INTELLIGENCE', report)
        self.assertIn('COMPOSITE SIGNAL', report)
        
        print("  ✅ Daily report generated")
        print(f"  📄 Length: {len(report)} chars")


class TestMacroAlerts(unittest.TestCase):
    """Tests for macroeconomic alerts."""
    
    def setUp(self):
        self.analyzer = OnchainAnalyzer()
    
    def test_macro_alert_check(self):
        """Test macroeconomic alert detection."""
        print("\n🧪 Testing Macroeconomic Alerts...")
        
        alert = self.analyzer.should_alert_macroeconomic()
        
        # May return None if no extreme conditions
        if alert:
            print(f"  🚨 Alert: {alert.alert_type}")
            print(f"  📊 Severity: {alert.severity}")
            print(f"  💬 Message: {alert.message[:50]}...")
        else:
            print("  ✅ No extreme macro conditions (expected in normal markets)")
        
        print("  ✅ Macro alert check working")


class TestFormatting(unittest.TestCase):
    """Tests for message formatting."""
    
    def setUp(self):
        self.analyzer = OnchainAnalyzer()
        self.intel = MarketIntelligence()
    
    def test_fear_greed_format(self):
        """Test Fear & Greed message formatting."""
        print("\n🧪 Testing Fear & Greed Formatting...")
        
        fg = self.analyzer.get_fear_greed_index()
        if fg:
            message = self.analyzer.format_fear_greed_message(fg)
            self.assertIsInstance(message, str)
            self.assertIn('Fear & Greed', message)
            print("  ✅ Fear & Greed formatting works")
            print(f"  📄 Sample: {message[:100]}...")
    
    def test_funding_format(self):
        """Test funding rate message formatting."""
        print("\n🧪 Testing Funding Rate Formatting...")
        
        funding = self.analyzer.get_funding_rates(['BTCUSDT'])
        if 'BTCUSDT' in funding:
            message = self.analyzer.format_funding_message(funding['BTCUSDT'])
            self.assertIsInstance(message, str)
            self.assertIn('FUNDING', message)
            print("  ✅ Funding formatting works")
            print(f"  📄 Sample: {message[:100]}...")
    
    def test_signal_format(self):
        """Test composite signal formatting."""
        print("\n🧪 Testing Signal Formatting...")
        
        signal = self.intel.calculate_composite_signal(['BTCUSDT'])
        message = self.intel.format_signal_for_telegram(signal)
        
        self.assertIsInstance(message, str)
        self.assertIn('COMPOSITE SIGNAL', message)
        print("  ✅ Signal formatting works")
        print(f"  📄 Sample: {message[:100]}...")


def run_specific_tests(test_type: str):
    """Run specific test category."""
    if test_type == 'fear-greed':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestFearGreedAPI)
    elif test_type == 'funding':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestFundingRatesAPI)
    elif test_type == 'oi':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestOpenInterestAPI)
    elif test_type == 'liquidations':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestLiquidationsAPI)
    elif test_type == 'sentiment':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMarketSentiment)
    elif test_type == 'composite':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMarketIntelligence)
    elif test_type == 'formatting':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestFormatting)
    elif test_type == 'macro':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestMacroAlerts)
    else:
        return None
    
    return suite


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description='Test On-Chain Analytics APIs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_onchain.py              # Run all tests
  python3 test_onchain.py --fear-greed # Test Fear & Greed only
  python3 test_onchain.py --funding    # Test Funding only
  python3 test_onchain.py --oi         # Test Open Interest only
  python3 test_onchain.py --composite  # Test composite signals
  python3 test_onchain.py --list       # List all test categories
        """
    )
    
    parser.add_argument('--fear-greed', action='store_true', help='Test Fear & Greed API')
    parser.add_argument('--funding', action='store_true', help='Test Funding Rates API')
    parser.add_argument('--oi', action='store_true', help='Test Open Interest API')
    parser.add_argument('--liquidations', action='store_true', help='Test Liquidations')
    parser.add_argument('--sentiment', action='store_true', help='Test Market Sentiment')
    parser.add_argument('--composite', action='store_true', help='Test Composite Signals')
    parser.add_argument('--macro', action='store_true', help='Test Macro Alerts')
    parser.add_argument('--formatting', action='store_true', help='Test Message Formatting')
    parser.add_argument('--list', action='store_true', help='List test categories')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.list:
        print("\n📋 Available Test Categories:")
        print("  --fear-greed    Fear & Greed Index (alternative.me)")
        print("  --funding       Funding Rates (Bybit)")
        print("  --oi            Open Interest (Bybit)")
        print("  --liquidations  Liquidation Data (Bybit)")
        print("  --sentiment     Market Sentiment Analysis")
        print("  --composite     Composite Signals & Intelligence")
        print("  --macro         Macroeconomic Alerts")
        print("  --formatting    Telegram Message Formatting")
        print("\n  (Default: run all tests)")
        return
    
    print("=" * 60)
    print("🧪 ON-CHAIN ANALYTICS TEST SUITE")
    print("=" * 60)
    print(f"⏰ Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Determine which tests to run
    test_categories = []
    if args.fear_greed:
        test_categories.append('fear-greed')
    if args.funding:
        test_categories.append('funding')
    if args.oi:
        test_categories.append('oi')
    if args.liquidations:
        test_categories.append('liquidations')
    if args.sentiment:
        test_categories.append('sentiment')
    if args.composite:
        test_categories.append('composite')
    if args.macro:
        test_categories.append('macro')
    if args.formatting:
        test_categories.append('formatting')
    
    # If no specific category, run all
    if not test_categories:
        test_categories = [
            'fear-greed', 'funding', 'oi', 'liquidations',
            'sentiment', 'composite', 'macro', 'formatting'
        ]
    
    print(f"\n🎯 Running tests: {', '.join(test_categories)}")
    print("-" * 60)
    
    # Build test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for category in test_categories:
        test_suite = run_specific_tests(category)
        if test_suite:
            suite.addTests(test_suite)
    
    # Run tests
    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"  ✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  ❌ Failed: {len(result.failures)}")
    print(f"  ⚠️  Errors: {len(result.errors)}")
    print(f"  🧪 Total: {result.testsRun}")
    print("-" * 60)
    
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
