import { Command } from 'commander';

interface ObserveCommandOptions {
    watch?: string;
    threshold?: number;
    reflectThreshold?: number;
    model?: string;
    extractTasks?: boolean;
    compress?: string;
    daemon?: boolean;
    vaultPath?: string;
    active?: boolean;
    agent?: string;
    minNew?: number;
    sessionsDir?: string;
    dryRun?: boolean;
    cron?: boolean;
}
declare function observeCommand(options: ObserveCommandOptions): Promise<void>;
declare function registerObserveCommand(program: Command): void;

export { type ObserveCommandOptions, observeCommand, registerObserveCommand };
