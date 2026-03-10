import {
  buildSessionRecap,
  formatSessionRecapMarkdown,
  sessionRecapCommand
} from "./chunk-ZKGY7WTT.js";
import {
  setupCommand
} from "./chunk-RVYA52PY.js";
import {
  registerSyncBdCommand,
  syncBdCommand
} from "./chunk-MGDEINGP.js";
import {
  migrateObservations,
  migrateObservationsCommand,
  registerMigrateObservationsCommand
} from "./chunk-VXEOHTSL.js";
import {
  rebuildCommand,
  registerRebuildCommand
} from "./chunk-PBEE567J.js";
import {
  registerReplayCommand,
  replayCommand
} from "./chunk-R6SXNSFD.js";
import {
  doctor
} from "./chunk-PZ2AUU2W.js";
import "./chunk-7ZRP733D.js";
import {
  graphCommand,
  graphSummary
} from "./chunk-OZ7RIXTO.js";
import {
  buildKanbanLanes,
  extractCardSlug,
  formatKanbanCard,
  generateKanbanMarkdown,
  importKanbanBoard,
  kanbanCommand,
  parseKanbanMarkdown,
  syncKanbanBoard
} from "./chunk-4OXMU5S2.js";
import "./chunk-4VQTUVH7.js";
import "./chunk-J7ZWCI2C.js";
import {
  registerCliCommands
} from "./chunk-6546Q4OR.js";
import {
  registerTailscaleCommands,
  registerTailscaleDiscoverCommand,
  registerTailscaleServeCommand,
  registerTailscaleStatusCommand,
  registerTailscaleSyncCommand,
  tailscaleDiscoverCommand,
  tailscaleServeCommand,
  tailscaleStatusCommand,
  tailscaleSyncCommand
} from "./chunk-THRJVD4L.js";
import {
  CLAWVAULT_SERVE_PATH,
  DEFAULT_SERVE_PORT,
  checkPeerClawVault,
  compareManifests,
  configureTailscaleServe,
  discoverClawVaultPeers,
  fetchRemoteFile,
  fetchRemoteManifest,
  findPeer,
  generateVaultManifest,
  getOnlinePeers,
  getTailscaleStatus,
  getTailscaleVersion,
  hasTailscale,
  pushFileToRemote,
  resolvePeerIP,
  serveVault,
  stopTailscaleServe,
  syncWithPeer
} from "./chunk-TIGW564L.js";
import "./chunk-IVRIKYFE.js";
import {
  SessionWatcher,
  observeCommand,
  registerObserveCommand
} from "./chunk-ME37YNW3.js";
import {
  parseSessionFile
} from "./chunk-P5EPF6MB.js";
import {
  reflectCommand,
  registerReflectCommand
} from "./chunk-3BTHWPMB.js";
import {
  runReflection
} from "./chunk-T76H47ZS.js";
import {
  buildContext,
  contextCommand,
  formatContextMarkdown,
  inferContextProfile,
  normalizeContextProfileInput,
  registerContextCommand,
  resolveContextProfile
} from "./chunk-DTEHFAL7.js";
import {
  getObserverStaleness,
  getScaledObservationThresholdBytes,
  observeActiveSessions,
  parseSessionSourceLabel
} from "./chunk-IEVLHNLU.js";
import "./chunk-HRLWZGMA.js";
import {
  Compressor,
  Observer,
  Reflector
} from "./chunk-Q2J5YTUF.js";
import {
  archiveProject,
  createProject,
  getProjectActivity,
  getProjectTasks,
  listProjects,
  readProject,
  updateProject
} from "./chunk-AZYOKJYC.js";
import {
  ClawVault,
  createVault,
  findVault
} from "./chunk-RCBMXTWS.js";
import "./chunk-FHFUXL6G.js";
import {
  embedCommand,
  registerEmbedCommand
} from "./chunk-4QYGFWRM.js";
import {
  QMD_INSTALL_COMMAND,
  QMD_INSTALL_URL,
  QmdUnavailableError,
  SearchEngine,
  extractTags,
  extractWikiLinks,
  hasQmd,
  qmdEmbed,
  qmdUpdate
} from "./chunk-MAKNAHAW.js";
import {
  buildInjectionResult,
  deterministicInjectMatches,
  indexInjectableItems,
  injectCommand,
  registerInjectCommand,
  runPromptInjection
} from "./chunk-4VRIMU4O.js";
import {
  requestLlmCompletion,
  resolveLlmProvider
} from "./chunk-HIHOUSXS.js";
import {
  SUPPORTED_CONFIG_KEYS,
  addRouteRule,
  getConfig,
  getConfigValue,
  listConfig,
  listRouteRules,
  matchRouteRule,
  removeRouteRule,
  resetConfig,
  setConfigValue,
  testRouteRule
} from "./chunk-ITPEXLHA.js";
import {
  DEFAULT_CATEGORIES,
  DEFAULT_CONFIG,
  MEMORY_TYPES,
  TYPE_TO_CATEGORY
} from "./chunk-2CDEETQN.js";
import {
  archiveCommand,
  registerArchiveCommand
} from "./chunk-VR5NE7PZ.js";
import {
  archiveObservations
} from "./chunk-MQUJNOHK.js";
import {
  findNearestVaultPath,
  getVaultPath,
  resolveVaultPath
} from "./chunk-MXSSG3QU.js";
import {
  MEMORY_GRAPH_SCHEMA_VERSION,
  buildOrUpdateMemoryGraphIndex,
  getMemoryGraph,
  loadMemoryGraphIndex
} from "./chunk-ZZA73MFY.js";
import "./chunk-Z2XBWN7A.js";
import {
  appendTransition,
  buildTransitionEvent,
  completeTask,
  countBlockedTransitions,
  formatTransitionsTable,
  isRegression,
  listDependentTasks,
  listSubtasks,
  queryTransitions,
  readAllTransitions,
  updateTask
} from "./chunk-QWQ3TIKS.js";
import "./chunk-MFAWT5O5.js";
import {
  buildTemplateVariables,
  renderTemplate
} from "./chunk-7766SIJP.js";
import {
  checkOpenClawCompatibility,
  compatCommand,
  compatibilityExitCode
} from "./chunk-QVMXF7FY.js";

// src/index.ts
import * as fs2 from "fs";

// src/lib/hybrid-search.ts
import * as fs from "fs";
import * as path from "path";
var embeddingPipeline = null;
var pipelineLoading = null;
async function getEmbeddingPipeline() {
  if (embeddingPipeline) return embeddingPipeline;
  if (pipelineLoading) return pipelineLoading;
  pipelineLoading = (async () => {
    const { pipeline } = await import("@huggingface/transformers");
    embeddingPipeline = await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2", {
      dtype: "fp32"
    });
    return embeddingPipeline;
  })();
  return pipelineLoading;
}
async function embed(text) {
  const pipe = await getEmbeddingPipeline();
  const result = await pipe(text, { pooling: "mean", normalize: true });
  return new Float32Array(result.data);
}
async function embedBatch(texts) {
  const pipe = await getEmbeddingPipeline();
  const results = [];
  const batchSize = 32;
  for (let i = 0; i < texts.length; i += batchSize) {
    const batch = texts.slice(i, i + batchSize);
    for (const text of batch) {
      const result = await pipe(text, { pooling: "mean", normalize: true });
      results.push(new Float32Array(result.data));
    }
  }
  return results;
}
function cosineSimilarity(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
  }
  return dot;
}
var EmbeddingCache = class {
  cachePath;
  cache = /* @__PURE__ */ new Map();
  dirty = false;
  constructor(vaultPath) {
    this.cachePath = path.join(vaultPath, ".clawvault", "embeddings.bin");
  }
  /**
   * Load cache from disk
   */
  load() {
    try {
      if (!fs.existsSync(this.cachePath)) return;
      const data = JSON.parse(fs.readFileSync(this.cachePath + ".json", "utf-8"));
      for (const [key, arr] of Object.entries(data)) {
        this.cache.set(key, new Float32Array(arr));
      }
    } catch {
    }
  }
  /**
   * Save cache to disk
   */
  save() {
    if (!this.dirty) return;
    const dir = path.dirname(this.cachePath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    const data = {};
    for (const [key, arr] of this.cache.entries()) {
      data[key] = Array.from(arr);
    }
    fs.writeFileSync(this.cachePath + ".json", JSON.stringify(data));
    this.dirty = false;
  }
  get(key) {
    return this.cache.get(key);
  }
  set(key, embedding) {
    this.cache.set(key, embedding);
    this.dirty = true;
  }
  has(key) {
    return this.cache.has(key);
  }
  entries() {
    return this.cache.entries();
  }
  get size() {
    return this.cache.size;
  }
};
function reciprocalRankFusion(list1, list2, k = 60) {
  const scores = /* @__PURE__ */ new Map();
  for (let rank = 0; rank < list1.length; rank++) {
    const { id } = list1[rank];
    scores.set(id, (scores.get(id) || 0) + 1 / (k + rank + 1));
  }
  for (let rank = 0; rank < list2.length; rank++) {
    const { id } = list2[rank];
    scores.set(id, (scores.get(id) || 0) + 1 / (k + rank + 1));
  }
  return Array.from(scores.entries()).map(([id, score]) => ({ id, score })).sort((a, b) => b.score - a.score);
}
async function semanticSearch(query, cache, topK = 20) {
  const queryEmb = await embed(query);
  const results = [];
  for (const [id, docEmb] of cache.entries()) {
    results.push({ id, score: cosineSimilarity(queryEmb, docEmb) });
  }
  results.sort((a, b) => b.score - a.score);
  return results.slice(0, topK);
}
async function hybridSearch(query, bm25Results, cache, options = {}) {
  const { topK = 20, rrfK = 60 } = options;
  const bm25Ranked = bm25Results.map((r) => ({ id: r.document.path || r.document.id, score: r.score }));
  const semanticRanked = await semanticSearch(query, cache, topK);
  const fused = reciprocalRankFusion(bm25Ranked, semanticRanked, rrfK);
  const bm25Map = new Map(bm25Results.map((r) => [r.document.path || r.document.id, r]));
  return fused.slice(0, topK).map(({ id, score }) => {
    const existing = bm25Map.get(id);
    if (existing) {
      return { ...existing, score };
    }
    const minimalDoc = {
      id: id.replace(/\.md$/, ""),
      path: id.endsWith(".md") ? id : id + ".md",
      title: (id.split("/").pop() || id).replace(/\.md$/, ""),
      content: "",
      category: id.split("/")[0] || "root",
      frontmatter: {},
      links: [],
      tags: [],
      modified: /* @__PURE__ */ new Date()
    };
    return {
      document: minimalDoc,
      score,
      snippet: "",
      matchedTerms: []
    };
  });
}

// src/index.ts
function readPackageVersion() {
  try {
    const pkgUrl = new URL("../package.json", import.meta.url);
    const pkg = JSON.parse(fs2.readFileSync(pkgUrl, "utf-8"));
    return pkg.version ?? "0.0.0";
  } catch {
    return "0.0.0";
  }
}
var VERSION = readPackageVersion();
function registerCommanderCommands(program) {
  return registerCliCommands(program);
}
export {
  CLAWVAULT_SERVE_PATH,
  ClawVault,
  Compressor,
  DEFAULT_CATEGORIES,
  DEFAULT_CONFIG,
  DEFAULT_SERVE_PORT,
  EmbeddingCache,
  MEMORY_GRAPH_SCHEMA_VERSION,
  MEMORY_TYPES,
  Observer,
  QMD_INSTALL_COMMAND,
  QMD_INSTALL_URL,
  QmdUnavailableError,
  Reflector,
  SUPPORTED_CONFIG_KEYS,
  SearchEngine,
  SessionWatcher,
  TYPE_TO_CATEGORY,
  VERSION,
  addRouteRule,
  appendTransition,
  archiveCommand,
  archiveObservations,
  archiveProject,
  buildContext,
  buildInjectionResult,
  buildKanbanLanes,
  buildOrUpdateMemoryGraphIndex,
  buildSessionRecap,
  buildTemplateVariables,
  buildTransitionEvent,
  checkOpenClawCompatibility,
  checkPeerClawVault,
  compareManifests,
  compatCommand,
  compatibilityExitCode,
  completeTask,
  configureTailscaleServe,
  contextCommand,
  cosineSimilarity,
  countBlockedTransitions,
  createProject,
  createVault,
  deterministicInjectMatches,
  discoverClawVaultPeers,
  doctor,
  embed,
  embedBatch,
  embedCommand,
  extractCardSlug,
  extractTags,
  extractWikiLinks,
  fetchRemoteFile,
  fetchRemoteManifest,
  findNearestVaultPath,
  findPeer,
  findVault,
  formatContextMarkdown,
  formatKanbanCard,
  formatSessionRecapMarkdown,
  formatTransitionsTable,
  generateKanbanMarkdown,
  generateVaultManifest,
  getConfig,
  getConfigValue,
  getMemoryGraph,
  getObserverStaleness,
  getOnlinePeers,
  getProjectActivity,
  getProjectTasks,
  getScaledObservationThresholdBytes,
  getTailscaleStatus,
  getTailscaleVersion,
  getVaultPath,
  graphCommand,
  graphSummary,
  hasQmd,
  hasTailscale,
  hybridSearch,
  importKanbanBoard,
  indexInjectableItems,
  inferContextProfile,
  injectCommand,
  isRegression,
  kanbanCommand,
  listConfig,
  listDependentTasks,
  listProjects,
  listRouteRules,
  listSubtasks,
  loadMemoryGraphIndex,
  matchRouteRule,
  migrateObservations,
  migrateObservationsCommand,
  normalizeContextProfileInput,
  observeActiveSessions,
  observeCommand,
  parseKanbanMarkdown,
  parseSessionFile,
  parseSessionSourceLabel,
  pushFileToRemote,
  qmdEmbed,
  qmdUpdate,
  queryTransitions,
  readAllTransitions,
  readProject,
  rebuildCommand,
  reciprocalRankFusion,
  reflectCommand,
  registerArchiveCommand,
  registerCliCommands,
  registerCommanderCommands,
  registerContextCommand,
  registerEmbedCommand,
  registerInjectCommand,
  registerMigrateObservationsCommand,
  registerObserveCommand,
  registerRebuildCommand,
  registerReflectCommand,
  registerReplayCommand,
  registerSyncBdCommand,
  registerTailscaleCommands,
  registerTailscaleDiscoverCommand,
  registerTailscaleServeCommand,
  registerTailscaleStatusCommand,
  registerTailscaleSyncCommand,
  removeRouteRule,
  renderTemplate,
  replayCommand,
  requestLlmCompletion,
  resetConfig,
  resolveContextProfile,
  resolveLlmProvider,
  resolvePeerIP,
  resolveVaultPath,
  runPromptInjection,
  runReflection,
  semanticSearch,
  serveVault,
  sessionRecapCommand,
  setConfigValue,
  setupCommand,
  stopTailscaleServe,
  syncBdCommand,
  syncKanbanBoard,
  syncWithPeer,
  tailscaleDiscoverCommand,
  tailscaleServeCommand,
  tailscaleStatusCommand,
  tailscaleSyncCommand,
  testRouteRule,
  updateProject,
  updateTask
};
