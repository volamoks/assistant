import { Command } from 'commander';

declare const MEMORY_GRAPH_SCHEMA_VERSION = 1;
type NodeCategory = 'note' | 'daily' | 'observation' | 'handoff' | 'decision' | 'lesson' | 'project' | 'person' | 'commitment' | 'tag' | 'unresolved';
type MemoryGraphNodeType = NodeCategory;
type MemoryGraphEdgeType = 'wiki_link' | 'tag' | 'frontmatter_relation';
interface MemoryGraphNode {
    id: string;
    title: string;
    type: MemoryGraphNodeType;
    category: string;
    path: string | null;
    tags: string[];
    missing: boolean;
    degree: number;
    modifiedAt: string | null;
}
interface MemoryGraphEdge {
    id: string;
    source: string;
    target: string;
    type: MemoryGraphEdgeType;
    label?: string;
}
interface MemoryGraphStats {
    generatedAt: string;
    nodeCount: number;
    edgeCount: number;
    nodeTypeCounts: Record<string, number>;
    edgeTypeCounts: Record<string, number>;
}
interface MemoryGraph {
    schemaVersion: number;
    nodes: MemoryGraphNode[];
    edges: MemoryGraphEdge[];
    stats: MemoryGraphStats;
}
interface MemoryGraphFileFragment {
    relativePath: string;
    mtimeMs: number;
    nodes: MemoryGraphNode[];
    edges: MemoryGraphEdge[];
}
interface MemoryGraphIndex {
    schemaVersion: number;
    vaultPath: string;
    generatedAt: string;
    files: Record<string, MemoryGraphFileFragment>;
    graph: MemoryGraph;
}
interface BuildGraphIndexOptions {
    forceFull?: boolean;
}
declare function loadMemoryGraphIndex(vaultPath: string): MemoryGraphIndex | null;
declare function buildOrUpdateMemoryGraphIndex(vaultPathInput: string, options?: BuildGraphIndexOptions): Promise<MemoryGraphIndex>;
declare function getMemoryGraph(vaultPath: string, options?: {
    refresh?: boolean;
}): Promise<MemoryGraph>;

type LlmProvider = 'anthropic' | 'openai' | 'gemini';
interface LlmCompletionOptions {
    prompt: string;
    provider?: LlmProvider | null;
    model?: string;
    systemPrompt?: string;
    temperature?: number;
    maxTokens?: number;
    fetchImpl?: typeof fetch;
}
declare function resolveLlmProvider(): LlmProvider | null;
declare function requestLlmCompletion(options: LlmCompletionOptions): Promise<string>;

declare const INJECTABLE_CATEGORIES: readonly ["rules", "decisions", "preferences"];
type InjectSourceCategory = (typeof INJECTABLE_CATEGORIES)[number];
type InjectMatchSource = 'trigger' | 'keyword' | 'entity' | 'graph_1hop' | 'llm_intent';
interface InjectableItem {
    id: string;
    category: InjectSourceCategory;
    relativePath: string;
    title: string;
    content: string;
    triggers: string[];
    scope: string[];
    priority: number;
    searchKeywords: string[];
    noteNodeId: string;
}
interface InjectMatchReason {
    source: InjectMatchSource;
    value: string;
    weight: number;
}
interface InjectMatch {
    item: InjectableItem;
    score: number;
    deterministicScore: number;
    llmScore: number | null;
    reasons: InjectMatchReason[];
}
interface InjectResult {
    message: string;
    generatedAt: string;
    deterministicMs: number;
    llmProvider: LlmProvider | null;
    usedLlm: boolean;
    matches: InjectMatch[];
}
interface InjectRuntimeOptions {
    maxResults?: number;
    useLlm?: boolean;
    scope?: string | string[];
    model?: string;
    fetchImpl?: typeof fetch;
}
declare function indexInjectableItems(vaultPathInput: string): InjectableItem[];
declare function deterministicInjectMatches(params: {
    message: string;
    items: InjectableItem[];
    graph: MemoryGraph;
    scope?: string | string[];
}): InjectMatch[];
declare function runPromptInjection(vaultPathInput: string, message: string, options?: InjectRuntimeOptions): Promise<InjectResult>;

type InjectFormat = 'markdown' | 'json';
interface InjectCommandOptions {
    vaultPath: string;
    maxResults?: number;
    useLlm?: boolean;
    scope?: string | string[];
    format?: InjectFormat;
    model?: string;
}
declare function buildInjectionResult(message: string, options: InjectCommandOptions): Promise<InjectResult>;
declare function injectCommand(message: string, options: InjectCommandOptions): Promise<void>;
declare function registerInjectCommand(program: Command): void;

export { runPromptInjection as A, type InjectCommandOptions as I, type LlmCompletionOptions as L, MEMORY_GRAPH_SCHEMA_VERSION as M, type InjectFormat as a, type InjectMatch as b, type InjectMatchReason as c, type InjectMatchSource as d, type InjectResult as e, type InjectRuntimeOptions as f, type InjectSourceCategory as g, type InjectableItem as h, type LlmProvider as i, type MemoryGraph as j, type MemoryGraphEdge as k, type MemoryGraphEdgeType as l, type MemoryGraphIndex as m, type MemoryGraphNode as n, type MemoryGraphNodeType as o, type MemoryGraphStats as p, buildInjectionResult as q, buildOrUpdateMemoryGraphIndex as r, deterministicInjectMatches as s, getMemoryGraph as t, indexInjectableItems as u, injectCommand as v, loadMemoryGraphIndex as w, registerInjectCommand as x, requestLlmCompletion as y, resolveLlmProvider as z };
