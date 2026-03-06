#!/usr/bin/env python3
"""
Plaud Monitor Script
Checks for new Plaud recordings, transcribes them via Groq Whisper,
summarizes using Groq Llama3, and saves the output to Obsidian.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
import subprocess

# Add workspace to path to import STT
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "workspace"))
try:
    from audio.stt import WhisperSTT
except ImportError:
    print("Error importing WhisperSTT. Ensure audio/stt.py exists.")
    sys.exit(1)

PLAUD_TOKEN = os.getenv("PLAUD_TOKEN")
PLAUD_API_DOMAIN = os.getenv("PLAUD_API_DOMAIN", "https://api-euc1.plaud.ai")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

DATA_DIR = PROJECT_ROOT / "data"
STATE_FILE = DATA_DIR / "plaud_state.json"
INBOX_DIR = Path(os.getenv("USER_VAULT_PATH", str(PROJECT_ROOT.parent / "obsidian/vault"))) / "Inbox"
AUDIO_TMP_DIR = Path("/tmp/plaud_audio")

if not PLAUD_TOKEN:
    print("Error: PLAUD_TOKEN not set")
    sys.exit(1)

if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY not set")
    sys.exit(1)

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
INBOX_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_TMP_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer {PLAUD_TOKEN}",
    "Content-Type": "application/json"
}

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def fetch_files_list():
    resp = requests.get(f"{PLAUD_API_DOMAIN}/file/simple/web", headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0 and not data.get("data_file_list"):
        print(f"Error fetching files: {data.get('msg')}")
        return []
    return data.get("data_file_list", [])

def fetch_file_detail(file_id):
    resp = requests.get(f"{PLAUD_API_DOMAIN}/file/detail/{file_id}", headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0 and not data.get("data"):
        return None
    return data.get("data")

def download_audio(file_id, output_path):
    resp = requests.get(f"{PLAUD_API_DOMAIN}/file/download/{file_id}", headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0 or not data.get("data", {}).get("download_url"):
        return False
    
    download_url = data["data"]["download_url"]
    audio_resp = requests.get(download_url, stream=True)
    audio_resp.raise_for_status()
    
    with open(output_path, "wb") as f:
        for chunk in audio_resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return True

def chunk_text(text, max_chars=20000):
    """Split text into chunks if it's too long for LLM context."""
    chunks = []
    current_chunk = ""
    for sentence in text.replace("\n", " ").split(". "):
        if len(current_chunk) + len(sentence) < max_chars:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def extract_summary_and_tasks(text):
    """Use Groq Llama 3 API to summarize and extract tasks."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    chunks = chunk_text(text)
    summaries = []
    
    for idx, chunk in enumerate(chunks):
        prompt = f"Analyze the following transcript chunk. Extract the main points and actionable tasks. If there are no tasks, just summarize.\n\nTranscript:\n{chunk}"
        
        payload = {
            "model": "llama-3.1-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are a highly efficient assistant. Respond in the same language as the transcript (Russian, Uzbek, or English). Give a concise summary and a bulleted list of tasks formatted as '- [ ] task name'."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        result = resp.json()
        summaries.append(result["choices"][0]["message"]["content"])
    
    if len(summaries) == 1:
        return summaries[0]
    
    # Final pass to combine chunks if there were multiple
    combined = "\n\n".join(summaries)
    final_prompt = f"Combine these summaries into a single cohesive summary and a single consolidated task list.\n\nSummaries:\n{combined}"
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are an assistant. Format the final output cleanly. Group all tasks at the bottom as '- [ ] task'."},
            {"role": "user", "content": final_prompt}
        ],
        "temperature": 0.3
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def push_tasks_to_vikunja(analysis_text, filename, dry_run=False):
    """Parses '- [ ] task name' strings from the text and pushes them to Vikunja using the bash script."""
    import re
    tasks = re.findall(r"^\s*-\s*\[\s*\]\s*(.+)$", analysis_text, re.MULTILINE)
    
    if not tasks:
        return 0
    
    vikunja_script = PROJECT_ROOT / "skills" / "vikunja" / "vikunja.sh"
    added_count = 0
    
    for task_name in tasks:
        # Clean task name of extra formatting if any (like bolding)
        clean_name = task_name.replace("**", "").strip()
        title = f"[Plaud] {clean_name}"
        description = f"Source recording: {filename}"
        
        if dry_run:
            print(f"  -> (DRY RUN) Would create Vikunja task: {title}")
            added_count += 1
            continue
            
        try:
            # Using the Vikunja wrapper script to create tasks
            result = subprocess.run(
                ["bash", str(vikunja_script), "create", title, description],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                added_count += 1
            else:
                print(f"  -> Vikunja push failed for: {title}\n     Error: {result.stderr}")
        except Exception as e:
            print(f"  -> Error pushing task '{task_name}' to Vikunja: {e}")
            
    return added_count

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

def main(dry_run=False):
    print(f"[{datetime.now()}] Starting Plaud Monitor check...")
    state = load_state()
    files = fetch_files_list()
    
    if not files:
        print("No files found or error fetching.")
        return

    stt = WhisperSTT()
    processed_count = 0
    updated_count = 0

    for f in list(files): # reversed to process oldest first? default order is newest first usually.
        file_id = f["id"]
        filename = f.get("filename", "Unknown")
        edit_time = f.get("edit_time", time.time())
        created_at_dt = datetime.fromtimestamp(edit_time)
        note_filename = f"Plaud_{created_at_dt.strftime('%Y-%m-%d_%H%M')}_{file_id[:8]}.md"
        note_path = INBOX_DIR / note_filename

        if file_id not in state:
            print(f"[{file_id}] New recording found: {filename}")
            
            audio_path = AUDIO_TMP_DIR / f"{file_id}.mp3"
            if not dry_run:
                print(f"  -> Downloading audio...")
                if not download_audio(file_id, audio_path):
                    print("  -> Download failed. Skipping.")
                    continue
                
                print(f"  -> Transcribing with Groq Whisper...")
                try:
                    transcript = stt.transcribe(str(audio_path))
                except Exception as e:
                    print(f"  -> Transcription error: {e}")
                    continue
                finally:
                    if audio_path.exists():
                        os.remove(audio_path)
                
                print(f"  -> Generating summary & tasks...")
                try:
                    analysis = extract_summary_and_tasks(transcript)
                    print(f"  -> Pushing extracted tasks to Vikunja...")
                    tasks_added = push_tasks_to_vikunja(analysis, filename, dry_run=False)
                    if tasks_added > 0:
                        print(f"  -> Successfully pushed {tasks_added} tasks to Vikunja.")
                except Exception as e:
                    print(f"  -> Analysis error: {e}")
                    analysis = "Error generating summary."
                
                # Check for native links right away
                native_links = []
                detail = fetch_file_detail(file_id)
                if detail and detail.get("content_list"):
                    native_links = detail["content_list"]
                
                print(f"  -> Saving to Obsidian: {note_filename}")
                note_content = format_obsidian_note(file_id, filename, edit_time, transcript, analysis, native_links)
                with open(note_path, "w") as nf:
                    nf.write(note_content)
                
                state[file_id] = {
                    "processed_at": time.time(),
                    "obsidian_file": str(note_path),
                    "has_native_links": bool(native_links)
                }
                save_state(state)
                processed_count += 1
                
            else:
                print("  -> (DRY RUN) Would download, transcribe, and save.")
        
        else:
            # File already processed. Check if native links became available later.
            if not state[file_id].get("has_native_links", False):
                detail = fetch_file_detail(file_id)
                if detail and detail.get("content_list"):
                    print(f"[{file_id}] Found new native Plaud links for {filename}")
                    if not dry_run:
                        note_path_str = state[file_id].get("obsidian_file")
                        if note_path_str and os.path.exists(note_path_str):
                            with open(note_path_str, "a") as nf:
                                nf.write("\n\n## New Plaud App Links\n")
                                for link in detail["content_list"]:
                                    nf.write(f"- [{link['data_title']}]({link['data_link']})\n")
                            state[file_id]["has_native_links"] = True
                            save_state(state)
                            updated_count += 1
                        else:
                            print(f"  -> Note file not found at {note_path_str}")
                    else:
                        print("  -> (DRY RUN) Would append native links to Obsidian note.")

    if processed_count > 0 or updated_count > 0:
        print(f"✅ Processed {processed_count} new recordings, updated {updated_count} existing.")
    else:
        pass # print("No new recordings.") # Avoid noisy output on cron success with nothing to do

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
