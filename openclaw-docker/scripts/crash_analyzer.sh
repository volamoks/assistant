#!/bin/bash
# crash_analyzer.sh
# Гибридный анализатор: bash-проверка + LLM только при наличии crash-файлов
# Запускается из OpenClaw cron (агент вызывает bash-инструментом)

CRASH_DIR="/data/obsidian/vault/Bot/crash-configs"
LESSONS_FILE="/data/obsidian/vault/Bot/lessons-learned.md"
AGENT_ERRORS_FILE="/data/bot/openclaw-docker/workspace/.learnings/ERRORS.md"
OLLAMA_URL="${OLLAMA_URL:-http://host.docker.internal:11434/api/generate}"
OLLAMA_MODEL="${OLLAMA_MODEL:-deepseek-r1:1.5b}"
TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN}"
TELEGRAM_CHAT="${TELEGRAM_CHAT_ID:-6053956251}"  # Configurable via env var
TODAY=$(date '+%Y-%m-%d')

# --- Шаг 1: Быстрая проверка (нет LLM, нет ресурсов) ---
if [ ! -d "$CRASH_DIR" ]; then
  exit 0
fi

mapfile -t FILES < <(find "$CRASH_DIR" -name "*.md" -type f 2>/dev/null)

if [ ${#FILES[@]} -eq 0 ]; then
  exit 0
fi

# --- Шаг 2: Есть файлы — подключаем LLM ---
echo "Found ${#FILES[@]} crash file(s). Invoking LLM analysis..." >&2

# Убедимся, что папка для уроков агента существует
mkdir -p "$(dirname "$AGENT_ERRORS_FILE")"

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

  # Вызов Ollama напрямую (не через агента)
  RESPONSE=$(curl -s --max-time 30 -X POST "$OLLAMA_URL" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"$OLLAMA_MODEL\", \"prompt\": $(echo "$PROMPT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'), \"stream\": false}" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("response",""))' 2>/dev/null)

  # Если модель DeepSeek возвращает теги <think>, вырезаем их для чистоты лога
  CLEAN_RESPONSE=$(echo "$RESPONSE" | sed -e 's/<think>.*<\/think>//g' | sed '/^$/N;/^\n$/D')

  if [ -z "$CLEAN_RESPONSE" ]; then
    echo "LLM failed for $FILENAME, skipping" >&2
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

  # Telegram уведомление
  MSG="🔴 *Crash analyzed: ${FILENAME%.md}*%0A%0A$(echo "$RESPONSE" | head -4 | sed 's/[*#]//g' | python3 -c 'import sys; print("%0A".join(l.strip() for l in sys.stdin if l.strip()))')"

  curl -s --max-time 10 \
    "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT}&text=${MSG}&parse_mode=Markdown" \
    > /dev/null 2>&1

done

echo "Done. Processed ${#FILES[@]} crash file(s)."
