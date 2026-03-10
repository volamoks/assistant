/**
 * Get the vault path from CLAWVAULT_PATH env var or throw
 */
declare function getVaultPath(): string;
declare function findNearestVaultPath(startPath?: string): string | null;
declare function resolveVaultPath(options?: {
    explicitPath?: string;
    cwd?: string;
}): string;

export { findNearestVaultPath, getVaultPath, resolveVaultPath };
