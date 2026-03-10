// src/lib/search.ts
import { execFileSync, spawnSync } from "child_process";
import * as fs from "fs";
import * as path from "path";
var QMD_INSTALL_URL = "https://github.com/tobi/qmd";
var QMD_INSTALL_COMMAND = "bun install -g github:tobi/qmd";
var QMD_NOT_INSTALLED_MESSAGE = `ClawVault requires qmd. Install: ${QMD_INSTALL_COMMAND}`;
var QMD_INDEX_ENV_VAR = "CLAWVAULT_QMD_INDEX";
var QmdUnavailableError = class extends Error {
  constructor(message = QMD_NOT_INSTALLED_MESSAGE) {
    super(message);
    this.name = "QmdUnavailableError";
  }
};
function ensureJsonArgs(args) {
  return args.includes("--json") ? args : [...args, "--json"];
}
function resolveQmdIndexName(indexName) {
  const explicit = indexName?.trim();
  if (explicit) {
    return explicit;
  }
  const fromEnv = process.env[QMD_INDEX_ENV_VAR]?.trim();
  return fromEnv || void 0;
}
function withQmdIndexArgs(args, indexName) {
  if (args.includes("--index")) {
    return [...args];
  }
  const resolvedIndexName = resolveQmdIndexName(indexName);
  if (!resolvedIndexName) {
    return [...args];
  }
  return ["--index", resolvedIndexName, ...args];
}
function tryParseJson(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
function extractJsonPayload(raw) {
  const start = raw.search(/[\[{]/);
  if (start === -1) return null;
  const end = Math.max(raw.lastIndexOf("]"), raw.lastIndexOf("}"));
  if (end <= start) return null;
  return raw.slice(start, end + 1);
}
function stripQmdNoise(raw) {
  return raw.split("\n").filter((line) => {
    const t = line.trim();
    if (!t) return true;
    if (t.startsWith("[node-llama-cpp]")) return false;
    if (t.startsWith("Expanding query")) return false;
    if (t.startsWith("Searching ") && t.endsWith("queries...")) return false;
    if (/^[├└─│]/.test(t)) return false;
    return true;
  }).join("\n");
}
function parseQmdOutput(raw) {
  const trimmed = stripQmdNoise(raw).trim();
  if (!trimmed) return [];
  const direct = tryParseJson(trimmed);
  const extracted = direct ? null : extractJsonPayload(trimmed);
  const parsed = direct ?? (extracted ? tryParseJson(extracted) : null);
  if (!parsed) {
    throw new Error("qmd returned non-JSON output. Ensure qmd supports --json.");
  }
  if (Array.isArray(parsed)) {
    return parsed;
  }
  if (parsed && typeof parsed === "object") {
    const candidate = parsed.results ?? parsed.items ?? parsed.data;
    if (Array.isArray(candidate)) {
      return candidate;
    }
  }
  throw new Error("qmd returned an unexpected JSON shape.");
}
function ensureQmdAvailable() {
  if (!hasQmd()) {
    throw new QmdUnavailableError();
  }
}
function execQmd(args, indexName) {
  ensureQmdAvailable();
  const finalArgs = withQmdIndexArgs(ensureJsonArgs(args), indexName);
  try {
    const result = execFileSync("qmd", finalArgs, {
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "pipe"],
      maxBuffer: 10 * 1024 * 1024
      // 10MB
    });
    return parseQmdOutput(result);
  } catch (err) {
    if (err?.code === "ENOENT") {
      throw new QmdUnavailableError();
    }
    const output = [err?.stdout, err?.stderr].filter(Boolean).join("\n");
    if (output) {
      try {
        return parseQmdOutput(output);
      } catch {
      }
    }
    const message = err?.message ? `qmd failed: ${err.message}` : "qmd failed";
    throw new Error(message);
  }
}
function hasQmd() {
  const result = spawnSync("qmd", ["--version"], { stdio: "ignore" });
  return !result.error;
}
function qmdUpdate(collection, indexName) {
  ensureQmdAvailable();
  const args = ["update"];
  if (collection) {
    args.push("-c", collection);
  }
  execFileSync("qmd", withQmdIndexArgs(args, indexName), { stdio: "inherit" });
}
function qmdEmbed(collection, indexName) {
  ensureQmdAvailable();
  const args = ["embed"];
  if (collection) {
    args.push("-c", collection);
  }
  execFileSync("qmd", withQmdIndexArgs(args, indexName), { stdio: "inherit" });
}
var SearchEngine = class {
  documents = /* @__PURE__ */ new Map();
  collection = "clawvault";
  vaultPath = "";
  collectionRoot = "";
  qmdIndexName;
  /**
   * Set the collection name (usually vault name)
   */
  setCollection(name) {
    this.collection = name;
  }
  /**
   * Set the vault path for file resolution
   */
  setVaultPath(vaultPath) {
    this.vaultPath = vaultPath;
  }
  /**
   * Set the collection root for qmd:// URI resolution
   */
  setCollectionRoot(root) {
    this.collectionRoot = path.resolve(root);
  }
  /**
   * Set qmd index name (defaults to qmd global default when omitted)
   */
  setIndexName(indexName) {
    this.qmdIndexName = indexName;
  }
  /**
   * Add or update a document in the local cache
   * Note: qmd indexing happens via qmd update command
   */
  addDocument(doc) {
    this.documents.set(doc.id, doc);
  }
  /**
   * Remove a document from the local cache
   */
  removeDocument(id) {
    this.documents.delete(id);
  }
  /**
   * No-op for qmd - indexing is managed externally
   */
  rebuildIDF() {
  }
  /**
   * BM25 search via qmd
   */
  search(query, options = {}) {
    return this.runQmdQuery("search", query, options);
  }
  /**
   * Vector/semantic search via qmd vsearch
   */
  vsearch(query, options = {}) {
    return this.runQmdQuery("vsearch", query, options);
  }
  /**
   * Combined search with query expansion (qmd query command)
   */
  query(query, options = {}) {
    return this.runQmdQuery("query", query, options);
  }
  runQmdQuery(command, query, options) {
    const {
      limit = 10,
      minScore = 0,
      category,
      tags,
      fullContent = false,
      temporalBoost = false
    } = options;
    if (!query.trim()) return [];
    const args = [
      command,
      query,
      "-n",
      String(limit * 2),
      "--json"
    ];
    if (this.collection) {
      args.push("-c", this.collection);
    }
    const qmdResults = execQmd(args, this.qmdIndexName);
    return this.convertResults(qmdResults, {
      limit,
      minScore,
      category,
      tags,
      fullContent,
      temporalBoost
    });
  }
  /**
   * Convert qmd results to ClawVault SearchResult format
   */
  convertResults(qmdResults, options) {
    const { limit = 10, minScore = 0, category, tags, fullContent = false, temporalBoost = false } = options;
    const results = [];
    const maxScore = qmdResults[0]?.score || 1;
    for (const qr of qmdResults) {
      const filePath = this.qmdUriToPath(qr.file);
      const relativePath = this.vaultPath ? path.relative(this.vaultPath, filePath) : filePath;
      const normalizedRelativePath = relativePath.replace(/\\/g, "/");
      if (normalizedRelativePath.startsWith("ledger/archive/") || normalizedRelativePath.includes("/ledger/archive/")) {
        continue;
      }
      const docId = normalizedRelativePath.replace(/\.md$/, "");
      let doc = this.documents.get(docId) ?? this.documents.get(docId.split("/").join(path.sep));
      const modifiedAt = this.resolveModifiedAt(doc, filePath);
      const parts = normalizedRelativePath.split("/");
      const docCategory = parts.length > 1 ? parts[0] : "root";
      if (category && docCategory !== category) continue;
      if (tags && tags.length > 0 && doc) {
        const docTags = new Set(doc.tags);
        if (!tags.some((t) => docTags.has(t))) continue;
      }
      const normalizedScore = maxScore > 0 ? qr.score / maxScore : 0;
      const finalScore = temporalBoost ? normalizedScore * this.getRecencyFactor(modifiedAt) : normalizedScore;
      if (finalScore < minScore) continue;
      if (!doc) {
        doc = {
          id: docId,
          path: filePath,
          category: docCategory,
          title: qr.title || path.basename(relativePath, ".md"),
          content: "",
          // Content loaded separately if needed
          frontmatter: {},
          links: [],
          tags: [],
          modified: modifiedAt
        };
      }
      results.push({
        document: fullContent ? doc : { ...doc, content: "" },
        score: finalScore,
        snippet: this.cleanSnippet(qr.snippet),
        matchedTerms: []
        // qmd doesn't provide this
      });
    }
    return results.sort((a, b) => b.score - a.score).slice(0, limit);
  }
  resolveModifiedAt(doc, filePath) {
    if (doc) return doc.modified;
    try {
      return fs.statSync(filePath).mtime;
    } catch {
      return /* @__PURE__ */ new Date(0);
    }
  }
  getRecencyFactor(modifiedAt) {
    const ageMs = Math.max(0, Date.now() - modifiedAt.getTime());
    const ageDays = ageMs / (24 * 60 * 60 * 1e3);
    if (ageDays < 1) return 1;
    if (ageDays <= 7) return 0.9;
    return 0.7;
  }
  /**
   * Convert qmd:// URI to file path
   */
  qmdUriToPath(uri) {
    if (uri.startsWith("qmd://")) {
      const withoutScheme = uri.slice(6);
      const slashIndex = withoutScheme.indexOf("/");
      if (slashIndex > -1) {
        const relativePath = withoutScheme.slice(slashIndex + 1);
        const root = this.collectionRoot || this.vaultPath;
        if (root) {
          return path.join(root, relativePath);
        }
        return relativePath;
      }
    }
    return uri;
  }
  /**
   * Clean up qmd snippet format
   */
  cleanSnippet(snippet) {
    if (!snippet) return "";
    return snippet.replace(/@@ [-+]?\d+,?\d* @@ \([^)]+\)/g, "").trim().split("\n").slice(0, 3).join("\n").slice(0, 300);
  }
  /**
   * Get all cached documents
   */
  getAllDocuments() {
    return [...this.documents.values()];
  }
  /**
   * Get document count
   */
  get size() {
    return this.documents.size;
  }
  /**
   * Clear the local document cache
   */
  clear() {
    this.documents.clear();
  }
  /**
   * Export documents for persistence
   */
  export() {
    return {
      documents: [...this.documents.values()]
    };
  }
  /**
   * Import from persisted data
   */
  import(data) {
    this.clear();
    for (const doc of data.documents) {
      this.addDocument(doc);
    }
  }
};
function extractWikiLinks(content) {
  const matches = content.match(/\[\[([^\]]+)\]\]/g) || [];
  return matches.map((m) => m.slice(2, -2).toLowerCase());
}
function extractTags(content) {
  const matches = content.match(/#[\w-]+/g) || [];
  return [...new Set(matches.map((m) => m.slice(1).toLowerCase()))];
}

export {
  QMD_INSTALL_URL,
  QMD_INSTALL_COMMAND,
  QmdUnavailableError,
  withQmdIndexArgs,
  hasQmd,
  qmdUpdate,
  qmdEmbed,
  SearchEngine,
  extractWikiLinks,
  extractTags
};
