---
name: plaud
description: "Sync, transcribe and analyze recordings from Plaud Note voice recorder. Lists recordings, downloads audio, transcribes via Whisper (Groq), and analyzes the transcript."
triggers:
  - plaud
  - plaud recordings
  - list recordings
  - plaud transcript
  - transcribe plaud
  - расшифровать запись
  - запись plaud
  - расшифровка plaud
  - analyze recording
  - анализ записи
---

# Plaud Skill

Sync and analyze recordings from Plaud Note devices.

## Typical workflow

### 1. List recordings

```bash
bash /data/bot/openclaw-docker/skills/plaud/plaud.sh list
```

Shows: ID, title, date. Ask the user which recording to process if not specified.

### 2a. Transcribe via Whisper (recommended)

Downloads audio + transcribes with Groq `whisper-large-v3`. Supports ru/uz/en, auto-detects language.

```bash
bash /data/bot/openclaw-docker/skills/plaud/plaud.sh transcribe <FILE_ID>
```

Output: prints full transcript to stdout. Optionally save to file:

```bash
bash /data/bot/openclaw-docker/skills/plaud/plaud.sh transcribe <FILE_ID> /tmp/transcript.txt
```

### 2b. Get Plaud built-in summary (alternative)

Uses Plaud's own AI — faster but lower quality, no ru/uz language control.

```bash
bash /data/bot/openclaw-docker/skills/plaud/plaud.sh summary <FILE_ID>
```

### 3. Analyze transcript

After getting the transcript text, analyze it based on what the user asked:
- Summarize key points
- Extract action items / tasks
- Identify decisions made
- Answer specific questions about the content
- Translate to another language
- Structure into sections

Always present the analysis in the language the user is communicating in.

## Download audio only

```bash
bash /data/bot/openclaw-docker/skills/plaud/plaud.sh download <FILE_ID> /tmp/recording.mp3
```

## Configuration

Required environment variables (set in `.env`):
- `PLAUD_TOKEN` — Plaud.ai auth token
- `PLAUD_API_DOMAIN` — API endpoint (e.g. `https://api-euc1.plaud.ai`)
- `GROQ_API_KEY` — for Whisper transcription

## Auto-Monitoring (Cron)

A python script (`skills/plaud/scripts/plaud_monitor.py`) runs periodically via `jobs.json` (every 3 hours from 9:00 to 20:00).
It automatically checks for new recordings, processes them through Groq Whisper and Llama 3 for translation/summarization tasks, and saves notes to your Obsidian `Inbox`. It'll also capture native Plaud links if they become available.

## Usage examples

- "List my Plaud recordings"
- "Transcribe my last recording from Plaud"
- "Summarize the meeting recorded in Plaud"
- "What action items were discussed in recording <ID>?"
- "Расшифруй последнюю запись с Plaud"
- "Какие задачи обсудили на встрече? (запись plaud <ID>)"
