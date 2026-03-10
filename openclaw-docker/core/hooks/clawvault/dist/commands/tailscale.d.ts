import { Command } from 'commander';
import { TailscalePeer, TailscaleStatus, TailscaleSyncResult } from '../lib/tailscale.js';
import 'child_process';
import 'http';

/**
 * Tailscale Commands for ClawVault
 *
 * CLI commands for Tailscale-based vault synchronization:
 * - tailscale-status: Show Tailscale connection status and peers
 * - tailscale-sync: Sync vault with a peer on the tailnet
 * - tailscale-serve: Serve vault for sync over Tailscale
 * - tailscale-discover: Discover ClawVault peers on the tailnet
 */

interface TailscaleStatusCommandOptions {
    json?: boolean;
    peers?: boolean;
}
interface TailscaleSyncCommandOptions {
    vaultPath?: string;
    peer: string;
    port?: number;
    direction?: 'push' | 'pull' | 'bidirectional';
    dryRun?: boolean;
    deleteOrphans?: boolean;
    categories?: string[];
    https?: boolean;
    json?: boolean;
}
interface TailscaleServeCommandOptions {
    vaultPath?: string;
    port?: number;
    funnel?: boolean;
    background?: boolean;
    stop?: boolean;
}
interface TailscaleDiscoverCommandOptions {
    port?: number;
    json?: boolean;
}
declare function tailscaleStatusCommand(options?: TailscaleStatusCommandOptions): Promise<TailscaleStatus>;
declare function registerTailscaleStatusCommand(program: Command): void;
declare function tailscaleSyncCommand(options: TailscaleSyncCommandOptions): Promise<TailscaleSyncResult>;
declare function registerTailscaleSyncCommand(program: Command): void;
declare function tailscaleServeCommand(options: TailscaleServeCommandOptions): Promise<void>;
declare function registerTailscaleServeCommand(program: Command): void;
declare function tailscaleDiscoverCommand(options?: TailscaleDiscoverCommandOptions): Promise<TailscalePeer[]>;
declare function registerTailscaleDiscoverCommand(program: Command): void;
declare function registerTailscaleCommands(program: Command): void;

export { type TailscaleDiscoverCommandOptions, type TailscaleServeCommandOptions, type TailscaleStatusCommandOptions, type TailscaleSyncCommandOptions, registerTailscaleCommands, registerTailscaleDiscoverCommand, registerTailscaleServeCommand, registerTailscaleStatusCommand, registerTailscaleSyncCommand, tailscaleDiscoverCommand, tailscaleServeCommand, tailscaleStatusCommand, tailscaleSyncCommand };
