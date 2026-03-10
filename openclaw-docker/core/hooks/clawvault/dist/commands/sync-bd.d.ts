import { Command } from 'commander';

interface SyncBdCommandOptions {
    vaultPath?: string;
    dryRun?: boolean;
}
declare function syncBdCommand(options: SyncBdCommandOptions): Promise<void>;
declare function registerSyncBdCommand(program: Command): void;

export { type SyncBdCommandOptions, registerSyncBdCommand, syncBdCommand };
