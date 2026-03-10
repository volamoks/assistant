/**
 * Provenance Module for ACP Server Integration
 * 
 * This is a JavaScript version of the provenance module that can be
 * integrated directly into the acpx ACP server.
 * 
 * Usage:
 *   const { ProvenanceManager, parseProvenanceMode } = require('./provenance');
 *   
 *   // Parse CLI flag
 *   const mode = parseProvenanceMode(process.argv.includes('--provenance') 
 *     ? process.argv[process.argv.indexOf('--provenance') + 1] 
 *     : undefined);
 *   
 *   // Create manager
 *   const provenance = new ProvenanceManager(mode);
 *   
 *   // Capture ingress
 *   provenance.captureIngress({ sessionKey: 'my-session' });
 *   
 *   // Inject receipts at key points
 *   provenance.injectIngress('my-session');
 *   provenance.injectToolCall('read_file');
 *   provenance.injectCompletion();
 *   
 *   // Get envelope for message attachment
 *   const envelope = provenance.buildEnvelope();
 */

// Provenance Mode Enumeration
const ProvenanceMode = {
  OFF: 'off',
  META: 'meta',
  META_RECEIPT: 'meta+receipt'
};

// Receipt Format Enumeration
const ReceiptFormat = {
  COMPACT: 'compact',
  VERBOSE: 'verbose',
  JSON: 'json'
};

/**
 * Parse provenance mode from CLI flag
 */
function parseProvenanceMode(value) {
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
 * Generate a ULID-style ID
 */
function generateId(prefix = '') {
  const now = Date.now();
  const random = Math.random().toString(36).substring(2, 15);
  const random2 = Math.random().toString(36).substring(2, 15);
  return prefix ? `${prefix}_${now}${random}${random2}` : `${now}${random}${random2}`;
}

/**
 * Provenance Manager Class
 */
class ProvenanceManager {
  constructor(mode = ProvenanceMode.OFF, options = {}) {
    this.mode = mode;
    this.traceId = mode !== ProvenanceMode.OFF ? generateId('tr') : '';
    this.receipts = [];
    this.metadata = null;
    this.receiptFormat = options.receiptFormat || ReceiptFormat.COMPACT;
    this.traceContext = {
      rootTraceId: this.traceId,
      currentTraceId: this.traceId,
      depth: 0,
      parentChain: [],
      mode: this.mode
    };
  }
  
  /**
   * Capture ingress metadata
   */
  captureIngress(options = {}) {
    if (this.mode === ProvenanceMode.OFF) {
      return;
    }
    
    this.metadata = {
      traceId: this.traceId,
      ingressTimestamp: new Date().toISOString(),
      source: 'cli',
      cliArgs: options.cliArgs || process.argv.slice(2),
      workingDirectory: options.workingDirectory || process.cwd(),
      environment: {
        shell: process.env.SHELL || 'unknown',
        user: process.env.USER,
        hostname: require('os').hostname(),
        openclawVersion: process.env.OPENCLAW_VERSION || 'unknown'
      },
      sessionKey: options.sessionKey,
      gatewayUrl: options.gatewayUrl
    };
  }
  
  /**
   * Create a child trace for sub-agents
   */
  createChild() {
    const child = new ProvenanceManager(this.mode, { receiptFormat: this.receiptFormat });
    child.traceId = generateId('tr');
    child.traceContext = {
      rootTraceId: this.traceContext.rootTraceId,
      currentTraceId: child.traceId,
      depth: this.traceContext.depth + 1,
      parentChain: [...this.traceContext.parentChain, this.traceId],
      mode: this.mode
    };
    child.metadata = {
      ...this.metadata,
      traceId: child.traceId,
      source: 'subagent',
      parentTraceId: this.traceId
    };
    return child;
  }
  
  /**
   * Generate a receipt ID
   */
  _generateReceiptId() {
    return generateId('rcpt');
  }
  
  /**
   * Format a receipt based on current format setting
   */
  _formatReceipt(receipt) {
    switch (this.receiptFormat) {
      case ReceiptFormat.COMPACT:
        return `[${receipt.operation}] ${receipt.description}`;
      case ReceiptFormat.VERBOSE:
        return `[${receipt.timestamp}] [${receipt.operation}] ${receipt.description}`;
      case ReceiptFormat.JSON:
        return JSON.stringify(receipt);
      default:
        return `[${receipt.operation}] ${receipt.description}`;
    }
  }
  
  /**
   * Inject an ingress receipt
   */
  injectIngress(sessionKey) {
    if (this.mode === ProvenanceMode.OFF) {
      return null;
    }
    
    const receipt = {
      receiptId: this._generateReceiptId(),
      traceId: this.traceId,
      operation: 'ingress',
      timestamp: new Date().toISOString(),
      description: `ACP session started${sessionKey ? `: ${sessionKey}` : ''}`,
      metadata: { sessionKey }
    };
    
    this.receipts.push(receipt);
    
    if (this.mode === ProvenanceMode.META_RECEIPT) {
      return this._formatReceipt(receipt);
    }
    return null;
  }
  
  /**
   * Inject agent start receipt
   */
  injectAgentStart(agentId) {
    if (this.mode === ProvenanceMode.OFF) {
      return null;
    }
    
    const receipt = {
      receiptId: this._generateReceiptId(),
      traceId: this.traceId,
      operation: 'processing',
      timestamp: new Date().toISOString(),
      description: `Agent ${agentId} started processing`,
      metadata: { agentId }
    };
    
    this.receipts.push(receipt);
    
    if (this.mode === ProvenanceMode.META_RECEIPT) {
      return this._formatReceipt(receipt);
    }
    return null;
  }
  
  /**
   * Inject tool call receipt
   */
  injectToolCall(toolName, params) {
    if (this.mode === ProvenanceMode.OFF) {
      return null;
    }
    
    const receipt = {
      receiptId: this._generateReceiptId(),
      traceId: this.traceId,
      operation: 'processing',
      timestamp: new Date().toISOString(),
      description: `Tool invoked: ${toolName}`,
      metadata: { toolName, hasParams: !!params }
    };
    
    this.receipts.push(receipt);
    
    if (this.mode === ProvenanceMode.META_RECEIPT) {
      return this._formatReceipt(receipt);
    }
    return null;
  }
  
  /**
   * Inject completion receipt
   */
  injectCompletion(tokenCount) {
    if (this.mode === ProvenanceMode.OFF) {
      return null;
    }
    
    const receipt = {
      receiptId: this._generateReceiptId(),
      traceId: this.traceId,
      operation: 'completion',
      timestamp: new Date().toISOString(),
      description: tokenCount !== undefined 
        ? `Response generated (${tokenCount} tokens)`
        : 'Response generated',
      metadata: { tokenCount }
    };
    
    this.receipts.push(receipt);
    
    if (this.mode === ProvenanceMode.META_RECEIPT) {
      return this._formatReceipt(receipt);
    }
    return null;
  }
  
  /**
   * Inject error receipt
   */
  injectError(error) {
    if (this.mode === ProvenanceMode.OFF) {
      return null;
    }
    
    const message = error instanceof Error ? error.message : String(error);
    const errorType = error instanceof Error ? error.name : 'Error';
    
    const receipt = {
      receiptId: this._generateReceiptId(),
      traceId: this.traceId,
      operation: 'error',
      timestamp: new Date().toISOString(),
      description: `Error: ${message}`,
      metadata: { errorType }
    };
    
    this.receipts.push(receipt);
    
    if (this.mode === ProvenanceMode.META_RECEIPT) {
      return this._formatReceipt(receipt);
    }
    return null;
  }
  
  /**
   * Inject sub-agent spawn receipt
   */
  injectSubAgentSpawn(agentId) {
    if (this.mode === ProvenanceMode.OFF) {
      return null;
    }
    
    const receipt = {
      receiptId: this._generateReceiptId(),
      traceId: this.traceId,
      operation: 'processing',
      timestamp: new Date().toISOString(),
      description: `Sub-agent spawned: ${agentId} (depth: ${this.traceContext.depth})`,
      metadata: { agentId, depth: this.traceContext.depth }
    };
    
    this.receipts.push(receipt);
    
    if (this.mode === ProvenanceMode.META_RECEIPT) {
      return this._formatReceipt(receipt);
    }
    return null;
  }
  
  /**
   * Get trace context
   */
  getTraceContext() {
    return { ...this.traceContext };
  }
  
  /**
   * Get metadata
   */
  getMetadata() {
    return this.metadata ? { ...this.metadata } : null;
  }
  
  /**
   * Get all receipts
   */
  getReceipts() {
    return [...this.receipts];
  }
  
  /**
   * Build provenance envelope for message attachment
   */
  buildEnvelope() {
    if (this.mode === ProvenanceMode.OFF) {
      return undefined;
    }
    
    return {
      version: '1.0',
      mode: this.mode,
      metadata: this.metadata,
      receipts: this.receipts,
      traceContext: this.traceContext
    };
  }
  
  /**
   * Check if provenance is active
   */
  isActive() {
    return this.mode !== ProvenanceMode.OFF;
  }
  
  /**
   * Check if visible receipts are enabled
   */
  hasVisibleReceipts() {
    return this.mode === ProvenanceMode.META_RECEIPT;
  }
}

module.exports = {
  ProvenanceMode,
  ReceiptFormat,
  parseProvenanceMode,
  ProvenanceManager,
  generateId
};
