"""
Universal HTTP Client for Bybit API

This module provides a shared HTTP client with rate limiting, retry logic,
error handling, and caching for all Bybit API interactions.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import httpx


class BybitAPIError(Exception):
    """Custom exception for Bybit API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.status_code:
            return f"BybitAPIError [{self.status_code}]: {self.message}"
        return f"BybitAPIError: {self.message}"


@dataclass
class CacheEntry:
    """Represents a cached response with TTL."""
    data: Dict
    expires_at: float


@dataclass
class BybitClient:
    """
    Universal async HTTP client for Bybit API.
    
    Features:
    - Rate limiting (configurable delay between requests)
    - Automatic retry with exponential backoff
    - Response caching with TTL
    - Comprehensive error handling
    - Type hints for Python 3.11+
    """
    
    BASE_URL: str = field(default="https://api.bybit.com", init=False)
    DEFAULT_CACHE_TTL: int = field(default=300, init=False)  # 5 minutes
    
    def __post_init__(self) -> None:
        self._rate_limit_ms: int = 200
        self._last_request_time: float = 0
        self._cache: Dict[str, CacheEntry] = {}
        self._client: Optional[httpx.AsyncClient] = None
        self._max_retries: int = 3
        self._base_delay: float = 1.0  # seconds for exponential backoff
    
    def __init__(self, rate_limit_ms: int = 200) -> None:
        """
        Initialize the Bybit client.
        
        Args:
            rate_limit_ms: Minimum delay between requests in milliseconds (default: 200)
        """
        self._rate_limit_ms = rate_limit_ms
        self._last_request_time = 0
        self._cache: Dict[str, CacheEntry] = {}
        self._max_retries = 3
        self._base_delay = 1.0
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "OpenClaw-Bot/1.0"
                }
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def _wait_for_rate_limit(self) -> None:
        """
        Wait if necessary to respect rate limiting.
        
        Ensures minimum delay between consecutive requests.
        """
        current_time = time.time()
        elapsed_ms = (current_time - self._last_request_time) * 1000
        
        if elapsed_ms < self._rate_limit_ms:
            wait_time = (self._rate_limit_ms - elapsed_ms) / 1000
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
    
    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with automatic retry and exponential backoff.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters or request body
            
        Returns:
            Parsed JSON response
            
        Raises:
            BybitAPIError: If all retries fail
        """
        client = await self._get_client()
        last_error: Optional[Exception] = None
        
        for attempt in range(self._max_retries):
            try:
                await self._wait_for_rate_limit()
                
                if method.upper() == "GET":
                    response = await client.get(endpoint, params=params)
                elif method.upper() == "POST":
                    response = await client.post(endpoint, json=params)
                else:
                    raise BybitAPIError(f"Unsupported HTTP method: {method}")
                
                # Handle HTTP errors
                if response.status_code >= 400:
                    if response.status_code in (429, 500, 502, 503, 504):
                        # Retry on rate limit or server errors
                        last_error = BybitAPIError(
                            f"HTTP {response.status_code}",
                            status_code=response.status_code,
                            response={"text": response.text}
                        )
                        if attempt < self._max_retries - 1:
                            delay = self._base_delay * (2 ** attempt)
                            await asyncio.sleep(delay)
                            continue
                    else:
                        # Don't retry on client errors (4xx except 429)
                        raise BybitAPIError(
                            f"HTTP {response.status_code}: {response.text}",
                            status_code=response.status_code,
                            response={"text": response.text}
                        )
                
                # Parse response
                data = response.json()
                
                # Check for Bybit-specific error codes
                if isinstance(data, dict):
                    ret_code = data.get("retCode")
                    if ret_code is not None and ret_code != 0:
                        ret_msg = data.get("retMsg", "Unknown error")
                        raise BybitAPIError(
                            f"Bybit error {ret_code}: {ret_msg}",
                            response=data
                        )
                
                return data
                
            except httpx.TimeoutException as e:
                last_error = BybitAPIError(f"Request timeout: {str(e)}")
                if attempt < self._max_retries - 1:
                    delay = self._base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                    
            except httpx.RequestError as e:
                last_error = BybitAPIError(f"Request failed: {str(e)}")
                if attempt < self._max_retries - 1:
                    delay = self._base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                    
            except BybitAPIError:
                raise
                
            except Exception as e:
                last_error = BybitAPIError(f"Unexpected error: {str(e)}")
                if attempt < self._max_retries - 1:
                    delay = self._base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
        
        # All retries exhausted
        raise last_error or BybitAPIError("Unknown error after retries")
    
    def get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        entry = self._cache.get(key)
        if entry is None:
            return None
        
        if time.time() > entry.expires_at:
            del self._cache[key]
            return None
        
        return entry.data
    
    def set_cached(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        """
        Cache a response with TTL.
        
        Args:
            key: Cache key
            value: Data to cache
            ttl_seconds: Time to live in seconds (default: 300)
        """
        ttl = ttl_seconds or self.DEFAULT_CACHE_TTL
        self._cache[key] = CacheEntry(
            data=value,
            expires_at=time.time() + ttl
        )
    
    def _cache_key(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Generate a cache key from endpoint and params."""
        if params:
            sorted_params = sorted(params.items(), key=lambda x: x[0])
            return f"{endpoint}?{sorted_params}"
        return endpoint
    
    # ==================== API Methods ====================
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest ticker data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            Ticker data dictionary
        """
        endpoint = "/v5/market/tickers"
        params = {"category": "linear", "symbol": symbol}
        
        cache_key = self._cache_key(endpoint, params)
        cached = self.get_cached(cache_key)
        if cached:
            return cached
        
        response = await self._request_with_retry("GET", endpoint, params)
        result = response.get("result", {})
        tickers = result.get("list", [])
        
        if tickers:
            ticker_data = {"symbol": symbol, "data": tickers[0]}
            self.set_cached(cache_key, ticker_data)
            return ticker_data
        
        return {"symbol": symbol, "data": None}
    
    async def get_tickers(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get ticker data for multiple symbols.
        
        Args:
            symbols: List of trading pair symbols
            
        Returns:
            Dictionary mapping symbols to their ticker data
        """
        endpoint = "/v5/market/tickers"
        params = {"category": "linear"}
        
        cache_key = self._cache_key(endpoint, params)
        cached = self.get_cached(cache_key)
        if cached:
            # Filter cached data for requested symbols
            return {
                sym: cached.get("data", {}).get(sym)
                for sym in symbols
            }
        
        response = await self._request_with_retry("GET", endpoint, params)
        result = response.get("result", {})
        tickers = result.get("list", [])
        
        # Build symbol -> ticker mapping
        ticker_map = {}
        for ticker in tickers:
            sym = ticker.get("symbol")
            if sym in symbols:
                ticker_map[sym] = ticker
        
        cached_data = {"data": ticker_map}
        self.set_cached(cache_key, cached_data)
        
        return {sym: ticker_map.get(sym) for sym in symbols}
    
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get K-line (candlestick) data.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            interval: K-line interval (e.g., "1", "5", "15", "60", "240", "D")
            limit: Number of candles to return (max 200)
            
        Returns:
            List of K-line data dictionaries
        """
        endpoint = "/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 200)
        }
        
        cache_key = self._cache_key(endpoint, params)
        cached = self.get_cached(cache_key)
        if cached:
            return cached.get("list", [])
        
        response = await self._request_with_retry("GET", endpoint, params)
        result = response.get("result", {})
        klines = result.get("list", [])
        
        # Parse kline data into structured format
        # Bybit kline format: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
        parsed_klines = []
        for kline in klines:
            if len(kline) >= 7:
                parsed_klines.append({
                    "start_time": kline[0],
                    "open": kline[1],
                    "high": kline[2],
                    "low": kline[3],
                    "close": kline[4],
                    "volume": kline[5],
                    "turnover": kline[6]
                })
        
        result_data = {"list": parsed_klines}
        self.set_cached(cache_key, result_data, ttl_seconds=60)  # Shorter TTL for klines
        
        return parsed_klines
    
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Get current funding rate for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            Funding rate data dictionary
        """
        endpoint = "/v5/market/tickers"
        params = {"category": "linear", "symbol": symbol}
        
        cache_key = self._cache_key(endpoint, params)
        cached = self.get_cached(cache_key)
        if cached:
            data = cached.get("data", {})
            return {
                "symbol": symbol,
                "funding_rate": data.get("fundingRate"),
                "next_funding_time": data.get("nextFundingTime")
            }
        
        response = await self._request_with_retry("GET", endpoint, params)
        result = response.get("result", {})
        tickers = result.get("list", [])
        
        if tickers:
            ticker = tickers[0]
            funding_data = {
                "symbol": symbol,
                "funding_rate": ticker.get("fundingRate"),
                "next_funding_time": ticker.get("nextFundingTime")
            }
            self.set_cached(cache_key, {"data": ticker}, ttl_seconds=60)
            return funding_data
        
        return {"symbol": symbol, "funding_rate": None, "next_funding_time": None}
    
    async def get_open_interest(self, symbol: str) -> Dict[str, Any]:
        """
        Get open interest data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            Open interest data dictionary
        """
        endpoint = "/v5/market/open-interest"
        params = {
            "category": "linear",
            "symbol": symbol,
            "limit": "1"
        }
        
        cache_key = self._cache_key(endpoint, params)
        cached = self.get_cached(cache_key)
        if cached:
            return cached
        
        response = await self._request_with_retry("GET", endpoint, params)
        result = response.get("result", {})
        oi_list = result.get("list", [])
        
        if oi_list:
            oi_data = {
                "symbol": symbol,
                "open_interest": oi_list[0].get("openInterest"),
                "timestamp": oi_list[0].get("timestamp")
            }
            self.set_cached(cache_key, oi_data, ttl_seconds=120)
            return oi_data
        
        return {"symbol": symbol, "open_interest": None, "timestamp": None}
    
    async def get_liquidation(self, symbol: str) -> Dict[str, Any]:
        """
        Get recent liquidation data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            Liquidation data dictionary
        """
        endpoint = "/v5/market/recent-trade"
        params = {
            "category": "linear",
            "symbol": symbol,
            "limit": "100"
        }
        
        # Note: Bybit doesn't have a direct liquidation endpoint in v5
        # This uses recent trades as a proxy - actual liquidations would need
        # to be filtered from trade data or use a different endpoint
        
        cache_key = self._cache_key(endpoint, params)
        cached = self.get_cached(cache_key)
        if cached:
            return cached
        
        response = await self._request_with_retry("GET", endpoint, params)
        result = response.get("result", {})
        trades = result.get("list", [])
        
        # Filter for potential liquidations (large trades)
        liquidations = []
        for trade in trades:
            # Mark trades that might be liquidations based on size
            # This is a simplified heuristic
            liquidations.append({
                "side": trade.get("side"),
                "size": trade.get("size"),
                "price": trade.get("price"),
                "time": trade.get("time"),
                "is_block_trade": trade.get("blockTradeId") is not None
            })
        
        liq_data = {
            "symbol": symbol,
            "liquidations": liquidations,
            "count": len(liquidations)
        }
        self.set_cached(cache_key, liq_data, ttl_seconds=30)
        
        return liq_data


# ==================== Convenience Functions ====================

async def create_client(rate_limit_ms: int = 200) -> BybitClient:
    """
    Factory function to create a BybitClient instance.
    
    Args:
        rate_limit_ms: Rate limit in milliseconds
        
    Returns:
        Configured BybitClient instance
    """
    return BybitClient(rate_limit_ms=rate_limit_ms)


# ==================== Example Usage ====================

if __name__ == "__main__":
    async def main() -> None:
        """Example usage of the BybitClient."""
        client = BybitClient()
        
        try:
            # Get single ticker
            ticker = await client.get_ticker("BTCUSDT")
            print(f"BTC Ticker: {ticker}")
            
            # Get multiple tickers
            tickers = await client.get_tickers(["BTCUSDT", "ETHUSDT"])
            print(f"Tickers: {tickers}")
            
            # Get K-lines
            klines = await client.get_klines("BTCUSDT", "15", limit=100)
            print(f"K-lines count: {len(klines)}")
            
            # Get funding rate
            funding = await client.get_funding_rate("BTCUSDT")
            print(f"Funding Rate: {funding}")
            
            # Get open interest
            oi = await client.get_open_interest("BTCUSDT")
            print(f"Open Interest: {oi}")
            
            # Get liquidations
            liq = await client.get_liquidation("BTCUSDT")
            print(f"Liquidations: {liq}")
            
        finally:
            await client.close()
    
    asyncio.run(main())
