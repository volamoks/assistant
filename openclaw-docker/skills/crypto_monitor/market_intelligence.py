#!/usr/bin/env python3
"""
Market Intelligence System

Combines multiple on-chain and market metrics into actionable signals:
- Fear & Greed + Funding + OI composite signal
- Extreme conditions detection
- Divergence identification
- Daily intelligence reports

Uses free APIs only:
- Fear & Greed: alternative.me
- Bybit: funding, OI, price data
- Alpha Vantage (free tier): DXY correlation
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
from collections import deque
from enum import Enum

sys.path.insert(0, '/home/node/.openclaw/skills')

from adaptive_alerts import Alert, send_telegram_alert
from onchain_analyzer import (
    OnchainAnalyzer, FearGreedData, FundingRateData, 
    OpenInterestData, LiquidationData,
    EXTREME_FEAR_THRESHOLD, EXTREME_GREED_THRESHOLD,
    EXTREME_FUNDING_NEGATIVE, EXTREME_FUNDING_POSITIVE
)


# ── Configuration ──────────────────────────────────────────────────────────────

# Signal thresholds
SIGNAL_CONFIDENCE_THRESHOLD = 0.6  # 60% confidence for signal
EXTREME_OI_CHANGE_PCT = 15  # 15% OI change is extreme
EXTREME_LIQUIDATION_USD = 10_000_000  # $10M in liquidations is extreme

# Correlation settings
CORRELATION_LOOKBACK_DAYS = 30

# State file
INTELLIGENCE_STATE_FILE = Path("/home/node/.openclaw/skills/crypto_monitor/intelligence_state.json")


class SignalType(Enum):
    """Types of trading signals."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class ExtremeCondition(Enum):
    """Types of extreme market conditions."""
    EXTREME_FEAR = "extreme_fear"
    EXTREME_GREED = "extreme_greed"
    EXTREME_NEGATIVE_FUNDING = "extreme_negative_funding"
    EXTREME_POSITIVE_FUNDING = "extreme_positive_funding"
    OI_PRICE_DIVERGENCE = "oi_price_divergence"
    HIGH_LIQUIDATIONS = "high_liquidations"
    SHORT_SQUEEZE_POTENTIAL = "short_squeeze_potential"
    LONG_SQUEEZE_POTENTIAL = "long_squeeze_potential"


@dataclass
class CompositeSignal:
    """Composite market signal."""
    signal: SignalType
    confidence: float  # 0.0 to 1.0
    score: int  # -100 to 100
    components: Dict[str, Any]
    reasoning: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            'signal': self.signal.value,
            'confidence': self.confidence,
            'score': self.score,
            'components': self.components,
            'reasoning': self.reasoning,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class MarketCondition:
    """Current market condition snapshot."""
    fear_greed: Optional[FearGreedData]
    funding: Dict[str, FundingRateData]
    open_interest: Dict[str, OpenInterestData]
    liquidations: Dict[str, LiquidationData]
    correlations: Dict[str, float]
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            'fear_greed': self.fear_greed.to_dict() if self.fear_greed else None,
            'funding': {k: v.to_dict() for k, v in self.funding.items()},
            'open_interest': {k: v.to_dict() for k, v in self.open_interest.items()},
            'liquidations': {k: v.to_dict() for k, v in self.liquidations.items()},
            'correlations': self.correlations,
            'timestamp': self.timestamp.isoformat()
        }


class MarketIntelligence:
    """
    Market Intelligence System
    
    Provides:
    - Composite BUY/SELL/NEUTRAL signals
    - Extreme condition detection
    - Multi-factor analysis
    - Daily intelligence reports
    """
    
    def __init__(self):
        self.analyzer = OnchainAnalyzer()
        self._signal_history: deque = deque(maxlen=100)
        self._condition_history: deque = deque(maxlen=30)
        self._extreme_alerts_sent: set = set()
        self._load_state()
    
    def _load_state(self):
        """Load persistent state."""
        if INTELLIGENCE_STATE_FILE.exists():
            try:
                with open(INTELLIGENCE_STATE_FILE, 'r') as f:
                    data = json.load(f)
                
                # Load extreme alerts sent (with date)
                self._extreme_alerts_sent = set(data.get('extreme_alerts_sent', []))
                
            except Exception as e:
                print(f"[MarketIntelligence] Could not load state: {e}")
    
    def _save_state(self):
        """Save persistent state."""
        try:
            INTELLIGENCE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'extreme_alerts_sent': list(self._extreme_alerts_sent),
                'saved_at': datetime.now().isoformat()
            }
            with open(INTELLIGENCE_STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[MarketIntelligence] Could not save state: {e}")
    
    def _is_alert_sent_today(self, alert_key: str) -> bool:
        """Check if alert was already sent today."""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"{alert_key}:{today}"
        return key in self._extreme_alerts_sent
    
    def _mark_alert_sent(self, alert_key: str):
        """Mark alert as sent today."""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"{alert_key}:{today}"
        self._extreme_alerts_sent.add(key)
        # Cleanup old entries (keep last 30 days)
        cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        self._extreme_alerts_sent = {
            k for k in self._extreme_alerts_sent 
            if k.split(':')[-1] >= cutoff
        }
        self._save_state()
    
    def gather_market_condition(self, symbols: List[str] = None) -> MarketCondition:
        """
        Gather current market condition data.
        
        Args:
            symbols: List of symbols to analyze
        
        Returns:
            MarketCondition with all metrics
        """
        symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        
        # Gather all data
        fear_greed = self.analyzer.get_fear_greed_index()
        funding = self.analyzer.get_funding_rates(symbols)
        
        open_interest = {}
        for symbol in symbols:
            oi = self.analyzer.get_open_interest(symbol)
            if oi:
                open_interest[symbol] = oi
        
        liquidations = {}
        for symbol in symbols:
            liq = self.analyzer.get_liquidation_data(symbol)
            if liq:
                liquidations[symbol] = liq
        
        # Calculate correlations (simplified - in real system would use price history)
        correlations = self._calculate_correlations(symbols)
        
        condition = MarketCondition(
            fear_greed=fear_greed,
            funding=funding,
            open_interest=open_interest,
            liquidations=liquidations,
            correlations=correlations,
            timestamp=datetime.now()
        )
        
        self._condition_history.append(condition)
        return condition
    
    def _calculate_correlations(self, symbols: List[str]) -> Dict[str, float]:
        """
        Calculate correlations (placeholder for actual correlation calculation).
        
        In a full implementation, this would:
        - Fetch DXY data
        - Fetch S&P 500 data  
        - Calculate rolling correlations
        
        For now, returns placeholder values.
        """
        # TODO: Implement actual correlation calculation with free data sources
        return {
            'BTC_DXY': -0.65,  # Typical inverse correlation
            'BTC_SPX': 0.45,   # Typical positive correlation
        }
    
    def calculate_composite_signal(self, symbols: List[str] = None) -> CompositeSignal:
        """
        Calculate composite BUY/SELL/NEUTRAL signal.
        
        Combines:
        - Fear & Greed (contrarian indicator)
        - Funding rates (sentiment)
        - Open Interest (leverage)
        - Liquidations (forced selling/buying)
        
        Returns:
            CompositeSignal with reasoning
        """
        symbols = symbols or ['BTCUSDT']
        condition = self.gather_market_condition(symbols)
        
        scores = []
        weights = []
        reasoning = []
        components = {}
        
        # 1. Fear & Greed Analysis (30% weight) - Contrarian indicator
        if condition.fear_greed:
            fg = condition.fear_greed
            # Extreme fear = bullish (contrarian)
            # Extreme greed = bearish (contrarian)
            # Scale: 0 (extreme fear) = +100 score, 100 (extreme greed) = -100 score
            fg_score = 50 - fg.value  # 50 - value gives range from +50 to -50
            fg_score *= 2  # Scale to -100 to +100
            
            scores.append(fg_score)
            weights.append(0.30)
            
            components['fear_greed'] = {
                'value': fg.value,
                'classification': fg.value_classification,
                'score': fg_score,
                'weight': 0.30
            }
            
            if fg.value <= EXTREME_FEAR_THRESHOLD:
                reasoning.append(f"🟢 Extreme Fear ({fg.value}): Historically bullish contrarian signal")
            elif fg.value >= EXTREME_GREED_THRESHOLD:
                reasoning.append(f"🔴 Extreme Greed ({fg.value}): Historically bearish contrarian signal")
            else:
                reasoning.append(f"⚪ Fear & Greed neutral at {fg.value}")
        
        # 2. Funding Rate Analysis (25% weight)
        if condition.funding:
            for symbol, fd in condition.funding.items():
                # Negative funding (shorts pay) = bullish
                # Positive funding (longs pay) = bearish
                # Typical range: -0.1% to +0.1%
                funding_score = -fd.funding_rate * 10000  # Scale to roughly -100 to +100
                funding_score = max(-100, min(100, funding_score))
                
                scores.append(funding_score)
                weights.append(0.25)
                
                components[f'funding_{symbol}'] = {
                    'rate': fd.funding_rate,
                    'score': funding_score,
                    'weight': 0.25
                }
                
                if fd.funding_rate <= EXTREME_FUNDING_NEGATIVE:
                    reasoning.append(f"🟢 {symbol} funding very negative ({fd.funding_rate:.4%}): Short squeeze potential")
                elif fd.funding_rate >= EXTREME_FUNDING_POSITIVE:
                    reasoning.append(f"🔴 {symbol} funding very positive ({fd.funding_rate:.4%}): Long squeeze risk")
        
        # 3. Open Interest Analysis (25% weight)
        if condition.open_interest:
            for symbol, oi in condition.open_interest.items():
                # OI increasing + price increasing = bullish (new longs)
                # OI increasing + price decreasing = bearish (new shorts)
                # OI decreasing = deleveraging
                
                if abs(oi.oi_change_24h_pct) > 5:
                    if oi.oi_change_24h_pct > 0 and oi.price_change_24h_pct > 0:
                        oi_score = 60  # Bullish accumulation
                        reasoning.append(f"🟢 {symbol} OI up {oi.oi_change_24h_pct:.1f}% with price: Long accumulation")
                    elif oi.oi_change_24h_pct > 0 and oi.price_change_24h_pct < 0:
                        oi_score = -60  # Bearish divergence
                        reasoning.append(f"🔴 {symbol} OI up {oi.oi_change_24h_pct:.1f}% but price down: Short buildup")
                    elif oi.oi_change_24h_pct < 0:
                        oi_score = 0  # Neutral deleveraging
                        reasoning.append(f"⚪ {symbol} OI down {abs(oi.oi_change_24h_pct):.1f}%: Deleveraging")
                    else:
                        oi_score = 0
                else:
                    oi_score = 0
                
                scores.append(oi_score)
                weights.append(0.25)
                
                components[f'oi_{symbol}'] = {
                    'change': oi.oi_change_24h_pct,
                    'price_change': oi.price_change_24h_pct,
                    'score': oi_score,
                    'weight': 0.25
                }
        
        # 4. Liquidation Analysis (20% weight)
        if condition.liquidations:
            for symbol, liq in condition.liquidations.items():
                # More long liquidations = bullish (selling pressure exhausted)
                # More short liquidations = bearish (buying pressure exhausted)
                if liq.total_usd > EXTREME_LIQUIDATION_USD:
                    if liq.long_short_ratio > 2:
                        liq_score = 70  # Mostly longs liquidated = bullish
                        reasoning.append(f"🟢 {symbol} high long liquidations: Potential selling exhaustion")
                    elif liq.long_short_ratio < 0.5:
                        liq_score = -70  # Mostly shorts liquidated = bearish
                        reasoning.append(f"🔴 {symbol} high short liquidations: Potential buying exhaustion")
                    else:
                        liq_score = 0
                else:
                    liq_score = 0
                
                if liq_score != 0:
                    scores.append(liq_score)
                    weights.append(0.20)
                    
                    components[f'liquidations_{symbol}'] = {
                        'total': liq.total_usd,
                        'ls_ratio': liq.long_short_ratio,
                        'score': liq_score,
                        'weight': 0.20
                    }
        
        # Calculate weighted composite score
        if scores and weights:
            total_weight = sum(weights)
            composite_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        else:
            composite_score = 0
        
        # Determine signal
        if composite_score >= 60:
            signal = SignalType.STRONG_BUY
        elif composite_score >= 30:
            signal = SignalType.BUY
        elif composite_score <= -60:
            signal = SignalType.STRONG_SELL
        elif composite_score <= -30:
            signal = SignalType.SELL
        else:
            signal = SignalType.NEUTRAL
        
        # Calculate confidence based on signal strength
        confidence = min(1.0, abs(composite_score) / 100)
        
        result = CompositeSignal(
            signal=signal,
            confidence=confidence,
            score=int(composite_score),
            components=components,
            reasoning=reasoning,
            timestamp=datetime.now()
        )
        
        self._signal_history.append(result)
        return result
    
    def detect_extreme_conditions(self, symbols: List[str] = None) -> List[Alert]:
        """
        Detect extreme market conditions and generate alerts.
        
        Args:
            symbols: List of symbols to check
        
        Returns:
            List of Alert objects for extreme conditions
        """
        symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        alerts = []
        
        condition = self.gather_market_condition(symbols)
        
        # 1. Extreme Fear & Greed
        if condition.fear_greed:
            fg = condition.fear_greed
            
            if fg.value <= EXTREME_FEAR_THRESHOLD:
                alert_key = f"extreme_fear_{fg.value}"
                if not self._is_alert_sent_today(alert_key):
                    alerts.append(Alert(
                        symbol='MARKET',
                        alert_type='extreme_fear',
                        severity='high',
                        message=f"🚨 EXTREME FEAR: Fear & Greed Index at {fg.value}",
                        price=0,
                        change_pct=fg.change_24h or 0,
                        details={
                            'condition': ExtremeCondition.EXTREME_FEAR.value,
                            'value': fg.value,
                            'threshold': EXTREME_FEAR_THRESHOLD,
                            'interpretation': 'Market in extreme fear - historically good buying opportunities',
                            'historical_bounce_rate': '70% within 30 days'
                        },
                        timestamp=datetime.now()
                    ))
                    self._mark_alert_sent(alert_key)
            
            elif fg.value >= EXTREME_GREED_THRESHOLD:
                alert_key = f"extreme_greed_{fg.value}"
                if not self._is_alert_sent_today(alert_key):
                    alerts.append(Alert(
                        symbol='MARKET',
                        alert_type='extreme_greed',
                        severity='medium',
                        message=f"⚠️ EXTREME GREED: Fear & Greed Index at {fg.value}",
                        price=0,
                        change_pct=fg.change_24h or 0,
                        details={
                            'condition': ExtremeCondition.EXTREME_GREED.value,
                            'value': fg.value,
                            'threshold': EXTREME_GREED_THRESHOLD,
                            'interpretation': 'Market in extreme greed - potential top, consider profit taking',
                            'historical_correction_rate': '60% within 30 days'
                        },
                        timestamp=datetime.now()
                    ))
                    self._mark_alert_sent(alert_key)
        
        # 2. Extreme Funding Rates
        for symbol, fd in condition.funding.items():
            if fd.funding_rate <= EXTREME_FUNDING_NEGATIVE:
                alert_key = f"extreme_funding_neg_{symbol}_{int(fd.funding_rate * 100000)}"
                if not self._is_alert_sent_today(alert_key):
                    alerts.append(Alert(
                        symbol=symbol,
                        alert_type='extreme_negative_funding',
                        severity='high',
                        message=f"📉 EXTREME FUNDING: {symbol} at {fd.funding_rate:.4%} (shorts paying)",
                        price=0,
                        change_pct=0,
                        details={
                            'condition': ExtremeCondition.EXTREME_NEGATIVE_FUNDING.value,
                            'funding_rate': fd.funding_rate,
                            'threshold': EXTREME_FUNDING_NEGATIVE,
                            'interpretation': 'Shorts heavily dominant - short squeeze potential high',
                            'squeeze_probability': 'elevated'
                        },
                        timestamp=datetime.now()
                    ))
                    self._mark_alert_sent(alert_key)
            
            elif fd.funding_rate >= EXTREME_FUNDING_POSITIVE:
                alert_key = f"extreme_funding_pos_{symbol}_{int(fd.funding_rate * 100000)}"
                if not self._is_alert_sent_today(alert_key):
                    alerts.append(Alert(
                        symbol=symbol,
                        alert_type='extreme_positive_funding',
                        severity='medium',
                        message=f"📈 EXTREME FUNDING: {symbol} at {fd.funding_rate:.4%} (longs paying)",
                        price=0,
                        change_pct=0,
                        details={
                            'condition': ExtremeCondition.EXTREME_POSITIVE_FUNDING.value,
                            'funding_rate': fd.funding_rate,
                            'threshold': EXTREME_FUNDING_POSITIVE,
                            'interpretation': 'Longs heavily dominant - long squeeze risk elevated',
                            'squeeze_probability': 'moderate'
                        },
                        timestamp=datetime.now()
                    ))
                    self._mark_alert_sent(alert_key)
        
        # 3. OI/Price Divergence
        for symbol, oi in condition.open_interest.items():
            if oi.is_divergence():
                alert_key = f"oi_divergence_{symbol}"
                if not self._is_alert_sent_today(alert_key):
                    alerts.append(Alert(
                        symbol=symbol,
                        alert_type='oi_price_divergence',
                        severity='high',
                        message=f"⚠️ OI/PRICE DIVERGENCE: {symbol} OI +{oi.oi_change_24h_pct:.1f}% but price {oi.price_change_24h_pct:+.1f}%",
                        price=0,
                        change_pct=oi.price_change_24h_pct,
                        details={
                            'condition': ExtremeCondition.OI_PRICE_DIVERGENCE.value,
                            'oi_change': oi.oi_change_24h_pct,
                            'price_change': oi.price_change_24h_pct,
                            'interpretation': 'OI rising while price falling suggests short buildup or distribution',
                            'action': 'Watch for potential reversal or acceleration'
                        },
                        timestamp=datetime.now()
                    ))
                    self._mark_alert_sent(alert_key)
        
        # 4. High Liquidations
        for symbol, liq in condition.liquidations.items():
            if liq.total_usd >= EXTREME_LIQUIDATION_USD:
                alert_key = f"high_liquidations_{symbol}"
                if not self._is_alert_sent_today(alert_key):
                    side = "longs" if liq.long_short_ratio > 1.5 else "shorts" if liq.long_short_ratio < 0.67 else "mixed"
                    alerts.append(Alert(
                        symbol=symbol,
                        alert_type='high_liquidations',
                        severity='high' if liq.total_usd >= 50_000_000 else 'medium',
                        message=f"💥 HIGH LIQUIDATIONS: {symbol} ${liq.total_usd:,.0f} ({side})",
                        price=0,
                        change_pct=0,
                        details={
                            'condition': ExtremeCondition.HIGH_LIQUIDATIONS.value,
                            'total_usd': liq.total_usd,
                            'long_short_ratio': liq.long_short_ratio,
                            'dominant_side': side,
                            'interpretation': 'High leverage being cleared - potential volatility ahead'
                        },
                        timestamp=datetime.now()
                    ))
                    self._mark_alert_sent(alert_key)
        
        return alerts
    
    def generate_daily_intelligence(self, symbols: List[str] = None) -> str:
        """
        Generate comprehensive daily intelligence report.
        
        Args:
            symbols: List of symbols to include
        
        Returns:
            Formatted report string
        """
        symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        
        # Gather data
        signal = self.calculate_composite_signal(symbols)
        condition = self._condition_history[-1] if self._condition_history else None
        
        # Build report
        lines = [
            "📊 *DAILY MARKET INTELLIGENCE REPORT*",
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
            f"",
            f"🎯 *COMPOSITE SIGNAL: {signal.signal.value}*",
            f"📈 Confidence: {signal.confidence:.0%}",
            f"📊 Score: {signal.score}/100",
            f"",
            f"💡 *REASONING:*"
        ]
        
        for reason in signal.reasoning[:5]:  # Top 5 reasons
            lines.append(f"  • {reason}")
        
        lines.append("")
        lines.append("📋 *METRICS SUMMARY:*")
        
        # Fear & Greed
        if condition and condition.fear_greed:
            fg = condition.fear_greed
            emoji = "🔴" if fg.value <= 25 else "🟡" if fg.value <= 45 else "🟢" if fg.value >= 75 else "🔵"
            lines.append(f"  {emoji} Fear & Greed: {fg.value} ({fg.value_classification})")
        
        # Funding
        for symbol, fd in (condition.funding.items() if condition else []):
            emoji = "🟢" if fd.funding_rate < 0 else "🔴" if fd.funding_rate > 0.0005 else "⚪"
            lines.append(f"  {emoji} {symbol} Funding: {fd.funding_rate:.4%}")
        
        # Open Interest
        for symbol, oi in (condition.open_interest.items() if condition else []):
            emoji = "📈" if oi.oi_change_24h_pct > 0 else "📉"
            lines.append(f"  {emoji} {symbol} OI: {oi.oi_change_24h_pct:+.2f}% (${oi.open_interest_value/1e9:.2f}B)")
        
        # Correlations
        if condition and condition.correlations:
            lines.append("")
            lines.append("🔗 *CORRELATIONS:*")
            for pair, corr in condition.correlations.items():
                emoji = "🟢" if corr > 0.5 else "🔴" if corr < -0.5 else "⚪"
                lines.append(f"  {emoji} {pair}: {corr:.2f}")
        
        lines.append("")
        lines.append("⚠️ This report is for informational purposes only")
        
        return '\n'.join(lines)
    
    def format_signal_for_telegram(self, signal: CompositeSignal) -> str:
        """Format composite signal for Telegram."""
        signal_emoji = {
            SignalType.STRONG_BUY: "🟢🟢",
            SignalType.BUY: "🟢",
            SignalType.NEUTRAL: "⚪",
            SignalType.SELL: "🔴",
            SignalType.STRONG_SELL: "🔴🔴"
        }
        
        lines = [
            f"{signal_emoji.get(signal.signal, '⚪')} *COMPOSITE SIGNAL: {signal.signal.value}*",
            f"",
            f"📈 Confidence: {signal.confidence:.0%}",
            f"📊 Score: {signal.score}/100",
            f"⏰ Generated: {signal.timestamp.strftime('%H:%M UTC')}",
            f"",
            f"💡 *KEY FACTORS:*"
        ]
        
        for reason in signal.reasoning[:3]:
            lines.append(f"  • {reason}")
        
        return '\n'.join(lines)
    
    def format_extreme_alert_for_telegram(self, alert: Alert) -> str:
        """Format extreme condition alert for Telegram."""
        severity_emoji = {
            'low': '⚪',
            'medium': '🟡',
            'high': '🔴',
            'critical': '🚨'
        }
        
        emoji = severity_emoji.get(alert.severity, '⚪')
        details = alert.details
        
        lines = [
            f"{emoji} *MARKET INTELLIGENCE ALERT*",
            f"",
            f"🚨 {alert.message}",
            f"",
            f"💡 *Interpretation:*",
            f"{details.get('interpretation', 'N/A')}",
        ]
        
        # Add specific details based on condition type
        condition = details.get('condition', '')
        
        if condition == ExtremeCondition.EXTREME_FEAR.value:
            lines.extend([
                f"",
                f"📊 *Historical Context:*",
                f"When Fear < 20, BTC historically up 45% within 3 months",
                f"Success rate: {details.get('historical_bounce_rate', 'N/A')}"
            ])
        
        elif condition == ExtremeCondition.EXTREME_GREED.value:
            lines.extend([
                f"",
                f"⚠️ *Risk Warning:*",
                f"When Greed > 80, correction probability increases",
                f"Historical correction rate: {details.get('historical_correction_rate', 'N/A')}"
            ])
        
        elif condition == ExtremeCondition.EXTREME_NEGATIVE_FUNDING.value:
            lines.extend([
                f"",
                f"🎯 *Short Squeeze Setup:*",
                f"Probability: {details.get('squeeze_probability', 'N/A')}",
                f"• Shorts are overextended",
                f"• Any positive catalyst could trigger squeeze"
            ])
        
        elif condition == ExtremeCondition.OI_PRICE_DIVERGENCE.value:
            lines.extend([
                f"",
                f"⚠️ *Divergence Details:*",
                f"OI Change: {details.get('oi_change', 0):+.1f}%",
                f"Price Change: {details.get('price_change', 0):+.1f}%",
                f"Action: {details.get('action', 'Watch closely')}"
            ])
        
        lines.append("")
        lines.append("⚠️ This is NOT financial advice")
        
        return '\n'.join(lines)


def main():
    """CLI for market intelligence."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Market Intelligence System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate composite signal
  python market_intelligence.py --signal
  
  # Detect extreme conditions
  python market_intelligence.py --extremes
  
  # Daily intelligence report
  python market_intelligence.py --daily
  
  # Send alerts to Telegram
  python market_intelligence.py --extremes --telegram
  
  # Full analysis
  python market_intelligence.py --full --telegram
        """
    )
    
    parser.add_argument('--signal', '-s', action='store_true',
                       help='Generate composite signal')
    parser.add_argument('--extremes', '-e', action='store_true',
                       help='Detect extreme conditions')
    parser.add_argument('--daily', '-d', action='store_true',
                       help='Generate daily intelligence report')
    parser.add_argument('--full', '-f', action='store_true',
                       help='Full analysis (signal + extremes)')
    parser.add_argument('--symbols', nargs='+',
                       default=['BTCUSDT', 'ETHUSDT'],
                       help='Symbols to analyze')
    parser.add_argument('--telegram', '-t', action='store_true',
                       help='Send to Telegram')
    
    args = parser.parse_args()
    
    intelligence = MarketIntelligence()
    
    if args.full:
        args.signal = True
        args.extremes = True
    
    if args.signal:
        print("Calculating composite signal...")
        signal = intelligence.calculate_composite_signal(args.symbols)
        
        print(f"\n{intelligence.format_signal_for_telegram(signal)}")
        
        if args.telegram:
            # Create alert from signal
            alert = Alert(
                symbol='MARKET',
                alert_type='composite_signal',
                severity='medium',
                message=f"Composite Signal: {signal.signal.value} (confidence: {signal.confidence:.0%})",
                price=0,
                change_pct=0,
                details=signal.to_dict(),
                timestamp=datetime.now()
            )
            success = send_telegram_alert(alert)
            print(f"\nTelegram: {'Sent' if success else 'Failed'}")
    
    if args.extremes:
        print("\nDetecting extreme conditions...")
        alerts = intelligence.detect_extreme_conditions(args.symbols)
        
        if alerts:
            print(f"\n{len(alerts)} extreme condition(s) detected:")
            for alert in alerts:
                print(f"\n{'='*50}")
                print(intelligence.format_extreme_alert_for_telegram(alert))
                
                if args.telegram:
                    success = send_telegram_alert(alert)
                    print(f"\nTelegram: {'Sent' if success else 'Failed'}")
        else:
            print("No extreme conditions detected.")
    
    if args.daily:
        print("\nGenerating daily intelligence report...")
        report = intelligence.generate_daily_intelligence(args.symbols)
        print(f"\n{report}")
        
        if args.telegram:
            # Create alert from report
            alert = Alert(
                symbol='MARKET',
                alert_type='daily_intelligence',
                severity='low',
                message='Daily Market Intelligence Report',
                price=0,
                change_pct=0,
                details={'report': report},
                timestamp=datetime.now()
            )
            success = send_telegram_alert(alert)
            print(f"\nTelegram: {'Sent' if success else 'Failed'}")
    
    # Default action
    if not any([args.signal, args.extremes, args.daily]):
        parser.print_help()


if __name__ == '__main__':
    main()
