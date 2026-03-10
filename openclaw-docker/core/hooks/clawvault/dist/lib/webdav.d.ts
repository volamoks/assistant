import * as fs from 'fs';
import { IncomingMessage, ServerResponse } from 'http';

/**
 * WebDAV Handler for ClawVault
 *
 * Implements WebDAV protocol support for Obsidian mobile sync via Remotely Save plugin.
 * Uses only Node built-in modules (http, fs, path) - zero external dependencies.
 *
 * Supported methods:
 * - GET: Serve file contents
 * - PUT: Write/create file (creates parent dirs if needed)
 * - DELETE: Delete file or directory
 * - MKCOL: Create directory
 * - PROPFIND: List directory contents or file properties (XML response)
 * - OPTIONS: Return allowed methods + DAV header
 * - HEAD: File metadata without body
 * - MOVE: Rename/move file (uses Destination header)
 * - COPY: Copy file
 */

interface WebDAVConfig {
    /** Root path for WebDAV files (vault path) */
    rootPath: string;
    /** URL prefix for WebDAV routes (default: /webdav) */
    prefix?: string;
    /** Optional Basic Auth credentials */
    auth?: {
        username: string;
        password: string;
    };
}
interface WebDAVRequest {
    method: string;
    path: string;
    headers: Record<string, string | string[] | undefined>;
    body?: string;
}
interface WebDAVResponse {
    status: number;
    headers: Record<string, string>;
    body?: string;
}
declare const WEBDAV_PREFIX = "/webdav";
/**
 * Check if a path is safe (no traversal attacks, not blocked)
 */
declare function isPathSafe(requestPath: string, rootPath: string): boolean;
/**
 * Resolve a WebDAV path to filesystem path
 */
declare function resolveWebDAVPath(requestPath: string, rootPath: string): string | null;
/**
 * Check Basic Auth credentials
 */
declare function checkAuth(req: IncomingMessage, auth?: {
    username: string;
    password: string;
}): boolean;
/**
 * Generate full PROPFIND response XML
 */
declare function generatePropfindResponse(entries: Array<{
    href: string;
    stats: fs.Stats | null;
    isCollection: boolean;
}>): string;
/**
 * Handle OPTIONS request
 */
declare function handleOptions(res: ServerResponse, prefix: string): void;
/**
 * Handle HEAD request
 */
declare function handleHead(res: ServerResponse, filePath: string): void;
/**
 * Handle GET request
 */
declare function handleGet(res: ServerResponse, filePath: string): void;
/**
 * Handle PUT request
 */
declare function handlePut(res: ServerResponse, filePath: string, body: Buffer): void;
/**
 * Handle DELETE request
 */
declare function handleDelete(res: ServerResponse, filePath: string): void;
/**
 * Handle MKCOL request (create directory)
 */
declare function handleMkcol(res: ServerResponse, filePath: string): void;
/**
 * Handle PROPFIND request
 */
declare function handlePropfind(res: ServerResponse, filePath: string, webdavPath: string, prefix: string, depth: string): void;
/**
 * Handle MOVE request
 */
declare function handleMove(res: ServerResponse, sourcePath: string, destinationPath: string | null, overwrite: boolean): void;
/**
 * Handle COPY request
 */
declare function handleCopy(res: ServerResponse, sourcePath: string, destinationPath: string | null, overwrite: boolean): void;
/**
 * Create WebDAV request handler
 */
declare function createWebDAVHandler(config: WebDAVConfig): (req: IncomingMessage, res: ServerResponse) => Promise<boolean>;

export { WEBDAV_PREFIX, type WebDAVConfig, type WebDAVRequest, type WebDAVResponse, checkAuth, createWebDAVHandler, generatePropfindResponse, handleCopy, handleDelete, handleGet, handleHead, handleMkcol, handleMove, handleOptions, handlePropfind, handlePut, isPathSafe, resolveWebDAVPath };
