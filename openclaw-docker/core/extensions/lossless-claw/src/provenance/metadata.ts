/**
 * Metadata Capture for ACP/Provenance Feature (Issue #40473)
 * 
 * This module handles capture and management of ACP ingress provenance metadata.
 */

import os from 'os';
import { execSync } from 'child_process';
import {
  ACPProvenanceMetadata,
  ACPEnvironmentContext,
  ProvenanceMode,
  SessionTraceContext
} from './types';
import { TraceIdGenerator, SessionTraceManager } from './trace';

/**
 * Capture sanitized environment context
 * Removes potentially sensitive information
 */
function captureEnvironmentContext(): ACPEnvironmentContext {
  let shell = 'unknown';
  let hostname: string | undefined;
  
  try {
    // Get shell
    shell = process.env.SHELL || process.env.COMSPEC || 'unknown';
    shell = shell.split('/').pop() || shell;
    
    // Get hostname (optional, may be stripped in some environments)
    try {
      hostname = os.hostname();
    } catch {
      // Ignore if not available
    }
  } catch {
    // Use defaults
  }
  
  return {
    shell,
    user: process.env.USER || process.env.USERNAME,
    hostname,
    openclawVersion: getOpenClawVersion()
  };
}

/**
 * Get OpenClaw version from package or environment
 */
function getOpenClawVersion(): string {
  // Try to get from environment variable first
  if (process.env.OPENCLAW_VERSION) {
    return process.env.OPENCLAW_VERSION;
  }
  
  // Try to get from package.json (common locations)
  try {
    // This would be resolved at runtime
    return process.env.npm_package_version || 'unknown';
  } catch {
    return 'unknown';
  }
}

/**
 * Metadata Capture class
 * Handles extraction and management of ACP ingress metadata
 */
export class MetadataCapture {
  private metadata: ACPProvenanceMetadata | null = null;
  private captured = false;
  
  /**
   * Capture ingress metadata for a new ACP session
   * @param options Provenance options
   */
  capture(options: {
    mode: ProvenanceMode;
    cliArgs?: string[];
    sessionKey?: string;
    gatewayUrl?: string;
    traceId?: string;
  }): ACPProvenanceMetadata | null {
    if (options.mode === ProvenanceMode.OFF) {
      return null;
    }
    
    this.metadata = {
      traceId: options.traceId || '',
      ingressTimestamp: new Date().toISOString(),
      source: 'cli',
      cliArgs: options.cliArgs,
      workingDirectory: process.cwd(),
      environment: captureEnvironmentContext(),
      sessionKey: options.sessionKey,
      gatewayUrl: options.gatewayUrl
    };
    
    this.captured = true;
    return this.metadata;
  }
  
  /**
   * Capture metadata for a sub-agent session
   * @param parentContext Parent trace context
   * @param agentId Agent ID
   */
  captureForSubAgent(
    parentContext: SessionTraceContext,
    agentId: string
  ): ACPProvenanceMetadata | null {
    if (parentContext.mode === ProvenanceMode.OFF) {
      return null;
    }
    
    this.metadata = {
      traceId: parentContext.currentTraceId,
      ingressTimestamp: new Date().toISOString(),
      source: 'subagent',
      parentTraceId: parentContext.rootTraceId,
      agentId,
      environment: captureEnvironmentContext()
    };
    
    this.captured = true;
    return this.metadata;
  }
  
  /**
   * Get captured metadata
   */
  getMetadata(): ACPProvenanceMetadata | null {
    return this.metadata ? { ...this.metadata } : null;
  }
  
  /**
   * Check if metadata has been captured
   */
  hasCaptured(): boolean {
    return this.captured;
  }
  
  /**
   * Update metadata with additional information
   */
  updateMetadata(updates: Partial<ACPProvenanceMetadata>): void {
    if (this.metadata) {
      this.metadata = { ...this.metadata, ...updates };
    }
  }
  
  /**
   * Serialize metadata for propagation
   */
  serialize(): string | null {
    if (!this.metadata) {
      return null;
    }
    return JSON.stringify(this.metadata);
  }
  
  /**
   * Deserialize metadata from incoming request
   */
  static deserialize(serialized: string): ACPProvenanceMetadata {
    return JSON.parse(serialized);
  }
}

/**
 * Create a metadata capture instance
 */
export function createMetadataCapture(): MetadataCapture {
  return new MetadataCapture();
}

/**
 * Capture metadata from CLI context
 */
export function captureCliMetadata(
  mode: ProvenanceMode,
  sessionKey?: string,
  gatewayUrl?: string
): ACPProvenanceMetadata | null {
  const capture = new MetadataCapture();
  
  // Generate trace ID if needed
  let traceId: string | undefined;
  if (mode !== ProvenanceMode.OFF) {
    const generator = new TraceIdGenerator();
    traceId = generator.generate();
  }
  
  return capture.capture({
    mode,
    cliArgs: process.argv.slice(2),
    sessionKey,
    gatewayUrl,
    traceId
  });
}
