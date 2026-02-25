#!/bin/bash
# copy_chat_db.sh — копирует chat.db в /tmp ТОЛЬКО если он изменился
# Запускать из Terminal (у него есть Full Disk Access)
#
# Usage:
#   ./copy_chat_db.sh          # бесконечный цикл
#   ./copy_chat_db.sh --once   # однократное копирование

SRC="$HOME/Library/Messages/chat.db"
DST="/tmp/chat_sms_copy.db"
INTERVAL=300  # проверяем раз в 5 минут

copy_if_changed() {
    # Пропускаем если DST свежее SRC
    if [ -f "$DST" ] && [ "$DST" -nt "$SRC" ]; then
        return 0  # уже актуально
    fi
    if cp "$SRC" "$DST" 2>/dev/null; then
        echo "[$(date '+%H:%M:%S')] Copied chat.db → $DST"
    else
        echo "[$(date '+%H:%M:%S')] ❌ Failed (FDA needed?)"
    fi
}

if [ "$1" = "--once" ]; then
    copy_if_changed
    exit 0
fi

echo "📋 chat.db watcher started (checks every ${INTERVAL}s, copies only on change)"
while true; do
    copy_if_changed
    sleep "$INTERVAL"
done
