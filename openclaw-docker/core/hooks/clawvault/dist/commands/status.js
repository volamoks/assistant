import {
  formatAge
} from "../chunk-7ZRP733D.js";
import {
  scanVaultLinks
} from "../chunk-4VQTUVH7.js";
import "../chunk-J7ZWCI2C.js";
import {
  getObserverStaleness
} from "../chunk-IEVLHNLU.js";
import "../chunk-HRLWZGMA.js";
import "../chunk-Q2J5YTUF.js";
import "../chunk-AZYOKJYC.js";
import {
  ClawVault
} from "../chunk-RCBMXTWS.js";
import "../chunk-FHFUXL6G.js";
import {
  QmdUnavailableError,
  hasQmd,
  withQmdIndexArgs
} from "../chunk-MAKNAHAW.js";
import "../chunk-ITPEXLHA.js";
import "../chunk-2CDEETQN.js";
import {
  loadMemoryGraphIndex
} from "../chunk-ZZA73MFY.js";
import "../chunk-Z2XBWN7A.js";
import "../chunk-QWQ3TIKS.js";
import "../chunk-MFAWT5O5.js";
import "../chunk-7766SIJP.js";

// src/commands/status.ts
import * as fs from "fs";
import * as path from "path";
import { execFileSync } from "child_process";

// src/lib/qmd-collections.ts
var COLLECTION_HEADER_RE = /^(\S+)\s+\(qmd:\/\/([^)]+)\)\s*$/;
var DETAIL_LINE_RE = /^\s+([A-Za-z][A-Za-z0-9 _-]*):\s*(.+)\s*$/;
function normalizeDetailKey(value) {
  return value.trim().toLowerCase().replace(/[ -]+/g, "_");
}
function parseCount(raw) {
  if (!raw) return void 0;
  const match = raw.match(/-?\d[\d,]*/);
  if (!match) return void 0;
  const parsed = Number.parseInt(match[0].replace(/,/g, ""), 10);
  return Number.isFinite(parsed) ? parsed : void 0;
}
function pickDetail(details, keys) {
  for (const key of keys) {
    const value = details[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return void 0;
}
function pickCount(details, keys) {
  for (const key of keys) {
    const parsed = parseCount(details[key]);
    if (parsed !== void 0) {
      return parsed;
    }
  }
  return void 0;
}
function parseQmdCollectionList(raw) {
  const collections = [];
  let current = null;
  for (const line of raw.split(/\r?\n/)) {
    const headerMatch = line.match(COLLECTION_HEADER_RE);
    if (headerMatch) {
      current = {
        name: headerMatch[1],
        uri: headerMatch[2],
        details: {}
      };
      collections.push(current);
      continue;
    }
    if (!current) continue;
    const detailMatch = line.match(DETAIL_LINE_RE);
    if (!detailMatch) continue;
    const key = normalizeDetailKey(detailMatch[1]);
    current.details[key] = detailMatch[2].trim();
  }
  for (const collection of collections) {
    const root = pickDetail(collection.details, ["root", "path", "directory"]);
    if (root) {
      collection.root = root;
    }
    collection.files = pickCount(collection.details, ["files", "documents", "docs"]);
    collection.vectors = pickCount(collection.details, ["vectors", "embeddings", "vector_embeddings"]);
    collection.pendingEmbeddings = pickCount(collection.details, [
      "pending",
      "pending_vectors",
      "pending_embeddings",
      "unembedded",
      "without_embeddings"
    ]);
    if (collection.pendingEmbeddings === void 0 && collection.files !== void 0 && collection.vectors !== void 0) {
      collection.pendingEmbeddings = Math.max(collection.files - collection.vectors, 0);
    }
  }
  return collections;
}

// src/commands/status.ts
var CLAWVAULT_DIR = ".clawvault";
var CHECKPOINT_FILE = "last-checkpoint.json";
var DIRTY_DEATH_FLAG = "dirty-death.flag";
function findGitRoot(startPath) {
  let current = path.resolve(startPath);
  while (true) {
    if (fs.existsSync(path.join(current, ".git"))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}
function getGitStatus(repoRoot) {
  const output = execFileSync("git", ["-C", repoRoot, "status", "--porcelain"], {
    encoding: "utf-8"
  });
  const lines = output.split("\n").filter(Boolean);
  return { clean: lines.length === 0, dirtyCount: lines.length };
}
function getLatestVaultMarkdownMtime(vaultPath) {
  const skipDirs = /* @__PURE__ */ new Set([".git", ".obsidian", ".trash", "node_modules", ".clawvault"]);
  let latest = null;
  function walk(currentPath) {
    const entries = fs.readdirSync(currentPath, { withFileTypes: true });
    for (const entry of entries) {
      const absolute = path.join(currentPath, entry.name);
      if (entry.isDirectory()) {
        if (!skipDirs.has(entry.name)) {
          walk(absolute);
        }
        continue;
      }
      if (!entry.isFile() || !entry.name.endsWith(".md")) {
        continue;
      }
      const mtime = fs.statSync(absolute).mtime;
      if (!latest || mtime.getTime() > latest.getTime()) {
        latest = mtime;
      }
    }
  }
  walk(vaultPath);
  return latest;
}
function getQmdIndexStatus(collection, root, indexName) {
  const output = execFileSync("qmd", withQmdIndexArgs(["collection", "list"], indexName), { encoding: "utf-8" });
  const collections = parseQmdCollectionList(output);
  const collectionInfo = collections.find((c) => c.name === collection);
  if (collectionInfo) {
    return {
      status: "present",
      files: collectionInfo.files,
      vectors: collectionInfo.vectors
    };
  }
  return { status: "missing" };
}
function loadCheckpoint(vaultPath) {
  const checkpointPath = path.join(vaultPath, CLAWVAULT_DIR, CHECKPOINT_FILE);
  if (!fs.existsSync(checkpointPath)) {
    return { data: null };
  }
  try {
    const data = JSON.parse(fs.readFileSync(checkpointPath, "utf-8"));
    return { data };
  } catch (err) {
    return { data: null, error: err?.message || "Failed to parse checkpoint" };
  }
}
async function getStatus(vaultPath, options = {}) {
  if (!hasQmd()) {
    throw new QmdUnavailableError();
  }
  const vault = new ClawVault(path.resolve(vaultPath));
  await vault.load();
  const stats = await vault.stats();
  const linkScan = scanVaultLinks(vault.getPath());
  const issues = [];
  const checkpointInfo = loadCheckpoint(vault.getPath());
  const checkpoint = checkpointInfo.data;
  if (checkpointInfo.error) {
    issues.push(`Checkpoint parse error: ${checkpointInfo.error}`);
  }
  const checkpointStatus = {
    exists: Boolean(checkpoint),
    timestamp: checkpoint?.timestamp,
    age: checkpoint?.timestamp ? formatAge(Date.now() - new Date(checkpoint.timestamp).getTime()) : void 0,
    sessionKey: checkpoint?.sessionKey,
    model: checkpoint?.model,
    tokenEstimate: checkpoint?.tokenEstimate
  };
  if (!checkpointStatus.exists) {
    issues.push("No checkpoint found");
  }
  const dirtyFlagPath = path.join(vault.getPath(), CLAWVAULT_DIR, DIRTY_DEATH_FLAG);
  if (fs.existsSync(dirtyFlagPath)) {
    issues.push("Dirty death flag is set");
  }
  const qmdCollection = vault.getQmdCollection();
  const qmdRoot = vault.getQmdRoot();
  let qmdIndexResult = { status: "missing" };
  let qmdError;
  try {
    qmdIndexResult = getQmdIndexStatus(qmdCollection, qmdRoot, options.qmdIndexName);
    if (qmdIndexResult.status !== "present") {
      issues.push(`qmd collection ${qmdIndexResult.status.replace("-", " ")}`);
    }
  } catch (err) {
    qmdError = err?.message || "Failed to check qmd index";
    issues.push(`qmd status error: ${qmdError}`);
  }
  let gitStatus;
  const gitRoot = findGitRoot(vault.getPath());
  if (gitRoot) {
    try {
      const gitInfo = getGitStatus(gitRoot);
      gitStatus = { repoRoot: gitRoot, ...gitInfo };
      if (!gitInfo.clean) {
        issues.push(`Uncommitted changes: ${gitInfo.dirtyCount}`);
      }
    } catch (err) {
      issues.push(`Git status error: ${err?.message || "unknown error"}`);
    }
  }
  const graphIndex = loadMemoryGraphIndex(vault.getPath());
  let graphStatus = {
    indexStatus: "missing"
  };
  if (!graphIndex) {
    issues.push("Memory graph index missing");
  } else {
    const generatedAt = graphIndex.generatedAt;
    const latestDocMtime = getLatestVaultMarkdownMtime(vault.getPath());
    const isStale = latestDocMtime ? latestDocMtime.getTime() > new Date(generatedAt).getTime() + 1e3 : false;
    graphStatus = {
      indexStatus: isStale ? "stale" : "present",
      generatedAt,
      nodeCount: graphIndex.graph.stats.nodeCount,
      edgeCount: graphIndex.graph.stats.edgeCount
    };
    if (isStale) {
      issues.push("Memory graph index stale");
    }
  }
  const observerStaleness = getObserverStaleness(vault.getPath());
  if (observerStaleness.staleCount > 0) {
    issues.push(`Observer stale sessions: ${observerStaleness.staleCount}`);
  }
  return {
    vaultName: vault.getName(),
    vaultPath: vault.getPath(),
    health: issues.length === 0 ? "ok" : "warning",
    issues,
    checkpoint: checkpointStatus,
    qmd: {
      collection: qmdCollection,
      root: qmdRoot,
      indexStatus: qmdIndexResult.status,
      files: qmdIndexResult.files,
      vectors: qmdIndexResult.vectors,
      error: qmdError
    },
    graph: graphStatus,
    observer: observerStaleness,
    git: gitStatus,
    links: {
      total: linkScan.linkCount,
      orphans: linkScan.orphans.length
    },
    documents: stats.documents,
    categories: stats.categories
  };
}
function formatStatus(status) {
  let output = "ClawVault Status\n";
  output += "-".repeat(40) + "\n";
  output += `Vault: ${status.vaultName}
`;
  output += `Path: ${status.vaultPath}
`;
  output += `Health: ${status.health}
`;
  if (status.issues.length > 0) {
    output += `Issues: ${status.issues.join("; ")}
`;
  } else {
    output += "Issues: none\n";
  }
  output += "\nCheckpoint:\n";
  if (!status.checkpoint.exists) {
    output += "  - none\n";
  } else {
    output += `  - Timestamp: ${status.checkpoint.timestamp}
`;
    if (status.checkpoint.age) {
      output += `  - Age: ${status.checkpoint.age}
`;
    }
    if (status.checkpoint.sessionKey) {
      output += `  - Session key: ${status.checkpoint.sessionKey}
`;
    }
    if (status.checkpoint.model) {
      output += `  - Model: ${status.checkpoint.model}
`;
    }
    if (status.checkpoint.tokenEstimate !== void 0) {
      output += `  - Token estimate: ${status.checkpoint.tokenEstimate}
`;
    }
  }
  output += "\nqmd:\n";
  output += `  - Collection: ${status.qmd.collection}
`;
  output += `  - Root: ${status.qmd.root}
`;
  output += `  - Index: ${status.qmd.indexStatus}
`;
  if (status.qmd.files !== void 0) {
    output += `  - Files: ${status.qmd.files}
`;
  }
  if (status.qmd.vectors !== void 0) {
    output += `  - Vectors: ${status.qmd.vectors}
`;
  }
  if (status.qmd.error) {
    output += `  - Error: ${status.qmd.error}
`;
  }
  if (status.git) {
    output += "\nGit:\n";
    output += `  - Repo: ${status.git.repoRoot}
`;
    output += `  - Status: ${status.git.clean ? "clean" : "dirty"} (${status.git.dirtyCount} change(s))
`;
  }
  output += "\nGraph:\n";
  output += `  - Index: ${status.graph.indexStatus}
`;
  if (status.graph.generatedAt) {
    output += `  - Generated: ${status.graph.generatedAt}
`;
  }
  if (status.graph.nodeCount !== void 0 && status.graph.edgeCount !== void 0) {
    output += `  - Size: ${status.graph.nodeCount} nodes, ${status.graph.edgeCount} edges
`;
  }
  output += "\nObserver:\n";
  output += `  - Stale sessions: ${status.observer.staleCount}
`;
  if (status.observer.staleCount > 0) {
    output += `  - Oldest stale age: ${formatAge(status.observer.oldestMs)}
`;
    output += `  - Newest stale age: ${formatAge(status.observer.newestMs)}
`;
  }
  output += "\nLinks:\n";
  output += `  - Total: ${status.links.total}
`;
  if (status.links.orphans > 0) {
    output += `  - Orphans: ${status.links.orphans}
`;
  }
  output += "\nDocuments:\n";
  output += `  - Total: ${status.documents}
`;
  output += "  - By category:\n";
  for (const [category, count] of Object.entries(status.categories)) {
    output += `    * ${category}: ${count}
`;
  }
  output += "-".repeat(40) + "\n";
  return output;
}
async function statusCommand(vaultPath, options = {}) {
  const status = await getStatus(vaultPath, { qmdIndexName: options.qmdIndexName });
  if (options.json) {
    console.log(JSON.stringify(status, null, 2));
    return;
  }
  console.log(formatStatus(status));
}
export {
  formatStatus,
  getStatus,
  statusCommand
};
