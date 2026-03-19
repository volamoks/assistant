"""
Obsidian Tasks helper — replaces Vikunja API calls.
Stores tasks as markdown files with Tasks plugin syntax.

CLI usage:
    python3 obsidian_tasks.py list [tag1,tag2]
    python3 obsidian_tasks.py count [tag1,tag2]
    python3 obsidian_tasks.py create "title" "tag1,tag2" [folder] [due] [priority]
    python3 obsidian_tasks.py done "title contains"
    python3 obsidian_tasks.py list-pending
    python3 obsidian_tasks.py count-pending [tag]

# Vikunja-compatible aliases (matching vikunja.sh CLI):
    python3 obsidian_tasks.py create-bug "title" "description" "YYYY-MM-DD"
    python3 obsidian_tasks.py create-improvement "title" "description" "YYYY-MM-DD"
    python3 obsidian_tasks.py create-discovery "title" "description" "YYYY-MM-DD"
    python3 obsidian_tasks.py list-by-status undone
    python3 obsidian_tasks.py list-overdue
"""
import os
import re
import json
import shutil
from datetime import datetime, date
from pathlib import Path

VAULT_PATH = os.environ.get("VAULT_PATH", "/data/obsidian/vault")
VAULT_PATH = os.environ.get("USER_VAULT_PATH", VAULT_PATH)
TASKS_DIR = f"{VAULT_PATH}/Bot/Tasks"

# Tag → filename mapping
TAG_FOLDER_MAP = {
    "task/bot":      "bot-tasks.md",
    "task/work":     "work-tasks.md",
    "task/personal": "personal-tasks.md",
    "bot":           "bot-tasks.md",
    "work":          "work-tasks.md",
    "personal":      "personal-tasks.md",
}

FOLDER_FILES = {
    "bot-tasks":     "bot-tasks.md",
    "work-tasks":    "work-tasks.md",
    "personal-tasks":"personal-tasks.md",
    "default":       "bot-tasks.md",
}

PRIORITY_MAP = {"high": "🔴", "medium": "🟡", "low": "🟢", None: "⚪"}


def _ensure_dir():
    Path(TASKS_DIR).mkdir(parents=True, exist_ok=True)


def _tags_to_str(tags: list) -> str:
    result = []
    for t in tags:
        if not t.startswith("#"):
            t = "#" + t
        result.append(t)
    return " ".join(result)


def _guess_folder(tags: list) -> str:
    """Guess folder from tags."""
    for t in tags:
        if t in TAG_FOLDER_MAP:
            return t
        if t.startswith("#"):
            base = t[1:]
            if base in TAG_FOLDER_MAP:
                return base
    return "bot-tasks"


def _resolve_file(folder: str = None) -> str:
    if folder and folder in FOLDER_FILES:
        return f"{TASKS_DIR}/{FOLDER_FILES[folder]}"
    if folder:
        # allow raw filename
        if folder.endswith(".md"):
            return f"{TASKS_DIR}/{folder}"
        return f"{TASKS_DIR}/{folder}.md"
    return f"{TASKS_DIR}/bot-tasks.md"


def create_task(
    title: str,
    tags: list,
    due: str = None,
    priority: str = None,
    folder: str = None,
    status: str = " ",
    description: str = None,
) -> str:
    """Create a task in Obsidian Tasks format. Returns file path."""
    _ensure_dir()
    
    if folder is None:
        folder = _guess_folder(tags)
    
    filepath = _resolve_file(folder)
    
    priority_str = PRIORITY_MAP.get(priority, "⚪")
    due_str = f"📅 {due}" if due else ""
    tags_str = _tags_to_str(tags)
    desc_comment = f" <!-- {description} -->" if description else ""
    
    line = f"- [{status}] {title} {priority_str} {due_str} {tags_str}{desc_comment}\n"
    
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line)
    
    return filepath


def list_tasks(tags: list = None, status_filter: str = None) -> list:
    """List tasks, optionally filtered by tags. Returns list of task strings."""
    _ensure_dir()
    results = []
    
    for fname in ["bot-tasks.md", "work-tasks.md", "personal-tasks.md"]:
        fpath = f"{TASKS_DIR}/{fname}"
        if not os.path.exists(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("- ["):
                    if status_filter and f"- [{status_filter}]" not in line:
                        continue
                    if tags is None or any(f"#{t}" in line for t in tags):
                        results.append(line.strip())
    return results


def list_all_raw() -> dict:
    """Return raw dict of all tasks per file."""
    _ensure_dir()
    result = {}
    for fname in ["bot-tasks.md", "work-tasks.md", "personal-tasks.md"]:
        fpath = f"{TASKS_DIR}/{fname}"
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                result[fname] = f.read()
        else:
            result[fname] = ""
    return result


def mark_done(title_contains: str, folder: str = None) -> bool:
    """Mark first matching task as done."""
    _ensure_dir()
    
    if folder:
        files = [_resolve_file(folder)]
    else:
        files = [
            f"{TASKS_DIR}/bot-tasks.md",
            f"{TASKS_DIR}/work-tasks.md",
            f"{TASKS_DIR}/personal-tasks.md",
        ]
    
    for filepath in files:
        if not os.path.exists(filepath):
            continue
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.strip().startswith("- [ ]") and title_contains.lower() in line.lower():
                lines[i] = line.replace("- [ ]", "- [x]")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                return True
    return False


def count_pending(tags: list = None) -> int:
    """Count pending tasks."""
    return len([t for t in list_tasks(tags=tags) if "- [ ]" in t])


def count_by_folder() -> dict:
    """Count pending tasks per folder."""
    result = {}
    for folder_key, fname in FOLDER_FILES.items():
        if folder_key == "default":
            continue
        fpath = f"{TASKS_DIR}/{fname}"
        count = 0
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    if "- [ ]" in line:
                        count += 1
        result[folder_key] = count
    return result


def parse_task_line(line: str) -> dict:
    """Parse a single task line into dict."""
    m = re.match(r"- \[([ x])\] (.+)", line.strip())
    if not m:
        return None
    done = m.group(1) == "x"
    rest = m.group(2)
    
    # Extract due date: 📅 YYYY-MM-DD
    due_m = re.search(r"📅 (\d{4}-\d{2}-\d{2})", rest)
    due = due_m.group(1) if due_m else None
    
    # Extract priority emoji
    priority = None
    if "🔴" in rest: priority = "high"
    elif "🟡" in rest: priority = "medium"
    elif "🟢" in rest: priority = "low"
    
    # Extract tags
    tags = re.findall(r"#[\w/]+", rest)
    
    # Extract description from HTML comment
    desc_m = re.search(r"<!-- (.+?) -->", rest)
    description = desc_m.group(1) if desc_m else None
    
    # Title = rest minus tags, due, priority, comment
    title = re.sub(r"📅 \S+", "", rest)
    title = re.sub(r"[🔴🟡🟢⚪]", "", title)
    title = re.sub(r"#[\w/]+", "", title)
    title = re.sub(r"<!-- .+? -->", "", title)
    title = title.strip()
    
    return {
        "done": done,
        "title": title,
        "due": due,
        "priority": priority,
        "tags": tags,
        "description": description,
    }


def _format_vikunja_style(tag_filter: str = None, status: str = " ") -> str:
    """Format tasks like Vikunja API output for backwards compat."""
    tasks = list_tasks(tags=[tag_filter] if tag_filter else None)
    output = []
    for line in tasks:
        if status and f"- [{status}]" not in line:
            continue
        parsed = parse_task_line(line)
        if parsed:
            due = parsed["due"] or "null"
            pri = {"high": "3", "medium": "2", "low": "1", None: "0"}.get(parsed["priority"], "0")
            # Match Vikunja jq output format
            output.append(
                f'{{"id": null, "title": "{parsed["title"]}", '
                f'"description": "{parsed["description"] or ""}", '
                f'"done": {str(parsed["done"]).lower()}, '
                f'"due_date": "{due}", '
                f'"priority": {pri}, "project_id": 1}}'
            )
    return "[" + ",\n".join(output) + "]" if output else "[]"


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    
    if cmd == "list":
        tags = sys.argv[2].split(",") if len(sys.argv) > 2 else None
        results = list_tasks(tags=tags)
        if results:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print("[]")
    
    elif cmd == "count":
        tags = sys.argv[2].split(",") if len(sys.argv) > 2 else None
        print(count_pending(tags=tags))
    
    elif cmd == "count-by-folder":
        counts = count_by_folder()
        total = sum(counts.values())
        print(f"bot: {counts.get('bot-tasks', 0)}, work: {counts.get('work-tasks', 0)}, personal: {counts.get('personal-tasks', 0)}, total: {total}")
    
    elif cmd == "create":
        # python3 obsidian_tasks.py create "title" "tag1,tag2" [folder] [due] [priority]
        title = sys.argv[2]
        tag_str = sys.argv[3] if len(sys.argv) > 3 else "task/bot"
        folder = sys.argv[4] if len(sys.argv) > 4 else None
        due = sys.argv[5] if len(sys.argv) > 5 else None
        priority = sys.argv[6] if len(sys.argv) > 6 else None
        tags_list = tag_str.split(",")
        result = create_task(title, tags_list, due=due, priority=priority, folder=folder)
        print(result)
    
    elif cmd == "done":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        ok = mark_done(title)
        print("done" if ok else "not found")
    
    # Vikunja-compatible aliases
    elif cmd == "create-bug":
        # python3 obsidian_tasks.py create-bug "title" "description" "YYYY-MM-DD"
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        desc = sys.argv[3] if len(sys.argv) > 3 else ""
        due = sys.argv[4] if len(sys.argv) > 4 else None
        result = create_task(f"[BUG] {title}", ["task/bot"], due=due, priority="high",
                           folder="bot-tasks", description=desc)
        print(json.dumps({"file": result, "title": title}, ensure_ascii=False))
    
    elif cmd == "create-improvement":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        desc = sys.argv[3] if len(sys.argv) > 3 else ""
        due = sys.argv[4] if len(sys.argv) > 4 else None
        result = create_task(f"[IMPROVE] {title}", ["task/bot"], due=due, priority="medium",
                           folder="bot-tasks", description=desc)
        print(json.dumps({"file": result, "title": title}, ensure_ascii=False))
    
    elif cmd == "create-discovery":
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        desc = sys.argv[3] if len(sys.argv) > 3 else ""
        due = sys.argv[4] if len(sys.argv) > 4 else None
        result = create_task(f"[IDEA] {title}", ["task/bot"], due=due, priority="low",
                           folder="bot-tasks", description=desc)
        print(json.dumps({"file": result, "title": title}, ensure_ascii=False))
    
    elif cmd == "list-by-status":
        status_arg = sys.argv[2] if len(sys.argv) > 2 else "undone"
        status_map = {"done": "x", "undone": " "}
        status_char = status_map.get(status_arg, " ")
        # Output in Vikunja-compatible JSON format
        print(_format_vikunja_style(status=status_char))
    
    elif cmd == "list-overdue":
        today = date.today().isoformat()
        tasks = list_tasks()
        overdue = []
        for line in tasks:
            if "- [ ]" not in line:
                continue
            parsed = parse_task_line(line)
            if parsed and parsed["due"] and parsed["due"] < today:
                overdue.append(line)
        if overdue:
            print("\n".join(overdue))
        else:
            print("")
    
    elif cmd == "create-task":
        # Vikunja-style: create-task "title" ["description"] ["YYYY-MM-DD"] [priority]
        title = sys.argv[2] if len(sys.argv) > 2 else ""
        desc = sys.argv[3] if len(sys.argv) > 3 else ""
        due = sys.argv[4] if len(sys.argv) > 4 else None
        priority = sys.argv[5] if len(sys.argv) > 5 else "medium"
        result = create_task(title, ["task/bot"], due=due, priority=priority,
                           folder="bot-tasks", description=desc)
        print(json.dumps({"file": result}, ensure_ascii=False))
    
    elif cmd == "create-for-project":
        # create-for-project <project_id> "title" ["desc"] ["date"] [priority]
        # project_id is ignored (we use folder-based), but kept for compat
        title = sys.argv[3] if len(sys.argv) > 3 else ""
        desc = sys.argv[4] if len(sys.argv) > 4 else ""
        due = sys.argv[5] if len(sys.argv) > 5 else None
        priority = sys.argv[6] if len(sys.argv) > 6 else "medium"
        result = create_task(title, ["task/bot"], due=due, priority=priority,
                           folder="bot-tasks", description=desc)
        print(json.dumps({"file": result}, ensure_ascii=False))
    
    elif cmd == "status":
        counts = count_by_folder()
        total = sum(counts.values())
        print(f"Obsidian Tasks — OK")
        print(f"Vault: {VAULT_PATH}")
        print(f"Tasks dir: {TASKS_DIR}")
        print(f"Pending: bot={counts.get('bot-tasks',0)}, work={counts.get('work-tasks',0)}, personal={counts.get('personal-tasks',0)}, total={total}")
    
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: list, count, count-by-folder, create, done, create-bug, create-improvement, create-discovery, list-by-status, list-overdue, create-task, create-for-project, status")
