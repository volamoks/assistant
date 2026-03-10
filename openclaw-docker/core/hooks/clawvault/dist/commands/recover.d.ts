import { CheckpointData } from './checkpoint.js';

/**
 * Recovery command - detect dirty death and provide recovery info
 */

interface RecoveryInfo {
    died: boolean;
    deathTime: string | null;
    checkpoint: CheckpointData | null;
    handoffPath: string | null;
    handoffContent: string | null;
    recoveryMessage: string;
}
interface RecoveryCheckInfo {
    died: boolean;
    deathTime: string | null;
    checkpoint: CheckpointData | null;
}
interface ListedCheckpoint extends CheckpointData {
    filePath: string;
}
declare function checkRecoveryStatus(vaultPath: string): Promise<RecoveryCheckInfo>;
declare function listCheckpoints(vaultPath: string): ListedCheckpoint[];
declare function recover(vaultPath: string, options?: {
    clearFlag?: boolean;
    verbose?: boolean;
}): Promise<RecoveryInfo>;
declare function formatRecoveryCheckStatus(info: RecoveryCheckInfo): string;
declare function formatCheckpointList(checkpoints: ListedCheckpoint[]): string;
/**
 * Format recovery info for CLI output
 */
declare function formatRecoveryInfo(info: RecoveryInfo, options?: {
    verbose?: boolean;
}): string;

export { type ListedCheckpoint, type RecoveryCheckInfo, type RecoveryInfo, checkRecoveryStatus, formatCheckpointList, formatRecoveryCheckStatus, formatRecoveryInfo, listCheckpoints, recover };
