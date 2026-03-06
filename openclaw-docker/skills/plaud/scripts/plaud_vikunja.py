import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

def push_tasks_to_vikunja(analysis_text, filename, dry_run=False):
    """Parses '- [ ] task name: description' strings from the text and pushes them to Vikunja."""
    
    # Match both format with description (separated by colon or dash) and without
    # Group 1: Title, Group 2: Description (optional)
    tasks = re.findall(r"^\s*-\s*\[\s*\]\s*([^:\-]+)(?:[:\-]\s*(.+))?$", analysis_text, re.MULTILINE)
    
    if not tasks:
        # Fallback if LLM used a different format
        tasks = re.findall(r"^\s*-\s*\[\s*\]\s*(.+)$", analysis_text, re.MULTILINE)
        if not tasks:
            return 0
        
        # Normalize to tuple (title, empty description)
        normalized_tasks = [(t, "") for t in tasks if not isinstance(t, tuple)]
    else:
        normalized_tasks = tasks
    
    vikunja_script = PROJECT_ROOT / "skills" / "vikunja" / "vikunja.sh"
    added_count = 0
    
    for task_entry in normalized_tasks:
        if isinstance(task_entry, tuple):
            task_title, task_desc = task_entry
        else:
            task_title, task_desc = task_entry, ""
            
        # Clean task name of extra formatting if any (like bolding)
        clean_name = task_title.replace("**", "").strip()
        title = f"[Plaud] {clean_name}"
        
        description = f"Source recording: {filename}"
        if task_desc:
            clean_desc = task_desc.replace("**", "").strip()
            description = f"{clean_desc}\n\n{description}"
        
        if dry_run:
            print(f"  -> (DRY RUN) Would create Vikunja task: {title}\n      Desc: {description.splitlines()[0][:50]}...")
            added_count += 1
            continue
            
        try:
            # Using the Vikunja wrapper script to create tasks
            result = subprocess.run(
                ["bash", str(vikunja_script), "create-improvement", title, description],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                added_count += 1
            else:
                print(f"  -> Vikunja push failed for: {title}\n     Error: {result.stderr}")
        except Exception as e:
            print(f"  -> Error pushing task '{clean_name}' to Vikunja: {e}")
            
    return added_count
