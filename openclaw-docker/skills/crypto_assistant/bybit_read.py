#!/usr/bin/env python3
"""
Crypto Assistant - Bybit Data Provider
Provides portfolio data for AI-driven investment advice
"""

import os
import json
import sys
from datetime import datetime

# Add parent directory of 'skills' and current directory to path for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from bybit_integration.src.client import BybitClient
except ImportError:
    # Fallback to absolute path search
    likely_paths = [
        os.path.expanduser('~/.openclaw/skills'),
        '/data/bot/openclaw-docker/skills',
        os.path.expanduser('~/Projects/bot/openclaw-docker/skills')
    ]
    for p in likely_paths:
        if p not in sys.path and os.path.exists(p):
            sys.path.insert(0, p)
    try:
        from bybit_integration.src.client import BybitClient
    except ImportError:
        # If still failing, try one more relative level
        sys.path.insert(0, os.path.dirname(BASE_DIR))
        from bybit_integration.src.client import BybitClient


def get_portfolio_summary():
    """Get comprehensive portfolio data"""
    client = BybitClient()
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "balance": {},
        "positions": [],
        "analysis": {}
    }
    
    try:
        # Get wallet balance
        wallet = client.get_wallet_balance()
        if 'list' in wallet and wallet['list']:
            w = wallet['list'][0]
            result["balance"] = {
                "total_equity": float(w.get('totalEquity', 0)),
                "total_wallet_balance": float(w.get('totalWalletBalance', 0)),
                "total_available_balance": float(w.get('totalAvailableBalance', 0)),
                "coins": []
            }
            
            # Parse coins
            if 'coin' in w:
                for coin in w['coin']:
                    usd_value = float(coin.get('usdValue', 0))
                    if usd_value > 1:  # Only show meaningful holdings
                        avg_cost = coin.get('avgCostPrice', '')
                        unreal_pnl = coin.get('unrealisedPnl', '')
                        cum_real_pnl = coin.get('cumRealisedPnl', '')
                        result["balance"]["coins"].append({
                            "symbol": coin.get('coin', ''),
                            "wallet_balance": float(coin.get('walletBalance', 0)),
                            "usd_value": usd_value,
                            "avg_cost_price": float(avg_cost) if avg_cost else None,
                            "unrealised_pnl": float(unreal_pnl) if unreal_pnl else None,
                            "cum_realised_pnl": float(cum_real_pnl) if cum_real_pnl else None,
                        })
        
        # Get open positions
        positions = client.get_positions()
        if 'list' in positions:
            for pos in positions['list']:
                size = float(pos.get('size', 0))
                if size > 0:  # Only active positions
                    result["positions"].append({
                        "symbol": pos.get('symbol', ''),
                        "side": pos.get('side', ''),
                        "size": size,
                        "avg_price": float(pos.get('avgPrice', 0)),
                        "last_price": float(pos.get('lastPrice', 0)),
                        "unrealized_pnl": float(pos.get('unrealizedPnl', 0)),
                        "leverage": pos.get('leverage', '1')
                    })
        
        # Generate analysis summary
        coins = result["balance"]["coins"]
        if coins:
            total = sum(c["usd_value"] for c in coins)
            stablecoins = [c for c in coins if c["symbol"] in ["USDT", "USDC", "DAI"]]
            stables_value = sum(c["usd_value"] for c in stablecoins)
            
            result["analysis"] = {
                "total_portfolio_value": total,
                "stablecoins_percentage": (stables_value / total * 100) if total > 0 else 0,
                "stablecoins_value": stables_value,
                "allocation": {}
            }
            
            for coin in coins:
                pct = (coin["usd_value"] / total * 100) if total > 0 else 0
                result["analysis"]["allocation"][coin["symbol"]] = round(pct, 2)
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        return result


def get_market_overview():
    """Get market data for top assets"""
    client = BybitClient()
    
    result = {"tickers": [], "error": None}
    
    try:
        # Get BTC and major alts
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "TONUSDT"]
        
        for symbol in symbols:
            try:
                ticker = client.get_tickers(category="linear", symbol=symbol)
                if 'list' in ticker and ticker['list']:
                    t = ticker['list'][0]
                    result["tickers"].append({
                        "symbol": symbol,
                        "last_price": float(t.get('lastPrice', 0)),
                        "price_24h_change": float(t.get('price24hPcnt', 0)) * 100,
                        "volume_24h": float(t.get('volume24h', 0)),
                        "turnover_24h": float(t.get('turnover24h', 0))
                    })
            except:
                pass
                
    except Exception as e:
        result["error"] = str(e)
    
    return result


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Assistant Data Provider')
    parser.add_argument('--portfolio', action='store_true', help='Get portfolio summary')
    parser.add_argument('--market', action='store_true', help='Get market overview')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    if args.portfolio or (not args.market):
        data = get_portfolio_summary()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print("\n" + "="*50)
            print("💰 PORTFOLIO SUMMARY")
            print("="*50)
            print(f"Total Equity: ${data['balance'].get('total_equity', 0):,.2f}")
            print(f"Available: ${data['balance'].get('total_available_balance', 0):,.2f}")
            print(f"\nHoldings:")
            for coin in data['balance'].get('coins', []):
                pnl_str = ""
                if coin.get('unrealised_pnl') is not None:
                    pnl_str = f"  PnL: ${coin['unrealised_pnl']:+,.2f}"
                    if coin.get('avg_cost_price'):
                        pnl_str += f" (avg: ${coin['avg_cost_price']:,.4f})"
                print(f"  {coin['symbol']}: {coin['wallet_balance']:.4f} (${coin['usd_value']:,.2f}){pnl_str}")
            print(f"\nAllocation: {data['analysis'].get('allocation', {})}")
            print(f"Stablecoins: {data['analysis'].get('stablecoins_percentage', 0):.1f}%")
            
            if data.get('positions'):
                print(f"\nOpen Positions:")
                for pos in data['positions']:
                    print(f"  {pos['symbol']}: {pos['side']} {pos['size']} @ ${pos['avg_price']}")
                    print(f"    PnL: ${pos['unrealized_pnl']:+.2f}")
    
    if args.market:
        data = get_market_overview()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print("\n" + "="*50)
            print("📊 MARKET OVERVIEW")
            print("="*50)
            for t in data.get('tickers', []):
                change = t['price_24h_change']
                emoji = "🟢" if change > 0 else "🔴"
                print(f"{t['symbol']}: ${t['last_price']:,.2f} {emoji} {change:+.2f}%")
