"""
Obsidian Tasks integration for Plaud.
Replaces Vikunja API calls with Obsidian Tasks plugin format.
Pushes parsed tasks from Plaud recordings to Bot/Tasks/bot-tasks.md.
"""

import os
import sys
import re
from pathlib import Path

# Add skills path so we can import obsidian_tasks
SCRIPT_DIR = Path(__file__).parent
SKILLS_DIR = SCRIPT_DIR.parent.parent.parent

# Import the obsidian tasks module
sys.path.insert(0, str(SKILLS_DIR / "obsidian_tasks"))
try:
    from obsidian_tasks import create_task
except ImportError:
    # Fallback: import directly
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "obsidian_tasks",
            SKILLS_DIR / "obsidian_tasks" / "obsidian_tasks.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        create_task = mod.create_task
    except Exception as e:
        def create_task_fallback(title, tags, due=None, priority=None, folder=None, description=None):
            print(f"WARNING: obsidian_tasks unavailable: {e}")
            print(f"  Would create: {title}")
            return None
        create_task = create_task_fallback


def push_tasks_to_obsidian(analysis_text: str, filename: str, dry_run: bool = False) -> int:
    """
    Parses '- [ ] task name: description' strings from text and pushes them to Obsidian Tasks.
    
    Returns:
        Number of tasks created
    """
    # Match: - [ ] Task Title: description
    tasks = re.findall(r"^\s*-\s*\[\s*\]\s*([^:\-]+)(?::\s*(.+))?$", analysis_text, re.MULTILINE)
    
    if not tasks:
        # Fallback: just find all unchecked task lines
        tasks = re.findall(r"^\s*-\s*\[\s*\]\s*(.+)$", analysis_text, re.MULTILINE)
        if tasks:
            tasks = [(t, "") for t in tasks]
    
    added_count = 0
    
    for task_entry in tasks:
        if isinstance(task_entry, tuple):
            task_title, task_desc = task_entry
        else:
            task_title, task_desc = task_entry, ""
        
        # Clean formatting
        clean_name = task_title.replace("**", "").strip()
        title = f"[Plaud] {clean_name}"
        
        description = f"Source recording: {filename}"
        if task_desc:
            clean_desc = task_desc.replace("**", "").strip()
            description = f"{clean_desc}\n\n{description}"
        
        if dry_run:
            print(f"  -> (DRY RUN) Would create Obsidian Task: {title}")
            added_count += 1
            continue
        
        try:
            result = create_task(
                title=title,
                tags=["task/bot", "plaud"],
                folder="bot-tasks",
                priority="medium",
                description=description
            )
            added_count += 1
            print(f"  -> Created Obsidian Task: {title}")
            if result:
                print(f"      File: {result}")
        except Exception as e:
            print(f"  -> Error pushing task '{clean_name}' to Obsidian Tasks: {e}")
    
    return added_count


# Backwards-compatible alias
push_tasks_to_vikunja = push_tasks_to_obsidian


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Push Plaud tasks to Obsidian Tasks")
    parser.add_argument("filename", help="Source recording filename")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually create tasks")
    args = parser.parse_args()
    
    # Read from stdin
    text = sys.stdin.read()
    count = push_tasks_to_obsidian(text, args.filename, dry_run=args.dry_run)
    print(f"Created {count} tasks")
