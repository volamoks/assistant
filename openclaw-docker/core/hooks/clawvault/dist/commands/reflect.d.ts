import { Command } from 'commander';

interface ReflectCommandOptions {
    vaultPath?: string;
    days?: number;
    dryRun?: boolean;
}
declare function reflectCommand(options: ReflectCommandOptions): Promise<void>;
declare function registerReflectCommand(program: Command): void;

export { type ReflectCommandOptions, reflectCommand, registerReflectCommand };
