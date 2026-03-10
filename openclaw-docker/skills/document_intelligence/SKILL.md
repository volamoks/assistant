---
name: document_intelligence
description: "Extract and search content from PDF, DOC, DOCX, RTF, XLSX, PPTX files stored in Obsidian vault via RAG. Files are auto-indexed nightly. Use obsidian_rag_search for retrieval."
triggers:
  - read pdf
  - read document
  - extract from docx
  - extract from doc
  - search in pdf
  - parse document
  - what does the document say
  - find in pdf
  - read doc file
---

# Document Intelligence via RAG

Binary documents (PDF, DOCX, RTF, XLSX, PPTX) in your Obsidian vault are
automatically indexed into ChromaDB alongside your markdown notes.

**Single unified search** — use the same RAG command for all content types:

```bash
bash /data/bot/openclaw-docker/scripts/obsidian_rag_search.sh "query" 5
```

## Manually re-index documents

Run after adding new PDFs/DOCX to the vault:

```bash
bash /data/bot/openclaw-docker/scripts/jobs/obsidian_reindex.sh
```

Or index documents only (skip markdown):

```bash
python3 /data/bot/openclaw-docker/scripts/ingest_docs.py
```

With options:
```bash
# Preview what will be indexed (no changes):
python3 /data/bot/openclaw-docker/scripts/ingest_docs.py --dry-run

# Force re-index all docs (ignore cache):
python3 /data/bot/openclaw-docker/scripts/ingest_docs.py --force
```

## Supported formats

| Format | Extension | Notes |
|---|---|---|
| PDF | `.pdf` | Text + tables (not scanned images) |
| Word | `.docx`, `.doc` | |
| RTF | `.rtf` | |
| Excel | `.xlsx` | Sheets → text |
| PowerPoint | `.pptx` | Slides → text |
| LibreOffice | `.odt` | |

## Where to put documents

Drop files anywhere in the vault — they will be found automatically:

```
/data/obsidian/vault/
  ├── Docs/          ← recommended folder for docs
  │   ├── api-spec.pdf
  │   ├── bank-srs.docx
  │   └── report.xlsx
  ├── Web Clips/     ← auto-created by web_clip.sh
  └── ...
```

## Notes

- Indexing uses **markitdown** (no server needed, ~100MB)
- Scanned PDFs (images) are NOT extracted — text-based only
- Nightly cron auto-reindexes at 03:00 Asia/Tashkent
- Incremental: only changed/new files are re-processed
