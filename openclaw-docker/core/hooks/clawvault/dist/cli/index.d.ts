import { Command } from 'commander';

declare function registerCliCommands(program: Command): Command;

export { registerCliCommands };
