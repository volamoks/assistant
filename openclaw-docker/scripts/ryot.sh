#!/bin/bash
# ryot.sh — Ryot API wrapper for OpenClaw agents
# Ryot is a self-hosted life tracker with GraphQL API
#
# Usage:
#   ryot.sh log_workout  "Bench Press" <weight_kg> <sets> <reps> [note]
#   ryot.sh log_weight   <weight_kg>
#   ryot.sh recent       [days=7]
#   ryot.sh progress     "<exercise_name>" [days=30]
#   ryot.sh exercises    [search_term]
#   ryot.sh status       -- check API health

RYOT_URL="${RYOT_URL:-http://ryot:8000/backend/graphql}"
RYOT_TOKEN="${RYOT_TOKEN:-}"
CMD="${1:-}"

# ── Auth header ─────────────────────────────────────────────────────────────
if [ -n "$RYOT_TOKEN" ]; then
  AUTH_HEADER="-H \"Cookie: auth-cookie=${RYOT_TOKEN}\""
else
  AUTH_HEADER=""
fi

gql() {
  local query="$1"
  curl -s -X POST "$RYOT_URL" \
    -H "Content-Type: application/json" \
    ${RYOT_TOKEN:+-H "Cookie: auth-cookie=${RYOT_TOKEN}"} \
    -d "{\"query\": $(echo "$query" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}" \
    2>/dev/null
}

# ── Status ──────────────────────────────────────────────────────────────────
if [ "$CMD" = "status" ]; then
  RESULT=$(gql "{ coreDetails { version } }")
  VERSION=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('coreDetails',{}).get('version','unknown'))" 2>/dev/null)
  echo "✅ Ryot API: $RYOT_URL | Version: $VERSION"
  exit 0
fi

# ── Log body weight ──────────────────────────────────────────────────────────
if [ "$CMD" = "log_weight" ]; then
  WEIGHT="${2:-}"
  DATE=$(date +%Y-%m-%d)
  if [ -z "$WEIGHT" ]; then echo "Usage: ryot.sh log_weight <kg>"; exit 1; fi

  QUERY="mutation {
    createOrUpdateUserMeasurement(input: {
      timestamp: \"${DATE}T12:00:00Z\"
      stats: { weight: ${WEIGHT} }
    })
  }"
  RESULT=$(gql "$QUERY")
  echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('data',{}).get('createOrUpdateUserMeasurement'):
    print(f'✅ Weight logged: ${WEIGHT} kg on ${DATE}')
else:
    print(f'❌ Error: {d}')
" 2>/dev/null
  exit 0
fi

# ── Log workout ──────────────────────────────────────────────────────────────
if [ "$CMD" = "log_workout" ]; then
  EXERCISE="${2:-}"
  WEIGHT="${3:-0}"
  SETS="${4:-1}"
  REPS="${5:-1}"
  NOTE="${6:-}"
  DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  if [ -z "$EXERCISE" ]; then
    echo "Usage: ryot.sh log_workout <exercise> <weight_kg> <sets> <reps> [note]"
    exit 1
  fi

  QUERY="mutation {
    createOrUpdateUserWorkout(input: {
      name: \"Quick log: ${EXERCISE}\"
      startTime: \"${DATE}\"
      endTime: \"${DATE}\"
      exercises: [{
        exerciseId: \"${EXERCISE}\"
        sets: [$(for i in $(seq 1 $SETS); do echo "{confirmedAt: \"${DATE}\", statistic: {weight: ${WEIGHT}, reps: ${REPS}}}$([ $i -lt $SETS ] && echo ',')"; done)]
        $([ -n "$NOTE" ] && echo "notes: [\"${NOTE}\"]")
      }]
    })
  }"

  RESULT=$(gql "$QUERY")
  echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if d.get('data',{}).get('createOrUpdateUserWorkout'):
    print(f'✅ Logged: $EXERCISE ${WEIGHT}kg × ${SETS}×${REPS}')
elif d.get('errors'):
    print(f'⚠️  Error: {d[\"errors\"][0][\"message\"]}')
    print('Tip: Use ryot.sh exercises to find the correct exercise ID')
else:
    print(f'Response: {d}')
" 2>/dev/null
  exit 0
fi

# ── List/search exercises ────────────────────────────────────────────────────
if [ "$CMD" = "exercises" ]; then
  SEARCH="${2:-}"
  QUERY="query {
    exercisesList(input: {
      search: { query: \"${SEARCH}\" }
    }) {
      items { id name lot muscles }
    }
  }"
  RESULT=$(gql "$QUERY")
  echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
items = d.get('data',{}).get('exercisesList',{}).get('items',[])
for ex in items[:20]:
    muscles = ', '.join(ex.get('muscles',[])[:2])
    print(f\"{ex['id']:<35} {ex['name']:<30} [{muscles}]\")
" 2>/dev/null
  exit 0
fi

# ── Recent workouts ──────────────────────────────────────────────────────────
if [ "$CMD" = "recent" ]; then
  DAYS="${2:-7}"
  FROM=$(date -d "$DAYS days ago" +%Y-%m-%d 2>/dev/null || date -v-${DAYS}d +%Y-%m-%d 2>/dev/null)
  QUERY="query {
    userWorkoutList(input: {
      startDate: \"${FROM}\"
    }) {
      items { id name startTime summary { total { duration weight } exercises { name bestSet { weight reps } } } }
    }
  }"
  RESULT=$(gql "$QUERY")
  echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
items = d.get('data',{}).get('userWorkoutList',{}).get('items',[])
if not items:
    print('No workouts in the last ${DAYS} days.')
    sys.exit()
print(f'Workouts (last ${DAYS} days):')
for w in items:
    date = w.get('startTime','')[:10]
    name = w.get('name','')
    exs = w.get('summary',{}).get('exercises',[])
    ex_list = ', '.join(e.get('name','') for e in exs[:4])
    total = w.get('summary',{}).get('total',{})
    kg = total.get('weight',0)
    dur = int(total.get('duration',0))
    print(f'  {date}  {name}: {ex_list} | {kg}kg total | {dur}min')
" 2>/dev/null
  exit 0
fi

# ── Progress for exercise ────────────────────────────────────────────────────
if [ "$CMD" = "progress" ]; then
  EXERCISE="${2:-}"
  DAYS="${3:-30}"
  FROM=$(date -d "$DAYS days ago" +%Y-%m-%d 2>/dev/null || date -v-${DAYS}d +%Y-%m-%d 2>/dev/null)

  if [ -z "$EXERCISE" ]; then
    echo "Usage: ryot.sh progress <exercise_name> [days=30]"
    exit 1
  fi

  QUERY="query {
    userWorkoutList(input: { startDate: \"${FROM}\" }) {
      items {
        startTime
        summary {
          exercises {
            name
            bestSet { weight reps }
          }
        }
      }
    }
  }"
  RESULT=$(gql "$QUERY")
  echo "$RESULT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
items = d.get('data',{}).get('userWorkoutList',{}).get('items',[])
rows = []
for w in items:
    date = w.get('startTime','')[:10]
    for ex in w.get('summary',{}).get('exercises',[]):
        if '${EXERCISE}'.lower() in ex.get('name','').lower():
            bs = ex.get('bestSet',{})
            w_kg = bs.get('weight',0)
            reps = bs.get('reps',0)
            rows.append((date, w_kg, reps))
if not rows:
    print(f'No data for \"${EXERCISE}\" in last ${DAYS} days')
else:
    print(f'Progress: ${EXERCISE} (last ${DAYS} days)')
    print(f'{\"Date\":<12} {\"Weight kg\":>10} {\"Reps\":>6}')
    print('-'*30)
    for r in sorted(rows):
        print(f'{r[0]:<12} {r[1]:>10.1f} {r[2]:>6}')
    if len(rows) >= 2:
        delta = rows[-1][1] - rows[0][1]
        print(f'\nDelta: {delta:+.1f}kg over ${DAYS} days')
" 2>/dev/null
  exit 0
fi

# ── Help ─────────────────────────────────────────────────────────────────────
echo "Ryot API wrapper v1.0"
echo "Usage:"
echo "  ryot.sh status"
echo "  ryot.sh exercises [search]"
echo "  ryot.sh log_workout <exercise_id> <kg> <sets> <reps> [note]"
echo "  ryot.sh log_weight <kg>"
echo "  ryot.sh recent [days=7]"
echo "  ryot.sh progress <exercise> [days=30]"
