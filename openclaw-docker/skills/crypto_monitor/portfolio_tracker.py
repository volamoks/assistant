#!/usr/bin/env python3
"""
Crypto Portfolio Tracker

Features:
- Portfolio tracking (holdings, average buy price)
- P&L calculation (realized/unrealized)
- DCA calculator
- Portfolio rebalancing recommendations
- Telegram bot commands integration
- Memory persistence
- Bybit API integration for automatic portfolio sync
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, '/home/node/.openclaw/skills')
sys.path.insert(0, '/home/node/.openclaw/skills/agent-memory')
sys.path.insert(0, '/home/node/.openclaw/skills/bybit_integration')

try:
    from agent_memory.memory import Memory
except ImportError:
    Memory = None

try:
    from bybit_memory import BybitWithMemory
    BYBIT_AVAILABLE = True
except ImportError:
    BYBIT_AVAILABLE = False


# File paths
PORTFOLIO_FILE = os.path.expanduser('~/.openclaw/skills/crypto_monitor/portfolio.json')
TRANSACTIONS_FILE = os.path.expanduser('~/.openclaw/skills/crypto_monitor/transactions.json')


@dataclass
class Holding:
    """Represents a crypto holding."""
    symbol: str
    amount: float
    average_buy_price: float
    last_updated: str


@dataclass
class Transaction:
    """Represents a buy/sell transaction."""
    symbol: str
    type: str  # 'buy' or 'sell'
    amount: float
    price: float
    total: float
    fee: float
    timestamp: str
    notes: str = ""


class PortfolioTracker:
    """Crypto portfolio tracker with P&L and DCA calculations."""
    
    def __init__(self):
        self.memory = Memory(collection="crypto_portfolio") if Memory else None
        self.bybit = BybitWithMemory() if BYBIT_AVAILABLE else None
        self.holdings: Dict[str, Holding] = {}
        self.transactions: List[Transaction] = []
        self.load_portfolio()
        self.load_transactions()
    
    def sync_from_bybit(self) -> Dict:
        """
        Sync portfolio from Bybit API.
        Fetches current positions and wallet balance, updates holdings.
        
        Returns:
            Dict with sync results
        """
        if not self.bybit:
            return {"error": "Bybit integration not available"}
        
        try:
            # Get portfolio from Bybit
            portfolio = self.bybit.get_portfolio_with_context()
            balance = portfolio.get('balance', {})
            positions = portfolio.get('positions', {})
            
            synced_holdings = {}
            total_equity = 0
            
            # Process wallet balance for spot holdings
            balance_list = balance.get('list', [])
            if balance_list:
                wallet_data = balance_list[0]
                total_equity = float(wallet_data.get('totalEquity', 0))
                
                # Get spot coins (non-zero balance)
                coins = wallet_data.get('coin', [])
                for coin_data in coins:
                    if isinstance(coin_data, dict):
                        symbol = coin_data.get('coin', '')
                        amount = float(coin_data.get('walletBalance', 0))
                        
                        if amount > 0 and symbol not in ['USDT', 'USD']:
                            # Fetch current price for average buy price estimation
                            current_price = self._fetch_spot_price(symbol)
                            
                            synced_holdings[symbol] = {
                                'amount': amount,
                                'average_buy_price': current_price,  # Use current price as fallback
                                'last_updated': datetime.now().isoformat()
                            }
            
            # Process derivatives positions
            positions_list = positions.get('list', [])
            for pos in positions_list:
                if isinstance(pos, dict):
                    symbol = pos.get('symbol', '').replace('USDT', '')
                    size = float(pos.get('size', 0))
                    avg_price = float(pos.get('avgPrice', 0))
                    side = pos.get('side', '')
                    
                    if size > 0:
                        # For positions, store entry price as average buy price
                        synced_holdings[symbol] = {
                            'amount': size if side == 'Buy' else -size,
                            'average_buy_price': avg_price,
                            'last_updated': datetime.now().isoformat()
                        }
            
            # Update holdings
            self.holdings = {
                k: Holding(**v) for k, v in synced_holdings.items()
            }
            self.save_portfolio()
            
            return {
                "success": True,
                "holdings_count": len(synced_holdings),
                "total_equity": total_equity,
                "holdings": synced_holdings
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _fetch_spot_price(self, symbol: str) -> float:
        """Fetch current spot price for a symbol."""
        try:
            url = 'https://api.bybit.com/v5/market/tickers'
            params = {'category': 'spot', 'symbol': f'{symbol}USDT'}
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('retCode') == 0 and data['result']['list']:
                return float(data['result']['list'][0]['lastPrice'])
        except Exception:
            pass
        return 0.0
    
    def load_portfolio(self):
        """Load portfolio from file."""
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE) as f:
                data = json.load(f)
                self.holdings = {
                    k: Holding(**v) for k, v in data.get('holdings', {}).items()
                }
    
    def save_portfolio(self):
        """Save portfolio to file."""
        os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
        data = {
            'holdings': {k: asdict(v) for k, v in self.holdings.items()},
            'last_updated': datetime.now().isoformat()
        }
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def load_transactions(self):
        """Load transactions from file."""
        if os.path.exists(TRANSACTIONS_FILE):
            with open(TRANSACTIONS_FILE) as f:
                data = json.load(f)
                self.transactions = [
                    Transaction(**t) for t in data.get('transactions', [])
                ]
    
    def save_transactions(self):
        """Save transactions to file."""
        os.makedirs(os.path.dirname(TRANSACTIONS_FILE), exist_ok=True)
        data = {
            'transactions': [asdict(t) for t in self.transactions],
            'last_updated': datetime.now().isoformat()
        }
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def add_transaction(self, symbol: str, tx_type: str, amount: float, 
                       price: float, fee: float = 0, notes: str = "") -> Transaction:
        """
        Add a buy/sell transaction and update holdings.
        
        Args:
            symbol: Asset symbol (e.g., 'BTC')
            tx_type: 'buy' or 'sell'
            amount: Amount of asset
            price: Price per asset in USDT
            fee: Transaction fee in USDT
            notes: Optional notes
        
        Returns:
            Created transaction
        """
        total = amount * price + fee if tx_type == 'buy' else amount * price - fee
        
        transaction = Transaction(
            symbol=symbol.upper(),
            type=tx_type.lower(),
            amount=amount,
            price=price,
            total=total,
            fee=fee,
            timestamp=datetime.now().isoformat(),
            notes=notes
        )
        
        self.transactions.append(transaction)
        self.save_transactions()
        
        # Update holdings
        self._update_holdings(transaction)
        
        return transaction
    
    def _update_holdings(self, tx: Transaction):
        """Update holdings based on transaction."""
        symbol = tx.symbol
        
        if tx.type == 'buy':
            if symbol in self.holdings:
                holding = self.holdings[symbol]
                # Calculate new average buy price
                total_cost = (holding.amount * holding.average_buy_price) + (tx.amount * tx.price) + tx.fee
                total_amount = holding.amount + tx.amount
                holding.average_buy_price = total_cost / total_amount if total_amount > 0 else 0
                holding.amount = total_amount
                holding.last_updated = datetime.now().isoformat()
            else:
                # New holding
                self.holdings[symbol] = Holding(
                    symbol=symbol,
                    amount=tx.amount,
                    average_buy_price=(tx.total / tx.amount) if tx.amount > 0 else 0,
                    last_updated=datetime.now().isoformat()
                )
        
        elif tx.type == 'sell':
            if symbol in self.holdings:
                holding = self.holdings[symbol]
                holding.amount -= tx.amount
                holding.last_updated = datetime.now().isoformat()
                
                # Remove holding if amount is zero or negative
                if holding.amount <= 0:
                    del self.holdings[symbol]
        
        self.save_portfolio()
    
    def get_current_prices(self, symbols: List[str] = None) -> Dict[str, float]:
        """
        Fetch current prices from Bybit.
        
        Args:
            symbols: List of symbols (default: all holdings)
        
        Returns:
            Dict of symbol -> current price
        """
        if symbols is None:
            symbols = list(self.holdings.keys())
        
        if not symbols:
            return {}
        
        prices = {}
        for symbol in symbols:
            usdt_symbol = f"{symbol}USDT"
            try:
                url = 'https://api.bybit.com/v5/market/tickers'
                params = {'category': 'spot', 'symbol': usdt_symbol}
                resp = requests.get(url, params=params, timeout=10)
                data = resp.json()
                
                if data.get('retCode') == 0 and data['result']['list']:
                    prices[symbol] = float(data['result']['list'][0]['lastPrice'])
            except Exception as e:
                print(f"Error fetching price for {symbol}: {e}")
                prices[symbol] = 0
        
        return prices
    
    def calculate_pnl(self) -> Dict:
        """
        Calculate P&L for all holdings.
        
        Returns:
            Dict with P&L data per holding and totals
        """
        prices = self.get_current_prices()
        result = {
            'holdings': [],
            'total_invested': 0,
            'total_current_value': 0,
            'total_pnl': 0,
            'total_pnl_pct': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        for symbol, holding in self.holdings.items():
            current_price = prices.get(symbol, 0)
            current_value = holding.amount * current_price
            invested = holding.amount * holding.average_buy_price
            pnl = current_value - invested
            pnl_pct = (pnl / invested * 100) if invested > 0 else 0
            
            holding_data = {
                'symbol': symbol,
                'amount': holding.amount,
                'avg_buy_price': holding.average_buy_price,
                'current_price': current_price,
                'invested': invested,
                'current_value': current_value,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'last_updated': holding.last_updated
            }
            
            result['holdings'].append(holding_data)
            result['total_invested'] += invested
            result['total_current_value'] += current_value
        
        result['total_pnl'] = result['total_current_value'] - result['total_invested']
        result['total_pnl_pct'] = (
            result['total_pnl'] / result['total_invested'] * 100 
            if result['total_invested'] > 0 else 0
        )
        
        return result
    
    def calculate_dca(self, symbol: str, target_amount: float, 
                     current_price: float, price_drop_pct: float = 5) -> Dict:
        """
        Calculate DCA (Dollar Cost Averaging) strategy.
        
        Args:
            symbol: Asset symbol
            target_amount: Total amount to invest (USDT)
            current_price: Current price
            price_drop_pct: Expected price drop percentage for each buy
        
        Returns:
            DCA plan with buy levels
        """
        # Get current holding
        holding = self.holdings.get(symbol.upper())
        current_amount = holding.amount if holding else 0
        avg_buy = holding.average_buy_price if holding else 0
        
        # Calculate buy levels (5 levels)
        levels = []
        remaining = target_amount
        
        for i in range(5):
            drop_pct = price_drop_pct * (i + 1)
            price_level = current_price * (1 - drop_pct / 100)
            
            # Allocate more to lower levels (pyramid strategy)
            if i == 0:
                allocation = target_amount * 0.15  # 15% at first level
            elif i == 1:
                allocation = target_amount * 0.20  # 20% at second level
            elif i == 2:
                allocation = target_amount * 0.25  # 25% at third level
            elif i == 3:
                allocation = target_amount * 0.25  # 25% at fourth level
            else:
                allocation = remaining  # Rest at fifth level
            
            allocation = min(allocation, remaining)
            remaining -= allocation
            
            levels.append({
                'level': i + 1,
                'price': round(price_level, 2),
                'drop_pct': drop_pct,
                'allocation_usdt': round(allocation, 2),
                'amount_to_buy': round(allocation / price_level, 6) if price_level > 0 else 0
            })
        
        # Calculate projected average after DCA
        total_new_amount = sum(l['amount_to_buy'] for l in levels)
        total_new_cost = target_amount
        
        if current_amount > 0:
            projected_avg = (
                (current_amount * avg_buy + total_new_cost) / 
                (current_amount + total_new_amount)
            ) if (current_amount + total_new_amount) > 0 else 0
        else:
            projected_avg = total_new_cost / total_new_amount if total_new_amount > 0 else 0
        
        return {
            'symbol': symbol.upper(),
            'current_price': current_price,
            'current_holding': current_amount,
            'current_avg_buy': avg_buy,
            'target_investment': target_amount,
            'levels': levels,
            'projected_avg_buy': round(projected_avg, 2),
            'total_new_amount': round(total_new_amount, 6)
        }
    
    def get_rebalancing_recommendations(self, target_allocation: Dict[str, float] = None) -> List[Dict]:
        """
        Get portfolio rebalancing recommendations.
        
        Args:
            target_allocation: Target allocation (symbol -> percentage)
                              Default: equal weight
        
        Returns:
            List of rebalancing recommendations
        """
        pnl_data = self.calculate_pnl()
        total_value = pnl_data['total_current_value']
        
        if total_value == 0:
            return []
        
        # Default: equal weight allocation
        if target_allocation is None:
            n_holdings = len(self.holdings)
            target_allocation = {
                symbol: 100 / n_holdings for symbol in self.holdings.keys()
            } if n_holdings > 0 else {}
        
        recommendations = []
        
        for holding_data in pnl_data['holdings']:
            symbol = holding_data['symbol']
            current_value = holding_data['current_value']
            current_pct = (current_value / total_value * 100) if total_value > 0 else 0
            target_pct = target_allocation.get(symbol, 0)
            
            diff_pct = target_pct - current_pct
            diff_value = total_value * diff_pct / 100
            
            if abs(diff_pct) > 5:  # Only recommend if difference > 5%
                action = 'BUY' if diff_pct > 0 else 'SELL'
                recommendations.append({
                    'symbol': symbol,
                    'action': action,
                    'current_pct': round(current_pct, 2),
                    'target_pct': round(target_pct, 2),
                    'diff_pct': round(diff_pct, 2),
                    'diff_value_usdt': round(diff_value, 2),
                    'current_value': round(current_value, 2)
                })
        
        # Sort by absolute difference (most urgent first)
        recommendations.sort(key=lambda x: abs(x['diff_pct']), reverse=True)
        
        return recommendations
    
    def get_portfolio_summary(self) -> str:
        """Get formatted portfolio summary."""
        pnl_data = self.calculate_pnl()
        
        lines = [
            "📊 *CRYPTO PORTFOLIO SUMMARY*",
            "=" * 40,
            f"💰 Total Invested: ${pnl_data['total_invested']:,.2f}",
            f"📈 Current Value: ${pnl_data['total_current_value']:,.2f}",
            f"📊 Total P&L: ${pnl_data['total_pnl']:+,.2f} ({pnl_data['total_pnl_pct']:+.2f}%)",
            "",
            "*Holdings:*"
        ]
        
        for holding in pnl_data['holdings']:
            emoji = "🟢" if holding['pnl'] >= 0 else "🔴"
            lines.append(
                f"{emoji} {holding['symbol']}: {holding['amount']:.6f} @ "
                f"${holding['current_price']:,.2f} | "
                f"P&L: ${holding['pnl']:+,.2f} ({holding['pnl_pct']:+.2f}%)"
            )
        
        return "\n".join(lines)


def main():
    """CLI for portfolio tracker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Crypto Portfolio Tracker")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add transaction
    add_parser = subparsers.add_parser('add', help='Add a transaction')
    add_parser.add_argument('symbol', help='Asset symbol (e.g., BTC)')
    add_parser.add_argument('type', choices=['buy', 'sell'], help='Transaction type')
    add_parser.add_argument('amount', type=float, help='Amount of asset')
    add_parser.add_argument('price', type=float, help='Price per asset in USDT')
    add_parser.add_argument('--fee', type=float, default=0, help='Transaction fee')
    add_parser.add_argument('--notes', default='', help='Optional notes')
    
    # Sync from Bybit
    subparsers.add_parser('sync', help='Sync portfolio from Bybit API')
    
    # Show portfolio
    subparsers.add_parser('show', help='Show portfolio summary')
    
    # Show P&L
    subparsers.add_parser('pnl', help='Show detailed P&L')
    
    # DCA calculator
    dca_parser = subparsers.add_parser('dca', help='Calculate DCA strategy')
    dca_parser.add_argument('symbol', help='Asset symbol')
    dca_parser.add_argument('amount', type=float, help='Total amount to invest (USDT)')
    dca_parser.add_argument('--drop', type=float, default=5, help='Price drop % per level')
    
    # Rebalance
    subparsers.add_parser('rebalance', help='Get rebalancing recommendations')
    
    # List transactions
    subparsers.add_parser('history', help='List transaction history')
    
    args = parser.parse_args()
    
    tracker = PortfolioTracker()
    
    if args.command == 'sync':
        if not BYBIT_AVAILABLE:
            print("❌ Bybit integration not available. Install bybit_memory.py")
            return
        
        result = tracker.sync_from_bybit()
        
        if "error" in result:
            print(f"❌ Sync failed: {result['error']}")
        else:
            print(f"✅ Synced {result['holdings_count']} holdings from Bybit")
            print(f"   Total Equity: ${result['total_equity']:,.2f}")
            for symbol, data in result['holdings'].items():
                print(f"   {symbol}: {data['amount']} @ ${data['average_buy_price']:,.2f}")
    
    if args.command == 'add':
        tx = tracker.add_transaction(
            args.symbol, args.type, args.amount, args.price, args.fee, args.notes
        )
        print(f"✅ Added {args.type.upper()} transaction:")
        print(f"   {tx.amount} {tx.symbol} @ ${tx.price:,.2f}")
        print(f"   Total: ${tx.total:,.2f} (fee: ${tx.fee:,.2f})")
    
    elif args.command == 'show':
        print(tracker.get_portfolio_summary())
    
    elif args.command == 'pnl':
        pnl_data = tracker.calculate_pnl()
        print(json.dumps(pnl_data, indent=2))
    
    elif args.command == 'dca':
        prices = tracker.get_current_prices([args.symbol])
        current_price = prices.get(args.symbol.upper(), 0)
        
        if current_price == 0:
            print(f"Error: Could not fetch price for {args.symbol}")
            return
        
        dca_plan = tracker.calculate_dca(args.symbol, args.amount, current_price, args.drop)
        
        print(f"📊 *DCA PLAN for {dca_plan['symbol']}*")
        print(f"Current Price: ${dca_plan['current_price']:,.2f}")
        print(f"Current Holding: {dca_plan['current_holding']}")
        print(f"Target Investment: ${dca_plan['target_investment']:,.2f}")
        print(f"Projected Avg Buy: ${dca_plan['projected_avg_buy']:,.2f}")
        print("")
        print("Buy Levels:")
        for level in dca_plan['levels']:
            print(f"  Level {level['level']}: ${level['price']:,.2f} "
                  f"(-{level['drop_pct']}%) → {level['amount_to_buy']} "
                  f"(alloc: ${level['allocation_usdt']:,.2f})")
    
    elif args.command == 'rebalance':
        recommendations = tracker.get_rebalancing_recommendations()
        
        if not recommendations:
            print("✅ Portfolio is well balanced!")
            return
        
        print("📊 *REBALANCING RECOMMENDATIONS*")
        for rec in recommendations:
            emoji = "🟢" if rec['action'] == 'BUY' else "🔴"
            print(f"{emoji} {rec['action']} {rec['symbol']}: "
                  f"{rec['current_pct']}% → {rec['target_pct']}% "
                  f"(${rec['diff_value_usdt']:+,.2f})")
    
    elif args.command == 'history':
        print("📜 *TRANSACTION HISTORY*")
        for tx in reversed(tracker.transactions[-10:]):  # Last 10 transactions
            emoji = "🟢" if tx.type == 'buy' else "🔴"
            print(f"{emoji} {tx.timestamp[:10]} | {tx.type.upper()} {tx.amount} "
                  f"{tx.symbol} @ ${tx.price:,.2f} = ${tx.total:,.2f}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
