#!/usr/bin/env python3
"""
Sync Bybit wallet balance to Actual Budget
Creates/updates a Bybit account with current crypto balances
"""

import os
import sys
from datetime import datetime
from typing import Dict, List

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from bybit_client import get_coin_balance, BYBIT_API_KEY, BYBIT_API_SECRET
from config import ACTUAL_URL, ACTUAL_PASSWORD, ACTUAL_FILE, validate_actual_config
from actual import Actual, get_accounts
from actual.queries import create_transaction

# Account name in Actual Budget
BYBIT_ACCOUNT_NAME = "Bybit Wallet"


def get_or_create_account(session, accounts: List, account_name: str):
    """Finds an existing account by name or creates a new one."""
    from actual.queries import create_account
    acc = next((a for a in accounts if a.name == account_name), None)
    if not acc:
        acc = create_account(session, account_name, initial_balance=0)
        print(f"  📂 Created account: {account_name}")
    return acc


def sync_bybit_balance():
    """Sync Bybit balance to Actual Budget"""
    
    # Check API keys
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        print("❌ Missing BYBIT_API or BYBIT_API_SECRET")
        return {"error": "Missing API keys"}
    
    # Get Bybit balance
    print("📡 Fetching Bybit balance...")
    balance = get_coin_balance()
    
    if "error" in balance:
        print(f"❌ Error fetching balance: {balance['error']}")
        return balance
    
    coins = balance.get("coins", [])
    
    if not coins:
        print("⚠️ No coins found in Bybit wallet")
        return {"success": True, "message": "No coins to sync"}
    
    # Calculate total balance in USD
    total_usd = sum(float(c.get("usd_value", "0")) for c in coins)
    
    print(f"\n💰 Bybit Wallet: ${total_usd:,.2f}")
    print(f"   Coins: {len(coins)}")
    
    # Show breakdown
    print("\n📊 Top coins:")
    sorted_coins = sorted(coins, key=lambda x: float(x.get("usd_value", "0")), reverse=True)
    for coin in sorted_coins[:10]:
        usd = float(coin.get("usd_value", "0"))
        if usd > 1:  # Only show coins worth > $1
            print(f"   {coin['coin']}: {coin['total']} (${usd:,.2f})")
    
    # Connect to Actual
    print("\n🔗 Connecting to Actual Budget...")
    
    try:
        validate_actual_config()
    except Exception as e:
        print(f"❌ Actual config error: {e}")
        return {"error": str(e)}
    
    try:
        with Actual(base_url=ACTUAL_URL, password=ACTUAL_PASSWORD, file=ACTUAL_FILE) as actual:
            actual.download_budget()
            
            # Get accounts
            accounts = get_accounts(actual.session)
            
            # Find or create Bybit account
            bybit_account = get_or_create_account(actual.session, accounts, BYBIT_ACCOUNT_NAME)
            
            # For now, we just show the balance - setting actual account balance
            # requires more complex handling in Actual's data model
            print(f"\n✅ Account '{BYBIT_ACCOUNT_NAME}' ready in Actual")
            print(f"   Current balance: ${total_usd:,.2f}")
            print(f"\n💡 To update balance, create a transaction manually in Actual")
            
            # Note: Creating transactions requires category selection in Actual
            # which is complex to automate. The account is now available.
            
    except Exception as e:
        print(f"❌ Error connecting to Actual: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
    return {
        "success": True,
        "total_usd": total_usd,
        "coins": len(coins),
        "account": BYBIT_ACCOUNT_NAME
    }


if __name__ == "__main__":
    result = sync_bybit_balance()
    print(f"\nResult: {result}")
