---
name: ryot
description: "Log workouts, body weight, and view fitness progress via Ryot (self-hosted life tracker). Use this for any fitness, gym, exercise, or body measurement tracking."
triggers:
  - log workout
  - bench press
  - gym session
  - log weight
  - body weight
  - workout progress
  - fitness progress
  - exercise history
  - "/workout"
  - "/progress"
  - "/log_weight"
---

# Ryot Fitness Tracker

Self-hosted life tracker at `http://ryot:8000`.
Script: `bash /data/bot/openclaw-docker/scripts/ryot.sh`

## Find exercise ID first (IMPORTANT)

Exercise IDs are specific strings (not always the common name).
**Always search before logging:**

```bash
bash /data/bot/openclaw-docker/scripts/ryot.sh exercises "bench"
# Output shows ID (for use in log_workout) and name
```

## Log a workout set

```bash
bash /data/bot/openclaw-docker/scripts/ryot.sh log_workout "<exercise_id>" <weight_kg> <sets> <reps> ["optional note"]

# Examples:
bash /data/bot/openclaw-docker/scripts/ryot.sh log_workout "BenchPress" 80 4 10
bash /data/bot/openclaw-docker/scripts/ryot.sh log_workout "Deadlift" 120 1 5 "new PR!"
```

## Log body weight

```bash
bash /data/bot/openclaw-docker/scripts/ryot.sh log_weight 82.5
```

## View recent workouts

```bash
bash /data/bot/openclaw-docker/scripts/ryot.sh recent 7   # last 7 days
bash /data/bot/openclaw-docker/scripts/ryot.sh recent 30  # last 30 days
```

## View progress for an exercise

```bash
bash /data/bot/openclaw-docker/scripts/ryot.sh progress "Bench Press" 30  # 30 days
bash /data/bot/openclaw-docker/scripts/ryot.sh progress "Deadlift" 90     # 3 months
```

## Check API status

```bash
bash /data/bot/openclaw-docker/scripts/ryot.sh status
```

## Parsing natural language

When user says things like:
- `"Сегодня жал 80кг 4 подхода по 10"` → log_workout Bench Press 80 4 10
- `"Становая 120кг на 5"` → search "deadlift" → log_workout
- `"Вес 82.5"` → log_weight 82.5
- `"Покажи прогресс по жиму за месяц"` → progress "Bench Press" 30

**Always use the EXACT exercise ID from the exercises search result.**

## Environment

- `RYOT_URL` — default: `http://ryot:8000/backend/graphql`
- `RYOT_TOKEN` — session cookie (if auth required, get from login)
