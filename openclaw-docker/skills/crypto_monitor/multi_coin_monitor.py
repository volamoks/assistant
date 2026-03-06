#!/usr/bin/env python3
"""
Multi-Coin Monitor

Monitors multiple coins and generates ranked opportunity reports.
Designed for scheduled scanning (every 4 hours).

Default schedule: 06:00, 10:00, 14:00, 18:00, 22:00 (UTC)

Uses Bybit public API for market data.
"""

import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, '/home/node/.openclaw/skills')

from opportunity_screener import (
    OpportunityScreener, Opportunity, OpportunityType, OpportunityStrength
)
from technical_analysis import TechnicalAnalyzer


# ── Configuration ──────────────────────────────────────────────────────────────

# Default watchlist - 15 major coins
DEFAULT_WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "ATOMUSDT", "UNIUSDT", "LTCUSDT", "ETCUSDT"
]

# Schedule times (UTC)
SCHEDULE_TIMES = ["06:00", "10:00", "14:00", "18:00", "22:00"]

# State file
STATE_FILE = Path("/home/node/.openclaw/skills/crypto_monitor/multi_coin_state.json")

# Request delay for API calls
REQUEST_DELAY = 0.3  # 300ms


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class CoinSnapshot:
    """Snapshot of coin data."""
    symbol: str
    price: float
    price_change_24h: float
    volume_24h: float
    rsi: Optional[float]
    trend: str
    score: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ScanReport:
    """Full scan report."""
    timestamp: datetime
    symbols_scanned: int
    opportunities_found: int
    top_opportunities: List[Opportunity]
    snapshots: List[CoinSnapshot]
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbols_scanned': self.symbols_scanned,
            'opportunities_found': self.opportunities_found,
            'top_opportunities': [o.to_dict() for o in self.top_opportunities],
            'snapshots': [
                {
                    'symbol': s.symbol,
                    'price': s.price,
                    'price_change_24h': s.price_change_24h,
                    'rsi': s.rsi,
                    'trend': s.trend,
                    'score': s.score
                }
                for s in self.snapshots
            ]
        }


# ── Multi-Coin Monitor ──────────────────────────────────────────────────────

class MultiCoinMonitor:
    """
    Monitors multiple coins and generates ranked opportunity reports.
    """
    
    def __init__(self, watchlist: Optional[List[str]] = None):
        self.watchlist = watchlist or DEFAULT_WATCHLIST
        self.screener = OpportunityScreener()
        self.analyzer = TechnicalAnalyzer()
        self._last_report: Optional[ScanReport] = None
    
    # ── Coin Snapshots ─────────────────────────────────────────────────────
    
    def get_coin_snapshots(self) -> List[CoinSnapshot]:
        """
        Get snapshots of all coins in watchlist.
        
        Returns:
            List of coin snapshots
        """
        snapshots = []
        
        for symbol in self.watchlist:
            try:
                # Get market data
                market_data = self.analyzer.fetch_market_data(symbol)
                if not market_data:
                    continue
                
                # Get RSI
                rsi = self.analyzer.fetch_rsi(symbol)
                
                # Get trend
                klines = self.analyzer.fetch_klines(symbol, interval="D", limit=50)
                trend = "SIDEWAYS"
                if klines and len(klines) >= 20:
                    close_prices = [float(k['close']) for k in klines]
                    trend = self.analyzer.detect_trend(close_prices)
                
                # Calculate basic score
                score = 0
                if rsi:
                    if rsi < 30:
                        score = 100 - rsi  # Oversold = higher score
                    elif rsi > 70:
                        score = rsi - 30   # Overbought for shorts
                
                score += abs(market_data.price_change_24h) * 2
                
                snapshot = CoinSnapshot(
                    symbol=symbol,
                    price=market_data.price,
                    price_change_24h=market_data.price_change_24h,
                    volume_24h=market_data.volume_24h,
                    rsi=rsi,
                    trend=trend,
                    score=score
                )
                snapshots.append(snapshot)
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"[MultiCoinMonitor] Error getting snapshot for {symbol}: {e}")
                continue
        
        return snapshots
    
    # ── Full Scan ───────────────────────────────────────────────────────────
    
    def scan_all(self) -> List[Opportunity]:
        """
        Run full scan on all coins in watchlist.
        
        Returns:
            List of opportunities found
        """
        print(f"[MultiCoinMonitor] Scanning {len(self.watchlist)} coins...")
        
        opportunities = self.screener.scan_all(self.watchlist)
        
        return opportunities
    
    # ── Ranking ──────────────────────────────────────────────────────────────
    
    def rank_opportunities(self, opportunities: List[Opportunity]) -> List[Opportunity]:
        """
        Rank opportunities by strength and filter.
        
        Rankings factors:
        - RSI extreme (oversold < 25 or overbought > 75): +30 points
        - Volume confirmation: +20 points
        - Strong momentum (>15%): +15 points
        - Near support: +10 points
        
        Args:
            opportunities: List of opportunities to rank
        
        Returns:
            Ranked list of opportunities
        """
        ranked = []
        
        for opp in opportunities:
            score = opp.score
            
            # Boost for extreme RSI
            if opp.rsi:
                if opp.rsi <= 25:
                    score += 30
                elif opp.rsi >= 75:
                    score += 30
                elif opp.rsi < 30 or opp.rsi > 70:
                    score += 15
            
            # Boost for volume confirmation
            if opp.volume_ratio and opp.volume_ratio >= 2.0:
                score += 20
            
            # Boost for strong momentum
            if abs(opp.price_change_24h) >= 15:
                score += 15
            
            # Boost for being near support
            if opp.nearest_support:
                score += 10
            
            opp.score = score
            ranked.append(opp)
        
        # Sort by final score
        ranked.sort(key=lambda x: x.score, reverse=True)
        
        return ranked
    
    # ── Report Generation ───────────────────────────────────────────────────
    
    def generate_opportunity_report(self) -> str:
        """
        Generate full opportunity report for Telegram.
        
        Returns:
            Formatted report string
        """
        # Run scan
        opportunities = self.scan_all()
        
        if not opportunities:
            return self._generate_empty_report()
        
        # Rank
        ranked = self.rank_opportunities(opportunities)
        
        # Get snapshots
        snapshots = self.get_coin_snapshots()
        
        # Store report
        self._last_report = ScanReport(
            timestamp=datetime.now(),
            symbols_scanned=len(self.watchlist),
            opportunities_found=len(opportunities),
            top_opportunities=ranked[:10],
            snapshots=snapshots
        )
        
        return self._format_report(ranked, snapshots)
    
    def _generate_empty_report(self) -> str:
        """Generate empty report."""
        lines = [
            "🔍 *DAILY OPPORTUNITY SCREENER*",
            "",
            f"⏰ Scan time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "✅ No significant opportunities found.",
            "",
            "Market appears calm. Waiting for setups."
        ]
        return '\n'.join(lines)
    
    def _format_report(self, opportunities: List[Opportunity], snapshots: List[CoinSnapshot]) -> str:
        """Format the report."""
        lines = [
            "🔍 *DAILY OPPORTUNITY SCREENER*",
            "",
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            f"📊 Scanned: {len(self.watchlist)} coins | Found: {len(opportunities)} signals",
            ""
        ]
        
        # Group by type
        rsi_oversold = [o for o in opportunities if o.opportunity_type == OpportunityType.RSI_OVERSOLD]
        rsi_overbought = [o for o in opportunities if o.opportunity_type == OpportunityType.RSI_OVERBOUGHT]
        volume_signals = [o for o in opportunities if o.opportunity_type == OpportunityType.VOLUME_BREAKOUT]
        momentum_up = [o for o in opportunities if o.opportunity_type == OpportunityType.MOMENTUM_UP]
        momentum_down = [o for o in opportunities if o.opportunity_type == OpportunityType.MOMENTUM_DOWN]
        
        # RSI Oversold (Potential Buy)
        if rsi_oversold:
            lines.append("📊 *RSI Oversold (Potential Buy):*")
            for i, opp in enumerate(rsi_oversold[:5], 1):
                strength = "🔶" if opp.strength == OpportunityStrength.VERY_STRONG else "🟢"
                lines.append(f"{i}. {strength} {opp.symbol} - RSI: {opp.rsi:.0f}")
            lines.append("")
        
        # RSI Overbought
        if rsi_overbought:
            lines.append("📊 *RSI Overbought (Potential Short):*")
            for i, opp in enumerate(rsi_overbought[:5], 1):
                strength = "🔴" if opp.strength == OpportunityStrength.VERY_STRONG else "🟠"
                lines.append(f"{i}. {strength} {opp.symbol} - RSI: {opp.rsi:.0f}")
            lines.append("")
        
        # Volume Breakouts
        if volume_signals:
            lines.append("📈 *Volume Breakouts:*")
            for i, opp in enumerate(volume_signals[:3], 1):
                vol_pct = (opp.volume_ratio - 1) * 100 if opp.volume_ratio else 0
                lines.append(f"{i}. 🟢 {opp.symbol} - Volume +{vol_pct:.0f}% above avg")
            lines.append("")
        
        # Strong Momentum
        if momentum_up:
            lines.append("📈 *Strong Momentum (24h):*")
            for i, opp in enumerate(momentum_up[:3], 1):
                lines.append(f"{i}. ⚡ {opp.symbol} +{opp.price_change_24h:.1f}%")
            lines.append("")
        
        if momentum_down:
            lines.append("📉 *Strong Downside (24h):*")
            for i, opp in enumerate(momentum_down[:3], 1):
                lines.append(f"{i}. 🔻 {opp.symbol} {opp.price_change_24h:.1f}%")
            lines.append("")
        
        # Top Opportunity
        if opportunities:
            top = opportunities[0]
            lines.append("🎯 *Top Opportunity:*")
            lines.append(f"#{top.symbol} - Score: {top.score:.0f}")
            lines.append(f"💡 {top.reason}")
        
        return '\n'.join(lines)
    
    # ── Quick Summary ───────────────────────────────────────────────────────
    
    def get_market_summary(self) -> str:
        """
        Get quick market summary.
        
        Returns:
            Formatted summary
        """
        snapshots = self.get_coin_snapshots()
        
        if not snapshots:
            return "Unable to fetch market data."
        
        # Sort by 24h change
        sorted_by_change = sorted(snapshots, key=lambda x: x.price_change_24h, reverse=True)
        
        lines = [
            "📊 *MARKET SUMMARY*",
            "",
            "🔥 Top Gainers:",
        ]
        
        for snap in sorted_by_change[:3]:
            lines.append(f"  {snap.symbol}: {snap.price_change_24h:+.2f}%")
        
        lines.extend([
            "",
            "📉 Top Losers:",
        ])
        
        for snap in sorted_by_change[-3:]:
            lines.append(f"  {snap.symbol}: {snap.price_change_24h:+.2f}%")
        
        # RSI summary
        oversold = [s for s in snapshots if s.rsi and s.rsi < 30]
        overbought = [s for s in snapshots if s.rsi and s.rsi > 70]
        
        lines.extend([
            "",
            f"📉 Oversold (RSI<30): {len(oversold)} coins",
            f"📈 Overbought (RSI>70): {len(overbought)} coins",
        ])
        
        return '\n'.join(lines)
    
    # ── State Management ───────────────────────────────────────────────────
    
    def save_state(self):
        """Save current state to file."""
        if self._last_report:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                import json
                json.dump(self._last_report.to_dict(), f, indent=2)
    
    def load_state(self) -> Optional[ScanReport]:
        """Load previous report from file."""
        if STATE_FILE.exists():
            try:
                import json
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                
                # Convert back to ScanReport
                return ScanReport(
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    symbols_scanned=data['symbols_scanned'],
                    opportunities_found=data['opportunities_found'],
                    top_opportunities=[],  # Don't restore opportunities
                    snapshots=[]  # Don't restore snapshots
                )
            except Exception as e:
                print(f"[MultiCoinMonitor] Error loading state: {e}")
        return None
    
    # ── Schedule Check ───────────────────────────────────────────────────
    
    def should_run_now(self) -> bool:
        """
        Check if we should run based on schedule.
        
        Returns:
            True if current time matches schedule
        """
        current_time = datetime.now()
        current_hour_minute = current_time.strftime("%H:%M")
        
        return current_hour_minute in SCHEDULE_TIMES
    
    def get_next_run_time(self) -> datetime:
        """Get next scheduled run time."""
        now = datetime.now()
        
        for schedule_time in SCHEDULE_TIMES:
            hour, minute = map(int, schedule_time.split(':'))
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if next_run > now:
                return next_run
        
        # Next day
        next_run = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return next_run


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    """CLI for multi-coin monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Multi-Coin Monitor with Scheduled Scanning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python multi_coin_monitor.py --scan
  python multi_coin_monitor.py --report
  python multi_coin_monitor.py --summary
  python multi_coin_monitor.py --watchlist BTCUSDT ETHUSDT SOLUSDT
  python multi_coin_monitor.py --schedule  # Check if should run now
        """
    )
    
    parser.add_argument('--scan', '-s', action='store_true',
                       help='Run full opportunity scan')
    parser.add_argument('--report', '-r', action='store_true',
                       help='Generate and print full report')
    parser.add_argument('--summary', action='store_true',
                       help='Show market summary only')
    parser.add_argument('--schedule', action='store_true',
                       help='Check schedule and run if due')
    parser.add_argument('--watchlist', '-w', nargs='+',
                       help='Custom watchlist')
    parser.add_argument('--output', '-o', type=str,
                       help='Save report to file')
    
    args = parser.parse_args()
    
    watchlist = args.watchlist or DEFAULT_WATCHLIST
    monitor = MultiCoinMonitor(watchlist=watchlist)
    
    if args.schedule:
        if monitor.should_run_now():
            print("[MultiCoinMonitor] Schedule match! Running scan...")
            report = monitor.generate_opportunity_report()
            print("\n" + report)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(report)
                print(f"\nReport saved to {args.output}")
        else:
            next_run = monitor.get_next_run_time()
            print(f"[MultiCoinMonitor] Not scheduled to run now.")
            print(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M UTC')}")
        return
    
    if args.report or not any([args.scan, args.summary]):
        report = monitor.generate_opportunity_report()
        print("\n" + report)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"\nReport saved to {args.output}")
    
    elif args.scan:
        print(f"\n🔍 Running scan on {len(watchlist)} coins...")
        opportunities = monitor.scan_all()
        ranked = monitor.rank_opportunities(opportunities)
        
        print(f"\nFound {len(opportunities)} opportunities:")
        for i, opp in enumerate(ranked[:10], 1):
            print(f"\n{i}. {opp.symbol} ({opp.opportunity_type.value})")
            print(f"   Score: {opp.score:.1f} | {opp.reason}")
    
    elif args.summary:
        print("\n" + monitor.get_market_summary())


if __name__ == '__main__':
    main()
