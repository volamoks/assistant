#!/usr/bin/env python3
"""Bybit CLI - Quick access to portfolio data"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from client import BybitClient

def format_balance(data):
    """Format wallet balance response"""
    output = []
    output.append("💰 **Баланс кошелька (UNIFIED)**\n")
    
    if 'list' in data:
        for wallet in data['list']:
            equity = wallet.get('totalEquity', '0')
            balance = wallet.get('totalWalletBalance', '0')
            available = wallet.get('totalAvailableBalance', '0')
            
            output.append(f"Общая эквити: **${float(equity):,.2f}**")
            output.append(f"Баланс кошелька: ${float(balance):,.2f}")
            output.append(f"Доступно: ${float(available):,.2f}\n")
            
            # Coins
            if 'coin' in wallet:
                coins = wallet['coin']
                if coins:
                    output.append("**Активы:**")
                    for coin in coins[:10]:  # Top 10
                        if float(coin.get('walletBalance', 0)) > 0:
                            output.append(f"• {coin['coin']}: {coin.get('walletBalance', '0')} (${float(coin.get('usdValue', 0)):,.2f})")
    
    return '\n'.join(output)

def format_positions(data):
    """Format positions response"""
    output = []
    output.append("📊 **Открытые позиции (Linear)**\n")
    
    if 'list' in data and data['list']:
        total_pnl = 0
        for pos in data['list']:
            symbol = pos.get('symbol', 'N/A')
            side = pos.get('side', 'N/A')
            size = pos.get('size', '0')
            avg_price = pos.get('avgPrice', '0')
            last_price = pos.get('lastPrice', '0')
            pnl = pos.get('unrealizedPnl', '0')
            margin = pos.get('margin', '0')
            
            side_emoji = "🟢" if side == "Buy" else "🔴"
            pnl_sign = "+" if float(pnl) >= 0 else ""
            total_pnl += float(pnl)
            
            output.append(f"{side_emoji} **{symbol}** ({side})")
            output.append(f"   Размер: {size} @ ${float(avg_price):,.2f}")
            output.append(f"   Текущая: ${float(last_price):,.2f}")
            output.append(f"   PnL: {pnl_sign}${float(pnl):,.2f} ({pnl_sign}{float(pnl)/float(margin)*100 if float(margin) > 0 else 0:.2f}%)")
            output.append(f"   Маржа: ${float(margin):,.2f}\n")
        
        total_sign = "+" if total_pnl >= 0 else ""
        output.append(f"**Всего PnL: {total_sign}${total_pnl:,.2f}**")
    else:
        output.append("Нет открытых позиций")
    
    return '\n'.join(output)

def format_transactions(data):
    """Format transaction log response"""
    output = []
    output.append("📜 **История транзакций (последние 10)**\n")
    
    if 'list' in data and data['list']:
        for tx in data['list'][:10]:
            tx_type = tx.get('type', 'N/A')
            amount = tx.get('amount', '0')
            coin = tx.get('coin', 'N/A')
            tx_time = tx.get('transactionTime', '0')
            status = tx.get('status', '')
            
            from datetime import datetime
            tx_date = datetime.fromtimestamp(int(tx_time) / 1000).strftime('%Y-%m-%d %H:%M')
            
            type_emoji = {
                'DEPOSIT': '✅',
                'WITHDRAW': '📤',
                'TRANSFER': '🔄',
                'TRADE': '💱',
                'FEE': '💸',
                'SETTLEMENT': '📋'
            }.get(tx_type, '📝')
            
            output.append(f"{type_emoji} **{tx_type}** {amount} {coin}")
            output.append(f"   {tx_date} | {status}\n")
    else:
        output.append("Нет транзакций")
    
    return '\n'.join(output)

def main():
    if len(sys.argv) < 2:
        print("Использование: bybit.py <balance|positions|transactions|portfolio>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    client = BybitClient()
    
    try:
        if command == 'balance':
            data = client.get_wallet_balance()
            print(format_balance(data))
        
        elif command == 'positions':
            data = client.get_positions()
            print(format_positions(data))
        
        elif command == 'transactions':
            data = client.get_transaction_log()
            print(format_transactions(data))
        
        elif command == 'portfolio':
            balance = client.get_wallet_balance()
            positions = client.get_positions()
            
            print("📈 **Портфель Bybit**\n")
            print(format_balance(balance))
            print("\n" + format_positions(positions))
        
        else:
            print(f"Неизвестная команда: {command}")
            print("Доступные: balance, positions, transactions, portfolio")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
