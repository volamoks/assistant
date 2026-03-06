#!/usr/bin/env python3
"""
Opportunity Screener

Scans crypto markets to find trading opportunities:
- RSI oversold/overbought conditions
- Volume anomalies (breakouts)
- Price momentum (strong 24h moves)
- Support/Resistance proximity
- Correlation plays (relative to BTC)

Uses Bybit public API for market data.
"""

import sys
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, '/home/node/.openclaw/skills')

from technical_analysis import TechnicalAnalyzer, MarketData, RSI_OVERSOLD, RSI_OVERBOUGHT
from signal_tracker import SignalTracker


# ── Configuration ──────────────────────────────────────────────────────────────

BYBIT_API_BASE = "https://api.bybit.com/v5"

# Opportunity thresholds
RSI_OVERSOLD_THRESHOLD = 30
RSI_OVERBOUGHT_THRESHOLD = 70
RSI_STRONG_OVERSOLD = 25
RSI_STRONG_OVERBOUGHT = 75

VOLUME_ANOMALY_THRESHOLD = 2.0  # 200% of average
VOLUME_STRONG_ANOMALY = 3.0  # 300%

MOMENTUM_THRESHOLD = 10.0  # 10% price move
MOMENTUM_CONFIRMED_THRESHOLD = 1.5  # Volume 1.5x average

SUPPORT_RESISTANCE_THRESHOLD_PCT = 2.0  # Within 2% of level

# Rate limiting
REQUEST_DELAY = 0.2  # 200ms between API calls


# ── Data Classes ──────────────────────────────────────────────────────────────

class OpportunityType(Enum):
    """Types of trading opportunities."""
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    VOLUME_BREAKOUT = "volume_breakout"
    MOMENTUM_UP = "momentum_up"
    MOMENTUM_DOWN = "momentum_down"
    NEAR_SUPPORT = "near_support"
    NEAR_RESISTANCE = "near_resistance"
    CORRELATION_PLAY = "correlation_play"


class OpportunityStrength(Enum):
    """Strength rating of opportunity."""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4


@dataclass
class Opportunity:
    """Trading opportunity."""
    symbol: str
    opportunity_type: OpportunityType
    strength: OpportunityStrength
    score: float  # 0-100
    
    # Market data
    price: float
    price_change_24h: float
    
    # Technical indicators
    rsi: Optional[float] = None
    volume_ratio: Optional[float] = None
    trend: Optional[str] = None
    
    # Context
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None
    
    # Details
    reason: str = ""
    details: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'opportunity_type': self.opportunity_type.value,
            'strength': self.strength.name,
            'score': self.score,
            'price': self.price,
            'price_change_24h': self.price_change_24h,
            'rsi': self.rsi,
            'volume_ratio': self.volume_ratio,
            'trend': self.trend,
            'nearest_support': self.nearest_support,
            'nearest_resistance': self.nearest_resistance,
            'reason': self.reason,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


# ── Opportunity Screener ──────────────────────────────────────────────────────

class OpportunityScreener:
    """
    Scans markets for trading opportunities.
    """
    
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._opportunities: List[Opportunity] = []
        self.signal_tracker = SignalTracker()
    
    def _get_cache(self, key: str, ttl_minutes: int = 5) -> Optional[Any]:
        """Get cached data if not expired."""
        if key in self._cache:
            data, cached_at = self._cache[key]
            if datetime.now() - cached_at < timedelta(minutes=ttl_minutes):
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Set cache with current timestamp."""
        self._cache[key] = (data, datetime.now())
    
    # ── RSI Scanning ──────────────────────────────────────────────────────────
    
    def scan_rsi_levels(self, symbols: List[str]) -> Dict[str, List[Opportunity]]:
        """
        Scan for RSI oversold/overbought opportunities.
        
        Args:
            symbols: List of trading pairs
        
        Returns:
            Dict with 'oversold' and 'overbought' lists
        """
        results = {
            'oversold': [],
            'overbought': []
        }
        
        for symbol in symbols:
            try:
                rsi = self.analyzer.fetch_rsi(symbol)
                if rsi is None:
                    continue
                
                market_data = self.analyzer.fetch_market_data(symbol)
                if not market_data:
                    continue
                
                # Check oversold
                if rsi <= RSI_STRONG_OVERSOLD:
                    strength = OpportunityStrength.VERY_STRONG
                    score = 100 - rsi  # Lower RSI = higher score
                    reason = f"RSI {rsi:.1f} - Strong oversold (potential reversal)"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.RSI_OVERSOLD,
                        strength=strength,
                        score=score,
                        price=market_data.price,
                        price_change_24h=market_data.price_change_24h,
                        rsi=rsi,
                        reason=reason,
                        details={'rsi_threshold': RSI_STRONG_OVERSOLD}
                    )
                    results['oversold'].append(opp)
                
                elif rsi <= RSI_OVERSOLD_THRESHOLD:
                    strength = OpportunityStrength.STRONG
                    score = 80 - rsi
                    reason = f"RSI {rsi:.1f} - Oversold"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.RSI_OVERSOLD,
                        strength=strength,
                        score=score,
                        price=market_data.price,
                        price_change_24h=market_data.price_change_24h,
                        rsi=rsi,
                        reason=reason,
                        details={'rsi_threshold': RSI_OVERSOLD_THRESHOLD}
                    )
                    results['oversold'].append(opp)
                
                # Check overbought
                elif rsi >= RSI_STRONG_OVERBOUGHT:
                    strength = OpportunityStrength.VERY_STRONG
                    score = rsi  # Higher RSI = higher score for short
                    reason = f"RSI {rsi:.1f} - Strong overbought (potential correction)"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.RSI_OVERBOUGHT,
                        strength=strength,
                        score=score,
                        price=market_data.price,
                        price_change_24h=market_data.price_change_24h,
                        rsi=rsi,
                        reason=reason,
                        details={'rsi_threshold': RSI_STRONG_OVERBOUGHT}
                    )
                    results['overbought'].append(opp)
                
                elif rsi >= RSI_OVERBOUGHT_THRESHOLD:
                    strength = OpportunityStrength.STRONG
                    score = rsi - 30
                    reason = f"RSI {rsi:.1f} - Overbought"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.RSI_OVERBOUGHT,
                        strength=strength,
                        score=score,
                        price=market_data.price,
                        price_change_24h=market_data.price_change_24h,
                        rsi=rsi,
                        reason=reason,
                        details={'rsi_threshold': RSI_OVERBOUGHT_THRESHOLD}
                    )
                    results['overbought'].append(opp)
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"[OpportunityScreener] Error scanning RSI for {symbol}: {e}")
                continue
        
        # Sort by score
        results['oversold'].sort(key=lambda x: x.score, reverse=True)
        results['overbought'].sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    # ── Volume Anomaly Scanning ─────────────────────────────────────────────
    
    def scan_volume_anomalies(self, symbols: List[str]) -> Dict[str, List[Opportunity]]:
        """
        Scan for volume anomalies (potential breakouts).
        
        Args:
            symbols: List of trading pairs
        
        Returns:
            Dict with 'breakout' and 'dump' lists
        """
        results = {
            'breakout': [],
            'anomaly': []
        }
        
        for symbol in symbols:
            try:
                market_data = self.analyzer.fetch_market_data(symbol)
                if not market_data:
                    continue
                
                # Get volume anomaly data
                klines = self.analyzer.fetch_klines(symbol, interval="D", limit=30)
                if not klines or len(klines) < 20:
                    continue
                
                volumes = [float(k['volume']) for k in klines]
                avg_volume = self.analyzer.calculate_average_volume(volumes)
                
                if avg_volume is None or avg_volume == 0:
                    continue
                
                volume_ratio = market_data.volume_24h / avg_volume
                
                # Strong volume anomaly
                if volume_ratio >= VOLUME_STRONG_ANOMALY:
                    strength = OpportunityStrength.VERY_STRONG
                    score = min(volume_ratio * 20, 100)
                    
                    price_action = "pump" if market_data.price_change_24h > 0 else "dump"
                    reason = f"Volume {volume_ratio:.1f}x avg - Strong {price_action} signal"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.VOLUME_BREAKOUT,
                        strength=strength,
                        score=score,
                        price=market_data.price,
                        price_change_24h=market_data.price_change_24h,
                        volume_ratio=volume_ratio,
                        reason=reason,
                        details={
                            'volume_ratio': volume_ratio,
                            'current_volume': market_data.volume_24h,
                            'avg_volume': avg_volume
                        }
                    )
                    results['anomaly'].append(opp)
                
                # Moderate volume anomaly
                elif volume_ratio >= VOLUME_ANOMALY_THRESHOLD:
                    strength = OpportunityStrength.STRONG
                    score = min(volume_ratio * 15, 80)
                    
                    price_action = "breakout" if market_data.price_change_24h > 0 else "selloff"
                    reason = f"Volume {volume_ratio:.1f}x avg - {price_action} potential"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.VOLUME_BREAKOUT,
                        strength=strength,
                        score=score,
                        price=market_data.price,
                        price_change_24h=market_data.price_change_24h,
                        volume_ratio=volume_ratio,
                        reason=reason,
                        details={
                            'volume_ratio': volume_ratio,
                            'current_volume': market_data.volume_24h,
                            'avg_volume': avg_volume
                        }
                    )
                    results['breakout'].append(opp)
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"[OpportunityScreener] Error scanning volume for {symbol}: {e}")
                continue
        
        # Sort by score
        results['breakout'].sort(key=lambda x: x.score, reverse=True)
        results['anomaly'].sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    # ── Momentum Scanning ───────────────────────────────────────────────────
    
    def scan_momentum(self, symbols: List[str]) -> Dict[str, List[Opportunity]]:
        """
        Scan for strong price momentum (with volume confirmation).
        
        Args:
            symbols: List of trading pairs
        
        Returns:
            Dict with 'up' and 'down' lists
        """
        results = {
            'up': [],
            'down': []
        }
        
        for symbol in symbols:
            try:
                market_data = self.analyzer.fetch_market_data(symbol)
                if not market_data:
                    continue
                
                # Check momentum threshold
                if abs(market_data.price_change_24h) < MOMENTUM_THRESHOLD:
                    continue
                
                # Get volume confirmation
                klines = self.analyzer.fetch_klines(symbol, interval="D", limit=30)
                if not klines or len(klines) < 20:
                    continue
                
                volumes = [float(k['volume']) for k in klines]
                avg_volume = self.analyzer.calculate_average_volume(volumes)
                
                if avg_volume is None or avg_volume == 0:
                    continue
                
                volume_ratio = market_data.volume_24h / avg_volume
                
                # Strong upward momentum with volume confirmation
                if market_data.price_change_24h >= MOMENTUM_THRESHOLD and volume_ratio >= MOMENTUM_CONFIRMED_THRESHOLD:
                    strength = OpportunityStrength.STRONG
                    score = market_data.price_change_24h + volume_ratio * 5
                    
                    reason = f"+{market_data.price_change_24h:.1f}% (24h) with volume {volume_ratio:.1f}x"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.MOMENTUM_UP,
                        strength=strength,
                        score=score,
                        price=market_data.price,
                        price_change_24h=market_data.price_change_24h,
                        volume_ratio=volume_ratio,
                        reason=reason,
                        details={
                            'momentum_pct': market_data.price_change_24h,
                            'volume_ratio': volume_ratio
                        }
                    )
                    results['up'].append(opp)
                
                # Strong downward momentum with volume confirmation
                elif market_data.price_change_24h <= -MOMENTUM_THRESHOLD and volume_ratio >= MOMENTUM_CONFIRMED_THRESHOLD:
                    strength = OpportunityStrength.STRONG
                    score = abs(market_data.price_change_24h) + volume_ratio * 5
                    
                    reason = f"{market_data.price_change_24h:.1f}% (24h) with volume {volume_ratio:.1f}x"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.MOMENTUM_DOWN,
                        strength=strength,
                        score=score,
                        price=market_data.price,
                        price_change_24h=market_data.price_change_24h,
                        volume_ratio=volume_ratio,
                        reason=reason,
                        details={
                            'momentum_pct': market_data.price_change_24h,
                            'volume_ratio': volume_ratio
                        }
                    )
                    results['down'].append(opp)
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"[OpportunityScreener] Error scanning momentum for {symbol}: {e}")
                continue
        
        # Sort by score
        results['up'].sort(key=lambda x: x.score, reverse=True)
        results['down'].sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    # ── Correlation Plays ───────────────────────────────────────────────────
    
    def find_correlation_opportunities(self, base_symbol: str, alt_symbols: List[str]) -> Dict:
        """
        Find correlation opportunities.
        
        If base_symbol is rising, find alts that are lagging.
        
        Args:
            base_symbol: Base currency (e.g., 'BTCUSDT')
            alt_symbols: Alternative coins to check
        
        Returns:
            Dict with 'lagging' and 'leading' lists
        """
        results = {
            'lagging': [],  # Alts that should catch up
            'leading': []   # Alts that are outperforming
        }
        
        # Get base symbol data
        try:
            base_data = self.analyzer.fetch_market_data(base_symbol)
            if not base_data:
                return results
            base_change = base_data.price_change_24h
        except Exception as e:
            print(f"[OpportunityScreener] Error fetching base symbol {base_symbol}: {e}")
            return results
        
        for symbol in alt_symbols:
            try:
                if symbol == base_symbol:
                    continue
                
                market_data = self.analyzer.fetch_market_data(symbol)
                if not market_data:
                    continue
                
                alt_change = market_data.price_change_24h
                
                # Calculate relative performance
                relative_change = alt_change - base_change
                
                # Lagging alts (should catch up if base is rising)
                if base_change > 0 and relative_change < -5:  # Alt is 5%+ behind
                    score = abs(relative_change)
                    reason = f"Lagging BTC by {abs(relative_change):.1f}% - potential catch-up play"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.CORRELATION_PLAY,
                        strength=OpportunityStrength.MODERATE,
                        score=score,
                        price=market_data.price,
                        price_change_24h=alt_change,
                        reason=reason,
                        details={
                            'base_symbol': base_symbol,
                            'base_change': base_change,
                            'relative_change': relative_change
                        }
                    )
                    results['lagging'].append(opp)
                
                # Leading alts (outperforming)
                elif relative_change > 10:  # Alt is 10%+ ahead
                    score = relative_change
                    reason = f"Outperforming BTC by {relative_change:.1f}%"
                    
                    opp = Opportunity(
                        symbol=symbol,
                        opportunity_type=OpportunityType.CORRELATION_PLAY,
                        strength=OpportunityStrength.MODERATE,
                        score=score,
                        price=market_data.price,
                        price_change_24h=alt_change,
                        reason=reason,
                        details={
                            'base_symbol': base_symbol,
                            'base_change': base_change,
                            'relative_change': relative_change
                        }
                    )
                    results['leading'].append(opp)
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"[OpportunityScreener] Error checking correlation for {symbol}: {e}")
                continue
        
        # Sort
        results['lagging'].sort(key=lambda x: x.score, reverse=True)
        results['leading'].sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    # ── Support/Resistance Proximity ───────────────────────────────────────
    
    def scan_support_resistance(self, symbols: List[str]) -> Dict[str, List[Opportunity]]:
        """
        Scan for opportunities near support/resistance levels.
        
        Args:
            symbols: List of trading pairs
        
        Returns:
            Dict with 'near_support' and 'near_resistance' lists
        """
        results = {
            'near_support': [],
            'near_resistance': []
        }
        
        for symbol in symbols:
            try:
                market_data = self.analyzer.fetch_market_data(symbol)
                if not market_data:
                    continue
                
                # Get S/R levels
                klines = self.analyzer.fetch_klines(symbol, interval="D", limit=200)
                if not klines or len(klines) < 50:
                    continue
                
                close_prices = [float(k['close']) for k in klines]
                sr_levels = self.analyzer.find_support_resistance(close_prices)
                nearest = self.analyzer.find_nearest_levels(market_data.price, sr_levels)
                
                # Check proximity to support
                supports = nearest.get('support', [])
                if supports:
                    nearest_support = supports[0]
                    distance_pct = abs(market_data.price - nearest_support) / market_data.price * 100
                    
                    if distance_pct <= SUPPORT_RESISTANCE_THRESHOLD_PCT:
                        strength = OpportunityStrength.MODERATE if distance_pct > 1 else OpportunityStrength.STRONG
                        score = 50 + (SUPPORT_RESISTANCE_THRESHOLD_PCT - distance_pct) * 10
                        
                        reason = f"Price within {distance_pct:.1f}% of support (${nearest_support:,.2f})"
                        
                        opp = Opportunity(
                            symbol=symbol,
                            opportunity_type=OpportunityType.NEAR_SUPPORT,
                            strength=strength,
                            score=score,
                            price=market_data.price,
                            price_change_24h=market_data.price_change_24h,
                            nearest_support=nearest_support,
                            reason=reason,
                            details={
                                'distance_pct': distance_pct,
                                'support_level': nearest_support
                            }
                        )
                        results['near_support'].append(opp)
                
                # Check proximity to resistance
                resistances = nearest.get('resistance', [])
                if resistances:
                    nearest_resistance = resistances[0]
                    distance_pct = abs(nearest_resistance - market_data.price) / market_data.price * 100
                    
                    if distance_pct <= SUPPORT_RESISTANCE_THRESHOLD_PCT:
                        strength = OpportunityStrength.MODERATE if distance_pct > 1 else OpportunityStrength.STRONG
                        score = 50 + (SUPPORT_RESISTANCE_THRESHOLD_PCT - distance_pct) * 10
                        
                        reason = f"Price within {distance_pct:.1f}% of resistance (${nearest_resistance:,.2f})"
                        
                        opp = Opportunity(
                            symbol=symbol,
                            opportunity_type=OpportunityType.NEAR_RESISTANCE,
                            strength=strength,
                            score=score,
                            price=market_data.price,
                            price_change_24h=market_data.price_change_24h,
                            nearest_resistance=nearest_resistance,
                            reason=reason,
                            details={
                                'distance_pct': distance_pct,
                                'resistance_level': nearest_resistance
                            }
                        )
                        results['near_resistance'].append(opp)
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"[OpportunityScreener] Error scanning S/R for {symbol}: {e}")
                continue
        
        # Sort
        results['near_support'].sort(key=lambda x: x.score, reverse=True)
        results['near_resistance'].sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    # ── Full Scan ───────────────────────────────────────────────────────────
    
    def scan_all(self, symbols: List[str]) -> List[Opportunity]:
        """
        Run full scan on all symbols.
        
        Args:
            symbols: List of trading pairs
        
        Returns:
            List of all opportunities found
        """
        all_opportunities = []
        
        print(f"[OpportunityScreener] Scanning {len(symbols)} symbols...")
        
        # RSI scan
        print("  → Scanning RSI levels...")
        rsi_results = self.scan_rsi_levels(symbols)
        all_opportunities.extend(rsi_results['oversold'])
        all_opportunities.extend(rsi_results['overbought'])
        
        # Volume scan
        print("  → Scanning volume anomalies...")
        volume_results = self.scan_volume_anomalies(symbols)
        all_opportunities.extend(volume_results['breakout'])
        all_opportunities.extend(volume_results['anomaly'])
        
        # Momentum scan
        print("  → Scanning momentum...")
        momentum_results = self.scan_momentum(symbols)
        all_opportunities.extend(momentum_results['up'])
        all_opportunities.extend(momentum_results['down'])
        
        # S/R scan
        print("  → Scanning support/resistance...")
        sr_results = self.scan_support_resistance(symbols)
        all_opportunities.extend(sr_results['near_support'])
        all_opportunities.extend(sr_results['near_resistance'])
        
        # Store
        self._opportunities = all_opportunities
        
        print(f"[OpportunityScreener] Found {len(all_opportunities)} opportunities")
        
        return all_opportunities
    
    def get_top_opportunities(self, limit: int = 5) -> List[Opportunity]:
        """
        Get top opportunities by score.
        
        Args:
            limit: Maximum number to return
        
        Returns:
            List of top opportunities
        """
        if not self._opportunities:
            return []
        
        sorted_opps = sorted(self._opportunities, key=lambda x: x.score, reverse=True)
        return sorted_opps[:limit]
    
    # ── Formatting ───────────────────────────────────────────────────────────
    
    def format_opportunity_report(self, opportunities: Optional[List[Opportunity]] = None) -> str:
        """
        Format opportunities as a Telegram-ready report.
        
        Args:
            opportunities: List of opportunities (uses cached if None)
        
        Returns:
            Formatted report string
        """
        if opportunities is None:
            opportunities = self._opportunities
        
        if not opportunities:
            return "🔍 No opportunities found in current scan."
        
        lines = [
            "🔍 *DAILY OPPORTUNITY SCREENER*",
            ""
        ]
        
        # Group by type
        rsi_oversold = [o for o in opportunities if o.opportunity_type == OpportunityType.RSI_OVERSOLD]
        rsi_overbought = [o for o in opportunities if o.opportunity_type == OpportunityType.RSI_OVERBOUGHT]
        volume_breakout = [o for o in opportunities if o.opportunity_type == OpportunityType.VOLUME_BREAKOUT]
        momentum_up = [o for o in opportunities if o.opportunity_type == OpportunityType.MOMENTUM_UP]
        momentum_down = [o for o in opportunities if o.opportunity_type == OpportunityType.MOMENTUM_DOWN]
        
        # RSI Oversold
        if rsi_oversold:
            lines.append("📊 *RSI Oversold (Potential Buy):*")
            for i, opp in enumerate(rsi_oversold[:3], 1):
                strength_emoji = "🔶" if opp.strength == OpportunityStrength.VERY_STRONG else "🟢"
                lines.append(f"{i}. {strength_emoji} {opp.symbol} - RSI: {opp.rsi:.1f}")
            lines.append("")
        
        # RSI Overbought
        if rsi_overbought:
            lines.append("📊 *RSI Overbought (Potential Short):*")
            for i, opp in enumerate(rsi_overbought[:3], 1):
                strength_emoji = "🔴" if opp.strength == OpportunityStrength.VERY_STRONG else "🟠"
                lines.append(f"{i}. {strength_emoji} {opp.symbol} - RSI: {opp.rsi:.1f}")
            lines.append("")
        
        # Volume Breakouts
        if volume_breakout:
            lines.append("📈 *Volume Breakouts:*")
            for i, opp in enumerate(volume_breakout[:3], 1):
                lines.append(f"{i}. 🟢 {opp.symbol} - Volume +{(opp.volume_ratio - 1) * 100:.0f}% above avg")
            lines.append("")
        
        # Momentum
        if momentum_up:
            lines.append("📈 *Strong Momentum (24h):*")
            for i, opp in enumerate(momentum_up[:3], 1):
                lines.append(f"{i}. ⚡ {opp.symbol} +{opp.price_change_24h:.1f}% (confirmed by volume)")
            lines.append("")
        
        if momentum_down:
            lines.append("📉 *Strong Downside (24h):*")
            for i, opp in enumerate(momentum_down[:3], 1):
                lines.append(f"{i}. 🔻 {opp.symbol} {opp.price_change_24h:.1f}% (confirmed by volume)")
            lines.append("")
        
        # Top Opportunity
        top = self.get_top_opportunities(1)
        if top:
            lines.append("🎯 *Top Opportunity:*")
            t = top[0]
            lines.append(f"#{t.symbol} - Score: {t.score:.0f}")
            lines.append(f"💡 {t.reason}")
        
        return '\n'.join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    """CLI for opportunity screener."""
    import argparse
    
    # Default watchlist
    DEFAULT_WATCHLIST = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
        "MATICUSDT", "ATOMUSDT", "UNIUSDT", "LTCUSDT", "ETCUSDT"
    ]
    
    parser = argparse.ArgumentParser(
        description="Crypto Opportunity Screener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python opportunity_screener.py --screener
  python opportunity_screener.py --rsi
  python opportunity_screener.py --volume
  python opportunity_screener.py --momentum
  python opportunity_screener.py --correlation BTCUSDT
  python opportunity_screener.py --symbols BTCUSDT ETHUSDT
        """
    )
    
    parser.add_argument('--screener', action='store_true',
                       help='Run full opportunity screener')
    parser.add_argument('--rsi', action='store_true',
                       help='Scan RSI levels only')
    parser.add_argument('--volume', action='store_true',
                       help='Scan volume anomalies only')
    parser.add_argument('--momentum', action='store_true',
                       help='Scan momentum only')
    parser.add_argument('--correlation', type=str, metavar='BASE',
                       help='Find correlation opportunities vs base (e.g., BTCUSDT)')
    parser.add_argument('--symbols', '-s', nargs='+',
                       default=DEFAULT_WATCHLIST,
                       help=f'Symbols to scan (default: all major coins)')
    parser.add_argument('--limit', '-l', type=int, default=10,
                       help='Limit results (default: 10)')
    parser.add_argument('--report', action='store_true',
                       help='Generate Telegram report')
    
    args = parser.parse_args()
    
    screener = OpportunityScreener()
    
    if args.screener or not any([args.rsi, args.volume, args.momentum, args.correlation]):
        # Full scan
        print(f"\n🔍 Running full opportunity scan on {len(args.symbols)} symbols...")
        opportunities = screener.scan_all(args.symbols)
        
        if args.report:
            print("\n" + screener.format_opportunity_report())
        else:
            top = screener.get_top_opportunities(args.limit)
            print(f"\n🎯 Top {len(top)} Opportunities:")
            print("=" * 60)
            for i, opp in enumerate(top, 1):
                print(f"\n{i}. {opp.symbol} ({opp.opportunity_type.value})")
                print(f"   Score: {opp.score:.1f} | Price: ${opp.price:,.2f}")
                print(f"   {opp.reason}")
    
    elif args.rsi:
        print(f"\n📊 Scanning RSI levels for {len(args.symbols)} symbols...")
        results = screener.scan_rsi_levels(args.symbols)
        
        print("\n🔶 RSI Oversold (Potential Buy):")
        for opp in results['oversold'][:args.limit]:
            print(f"  {opp.symbol}: RSI {opp.rsi:.1f} - {opp.reason}")
        
        print("\n🔴 RSI Overbought (Potential Short):")
        for opp in results['overbought'][:args.limit]:
            print(f"  {opp.symbol}: RSI {opp.rsi:.1f} - {opp.reason}")
    
    elif args.volume:
        print(f"\n📈 Scanning volume anomalies for {len(args.symbols)} symbols...")
        results = screener.scan_volume_anomalies(args.symbols)
        
        print("\n🟢 Volume Breakouts:")
        for opp in results['breakout'][:args.limit]:
            print(f"  {opp.symbol}: {opp.volume_ratio:.1f}x avg - {opp.reason}")
        
        print("\n🔴 Strong Volume Anomalies:")
        for opp in results['anomaly'][:args.limit]:
            print(f"  {opp.symbol}: {opp.volume_ratio:.1f}x avg - {opp.reason}")
    
    elif args.momentum:
        print(f"\n⚡ Scanning momentum for {len(args.symbols)} symbols...")
        results = screener.scan_momentum(args.symbols)
        
        print("\n📈 Strong Uptrend:")
        for opp in results['up'][:args.limit]:
            print(f"  {opp.symbol}: {opp.price_change_24h:+.1f}% - {opp.reason}")
        
        print("\n📉 Strong Downtrend:")
        for opp in results['down'][:args.limit]:
            print(f"  {opp.symbol}: {opp.price_change_24h:+.1f}% - {opp.reason}")
    
    elif args.correlation:
        print(f"\n🔗 Finding correlation opportunities vs {args.correlation}...")
        # Remove base from alts
        alts = [s for s in args.symbols if s != args.correlation]
        results = screener.find_correlation_opportunities(args.correlation, alts)
        
        print("\n📉 Lagging (potential catch-up):")
        for opp in results['lagging'][:args.limit]:
            print(f"  {opp.symbol}: {opp.reason}")
        
        print("\n📈 Leading (outperforming):")
        for opp in results['leading'][:args.limit]:
            print(f"  {opp.symbol}: {opp.reason}")


if __name__ == '__main__':
    main()
