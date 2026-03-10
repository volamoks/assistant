/**
 * Compatibility bridge for plugin-sdk context-engine symbols.
 *
 * This module intentionally exports only stable plugin-sdk surface area.
 */

export type {
  ContextEngine,
  ContextEngineInfo,
  AssembleResult,
  CompactResult,
  IngestResult,
  IngestBatchResult,
  BootstrapResult,
  SubagentSpawnPreparation,
  SubagentEndReason,
} from "openclaw/plugin-sdk";

export {
  registerContextEngine,
  type ContextEngineFactory,
} from "openclaw/plugin-sdk";

// Provenance types for ACP/Provenance feature (Issue #40473)
export type {
  ProvenanceMode,
  ReceiptFormat,
  TraceIdGeneratorType,
  ReceiptOperation,
  ACPProvenanceMetadata,
  ACPEnvironmentContext,
  ACPReceipt,
  SessionTraceContext,
  ProvenanceEnvelope,
  ProvenanceConfig,
  ProvenanceOptions,
  ProvenanceBridgeMessage,
} from "./provenance/types";

export {
  parseProvenanceMode,
  parseReceiptFormat,
  parseTraceIdGenerator,
  DEFAULT_PROVENANCE_CONFIG,
} from "./provenance/types";

export { TraceIdGenerator, SessionTraceManager } from "./provenance/trace";
export { MetadataCapture } from "./provenance/metadata";
export { ReceiptInjector } from "./provenance/receipt";
export { ProvenanceManager } from "./provenance/index";
