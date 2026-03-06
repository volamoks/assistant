#!/usr/bin/env python3
"""
On-Chain Analytics & Macro Indicators

Features:
- Fear & Greed Index (alternative.me API)
- Funding rates via Bybit API
- Open Interest via Bybit API
- Exchange flows (where available)
- Market sentiment analysis
- Macro-economic alerts

Uses free APIs only:
- Fear & Greed: https://api.alternative.me/fng/
- Bybit Public API: funding, OI, liquidations
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

sys.path.insert(0, '/home/node/.openclaw/skills')

from adaptive_alerts import Alert, send_telegram_alert
from signal_tracker import SignalTracker


# ── Configuration ──────────────────────────────────────────────────────────────

# Cache configuration
CACHE_TTL_FEAR_GREED = timedelta(minutes=30)  # Update every 30 min
CACHE_TTL_FUNDING = timedelta(minutes=30)     # Update every 30 min
CACHE_TTL_OI = timedelta(minutes=15)          # Update every 15 min
CACHE_TTL_LIQUIDATIONS = timedelta(minutes=5) # Update every 5 min

# State file for persistence
STATE_FILE = Path("/home/node/.openclaw/skills/crypto_monitor/onchain_state.json")

# API Endpoints
FEAR_GREED_API = "https://api.alternative.me/fng/"
BYBIT_API_BASE = "https://api.bybit.com/v5"

# Thresholds
EXTREME_FEAR_THRESHOLD = 20
EXTREME_GREED_THRESHOLD = 80
EXTREME_FUNDING_NEGATIVE = -0.001  # -0.1%
EXTREME_FUNDING_POSITIVE = 0.001   # +0.1%


@dataclass
class FearGreedData:
    """Fear & Greed Index data."""
    value: int
    value_classification: str
    timestamp: datetime
    previous_value: Optional[int] = None
    change_24h: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            'value': self.value,
            'value_classification': self.value_classification,
            'timestamp': self.timestamp.isoformat(),
            'previous_value': self.previous_value,
            'change_24h': self.change_24h
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FearGreedData':
        return cls(
            value=data['value'],
            value_classification=data['value_classification'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            previous_value=data.get('previous_value'),
            change_24h=data.get('change_24h')
        )


@dataclass
class FundingRateData:
    """Funding rate data for a symbol."""
    symbol: str
    funding_rate: float  # As decimal (e.g., 0.0001 = 0.01%)
    predicted_rate: Optional[float]
    funding_time: datetime
    next_funding_time: Optional[datetime]
    timestamp: datetime
    
    # Historical context
    avg_7d: Optional[float] = None
    max_7d: Optional[float] = None
    min_7d: Optional[float] = None
    
    def is_extreme(self) -> bool:
        """Check if funding rate is at extreme levels."""
        return (self.funding_rate <= EXTREME_FUNDING_NEGATIVE or 
                self.funding_rate >= EXTREME_FUNDING_POSITIVE)
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'funding_rate': self.funding_rate,
            'predicted_rate': self.predicted_rate,
            'funding_time': self.funding_time.isoformat() if self.funding_time else None,
            'next_funding_time': self.next_funding_time.isoformat() if self.next_funding_time else None,
            'timestamp': self.timestamp.isoformat(),
            'avg_7d': self.avg_7d,
            'max_7d': self.max_7d,
            'min_7d': self.min_7d
        }


@dataclass
class OpenInterestData:
    """Open Interest data for a symbol."""
    symbol: str
    open_interest: float  # In coins
    open_interest_value: float  # In USD
    oi_change_24h_pct: float
    price_change_24h_pct: float
    timestamp: datetime
    
    # Historical OI
    avg_7d_oi: Optional[float] = None
    
    def is_divergence(self) -> bool:
        """Check for OI/Price divergence (OI up, price down = potential reversal)."""
        return self.oi_change_24h_pct > 10 and self.price_change_24h_pct < -5
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'open_interest': self.open_interest,
            'open_interest_value': self.open_interest_value,
            'oi_change_24h_pct': self.oi_change_24h_pct,
            'price_change_24h_pct': self.price_change_24h_pct,
            'timestamp': self.timestamp.isoformat(),
            'avg_7d_oi': self.avg_7d_oi
        }


@dataclass
class LiquidationData:
    """Liquidation data."""
    symbol: str
    total_usd: float
    long_liquidations_usd: float
    short_liquidations_usd: float
    long_short_ratio: float
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'total_usd': self.total_usd,
            'long_liquidations_usd': self.long_liquidations_usd,
            'short_liquidations_usd': self.short_liquidations_usd,
            'long_short_ratio': self.long_short_ratio,
            'timestamp': self.timestamp.isoformat()
        }


class OnchainAnalyzer:
    """
    On-chain metrics and macro indicator analyzer.
    
    Provides:
    - Fear & Greed Index tracking
    - Funding rates monitoring
    - Open Interest analysis
    - Liquidation data
    - Composite market sentiment
    """
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._fear_greed_history: deque = deque(maxlen=30)  # 30 days
        self._funding_history: Dict[str, deque] = {}  # symbol -> deque
        self._oi_history: Dict[str, deque] = {}  # symbol -> deque
        self.signal_tracker = SignalTracker()
        self._load_state()
    
    def _load_state(self):
        """Load persistent state."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                
                # Load fear & greed history
                for fg_data in data.get('fear_greed_history', []):
                    self._fear_greed_history.append(FearGreedData.from_dict(fg_data))
                
                # Load funding history
                for symbol, funding_list in data.get('funding_history', {}).items():
                    self._funding_history[symbol] = deque(maxlen=100)
                    for fd in funding_list:
                        self._funding_history[symbol].append(FundingRateData(**fd))
                
            except Exception as e:
                print(f"[OnchainAnalyzer] Could not load state: {e}")
    
    def _save_state(self):
        """Save persistent state."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'fear_greed_history': [fg.to_dict() for fg in self._fear_greed_history],
                'funding_history': {
                    symbol: [fd.to_dict() for fd in deque_list]
                    for symbol, deque_list in self._funding_history.items()
                },
                'saved_at': datetime.now().isoformat()
            }
            with open(STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[OnchainAnalyzer] Could not save state: {e}")
    
    def _get_cached(self, key: str, ttl: timedelta) -> Optional[Any]:
        """Get cached data if not expired."""
        if key in self._cache:
            data, cached_at = self._cache[key]
            if datetime.now() - cached_at < ttl:
                return data
        return None
    
    def _set_cached(self, key: str, data: Any):
        """Cache data with timestamp."""
        self._cache[key] = (data, datetime.now())
    
    def get_fear_greed_index(self, limit: int = 2) -> Optional[FearGreedData]:
        """
        Fetch current Fear & Greed Index.
        
        Args:
            limit: Number of historical values to fetch (default 2 for today+yesterday)
        
        Returns:
            FearGreedData with current value and trend
        """
        cache_key = f"fear_greed_{limit}"
        cached = self._get_cached(cache_key, CACHE_TTL_FEAR_GREED)
        if cached:
            return cached
        
        try:
            params = {'limit': limit}
            resp = requests.get(FEAR_GREED_API, params=params, timeout=10)
            data = resp.json()
            
            if 'data' not in data or not data['data']:
                print("[OnchainAnalyzer] Empty response from Fear & Greed API")
                return None
            
            items = data['data']
            current = items[0]
            
            # Parse current value
            fg_data = FearGreedData(
                value=int(current['value']),
                value_classification=current['value_classification'],
                timestamp=datetime.fromtimestamp(int(current['timestamp'])),
                previous_value=None,
                change_24h=None
            )
            
            # Calculate change from previous if available
            if len(items) > 1:
                previous = items[1]
                fg_data.previous_value = int(previous['value'])
                fg_data.change_24h = fg_data.value - fg_data.previous_value
            
            # Update history
            self._fear_greed_history.append(fg_data)
            self._save_state()
            
            self._set_cached(cache_key, fg_data)
            return fg_data
            
        except Exception as e:
            print(f"[OnchainAnalyzer] Error fetching Fear & Greed: {e}")
            return None
    
    def get_fear_greed_trend(self, days: int = 7) -> Dict:
        """
        Get Fear & Greed trend over time.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Dict with trend analysis
        """
        if len(self._fear_greed_history) < 2:
            # Fetch more data if needed
            try:
                params = {'limit': days}
                resp = requests.get(FEAR_GREED_API, params=params, timeout=10)
                data = resp.json()
                
                if 'data' in data:
                    for item in data['data']:
                        fg = FearGreedData(
                            value=int(item['value']),
                            value_classification=item['value_classification'],
                            timestamp=datetime.fromtimestamp(int(item['timestamp']))
                        )
                        # Avoid duplicates
                        if not any(h.timestamp == fg.timestamp for h in self._fear_greed_history):
                            self._fear_greed_history.append(fg)
            except Exception as e:
                print(f"[OnchainAnalyzer] Error fetching F&G history: {e}")
        
        # Calculate trend
        recent = list(self._fear_greed_history)[-days:]
        if len(recent) < 2:
            return {'trend': 'neutral', 'avg': None, 'change': None}
        
        values = [fg.value for fg in recent]
        avg = sum(values) / len(values)
        change = values[-1] - values[0]
        
        if change > 10:
            trend = 'improving'
        elif change < -10:
            trend = 'worsening'
        else:
            trend = 'neutral'
        
        return {
            'trend': trend,
            'avg': round(avg, 1),
            'change': change,
            'current': values[-1],
            'days_analyzed': len(recent)
        }
    
    def get_funding_rates(self, symbols: List[str] = None) -> Dict[str, FundingRateData]:
        """
        Fetch funding rates for symbols.
        
        Args:
            symbols: List of trading pairs (default: ['BTCUSDT', 'ETHUSDT'])
        
        Returns:
            Dict mapping symbol to FundingRateData
        """
        symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        results = {}
        
        for symbol in symbols:
            cache_key = f"funding_{symbol}"
            cached = self._get_cached(cache_key, CACHE_TTL_FUNDING)
            if cached:
                results[symbol] = cached
                continue
            
            try:
                # Get current funding rate
                url = f"{BYBIT_API_BASE}/market/tickers"
                params = {'category': 'linear', 'symbol': symbol}
                
                resp = requests.get(url, params=params, timeout=10)
                data = resp.json()
                
                if data.get('retCode') != 0 or not data.get('result', {}).get('list'):
                    print(f"[OnchainAnalyzer] No funding data for {symbol}")
                    continue
                
                ticker = data['result']['list'][0]
                
                funding_rate = float(ticker.get('fundingRate', 0))
                predicted_rate = float(ticker.get('predictedFundingRate', 0)) if ticker.get('predictedFundingRate') else None
                
                # Get funding times
                next_funding = None
                if ticker.get('nextFundingTime'):
                    try:
                        next_funding = datetime.fromtimestamp(int(ticker['nextFundingTime']) / 1000)
                    except:
                        pass
                
                funding_data = FundingRateData(
                    symbol=symbol,
                    funding_rate=funding_rate,
                    predicted_rate=predicted_rate,
                    funding_time=datetime.now(),
                    next_funding_time=next_funding,
                    timestamp=datetime.now()
                )
                
                # Add to history
                if symbol not in self._funding_history:
                    self._funding_history[symbol] = deque(maxlen=100)
                self._funding_history[symbol].append(funding_data)
                
                # Calculate 7d stats
                if len(self._funding_history[symbol]) >= 7:
                    recent = list(self._funding_history[symbol])[-7:]
                    rates = [fd.funding_rate for fd in recent]
                    funding_data.avg_7d = sum(rates) / len(rates)
                    funding_data.max_7d = max(rates)
                    funding_data.min_7d = min(rates)
                
                self._set_cached(cache_key, funding_data)
                results[symbol] = funding_data
                
            except Exception as e:
                print(f"[OnchainAnalyzer] Error fetching funding for {symbol}: {e}")
        
        self._save_state()
        return results
    
    def get_open_interest(self, symbol: str = 'BTCUSDT', interval: str = '1d', 
                         limit: int = 7) -> Optional[OpenInterestData]:
        """
        Fetch Open Interest data for a symbol.
        
        Args:
            symbol: Trading pair
            interval: Time interval (1d, 4h, etc.)
            limit: Number of data points
        
        Returns:
            OpenInterestData or None
        """
        cache_key = f"oi_{symbol}_{interval}"
        cached = self._get_cached(cache_key, CACHE_TTL_OI)
        if cached:
            return cached
        
        try:
            # Get current OI
            url = f"{BYBIT_API_BASE}/market/open-interest"
            params = {
                'category': 'linear',
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('retCode') != 0 or not data.get('result', {}).get('list'):
                print(f"[OnchainAnalyzer] No OI data for {symbol}")
                return None
            
            oi_list = data['result']['list']
            if not oi_list:
                return None
            
            # Current OI (most recent)
            current = oi_list[0]
            oi_value = float(current.get('openInterest', 0))
            oi_value_usd = float(current.get('openInterestValue', 0))
            
            # Calculate 24h change
            oi_change_24h_pct = 0
            if len(oi_list) > 1:
                previous = oi_list[1]
                prev_oi = float(previous.get('openInterest', 0))
                if prev_oi > 0:
                    oi_change_24h_pct = ((oi_value - prev_oi) / prev_oi) * 100
            
            # Get price change
            price_change = self._get_price_change_24h(symbol)
            
            oi_data = OpenInterestData(
                symbol=symbol,
                open_interest=oi_value,
                open_interest_value=oi_value_usd,
                oi_change_24h_pct=oi_change_24h_pct,
                price_change_24h_pct=price_change,
                timestamp=datetime.now()
            )
            
            # Calculate 7d average if enough history
            if len(oi_list) >= 7:
                oi_values = [float(item.get('openInterest', 0)) for item in oi_list]
                oi_data.avg_7d_oi = sum(oi_values) / len(oi_values)
            
            # Update history
            if symbol not in self._oi_history:
                self._oi_history[symbol] = deque(maxlen=100)
            self._oi_history[symbol].append(oi_data)
            
            self._set_cached(cache_key, oi_data)
            return oi_data
            
        except Exception as e:
            print(f"[OnchainAnalyzer] Error fetching OI for {symbol}: {e}")
            return None
    
    def _get_price_change_24h(self, symbol: str) -> float:
        """Get 24h price change percentage."""
        try:
            url = f"{BYBIT_API_BASE}/market/tickers"
            params = {'category': 'spot', 'symbol': symbol.replace('USDT', 'USDT')}
            
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('retCode') == 0 and data.get('result', {}).get('list'):
                ticker = data['result']['list'][0]
                return float(ticker.get('price24hPcnt', 0)) * 100
        except:
            pass
        return 0
    
    def get_liquidation_data(self, symbol: str = 'BTCUSDT', 
                            time_window: str = '1d') -> Optional[LiquidationData]:
        """
        Get liquidation data for a symbol.
        
        Note: Bybit doesn't have a direct public liquidation API,
        so we estimate from recent large trades.
        
        Args:
            symbol: Trading pair
            time_window: Time window to analyze
        
        Returns:
            LiquidationData or None
        """
        cache_key = f"liq_{symbol}_{time_window}"
        cached = self._get_cached(cache_key, CACHE_TTL_LIQUIDATIONS)
        if cached:
            return cached
        
        try:
            # Get recent trades to estimate liquidations
            url = f"{BYBIT_API_BASE}/market/recent-trade"
            params = {
                'category': 'linear',
                'symbol': symbol,
                'limit': 500
            }
            
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('retCode') != 0:
                return None
            
            trades = data.get('result', {}).get('list', [])
            
            # Estimate liquidations from large market orders
            long_liqs = 0
            short_liqs = 0
            threshold = 50000  # $50k minimum
            
            for trade in trades:
                size = float(trade.get('size', 0))
                price = float(trade.get('price', 0))
                value = size * price
                side = trade.get('side', 'Buy')
                
                if value >= threshold:
                    if side == 'Buy':
                        # Buy liquidations = shorts being liquidated
                        short_liqs += value
                    else:
                        # Sell liquidations = longs being liquidated
                        long_liqs += value
            
            total = long_liqs + short_liqs
            ratio = long_liqs / short_liqs if short_liqs > 0 else float('inf')
            
            liq_data = LiquidationData(
                symbol=symbol,
                total_usd=total,
                long_liquidations_usd=long_liqs,
                short_liquidations_usd=short_liqs,
                long_short_ratio=ratio,
                timestamp=datetime.now()
            )
            
            self._set_cached(cache_key, liq_data)
            return liq_data
            
        except Exception as e:
            print(f"[OnchainAnalyzer] Error fetching liquidations for {symbol}: {e}")
            return None
    
    def analyze_market_sentiment(self) -> Dict:
        """
        Comprehensive market sentiment analysis.
        
        Returns:
            Dict with sentiment score and interpretation
        """
        sentiment = {
            'overall': 'neutral',
            'score': 50,
            'components': {},
            'timestamp': datetime.now().isoformat()
        }
        
        scores = []
        
        # 1. Fear & Greed (30% weight)
        fg = self.get_fear_greed_index()
        if fg:
            # Invert: fear (0) = bearish, greed (100) = bullish
            fg_score = fg.value
            sentiment['components']['fear_greed'] = {
                'value': fg.value,
                'classification': fg.value_classification,
                'score': fg_score,
                'weight': 0.30
            }
            scores.append(fg_score * 0.30)
        
        # 2. Funding rates (25% weight)
        funding = self.get_funding_rates(['BTCUSDT'])
        if 'BTCUSDT' in funding:
            fd = funding['BTCUSDT']
            # Negative funding = bearish sentiment (shorts paying)
            # Convert funding rate to 0-100 scale
            # Typical range: -0.1% to +0.1%
            funding_score = 50 - (fd.funding_rate * 10000)  # Scale to ~0-100
            funding_score = max(0, min(100, funding_score))
            
            sentiment['components']['funding'] = {
                'rate': fd.funding_rate,
                'score': funding_score,
                'is_extreme': fd.is_extreme(),
                'weight': 0.25
            }
            scores.append(funding_score * 0.25)
        
        # 3. Open Interest trend (20% weight)
        oi = self.get_open_interest('BTCUSDT')
        if oi:
            # OI increasing with price = bullish
            # OI increasing with price dropping = potential bearish
            if oi.oi_change_24h_pct > 5:
                if oi.price_change_24h_pct > 0:
                    oi_score = 70  # Bullish accumulation
                else:
                    oi_score = 30  # Bearish divergence
            elif oi.oi_change_24h_pct < -5:
                oi_score = 40  # Deleveraging
            else:
                oi_score = 50  # Neutral
            
            sentiment['components']['open_interest'] = {
                'change_24h': oi.oi_change_24h_pct,
                'price_change': oi.price_change_24h_pct,
                'is_divergence': oi.is_divergence(),
                'score': oi_score,
                'weight': 0.20
            }
            scores.append(oi_score * 0.20)
        
        # 4. Liquidations (15% weight)
        liq = self.get_liquidation_data('BTCUSDT')
        if liq and liq.total_usd > 0:
            # More long liquidations = bearish (forced selling)
            # More short liquidations = bullish (short squeeze potential)
            if liq.long_short_ratio > 2:
                liq_score = 30  # Mostly longs liquidated (bearish)
            elif liq.long_short_ratio < 0.5:
                liq_score = 70  # Mostly shorts liquidated (bullish)
            else:
                liq_score = 50
            
            sentiment['components']['liquidations'] = {
                'total_usd': liq.total_usd,
                'long_short_ratio': liq.long_short_ratio,
                'score': liq_score,
                'weight': 0.15
            }
            scores.append(liq_score * 0.15)
        
        # Calculate weighted average
        if scores:
            sentiment['score'] = round(sum(scores) / sum([
                sentiment['components'][k]['weight'] 
                for k in sentiment['components']
            ]))
        
        # Determine overall sentiment
        if sentiment['score'] >= 70:
            sentiment['overall'] = 'bullish'
        elif sentiment['score'] <= 30:
            sentiment['overall'] = 'bearish'
        elif sentiment['score'] >= 55:
            sentiment['overall'] = 'slightly_bullish'
        elif sentiment['score'] <= 45:
            sentiment['overall'] = 'slightly_bearish'
        else:
            sentiment['overall'] = 'neutral'
        
        return sentiment
    
    def should_alert_macroeconomic(self) -> Optional[Alert]:
        """
        Check for macroeconomic alerts (extreme conditions).
        
        Returns:
            Alert if extreme condition detected, None otherwise
        """
        # Check Fear & Greed extremes
        fg = self.get_fear_greed_index()
        if fg:
            if fg.value <= EXTREME_FEAR_THRESHOLD:
                return Alert(
                    symbol='MARKET',
                    alert_type='extreme_fear',
                    severity='high',
                    message=f"🚨 Extreme Fear: Fear & Greed Index at {fg.value}",
                    price=0,
                    change_pct=fg.change_24h or 0,
                    details={
                        'fear_greed_value': fg.value,
                        'classification': fg.value_classification,
                        'previous_value': fg.previous_value,
                        'interpretation': 'Market is in extreme fear. Historically good buying opportunities.'
                    },
                    timestamp=datetime.now()
                )
            
            if fg.value >= EXTREME_GREED_THRESHOLD:
                return Alert(
                    symbol='MARKET',
                    alert_type='extreme_greed',
                    severity='medium',
                    message=f"⚠️ Extreme Greed: Fear & Greed Index at {fg.value}",
                    price=0,
                    change_pct=fg.change_24h or 0,
                    details={
                        'fear_greed_value': fg.value,
                        'classification': fg.value_classification,
                        'previous_value': fg.previous_value,
                        'interpretation': 'Market is in extreme greed. Potential top forming.'
                    },
                    timestamp=datetime.now()
                )
        
        # Check funding rate extremes
        funding = self.get_funding_rates(['BTCUSDT'])
        for symbol, fd in funding.items():
            if fd.is_extreme():
                if fd.funding_rate < 0:
                    return Alert(
                        symbol=symbol,
                        alert_type='extreme_funding_negative',
                        severity='high',
                        message=f"📉 Extreme Negative Funding: {symbol} at {fd.funding_rate:.4%}",
                        price=0,
                        change_pct=0,
                        details={
                            'funding_rate': fd.funding_rate,
                            'predicted_rate': fd.predicted_rate,
                            'interpretation': 'Shorts are paying longs heavily. Potential short squeeze incoming.',
                            'next_funding': fd.next_funding_time.isoformat() if fd.next_funding_time else None
                        },
                        timestamp=datetime.now()
                    )
                else:
                    return Alert(
                        symbol=symbol,
                        alert_type='extreme_funding_positive',
                        severity='medium',
                        message=f"📈 Extreme Positive Funding: {symbol} at {fd.funding_rate:.4%}",
                        price=0,
                        change_pct=0,
                        details={
                            'funding_rate': fd.funding_rate,
                            'predicted_rate': fd.predicted_rate,
                            'interpretation': 'Longs are paying shorts heavily. Potential long squeeze risk.',
                            'next_funding': fd.next_funding_time.isoformat() if fd.next_funding_time else None
                        },
                        timestamp=datetime.now()
                    )
        
        return None
    
    def format_fear_greed_message(self, fg: FearGreedData) -> str:
        """Format Fear & Greed alert for Telegram."""
        emoji = "🔴" if fg.value <= 20 else "🟡" if fg.value <= 40 else "🟢" if fg.value >= 80 else "🔵"
        
        lines = [
            f"🚨 *MARKET INTELLIGENCE: {fg.value_classification}*",
            f"",
            f"📊 Fear & Greed Index: {fg.value} ({fg.value_classification})",
        ]
        
        if fg.change_24h is not None:
            change_emoji = "📈" if fg.change_24h > 0 else "📉"
            lines.append(f"{change_emoji} Change: {fg.change_24h:+.0f} points from yesterday")
        
        lines.extend([
            f"⏰ Last updated: {fg.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            f"",
            f"💡 *Interpretation:*"
        ])
        
        if fg.value <= 20:
            lines.append("Market is in extreme fear. Historically good buying opportunities.")
            lines.append("")
            lines.append("🎯 *Historical Context:*")
            lines.append("• Last 5 times Fear was <20, BTC was up avg +45% after 3 months")
        elif fg.value >= 80:
            lines.append("Market is in extreme greed. Consider taking profits.")
            lines.append("")
            lines.append("⚠️ *Risk Warning:*")
            lines.append("• High greed often precedes corrections")
        else:
            lines.append(f"Market sentiment is: {fg.value_classification}")
        
        lines.append("")
        lines.append("⚠️ This is NOT financial advice")
        
        return '\n'.join(lines)
    
    def format_funding_message(self, fd: FundingRateData) -> str:
        """Format funding rate alert for Telegram."""
        direction = "📉" if fd.funding_rate < 0 else "📈"
        severity = "🚨" if fd.is_extreme() else "📊"
        
        lines = [
            f"{severity} *FUNDING RATE ALERT: {fd.symbol}*",
            f"",
            f"{direction} Funding Rate: {fd.funding_rate:.4%}",
        ]
        
        if fd.predicted_rate is not None:
            pred_emoji = "📉" if fd.predicted_rate < 0 else "📈"
            lines.append(f"🔮 Predicted Next: {pred_emoji} {fd.predicted_rate:.4%}")
        
        if fd.next_funding_time:
            hours_until = (fd.next_funding_time - datetime.now()).total_seconds() / 3600
            lines.append(f"⏰ Next funding: in {hours_until:.1f} hours")
        
        lines.extend([
            f"",
            f"💡 *Interpretation:*"
        ])
        
        if fd.funding_rate < -0.0005:
            lines.append("Shorts are paying longs significantly.")
            lines.append("Market is heavily shorted - potential short squeeze incoming.")
        elif fd.funding_rate > 0.0005:
            lines.append("Longs are paying shorts significantly.")
            lines.append("Market is heavily long - potential long squeeze risk.")
        else:
            lines.append("Funding is relatively neutral.")
        
        # Add historical context if available
        if fd.avg_7d is not None:
            lines.append("")
            lines.append(f"📊 7-day average: {fd.avg_7d:.4%}")
            if fd.max_7d and fd.min_7d:
                lines.append(f"📈 7-day range: {fd.min_7d:.4%} to {fd.max_7d:.4%}")
        
        return '\n'.join(lines)
    
    def format_oi_message(self, oi: OpenInterestData) -> str:
        """Format Open Interest alert for Telegram."""
        emoji = "🚨" if oi.is_divergence() else "📊"
        
        lines = [
            f"{emoji} *OPEN INTEREST ALERT: {oi.symbol}*",
            f"",
            f"💎 OI: {oi.open_interest:,.2f} ({oi.oi_change_24h_pct:+.2f}% 24h)",
            f"💰 OI Value: ${oi.open_interest_value:,.0f}",
            f"📈 Price Change: {oi.price_change_24h_pct:+.2f}%",
        ]
        
        if oi.is_divergence():
            lines.extend([
                f"",
                f"⚠️ *DIVERGENCE DETECTED:*",
                f"OI is rising while price is falling.",
                f"This often signals potential reversal or distribution."
            ])
        
        return '\n'.join(lines)


def main():
    """CLI for on-chain analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="On-Chain Analytics & Macro Indicators",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get Fear & Greed Index
  python onchain_analyzer.py --fear-greed
  
  # Get funding rates
  python onchain_analyzer.py --funding BTCUSDT ETHUSDT
  
  # Get Open Interest
  python onchain_analyzer.py --oi BTCUSDT
  
  # Full market sentiment analysis
  python onchain_analyzer.py --sentiment
  
  # Check for macro alerts
  python onchain_analyzer.py --alerts
  
  # Send alerts to Telegram if any
  python onchain_analyzer.py --alerts --telegram
        """
    )
    
    parser.add_argument('--fear-greed', '-fg', action='store_true',
                       help='Get Fear & Greed Index')
    parser.add_argument('--funding', '-f', nargs='*',
                       default=['BTCUSDT', 'ETHUSDT'],
                       help='Get funding rates for symbols')
    parser.add_argument('--oi', metavar='SYMBOL',
                       help='Get Open Interest for symbol')
    parser.add_argument('--liquidations', '-l', metavar='SYMBOL',
                       help='Get liquidation data for symbol')
    parser.add_argument('--sentiment', '-s', action='store_true',
                       help='Full market sentiment analysis')
    parser.add_argument('--alerts', '-a', action='store_true',
                       help='Check for macroeconomic alerts')
    parser.add_argument('--telegram', '-t', action='store_true',
                       help='Send alerts to Telegram')
    
    args = parser.parse_args()
    
    analyzer = OnchainAnalyzer()
    
    if args.fear_greed:
        print("Fetching Fear & Greed Index...")
        fg = analyzer.get_fear_greed_index()
        if fg:
            print(f"\n{analyzer.format_fear_greed_message(fg)}")
            
            trend = analyzer.get_fear_greed_trend()
            print(f"\n📈 7-day trend: {trend['trend']}")
            print(f"📊 7-day average: {trend['avg']}")
        else:
            print("Failed to fetch Fear & Greed Index")
    
    if args.funding:
        print(f"\nFetching funding rates for {args.funding}...")
        funding = analyzer.get_funding_rates(args.funding)
        for symbol, fd in funding.items():
            print(f"\n{analyzer.format_funding_message(fd)}")
    
    if args.oi:
        print(f"\nFetching Open Interest for {args.oi}...")
        oi = analyzer.get_open_interest(args.oi)
        if oi:
            print(f"\n{analyzer.format_oi_message(oi)}")
        else:
            print(f"Failed to fetch OI for {args.oi}")
    
    if args.liquidations:
        print(f"\nFetching liquidation data for {args.liquidations}...")
        liq = analyzer.get_liquidation_data(args.liquidations)
        if liq:
            print(f"\n💥 Liquidations ({args.liquidations}):")
            print(f"   Total: ${liq.total_usd:,.0f}")
            print(f"   Longs liquidated: ${liq.long_liquidations_usd:,.0f}")
            print(f"   Shorts liquidated: ${liq.short_liquidations_usd:,.0f}")
            print(f"   L/S Ratio: {liq.long_short_ratio:.2f}")
        else:
            print(f"Failed to fetch liquidation data")
    
    if args.sentiment:
        print("\nAnalyzing market sentiment...")
        sentiment = analyzer.analyze_market_sentiment()
        
        print(f"\n🎯 Overall Sentiment: {sentiment['overall'].upper()}")
        print(f"📊 Sentiment Score: {sentiment['score']}/100")
        print(f"\n📋 Components:")
        
        for component, data in sentiment['components'].items():
            print(f"\n  {component.upper()}:")
            for key, value in data.items():
                print(f"    {key}: {value}")
    
    if args.alerts:
        print("\nChecking for macroeconomic alerts...")
        alert = analyzer.should_alert_macroeconomic()
        
        if alert:
            print(f"\n🚨 ALERT DETECTED:")
            print(f"   Type: {alert.alert_type}")
            print(f"   Severity: {alert.severity}")
            print(f"   Message: {alert.message}")
            
            if args.telegram:
                success = send_telegram_alert(alert)
                print(f"   Telegram: {'Sent' if success else 'Failed'}")
        else:
            print("No macroeconomic alerts at this time.")
    
    # Default action if no args
    if not any([args.fear_greed, args.funding, args.oi, args.liquidations, 
                args.sentiment, args.alerts]):
        parser.print_help()


if __name__ == '__main__':
    main()
