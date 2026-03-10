import { ChildProcess } from 'child_process';
import * as http from 'http';

/**
 * Tailscale Integration for ClawVault
 *
 * Provides native Tailscale networking capabilities for vault synchronization
 * across devices on a Tailscale network (tailnet).
 *
 * Features:
 * - Tailscale status detection and peer discovery
 * - MagicDNS hostname resolution
 * - Secure peer-to-peer vault sync
 * - Tailscale Funnel/Serve integration for vault sharing
 */

interface TailscaleStatus {
    /** Whether Tailscale is installed */
    installed: boolean;
    /** Whether Tailscale daemon is running */
    running: boolean;
    /** Whether connected to tailnet */
    connected: boolean;
    /** Current device's Tailscale IP */
    selfIP?: string;
    /** Current device's MagicDNS hostname */
    selfHostname?: string;
    /** Current device's full domain name */
    selfDNSName?: string;
    /** Tailnet name */
    tailnetName?: string;
    /** Backend state (Running, Stopped, etc.) */
    backendState?: string;
    /** List of peers on the tailnet */
    peers: TailscalePeer[];
    /** Error message if any */
    error?: string;
}
interface TailscalePeer {
    /** Peer's hostname */
    hostname: string;
    /** Peer's MagicDNS name */
    dnsName: string;
    /** Peer's Tailscale IP addresses */
    tailscaleIPs: string[];
    /** Whether peer is currently online */
    online: boolean;
    /** Operating system */
    os?: string;
    /** Whether this peer is the exit node */
    exitNode?: boolean;
    /** Whether this peer is a tagged device */
    tags?: string[];
    /** Last seen timestamp */
    lastSeen?: string;
    /** Whether peer is running ClawVault serve */
    clawvaultServing?: boolean;
    /** ClawVault serve port if detected */
    clawvaultPort?: number;
}
interface TailscaleServeConfig {
    /** Port to serve on (default: 8384) */
    port?: number;
    /** Whether to use HTTPS (via Tailscale) */
    https?: boolean;
    /** Whether to expose via Tailscale Funnel (public internet) */
    funnel?: boolean;
    /** Path prefix for the serve endpoint */
    pathPrefix?: string;
    /** Optional WebDAV Basic Auth credentials */
    webdavAuth?: {
        username: string;
        password: string;
    };
}
interface TailscaleSyncOptions {
    /** Target peer hostname or IP */
    peer: string;
    /** Port on the peer (default: 8384) */
    port?: number;
    /** Direction: push, pull, or bidirectional */
    direction?: 'push' | 'pull' | 'bidirectional';
    /** Dry run - don't actually sync */
    dryRun?: boolean;
    /** Delete files on target that don't exist on source */
    deleteOrphans?: boolean;
    /** Categories to sync (default: all) */
    categories?: string[];
    /** Use HTTPS for connection */
    https?: boolean;
}
interface TailscaleSyncResult {
    /** Files pushed to peer */
    pushed: string[];
    /** Files pulled from peer */
    pulled: string[];
    /** Files deleted */
    deleted: string[];
    /** Files unchanged */
    unchanged: string[];
    /** Errors encountered */
    errors: string[];
    /** Sync statistics */
    stats: {
        bytesTransferred: number;
        filesProcessed: number;
        duration: number;
    };
}
interface VaultManifest {
    /** Vault name */
    name: string;
    /** Vault version */
    version: string;
    /** Last updated timestamp */
    lastUpdated: string;
    /** File manifest with checksums */
    files: VaultFileEntry[];
}
interface VaultFileEntry {
    /** Relative path */
    path: string;
    /** File size in bytes */
    size: number;
    /** Last modified timestamp */
    modified: string;
    /** SHA-256 checksum */
    checksum: string;
    /** Category */
    category: string;
}
declare const DEFAULT_SERVE_PORT = 8384;
declare const CLAWVAULT_SERVE_PATH = "/.clawvault";
declare const MANIFEST_ENDPOINT = "/.clawvault/manifest";
declare const SYNC_ENDPOINT = "/.clawvault/sync";
declare const FILE_ENDPOINT = "/.clawvault/files";
/**
 * Check if Tailscale CLI is installed
 */
declare function hasTailscale(): boolean;
/**
 * Get Tailscale version
 */
declare function getTailscaleVersion(): string | null;
/**
 * Get comprehensive Tailscale status
 */
declare function getTailscaleStatus(): TailscaleStatus;
/**
 * Find a peer by hostname (partial match supported)
 */
declare function findPeer(hostname: string): TailscalePeer | null;
/**
 * Get online peers only
 */
declare function getOnlinePeers(): TailscalePeer[];
/**
 * Resolve a peer hostname to its Tailscale IP
 */
declare function resolvePeerIP(hostname: string): string | null;
/**
 * Generate vault manifest for synchronization
 */
declare function generateVaultManifest(vaultPath: string): VaultManifest;
/**
 * Compare two manifests and return differences
 */
declare function compareManifests(local: VaultManifest, remote: VaultManifest): {
    toPush: VaultFileEntry[];
    toPull: VaultFileEntry[];
    conflicts: Array<{
        path: string;
        local: VaultFileEntry;
        remote: VaultFileEntry;
    }>;
    unchanged: string[];
};
interface ServeInstance {
    server: http.Server;
    port: number;
    stop: () => Promise<void>;
}
/**
 * Start serving a vault over HTTP for Tailscale sync
 * Includes WebDAV support at /webdav/ for Obsidian mobile sync
 */
declare function serveVault(vaultPath: string, options?: TailscaleServeConfig): ServeInstance;
/**
 * Fetch remote vault manifest
 */
declare function fetchRemoteManifest(host: string, port?: number, useHttps?: boolean): Promise<VaultManifest>;
/**
 * Fetch a file from remote vault
 */
declare function fetchRemoteFile(host: string, filePath: string, port?: number, useHttps?: boolean): Promise<string>;
/**
 * Push a file to remote vault
 */
declare function pushFileToRemote(host: string, filePath: string, content: string, port?: number, useHttps?: boolean): Promise<void>;
/**
 * Sync vault with a remote peer
 */
declare function syncWithPeer(vaultPath: string, options: TailscaleSyncOptions): Promise<TailscaleSyncResult>;
/**
 * Configure Tailscale serve for the vault
 * This uses `tailscale serve` to expose the vault server via Tailscale's HTTPS
 */
declare function configureTailscaleServe(localPort: number, options?: {
    funnel?: boolean;
    background?: boolean;
}): ChildProcess | null;
/**
 * Stop Tailscale serve
 */
declare function stopTailscaleServe(): boolean;
/**
 * Check if a peer is serving ClawVault
 */
declare function checkPeerClawVault(host: string, port?: number): Promise<boolean>;
/**
 * Discover ClawVault peers on the tailnet
 */
declare function discoverClawVaultPeers(port?: number): Promise<TailscalePeer[]>;

export { CLAWVAULT_SERVE_PATH, DEFAULT_SERVE_PORT, FILE_ENDPOINT, MANIFEST_ENDPOINT, SYNC_ENDPOINT, type ServeInstance, type TailscalePeer, type TailscaleServeConfig, type TailscaleStatus, type TailscaleSyncOptions, type TailscaleSyncResult, type VaultFileEntry, type VaultManifest, checkPeerClawVault, compareManifests, configureTailscaleServe, discoverClawVaultPeers, fetchRemoteFile, fetchRemoteManifest, findPeer, generateVaultManifest, getOnlinePeers, getTailscaleStatus, getTailscaleVersion, hasTailscale, pushFileToRemote, resolvePeerIP, serveVault, stopTailscaleServe, syncWithPeer };
