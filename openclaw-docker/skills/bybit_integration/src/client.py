#!/usr/bin/env python3
"""Bybit V5 API Client with HMAC authentication"""

import hmac
import hashlib
import time
import requests
import os
from typing import Optional, Dict, Any

class BybitClient:
    def __init__(self, testnet: bool = False):
        self.api_key = os.environ.get('BYBIT_API', '')
        self.api_secret = os.environ.get('BYBIT_API_SECRET', '')
        self.base_url = 'https://api-testnet.bybit.com' if testnet else 'https://api.bybit.com'
        self.recv_window = '5000'
        self.timeout = 30
        self._cache = {}
        self._cache_ttl = 60  # seconds
    
    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC SHA256 signature"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _get_headers(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict[str, str]:
        """Generate authentication headers"""
        timestamp = str(int(time.time() * 1000))
        
        if params:
            query_string = '&'.join([f'{k}={v}' for k, v in sorted(params.items())])
        else:
            query_string = ''
        
        sign_str = f'{timestamp}{self.api_key}{self.recv_window}{query_string}'
        signature = self._generate_signature(sign_str)
        
        return {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': self.recv_window,
            'Content-Type': 'application/json'
        }
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request"""
        url = f'{self.base_url}{endpoint}'
        headers = self._get_headers(method, endpoint, params)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            else:
                response = requests.post(url, headers=headers, json=params, timeout=self.timeout)
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('retCode') != 0:
                raise Exception(f"Bybit API error: {data.get('retMsg', 'Unknown error')}")
            
            return data.get('result', {})
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def _get_cached(self, key: str, func, *args, **kwargs):
        """Cache results for TTL seconds"""
        now = time.time()
        if key in self._cache:
            cached_time, cached_data = self._cache[key]
            if now - cached_time < self._cache_ttl:
                return cached_data
        
        result = func(*args, **kwargs)
        self._cache[key] = (now, result)
        return result
    
    def get_wallet_balance(self, account_type: str = 'UNIFIED', coin: Optional[str] = None) -> Dict:
        """Get wallet balance"""
        params = {'accountType': account_type}
        if coin:
            params['coin'] = coin
        
        return self._request('GET', '/v5/account/wallet-balance', params)
    
    def get_positions(self, category: str = 'linear', symbol: Optional[str] = None, settle_coin: str = 'USDT') -> Dict:
        """Get open positions"""
        params = {'category': category, 'settleCoin': settle_coin}
        if symbol:
            params['symbol'] = symbol
        
        return self._request('GET', '/v5/position/list', params)
    
    def get_transaction_log(self, account_type: str = 'UNIFIED', limit: int = 50) -> Dict:
        """Get transaction log"""
        params = {
            'accountType': account_type,
            'limit': limit
        }
        
        return self._request('GET', '/v5/account/transaction-log', params)
    
    def get_tickers(self, category: str = 'spot', symbol: Optional[str] = None) -> Dict:
        """Get market tickers"""
        params = {'category': category}
        if symbol:
            params['symbol'] = symbol
        
        return self._request('GET', '/v5/market/tickers', params)


# Test function
if __name__ == '__main__':
    client = BybitClient()
    
    print("Testing Bybit API connection...")
    
    try:
        # Test wallet balance
        balance = client.get_wallet_balance()
        print("\n✅ Wallet Balance:")
        if 'list' in balance:
            for wallet in balance['list']:
                print(f"  Total Equity: ${wallet.get('totalEquity', 'N/A')}")
                print(f"  Wallet Balance: ${wallet.get('totalWalletBalance', 'N/A')}")
                print(f"  Available Balance: ${wallet.get('totalAvailableBalance', 'N/A')}")
        
        # Test positions
        positions = client.get_positions()
        print("\n✅ Positions:")
        if 'list' in positions:
            for pos in positions['list']:
                print(f"  {pos.get('symbol', 'N/A')}: {pos.get('side', 'N/A')} {pos.get('size', '0')} @ ${pos.get('avgPrice', '0')}")
        
        print("\n✅ Bybit API connection successful!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
