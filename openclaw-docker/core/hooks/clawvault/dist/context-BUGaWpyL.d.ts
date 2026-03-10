import { Command } from 'commander';

type ResolvedContextProfile = 'default' | 'planning' | 'incident' | 'handoff';
type ContextProfileInput = ResolvedContextProfile | 'auto';
declare function inferContextProfile(task: string): ResolvedContextProfile;
declare function normalizeContextProfileInput(profile: string | undefined): ContextProfileInput;
declare function resolveContextProfile(profile: ContextProfileInput | undefined, task: string): ResolvedContextProfile;

type ContextFormat = 'markdown' | 'json';
type ContextProfile = ResolvedContextProfile;
type ContextProfileOption = ContextProfile | 'auto';
interface ContextOptions {
    vaultPath: string;
    limit?: number;
    format?: ContextFormat;
    recent?: boolean;
    includeObservations?: boolean;
    budget?: number;
    profile?: ContextProfileOption;
    maxHops?: number;
}
interface ContextEntry {
    title: string;
    path: string;
    category: string;
    score: number;
    snippet: string;
    modified: string;
    age: string;
    source: 'observation' | 'daily-note' | 'search' | 'graph';
    signals?: string[];
    rationale?: string;
}
interface ContextResult {
    task: string;
    profile: ContextProfile;
    generated: string;
    context: ContextEntry[];
    markdown: string;
}
declare function formatContextMarkdown(task: string, entries: ContextEntry[]): string;
declare function buildContext(task: string, options: ContextOptions): Promise<ContextResult>;
declare function contextCommand(task: string, options: ContextOptions): Promise<void>;
declare function registerContextCommand(program: Command): void;

export { type ContextEntry as C, type ResolvedContextProfile as R, type ContextFormat as a, type ContextOptions as b, type ContextProfile as c, type ContextProfileInput as d, type ContextProfileOption as e, type ContextResult as f, buildContext as g, contextCommand as h, formatContextMarkdown as i, inferContextProfile as j, resolveContextProfile as k, normalizeContextProfileInput as n, registerContextCommand as r };
