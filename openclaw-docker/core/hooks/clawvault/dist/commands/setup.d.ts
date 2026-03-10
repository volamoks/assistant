interface SetupOptions {
    graphColors?: boolean;
    bases?: boolean;
    canvas?: boolean;
    theme?: 'neural' | 'minimal' | 'none';
    force?: boolean;
    vault?: string;
    qmdIndexName?: string;
}
declare function setupCommand(options?: SetupOptions): Promise<void>;

export { type SetupOptions, setupCommand };
