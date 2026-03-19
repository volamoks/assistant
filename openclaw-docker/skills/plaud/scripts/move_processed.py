import json
import os
import shutil
from pathlib import Path

state_path = Path("/data/bot/openclaw-docker/data/plaud_state.json")
state = json.loads(state_path.read_text())

vault_root = Path("/data/abror_vault")
work_transcripts = vault_root / "Work" / "Transcripts"
calls_dir = work_transcripts / "Calls"
meetings_dir = work_transcripts / "Meetings"
ideas_dir = work_transcripts / "Ideas"
calls_dir.mkdir(parents=True, exist_ok=True)
meetings_dir.mkdir(parents=True, exist_ok=True)
ideas_dir.mkdir(parents=True, exist_ok=True)

inbox_dir = vault_root / "Inbox"

for file_id, info in state.items():
    if info.get("has_native_transcript"):
        old_path = Path(info["obsidian_file"])
        if not old_path.exists():
            print(f"File not found: {old_path}")
            continue
        # Determine type: we can guess from filename or content
        # For simplicity, we'll put all in Meetings except known call
        filename = old_path.name
        if "02-12" in filename or "a6f4f888" in filename:
            target_dir = calls_dir
        else:
            target_dir = meetings_dir
        new_path = target_dir / old_path.name
        try:
            shutil.move(str(old_path), str(new_path))
            info["obsidian_file"] = str(new_path)
            print(f"Moved {old_path.name} -> {new_path}")
        except Exception as e:
            print(f"Error moving {old_path}: {e}")

# Write back state
state_path.write_text(json.dumps(state, indent=2))
print("State updated.")
