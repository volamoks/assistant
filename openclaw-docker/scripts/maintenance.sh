#!/bin/bash
# maintenance.sh — включить/выключить maintenance mode для watchdog
# Usage:
#   ./maintenance.sh on         — включить (watchdog молчит)
#   ./maintenance.sh off        — выключить
#   ./maintenance.sh restart    — on + docker compose restart + off
#
# Также: при docker compose up/down внутри контейнера используй:
#   touch /tmp/openclaw-maintenance.lock
#   ... деплой ...
#   rm /tmp/openclaw-maintenance.lock

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
export DOCKER_HOST="unix:///Users/abror_mac_mini/.orbstack/run/docker.sock"

LOCK="/tmp/openclaw-maintenance.lock"
PROJECT_DIR="/Users/abror_mac_mini/Projects/bot/openclaw-docker"

case "$1" in
  on)
    touch "$LOCK"
    echo "✅ Maintenance ON — watchdog заглушен"
    ;;
  off)
    rm -f "$LOCK"
    echo "✅ Maintenance OFF — watchdog активен"
    ;;
  restart)
    touch "$LOCK"
    echo "🔧 Maintenance ON — перезапускаем openclaw..."
    cd "$PROJECT_DIR"
    docker compose up -d --no-deps openclaw
    sleep 5
    rm -f "$LOCK"
    echo "✅ Maintenance OFF — watchdog активен"
    ;;
  status)
    if [ -f "$LOCK" ]; then
      echo "🔧 Maintenance: ON (watchdog заглушен)"
    else
      echo "✅ Maintenance: OFF (watchdog активен)"
    fi
    ;;
  *)
    echo "Usage: $0 {on|off|restart|status}"
    exit 1
    ;;
esac
