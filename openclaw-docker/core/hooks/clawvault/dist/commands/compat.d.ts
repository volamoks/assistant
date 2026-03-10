type CompatStatus = 'ok' | 'warn' | 'error';
interface CompatCheck {
    label: string;
    status: CompatStatus;
    detail?: string;
    hint?: string;
}
interface CompatReport {
    generatedAt: string;
    checks: CompatCheck[];
    warnings: number;
    errors: number;
}
interface CompatOptions {
    baseDir?: string;
}
interface CompatCommandOptions {
    json?: boolean;
    strict?: boolean;
    baseDir?: string;
}
declare function checkOpenClawCompatibility(options?: CompatOptions): CompatReport;
declare function compatibilityExitCode(report: CompatReport, options?: {
    strict?: boolean;
}): number;
declare function compatCommand(options?: CompatCommandOptions): Promise<CompatReport>;

export { type CompatCheck, type CompatCommandOptions, type CompatReport, type CompatStatus, checkOpenClawCompatibility, compatCommand, compatibilityExitCode };
