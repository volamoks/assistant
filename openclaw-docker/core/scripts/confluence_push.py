#!/usr/bin/env python3
"""
Confluence Push — Push Obsidian Markdown to Confluence (Live Edit Mode)

Uses: atlas_doc_format representation + ADF JSON
→ Confluence stores HTML with local-id attributes
→ Pages are indistinguishable from manually created live edit pages

Usage:
    python3 confluence_push.py --file "/path/to/note.md" --page-id "123456789"
    python3 confluence_push.py --file "/path/to/note.md" --space "LP" --title "Title" --create
    python3 confluence_push.py --file "/path/to/note.md" --space "LP" --title "Title"
      (creates if not exists, updates if exists)
"""
import argparse, os, sys, re, uuid, json as js

# ── Load env ──────────────────────────────────────────────────────────────────
ENV_FILE = '/data/bot/openclaw-docker/core/.env'
if os.path.exists(ENV_FILE):
    for line in open(ENV_FILE):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

URL   = os.environ.get('CONFLUENCE_URL', '')
EMAIL = os.environ.get('CONFLUENCE_EMAIL', '')
TOKEN = os.environ.get('CONFLUENCE_API_TOKEN', '')
if not URL or not EMAIL or not TOKEN:
    print("ERROR: Missing CONFLUENCE_* vars in", ENV_FILE); sys.exit(1)

import base64, requests
AUTH    = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json", "Accept": "application/json"}

# ── ID generation ──────────────────────────────────────────────────────────────
def uid():
    return uuid.uuid4().hex[:16]

# ── ADF Node builders ─────────────────────────────────────────────────────────
def text(text_str, marks=None):
    return {"type": "text", "text": text_str, "attrs": {"localId": uid()}, "marks": marks or []}

def paragraph(children=None):
    if children is None:
        children = [text("")]
    elif isinstance(children, str):
        children = [text(children)]
    return {"type": "paragraph", "attrs": {"localId": uid()}, "content": children}

def heading(level, text_str):
    return {"type": "heading", "attrs": {"level": level, "localId": uid()},
            "content": [text(text_str)]}

def bullet_list(items):
    return {"type": "bulletList", "attrs": {"localId": uid()},
            "content": [{"type": "listItem", "attrs": {"localId": uid()},
                         "content": [paragraph(item)]} for item in items if item.strip()]}

def ordered_list(items):
    return {"type": "orderedList", "attrs": {"localId": uid(), "startNumber": 1},
            "content": [{"type": "listItem", "attrs": {"localId": uid()},
                         "content": [paragraph(item)]} for item in items if item.strip()]}

def code_block(code_str, language=''):
    return {"type": "codeBlock", "attrs": {"language": language, "localId": uid()},
            "content": [text(code_str)]}

def table(rows):
    if not rows:
        return None
    def cell(text_str, is_header=False):
        tag = "tableHeader" if is_header else "tableCell"
        return {"type": tag, "attrs": {"localId": uid()},
                "content": [paragraph(text_str)]}
    def table_row(row_cells, is_header=False):
        return {"type": "tableRow", "attrs": {"localId": uid()},
                "content": [cell(c, is_header) for c in row_cells if str(c).strip()]}
    header = [c for c in rows[0] if str(c).strip()] if rows else []
    body   = [[c for c in r if str(c).strip()] for r in rows[1:]] if len(rows) > 1 else []
    rows_list = [table_row(header, True)] + [table_row(r, False) for r in body if r]
    return {"type": "table", "attrs": {"localId": uid()}, "content": rows_list} if rows_list else None

def hr():
    return {"type": "rule", "attrs": {"localId": uid()}}

# ── Inline mark parsing ───────────────────────────────────────────────────────
def parse_inline(text_str):
    """Parse inline marks and return list of ADF text nodes."""
    nodes = []
    remaining = text_str
    while remaining:
        # Code: `text`
        m = re.match(r'`([^`]+)`(.*)', remaining, re.DOTALL)
        if m:
            nodes.append(text(m.group(1), [{"type": "code"}])); remaining = m.group(2); continue
        # Bold: **text**
        m = re.match(r'\*\*([^*]+)\*\*(.*)', remaining)
        if m:
            nodes.append(text(m.group(1), [{"type": "strong"}])); remaining = m.group(2); continue
        # Italic: *text* (but not at start of list item)
        m = re.match(r'(?<!\*)\*([^*]+)\*(.*)', remaining)
        if m:
            nodes.append(text(m.group(1), [{"type": "em"}])); remaining = m.group(2); continue
        # Strikethrough: ~~text~~
        m = re.match(r'~~([^~]+)~~(.*)', remaining)
        if m:
            nodes.append(text(m.group(1), [{"type": "strikeThrough"}])); remaining = m.group(2); continue
        # Link: [text](url)
        m = re.match(r'\[([^\]]+)\]\(([^)]+)\)(.*)', remaining)
        if m:
            nodes.append(text(m.group(1), [{"type": "link", "attrs": {"href": m.group(2)}}])); remaining = m.group(3); continue
        # Collect remaining characters
        plain_end = min(len(remaining), 1)
        for i, ch in enumerate(remaining):
            if ch in '`*_~[': break
            plain_end = i + 1
        if plain_end > 0:
            nodes.append(text(remaining[:plain_end])); remaining = remaining[plain_end:]
        if remaining and remaining[0] not in '`*_~[':
            nodes.append(text(remaining[0])); remaining = remaining[1:]
        else:
            nodes.append(text(remaining[0])); remaining = remaining[1:]
    return nodes if nodes else [text('')]

# ── Markdown → ADF converter ─────────────────────────────────────────────────
def md_to_adf(md_text):
    """Convert Markdown text to ADF JSON (Confluence native format)."""
    doc_id = uid()
    lines = md_text.split('\n')
    doc_content = []
    i = 0

    # Flush helpers
    pending_ul, pending_ol, pending_table = [], [], False

    def flush_ul():
        nonlocal pending_ul
        if pending_ul:
            doc_content.append(bullet_list(pending_ul)); pending_ul = []

    def flush_ol():
        nonlocal pending_ol
        if pending_ol:
            doc_content.append(ordered_list(pending_ol)); pending_ol = []

    def flush_table():
        nonlocal pending_table
        if pending_table:
            t = table(pending_table)
            if t: doc_content.append(t)
            pending_table = False

    while i < len(lines):
        line = lines[i]; original_line = line

        # Code block fences
        if line.strip().startswith('```'):
            flush_ul(); flush_ol(); flush_table()
            lang = line.strip()[3:].strip().split()[0]
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].rstrip().endswith('```'):
                code_lines.append(lines[i]); i += 1
            if i < len(lines):
                code_lines.append(lines[i].rstrip().rstrip('`')); i += 1
            doc_content.append(code_block('\n'.join(code_lines), lang))
            continue

        # HR
        if re.match(r'^[-*_]{3,}\s*$', line.strip()):
            flush_ul(); flush_ol(); flush_table()
            doc_content.append(hr()); i += 1; continue

        # Table rows
        if '|' in line and not line.strip().startswith('|---'):
            cells = [c.strip() for c in line.split('|')]
            cells = [c for c in cells if c and not re.match(r'^[-: ]+$', c)]
            if cells:
                flush_ul(); flush_ol()
                pending_table = True
                pending_table_rows = getattr(md_to_adf, '_table_buf', [])
                pending_table_rows.append(cells)
                md_to_adf._table_buf = pending_table_rows
                i += 1; continue
            else:
                if hasattr(md_to_adf, '_table_buf') and md_to_adf._table_buf:
                    t = table(md_to_adf._table_buf)
                    if t: doc_content.append(t)
                    md_to_adf._table_buf = []
                pending_table = False

        # Close table on blank/non-table line
        if hasattr(md_to_adf, '_table_buf') and md_to_adf._table_buf and not ('|' in line):
            t = table(md_to_adf._table_buf)
            if t: doc_content.append(t)
            md_to_adf._table_buf = []

        # Headings
        hm = re.match(r'^(#{1,6})\s+(.+)$', line)
        if hm:
            flush_ul(); flush_ol(); flush_table()
            lvl = len(hm.group(1))
            doc_content.append(heading(lvl, hm.group(2).strip())); i += 1; continue

        # Unordered list
        lm = re.match(r'^[\*\-\+]\s+(.+)$', line)
        if lm:
            flush_ol(); flush_table()
            pending_ul.append(lm.group(1)); i += 1; continue
        else:
            flush_ul()

        # Ordered list
        om = re.match(r'^\d+\.\s+(.+)$', line)
        if om:
            flush_ul(); flush_table()
            pending_ol.append(om.group(1)); i += 1; continue
        else:
            flush_ol()

        # Blockquote
        bm = re.match(r'^\>\s*(.*)$', line)
        if bm:
            flush_ul(); flush_ol(); flush_table()
            content_parts = [bm.group(1)]
            i += 1
            while i < len(lines) and re.match(r'^\>\s*(.*)$', lines[i]):
                content_parts.append(re.match(r'^\>\s*(.*)$', lines[i]).group(1))
                i += 1
            block_nodes = []
            for part in content_parts:
                if part.strip():
                    block_nodes.extend(parse_inline(part))
            if block_nodes:
                doc_content.append({"type": "blockquote", "attrs": {"localId": uid()},
                                     "content": [{"type": "paragraph", "attrs": {"localId": uid()},
                                                  "content": block_nodes}]})
            continue

        # Paragraphs (non-empty lines)
        stripped = line.rstrip()
        if stripped:
            doc_content.extend(parse_inline(stripped))
            i += 1; continue

        i += 1

    # Flush remaining
    flush_ul(); flush_ol()
    if hasattr(md_to_adf, '_table_buf') and md_to_adf._table_buf:
        t = table(md_to_adf._table_buf)
        if t: doc_content.append(t)
        md_to_adf._table_buf = []

    return {"type": "doc", "version": 1, "attrs": {"localId": doc_id}, "content": doc_content}

# ── API helpers ────────────────────────────────────────────────────────────────
def get_page(page_id=None, space=None, title=None):
    if page_id:
        r = requests.get(f"{URL}/rest/api/content/{page_id}?expand=version",
                         headers=HEADERS, timeout=15)
        return r.json() if r.status_code == 200 else None
    if space and title:
        r = requests.get(f"{URL}/rest/api/content",
                         params={"spaceKey": space, "title": title, "expand": "version"},
                         headers=HEADERS, timeout=15)
        results = r.json().get('results', [])
        return results[0] if results else None
    return None

def set_content_appearance(pid, ver):
    """Set content-appearance-draft property for live edit mode."""
    requests.post(f"{URL}/rest/api/content/{pid}/property",
                 headers=HEADERS,
                 json={"key": "content-appearance-draft", "value": "max",
                       "version": {"number": ver}},
                 timeout=10)

def push(page_id, adf_json, title):
    page = get_page(page_id)
    if not page:
        print(f"ERROR: page {page_id} not found"); sys.exit(1)
    ver = page.get('version', {}).get('number', 1)
    adf_str = js.dumps(adf_json, ensure_ascii=False)
    payload = {
        "version": {"number": ver + 1},
        "title": title,
        "type": "page",
        "body": {
            "editor": {
                "value": adf_str,
                "representation": "atlas_doc_format"
            }
        }
    }
    r = requests.put(f"{URL}/rest/api/content/{page_id}", headers=HEADERS, json=payload, timeout=30)
    if r.status_code in (200, 201):
        new_ver = r.json().get('version', {}).get('number', '?')
        print(f"✅ Updated! v{new_ver} ({len(adf_str)} ADF chars)")
        set_content_appearance(page_id, new_ver)
    else:
        print(f"❌ {r.status_code}: {r.text[:300]}"); sys.exit(1)

def create(space, title, adf_json, ancestor_id=None):
    adf_str = js.dumps(adf_json, ensure_ascii=False)
    ancestors = [{"id": ancestor_id}] if ancestor_id else []
    payload = {
        "type": "page", "title": title, "space": {"key": space},
        "ancestors": ancestors,
        "body": {
            "editor": {
                "value": adf_str,
                "representation": "atlas_doc_format"
            }
        }
    }
    r = requests.post(f"{URL}/rest/api/content", headers=HEADERS, json=payload, timeout=30)
    if r.status_code in (200, 201):
        d = r.json()
        pid = d.get('id', '?')
        new_ver = d.get('version', {}).get('number', '?')
        print(f"✅ Created! ID: {pid}, v{new_ver} ({len(adf_str)} ADF chars)")
        set_content_appearance(pid, new_ver)
        return pid
    else:
        print(f"❌ {r.status_code}: {r.text[:300]}"); sys.exit(1)

# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Push Markdown to Confluence (Live Edit)')
    p.add_argument('--file',    required=True)
    p.add_argument('--page-id')
    p.add_argument('--space')
    p.add_argument('--title')
    p.add_argument('--create',  action='store_true')
    p.add_argument('--parent-id', help='Parent page ID for hierarchy')
    args = p.parse_args()

    if not os.path.exists(args.file):
        print(f"File not found: {args.file}"); sys.exit(1)

    with open(args.file, encoding='utf-8') as f:
        md_text = f.read()
    if not md_text.strip():
        print("Empty file"); sys.exit(1)

    # Extract title from first H1 or first line
    hm = re.search(r'^#\s+(.+)$', md_text, re.MULTILINE)
    title = args.title or (hm.group(1).strip() if hm else os.path.basename(args.file))

    print(f"📄 {args.file}")
    print(f"📝 Title: {title}")
    print(f"🔄 Converting Markdown → ADF...")

    # Convert
    adf = md_to_adf(md_text)
    node_count = len(adf.get('content', []))
    adf_str = js.dumps(adf, ensure_ascii=False)
    print(f"✅ ADF: {node_count} nodes, {len(adf_str)} chars")

    # Find or validate target
    page_id = args.page_id
    if not page_id:
        if args.space and args.title:
            pg = get_page(space=args.space, title=args.title)
            if pg:
                page_id = pg.get('id')
                print(f"🔍 Found existing: {page_id} (v{pg.get('version',{}).get('number','?')})")
        if not page_id and not args.create:
            print("⚠️  Page not found. Use --create to create it.")
            sys.exit(1)

    # Push or create
    if page_id:
        push(page_id, adf, title)
    else:
        pid = create(args.space, title, adf, args.parent_id)
        print(f"🚀 Page ready: {URL}/wiki/spaces/LP/pages/{pid}")
