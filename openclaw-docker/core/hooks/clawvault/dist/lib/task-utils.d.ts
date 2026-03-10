/**
 * Task utilities for ClawVault task tracking
 * Handles task and backlog file read/write/query operations
 */
type TaskStatus = 'open' | 'in-progress' | 'blocked' | 'done';
type TaskPriority = 'critical' | 'high' | 'medium' | 'low';
interface TaskFrontmatter {
    status: TaskStatus;
    source?: string;
    created: string;
    updated: string;
    owner?: string;
    project?: string;
    priority?: TaskPriority;
    blocked_by?: string;
    completed?: string;
    escalation?: boolean;
    confidence?: number;
    reason?: string;
    due?: string;
    tags?: string[];
    description?: string;
    estimate?: string;
    parent?: string;
    depends_on?: string[];
}
interface Task {
    slug: string;
    title: string;
    content: string;
    frontmatter: TaskFrontmatter;
    path: string;
}
interface BacklogFrontmatter {
    source?: string;
    project?: string;
    created: string;
    lastSeen?: string;
    tags?: string[];
}
interface BacklogItem {
    slug: string;
    title: string;
    content: string;
    frontmatter: BacklogFrontmatter;
    path: string;
}
interface TaskFilterOptions {
    status?: TaskStatus;
    owner?: string;
    project?: string;
    priority?: TaskPriority;
    due?: boolean;
    tag?: string;
    overdue?: boolean;
}
interface BacklogFilterOptions {
    project?: string;
    source?: string;
}
interface TaskTransitionOptions {
    skipTransition?: boolean;
    confidence?: number;
    reason?: string | null;
}
type CreateTaskOptions = {
    source?: string;
    owner?: string;
    project?: string;
    priority?: TaskPriority;
    due?: string;
    content?: string;
    tags?: string[];
    description?: string;
    estimate?: string;
    parent?: string;
    depends_on?: string[];
};
/**
 * Slugify a title for use as filename
 * Deterministic: same title = same slug
 */
declare function slugify(text: string): string;
/**
 * Get the tasks directory path
 */
declare function getTasksDir(vaultPath: string): string;
/**
 * Get the backlog directory path
 */
declare function getBacklogDir(vaultPath: string): string;
/**
 * Ensure the tasks directory exists
 */
declare function ensureTasksDir(vaultPath: string): void;
/**
 * Ensure the backlog directory exists
 */
declare function ensureBacklogDir(vaultPath: string): void;
/**
 * Get task file path from slug
 */
declare function getTaskPath(vaultPath: string, slug: string): string;
/**
 * Get backlog file path from slug
 */
declare function getBacklogPath(vaultPath: string, slug: string): string;
/**
 * Read a task file and parse it
 */
declare function readTask(vaultPath: string, slug: string): Task | null;
/**
 * Read a backlog item file and parse it
 */
declare function readBacklogItem(vaultPath: string, slug: string): BacklogItem | null;
/**
 * List all tasks in the vault
 */
declare function listTasks(vaultPath: string, filters?: TaskFilterOptions): Task[];
/**
 * List all backlog items in the vault
 */
declare function listBacklogItems(vaultPath: string, filters?: BacklogFilterOptions): BacklogItem[];
/**
 * Create a new task
 */
declare function createTask(vaultPath: string, title: string, options?: CreateTaskOptions): Task;
/**
 * Update an existing task
 */
declare function updateTask(vaultPath: string, slug: string, updates: {
    status?: TaskStatus;
    source?: string | null;
    owner?: string | null;
    project?: string | null;
    priority?: TaskPriority | null;
    blocked_by?: string | null;
    due?: string | null;
    tags?: string[] | null;
    completed?: string | null;
    escalation?: boolean | null;
    confidence?: number | null;
    reason?: string | null;
    description?: string | null;
    estimate?: string | null;
    parent?: string | null;
    depends_on?: string[] | null;
}, options?: TaskTransitionOptions): Task;
/**
 * Mark a task as done
 */
declare function completeTask(vaultPath: string, slug: string, options?: TaskTransitionOptions): Task;
/**
 * Create a new backlog item
 */
declare function createBacklogItem(vaultPath: string, title: string, options?: {
    source?: string;
    project?: string;
    content?: string;
    tags?: string[];
}): BacklogItem;
/**
 * Update an existing backlog item frontmatter.
 */
declare function updateBacklogItem(vaultPath: string, slug: string, updates: {
    source?: string;
    project?: string;
    tags?: string[];
    lastSeen?: string;
}): BacklogItem;
/**
 * Promote a backlog item to a task
 */
declare function promoteBacklogItem(vaultPath: string, slug: string, options?: {
    owner?: string;
    priority?: TaskPriority;
    due?: string;
}): Task;
/**
 * Get blocked tasks
 */
declare function getBlockedTasks(vaultPath: string, project?: string): Task[];
/**
 * Get active tasks (open or in-progress)
 */
declare function getActiveTasks(vaultPath: string, filters?: Omit<TaskFilterOptions, 'status'>): Task[];
/**
 * List subtasks for a parent task slug.
 */
declare function listSubtasks(vaultPath: string, parentSlug: string): Task[];
/**
 * List tasks that depend on a given task slug.
 */
declare function listDependentTasks(vaultPath: string, dependencySlug: string): Task[];
/**
 * Get recently completed tasks
 */
declare function getRecentlyCompletedTasks(vaultPath: string, limit?: number): Task[];
/**
 * Format task status icon
 */
declare function getStatusIcon(status: TaskStatus): string;
/**
 * Format task status display name
 */
declare function getStatusDisplay(status: TaskStatus): string;

export { type BacklogFilterOptions, type BacklogFrontmatter, type BacklogItem, type Task, type TaskFilterOptions, type TaskFrontmatter, type TaskPriority, type TaskStatus, type TaskTransitionOptions, completeTask, createBacklogItem, createTask, ensureBacklogDir, ensureTasksDir, getActiveTasks, getBacklogDir, getBacklogPath, getBlockedTasks, getRecentlyCompletedTasks, getStatusDisplay, getStatusIcon, getTaskPath, getTasksDir, listBacklogItems, listDependentTasks, listSubtasks, listTasks, promoteBacklogItem, readBacklogItem, readTask, slugify, updateBacklogItem, updateTask };
