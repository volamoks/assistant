import { Command } from 'commander';

type ReplaySource = 'chatgpt' | 'claude' | 'opencode' | 'openclaw';

interface ReplayCommandOptions {
    source: ReplaySource;
    inputPath: string;
    from?: string;
    to?: string;
    dryRun?: boolean;
    vaultPath?: string;
}
declare function replayCommand(options: ReplayCommandOptions): Promise<void>;
declare function registerReplayCommand(program: Command): void;

export { type ReplayCommandOptions, registerReplayCommand, replayCommand };
