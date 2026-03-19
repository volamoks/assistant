---
name: plaud
description: "Sync, transcribe and analyze recordings from Plaud Note voice recorder. Lists recordings, downloads audio, transcribes via Groq Whisper, analyzes with LLM, saves notes + tasks to Obsidian vault."
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
  - обработай записи plaud
  - plaud monitor
---

# Plaud Skill

Full pipeline for syncing, transcribing and analyzing voice recordings from Plaud Note.

**Data destination:** Obsidian vault at `/data/obsidian/`  
**Tasks:** Obsidian Tasks plugin format (`- [ ]`) embedded in the note itself  
**No external task managers — everything stays local in Obsidian.**

---

## Architecture

```
Plaud API
  └─ list_files()         → [recording metadata]
       │
       ├─ download_audio() ───────────────────────┐
       │                                         ↓
       │  Groq Whisper (whisper-large-v3)   ← PRIMARY TRANSCRIPTION
       │   • Groq API → plain text          (always runs)
       │   • Handles: ru, uz, en (auto-detect)
       │   • Chunks long audio (>25MB / >20min)
       │
       ├─ get_native_transcript()           ← BONUS (if is_trans=True)
       │   • Plaud AI transcript from API
       │   • Appended to Obsidian note for comparison
       │
       └─ get_file_details().ai_content     ← BONUS (if is_summary=True)
            • Plaud AI summary from API
            • Appended to Obsidian note

Groq Whisper text
  └─ extract_summary_and_tasks()      ← LLM analysis (Groq Llama 3.3 70B)
       │  • Chunks long transcripts automatically
       │  • Returns: summary + action items (formatted as '- [ ] Task: desc')
       │
       └─ format_obsidian_note()       ← Obsidian Note + embedded tasks
            • Tasks parsed from LLM output → `- [ ]` checklist items with #tasks tag
            • Saved to /data/obsidian/Work/Transcripts/{Calls,Meetings,Ideas}/
```

---

## Usage Modes

### 1. Manual Mode (Voice Commands)

**Trigger phrases:**
- "List my Plaud recordings"
- "Transcribe my last recording from Plaud"
- "Расшифруй последнюю запись с Plaud"
- "Какие задачи обсудили на встрече? (запись plaud <ID>)"
- "Analyze recording `<ID>`"

**Manual pipeline:**
```bash
# Step 1 — list recordings
bash /data/bot/openclaw-docker/skills/plaud/plaud.sh list

# Step 2 — transcribe via Whisper (download + Groq Whisper)
bash /data/bot/openclaw-docker/skills/plaud/plaud.sh transcribe <FILE_ID> /tmp/transcript.txt

# The script chain: download → audio convert → WhisperSTT → Groq whisper-large-v3 → text
# Supports: ru, uz, en (auto-detect). Long files are auto-chunked.
```

**Get Plaud built-in summary (alternative):**
```bash
bash /data/bot/openclaw-docker/skills/plaud/plaud.sh summary <FILE_ID>
```
Uses Plaud's own AI — faster but lower quality, no ru/uz language control.

**Download audio only:**
```bash
bash /data/bot/openclaw-docker/skills/plaud/plaud.sh download <FILE_ID> /tmp/recording.mp3
```

---

### 2. Auto Mode (Cron — every 3 hours, 9:00–20:00 Tashkent)

**Schedule:** `0 9-20/3 * * *` (Asia/Tashkent) → runs at 09:00, 12:00, 15:00, 18:00

**Job definition** (`jobs.json`):
```json
{
  "schedule": {
    "kind": "cron",
    "expr": "0 9-20/3 * * *",
    "tz": "Asia/Tashkent"
  },
  "command": ["python3", "skills/plaud/scripts/plaud_monitor.py"]
}
```

**What the monitor does every run:**
1. Lists all recordings from Plaud API
2. Skips already-processed recordings (tracked in `plaud_state.json`)
3. For every new recording:
   - Downloads audio
   - **Transcribes via Groq Whisper** (primary — always, regardless of `is_trans`)
   - If `is_trans=True`: also fetches native Plaud transcript (bonus)
   - Analyzes with LLM (Groq Llama 3.3 70B) → summary + tasks
   - Parses task lines (`- [ ] ...`) from LLM output → embeds in note
   - Saves formatted note to `Work/Transcripts/{Calls,Meetings,Ideas}/`
4. Updates state file

**State file:** `/data/bot/openclaw-docker/data/plaud_state.json`

**Logs:** `/tmp/plaud_monitor.log` (also via healthcheck endpoint)

---

## Groq Free Tier Limits

| Limit | Value |
|-------|-------|
| Max file size | 25 MB |
| Max duration | ~20 minutes |

Monitor handles this automatically:
- Files >25MB or >20min → split into chunks → transcribe sequentially → concatenate
- Rate limit (429) → exponential backoff + Retry-After header respect

---

## Important: Device Sync Required

The Plaud API returns encrypted audio for recordings that haven't been synced to the cloud.

Before a recording can be processed:
1. Open the Plaud mobile app
2. Sync/pull the recording from your Plaud device
3. Once synced, the API will return the actual audio file

The script detects encrypted files and skips them:
```
Warning: Audio may be encrypted (wait_pull=0). Device sync required.
Tip: Open Plaud app and sync the recording first.
```

---

## Output Locations

| Output | Location |
|--------|----------|
| Obsidian notes | `/data/obsidian/Work/Transcripts/{Calls,Meetings,Ideas}/Plaud_YYYY-MM-DD_HHMM_<id>.md` |
| Tasks | Embedded in the note as `- [ ]` checklist items with `#tasks` tag |
| State | `/data/bot/openclaw-docker/data/plaud_state.json` |
| Logs | `/tmp/plaud_monitor.log` |

**Obsidian note structure:**
```markdown
# Plaud: <filename>

## Metadata
- Date: YYYY-MM-DD HH:MM
- ID: <file_id>
- Source: Plaud Note

## Summary
<LLM summary>

## Tasks
- [ ] Task description #tasks
- [ ] Another task: with details #tasks

## Native Plaud Transcript (bonus, N segments)  ← only if is_trans=True
<transcript text>

## Plaud AI Summary  ← only if available
<summary>

## Full Transcript
<details>
<summary>Click to expand</summary>
<transcribed text>
</details>
```

Tasks in the note are automatically picked up by the **Obsidian Tasks plugin** and appear in task queries, filters, and the calendar view.

---

## Configuration

Required environment variables (set in `.env` or container env):

| Variable | Description |
|----------|-------------|
| `PLAUD_TOKEN` | Plaud.ai auth token |
| `PLAUD_API_DOMAIN` | API endpoint (e.g. `https://api-euc1.plaud.ai`) |
| `GROQ_API_KEY` | Groq API key (for Whisper + LLM) |
| `USER_VAULT_PATH` | Obsidian vault root (default: `/data/obsidian`) |

Optional:
| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Send run summaries to Telegram |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications |

---

## Testing

```bash
# Dry run — list what would be processed
python3 /data/bot/openclaw-docker/skills/plaud/scripts/plaud_monitor.py --dry-run --limit 5 --log-level DEBUG

# Process only first 3 recordings
python3 /data/bot/openclaw-docker/skills/plaud/scripts/plaud_monitor.py --limit 3

# Check last run health
python3 /data/bot/openclaw-docker/skills/plaud/scripts/plaud_monitor.py --healthcheck

# Run manually (outside working hours, bypass hours check)
python3 /data/bot/openclaw-docker/skills/plaud/scripts/plaud_monitor.py --log-level INFO
```
