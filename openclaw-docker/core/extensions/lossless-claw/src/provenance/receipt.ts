/**
 * Receipt Injector for ACP/Provenance Feature (Issue #40473)
 * 
 * This module handles receipt generation and injection for provenance tracking.
 * Receipts provide visible provenance information in the conversation flow.
 */

import { ulid } from 'ulid';
import {
  ACPReceipt,
  ReceiptOperation,
  ProvenanceMode,
  ReceiptFormat,
  SessionTraceContext,
  parseReceiptFormat
} from './types';

/**
 * Receipt Injector class
 * Manages receipt generation and formatting for provenance tracking
 */
export class ReceiptInjector {
  private receipts: ACPReceipt[] = [];
  private traceId: string;
  private mode: ProvenanceMode;
  private receiptFormat: ReceiptFormat;
  
  /**
   * Create a new ReceiptInjector
   * @param traceId Trace ID for this session
   * @param mode Provenance mode
   * @param receiptFormat Format for receipt display
   */
  constructor(
    traceId: string,
    mode: ProvenanceMode,
    receiptFormat: ReceiptFormat = ReceiptFormat.COMPACT
  ) {
    this.traceId = traceId;
    this.mode = mode;
    this.receiptFormat = receiptFormat;
  }
  
  /**
   * Inject a receipt into the conversation
   * Returns formatted receipt string for meta+receipt mode
   * @param receipt Receipt data (without receiptId and traceId)
   * @returns Formatted receipt string or null (if mode is off or meta)
   */
  inject(receipt: Omit<ACPReceipt, 'receiptId' | 'traceId'>): string | null {
    if (this.mode === ProvenanceMode.OFF) {
      return null;
    }
    
    const fullReceipt: ACPReceipt = {
      ...receipt,
      receiptId: this.generateReceiptId(),
      traceId: this.traceId,
      timestamp: new Date().toISOString()
    };
    
    this.receipts.push(fullReceipt);
    
    // Only return visible receipt for meta+receipt mode
    if (this.mode === ProvenanceMode.META_RECEIPT) {
      return this.formatReceipt(fullReceipt);
    }
    
    return null;
  }
  
  /**
   * Inject ingress receipt
   */
  injectIngress(sessionKey?: string): string | null {
    return this.inject({
      operation: 'ingress',
      description: `ACP session started${sessionKey ? `: ${sessionKey}` : ''}`,
      metadata: {
        sessionKey
      }
    });
  }
  
  /**
   * Inject processing receipt (agent start)
   */
  injectAgentStart(agentId: string): string | null {
    return this.inject({
      operation: 'processing',
      description: `Agent ${agentId} started processing`,
      metadata: { agentId }
    });
  }
  
  /**
   * Inject processing receipt (tool call)
   */
  injectToolCall(toolName: string, params?: unknown): string | null {
    return this.inject({
      operation: 'processing',
      description: `Tool invoked: ${toolName}`,
      metadata: { toolName, hasParams: !!params }
    });
  }
  
  /**
   * Inject completion receipt
   */
  injectCompletion(tokenCount?: number): string | null {
    return this.inject({
      operation: 'completion',
      description: tokenCount !== undefined 
        ? `Response generated (${tokenCount} tokens)`
        : 'Response generated',
      metadata: { tokenCount }
    });
  }
  
  /**
   * Inject error receipt
   */
  injectError(error: Error | string): string | null {
    const message = typeof error === 'string' ? error : error.message;
    const errorType = typeof error === 'string' ? 'Error' : error.name;
    
    return this.inject({
      operation: 'error',
      description: `Error: ${message}`,
      metadata: { errorType }
    });
  }
  
  /**
   * Inject sub-agent spawn receipt
   */
  injectSubAgentSpawn(agentId: string, depth: number): string | null {
    return this.inject({
      operation: 'processing',
      description: `Sub-agent spawned: ${agentId} (depth: ${depth})`,
      metadata: { agentId, depth }
    });
  }
  
  /**
   * Format receipt for visible injection into conversation
   */
  private formatReceipt(receipt: ACPReceipt): string {
    switch (this.receiptFormat) {
      case ReceiptFormat.COMPACT:
        return this.formatCompact(receipt);
      case ReceiptFormat.VERBOSE:
        return this.formatVerbose(receipt);
      case ReceiptFormat.JSON:
        return this.formatJson(receipt);
      default:
        return this.formatCompact(receipt);
    }
  }
  
  /**
   * Format receipt in compact mode
   * Example: [ingress] ACP session started
   */
  private formatCompact(receipt: ACPReceipt): string {
    return `[${receipt.operation}] ${receipt.description}`;
  }
  
  /**
   * Format receipt in verbose mode
   * Example: [2024-01-15T10:30:00.000Z] [ingress] ACP session started
   */
  private formatVerbose(receipt: ACPReceipt): string {
    return `[${receipt.timestamp}] [${receipt.operation}] ${receipt.description}`;
  }
  
  /**
   * Format receipt as JSON
   */
  private formatJson(receipt: ACPReceipt): string {
    return JSON.stringify(receipt);
  }
  
  /**
   * Generate a unique receipt ID
   */
  private generateReceiptId(): string {
    return `rcpt_${ulid()}`;
  }
  
  /**
   * Get all receipts (for metadata attachment)
   */
  getReceipts(): ACPReceipt[] {
    return [...this.receipts];
  }
  
  /**
   * Get receipt count
   */
  getReceiptCount(): number {
    return this.receipts.length;
  }
  
  /**
   * Clear all receipts
   */
  clear(): void {
    this.receipts = [];
  }
  
  /**
   * Check if provenance is active
   */
  isActive(): boolean {
    return this.mode !== ProvenanceMode.OFF;
  }
  
  /**
   * Check if visible receipts are enabled
   */
  hasVisibleReceipts(): boolean {
    return this.mode === ProvenanceMode.META_RECEIPT;
  }
}

/**
 * Create a receipt injector from trace context
 */
export function createReceiptInjector(
  traceContext: SessionTraceContext,
  receiptFormat?: string
): ReceiptInjector {
  const format = receiptFormat ? parseReceiptFormat(receiptFormat) : ReceiptFormat.COMPACT;
  
  return new ReceiptInjector(
    traceContext.currentTraceId,
    traceContext.mode,
    format
  );
}

/**
 * Create a receipt injector from mode and trace ID
 */
export function createReceiptInjectorFromMode(
  mode: ProvenanceMode,
  traceId: string,
  receiptFormat?: string
): ReceiptInjector | null {
  if (mode === ProvenanceMode.OFF) {
    return null;
  }
  
  const format = receiptFormat ? parseReceiptFormat(receiptFormat) : ReceiptFormat.COMPACT;
  return new ReceiptInjector(traceId, mode, format);
}
