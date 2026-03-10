/**
 * Provenance Module Index
 * 
 * Main export point for the ACP Provenance feature (Issue #40473)
 * 
 * This module provides:
 * - Trace ID generation and management
 * - Metadata capture from ACP ingress
 * - Receipt generation and injection
 * - Session context propagation
 */

// Types
export * from './types';

// Trace ID Generation
export * from './trace';

// Metadata Capture
export * from './metadata';

// Receipt Injection
export * from './receipt';

/**
 * Main Provenance Manager class
 * Combines all provenance functionality
 */
import {
  ProvenanceMode,
  ProvenanceConfig,
  ProvenanceEnvelope,
  SessionTraceContext,
  ACPProvenanceMetadata,
  ACPReceipt,
  DEFAULT_PROVENANCE_CONFIG
} from './types';
import { SessionTraceManager } from './trace';
import { MetadataCapture } from './metadata';
import { ReceiptInjector } from './receipt';

/**
 * Complete Provenance Manager
 * Orchestrates all provenance tracking functionality
 */
export class ProvenanceManager {
  private traceManager: SessionTraceManager;
  private metadataCapture: MetadataCapture;
  private receiptInjector: ReceiptInjector | null = null;
  private config: ProvenanceConfig;
  private initialized = false;
  
  /**
   * Create a new ProvenanceManager
   * @param mode Provenance mode
   * @param config Configuration options
   */
  constructor(mode: ProvenanceMode, config?: Partial<ProvenanceConfig>) {
    this.config = { ...DEFAULT_PROVENANCE_CONFIG, ...config };
    
    // Initialize trace manager
    this.traceManager = new SessionTraceManager(
      mode,
      undefined,
      this.config.traceIdGenerator
    );
    
    // Initialize metadata capture
    this.metadataCapture = new MetadataCapture();
    
    // Initialize receipt injector if mode is not off
    if (mode !== ProvenanceMode.OFF) {
      this.receiptInjector = new ReceiptInjector(
        this.traceManager.getCurrentTraceId(),
        mode,
        this.config.receiptFormat
      );
    }
    
    this.initialized = true;
  }
  
  /**
   * Initialize with parent context (for sub-agents)
   */
  static fromParent(
    parentContext: SessionTraceContext,
    config?: Partial<ProvenanceConfig>
  ): ProvenanceManager {
    const mergedConfig = { ...DEFAULT_PROVENANCE_CONFIG, ...config };
    
    const traceManager = new SessionTraceManager(
      parentContext.mode,
      parentContext,
      mergedConfig.traceIdGenerator
    );
    
    const metadataCapture = new MetadataCapture();
    metadataCapture.captureForSubAgent(parentContext, 'unknown');
    
    const receiptInjector = parentContext.mode !== ProvenanceMode.OFF
      ? new ReceiptInjector(
          traceManager.getCurrentTraceId(),
          parentContext.mode,
          mergedConfig.receiptFormat
        )
      : null;
    
    const manager = new ProvenanceManager(parentContext.mode, config);
    manager.traceManager = traceManager;
    manager.metadataCapture = metadataCapture;
    manager.receiptInjector = receiptInjector;
    
    return manager;
  }
  
  /**
   * Capture ingress metadata
   */
  captureIngress(options: {
    cliArgs?: string[];
    sessionKey?: string;
    gatewayUrl?: string;
  }): void {
    if (!this.initialized) return;
    
    this.metadataCapture.capture({
      mode: this.traceManager.getContext().mode,
      cliArgs: options.cliArgs,
      sessionKey: options.sessionKey,
      gatewayUrl: options.gatewayUrl,
      traceId: this.traceManager.getCurrentTraceId()
    });
  }
  
  /**
   * Inject an ingress receipt
   */
  injectIngress(sessionKey?: string): string | null {
    return this.receiptInjector?.injectIngress(sessionKey) ?? null;
  }
  
  /**
   * Inject agent start receipt
   */
  injectAgentStart(agentId: string): string | null {
    return this.receiptInjector?.injectAgentStart(agentId) ?? null;
  }
  
  /**
   * Inject tool call receipt
   */
  injectToolCall(toolName: string, params?: unknown): string | null {
    return this.receiptInjector?.injectToolCall(toolName, params) ?? null;
  }
  
  /**
   * Inject completion receipt
   */
  injectCompletion(tokenCount?: number): string | null {
    return this.receiptInjector?.injectCompletion(tokenCount) ?? null;
  }
  
  /**
   * Inject error receipt
   */
  injectError(error: Error | string): string | null {
    return this.receiptInjector?.injectError(error) ?? null;
  }
  
  /**
   * Inject sub-agent spawn receipt
   */
  injectSubAgentSpawn(agentId: string): string | null {
    return this.receiptInjector?.injectSubAgentSpawn(
      agentId,
      this.traceManager.getDepth()
    ) ?? null;
  }
  
  /**
   * Get trace context
   */
  getTraceContext(): SessionTraceContext {
    return this.traceManager.getContext();
  }
  
  /**
   * Get metadata
   */
  getMetadata(): ACPProvenanceMetadata | null {
    return this.metadataCapture.getMetadata();
  }
  
  /**
   * Get all receipts
   */
  getReceipts(): ACPReceipt[] {
    return this.receiptInjector?.getReceipts() ?? [];
  }
  
  /**
   * Build provenance envelope for message attachment
   */
  buildEnvelope(): ProvenanceEnvelope | undefined {
    if (this.traceManager.getContext().mode === ProvenanceMode.OFF) {
      return undefined;
    }
    
    return {
      version: '1.0',
      mode: this.traceManager.getContext().mode,
      metadata: this.metadataCapture.getMetadata()!,
      receipts: this.getReceipts(),
      traceContext: this.traceManager.getContext()
    };
  }
  
  /**
   * Check if provenance is active
   */
  isActive(): boolean {
    return this.traceManager.isActive();
  }
  
  /**
   * Check if visible receipts are enabled
   */
  hasVisibleReceipts(): boolean {
    return this.receiptInjector?.hasVisibleReceipts() ?? false;
  }
  
  /**
   * Create child manager for sub-agent
   */
  createChild(): ProvenanceManager {
    return ProvenanceManager.fromParent(
      this.traceManager.getContext(),
      this.config
    );
  }
}

/**
 * Create a provenance manager from CLI flags
 */
export function createProvenanceManager(
  provenanceFlag: string | undefined,
  config?: Partial<ProvenanceConfig>
): ProvenanceManager {
  const { parseProvenanceMode, ProvenanceMode } = require('./types');
  const mode = parseProvenanceMode(provenanceFlag);
  return new ProvenanceManager(mode, config);
}
