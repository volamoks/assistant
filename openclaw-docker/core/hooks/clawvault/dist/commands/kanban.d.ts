import { Task } from '../lib/task-utils.js';

/**
 * Kanban command for ClawVault.
 * Syncs task frontmatter to/from Obsidian Kanban markdown boards.
 */

type KanbanGroupBy = 'status' | 'priority' | 'project' | 'owner';
interface KanbanSyncOptions {
    output?: string;
    groupBy?: KanbanGroupBy | string;
    filterProject?: string;
    filterOwner?: string;
    includeDone?: boolean;
    now?: Date;
}
interface KanbanImportOptions {
    output?: string;
}
interface KanbanLane {
    name: string;
    cards: string[];
}
interface KanbanSyncResult {
    outputPath: string;
    groupBy: KanbanGroupBy;
    markdown: string;
    lanes: KanbanLane[];
    taskCount: number;
}
interface KanbanImportChange {
    slug: string;
    field: KanbanGroupBy;
    from: string | null;
    to: string | null;
}
interface KanbanImportResult {
    outputPath: string;
    groupBy: KanbanGroupBy;
    changes: KanbanImportChange[];
    missingSlugs: string[];
}
interface ParsedKanbanLane {
    name: string;
    slugs: string[];
}
interface ParsedKanbanBoard {
    groupBy: KanbanGroupBy;
    lanes: ParsedKanbanLane[];
}
declare function formatKanbanCard(task: Task): string;
declare function buildKanbanLanes(tasks: Task[], groupBy: KanbanGroupBy): KanbanLane[];
declare function generateKanbanMarkdown(tasks: Task[], options?: {
    groupBy?: KanbanGroupBy | string;
    now?: Date;
}): string;
declare function syncKanbanBoard(vaultPath: string, options?: KanbanSyncOptions): KanbanSyncResult;
declare function extractCardSlug(line: string): string | null;
declare function parseKanbanMarkdown(markdown: string): ParsedKanbanBoard;
declare function importKanbanBoard(vaultPath: string, options?: KanbanImportOptions): KanbanImportResult;
declare function kanbanCommand(vaultPath: string, action: 'sync' | 'import', options?: KanbanSyncOptions & KanbanImportOptions): Promise<void>;

export { type KanbanGroupBy, type KanbanImportChange, type KanbanImportOptions, type KanbanImportResult, type KanbanLane, type KanbanSyncOptions, type KanbanSyncResult, type ParsedKanbanBoard, type ParsedKanbanLane, buildKanbanLanes, extractCardSlug, formatKanbanCard, generateKanbanMarkdown, importKanbanBoard, kanbanCommand, parseKanbanMarkdown, syncKanbanBoard };
