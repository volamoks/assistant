#!/bin/bash
# crash_analyzer.sh
# Гибридный анализатор: bash-проверка + LLM только при наличии crash-файлов
# Запускается из OpenClaw cron (агент вызывает bash-инструментом)

CRASH_DIR="${CRASH_DIR:-/data/obsidian/vault/Bot/crash-configs}"
LESSONS_FILE="${LESSONS_FILE:-/data/obsidian/vault/Bot/lessons-learned.md}"
AGENT_ERRORS_FILE="${AGENT_ERRORS_FILE:-/data/bot/openclaw-docker/workspace/.learnings/ERRORS.md}"
OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434/api/generate}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN}"
TELEGRAM_CHAT="${TELEGRAM_CHAT_ID:-6053956251}"  # Configurable via env var
TODAY=$(date '+%Y-%m-%d')

# --- Шаг 1: Быстрая проверка (нет LLM, нет ресурсов) ---
if [ ! -d "$CRASH_DIR" ]; then
  exit 0
fi

FILES=()
while IFS= read -r line; do
  FILES+=("$line")
done < <(find "$CRASH_DIR" -name "*.md" -type f 2>/dev/null)

if [ ${#FILES[@]} -eq 0 ]; then
  exit 0
fi

# --- Шаг 2: Есть файлы — подключаем LLM ---
echo "Found ${#FILES[@]} crash file(s). Invoking LLM analysis..." >&2

# --- Папка для логов/уроков ---
mkdir -p "$(dirname "$AGENT_ERRORS_FILE")"

FAILED_COUNT=0
PROCESSED_COUNT=0
TOTAL_FILES=${#FILES[@]}
for FILE in "${FILES[@]}"; do
  FILENAME=$(basename "$FILE")
  CONTENT=$(cat "$FILE" 2>/dev/null)

  if [ -z "$CONTENT" ]; then
    rm -f "$FILE"
    continue
  fi

  PROMPT="Analyze this crash/incident report and write ONE concise lesson in this EXACT format (no extra text):
## ${TODAY} — ${FILENAME%.md}
**What happened:** <one sentence>
**Root cause:** <one sentence>
**Rule:** <one actionable rule to prevent recurrence>

Crash report:
${CONTENT}"

  # Вызов Ollama напрямую через Python
  RESPONSE=$(python3 -c "
import json
import urllib.request
import urllib.error

payload = {
    'model': '$OLLAMA_MODEL',
    'prompt': '''$PROMPT''',
    'stream': False
}

try:
    req = urllib.request.Request(
        '$OLLAMA_URL',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
        print(data.get('response', ''))
except Exception as e:
    print('', end='')
" 2>/dev/null)

  # Если модель DeepSeek возвращает теги <think>, вырезаем их для чистоты лога
  CLEAN_RESPONSE=$(echo "$RESPONSE" | sed -e 's/<think>.*<\/think>//g' | sed '/^$/N;/^\n$/D')

  if [ -z "$CLEAN_RESPONSE" ]; then
    echo "LLM failed for $FILENAME, skipping" >&2
    FAILED_COUNT=$((FAILED_COUNT + 1))
    continue
  fi

  # Добавляем урок в lessons-learned.md (Obsidian)
  echo "" >> "$LESSONS_FILE"
  echo "$CLEAN_RESPONSE" >> "$LESSONS_FILE"
  echo "" >> "$LESSONS_FILE"

  # Дублируем урок в мозг агенту (Workspace)
  echo "" >> "$AGENT_ERRORS_FILE"
  echo "$CLEAN_RESPONSE" >> "$AGENT_ERRORS_FILE"
  echo "" >> "$AGENT_ERRORS_FILE"

  # Удаляем обработанный crash-файл
  rm -f "$FILE"
  echo "Processed and deleted: $FILENAME" >&2
  PROCESSED_COUNT=$((PROCESSED_COUNT + 1))

  # Telegram уведомление через Python
  MSG="🔴 *Crash analyzed: ${FILENAME%.md}*%0A%0A$(echo "$RESPONSE" | head -4 | sed 's/[*#]//g' | python3 -c 'import sys; print("%0A".join(l.strip() for l in sys.stdin if l.strip()))')"

  if ! python3 -c "
import urllib.request
url = 'https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage'
data = 'chat_id=${TELEGRAM_CHAT}&text=${MSG}&parse_mode=Markdown'
req = urllib.request.Request(url, data=data.encode(), headers={'Content-Type': 'application/x-www-form-urlencoded'})
urllib.request.urlopen(req, timeout=10)
" > /dev/null 2>&1; then
    echo "Telegram notification failed for $FILENAME" >&2
  fi

done

echo "Done. Processed $PROCESSED_COUNT/$TOTAL_FILES crash file(s)."

if [ "$FAILED_COUNT" -gt 0 ]; then
  echo "Errors encountered: $FAILED_COUNT files failed." >&2
  exit 1
fi

exit 0
