import { Command } from 'commander';

interface EmbedCommandOptions {
    vaultPath?: string;
    quiet?: boolean;
}
interface EmbedCommandResult {
    vaultPath: string;
    qmdCollection: string;
    qmdRoot: string;
    startedAt: string;
    finishedAt: string;
}
declare function embedCommand(options?: EmbedCommandOptions): Promise<EmbedCommandResult>;
declare function registerEmbedCommand(program: Command): void;

export { type EmbedCommandOptions, type EmbedCommandResult, embedCommand, registerEmbedCommand };
