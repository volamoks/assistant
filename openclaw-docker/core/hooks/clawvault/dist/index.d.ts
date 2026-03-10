import { Command } from 'commander';
import { V as VaultConfig, S as StoreOptions, D as Document, a as SearchOptions, b as SearchResult, c as SyncOptions, d as SyncResult, C as Category, M as MemoryType, H as HandoffDocument, e as SessionRecap } from './types-C74wgGL1.js';
export { f as DEFAULT_CATEGORIES, g as DEFAULT_CONFIG, h as MEMORY_TYPES, T as TYPE_TO_CATEGORY, i as VaultMeta } from './types-C74wgGL1.js';
export { setupCommand } from './commands/setup.js';
export { CompatCheck, CompatCommandOptions, CompatReport, CompatStatus, checkOpenClawCompatibility, compatCommand, compatibilityExitCode } from './commands/compat.js';
export { GraphSummary, graphCommand, graphSummary } from './commands/graph.js';
export { KanbanGroupBy, KanbanImportChange, KanbanImportOptions, KanbanImportResult, KanbanLane, KanbanSyncOptions, KanbanSyncResult, ParsedKanbanBoard, ParsedKanbanLane, buildKanbanLanes, extractCardSlug, formatKanbanCard, generateKanbanMarkdown, importKanbanBoard, kanbanCommand, parseKanbanMarkdown, syncKanbanBoard } from './commands/kanban.js';
export { C as ContextEntry, a as ContextFormat, b as ContextOptions, c as ContextProfile, d as ContextProfileInput, e as ContextProfileOption, f as ContextResult, R as ResolvedContextProfile, g as buildContext, h as contextCommand, i as formatContextMarkdown, j as inferContextProfile, n as normalizeContextProfileInput, r as registerContextCommand, k as resolveContextProfile } from './context-BUGaWpyL.js';
export { I as InjectCommandOptions, a as InjectFormat, b as InjectMatch, c as InjectMatchReason, d as InjectMatchSource, e as InjectResult, f as InjectRuntimeOptions, g as InjectSourceCategory, h as InjectableItem, L as LlmCompletionOptions, i as LlmProvider, M as MEMORY_GRAPH_SCHEMA_VERSION, j as MemoryGraph, k as MemoryGraphEdge, l as MemoryGraphEdgeType, m as MemoryGraphIndex, n as MemoryGraphNode, o as MemoryGraphNodeType, p as MemoryGraphStats, q as buildInjectionResult, r as buildOrUpdateMemoryGraphIndex, s as deterministicInjectMatches, t as getMemoryGraph, u as indexInjectableItems, v as injectCommand, w as loadMemoryGraphIndex, x as registerInjectCommand, y as requestLlmCompletion, z as resolveLlmProvider, A as runPromptInjection } from './inject-x65KXWPk.js';
export { ObserveCommandOptions, observeCommand, registerObserveCommand } from './commands/observe.js';
export { ReflectCommandOptions, reflectCommand, registerReflectCommand } from './commands/reflect.js';
export { ArchiveCommandOptions, archiveCommand, registerArchiveCommand } from './commands/archive.js';
export { RebuildCommandOptions, rebuildCommand, registerRebuildCommand } from './commands/rebuild.js';
export { DoctorCheck, DoctorReport, DoctorStatus, doctor } from './commands/doctor.js';
export { EmbedCommandOptions, EmbedCommandResult, embedCommand, registerEmbedCommand } from './commands/embed.js';
export { ReplayCommandOptions, registerReplayCommand, replayCommand } from './commands/replay.js';
export { MigrateObservationsOptions, MigrateObservationsResult, migrateObservations, migrateObservationsCommand, registerMigrateObservationsCommand } from './commands/migrate-observations.js';
export { SyncBdCommandOptions, registerSyncBdCommand, syncBdCommand } from './commands/sync-bd.js';
export { SessionRecapFormat, SessionRecapOptions, SessionRecapResult, SessionTurn, buildSessionRecap, formatSessionRecapMarkdown, sessionRecapCommand } from './commands/session-recap.js';
export { findNearestVaultPath, getVaultPath, resolveVaultPath } from './lib/config.js';
export { registerCliCommands } from './cli/index.js';
import { TaskStatus } from './lib/task-utils.js';
export { completeTask, listDependentTasks, listSubtasks, updateTask } from './lib/task-utils.js';
export { CLAWVAULT_SERVE_PATH, DEFAULT_SERVE_PORT, ServeInstance, TailscalePeer, TailscaleServeConfig, TailscaleStatus, TailscaleSyncOptions, TailscaleSyncResult, VaultFileEntry, VaultManifest, checkPeerClawVault, compareManifests, configureTailscaleServe, discoverClawVaultPeers, fetchRemoteFile, fetchRemoteManifest, findPeer, generateVaultManifest, getOnlinePeers, getTailscaleStatus, getTailscaleVersion, hasTailscale, pushFileToRemote, resolvePeerIP, serveVault, stopTailscaleServe, syncWithPeer } from './lib/tailscale.js';
export { TailscaleDiscoverCommandOptions, TailscaleServeCommandOptions, TailscaleStatusCommandOptions, TailscaleSyncCommandOptions, registerTailscaleCommands, registerTailscaleDiscoverCommand, registerTailscaleServeCommand, registerTailscaleStatusCommand, registerTailscaleSyncCommand, tailscaleDiscoverCommand, tailscaleServeCommand, tailscaleStatusCommand, tailscaleSyncCommand } from './commands/tailscale.js';
export { TemplateVariables, buildTemplateVariables, renderTemplate } from './lib/template-engine.js';
export { Project, ProjectFrontmatter, ProjectStatus, archiveProject, createProject, getProjectActivity, getProjectTasks, listProjects, readProject, updateProject } from './lib/project-utils.js';
import 'child_process';
import 'http';

/**
 * ClawVault - The elephant's memory
 */

declare class ClawVault {
    private config;
    private search;
    private initialized;
    constructor(vaultPath: string);
    /**
     * Initialize a new vault
     */
    init(options?: Partial<VaultConfig>, initFlags?: {
        skipBases?: boolean;
        skipTasks?: boolean;
        skipGraph?: boolean;
    }): Promise<void>;
    private createBasesFiles;
    /**
     * Load an existing vault
     */
    load(): Promise<void>;
    /**
     * Reindex all documents
     */
    reindex(): Promise<number>;
    /**
     * Load a document from disk
     */
    private loadDocument;
    /**
     * Store a new document
     */
    store(options: StoreOptions): Promise<Document>;
    /**
     * Quick store to inbox
     */
    capture(note: string, title?: string): Promise<Document>;
    /**
     * Search the vault (BM25 via qmd)
     */
    find(query: string, options?: SearchOptions): Promise<SearchResult[]>;
    /**
     * Semantic/vector search (via qmd vsearch)
     */
    vsearch(query: string, options?: SearchOptions): Promise<SearchResult[]>;
    /**
     * Combined search with query expansion (via qmd query)
     */
    query(query: string, options?: SearchOptions): Promise<SearchResult[]>;
    /**
     * Get a document by ID or path
     */
    get(idOrPath: string): Promise<Document | null>;
    /**
     * List documents in a category
     */
    list(category?: string): Promise<Document[]>;
    /**
     * Sync vault to another location (for Obsidian on Windows, etc.)
     */
    sync(options: SyncOptions): Promise<SyncResult>;
    /**
     * Get vault statistics
     */
    stats(): Promise<{
        documents: number;
        categories: {
            [key: string]: number;
        };
        links: number;
        tags: string[];
    }>;
    /**
     * Get all categories
     */
    getCategories(): Category[];
    /**
     * Check if vault is initialized
     */
    isInitialized(): boolean;
    /**
     * Get vault path
     */
    getPath(): string;
    /**
     * Get vault name
     */
    getName(): string;
    /**
     * Get qmd collection name
     */
    getQmdCollection(): string;
    /**
     * Get qmd collection root
     */
    getQmdRoot(): string;
    /**
     * Store a memory with type classification
     * Automatically routes to correct category based on type
     */
    remember(type: MemoryType, title: string, content: string, frontmatter?: Record<string, unknown>): Promise<Document>;
    /**
     * Create a session handoff document
     * Call this before context death or long pauses
     */
    createHandoff(handoff: Omit<HandoffDocument, 'created'>): Promise<Document>;
    /**
     * Format handoff as readable markdown
     */
    private formatHandoff;
    /**
     * Generate a session recap - who I was
     * Call this on bootstrap to restore context
     */
    generateRecap(options?: {
        handoffLimit?: number;
        brief?: boolean;
    }): Promise<SessionRecap>;
    /**
     * Format recap as readable markdown for injection
     */
    formatRecap(recap: SessionRecap, options?: {
        brief?: boolean;
    }): string;
    /**
     * Parse a handoff document back into structured form
     */
    private parseHandoff;
    /**
     * Safely convert a date value to ISO string format.
     * Handles Date objects, strings, and undefined values.
     */
    private toDateString;
    /**
     * Extract the date portion (YYYY-MM-DD) from an ISO date string or Date object.
     * Provides safe handling for various date formats.
     */
    private extractDatePart;
    private applyQmdConfig;
    private slugify;
    private saveIndex;
    private createTemplates;
    private createWelcomeNote;
    private syncMemoryGraphIndex;
    private generateReadme;
    private getCategoryDescription;
}
/**
 * Find and open the nearest vault (walks up directory tree)
 */
declare function findVault(startPath?: string): Promise<ClawVault | null>;
/**
 * Create a new vault
 */
declare function createVault(vaultPath: string, options?: Partial<VaultConfig>, initFlags?: {
    skipBases?: boolean;
    skipTasks?: boolean;
    skipGraph?: boolean;
}): Promise<ClawVault>;

/**
 * ClawVault Search Engine - qmd Backend
 * Uses qmd CLI for BM25 and vector search
 */

declare const QMD_INSTALL_URL = "https://github.com/tobi/qmd";
declare const QMD_INSTALL_COMMAND = "bun install -g github:tobi/qmd";
declare class QmdUnavailableError extends Error {
    constructor(message?: string);
}
/**
 * Check if qmd is available
 */
declare function hasQmd(): boolean;
/**
 * Trigger qmd update (reindex)
 */
declare function qmdUpdate(collection?: string, indexName?: string): void;
/**
 * Trigger qmd embed (create/update vector embeddings)
 */
declare function qmdEmbed(collection?: string, indexName?: string): void;
/**
 * QMD Search Engine - wraps qmd CLI
 */
declare class SearchEngine {
    private documents;
    private collection;
    private vaultPath;
    private collectionRoot;
    private qmdIndexName?;
    /**
     * Set the collection name (usually vault name)
     */
    setCollection(name: string): void;
    /**
     * Set the vault path for file resolution
     */
    setVaultPath(vaultPath: string): void;
    /**
     * Set the collection root for qmd:// URI resolution
     */
    setCollectionRoot(root: string): void;
    /**
     * Set qmd index name (defaults to qmd global default when omitted)
     */
    setIndexName(indexName?: string): void;
    /**
     * Add or update a document in the local cache
     * Note: qmd indexing happens via qmd update command
     */
    addDocument(doc: Document): void;
    /**
     * Remove a document from the local cache
     */
    removeDocument(id: string): void;
    /**
     * No-op for qmd - indexing is managed externally
     */
    rebuildIDF(): void;
    /**
     * BM25 search via qmd
     */
    search(query: string, options?: SearchOptions): SearchResult[];
    /**
     * Vector/semantic search via qmd vsearch
     */
    vsearch(query: string, options?: SearchOptions): SearchResult[];
    /**
     * Combined search with query expansion (qmd query command)
     */
    query(query: string, options?: SearchOptions): SearchResult[];
    private runQmdQuery;
    /**
     * Convert qmd results to ClawVault SearchResult format
     */
    private convertResults;
    private resolveModifiedAt;
    private getRecencyFactor;
    /**
     * Convert qmd:// URI to file path
     */
    private qmdUriToPath;
    /**
     * Clean up qmd snippet format
     */
    private cleanSnippet;
    /**
     * Get all cached documents
     */
    getAllDocuments(): Document[];
    /**
     * Get document count
     */
    get size(): number;
    /**
     * Clear the local document cache
     */
    clear(): void;
    /**
     * Export documents for persistence
     */
    export(): {
        documents: Document[];
    };
    /**
     * Import from persisted data
     */
    import(data: {
        documents: Document[];
    }): void;
}
/**
 * Find wiki-links in content
 */
declare function extractWikiLinks(content: string): string[];
/**
 * Find tags in content (#tag format)
 */
declare function extractTags(content: string): string[];

/**
 * ClawVault Hybrid Search — BM25 + Semantic Embeddings + RRF
 *
 * Proven in LongMemEval benchmarks:
 * - v28 pipeline: 57.0% overall (up from 52.6% with BM25-only)
 * - Multi-session: 45.9% (up from 28.6%)
 * - Single-session-user: 85.7% (up from 72.9%)
 *
 * Architecture:
 * 1. BM25 via existing qmd search
 * 2. Semantic via @huggingface/transformers (all-MiniLM-L6-v2)
 * 3. Reciprocal Rank Fusion (k=60)
 */

/**
 * Compute embedding for a text string
 */
declare function embed(text: string): Promise<Float32Array>;
/**
 * Compute embeddings for multiple texts
 */
declare function embedBatch(texts: string[]): Promise<Float32Array[]>;
/**
 * Cosine similarity between two normalized vectors
 */
declare function cosineSimilarity(a: Float32Array, b: Float32Array): number;
/**
 * Embedding cache — stores embeddings on disk alongside vault files
 */
declare class EmbeddingCache {
    private cachePath;
    private cache;
    private dirty;
    constructor(vaultPath: string);
    /**
     * Load cache from disk
     */
    load(): void;
    /**
     * Save cache to disk
     */
    save(): void;
    get(key: string): Float32Array | undefined;
    set(key: string, embedding: Float32Array): void;
    has(key: string): boolean;
    entries(): IterableIterator<[string, Float32Array]>;
    get size(): number;
}
/**
 * Reciprocal Rank Fusion of two ranked lists
 */
declare function reciprocalRankFusion(list1: {
    id: string;
    score: number;
}[], list2: {
    id: string;
    score: number;
}[], k?: number): {
    id: string;
    score: number;
}[];
/**
 * Semantic search against embedding cache
 */
declare function semanticSearch(query: string, cache: EmbeddingCache, topK?: number): Promise<{
    id: string;
    score: number;
}[]>;
/**
 * Hybrid search: combines BM25 results with semantic results via RRF
 */
declare function hybridSearch(query: string, bm25Results: SearchResult[], cache: EmbeddingCache, options?: {
    topK?: number;
    rrfK?: number;
}): Promise<SearchResult[]>;

declare const OBSERVE_PROVIDERS: readonly ["anthropic", "openai", "gemini"];
declare const OBSERVER_COMPRESSION_PROVIDERS: readonly ["anthropic", "openai", "gemini", "openai-compatible", "ollama"];
declare const THEMES: readonly ["neural", "minimal", "none"];
declare const CONTEXT_PROFILES: readonly ["default", "planning", "incident", "handoff", "auto"];
type ObserveProvider = (typeof OBSERVE_PROVIDERS)[number];
type ObserverCompressionProvider = (typeof OBSERVER_COMPRESSION_PROVIDERS)[number];
type Theme = (typeof THEMES)[number];
type ContextProfile = (typeof CONTEXT_PROFILES)[number];
type ManagedConfigKey = 'name' | 'categories' | 'theme' | 'observe.model' | 'observe.provider' | 'observer.compression.provider' | 'observer.compression.model' | 'observer.compression.baseUrl' | 'observer.compression.apiKey' | 'context.maxResults' | 'context.defaultProfile' | 'graph.maxHops' | 'inject.maxResults' | 'inject.useLlm' | 'inject.scope';
interface RouteRule {
    pattern: string;
    target: string;
    priority: number;
}
declare const SUPPORTED_CONFIG_KEYS: ManagedConfigKey[];
declare function listConfig(vaultPath: string): Record<string, unknown>;
declare function getConfig(vaultPath: string): Record<string, unknown>;
declare function getConfigValue(vaultPath: string, key: ManagedConfigKey): unknown;
declare function setConfigValue(vaultPath: string, key: ManagedConfigKey, value: unknown): {
    value: unknown;
    config: Record<string, unknown>;
};
declare function resetConfig(vaultPath: string): Record<string, unknown>;
declare function listRouteRules(vaultPath: string): RouteRule[];
declare function addRouteRule(vaultPath: string, pattern: string, target: string): RouteRule;
declare function removeRouteRule(vaultPath: string, pattern: string): boolean;
declare function matchRouteRule(text: string, routes: RouteRule[]): RouteRule | null;
declare function testRouteRule(vaultPath: string, text: string): RouteRule | null;

/**
 * Transition Ledger for ClawVault
 * Logs task status transitions to JSONL files and supports querying.
 */

interface TransitionEvent {
    task_id: string;
    agent_id: string;
    from_status: TaskStatus;
    to_status: TaskStatus;
    timestamp: string;
    confidence: number;
    cost_tokens: number | null;
    reason: string | null;
}
declare function isRegression(from: TaskStatus, to: TaskStatus): boolean;
/**
 * Append a transition event to the ledger
 */
declare function appendTransition(vaultPath: string, event: TransitionEvent): void;
/**
 * Build a transition event from context
 */
declare function buildTransitionEvent(taskId: string, fromStatus: TaskStatus, toStatus: TaskStatus, options?: {
    confidence?: number;
    reason?: string;
}): TransitionEvent;
/**
 * Read all transition events from all ledger files
 */
declare function readAllTransitions(vaultPath: string): TransitionEvent[];
/**
 * Query transitions with filters
 */
declare function queryTransitions(vaultPath: string, filters?: {
    taskId?: string;
    agent?: string;
    failed?: boolean;
}): TransitionEvent[];
/**
 * Count blocked transitions for a task
 */
declare function countBlockedTransitions(vaultPath: string, taskId: string): number;
/**
 * Format transitions as a table string
 */
declare function formatTransitionsTable(events: TransitionEvent[]): string;

interface CompressorOptions {
    provider?: CompressionProvider;
    model?: string;
    baseUrl?: string;
    apiKey?: string;
    now?: () => Date;
    fetchImpl?: typeof fetch;
}
type CompressionProvider = 'anthropic' | 'openai' | 'gemini' | 'openai-compatible' | 'ollama';
declare class Compressor {
    private readonly provider?;
    private readonly model?;
    private readonly baseUrl?;
    private readonly apiKey?;
    private readonly now;
    private readonly fetchImpl;
    constructor(options?: CompressorOptions);
    compress(messages: string[], existingObservations: string): Promise<string>;
    private resolveProvider;
    private resolveConfiguredProvider;
    private resolveProviderFromEnv;
    private resolveModel;
    private resolveApiKey;
    private resolveBaseUrl;
    private readEnvValue;
    private buildPrompt;
    private buildOpenAICompatibleUrl;
    private buildOpenAICompatibleHeaders;
    private extractOpenAIContent;
    private callAnthropic;
    private callOpenAI;
    private callOpenAICompatible;
    private callGemini;
    private normalizeLlmOutput;
    /**
     * Fix wiki-link corruption from LLM compression.
     * LLMs often fuse preceding word fragments into wiki-links during rewriting:
     *   "reque[[people/pedro]]" → "[[people/pedro]]"
     *   "Linke[[agents/zeca]]" → "[[agents/zeca]]"
     *   "taske[[people/pedro]]a" → "[[people/pedro]]"
     * Also fixes trailing word fragments fused after closing brackets.
     */
    private sanitizeWikiLinks;
    private enforceImportanceRules;
    private enforceImportanceForRecord;
    private fallbackCompression;
    private mergeObservations;
    private mergeRecord;
    private renderSections;
    private inferImportance;
    private inferConfidence;
    private isCriticalContent;
    private isNotableContent;
    private inferTaskType;
    private normalizeText;
    private extractDate;
    private extractTime;
    private formatDate;
    private formatTime;
    private clamp01;
}

interface ObserverCompressor {
    compress(messages: string[], existingObservations: string): Promise<string>;
}
interface ObserverReflector {
    reflect(observations: string): string;
}
interface ObserverOptions {
    tokenThreshold?: number;
    reflectThreshold?: number;
    model?: string;
    compressionProvider?: CompressionProvider;
    compressionBaseUrl?: string;
    compressionApiKey?: string;
    compressor?: ObserverCompressor;
    reflector?: ObserverReflector;
    now?: () => Date;
    rawCapture?: boolean;
    extractTasks?: boolean;
}
interface ObserverProcessOptions {
    source?: string;
    sessionKey?: string;
    transcriptId?: string;
    timestamp?: Date;
}
declare class Observer {
    private readonly vaultPath;
    private readonly tokenThreshold;
    private readonly reflectThreshold;
    private readonly compressor;
    private readonly reflector;
    private readonly now;
    private readonly rawCapture;
    private readonly router;
    private pendingMessages;
    private pendingRouteContext;
    private observationsCache;
    private lastRoutingSummary;
    constructor(vaultPath: string, options?: ObserverOptions);
    processMessages(messages: string[], options?: ObserverProcessOptions): Promise<void>;
    /**
     * Force-flush pending messages regardless of threshold.
     * Call this on session end to capture everything.
     */
    flush(): Promise<{
        observations: string;
        routingSummary: string;
    }>;
    getObservations(): string;
    private estimateTokens;
    private readTodayObservations;
    private readObservationForDate;
    private readObservationFile;
    private writeObservationFile;
    private deduplicateObservationMarkdown;
    private persistRawMessages;
    private sanitizeSource;
    private mergeRouteContext;
}

interface ObserveCursorEntry {
    lastObservedOffset: number;
    lastObservedAt: string;
    sessionKey: string;
    lastFileSize: number;
}
type ObserveCursorStore = Record<string, ObserveCursorEntry>;
interface ActiveObserveOptions {
    vaultPath: string;
    agentId?: string;
    minNewBytes?: number;
    sessionsDir?: string;
    dryRun?: boolean;
    threshold?: number;
    reflectThreshold?: number;
    model?: string;
    extractTasks?: boolean;
}
interface ActiveObservationCandidate {
    sessionId: string;
    sessionKey: string;
    sourceLabel: string;
    filePath: string;
    fileSize: number;
    startOffset: number;
    newBytes: number;
    thresholdBytes: number;
}
interface ActiveObservationFailure {
    sessionId: string;
    sessionKey: string;
    sourceLabel: string;
    error: string;
}
interface ActiveObserveResult {
    agentId: string;
    sessionsDir: string;
    checkedSessions: number;
    candidateSessions: number;
    observedSessions: number;
    cursorUpdates: number;
    dryRun: boolean;
    totalNewBytes: number;
    observedNewBytes: number;
    routedCounts: Record<string, number>;
    failedSessionCount: number;
    failedSessions: ActiveObservationFailure[];
    candidates: ActiveObservationCandidate[];
}
interface ObserverStalenessResult {
    staleCount: number;
    oldestMs: number;
    newestMs: number;
}
type MinimalObserver = Pick<Observer, 'processMessages' | 'flush'>;
type ObserverFactory = (vaultPath: string, options: ObserverOptions) => MinimalObserver;
interface ActiveObserveDependencies {
    createObserver?: ObserverFactory;
    now?: () => Date;
}
interface ObserverStalenessOptions {
    sessionsDir?: string;
    now?: () => Date;
}
declare function getScaledObservationThresholdBytes(fileSizeBytes: number): number;
declare function getObserverStaleness(vaultPath: string, options?: ObserverStalenessOptions): ObserverStalenessResult;
declare function parseSessionSourceLabel(sessionKey: string): string;
declare function observeActiveSessions(options: ActiveObserveOptions, dependencies?: ActiveObserveDependencies): Promise<ActiveObserveResult>;

interface ReflectorOptions {
    now?: () => Date;
}
declare class Reflector {
    private readonly now;
    constructor(options?: ReflectorOptions);
    reflect(observations: string): string;
    private buildCutoffDate;
    private parseDate;
    private parseSections;
    private renderSections;
    private normalizeText;
    private isSimilar;
}

interface SessionWatcherOptions {
    ignoreInitial?: boolean;
    debounceMs?: number;
    flushThresholdChars?: number;
}
declare class SessionWatcher {
    private readonly watchPath;
    private readonly observer;
    private readonly ignoreInitial;
    private readonly debounceMs;
    private readonly flushThresholdChars;
    private watcher;
    private fileOffsets;
    private pendingPaths;
    private debounceTimer;
    private processingQueue;
    private bufferedChars;
    constructor(watchPath: string, observer: Observer, options?: SessionWatcherOptions);
    start(): Promise<void>;
    stop(): Promise<void>;
    private scheduleDrain;
    private drainPendingPaths;
    private consumeFile;
    private primeInitialOffsets;
    private collectFiles;
}

declare function parseSessionFile(filePath: string): string[];

interface ArchiveObservationsOptions {
    olderThanDays?: number;
    dryRun?: boolean;
    now?: () => Date;
}
interface ArchiveObservationsResult {
    scanned: number;
    archived: number;
    skipped: number;
    dryRun: boolean;
    archivedDates: string[];
}
declare function archiveObservations(vaultPath: string, options?: ArchiveObservationsOptions): ArchiveObservationsResult;

interface ReflectOptions {
    vaultPath: string;
    days?: number;
    dryRun?: boolean;
    now?: () => Date;
}
interface ReflectResult {
    processedWeeks: number;
    writtenWeeks: number;
    dryRun: boolean;
    files: string[];
    archive: ArchiveObservationsResult | null;
}
declare function runReflection(options: ReflectOptions): Promise<ReflectResult>;

/**
 * ClawVault 🐘 — An Elephant Never Forgets
 *
 * Structured memory system for AI agents with Obsidian-compatible markdown
 * and embedded semantic search.
 *
 * @example
 * ```typescript
 * import { ClawVault, createVault, findVault } from 'clawvault';
 *
 * // Create a new vault
 * const vault = await createVault('./my-memory');
 *
 * // Store a memory
 * await vault.store({
 *   category: 'decisions',
 *   title: 'Use ClawVault',
 *   content: 'Decided to use ClawVault for memory management.'
 * });
 *
 * // Search memories
 * const results = await vault.find('memory management');
 * console.log(results);
 * ```
 */

declare const VERSION: string;
declare function registerCommanderCommands(program: Command): Command;

export { type ActiveObservationCandidate, type ActiveObservationFailure, type ActiveObserveOptions, type ActiveObserveResult, type ArchiveObservationsOptions, type ArchiveObservationsResult, Category, ClawVault, type CompressionProvider, Compressor, type CompressorOptions, type ContextProfile as ConfigDefaultProfile, Document, EmbeddingCache, HandoffDocument, type ManagedConfigKey, MemoryType, type ObserveCursorEntry, type ObserveCursorStore, type ObserveProvider, Observer, type ObserverCompressionProvider, type ObserverCompressor, type ObserverOptions, type ObserverReflector, type ObserverStalenessResult, QMD_INSTALL_COMMAND, QMD_INSTALL_URL, QmdUnavailableError, type ReflectOptions, type ReflectResult, Reflector, type ReflectorOptions, type RouteRule, SUPPORTED_CONFIG_KEYS, SearchEngine, SearchOptions, SearchResult, SessionRecap, SessionWatcher, type SessionWatcherOptions, StoreOptions, SyncOptions, SyncResult, type Theme, type TransitionEvent, VERSION, VaultConfig, addRouteRule, appendTransition, archiveObservations, buildTransitionEvent, cosineSimilarity, countBlockedTransitions, createVault, embed, embedBatch, extractTags, extractWikiLinks, findVault, formatTransitionsTable, getConfig, getConfigValue, getObserverStaleness, getScaledObservationThresholdBytes, hasQmd, hybridSearch, isRegression, listConfig, listRouteRules, matchRouteRule, observeActiveSessions, parseSessionFile, parseSessionSourceLabel, qmdEmbed, qmdUpdate, queryTransitions, readAllTransitions, reciprocalRankFusion, registerCommanderCommands, removeRouteRule, resetConfig, runReflection, semanticSearch, setConfigValue, testRouteRule };
