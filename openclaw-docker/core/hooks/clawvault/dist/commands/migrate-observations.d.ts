import { Command } from 'commander';

interface MigrateObservationsOptions {
    vaultPath?: string;
    dryRun?: boolean;
}
interface MigrateObservationsResult {
    scanned: number;
    migrated: number;
    backups: number;
    dryRun: boolean;
}
declare function migrateObservations(vaultPath: string, options?: {
    dryRun?: boolean;
}): MigrateObservationsResult;
declare function migrateObservationsCommand(options: MigrateObservationsOptions): Promise<void>;
declare function registerMigrateObservationsCommand(program: Command): void;

export { type MigrateObservationsOptions, type MigrateObservationsResult, migrateObservations, migrateObservationsCommand, registerMigrateObservationsCommand };
