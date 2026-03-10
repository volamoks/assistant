#!/usr/bin/env python3
"""
Skill Researcher — ночной цикл улучшения Python-скриптов бота.
Запускается на ХОСТЕ через LaunchAgent, использует Ollama напрямую.

Метрика качества (аналог val_loss):
  score = avg(clarity, error_handling, correctness) от LLM-судьи
  Если score_new > score_old + 0.5 → сохраняем, бэкап старой версии.
"""

import os
import json
import ast
import time
import shutil
import requests
import subprocess
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
SKILLS_DIR   = Path("/Users/abror_mac_mini/Projects/bot/openclaw-docker/skills")
STATE_FILE   = Path("/Users/abror_mac_mini/Projects/bot/openclaw-docker/scripts/skill_researcher_state.json")
LOG_FILE     = Path("/Users/abror_mac_mini/Projects/bot/openclaw-docker/scripts/skill_researcher.log")
OLLAMA_URL   = "http://localhost:11434/api/generate"
IMPROVER_MODEL = "qwen3.5:9b"    # генерирует улучшения
JUDGE_MODEL    = "qwen3.5:0.8b"  # быстрая оценка до/после
MAX_PER_RUN  = 3                  # скрипты за одну ночь
MIN_LINES    = 30                 # пропускаем совсем маленькие файлы
MAX_CHARS    = 8000               # не гоним огромные файлы в LLM

# Грузим из .env
env_path = Path("/Users/abror_mac_mini/Projects/bot/openclaw-docker/.env")
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            TELEGRAM_TOKEN = line.split("=", 1)[1].strip().strip('"\'')
        if line.startswith("TELEGRAM_CHAT_ID="):
            TELEGRAM_CHAT_ID = line.split("=", 1)[1].strip().strip('"\'')

# ── Helpers ───────────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def send_telegram(msg: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        log(f"Telegram error: {e}")

def ollama(model: str, prompt: str, timeout: int = 120) -> str:
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": model, "prompt": prompt,
            "stream": False, "options": {"temperature": 0.3}
        }, timeout=timeout)
        return r.json().get("response", "").strip()
    except Exception as e:
        log(f"Ollama error ({model}): {e}")
        return ""

def syntax_ok(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        log(f"  Syntax error: {e}")
        return False

def judge_score(code: str, filename: str) -> float:
    prompt = f"""Rate this Python script '{filename}' from 1.0 to 10.0.
Criteria: error handling (3pts), code clarity (3pts), correctness/robustness (4pts).
Reply with ONLY a JSON: {{"score": 7.5, "issues": ["issue1", "issue2"]}}

```python
{code[:3000]}
```"""
    raw = ollama(JUDGE_MODEL, prompt, timeout=60)
    try:
        # find JSON in response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            return float(data.get("score", 5.0))
    except Exception:
        pass
    return 5.0  # default if parsing fails

def improve_code(code: str, filename: str, issues: list) -> str:
    issues_text = "\n".join(f"- {i}" for i in issues) if issues else "- general code quality"
    prompt = f"""You are an expert Python developer. Improve this script '{filename}'.

Known issues to fix:
{issues_text}

Rules:
- Keep ALL existing functionality, don't remove features
- Fix error handling (add try/except where missing, better error messages)
- Improve code clarity (better variable names, add comments for complex logic)
- Keep the same imports and dependencies
- Do NOT add new external dependencies
- Return ONLY the improved Python code, no explanation

Current code:
```python
{code}
```"""
    return ollama(IMPROVER_MODEL, prompt, timeout=180)

def extract_code(raw: str) -> str:
    """Extract Python code from LLM response (strip markdown fences)."""
    if "```python" in raw:
        parts = raw.split("```python")
        if len(parts) > 1:
            return parts[1].split("```")[0].strip()
    if "```" in raw:
        parts = raw.split("```")
        if len(parts) > 1:
            return parts[1].strip()
    return raw.strip()

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"processed": {}, "last_run": None}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def find_candidate_scripts(state: dict) -> list[Path]:
    """Find Python scripts, prioritize least recently processed."""
    candidates = []
    for py in sorted(SKILLS_DIR.rglob("*.py")):
        if "__pycache__" in str(py):
            continue
        code = py.read_text(errors="ignore")
        lines = code.count("\n")
        if lines < MIN_LINES or len(code) > MAX_CHARS:
            continue
        last = state["processed"].get(str(py), 0)
        candidates.append((last, py))
    # Sort by last processed time (oldest first)
    candidates.sort(key=lambda x: x[0])
    return [p for _, p in candidates]

# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log(f"Skill Researcher started")

    state = load_state()
    candidates = find_candidate_scripts(state)

    if not candidates:
        log("No eligible scripts found.")
        return

    results = []
    processed = 0

    for script_path in candidates[:MAX_PER_RUN]:
        rel = script_path.relative_to(SKILLS_DIR)
        log(f"\n--- Processing: {rel} ---")

        original_code = script_path.read_text(errors="ignore")

        # Step 1: Judge original
        log("  Judging original...")
        orig_score = judge_score(original_code, script_path.name)
        log(f"  Original score: {orig_score:.1f}")

        # Step 2: Get issues from judge
        judge_prompt = f"""List the top 3 specific issues in this Python script.
Reply ONLY with JSON: {{"issues": ["issue1", "issue2", "issue3"]}}

```python
{original_code[:3000]}
```"""
        judge_raw = ollama(JUDGE_MODEL, judge_prompt, timeout=60)
        issues = []
        try:
            start = judge_raw.find("{")
            end = judge_raw.rfind("}") + 1
            if start >= 0 and end > start:
                issues = json.loads(judge_raw[start:end]).get("issues", [])
        except Exception:
            pass
        log(f"  Issues: {issues}")

        # Step 3: Generate improvement
        log("  Generating improvement...")
        improved_raw = improve_code(original_code, script_path.name, issues)
        improved_code = extract_code(improved_raw)

        if not improved_code or len(improved_code) < 50:
            log("  Empty response from improver, skipping.")
            state["processed"][str(script_path)] = int(time.time())
            results.append({"file": str(rel), "status": "skipped", "reason": "empty response"})
            continue

        # Step 4: Syntax check
        if not syntax_ok(improved_code):
            log("  Syntax error in improved code, skipping.")
            state["processed"][str(script_path)] = int(time.time())
            results.append({"file": str(rel), "status": "skipped", "reason": "syntax error"})
            continue

        # Step 5: Judge improved
        new_score = judge_score(improved_code, script_path.name)
        log(f"  New score: {new_score:.1f} (delta: {new_score - orig_score:+.1f})")

        # Step 6: Accept if better by threshold
        if new_score > orig_score + 0.5:
            # Backup original
            backup_path = script_path.with_suffix(
                f".py.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            shutil.copy2(script_path, backup_path)
            script_path.write_text(improved_code)
            log(f"  ✅ Improved! {orig_score:.1f} → {new_score:.1f}. Backup: {backup_path.name}")
            results.append({
                "file": str(rel),
                "status": "improved",
                "score_before": orig_score,
                "score_after": new_score,
                "issues_fixed": issues
            })
        else:
            log(f"  ℹ️ No significant improvement ({orig_score:.1f} → {new_score:.1f}), keeping original.")
            results.append({
                "file": str(rel),
                "status": "unchanged",
                "score_before": orig_score,
                "score_after": new_score
            })

        state["processed"][str(script_path)] = int(time.time())
        processed += 1

    state["last_run"] = datetime.now().isoformat()
    save_state(state)

    # Summary
    improved = [r for r in results if r["status"] == "improved"]
    unchanged = [r for r in results if r["status"] == "unchanged"]
    skipped = [r for r in results if r["status"] == "skipped"]

    log(f"\n=== Summary: {len(improved)} improved, {len(unchanged)} unchanged, {len(skipped)} skipped ===")

    if results:
        lines = [f"🔬 <b>Skill Researcher</b> — {datetime.now().strftime('%Y-%m-%d')}"]
        lines.append(f"Проверено: {processed} скриптов")
        if improved:
            lines.append(f"\n✅ Улучшено ({len(improved)}):")
            for r in improved:
                lines.append(f"  • {r['file']}: {r['score_before']:.1f}→{r['score_after']:.1f}")
        if unchanged:
            lines.append(f"\nℹ️ Без изменений ({len(unchanged)}):")
            for r in unchanged:
                lines.append(f"  • {r['file']}: {r['score_before']:.1f}")
        if skipped:
            lines.append(f"\n⚠️ Пропущено: {len(skipped)}")
        send_telegram("\n".join(lines))

if __name__ == "__main__":
    main()
