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

A python script (`skills/plaud/scripts/plaud_monitor.py`) runs periodically via `jobs.json` (every 3 hours from 9:00 to 20:00 Tashkent time).

### Features

- **Working Hours Check**: Only runs between 9:00-20:00 Asia/Tashkent timezone
- **Audio Format Conversion**: Automatically converts opus to mp3 via pydub for better compatibility
- **Audio Chunking**: Splits long recordings (>25MB or >20min) into chunks for Groq free tier limits
- **Groq Whisper Transcription**: Multi-language support (ru/uz/en auto-detect)
- **Llama 3 Analysis**: Extracts summary and action items from transcripts
- **Vikunja Integration**: Automatically creates tasks from action items
- **Obsidian Notes**: Saves formatted notes with summary, tasks, and collapsible transcript
- **Native Plaud Links**: Captures and appends Plaud app links when available
- **Plaud Transcription Check**: Detects and adds Plaud's native transcription for comparison

### Cron Schedule

```json
{
  "schedule": {
    "kind": "cron",
    "expr": "0 9-20/3 * * *",
    "tz": "Asia/Tashkent"
  }
}
```

Runs at: 9:00, 12:00, 15:00, 18:00 (Tashkent time)

### Groq Free Tier Limits

The monitor automatically handles Groq's free tier limits:
- Max file size: 25MB
- Max duration: ~20 minutes (1200 seconds)

If audio exceeds these limits, it's automatically split into chunks and transcribed sequentially.

### Important: Device Sync Required

**The Plaud API returns encrypted audio for recordings that haven't been synced to the cloud.**

Before a recording can be processed:
1. Open the Plaud mobile app
2. Sync/pull the recording from your Plaud device
3. Once synced, the API will return the actual audio file

The script will detect encrypted files and skip them with a warning message:
```
-> Warning: Audio may be encrypted (wait_pull=0). Device sync required.
-> Tip: Open Plaud app and sync the recording first.
```

## Usage examples

- "List my Plaud recordings"
- "Transcribe my last recording from Plaud"
- "Summarize the meeting recorded in Plaud"
- "What action items were discussed in recording <ID>?"
- "Расшифруй последнюю запись с Plaud"
- "Какие задачи обсудили на встрече? (запись plaud <ID>)"
