#!/bin/bash
# Bybit PFM - Quick balance check
# Usage: ./bybit.sh [command]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load env vars from project .env
set -a
source ../openclaw-docker/.env 2>/dev/null || true
set +a

case "${1:-balance}" in
  balance)
    python3 bybit_client.py balance
    ;;
  balance-json)
    python3 bybit_client.py balance --json
    ;;
  trades)
    python3 bybit_client.py trades --days "${2:-7}"
    ;;
  positions)
    python3 bybit_client.py positions
    ;;
  help|--help|-h)
    echo "Usage: ./bybit.sh [command]"
    echo ""
    echo "Commands:"
    echo "  balance           Show wallet balance (default)"
    echo "  balance-json      Show balance as JSON"
    echo "  trades [days]     Show trade history (default 7 days)"
    echo "  positions         Show closed positions"
    echo ""
    echo "Examples:"
    echo "  ./bybit.sh balance"
    echo "  ./bybit.sh balance --coin ETH"
    echo "  ./bybit.sh trades 30"
    ;;
  *)
    python3 bybit_client.py "$@"
    ;;
esac
