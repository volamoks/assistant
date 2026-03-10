import { Command } from 'commander';

interface RebuildCommandOptions {
    vaultPath?: string;
    from?: string;
    to?: string;
}
declare function rebuildCommand(options: RebuildCommandOptions): Promise<void>;
declare function registerRebuildCommand(program: Command): void;

export { type RebuildCommandOptions, rebuildCommand, registerRebuildCommand };
