/**
 * Provenance Types for ACP/Provenance Feature (Issue #40473)
 * 
 * This module defines the core data structures for provenance tracking
 * in the OpenClaw ACP (Agent Communication Protocol) system.
 */

/**
 * Provenance mode enumeration
 * Controls the level of provenance tracking:
 * - off: No provenance tracking
 * - meta: Metadata and trace IDs only (no visible receipts)
 * - meta+receipt: Full provenance with visible receipts
 */
export enum ProvenanceMode {
  OFF = 'off',
  META = 'meta',
  META_RECEIPT = 'meta+receipt'
}

/**
 * Receipt format options
 */
export enum ReceiptFormat {
  COMPACT = 'compact',
  VERBOSE = 'verbose',
  JSON = 'json'
}

/**
 * Trace ID generator strategies
 */
export enum TraceIdGeneratorType {
  UUID = 'uuid',
  ULID = 'ulid',
  SNOWFLAKE = 'snowflake'
}

/**
 * Receipt operation types
 */
export type ReceiptOperation = 'ingress' | 'processing' | 'completion' | 'error';

/**
 * ACP ingress provenance metadata
 * Captures the origin context of ACP requests
 */
export interface ACPProvenanceMetadata {
  /** Unique trace ID for the entire ACP session chain */
  traceId: string;
  
  /** Timestamp when the ACP request was initiated (ISO 8601) */
  ingressTimestamp: string;
  
  /** Source identifier (e.g., 'cli', 'gateway', 'bridge') */
  source: string;
  
  /** CLI command arguments that initiated the ACP session */
  cliArgs?: string[];
  
  /** Working directory where ACP was invoked */
  workingDirectory?: string;
  
  /** Environment context (sanitized) */
  environment?: ACPEnvironmentContext;
  
  /** Session key/label if provided */
  sessionKey?: string;
  
  /** Gateway URL if remote connection */
  gatewayUrl?: string;
  
  /** Parent trace ID if this is a nested/sub-agent call */
  parentTraceId?: string;
  
  /** Agent ID that processed the request */
  agentId?: string;
}

/**
 * Sanitized environment context
 */
export interface ACPEnvironmentContext {
  /** Shell being used */
  shell: string;
  
  /** User name (optional, may be sanitized) */
  user?: string;
  
  /** Hostname (optional, may be sanitized) */
  hostname?: string;
  
  /** OpenClaw version */
  openclawVersion: string;
}

/**
 * Receipt data structure for visible injection
 */
export interface ACPReceipt {
  /** Receipt unique identifier */
  receiptId: string;
  
  /** Trace ID this receipt belongs to */
  traceId: string;
  
  /** Receipt type/operation */
  operation: ReceiptOperation;
  
  /** Timestamp of the receipt event */
  timestamp: string;
  
  /** Human-readable description */
  description: string;
  
  /** Optional metadata payload */
  metadata?: Record<string, unknown>;
}

/**
 * Session trace context propagated through agent chain
 */
export interface SessionTraceContext {
  /** Root trace ID for the entire session */
  rootTraceId: string;
  
  /** Current span/trace ID in the chain */
  currentTraceId: string;
  
  /** Depth in the agent spawn chain (0 = root) */
  depth: number;
  
  /** Chain of parent trace IDs */
  parentChain: string[];
  
  /** Provenance mode active for this session */
  mode: ProvenanceMode;
}

/**
 * Complete provenance envelope attached to ACP messages
 */
export interface ProvenanceEnvelope {
  /** Schema version */
  version: '1.0';
  
  /** Active provenance mode */
  mode: ProvenanceMode;
  
  /** Ingress metadata */
  metadata: ACPProvenanceMetadata;
  
  /** Receipts generated during the session */
  receipts: ACPReceipt[];
  
  /** Current trace context */
  traceContext: SessionTraceContext;
}

/**
 * Provenance configuration (from plugin config)
 */
export interface ProvenanceConfig {
  /** Default provenance mode */
  defaultMode: ProvenanceMode;
  
  /** Receipt display format */
  receiptFormat: ReceiptFormat;
  
  /** Trace ID generator strategy */
  traceIdGenerator: TraceIdGeneratorType;
  
  /** How long to retain provenance data (hours) */
  retentionHours: number;
}

/**
 * Provenance initialization options
 */
export interface ProvenanceOptions {
  /** Provenance mode (from CLI flag or config) */
  mode: ProvenanceMode;
  
  /** Parent trace context (for sub-agent spawning) */
  parentTraceContext?: SessionTraceContext;
  
  /** Configuration overrides */
  config?: Partial<ProvenanceConfig>;
}

/**
 * Bridge message with provenance support
 */
export interface ProvenanceBridgeMessage {
  /** Message payload */
  payload: unknown;
  
  /** Provenance envelope (optional) */
  provenance?: ProvenanceEnvelope;
  
  /** Trace context for propagation */
  traceContext?: SessionTraceContext;
}

/**
 * Helper type for converting string to ProvenanceMode
 */
export function parseProvenanceMode(value: string | undefined): ProvenanceMode {
  if (!value) {
    return ProvenanceMode.OFF;
  }
  
  const normalized = value.toLowerCase().trim();
  
  switch (normalized) {
    case 'off':
      return ProvenanceMode.OFF;
    case 'meta':
      return ProvenanceMode.META;
    case 'meta+receipt':
    case 'meta_receipt':
    case 'metareceipt':
      return ProvenanceMode.META_RECEIPT;
    default:
      throw new Error(
        `Invalid provenance mode: "${value}". Expected: off|meta|meta+receipt`
      );
  }
}

/**
 * Helper type for converting string to ReceiptFormat
 */
export function parseReceiptFormat(value: string | undefined): ReceiptFormat {
  if (!value) {
    return ReceiptFormat.COMPACT;
  }
  
  const normalized = value.toLowerCase().trim();
  
  switch (normalized) {
    case 'compact':
      return ReceiptFormat.COMPACT;
    case 'verbose':
      return ReceiptFormat.VERBOSE;
    case 'json':
      return ReceiptFormat.JSON;
    default:
      throw new Error(
        `Invalid receipt format: "${value}". Expected: compact|verbose|json`
      );
  }
}

/**
 * Helper type for converting string to TraceIdGeneratorType
 */
export function parseTraceIdGenerator(value: string | undefined): TraceIdGeneratorType {
  if (!value) {
    return TraceIdGeneratorType.ULID;
  }
  
  const normalized = value.toLowerCase().trim();
  
  switch (normalized) {
    case 'uuid':
      return TraceIdGeneratorType.UUID;
    case 'ulid':
      return TraceIdGeneratorType.ULID;
    case 'snowflake':
      return TraceIdGeneratorType.SNOWFLAKE;
    default:
      throw new Error(
        `Invalid trace ID generator: "${value}". Expected: uuid|ulid|snowflake`
      );
  }
}

/**
 * Default provenance configuration
 */
export const DEFAULT_PROVENANCE_CONFIG: ProvenanceConfig = {
  defaultMode: ProvenanceMode.OFF,
  receiptFormat: ReceiptFormat.COMPACT,
  traceIdGenerator: TraceIdGeneratorType.ULID,
  retentionHours: 168 // 7 days
};
