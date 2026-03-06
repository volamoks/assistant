#!/usr/bin/env python3
"""
Technical Analysis Module

Provides technical analysis tools for crypto markets:
- RSI calculation (14-period)
- Moving Averages (SMA 20, 50, 200)
- Support/Resistance levels detection
- Trend detection
- Divergence detection

Uses Bybit public API for market data.
"""

import sys
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
from collections import deque
import statistics

sys.path.insert(0, '/home/node/.openclaw/skills')

from adaptive_alerts import Alert


# ── Configuration ──────────────────────────────────────────────────────────────

BYBIT_API_BASE = "https://api.bybit.com/v5"

# RSI thresholds
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_PERIOD = 14

# Moving average periods
SMA_PERIODS = [20, 50, 200]

# Volume anomaly threshold
VOLUME_ANOMALY_MULTIPLIER = 2.0  # 200% of average


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class Divergence:
    """Divergence detected between price and indicator."""
    type: str  # 'bullish', 'bearish'
    price_trend: str  # 'higher_high', 'lower_low', 'equal'
    indicator_trend: str  # 'lower_high', 'higher_low', 'equal'
    strength: float  # 0.0 to 1.0
    description: str


@dataclass
class SupportResistanceLevel:
    """Support or Resistance level."""
    price: float
    type: str  # 'support' or 'resistance'
    strength: int  # 1-5 (touches)
    is_confirmed: bool


@dataclass
class MarketData:
    """Market data snapshot."""
    symbol: str
    price: float
    price_change_24h: float
    volume_24h: float
    high_24h: float
    low_24h: float
    timestamp: datetime


# ── Technical Analyzer ──────────────────────────────────────────────────────────────

class TechnicalAnalyzer:
    """
    Technical analysis tools for crypto markets.
    """
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._klines_cache: Dict[str, Tuple[List, datetime]] = {}
    
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
    
    # ── RSI Calculation ─────────────────────────────────────────────────────
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate RSI (Relative Strength Index).
        
        Args:
            prices: List of closing prices
            period: RSI period (default: 14)
        
        Returns:
            RSI value (0-100) or None if insufficient data
        """
        if len(prices) < period + 1:
            return None
        
        # Calculate price changes
        changes = []
        for i in range(1, len(prices)):
            changes.append(prices[i] - prices[i - 1])
        
        # Use only the last 'period' changes
        changes = changes[-period:]
        
        gains = [c if c > 0 else 0 for c in changes]
        losses = [-c if c < 0 else 0 for c in changes]
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def fetch_rsi(self, symbol: str, period: int = 14) -> Optional[float]:
        """
        Fetch RSI for a symbol from Bybit.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            period: RSI period
        
        Returns:
            RSI value or None if failed
        """
        # Check cache first
        cache_key = f"rsi_{symbol}_{period}"
        cached = self._get_cache(cache_key, ttl_minutes=5)
        if cached is not None:
            return cached
        
        # Fetch klines
        klines = self.fetch_klines(symbol, interval="D", limit=period + 1)
        if not klines or len(klines) < period + 1:
            return None
        
        # Extract closing prices
        close_prices = [float(k['close']) for k in klines]
        
        # Calculate RSI
        rsi = self.calculate_rsi(close_prices, period)
        
        if rsi is not None:
            self._set_cache(cache_key, rsi)
        
        return rsi
    
    # ── Moving Averages ─────────────────────────────────────────────────────
    
    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Simple Moving Average.
        
        Args:
            prices: List of prices
            period: SMA period
        
        Returns:
            SMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        return round(sum(prices[-period:]) / period, 8)
    
    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Exponential Moving Average.
        
        Args:
            prices: List of prices
            period: EMA period
        
        Returns:
            EMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        
        # Start with SMA for first EMA
        ema = sum(prices[:period]) / period
        
        # Calculate EMA
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return round(ema, 8)
    
    def fetch_sma(self, symbol: str, period: int = 20) -> Optional[float]:
        """
        Fetch SMA for a symbol.
        
        Args:
            symbol: Trading pair
            period: SMA period
        
        Returns:
            SMA value or None
        """
        cache_key = f"sma_{symbol}_{period}"
        cached = self._get_cache(cache_key, ttl_minutes=10)
        if cached is not None:
            return cached
        
        klines = self.fetch_klines(symbol, interval="D", limit=max(period, 200))
        if not klines or len(klines) < period:
            return None
        
        close_prices = [float(k['close']) for k in klines]
        sma = self.calculate_sma(close_prices, period)
        
        if sma is not None:
            self._set_cache(cache_key, sma)
        
        return sma
    
    # ── Support/Resistance Levels ───────────────────────────────────────────
    
    def find_support_resistance(self, prices: List[float], window: int = 20) -> List[SupportResistanceLevel]:
        """
        Find support and resistance levels from price data.
        
        Uses pivot point detection algorithm.
        
        Args:
            prices: List of prices
            window: Lookback window for pivot detection
        
        Returns:
            List of support/resistance levels
        """
        if len(prices) < window * 2:
            return []
        
        levels = []
        price_dict = {}  # price -> count
        
        # Find local maxima and minima
        for i in range(window, len(prices) - window):
            is_resistance = True
            is_support = True
            
            # Check if local maximum
            for j in range(i - window, i + window + 1):
                if j != i:
                    if prices[j] > prices[i]:
                        is_resistance = False
                    if prices[j] < prices[i]:
                        is_support = False
            
            if is_resistance:
                price = prices[i]
                price_dict[price] = price_dict.get(price, 0) + 1
                levels.append(SupportResistanceLevel(
                    price=price,
                    type='resistance',
                    strength=1,
                    is_confirmed=False
                ))
            
            if is_support:
                price = prices[i]
                price_dict[price] = price_dict.get(price, 0) + 1
                levels.append(SupportResistanceLevel(
                    price=price,
                    type='support',
                    strength=1,
                    is_confirmed=False
                ))
        
        # Group nearby levels
        grouped = self._group_levels(levels)
        
        # Sort by strength
        grouped.sort(key=lambda x: x[1], reverse=True)
        
        result = []
        for level_price, strength, level_type in grouped[:10]:
            result.append(SupportResistanceLevel(
                price=level_price,
                type=level_type,
                strength=strength,
                is_confirmed=strength >= 2
            ))
        
        return result
    
    def _group_levels(self, levels: List[SupportResistanceLevel], threshold_pct: float = 0.5) -> List[Tuple[float, int, str]]:
        """Group nearby levels together."""
        if not levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(levels, key=lambda x: x.price)
        
        grouped = []
        current_group = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            prev_price = current_group[-1].price
            current_price = level.price
            
            # Calculate percentage difference
            pct_diff = abs(current_price - prev_price) / prev_price * 100
            
            if pct_diff <= threshold_pct:
                current_group.append(level)
            else:
                # Finalize current group
                avg_price = sum(l.price for l in current_group) / len(current_group)
                strength = sum(l.strength for l in current_group)
                level_type = current_group[0].type
                grouped.append((avg_price, strength, level_type))
                
                current_group = [level]
        
        # Final group
        if current_group:
            avg_price = sum(l.price for l in current_group) / len(current_group)
            strength = sum(l.strength for l in current_group)
            level_type = current_group[0].type
            grouped.append((avg_price, strength, level_type))
        
        return grouped
    
    def find_nearest_levels(self, current_price: float, levels: List[SupportResistanceLevel], num_levels: int = 3) -> Dict[str, List[float]]:
        """
        Find nearest support and resistance levels.
        
        Args:
            current_price: Current price
            levels: List of S/R levels
            num_levels: Number of levels to return
        
        Returns:
            Dict with 'support' and 'resistance' lists
        """
        supports = [l.price for l in levels if l.type == 'support' and l.price < current_price]
        resistances = [l.price for l in levels if l.type == 'resistance' and l.price > current_price]
        
        # Sort by distance to current price
        supports.sort(key=lambda x: abs(x - current_price), reverse=False)
        resistances.sort(key=lambda x: abs(x - current_price), reverse=False)
        
        return {
            'support': supports[:num_levels],
            'resistance': resistances[:num_levels]
        }
    
    # ── Trend Detection ─────────────────────────────────────────────────────
    
    def detect_trend(self, prices: List[float], sma_short: int = 20, sma_long: int = 50) -> str:
        """
        Detect trend direction.
        
        Args:
            prices: List of prices
            sma_short: Short-term SMA period
            sma_long: Long-term SMA period
        
        Returns:
            'UP', 'DOWN', or 'SIDEWAYS'
        """
        if len(prices) < sma_long:
            return 'SIDEWAYS'
        
        sma_20 = self.calculate_sma(prices, sma_short)
        sma_50 = self.calculate_sma(prices, sma_long)
        
        if sma_20 is None or sma_50 is None:
            return 'SIDEWAYS'
        
        current_price = prices[-1]
        
        # Up trend: price above both SMAs, short SMA above long SMA
        if current_price > sma_20 > sma_50:
            return 'UP'
        
        # Down trend: price below both SMAs, short SMA below long SMA
        elif current_price < sma_20 < sma_50:
            return 'DOWN'
        
        # Sideways
        return 'SIDEWAYS'
    
    # ── Divergence Detection ─────────────────────────────────────────────────
    
    def detect_divergence(self, prices: List[float], indicator: List[float], lookback: int = 20) -> Optional[Divergence]:
        """
        Detect divergence between price and indicator (RSI, MACD, etc.).
        
        Args:
            prices: List of prices
            indicator: List of indicator values
            lookback: Number of periods to look back
        
        Returns:
            Divergence object or None
        """
        if len(prices) < lookback or len(indicator) < lookback:
            return None
        
        # Get recent price/action
        recent_prices = prices[-lookback:]
        recent_indicator = indicator[-lookback:]
        
        # Find local extremes
        price_high_idx = recent_prices.index(max(recent_prices))
        price_low_idx = recent_prices.index(min(recent_prices))
        
        indicator_high_idx = recent_indicator.index(max(recent_indicator))
        indicator_low_idx = recent_indicator.index(min(recent_indicator))
        
        # Check for bearish divergence (price higher high, indicator lower high)
        if price_high_idx > indicator_high_idx:
            if recent_prices[-1] > recent_prices[0]:  # Uptrend
                return Divergence(
                    type='bearish',
                    price_trend='higher_high',
                    indicator_trend='lower_high',
                    strength=0.7,
                    description='Bearish divergence: price making higher highs while indicator makes lower highs'
                )
        
        # Check for bullish divergence (price lower low, indicator higher low)
        if price_low_idx > indicator_low_idx:
            if recent_prices[-1] < recent_prices[0]:  # Downtrend
                return Divergence(
                    type='bullish',
                    price_trend='lower_low',
                    indicator_trend='higher_low',
                    strength=0.7,
                    description='Bullish divergence: price making lower lows while indicator makes higher lows'
                )
        
        return None
    
    # ── Volume Analysis ─────────────────────────────────────────────────────
    
    def calculate_average_volume(self, volumes: List[float], period: int = 20) -> Optional[float]:
        """Calculate average volume over period."""
        if len(volumes) < period:
            return None
        return sum(volumes[-period:]) / period
    
    def detect_volume_anomaly(self, symbol: str, multiplier: float = 2.0) -> Optional[Dict]:
        """
        Detect if current volume is anomalous.
        
        Args:
            symbol: Trading pair
            multiplier: Threshold multiplier (e.g., 2.0 = 200% of average)
        
        Returns:
            Dict with anomaly info or None
        """
        cache_key = f"volume_{symbol}"
        cached = self._get_cache(cache_key, ttl_minutes=5)
        if cached is not None:
            return cached
        
        klines = self.fetch_klines(symbol, interval="D", limit=30)
        if not klines or len(klines) < 20:
            return None
        
        volumes = [float(k['volume']) for k in klines]
        current_volume = volumes[-1]
        
        avg_volume = self.calculate_average_volume(volumes)
        if avg_volume is None or avg_volume == 0:
            return None
        
        volume_ratio = current_volume / avg_volume
        
        if volume_ratio >= multiplier:
            result = {
                'current_volume': current_volume,
                'average_volume': avg_volume,
                'volume_ratio': volume_ratio,
                'is_anomaly': True
            }
            self._set_cache(cache_key, result)
            return result
        
        self._set_cache(cache_key, {'is_anomaly': False})
        return None
    
    # ── Data Fetching ───────────────────────────────────────────────────────
    
    def fetch_klines(self, symbol: str, interval: str = "D", limit: int = 100) -> List[Dict]:
        """
        Fetch kline/candlestick data from Bybit.
        
        Args:
            symbol: Trading pair
            interval: Timeframe (D, 60, 15, 5, etc.)
            limit: Number of candles
        
        Returns:
            List of kline data
        """
        cache_key = f"klines_{symbol}_{interval}_{limit}"
        
        # Check cache (5 min TTL)
        if cache_key in self._klines_cache:
            data, cached_at = self._klines_cache[cache_key]
            if datetime.now() - cached_at < timedelta(minutes=5):
                return data
        
        try:
            url = f"{BYBIT_API_BASE}/market/kline"
            params = {
                'category': 'spot',
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('retCode') == 0 and data.get('result', {}).get('list'):
                klines = data['result']['list']
                
                # Parse klines: [timestamp, open, high, low, close, volume, turnover]
                parsed = []
                for k in klines:
                    parsed.append({
                        'timestamp': datetime.fromtimestamp(int(k[0]) / 1000),
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5]),
                        'turnover': float(k[6])
                    })
                
                # Reverse to get chronological order
                parsed.reverse()
                
                self._klines_cache[cache_key] = (parsed, datetime.now())
                return parsed
        except Exception as e:
            print(f"[TechnicalAnalyzer] Error fetching klines for {symbol}: {e}")
        
        return []
    
    def fetch_market_data(self, symbol: str) -> Optional[MarketData]:
        """Fetch current market data for a symbol."""
        try:
            url = f"{BYBIT_API_BASE}/market/tickers"
            params = {'category': 'spot', 'symbol': symbol}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('retCode') == 0 and data.get('result', {}).get('list'):
                ticker = data['result']['list'][0]
                
                return MarketData(
                    symbol=symbol,
                    price=float(ticker['price']),
                    price_change_24h=float(ticker.get('price24hPcnt', 0)) * 100,
                    volume_24h=float(ticker.get('volume24h', 0)),
                    high_24h=float(ticker.get('high24h', 0)),
                    low_24h=float(ticker.get('low24h', 0)),
                    timestamp=datetime.now()
                )
        except Exception as e:
            print(f"[TechnicalAnalyzer] Error fetching market data for {symbol}: {e}")
        
        return None
    
    # ── Comprehensive Analysis ───────────────────────────────────────────────
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """
        Perform comprehensive technical analysis on a symbol.
        
        Args:
            symbol: Trading pair
        
        Returns:
            Dict with analysis results
        """
        result = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'success': False
        }
        
        # Fetch data
        market_data = self.fetch_market_data(symbol)
        if not market_data:
            return result
        
        klines = self.fetch_klines(symbol, interval="D", limit=200)
        if not klines:
            return result
        
        close_prices = [float(k['close']) for k in klines]
        volumes = [float(k['volume']) for k in klines]
        
        # RSI
        rsi = self.calculate_rsi(close_prices)
        
        # SMAs
        sma_20 = self.calculate_sma(close_prices, 20)
        sma_50 = self.calculate_sma(close_prices, 50)
        sma_200 = self.calculate_sma(close_prices, 200)
        
        # Trend
        trend = self.detect_trend(close_prices)
        
        # Support/Resistance
        sr_levels = self.find_support_resistance(close_prices)
        nearest_levels = self.find_nearest_levels(market_data.price, sr_levels)
        
        # Volume
        avg_volume = self.calculate_average_volume(volumes)
        volume_ratio = market_data.volume_24h / avg_volume if avg_volume else 0
        
        # Divergence (if RSI available)
        divergence = None
        if rsi:
            rsi_history = []
            for i in range(len(close_prices) - 14):
                rsi_val = self.calculate_rsi(close_prices[:i+15])
                if rsi_val:
                    rsi_history.append(rsi_val)
            if rsi_history:
                divergence = self.detect_divergence(close_prices, rsi_history)
        
        result.update({
            'success': True,
            'price': market_data.price,
            'price_change_24h': market_data.price_change_24h,
            'volume_24h': market_data.volume_24h,
            'avg_volume_20d': avg_volume,
            'volume_ratio': volume_ratio,
            'rsi': rsi,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'trend': trend,
            'support_levels': nearest_levels.get('support', []),
            'resistance_levels': nearest_levels.get('resistance', []),
            'divergence': divergence.to_dict() if divergence else None
        })
        
        return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    """CLI for technical analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Technical Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python technical_analysis.py --symbol BTCUSDT
  python technical_analysis.py --symbol ETHUSDT --rsi
  python technical_analysis.py --symbol SOLUSDT --sr-levels
  python technical_analysis.py --symbol AVAXUSDT --full
        """
    )
    
    parser.add_argument('--symbol', '-s', default='BTCUSDT',
                       help='Trading pair (default: BTCUSDT)')
    parser.add_argument('--rsi', action='store_true',
                       help='Show RSI analysis')
    parser.add_argument('--sma', action='store_true',
                       help='Show Moving Averages')
    parser.add_argument('--sr-levels', action='store_true',
                       help='Show Support/Resistance levels')
    parser.add_argument('--trend', action='store_true',
                       help='Show trend analysis')
    parser.add_argument('--volume', action='store_true',
                       help='Show volume analysis')
    parser.add_argument('--full', action='store_true',
                       help='Full analysis (all indicators)')
    
    args = parser.parse_args()
    
    analyzer = TechnicalAnalyzer()
    
    print(f"\n📊 Technical Analysis: {args.symbol}")
    print("=" * 50)
    
    # Get market data
    market_data = analyzer.fetch_market_data(args.symbol)
    if market_data:
        print(f"💰 Price: ${market_data.price:,.2f}")
        print(f"📈 24h Change: {market_data.price_change_24h:+.2f}%")
        print(f"📊 24h Volume: {market_data.volume_24h:,.0f}")
    else:
        print("❌ Failed to fetch market data")
        return
    
    # Get klines
    klines = analyzer.fetch_klines(args.symbol, interval="D", limit=200)
    if not klines:
        print("❌ Failed to fetch kline data")
        return
    
    close_prices = [float(k['close']) for k in klines]
    volumes = [float(k['volume']) for k in klines]
    
    # Full analysis or specific
    show_all = args.full or not any([args.rsi, args.sma, args.sr_levels, args.trend, args.volume])
    
    if show_all or args.rsi:
        rsi = analyzer.calculate_rsi(close_prices)
        rsi_status = "🔴 Oversold" if rsi and rsi < 30 else "🟢 Overbought" if rsi and rsi > 70 else "⚪ Neutral"
        print(f"\n📉 RSI (14): {rsi:.2f} {rsi_status if rsi else 'N/A'}")
    
    if show_all or args.sma:
        sma_20 = analyzer.calculate_sma(close_prices, 20)
        sma_50 = analyzer.calculate_sma(close_prices, 50)
        sma_200 = analyzer.calculate_sma(close_prices, 200)
        print(f"\n📊 Moving Averages:")
        print(f"   SMA 20:  ${sma_20:,.2f}" if sma_20 else "   SMA 20: N/A")
        print(f"   SMA 50:  ${sma_50:,.2f}" if sma_50 else "   SMA 50: N/A")
        print(f"   SMA 200: ${sma_200:,.2f}" if sma_200 else "   SMA 200: N/A")
    
    if show_all or args.trend:
        trend = analyzer.detect_trend(close_prices)
        trend_emoji = {"UP": "🟢", "DOWN": "🔴", "SIDEWAYS": "⚪"}
        print(f"\n📈 Trend: {trend_emoji.get(trend, '')} {trend}")
    
    if show_all or args.sr_levels:
        sr_levels = analyzer.find_support_resistance(close_prices)
        nearest = analyzer.find_nearest_levels(market_data.price, sr_levels)
        print(f"\n📍 Support Levels:")
        for i, level in enumerate(nearest.get('support', [])[:3], 1):
            print(f"   S{i}: ${level:,.2f}")
        print(f"📍 Resistance Levels:")
        for i, level in enumerate(nearest.get('resistance', [])[:3], 1):
            print(f"   R{i}: ${level:,.2f}")
    
    if show_all or args.volume:
        avg_vol = analyzer.calculate_average_volume(volumes)
        vol_ratio = market_data.volume_24h / avg_vol if avg_vol else 0
        vol_status = "🔴 ANOMALY" if vol_ratio > 2.0 else "⚪ Normal"
        print(f"\n📊 Volume Analysis:")
        print(f"   Current: {market_data.volume_24h:,.0f}")
        print(f"   20d Avg: {avg_vol:,.0f}" if avg_vol else "   20d Avg: N/A")
        print(f"   Ratio:   {vol_ratio:.2f}x {vol_status}")
    
    print()


if __name__ == '__main__':
    main()
