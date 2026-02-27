---
name: slidev
description: "Create presentations using Slidev. Generate slide decks from markdown, manage slides, and export to PDF/HTML."
triggers:
  - создай презентацию
  - slidev
  - презентация
  - make presentation
  - new slides
---

# Slidev — Presentation Builder

Create beautiful developer presentations using Markdown.

## Quick Start

### Create new presentation
```bash
mkdir -p /data/bot/openclaw-docker/slidev/presentations/$(date +%Y-%m-%d)
cd /data/bot/openclaw-docker/slidev/presentations/$(date +%Y-%m-%d)
slidev create my-presentation
```

### Run presentation locally
```bash
cd /data/bot/openclaw-docker/slidev/presentations/2026-02-27
docker exec slidev slidev
```

### Default slidev template
```markdown
---
theme: default
---

# Slide Title

- Point 1
- Point 2

---

## Next Slide

More content here
```

## Workflow

1. **Generate content** — create markdown with slide structure
2. **Create presentation** — use slidev CLI
3. **Preview** — open http://localhost:3030
4. **Export** — to PDF, PNG, or HTML

## Export commands
```bash
# PDF
slidev export

# HTML (static)
slidev build
```

## Environment

- URL: http://localhost:3030
- Presentations: /data/bot/openclaw-docker/slidev/presentations/

## Examples

### Create quick deck
```bash
# Quick deck from CLI
cd /data/bot/openclaw-docker/slidev
echo "# Hello\n\n- Point 1\n- Point 2" > deck.md
docker run --rm -v $(pwd):/slidev/app -p 3030:3030 ghcr.io/slidevjs/slidev deck.md
```
