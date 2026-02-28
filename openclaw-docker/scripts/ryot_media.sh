#!/bin/bash
# ryot_media.sh — Ryot API wrapper for OpenClaw agents to manage Media Recommendations
#
# Usage:
#   ryot_media.sh recommend <MOVIE|SHOW|BOOK>
#   ryot_media.sh add <lot> <title> [description]
#   ryot_media.sh list <MOVIE|SHOW|BOOK> [UNFINISHED|ALL]

RYOT_URL="${RYOT_URL:-http://localhost:3014/backend/graphql}"
RYOT_TOKEN="${RYOT_TOKEN:-}"
CMD="${1:-}"

gql() {
  local query="$1"
  curl -s -X POST "$RYOT_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${RYOT_TOKEN}" \
    -d "{\"query\": $(echo "$query" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}" \
    2>/dev/null
}

if [ -z "$RYOT_TOKEN" ]; then
  echo "❌ Error: RYOT_TOKEN is empty."
  exit 1
fi

# ── Recommend ────────────────────────────────────────────────────────────────
if [ "$CMD" = "recommend" ]; then
  LOT="${2:-MOVIE}"
  
  # 1. Fetch unfinished items (Want to watch/read)
  QUERY="query {
    userMetadataList(input: { lot: ${LOT}, filter: { general: UNFINISHED } }) {
      response { items }
    }
  }"
  
  RESULT=$(gql "$QUERY")
  
  # Pick a random item ID
  RANDOM_ID=$(echo "$RESULT" | python3 -c "
import json, sys, random
d = json.load(sys.stdin)
items = (d.get('data') or {}).get('userMetadataList', {}).get('response', {}).get('items', [])
if not items:
    sys.exit(1)
print(random.choice(items))
" 2>/dev/null)

  if [ -z "$RANDOM_ID" ]; then
    echo "Ничего не найдено в списке 'Хочу посмотреть/почитать' для типа ${LOT}."
    echo "Добавьте что-то в список сначала!"
    exit 0
  fi

  # 2. Fetch metadata details for the random item
  DETAILS_QUERY="query {
    metadataDetails(metadataId: \"${RANDOM_ID}\") {
      response {
        title
        description
        genres { name }
        publishYear
      }
    }
  }"

  DETAILS_RESULT=$(gql "$DETAILS_QUERY")

  echo "$DETAILS_RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
resp = (d.get('data') or {}).get('metadataDetails', {}).get('response', {})
if not resp:
    print('Ошибка получения данных.')
    sys.exit(1)

title = resp.get('title', 'Unknown')
desc = resp.get('description') or 'Нет описания.'
year = resp.get('publishYear') or '?'
genres = ', '.join([g.get('name', '') for g in resp.get('genres', [])])

print(f'🎬 Рекомендую: {title} ({year})')
if genres:
    print(f'🎭 Жанры: {genres}')
print(f'📖 Описание: {desc[:300]}...')
print(f'⭐ Из твоего списка Хочу посмотреть/почитать ({LOT})')
"
  exit 0
fi

# ── Add (Custom Metadata) ────────────────────────────────────────────────────
if [ "$CMD" = "add" ]; then
  LOT="${2:-MOVIE}"
  TITLE="${3:-}"
  DESC="${4:-}"
  
  if [ -z "$TITLE" ]; then
    echo "Usage: ryot_media.sh add <MOVIE|SHOW|BOOK> <\"Title\"> [\"Description\"]"
    exit 1
  fi

  # Create a custom metadata entry and optionally mark it as partial (unfinished/want to watch)
  QUERY="mutation {
    createCustomMetadata(input: {
      lot: ${LOT}
      title: \"${TITLE}\"
      description: \"${DESC}\"
      assets: { s3Images: [], s3Videos: [], remoteImages: [], remoteVideos: [] }
    }) { id }
  }"

  # Ryot automatically tracks custom metadata when created, but let's just create it.
  # The user can manage lists from UI. 
  RESULT=$(gql "$QUERY")
  
  echo "DEBUG_RAW: $RESULT"
  
  echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
resp = (d.get('data') or {}).get('createCustomMetadata', {})
if resp and resp.get('id'):
    print(f'✅ Успешно добавлено: \"${TITLE}\" (${LOT})')
else:
    errs = d.get('errors', [{}])
    msg = errs[0].get('message', str(d))
    if msg == 'NO_USER_ID':
        print(f'❌ Ошибка: API Key не поддерживает добавление кастомных медиа.')
        print('Используйте Web UI или auth-cookie для добавления.')
    else:
        print(f'❌ Ошибка добавления: {msg}')
"
  exit 0
fi

# ── List ─────────────────────────────────────────────────────────────────────
if [ "$CMD" = "list" ]; then
  LOT="${2:-MOVIE}"
  STATUS="${3:-UNFINISHED}"

  QUERY="query {
    userMetadataList(input: { lot: ${LOT}, filter: { general: ${STATUS} } }) {
      response { items }
    }
  }"
  
  RESULT=$(gql "$QUERY")
  IDS=$(echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
items = (d.get('data') or {}).get('userMetadataList', {}).get('response', {}).get('items', [])
print(' '.join(items[:10]))
" 2>/dev/null)

  if [ -z "$IDS" ]; then
    echo "Список пуст."
    exit 0
  fi

  echo "Твои сохраненные объекты (до 10 шт):"
  for ID in $IDS; do
    DETAILS_QUERY="query { metadataDetails(metadataId: \"${ID}\") { response { title publishYear } } }"
    gql "$DETAILS_QUERY" | python3 -c "
import json, sys
d = json.load(sys.stdin)
resp = d.get('data',{}).get('metadataDetails',{}).get('response',{})
if resp:
    print(f'- {resp.get(\"title\")} ({resp.get(\"publishYear\")})')
"
  done
  exit 0
fi

echo "Ryot Media Recommender v1.0"
echo "Usage:"
echo "  ryot_media.sh recommend <MOVIE|SHOW|BOOK>"
echo "  ryot_media.sh add <MOVIE|SHOW|BOOK> <title> [description]"
echo "  ryot_media.sh list <MOVIE|SHOW|BOOK> [UNFINISHED|ALL]"
