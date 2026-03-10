#!/usr/bin/env python3
"""
karpathy-autoresearch/prompt_patch.py — Prompt Patch System

Applies changes to SKILL.md files based on approved hypotheses.
Creates backups before changes and validates syntax after.

Part of the Karpathy Autoresearch self-improvement cycle (P1).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path("~/.openclaw/skills/karpathy-autoresearch/config.yaml").expanduser()
BACKUP_DIR = Path("/tmp/karpathy_backups")

# ── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class PatchResult:
    """Result of applying a patch."""
    hypothesis_id: str
    file_path: str
    success: bool
    backup_path: Optional[str]
    error: Optional[str]
    changes_made: List[str]


@dataclass
class AppliedPatch:
    """Record of an applied patch."""
    id: str
    hypothesis_id: str
    file_path: str
    backup_path: str
    timestamp: str
    changes: List[str]
    original_hash: str
    new_hash: str
    validated: bool


# ── Core Functions ───────────────────────────────────────────────────────────

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def get_file_hash(filepath: Path) -> str:
    """Get SHA256 hash of file content."""
    content = filepath.read_bytes()
    return hashlib.sha256(content).hexdigest()


def create_backup(filepath: Path, backup_dir: Path) -> Optional[Path]:
    """Create a timestamped backup of the file."""
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{filepath.stem}_{timestamp}{filepath.suffix}"
        backup_path = backup_dir / backup_name
        
        shutil.copy2(filepath, backup_path)
        
        print(f"  💾 Backup created: {backup_path}")
        return backup_path
        
    except Exception as e:
        print(f"  ❌ Backup failed: {e}")
        return None


def validate_yaml_syntax(content: str) -> Tuple[bool, Optional[str]]:
    """Validate YAML syntax in content."""
    try:
        # Try to parse as full YAML document
        yaml.safe_load(content)
        return True, None
    except yaml.YAMLError as e:
        return False, f"YAML error: {e}"


def validate_markdown_structure(content: str) -> Tuple[bool, Optional[str]]:
    """Validate markdown structure (basic checks)."""
    lines = content.splitlines()
    
    # Check for balanced headers
    header_counts = {}
    for line in lines:
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            header_counts[level] = header_counts.get(level, 0) + 1
    
    # Check for broken links
    broken_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    for text, url in broken_links:
        if not url or url.startswith("#") or url.startswith("mailto:"):
            continue
    
    # Check for unclosed code blocks
    code_blocks = re.findall(r'```', content)
    if len(code_blocks) % 2 != 0:
        return False, "Unclosed code block detected"
    
    return True, None


def validate_frontmatter(content: str) -> Tuple[bool, Optional[str]]:
    """Validate YAML frontmatter if present."""
    if not content.startswith("---"):
        return True, None
    
    # Find frontmatter end
    lines = content.splitlines()
    if len(lines) < 3:
        return False, "Incomplete frontmatter"
    
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break
    
    if end_idx is None:
        return False, "Unclosed frontmatter"
    
    # Validate YAML in frontmatter
    frontmatter = "\n".join(lines[1:end_idx])
    return validate_yaml_syntax(frontmatter)


def validate_file(filepath: Path) -> Tuple[bool, List[str]]:
    """Validate file syntax and structure."""
    errors = []
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Cannot read file: {e}"]
    
    # Check frontmatter
    valid, error = validate_frontmatter(content)
    if not valid:
        errors.append(error)
    
    # Check YAML blocks (config sections)
    yaml_blocks = re.findall(r'^```yaml\s*\n(.*?)^```', content, re.MULTILINE | re.DOTALL)
    for block in yaml_blocks:
        valid, error = validate_yaml_syntax(block)
        if not valid:
            errors.append(f"YAML block error: {error}")
    
    # Check markdown structure
    valid, error = validate_markdown_structure(content)
    if not valid:
        errors.append(error)
    
    return len(errors) == 0, errors


def find_section(content: str, section_name: str) -> Optional[Tuple[int, int]]:
    """Find a markdown section by name. Returns (start_line, end_line)."""
    lines = content.splitlines()
    
    for i, line in enumerate(lines):
        # Match exact section header (e.g., "## Usage" or "### Components")
        if re.match(rf'^{{1,6}}\s+{re.escape(section_name)}$', line, re.IGNORECASE):
            # Find the end of this section (next header or end of file)
            end_idx = len(lines)
            for j in range(i + 1, len(lines)):
                if re.match(r'^#{1,6}\s+', lines[j]):
                    end_idx = j
                    break
            
            return i, end_idx
    
    return None


def apply_prompt_patch(
    filepath: Path,
    hypothesis: Dict[str, Any],
    backup_dir: Path
) -> PatchResult:
    """Apply a patch to a file based on hypothesis."""
    hypothesis_id = hypothesis.get("id", "unknown")
    
    # Read original content
    if not filepath.exists():
        return PatchResult(
            hypothesis_id=hypothesis_id,
            file_path=str(filepath),
            success=False,
            backup_path=None,
            error=f"File not found: {filepath}",
            changes_made=[]
        )
    
    original_content = filepath.read_text(encoding="utf-8")
    original_hash = get_file_hash(filepath)
    
    # Create backup
    backup_path = create_backup(filepath, backup_dir)
    if not backup_path:
        return PatchResult(
            hypothesis_id=hypothesis_id,
            file_path=str(filepath),
            success=False,
            backup_path=None,
            error="Failed to create backup",
            changes_made=[]
        )
    
    new_content = original_content
    changes_made = []
    
    # Apply changes based on hypothesis type
    proposed_change = hypothesis.get("proposed_change", "")
    target_section = hypothesis.get("target_section")
    
    if not target_section:
        # Try to infer target from target_file
        target_file = hypothesis.get("target_file", "")
        if "usage" in target_file.lower():
            target_section = "Usage"
        elif "components" in target_file.lower():
            target_section = "Components"
        elif "configuration" in target_file.lower() or "config" in target_file.lower():
            target_section = "Configuration"
    
    # Apply different types of changes
    change_type = hypothesis.get("change_type", "append")
    
    if change_type == "append":
        # Append to end or to specific section
        if target_section:
            section_range = find_section(new_content, target_section)
            if section_range:
                start, end = section_range
                # Append after section header
                lines = new_content.splitlines()
                insert_pos = start + 1
                
                # Find where to insert (after section content)
                insert_content = f"\n{proposed_change}\n"
                lines.insert(insert_pos, insert_content)
                new_content = "\n".join(lines)
                changes_made.append(f"Appended to {target_section} section")
            else:
                # Section not found, append to end
                new_content += f"\n\n{proposed_change}\n"
                changes_made.append(f"Appended content (section {target_section} not found)")
        else:
            new_content += f"\n\n{proposed_change}\n"
            changes_made.append("Appended content")
    
    elif change_type == "replace":
        # Replace a specific section
        if target_section:
            section_range = find_section(new_content, target_section)
            if section_range:
                start, end = section_range
                lines = new_content.splitlines()
                replacement = f"{lines[start]}\n\n{proposed_change}\n"
                lines[start:end] = [replacement]
                new_content = "\n".join(lines)
                changes_made.append(f"Replaced {target_section} section")
            else:
                changes_made.append(f"Section {target_section} not found - no changes")
        else:
            changes_made.append("No target section specified for replace")
    
    elif change_type == "add_tool":
        # Add a new tool to the tools section
        tool_name = hypothesis.get("tool_name", "new_tool")
        tool_config = hypothesis.get("tool_config", {})
        
        # Find tools section
        tools_section = find_section(new_content, "Tools")
        if tools_section:
            start, _ = tools_section
            lines = new_content.splitlines()
            
            tool_entry = f"### {tool_name}\n"
            for key, value in tool_config.items():
                tool_entry += f"- **{key}**: {value}\n"
            
            lines.insert(start + 1, tool_entry)
            new_content = "\n".join(lines)
            changes_made.append(f"Added tool: {tool_name}")
        else:
            # Add tools section if not exists
            new_content += f"\n\n## Tools\n\n### {tool_name}\n"
            for key, value in tool_config.items():
                new_content += f"- **{key}**: {value}\n"
            changes_made.append(f"Added tools section with {tool_name}")
    
    elif change_type == "improve_prompt":
        # Improve existing prompt/instruction
        if target_section:
            section_range = find_section(new_content, target_section)
            if section_range:
                start, end = section_range
                lines = new_content.splitlines()
                old_section = "\n".join(lines[start:end])
                
                # Replace with improved version
                improved_section = f"{lines[start]}\n\n{proposed_change}\n"
                lines[start:end] = [improved_section]
                new_content = "\n".join(lines)
                changes_made.append(f"Improved {target_section} prompt")
            else:
                changes_made.append(f"Section {target_section} not found")
        else:
            # Try to find prompt-related sections
            for section in ["System Prompt", "Instructions", "Behavior"]:
                section_range = find_section(new_content, section)
                if section_range:
                    start, end = section_range
                    lines = new_content.splitlines()
                    improved_section = f"{lines[start]}\n\n{proposed_change}\n"
                    lines[start:end] = [improved_section]
                    new_content = "\n".join(lines)
                    changes_made.append(f"Improved {section} section")
                    break
            else:
                changes_made.append("No suitable prompt section found")
    
    else:
        # Default: append
        new_content += f"\n\n{proposed_change}\n"
        changes_made.append("Appended generic content")
    
    # Write new content
    try:
        filepath.write_text(new_content, encoding="utf-8")
    except Exception as e:
        # Restore from backup on failure
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, filepath)
        return PatchResult(
            hypothesis_id=hypothesis_id,
            file_path=str(filepath),
            success=False,
            backup_path=str(backup_path),
            error=f"Failed to write: {e}",
            changes_made=changes_made
        )
    
    # Validate after change
    valid, errors = validate_file(filepath)
    
    if not valid:
        # Rollback on validation failure
        print(f"  ⚠️ Validation failed: {errors}")
        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, filepath)
            print(f"  🔄 Rolled back to backup")
        
        return PatchResult(
            hypothesis_id=hypothesis_id,
            file_path=str(filepath),
            success=False,
            backup_path=str(backup_path),
            error=f"Validation failed: {errors}",
            changes_made=changes_made
        )
    
    new_hash = get_file_hash(filepath)
    
    return PatchResult(
        hypothesis_id=hypothesis_id,
        file_path=str(filepath),
        success=True,
        backup_path=str(backup_path),
        error=None,
        changes_made=changes_made
    )


def rollback_patch(filepath: Path, backup_path: Path) -> bool:
    """Rollback a patch by restoring from backup."""
    try:
        if backup_path.exists():
            shutil.copy2(backup_path, filepath)
            print(f"  🔄 Rolled back: {filepath}")
            return True
        else:
            print(f"  ❌ Backup not found: {backup_path}")
            return False
    except Exception as e:
        print(f"  ❌ Rollback failed: {e}")
        return False


def record_applied_patch(
    patch: PatchResult,
    original_hash: str,
    applied_patches_path: Path
) -> None:
    """Record applied patch in history file."""
    history = []
    
    if applied_patches_path.exists():
        try:
            history = json.loads(applied_patches_path.read_text())
        except json.JSONDecodeError:
            history = []
    
    new_hash = get_file_hash(Path(patch.file_path))
    
    record = {
        "id": f"patch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "hypothesis_id": patch.hypothesis_id,
        "file_path": patch.file_path,
        "backup_path": patch.backup_path,
        "timestamp": datetime.now().isoformat(),
        "changes": patch.changes_made,
        "original_hash": original_hash,
        "new_hash": new_hash,
        "validated": patch.success
    }
    
    history.append(record)
    
    applied_patches_path.parent.mkdir(parents=True, exist_ok=True)
    with open(applied_patches_path, "w") as f:
        json.dump(history, f, indent=2)


def get_applied_patches(applied_patches_path: Path) -> List[Dict[str, Any]]:
    """Get list of applied patches."""
    if not applied_patches_path.exists():
        return []
    
    try:
        return json.loads(applied_patches_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return []


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Prompt Patch System for Karpathy Autoresearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Apply a patch from hypothesis
  python3 prompt_patch.py --hypothesis '{"id": "hyp_001", "proposed_change": "..."}'
  
  # Apply patch to specific file
  python3 prompt_patch.py --file /path/to/SKILL.md --hypothesis '{"proposed_change": "..."}'
  
  # Validate a file
  python3 prompt_patch.py --validate /path/to/SKILL.md
  
  # Rollback a patch
  python3 prompt_patch.py --rollback patch_id
        """
    )
    parser.add_argument("--hypothesis", type=str, help="JSON hypothesis to apply")
    parser.add_argument("--file", type=Path, help="Target file path")
    parser.add_argument("--backup-dir", type=Path, default=BACKUP_DIR, help="Backup directory")
    parser.add_argument("--validate", type=Path, help="Validate file syntax")
    parser.add_argument("--rollback", type=str, help="Rollback patch by ID")
    parser.add_argument("--list-patches", action="store_true", help="List applied patches")
    parser.add_argument("--output", type=Path, default=Path("/tmp/karpathy_patches.json"))
    args = parser.parse_args()
    
    print("🩹 Prompt Patch System")
    print("=" * 60)
    
    # Load config
    config = load_config()
    
    # Validate mode
    if args.validate:
        filepath = args.validate
        print(f"  Validating: {filepath}")
        
        valid, errors = validate_file(filepath)
        
        if valid:
            print(f"  ✅ Validation passed")
        else:
            print(f"  ❌ Validation failed:")
            for error in errors:
                print(f"     - {error}")
        
        return 0 if valid else 1
    
    # List patches
    if args.list_patches:
        applied_patches_path = Path("/tmp/karpathy_applied_patches.json")
        patches = get_applied_patches(applied_patches_path)
        
        print(f"\n📋 Applied Patches ({len(patches)} total):")
        for p in patches:
            status = "✅" if p.get("validated") else "❌"
            print(f"  {status} [{p['id']}] {p['hypothesis_id']}")
            print(f"      File: {p['file_path']}")
            print(f"      Time: {p['timestamp']}")
            print(f"      Changes: {len(p.get('changes', []))}")
        
        return 0
    
    # Rollback mode
    if args.rollback:
        patch_id = args.rollback
        applied_patches_path = Path("/tmp/karpathy_applied_patches.json")
        patches = get_applied_patches(applied_patches_path)
        
        patch = next((p for p in patches if p["id"] == patch_id), None)
        if not patch:
            print(f"  ❌ Patch not found: {patch_id}")
            return 1
        
        filepath = Path(patch["file_path"])
        backup_path = Path(patch["backup_path"])
        
        success = rollback_patch(filepath, backup_path)
        
        if success:
            # Remove from history
            patches = [p for p in patches if p["id"] != patch_id]
            with open(applied_patches_path, "w") as f:
                json.dump(patches, f, indent=2)
            
            print(f"  ✅ Rolled back successfully")
        
        return 0 if success else 1
    
    # Apply patch mode
    if args.hypothesis and args.file:
        hypothesis = json.loads(args.hypothesis)
        filepath = args.file
        
        # Get original hash before change
        original_hash = get_file_hash(filepath) if filepath.exists() else ""
        
        print(f"\n🩹 Applying patch:")
        print(f"   File: {filepath}")
        print(f"   Hypothesis: {hypothesis.get('id', 'unknown')}")
        
        result = apply_prompt_patch(filepath, hypothesis, args.backup_dir)
        
        if result.success:
            print(f"  ✅ Patch applied successfully")
            for change in result.changes_made:
                print(f"     - {change}")
            
            # Record patch
            applied_patches_path = Path("/tmp/karpathy_applied_patches.json")
            record_applied_patch(result, original_hash, applied_patches_path)
            print(f"  💾 Recorded to {applied_patches_path}")
        else:
            print(f"  ❌ Patch failed: {result.error}")
        
        # Save result
        with open(args.output, "w") as f:
            json.dump({
                "success": result.success,
                "hypothesis_id": result.hypothesis_id,
                "file_path": result.file_path,
                "backup_path": result.backup_path,
                "error": result.error,
                "changes_made": result.changes_made
            }, f, indent=2)
        
        return 0 if result.success else 1
    
    else:
        print("❌ Please specify --hypothesis and --file, or use --validate/--list-patches/--rollback")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
