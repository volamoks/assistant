# План миграции Obsidian на PARA-структуру + Оптимизации

## Содержание
1. [Анализ текущего состояния](#1-анализ-текущего-состояния)
2. [Целевая PARA-структура](#2-целевая-пара-структура)
3. [Маппинг переноса данных](#3-маппинг-переноса-данных)
4. [Скрипт миграции](#4-скрипт-миграции)
5. [Обновление скриптов](#5-обновление-скриптов)
6. [Оптимизации](#6-оптимизации)
7. [План отката](#7-план-отката)
8. [Пошаговый план выполнения](#8-пошаговый-план-выполнения)

---

## 1. Анализ текущего состояния

### 1.1 Текущая структура
```
My Docs/
├── To claw/
│   ├── possible_improvements/
│   │   ├── 00-index.md
│   │   └── 22-tts-stt-voice.md
│   ├── Bot/
│   │   ├── obsidian.db          # SQLite индекс
│   │   ├── today-session.md     # Лог сессии
│   │   ├── crash-configs/       # Конфиги крашей
│   │   └── lessons-learned.md   # Уроки
│   └── Web Clips/               # Веб-клипы
└── Personal/
    └── CV/                       # Резюме
```

### 1.2 Существующие скрипты и их пути

| Скрипт | Текущий путь | Тип пути |
|--------|--------------|----------|
| `obsidian_index.py` | `/Users/.../My Docs/To claw/Bot/obsidian.db` | Host |
| `obsidian_search.sh` | `/data/obsidian` | Docker |
| `obsidian_rag_search.sh` | ChromaDB коллекция | Docker |
| `obsidian_reindex.sh` | `/data/obsidian/To claw` | Docker |
| `ingest_docs.py` | `/data/obsidian/To claw` | Docker |
| `ingest.js` | `/data/obsidian` | Docker |
| `web_clip.sh` | `/data/obsidian/To claw` | Docker |
| `crash_analyzer.sh` | `/data/obsidian/To claw/Bot/` | Docker |
| `morning_task_briefing.sh` | `/data/obsidian/To claw` | Docker |
| `intraday_snapshot.sh` | `/data/obsidian/To claw/Bot/today-session.md` | Docker |
| `vault_gardening.sh` | `/data/obsidian/To claw` | Docker |
| `morning_system_status.sh` | `/data/obsidian/To claw/Bot/lessons-learned.md` | Docker |

---

## 2. Целевая PARA-структура

### 2.1 Структура папок

```
My Docs/
├── 00_Meta/                      # Системные файлы
│   ├── Bot/                      # Файлы бота
│   │   ├── obsidian.db           # ← To claw/Bot/obsidian.db
│   │   ├── today-session.md      # ← To claw/Bot/today-session.md
│   │   ├── lessons-learned.md    # ← To claw/Bot/lessons-learned.md
│   │   ├── crash-configs/        # ← To claw/Bot/crash-configs/
│   │   └── index.log             # Логи индексации
│   └── Templates/                # Шаблоны заметок
│       ├── project_template.md
│       ├── area_template.md
│       └── daily_note_template.md
│
├── 01_Inbox/                     # Новые заметки (входящие)
│   └── .gitkeep
│
├── 02_Projects/                  # Активные проекты
│   └── .gitkeep
│
├── 03_Areas/                     # Области ответственности
│   ├── Career/                   # ← Personal/CV/
│   │   ├── Resume/
│   │   │   ├── Abror_Komalov_FINAL.md
│   │   │   └── Abror_Komalov_FINAL_2026.md
│   │   └── Cover_Letters/
│   ├── Bot_Improvements/         # ← To claw/possible_improvements/
│   │   ├── 00-index.md
│   │   └── 22-tts-stt-voice.md
│   └── Web_Clips/                # ← To claw/Web Clips/
│
├── 04_Resources/                 # Справочники и ресурсы
│   ├── Documentation/
│   ├── Cheat_Sheets/
│   └── References/
│
└── 05_Archive/                   # Архив
    ├── 2024/
    ├── 2025/
    └── _Legacy_Symlinks/         # Symlink'и для обратной совместимости
        ├── To claw → ../00_Meta/Bot/
        └── Personal/CV → ../03_Areas/Career/
```

### 2.2 Приоритеты индексации (Smart Indexing)

| Приоритет | Папка | Описание |
|-----------|-------|----------|
| 🔴 High | `02_Projects/` | Активные проекты — всегда актуально |
| 🔴 High | `03_Areas/` | Области ответственности — часто используется |
| 🟡 Medium | `01_Inbox/` | Входящие — временно |
| 🟡 Medium | `04_Resources/` | Справочники — редко меняются |
| 🟢 Low | `00_Meta/` | Системные — только при изменениях |
| ⚪ Skip | `05_Archive/` | Архив — не индексируется по умолчанию |

---

## 3. Маппинг переноса данных

### 3.1 Файлы для переноса

| Источник (старый путь) | Назначение (новый путь) | Тип операции |
|------------------------|------------------------|--------------|
| `To claw/Bot/obsidian.db` | `00_Meta/Bot/obsidian.db` | Копировать |
| `To claw/Bot/today-session.md` | `00_Meta/Bot/today-session.md` | Копировать |
| `To claw/Bot/lessons-learned.md` | `00_Meta/Bot/lessons-learned.md` | Копировать |
| `To claw/Bot/crash-configs/` | `00_Meta/Bot/crash-configs/` | Копировать рекурсивно |
| `To claw/possible_improvements/` | `03_Areas/Bot_Improvements/` | Копировать рекурсивно |
| `To claw/Web Clips/` | `03_Areas/Web_Clips/` | Копировать рекурсивно |
| `Personal/CV/` | `03_Areas/Career/` | Копировать рекурсивно |

### 3.2 Symlink'и для обратной совместимости

| Symlink путь | Указывает на | Назначение |
|--------------|--------------|------------|
| `05_Archive/_Legacy_Symlinks/To claw/Bot/obsidian.db` | `00_Meta/Bot/obsidian.db` | Обратная совместимость со старыми скриптами |
| `05_Archive/_Legacy_Symlinks/To claw/Bot/today-session.md` | `00_Meta/Bot/today-session.md` | Логи сессий |
| `05_Archive/_Legacy_Symlinks/To claw/Bot/lessons-learned.md` | `00_Meta/Bot/lessons-learned.md` | Уроки |
| `05_Archive/_Legacy_Symlinks/To claw/Bot/crash-configs` | `00_Meta/Bot/crash-configs` | Конфиги крашей |
| `05_Archive/_Legacy_Symlinks/To claw/possible_improvements` | `03_Areas/Bot_Improvements` | Улучшения |
| `05_Archive/_Legacy_Symlinks/Personal/CV` | `03_Areas/Career` | Резюме |

---

## 4. Скрипт миграции

### 4.1 `migrate_obsidian_structure.sh`

```bash
#!/bin/bash
# migrate_obsidian_structure.sh — Миграция Obsidian на PARA-структуру
# Usage: ./migrate_obsidian_structure.sh [--dry-run] [--verbose]

set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────
VAULT_HOST="${OBSIDIAN_VAULT_HOST:-/Users/abror_mac_mini/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs}"
DRY_RUN=false
VERBOSE=false
LOG_FILE="${VAULT_HOST}/00_Meta/Bot/migration_$(date +%Y%m%d_%H%M%S).log"

# ─── PARA Structure Definition ───────────────────────────────────────────────
declare -A MIGRATION_MAP=(
    ["To claw/Bot/obsidian.db"]="00_Meta/Bot/obsidian.db"
    ["To claw/Bot/today-session.md"]="00_Meta/Bot/today-session.md"
    ["To claw/Bot/lessons-learned.md"]="00_Meta/Bot/lessons-learned.md"
    ["To claw/possible_improvements"]="03_Areas/Bot_Improvements"
    ["Personal/CV"]="03_Areas/Career"
)

declare -A SYMLINK_MAP=(
    ["05_Archive/_Legacy_Symlinks/To claw/Bot/obsidian.db"]="00_Meta/Bot/obsidian.db"
    ["05_Archive/_Legacy_Symlinks/To claw/Bot/today-session.md"]="00_Meta/Bot/today-session.md"
    ["05_Archive/_Legacy_Symlinks/To claw/Bot/lessons-learned.md"]="00_Meta/Bot/lessons-learned.md"
    ["05_Archive/_Legacy_Symlinks/To claw/possible_improvements"]="03_Areas/Bot_Improvements"
    ["05_Archive/_Legacy_Symlinks/Personal/CV"]="03_Areas/Career"
)

# ─── Functions ───────────────────────────────────────────────────────────────

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    [[ "$DRY_RUN" == false ]] && echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

log_verbose() {
    [[ "$VERBOSE" == true ]] && log "$1"
}

error() {
    log "❌ ERROR: $1" >&2
    exit 1
}

# Проверка существования исходного файла
check_source() {
    local src="$1"
    if [[ ! -e "$VAULT_HOST/$src" ]]; then
        error "Source not found: $src"
    fi
}

# Копирование файла/директории
copy_item() {
    local src="$1"
    local dst="$2"
    local src_path="$VAULT_HOST/$src"
    local dst_path="$VAULT_HOST/$dst"
    
    # Создаём директорию назначения
    local dst_dir=$(dirname "$dst_path")
    
    if [[ "$DRY_RUN" == true ]]; then
        log "[DRY-RUN] Would copy: $src → $dst"
        return 0
    fi
    
    mkdir -p "$dst_dir"
    
    if [[ -d "$src_path" ]]; then
        cp -R "$src_path" "$dst_path"
        log "📁 Copied dir:  $src → $dst"
    else
        cp "$src_path" "$dst_path"
        log "📄 Copied file: $src → $dst"
    fi
}

# Создание symlink
create_symlink() {
    local link="$1"
    local target="$2"
    local link_path="$VAULT_HOST/$link"
    local target_path="$VAULT_HOST/$target"
    local rel_target=$(realpath --relative-to="$(dirname "$link_path")" "$target_path" 2>/dev/null || echo "$target_path")
    
    if [[ "$DRY_RUN" == true ]]; then
        log "[DRY-RUN] Would create symlink: $link → $target"
        return 0
    fi
    
    mkdir -p "$(dirname "$link_path")"
    ln -sfn "$rel_target" "$link_path"
    log "🔗 Created symlink: $link → $target"
}

# Создание структуры директорий
create_directories() {
    local dirs=(
        "00_Meta/Bot"
        "00_Meta/Templates"
        "01_Inbox"
        "02_Projects"
        "03_Areas/Career"
        "03_Areas/Bot_Improvements"
        "03_Areas/Web_Clips"
        "04_Resources/Documentation"
        "04_Resources/Cheat_Sheets"
        "04_Resources/References"
        "05_Archive/_Legacy_Symlinks/To claw/Bot"
        "05_Archive/_Legacy_Symlinks/Personal"
    )
    
    for dir in "${dirs[@]}"; do
        local full_path="$VAULT_HOST/$dir"
        if [[ "$DRY_RUN" == true ]]; then
            log "[DRY-RUN] Would create dir: $dir"
        else
            mkdir -p "$full_path"
            log_verbose "📂 Created dir: $dir"
        fi
    done
}

# Создание README файлов
create_readmes() {
    local readmes=(
        "01_Inbox/README.md:Входящие заметки. Всё новое попадает сюда первым делом."
        "02_Projects/README.md:Активные проекты с чёткими сроками и результатами."
        "03_Areas/README.md:Области ответственности — постоянные направления деятельности."
        "04_Resources/README.md:Справочники, шпаргалки, полезные материалы."
        "05_Archive/README.md:Архив завершённых проектов и устаревших материалов."
    )
    
    for item in "${readmes[@]}"; do
        local file="${item%%:*}"
        local desc="${item##*:}"
        local full_path="$VAULT_HOST/$file"
        
        if [[ "$DRY_RUN" == true ]]; then
            log "[DRY-RUN] Would create README: $file"
        else
            cat > "$full_path" << EOF
# $(basename "$(dirname "$full_path")")

$desc

## Структура

\`\`\`
$(tree -L 1 "$(dirname "$full_path")" 2>/dev/null || echo "[директория пуста]")
\`\`\`

---
*Generated: $(date '+%Y-%m-%d %H:%M:%S')*
EOF
            log "📝 Created README: $file"
        fi
    done
}

# Валидация миграции
validate_migration() {
    log "🔍 Validating migration..."
    local errors=0
    
    for src in "${!MIGRATION_MAP[@]}"; do
        local dst="${MIGRATION_MAP[$src]}"
        if [[ ! -e "$VAULT_HOST/$dst" ]]; then
            log "❌ Missing: $dst"
            ((errors++))
        else
            log_verbose "✅ Verified: $dst"
        fi
    done
    
    if [[ $errors -gt 0 ]]; then
        error "Validation failed: $errors items missing"
    fi
    
    log "✅ Validation passed"
}

# Создание rollback скрипта
create_rollback_script() {
    local rollback_script="$VAULT_HOST/00_Meta/Bot/rollback_migration_$(date +%Y%m%d_%H%M%S).sh"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "[DRY-RUN] Would create rollback script"
        return 0
    fi
    
    cat > "$rollback_script" << 'ROLLBACK_EOF'
#!/bin/bash
# Rollback script for Obsidian migration
# Generated: $(date)

VAULT_HOST="${OBSIDIAN_VAULT_HOST:-/Users/abror_mac_mini/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs}"
echo "Rolling back migration..."

# Remove symlinks
find "$VAULT_HOST/05_Archive/_Legacy_Symlinks" -type l -delete 2>/dev/null || true

# Note: Copied files are NOT automatically deleted for safety
# Manual cleanup required:
echo "Manual cleanup needed:"
echo "  - Remove: 00_Meta/"
echo "  - Remove: 01_Inbox/"
echo "  - Remove: 02_Projects/"
echo "  - Remove: 03_Areas/"
echo "  - Remove: 04_Resources/"
echo "  - Remove: 05_Archive/"
echo ""
echo "Original files in 'To claw/' and 'Personal/' are preserved."
ROLLBACK_EOF

    chmod +x "$rollback_script"
    log "🔄 Created rollback script: $rollback_script"
}

# ─── Main ────────────────────────────────────────────────────────────────────

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run) DRY_RUN=true; shift ;;
            --verbose) VERBOSE=true; shift ;;
            -h|--help)
                echo "Usage: $0 [--dry-run] [--verbose]"
                echo "  --dry-run   Show what would be done without making changes"
                echo "  --verbose   Show detailed output"
                exit 0
                ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done
    
    log "🚀 Starting Obsidian migration${DRY_RUN:+ (DRY-RUN mode)}"
    log "📂 Vault: $VAULT_HOST"
    
    # Step 1: Create directory structure
    log "📂 Step 1: Creating directory structure..."
    create_directories
    
    # Step 2: Copy files
    log "📋 Step 2: Copying files..."
    for src in "${!MIGRATION_MAP[@]}"; do
        check_source "$src"
        copy_item "$src" "${MIGRATION_MAP[$src]}"
    done
    
    # Step 3: Create symlinks
    log "🔗 Step 3: Creating symlinks..."
    for link in "${!SYMLINK_MAP[@]}"; do
        create_symlink "$link" "${SYMLINK_MAP[$link]}"
    done
    
    # Step 4: Create READMEs
    log "📝 Step 4: Creating README files..."
    create_readmes
    
    # Step 5: Create rollback script
    log "🔄 Step 5: Creating rollback script..."
    create_rollback_script
    
    # Step 6: Validation (skip in dry-run)
    if [[ "$DRY_RUN" == false ]]; then
        log "🔍 Step 6: Validating migration..."
        validate_migration
    else
        log "[DRY-RUN] Skipping validation"
    fi
    
    log "✅ Migration completed successfully${DRY_RUN:+ (DRY-RUN mode)}"
    
    if [[ "$DRY_RUN" == false ]]; then
        log "📋 Next steps:"
        log "  1. Update scripts with new paths (see Section 5)"
        log "  2. Test search functionality"
        log "  3. Update cron jobs"
        log "  4. After verification, remove legacy symlinks from 05_Archive/_Legacy_Symlinks/"
    fi
}

main "$@"
```

---

## 5. Обновление скриптов

### 5.1 Список файлов для обновления

| Файл | Изменения | Приоритет |
|------|-----------|-----------|
| `openclaw-docker/scripts/obsidian_index.py` | Обновить `VAULT_HOST`, `DB_DEFAULT` | 🔴 Critical |
| `openclaw-docker/scripts/obsidian_search.sh` | Обновить `VAULT` по умолчанию | 🔴 Critical |
| `openclaw-docker/scripts/obsidian_rag_search.sh` | Добавить приоритеты папок | 🟡 Medium |
| `openclaw-docker/scripts/jobs/obsidian_reindex.sh` | Обновить `VAULT_PATH` | 🔴 Critical |
| `openclaw-docker/scripts/ingest_docs.py` | Обновить `VAULT_PATH`, добавить фильтры | 🔴 Critical |
| `openclaw-docker/skills/obsidian_search/ingest.js` | Обновить `VAULT_PATH` | 🔴 Critical |
| `openclaw-docker/scripts/jobs/morning_task_briefing.sh` | Обновить `VAULT_PATH` | 🟡 Medium |
| `openclaw-docker/scripts/jobs/intraday_snapshot.sh` | Обновить `VAULT_PATH` и путь к файлу | 🔴 Critical |
| `openclaw-docker/scripts/jobs/vault_gardening.sh` | Обновить `VAULT_PATH` | 🟡 Medium |
| `openclaw-docker/scripts/jobs/morning_system_status.sh` | Обновить путь к `lessons-learned.md` | 🟡 Medium |
| `openclaw-docker/scripts/web_clip.sh` | Обновить `VAULT_PATH` и `CLIPS_DIR` | 🟡 Medium |
| `openclaw-docker/scripts/crash_analyzer.sh` | Обновить `CRASH_DIR`, `LESSONS_FILE` | 🔴 Critical |
| `openclaw-docker/watchdog.sh` | Обновить `OBSIDIAN_DIR` | 🟡 Medium |
| `openclaw-docker/recover.sh` | Обновить `OBSIDIAN_DIR` | 🟡 Medium |

### 5.2 Новые пути (Docker-контейнер)

```bash
# Было
OBSIDIAN_VAULT_PATH=/data/obsidian/To claw

# Стало
OBSIDIAN_VAULT_PATH=/data/obsidian
OBSIDIAN_META_PATH=/data/obsidian/00_Meta/Bot
OBSIDIAN_AREAS_PATH=/data/obsidian/03_Areas
OBSIDIAN_PROJECTS_PATH=/data/obsidian/02_Projects
OBSIDIAN_INBOX_PATH=/data/obsidian/01_Inbox
OBSIDIAN_ARCHIVE_PATH=/data/obsidian/05_Archive
```

### 5.3 Новые пути (Host)

```python
# obsidian_index.py
VAULT_HOST = Path("/Users/abror_mac_mini/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs")
DB_DEFAULT = VAULT_HOST / "00_Meta" / "Bot" / "obsidian.db"
```

---

## 6. Оптимизации

### 6.1 Smart Indexing (Приоритетная индексация)

Создать файл `openclaw-docker/scripts/jobs/smart_reindex.sh`:

```bash
#!/bin/bash
# smart_reindex.sh — Приоритетная индексация по PARA-структуре

VAULT_BASE="${OBSIDIAN_VAULT_PATH:-/data/obsidian}"
CHROMA_HOST="${CHROMA_HOST:-http://chromadb:8000}"
OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"

# Priority 1: Projects (каждые 30 мин)
echo "🔴 Indexing 02_Projects (High priority)..."
PRIORITY_PATHS=("$VAULT_BASE/02_Projects" "$VAULT_BASE/03_Areas")

# Priority 2: Inbox (каждый час)
echo "🟡 Indexing 01_Inbox (Medium priority)..."

# Priority 3: Archive (раз в день, ночью)
echo "⚪ Skipping 05_Archive (Low priority)..."
```

### 6.2 Content Filtering

Добавить в `obsidian_index.py`:

```python
# Исключения из индексации
EXCLUDE_PATTERNS = [
    "*.tmp",
    "*.log",
    ".git/*",
    "05_Archive/*",  # Skip archive by default
    "*.pdf",  # Binary files handled by ingest_docs.py
]

MAX_FILE_SIZE_MB = 10

def should_index(file_path: Path) -> bool:
    """Check if file should be indexed based on rules."""
    # Size check
    if file_path.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False
    
    # Pattern check
    for pattern in EXCLUDE_PATTERNS:
        if file_path.match(pattern):
            return False
    
    return True
```

### 6.3 Hierarchical Search

Создать `openclaw-docker/scripts/obsidian_smart_search.sh`:

```bash
#!/bin/bash
# obsidian_smart_search.sh — Двухуровневый поиск
# L1: SQLite FTS5 (быстро)
# L2: ChromaDB RAG (семантический)

QUERY="$1"
LIMIT="${2:-3}"

# Step 1: Try SQLite first (fast)
SQLITE_RESULTS=$(python3 /data/bot/openclaw-docker/scripts/obsidian_index.py --search "$QUERY" --limit "$LIMIT" 2>/dev/null)

if [[ -n "$SQLITE_RESULTS" ]] && [[ "$SQLITE_RESULTS" != "No results"* ]]; then
    echo "🔍 Fast search results (SQLite):"
    echo "$SQLITE_RESULTS"
    exit 0
fi

# Step 2: Fallback to RAG (slower but semantic)
echo "🔍 No exact matches. Trying semantic search (RAG)..."
/data/bot/openclaw-docker/scripts/obsidian_rag_search.sh "$QUERY" "$LIMIT"
```

### 6.4 Auto-Archiving

Создать `openclaw-docker/scripts/jobs/auto_archive.sh`:

```bash
#!/bin/bash
# auto_archive.sh — Автоматическая архивация старых заметок

VAULT_BASE="${OBSIDIAN_VAULT_PATH:-/data/obsidian}"
ARCHIVE_AGE_DAYS=90
ARCHIVE_DEST="$VAULT_BASE/05_Archive/$(date +%Y)"

# Find old files in Inbox
find "$VAULT_BASE/01_Inbox" -name "*.md" -type f -mtime +$ARCHIVE_AGE_DAYS | while read -r file; do
    filename=$(basename "$file")
    echo "Archiving: $filename"
    mkdir -p "$ARCHIVE_DEST/Inbox"
    mv "$file" "$ARCHIVE_DEST/Inbox/"
done

# Find completed projects
# (логика определения "completed" — по наличию тега #completed или статуса в YAML)
```

### 6.5 Token Optimization

Обновить `ingest_docs.py`:

```python
# Smart chunking с сохранением контекста
def smart_chunk(text: str, source: str, chunk_size: int = 800) -> list[dict]:
    """Chunk text while preserving headers context."""
    chunks = []
    lines = text.split('\n')
    current_chunk = []
    current_headers = []  # Stack of current headers
    chunk_idx = 0
    
    for line in lines:
        # Track headers
        if line.startswith('#'):
            # Save current chunk if it has content
            if current_chunk:
                chunk_text = '\n'.join(current_headers + current_chunk)
                chunks.append(create_chunk(chunk_text, source, chunk_idx))
                chunk_idx += 1
                current_chunk = []
            
            # Update header stack
            level = len(line) - len(line.lstrip('#'))
            current_headers = current_headers[:level-1] + [line]
        else:
            current_chunk.append(line)
            
            # Check chunk size
            if len('\n'.join(current_chunk)) > chunk_size:
                chunk_text = '\n'.join(current_headers + current_chunk)
                chunks.append(create_chunk(chunk_text, source, chunk_idx))
                chunk_idx += 1
                current_chunk = []
    
    # Don't forget last chunk
    if current_chunk:
        chunk_text = '\n'.join(current_headers + current_chunk)
        chunks.append(create_chunk(chunk_text, source, chunk_idx))
    
    return chunks
```

---

## 7. План отката (Rollback)

### 7.1 Автоматический rollback скрипт

Создаётся автоматически при миграции: `00_Meta/Bot/rollback_migration_*.sh`

### 7.2 Ручной откат

```bash
#!/bin/bash
# manual_rollback.sh

VAULT_HOST="/Users/abror_mac_mini/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs"

echo "=== Manual Rollback ==="

# 1. Stop cron jobs
echo "Stopping cron jobs..."
# (disable cron temporarily)

# 2. Remove symlinks
echo "Removing symlinks..."
find "$VAULT_HOST/05_Archive/_Legacy_Symlinks" -type l -delete 2>/dev/null || true

# 3. Backup new structure
echo "Backing up new structure..."
tar -czf "$HOME/obsidian_para_backup_$(date +%Y%m%d).tar.gz" \
    "$VAULT_HOST/00_Meta" \
    "$VAULT_HOST/01_Inbox" \
    "$VAULT_HOST/02_Projects" \
    "$VAULT_HOST/03_Areas" \
    "$VAULT_HOST/04_Resources" \
    "$VAULT_HOST/05_Archive" 2>/dev/null || true

# 4. Restore old scripts
echo "Restoring script paths..."
# (git checkout or restore from backup)

# 5. Verify old structure
echo "Verifying old structure..."
ls -la "$VAULT_HOST/To claw/Bot/"

echo "Rollback complete. Original data preserved in:"
echo "  - To claw/"
echo "  - Personal/"
```

### 7.3 Контрольные точки для отката

| Этап | Действие | Точка отката |
|------|----------|---------------|
| 1 | dry-run миграции | Любое время |
| 2 | Копирование файлов | Удаление новых папок |
| 3 | Создание symlink | Удаление symlink, данные не затронуты |
| 4 | Обновление скриптов | git restore или backup |
| 5 | Re-index | Переиндексация на старые пути |

---

## 8. Пошаговый план выполнения

### Фаза 1: Подготовка (День 0)

- [ ] **1.1** Создать backup текущего vault
  ```bash
  tar -czf ~/obsidian_backup_$(date +%Y%m%d).tar.gz \
      "/Users/abror_mac_mini/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs"
  ```
  **Проверка:** `ls -lh ~/obsidian_backup_*.tar.gz`

- [ ] **1.2** Остановить cron jobs
  ```bash
  # Временно отключить reindex
  crontab -l > ~/crontab.backup
  # Comment out obsidian reindex jobs
  ```
  **Проверка:** `crontab -l | grep -c obsidian` → 0

- [ ] **1.3** Закрыть Obsidian.app (чтобы не было конфликтов)
  **Проверка:** `pgrep -i obsidian` → пусто

### Фаза 2: Миграция структуры (День 0, вечер)

- [ ] **2.1** Запустить dry-run
  ```bash
  ./migrate_obsidian_structure.sh --dry-run --verbose
  ```
  **Проверка:** Просмотреть лог, убедиться в корректности путей

- [ ] **2.2** Выполнить миграцию
  ```bash
  ./migrate_obsidian_structure.sh --verbose
  ```
  **Проверка:**
  - `ls -la "My Docs/00_Meta/Bot/"` — файлы на месте
  - `ls -la "My Docs/03_Areas/Career/"` — CV перенесено
  - `ls -la "My Docs/05_Archive/_Legacy_Symlinks/"` — symlink созданы

- [ ] **2.3** Проверить symlink'и
  ```bash
  ls -la "My Docs/05_Archive/_Legacy_Symlinks/To claw/Bot/"
  ```
  **Проверка:** Ссылки не битые (не красные)

### Фаза 3: Обновление скриптов (День 1)

- [ ] **3.1** Обновить `obsidian_index.py`
  - Изменить `DB_DEFAULT`
  - Добавить `EXCLUDE_PATTERNS`
  **Проверка:** `python3 obsidian_index.py --help`

- [ ] **3.2** Обновить `obsidian_reindex.sh`
  - Изменить `VAULT_PATH`
  **Проверка:** `bash -n obsidian_reindex.sh`

- [ ] **3.3** Обновить `ingest_docs.py` и `ingest.js`
  - Изменить `VAULT_PATH`
  **Проверка:** Синтаксическая проверка

- [ ] **3.4** Обновить job-скрипты
  - `morning_task_briefing.sh`
  - `intraday_snapshot.sh`
  - `vault_gardening.sh`
  - `morning_system_status.sh`
  **Проверка:** `bash -n` для каждого

- [ ] **3.5** Обновить `crash_analyzer.sh`, `web_clip.sh`
  **Проверка:** `bash -n`

- [ ] **3.6** Обновить `watchdog.sh`, `recover.sh`
  **Проверка:** `bash -n`

### Фаза 4: Тестирование (День 1)

- [ ] **4.1** Тест индексации
  ```bash
  python3 obsidian_index.py --force
  ```
  **Проверка:** Без ошибок, obsidian.db создан в новом месте

- [ ] **4.2** Тест поиска SQLite
  ```bash
  python3 obsidian_index.py --search "test" --limit 3
  ```
  **Проверка:** Результаты из новых путей

- [ ] **4.3** Тест поиска bash
  ```bash
  ./obsidian_search.sh "test" --limit 3
  ```
  **Проверка:** Результаты корректны

- [ ] **4.4** Тест RAG search (если Ollama/ChromaDB работают)
  ```bash
  ./obsidian_rag_search.sh "test query" 3
  ```
  **Проверка:** Без ошибок

- [ ] **4.5** Тест web_clip
  ```bash
  ./web_clip.sh "https://example.com" 1000 true
  ```
  **Проверка:** Файл создан в `03_Areas/Web_Clips/`

- [ ] **4.6** Тест crash_analyzer
  ```bash
  ./crash_analyzer.sh
  ```
  **Проверка:** Не падает, ищет в правильной директории

### Фаза 5: Запуск в production (День 2)

- [ ] **5.1** Восстановить cron jobs
  ```bash
  crontab ~/crontab.backup
  ```
  **Проверка:** `crontab -l | grep obsidian`

- [ ] **5.2** Запустить ручную переиндексацию
  ```bash
  ./obsidian_reindex.sh
  ```
  **Проверка:** Лог без ошибок

- [ ] **5.3** Открыть Obsidian.app
  **Проверка:** Новая структура видна, файлы открываются

- [ ] **5.4** Проверить работу бота
  **Проверка:** Агент может искать в vault

### Фаза 6: Оптимизации (День 3+)

- [ ] **6.1** Внедрить Smart Indexing
  - Создать `smart_reindex.sh`
  - Настроить приоритеты в cron

- [ ] **6.2** Внедрить Hierarchical Search
  - Создать `obsidian_smart_search.sh`
  - Обновить агентов на использование

- [ ] **6.3** Настроить Auto-Archiving
  - Создать `auto_archive.sh`
  - Добавить в cron (1 раз в неделю)

- [ ] **6.4** Оптимизировать chunking
  - Обновить `ingest_docs.py`

### Фаза 7: Cleanup (Через 1 неделю)

- [ ] **7.1** Убедиться в стабильности
  - Нет ошибок в логах за неделю
  - Все агенты работают корректно

- [ ] **7.2** Удалить symlink'и (опционально)
  ```bash
  rm -rf "My Docs/05_Archive/_Legacy_Symlinks"
  ```

- [ ] **7.3** Удалить старые папки (опционально, после полной проверки)
  ```bash
  # Только после 100% уверенности!
  rm -rf "My Docs/To claw"
  rm -rf "My Docs/Personal"
  ```

---

## Приложения

### A. Проверочный чек-лист

```markdown
## Post-Migration Checklist

### Функциональность
- [ ] SQLite поиск работает
- [ ] RAG поиск работает  
- [ ] Web clip сохраняет в правильную папку
- [ ] Crash analyzer находит конфиги
- [ ] Daily snapshot пишет в today-session.md
- [ ] Lessons learned обновляется

### Структура
- [ ] PARA папки созданы
- [ ] Файлы скопированы
- [ ] Symlink работают
- [ ] README созданы

### Интеграция
- [ ] Cron jobs запущены
- [ ] Docker mount points корректны
- [ ] Агенты используют новые пути
```

### B. Обновление docker-compose (если нужно)

```yaml
# Если используются volume mounts
volumes:
  - type: bind
    source: ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/My Docs
    target: /data/obsidian
    read_only: true
```

### C. Таблица соответствия переменных окружения

| Переменная | Старое значение | Новое значение |
|------------|-----------------|----------------|
| `OBSIDIAN_VAULT_PATH` | `/data/obsidian/To claw` | `/data/obsidian` |
| `OBSIDIAN_DB_PATH` | `/data/obsidian/To claw/Bot/obsidian.db` | `/data/obsidian/00_Meta/Bot/obsidian.db` |
| `OBSIDIAN_META_PATH` | — | `/data/obsidian/00_Meta/Bot` |

---

## Итог

Этот план обеспечивает:
1. **Безопасность** — копирование вместо перемещения, symlink для совместимости
2. **Откат** — автоматический скрипт rollback
3. **Оптимизацию** — smart indexing, hierarchical search, auto-archive
4. **Прозрачность** — подробное логирование, dry-run режим
