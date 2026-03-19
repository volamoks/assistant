import os
from pathlib import Path
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
VAULT_ROOT = Path(os.getenv(
    "USER_VAULT_PATH",
    str(PROJECT_ROOT.parent / "obsidian/vault")
))
INBOX_DIR = VAULT_ROOT / "Inbox"
TRANSCRIPTS_DIR = VAULT_ROOT / "Transcripts"

def format_obsidian_note(file_id, filename, created_at, transcript, summary, native_links=None):
    dt = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M")
    
    note_content = f"""# Plaud: {filename}

## Metadata
- **Date**: {dt}
- **ID**: {file_id}
- **Source**: Plaud Note

## Summary & Tasks
{summary}

"""
    if native_links:
        note_content += "## Plaud App Links\n"
        for link in native_links:
            note_content += f"- [{link['data_title']}]({link['data_link']})\n"
        note_content += "\n"

    note_content += f"""## Full Transcript
<details>
<summary>Click to expand transcript</summary>

{transcript}

</details>
"""
    return note_content