/**
 * Trace ID Generator for ACP/Provenance Feature (Issue #40473)
 * 
 * This module provides trace ID generation strategies for session tracking
 * and propagation through agent chains.
 */

import { ulid } from 'ulid';
import { v4 as uuidv4 } from 'uuid';
import {
  TraceIdGeneratorType,
  SessionTraceContext,
  ProvenanceMode,
  parseTraceIdGenerator
} from './types';

/**
 * Trace ID Generator class
 * Supports multiple generation strategies: UUID, ULID, Snowflake
 */
export class TraceIdGenerator {
  private strategy: TraceIdGeneratorType;
  
  constructor(strategy: TraceIdGeneratorType = TraceIdGeneratorType.ULID) {
    this.strategy = strategy;
  }
  
  /**
   * Generate a new trace ID with the configured strategy
   * @returns Trace ID prefixed with 'tr_'
   */
  generate(): string {
    switch (this.strategy) {
      case TraceIdGeneratorType.UUID:
        return `tr_${uuidv4()}`;
      case TraceIdGeneratorType.ULID:
        return `tr_${ulid()}`;
      case TraceIdGeneratorType.SNOWFLAKE:
        return `tr_${this.generateSnowflake()}`;
      default:
        return `tr_${ulid()}`;
    }
  }
  
  /**
   * Generate a Twitter-style snowflake ID
   */
  private generateSnowflake(): string {
    const timestamp = Date.now();
    const random = Math.floor(Math.random() * 4096);
    return `${timestamp}${random.toString(16).padStart(3, '0')}`;
  }
}

/**
 * Session Trace Manager
 * Manages trace context for ACP sessions and sub-agent spawning
 */
export class SessionTraceManager {
  private context: SessionTraceContext;
  private generator: TraceIdGenerator;
  
  /**
   * Create a new SessionTraceManager
   * @param mode Provenance mode for this session
   * @param parentContext Parent trace context (for sub-agents)
   * @param generatorStrategy Trace ID generation strategy
   */
  constructor(
    mode: ProvenanceMode,
    parentContext?: SessionTraceContext,
    generatorStrategy: TraceIdGeneratorType = TraceIdGeneratorType.ULID
  ) {
    this.generator = new TraceIdGenerator(generatorStrategy);
    
    if (parentContext && mode !== ProvenanceMode.OFF) {
      // Child session - inherit from parent
      const newTraceId = this.generator.generate();
      this.context = {
        rootTraceId: parentContext.rootTraceId,
        currentTraceId: newTraceId,
        depth: parentContext.depth + 1,
        parentChain: [...parentContext.parentChain, parentContext.currentTraceId],
        mode
      };
    } else if (mode !== ProvenanceMode.OFF) {
      // Root session
      const rootTraceId = this.generator.generate();
      this.context = {
        rootTraceId,
        currentTraceId: rootTraceId,
        depth: 0,
        parentChain: [],
        mode
      };
    } else {
      // OFF mode - create placeholder context
      this.context = {
        rootTraceId: '',
        currentTraceId: '',
        depth: 0,
        parentChain: [],
        mode: ProvenanceMode.OFF
      };
    }
  }
  
  /**
   * Get the current trace context (immutable copy)
   */
  getContext(): SessionTraceContext {
    return { ...this.context };
  }
  
  /**
   * Get the current trace ID
   */
  getCurrentTraceId(): string {
    return this.context.currentTraceId;
  }
  
  /**
   * Get the root trace ID
   */
  getRootTraceId(): string {
    return this.context.rootTraceId;
  }
  
  /**
   * Get the depth in the agent chain
   */
  getDepth(): number {
    return this.context.depth;
  }
  
  /**
   * Check if provenance is active
   */
  isActive(): boolean {
    return this.context.mode !== ProvenanceMode.OFF;
  }
  
  /**
   * Serialize trace context for propagation
   */
  serialize(): string {
    return JSON.stringify(this.context);
  }
  
  /**
   * Deserialize trace context from incoming request
   */
  static deserialize(serialized: string): SessionTraceContext {
    return JSON.parse(serialized);
  }
  
  /**
   * Create a child trace manager for sub-agent spawning
   * Returns a new manager with inherited trace context
   */
  createChildTrace(): SessionTraceManager {
    if (this.context.mode === ProvenanceMode.OFF) {
      return new SessionTraceManager(ProvenanceMode.OFF);
    }
    return new SessionTraceManager(
      this.context.mode,
      this.context,
      TraceIdGeneratorType.ULID // Could make configurable
    );
  }
  
  /**
   * Create trace context from CLI arguments
   */
  static fromCliArgs(
    args: string[],
    generatorStrategy?: string
  ): { traceId: string; cliArgs: string[] } {
    const strategy = generatorStrategy 
      ? parseTraceIdGenerator(generatorStrategy)
      : TraceIdGeneratorType.ULID;
    
    const generator = new TraceIdGenerator(strategy);
    return {
      traceId: generator.generate(),
      cliArgs: args
    };
  }
}

/**
 * Create a trace manager from provenance options
 */
export function createTraceManager(
  mode: ProvenanceMode,
  parentTraceContext?: SessionTraceContext,
  generatorType?: string
): SessionTraceManager {
  const generatorStrategy = generatorType 
    ? parseTraceIdGenerator(generatorType)
    : TraceIdGeneratorType.ULID;
  
  return new SessionTraceManager(mode, parentTraceContext, generatorStrategy);
}
