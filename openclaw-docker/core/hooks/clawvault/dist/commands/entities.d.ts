interface EntitiesOptions {
    json?: boolean;
    vaultPath?: string;
}
declare function entitiesCommand(options: EntitiesOptions): Promise<void>;

export { entitiesCommand };
