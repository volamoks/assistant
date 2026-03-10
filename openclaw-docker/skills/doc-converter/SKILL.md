---
name: doc-converter
description: "Convert .doc/.docx files to Markdown using catdoc (for .doc) or markitdown (for .docx). Use when user asks to read, convert, or extract text from Word documents."
triggers:
  - convert doc
  - read doc file
  - extract from doc
  - doc to markdown
  - конвертировать doc
  - прочитай doc файл
---

# Document Converter Skill

Converts Microsoft Word documents (.doc, .docx) to Markdown for reading and RAG indexing.

## Tools

| Format | Tool | Command |
|--------|------|---------|
| `.doc` (old) | `catdoc` | `catdoc file.doc > file.md` |
| `.docx` (new) | `markitdown` | `python3 -c "from markitdown import MarkItDown; md = MarkItDown(); print(md.convert('file.docx').text_content)"` |

## Usage

### Convert .doc file
```bash
catdoc "/path/to/file.doc" > "/path/to/file.md"
```

### Convert .docx file
```bash
python3 -c "
from markitdown import MarkItDown
md = MarkItDown()
result = md.convert('/path/to/file.docx')
print(result.text_content)
" > "/path/to/file.md"
```

### Re-index after conversion
```bash
bash /data/bot/openclaw-docker/scripts/jobs/obsidian_reindex.sh
```

## Workflow

1. Find .doc/.docx files in Obsidian vault
2. Convert to Markdown
3. Save alongside original
4. Trigger re-index for RAG search

## Location

Documents typically in:
- `/data/obsidian/Claw/Docs/`
- `/data/obsidian/Assets/Misc/`
- `/data/obsidian/Assets/Examples/`
