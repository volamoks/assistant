import { e as SessionRecap } from '../types-C74wgGL1.js';
import { RecoveryInfo } from './recover.js';
import './checkpoint.js';

interface WakeOptions {
    vaultPath: string;
    handoffLimit?: number;
    brief?: boolean;
    /** Skip LLM executive summary generation (useful for tests/offline) */
    noSummary?: boolean;
}
interface WakeResult {
    recovery: RecoveryInfo;
    recap: SessionRecap;
    recapMarkdown: string;
    summary: string;
    observations: string;
}
declare function buildWakeSummary(recovery: RecoveryInfo, recap: SessionRecap): string;
declare function wake(options: WakeOptions): Promise<WakeResult>;

export { type WakeOptions, type WakeResult, buildWakeSummary, wake };
