---
name: gemini-deep
description: "Use Gemini CLI (gemini-3.1-pro) for complex reasoning, architecture analysis, deep code review, and hard research questions. 1000 requests/day free. Use when the main model is not enough for the task complexity."
triggers:
  - deep analysis
  - architecture review
  - complex code review
  - deep think
  - gemini pro
  - think harder
  - analyze architecture
  - refactor large
  - "/deep"
  - "/think"
---

# Gemini Deep Thinking Skill

Uses Gemini CLI with `gemini-3.1-pro` — the most capable model available.
**1000 requests/day free** (via Google account auth).

## When to use

Use this skill (not the main model) when:
- Analyzing architecture of a large codebase
- Deep code review for security, performance, design issues
- Refactoring large/complex files
- Research that needs synthesis across many concepts
- Any task where you've already tried and the answer is insufficient

## Commands

### Architecture Analysis
```bash
# Analyze entire project structure
find /data/bot/openclaw-docker -name "*.json" -o -name "*.yaml" | head -20 | xargs cat | \
  gemini -m gemini-3.1-pro -p "Analyze the architecture of this OpenClaw bot. Identify: 1) Design patterns used 2) Potential bottlenecks 3) Missing components 4) Improvement opportunities"
```

### Deep Code Review
```bash
# Review a specific file
gemini -m gemini-3.1-pro -p "Perform a thorough code review. Check for: bugs, security issues, performance problems, and design flaws. Be specific with line references." \
  < /path/to/file.py
```

### Large File Refactoring
```bash
# Get refactoring plan first (don't output full file)
gemini -m gemini-3.1-pro -p "Analyze this code and provide a detailed refactoring plan following SOLID principles. List specific changes needed, do NOT output the full refactored code yet." \
  < /path/to/large_file.py
```

### Deep Research
```bash
# Complex research question
gemini -m gemini-3.1-pro -p "Research question: [QUESTION]. Provide: 1) Comprehensive answer 2) Trade-offs 3) Best practices 4) Specific recommendations for our setup"
```

### Fallback to Gemini 3 Flash (faster)
```bash
# For less complex but still above-average tasks
gemini -m gemini-3-flash -p "..." < file
```

## Output handling

Always pipe long output through a file to avoid truncation:
```bash
gemini -m gemini-3.1-pro -p "..." < input.txt > /tmp/gemini_output.txt
cat /tmp/gemini_output.txt
```

## Auth setup (one-time, DONE by user)
```bash
# Already done — user logged in via:
gemini auth login
```

## Limits
- gemini-3.1-pro: 1000 req/day via Google account
- gemini-3-flash: 1000 req/day via Google account  
- Resets at midnight Pacific time
