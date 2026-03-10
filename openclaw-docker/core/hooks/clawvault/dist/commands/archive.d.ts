import { Command } from 'commander';

interface ArchiveCommandOptions {
    vaultPath?: string;
    olderThan?: number;
    dryRun?: boolean;
}
declare function archiveCommand(options: ArchiveCommandOptions): Promise<void>;
declare function registerArchiveCommand(program: Command): void;

export { type ArchiveCommandOptions, archiveCommand, registerArchiveCommand };
