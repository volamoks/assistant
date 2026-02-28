#!/usr/bin/env python3
"""
Bybit Integration for PFM
Fetches wallet balance and trade history from Bybit API
"""

import os
import json
import hashlib
import hmac
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configuration
BYBIT_API_KEY = os.getenv("BYBIT_API", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
BYBIT_BASE_URL = "https://api.bybit.com"

# For testing - set to True to see raw responses
DEBUG = os.getenv("BYBIT_DEBUG", "false").lower() == "true"

# Default recv_window for API requests
RECV_WINDOW = "5000"


def generate_signature(secret: str, timestamp: str, method: str, path: str, body: str = "") -> str:
    """Generate Bybit API signature"""
    message = timestamp + method + path + body
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def make_request(method: str, endpoint: str, params: Dict = None) -> Dict:
    """Make authenticated request to Bybit API"""
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        return {"error": "Missing BYBIT_API or BYBIT_API_SECRET"}
    
    url = BYBIT_BASE_URL + endpoint
    timestamp = str(int(time.time() * 1000))
    
    # Build query string for GET or body for POST
    if params:
        # Sort params alphabetically
        sorted_params = sorted(params.items())
        param_str = "&".join([f"{k}={v}" for k, v in sorted_params])
    else:
        param_str = ""
    
    # For v5 API, signature includes timestamp, method, path, and sorted params
    signature_params = timestamp + BYBIT_API_KEY + RECV_WINDOW + param_str
    
    signature = hmac.new(
        BYBIT_API_SECRET.encode('utf-8'),
        signature_params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-SIGN": signature,
        "X-BAPI-SIGN-TYPE": "2",
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": RECV_WINDOW,
        "Content-Type": "application/json"
    }
    
    if DEBUG:
        print(f"[DEBUG] {method} {url}")
        print(f"[DEBUG] Params: {params}")
        print(f"[DEBUG] Signature string: {signature_params}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=param_str, timeout=10)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        if DEBUG:
            print(f"[DEBUG] Response: {response.status_code}")
            print(f"[DEBUG] {response.text[:500]}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_wallet_balance(account_type: str = "UNIFIED") -> Dict:
    """
    Get wallet balance from Bybit
    account_type: UNIFIED (spot + derivatives), SPOT, CONTRACT
    """
    endpoint = "/v5/account/wallet-balance"
    params = {
        "accountType": account_type
    }
    
    result = make_request("GET", endpoint, params)
    
    if "error" in result:
        return result
    
    # Parse the response
    if result.get("retCode") == 0:
        list_data = result.get("result", {}).get("list", [])
        if list_data:
            return {
                "success": True,
                "data": list_data[0],
                "raw": result
            }
    
    return {"error": result.get("retMsg", "Unknown error")}


def get_coin_balance(coin: str = None) -> Dict:
    """Get balance for specific coin or all coins"""
    wallet = get_wallet_balance()
    
    if "error" in wallet:
        return wallet
    
    all_coins = wallet.get("data", {}).get("coin", [])
    
    if coin:
        for c in all_coins:
            if c.get("coin") == coin.upper():
                return {
                    "success": True,
                    "coin": c.get("coin"),
                    "available": c.get("availableToWithdraw", "0"),
                    "locked": c.get("locked", "0"),
                    "total": c.get("walletBalance", "0"),
                    "usd_value": c.get("usdValue", "0")
                }
        return {"error": f"Coin {coin} not found"}
    
    # Return all coins
    coins = []
    for c in all_coins:
        total = float(c.get("walletBalance", "0"))
        if total > 0:
            coins.append({
                "coin": c.get("coin"),
                "available": c.get("availableToWithdraw", "0"),
                "locked": c.get("locked", "0"),
                "total": c.get("walletBalance", "0"),
                "usd_value": c.get("usdValue", "0")
            })
    
    return {"success": True, "coins": coins}


def get_trade_history(
    category: str = "spot",
    symbol: str = None,
    days: int = 7,
    limit: int = 100
) -> Dict:
    """
    Get trade history from Bybit
    category: spot, linear, inverse
    """
    endpoint = "/v5/execution/list"
    
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    params = {
        "category": category,
        "startTime": start_time,
        "limit": limit
    }
    
    if symbol:
        params["symbol"] = symbol
    
    result = make_request("GET", endpoint, params)
    
    if "error" in result:
        return result
    
    if result.get("retCode") == 0:
        return {
            "success": True,
            "trades": result.get("result", {}).get("list", []),
            "raw": result
        }
    
    return {"error": result.get("retMsg", "Unknown error")}


def get_positions(category: str = "linear") -> Dict:
    """
    Get open positions
    category: linear, inverse
    """
    endpoint = "/v5/position/closed-pnl"
    
    # Get last 7 days
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    
    params = {
        "category": category,
        "startTime": start_time,
        "endTime": end_time,
        "limit": 100
    }
    
    result = make_request("GET", endpoint, params)
    
    if "error" in result:
        return result
    
    if result.get("retCode") == 0:
        return {
            "success": True,
            "positions": result.get("result", {}).get("list", []),
            "raw": result
        }
    
    return {"error": result.get("retMsg", "Unknown error")}


def get_unified_positions() -> Dict:
    """Get unified account positions (includes spot, linear, options)"""
    endpoint = "/v5/position/closed-pnl"
    
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    
    params = {
        "category": "unified",
        "startTime": start_time,
        "endTime": end_time,
        "limit": 100
    }
    
    result = make_request("GET", endpoint, params)
    
    if "error" in result:
        return result
    
    if result.get("retCode") == 0:
        return {
            "success": True,
            "positions": result.get("result", {}).get("list", []),
            "raw": result
        }
    
    return {"error": result.get("retMsg", "Unknown error")}


def format_balance_output() -> str:
    """Format balance for display"""
    balance = get_coin_balance()
    
    if "error" in balance:
        return f"❌ Error: {balance['error']}"
    
    if "coins" not in balance:
        # Single coin
        return f"""
💰 Bybit Balance ({balance.get('coin')}):
   Available: {balance.get('available')}
   Locked: {balance.get('locked')}
   Total: {balance.get('total')}
   USD: ${balance.get('usd_value')}
"""
    
    # All coins
    output = "💰 Bybit Wallet Balance:\n"
    total_usd = 0
    
    for coin in sorted(balance["coins"], key=lambda x: float(x.get("usd_value", "0")), reverse=True):
        usd = float(coin.get("usd_value", "0"))
        total_usd += usd
        output += f"   {coin['coin']}: {coin['total']} (${usd:.2f})\n"
    
    output += f"\n   💵 Total: ${total_usd:.2f}"
    
    return output


def format_trades_output(days: int = 7) -> str:
    """Format recent trades for display"""
    trades = get_trade_history(days=days)
    
    if "error" in trades:
        return f"❌ Error: {trades['error']}"
    
    trade_list = trades.get("trades", [])
    
    if not trade_list:
        return f"📊 No trades in last {days} days"
    
    output = f"📊 Bybit Trades (last {days} days):\n"
    
    # Group by symbol
    by_symbol = {}
    for t in trade_list:
        sym = t.get("symbol", "UNKNOWN")
        if sym not in by_symbol:
            by_symbol[sym] = []
        by_symbol[sym].append(t)
    
    for sym, sym_trades in list(by_symbol.items())[:5]:  # Top 5 symbols
        total_volume = sum(float(t.get("execValue", "0")) for t in sym_trades)
        output += f"\n   {sym}: {len(sym_trades)} trades, ${total_volume:.2f} volume"
    
    return output


def sync_to_actual() -> Dict:
    """
    Sync Bybit balance to Actual Budget as an account
    This would create/update a Bybit account in Actual Budget
    """
    balance = get_coin_balance()
    
    if "error" in balance:
        return balance
    
    # This would need actualpy integration to create transactions
    # For now, just return the balance data
    return {
        "success": True,
        "message": "Balance fetched - integrate with Actual Budget here",
        "balance": balance
    }


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bybit PFM Integration")
    parser.add_argument("command", choices=["balance", "trades", "positions", "sync"], 
                       help="Command to execute")
    parser.add_argument("--coin", "-c", help="Specific coin to query")
    parser.add_argument("--days", "-d", type=int, default=7, help="Days of history")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.command == "balance":
        if args.coin:
            result = get_coin_balance(args.coin)
        else:
            result = get_coin_balance()
    
    elif args.command == "trades":
        result = get_trade_history(days=args.days)
    
    elif args.command == "positions":
        result = get_unified_positions()
    
    elif args.command == "sync":
        result = sync_to_actual()
    
    else:
        result = {"error": "Unknown command"}
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.command == "balance":
            print(format_balance_output())
        elif args.command == "trades":
            print(format_trades_output(args.days))
        elif args.command == "positions":
            if "error" in result:
                print(f"❌ {result['error']}")
            else:
                positions = result.get("positions", [])
                print(f"📊 Positions (last 30 days): {len(positions)} closed")
        else:
            print(result)


if __name__ == "__main__":
    main()
