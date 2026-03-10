import { TaskPriority, BacklogItem, Task } from '../lib/task-utils.js';

/**
 * Backlog command for ClawVault
 * Manages backlog add/list/promote operations
 */

interface BacklogAddOptions {
    source?: string;
    project?: string;
    content?: string;
    tags?: string[];
}
interface BacklogListOptions {
    project?: string;
    json?: boolean;
}
interface BacklogPromoteOptions {
    owner?: string;
    priority?: TaskPriority;
    due?: string;
}
/**
 * Add a new backlog item
 */
declare function backlogAdd(vaultPath: string, title: string, options?: BacklogAddOptions): BacklogItem;
/**
 * List backlog items with optional filters
 */
declare function backlogList(vaultPath: string, options?: BacklogListOptions): BacklogItem[];
/**
 * Promote a backlog item to a task
 */
declare function backlogPromote(vaultPath: string, slug: string, options?: BacklogPromoteOptions): Task;
/**
 * Format backlog list for terminal display
 */
declare function formatBacklogList(items: BacklogItem[]): string;
/**
 * Format backlog item details for display
 */
declare function formatBacklogDetails(item: BacklogItem): string;
/**
 * Backlog command handler for CLI
 * Note: The CLI uses "clawvault backlog <title>" as shorthand for add
 */
declare function backlogCommand(vaultPath: string, action: 'add' | 'list' | 'promote', args: {
    title?: string;
    slug?: string;
    options?: BacklogAddOptions & BacklogListOptions & BacklogPromoteOptions;
}): Promise<void>;

export { type BacklogAddOptions, type BacklogListOptions, type BacklogPromoteOptions, backlogAdd, backlogCommand, backlogList, backlogPromote, formatBacklogDetails, formatBacklogList };
