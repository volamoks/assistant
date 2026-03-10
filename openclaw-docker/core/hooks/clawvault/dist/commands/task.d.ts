import { TaskPriority, TaskStatus, Task } from '../lib/task-utils.js';

/**
 * Task command for ClawVault
 * Manages task add/list/update/done/show operations
 */

interface TaskAddOptions {
    owner?: string;
    project?: string;
    priority?: TaskPriority;
    due?: string;
    content?: string;
    tags?: string[];
    description?: string;
    estimate?: string;
    parent?: string;
    dependsOn?: string[];
}
interface TaskListOptions {
    status?: TaskStatus;
    owner?: string;
    project?: string;
    priority?: TaskPriority;
    due?: boolean;
    tag?: string;
    overdue?: boolean;
    json?: boolean;
}
interface TaskUpdateOptions {
    status?: TaskStatus;
    owner?: string | null;
    project?: string | null;
    priority?: TaskPriority | null;
    blockedBy?: string | null;
    due?: string | null;
    tags?: string[] | null;
    description?: string | null;
    estimate?: string | null;
    parent?: string | null;
    dependsOn?: string[] | null;
    confidence?: number;
    reason?: string | null;
}
interface TaskTransitionsOptions {
    agent?: string;
    failed?: boolean;
    json?: boolean;
}
interface TaskShowOptions {
    json?: boolean;
}
/**
 * Add a new task
 */
declare function taskAdd(vaultPath: string, title: string, options?: TaskAddOptions): Task;
/**
 * List tasks with optional filters
 */
declare function taskList(vaultPath: string, options?: TaskListOptions): Task[];
/**
 * Update a task
 */
declare function taskUpdate(vaultPath: string, slug: string, options: TaskUpdateOptions): Task;
/**
 * Mark a task as done
 */
declare function taskDone(vaultPath: string, slug: string, options?: {
    confidence?: number;
    reason?: string;
}): Task;
/**
 * Query task transitions
 */
declare function taskTransitions(vaultPath: string, taskId?: string, options?: TaskTransitionsOptions): string;
/**
 * Show task details
 */
declare function taskShow(vaultPath: string, slug: string): Task | null;
/**
 * Format task list as terminal table
 */
declare function formatTaskList(tasks: Task[]): string;
/**
 * Format task details for display
 */
declare function formatTaskDetails(task: Task): string;
/**
 * Task command handler for CLI
 */
declare function taskCommand(vaultPath: string, action: 'add' | 'list' | 'update' | 'done' | 'show' | 'transitions', args: {
    title?: string;
    slug?: string;
    options?: TaskAddOptions & TaskListOptions & TaskUpdateOptions & TaskShowOptions & TaskTransitionsOptions;
}): Promise<void>;

export { type TaskAddOptions, type TaskListOptions, type TaskShowOptions, type TaskTransitionsOptions, type TaskUpdateOptions, formatTaskDetails, formatTaskList, taskAdd, taskCommand, taskDone, taskList, taskShow, taskTransitions, taskUpdate };
