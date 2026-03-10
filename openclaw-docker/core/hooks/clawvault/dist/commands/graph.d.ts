interface GraphSummary {
    schemaVersion: number;
    generatedAt: string;
    nodeCount: number;
    edgeCount: number;
    nodeTypeCounts: Record<string, number>;
    edgeTypeCounts: Record<string, number>;
    fileCount: number;
}
declare function graphSummary(options?: {
    vaultPath?: string;
    refresh?: boolean;
    json?: boolean;
}): Promise<GraphSummary>;
declare function graphCommand(options?: {
    vaultPath?: string;
    refresh?: boolean;
    json?: boolean;
}): Promise<void>;

export { type GraphSummary, graphCommand, graphSummary };
