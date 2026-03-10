import { Task } from '../lib/task-utils.js';

/**
 * Blocked command for ClawVault
 * Quick view of blocked tasks
 */

interface BlockedOptions {
    project?: string;
    json?: boolean;
    escalated?: boolean;
}
/**
 * Get blocked tasks
 */
declare function blockedList(vaultPath: string, options?: BlockedOptions): Task[];
/**
 * Format blocked tasks for terminal display
 */
declare function formatBlockedList(tasks: Task[]): string;
/**
 * Blocked command handler for CLI
 */
declare function blockedCommand(vaultPath: string, options?: BlockedOptions): Promise<void>;

export { type BlockedOptions, blockedCommand, blockedList, formatBlockedList };
