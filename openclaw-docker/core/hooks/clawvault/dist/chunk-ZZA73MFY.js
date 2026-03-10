// src/lib/memory-graph.ts
import * as fs from "fs";
import * as path from "path";
import matter from "gray-matter";
import { glob } from "glob";
var MEMORY_GRAPH_SCHEMA_VERSION = 1;
var GRAPH_INDEX_RELATIVE_PATH = path.join(".clawvault", "graph-index.json");
var WIKI_LINK_RE = /\[\[([^\]]+)\]\]/g;
var HASH_TAG_RE = /(^|\s)#([\w-]+)/g;
var FRONTMATTER_RELATION_FIELDS = [
  "related",
  "depends_on",
  "dependsOn",
  "blocked_by",
  "blocks",
  "owner",
  "project",
  "people",
  "links"
];
function normalizeRelativePath(value) {
  return value.split(path.sep).join("/").replace(/^\.\//, "").replace(/^\/+/, "");
}
function toNoteKey(relativePath) {
  const normalized = normalizeRelativePath(relativePath);
  return normalized.toLowerCase().endsWith(".md") ? normalized.slice(0, -3) : normalized;
}
function toNoteNodeId(noteKey) {
  return `note:${noteKey}`;
}
function toTagNodeId(tag) {
  return `tag:${tag.toLowerCase()}`;
}
function normalizeUnresolvedKey(raw) {
  const normalized = raw.trim().toLowerCase().replace(/\\/g, "/").replace(/^\.\//, "").replace(/^\/+/, "").replace(/\.md$/, "").replace(/[^a-z0-9/_-]+/g, "-").replace(/\/+/g, "/").replace(/-+/g, "-").replace(/^[-/]+|[-/]+$/g, "");
  return normalized || "unknown";
}
function toUnresolvedNodeId(raw) {
  return `unresolved:${normalizeUnresolvedKey(raw)}`;
}
function titleFromNoteKey(noteKey) {
  const basename = noteKey.split("/").pop() ?? noteKey;
  return basename.replace(/[-_]+/g, " ").replace(/\s+/g, " ").trim().replace(/\b\w/g, (char) => char.toUpperCase());
}
function inferNodeType(relativePath, frontmatter) {
  const normalized = normalizeRelativePath(relativePath).toLowerCase();
  const category = normalized.split("/")[0] ?? "note";
  const explicitType = typeof frontmatter.type === "string" ? frontmatter.type.toLowerCase() : "";
  if (category.includes("daily") || explicitType === "daily") return "daily";
  if (category === "observations" || explicitType === "observation") return "observation";
  if (category === "handoffs" || explicitType === "handoff") return "handoff";
  if (category === "decisions" || explicitType === "decision") return "decision";
  if (category === "lessons" || explicitType === "lesson") return "lesson";
  if (category === "projects" || explicitType === "project") return "project";
  if (category === "people" || explicitType === "person") return "person";
  if (category === "commitments" || explicitType === "commitment") return "commitment";
  return "note";
}
function ensureClawvaultDir(vaultPath) {
  const dirPath = path.join(vaultPath, ".clawvault");
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
  return dirPath;
}
function getGraphIndexPath(vaultPath) {
  return path.join(vaultPath, GRAPH_INDEX_RELATIVE_PATH);
}
function normalizeWikiTarget(target) {
  let value = target.trim();
  if (!value) return "";
  const pipeIndex = value.indexOf("|");
  if (pipeIndex >= 0) {
    value = value.slice(0, pipeIndex);
  }
  const hashIndex = value.indexOf("#");
  if (hashIndex >= 0) {
    value = value.slice(0, hashIndex);
  }
  value = value.trim().replace(/\\/g, "/").replace(/^\.\//, "").replace(/^\/+/, "");
  if (value.toLowerCase().endsWith(".md")) {
    value = value.slice(0, -3);
  }
  return value.trim();
}
function collectTags(frontmatter, markdownContent) {
  const tags = /* @__PURE__ */ new Set();
  const fmTags = frontmatter.tags;
  if (Array.isArray(fmTags)) {
    for (const tag of fmTags) {
      if (typeof tag === "string" && tag.trim()) tags.add(tag.trim().toLowerCase());
    }
  } else if (typeof fmTags === "string") {
    for (const token of fmTags.split(",")) {
      const normalized = token.trim().toLowerCase();
      if (normalized) tags.add(normalized);
    }
  }
  const markdownMatches = markdownContent.matchAll(HASH_TAG_RE);
  for (const match of markdownMatches) {
    const tag = match[2]?.trim().toLowerCase();
    if (tag) tags.add(tag);
  }
  return [...tags].sort((a, b) => a.localeCompare(b));
}
function extractWikiTargets(markdownContent) {
  const targets = /* @__PURE__ */ new Set();
  for (const match of markdownContent.matchAll(WIKI_LINK_RE)) {
    const candidate = match[1];
    if (!candidate) continue;
    const normalized = normalizeWikiTarget(candidate);
    if (normalized) targets.add(normalized);
  }
  return [...targets];
}
function toStringArray(value) {
  if (typeof value === "string") {
    return value.split(",").map((entry) => entry.trim()).filter(Boolean);
  }
  if (Array.isArray(value)) {
    return value.flatMap((entry) => typeof entry === "string" ? entry.split(",") : []).map((entry) => entry.trim()).filter(Boolean);
  }
  return [];
}
function extractFrontmatterRelations(frontmatter) {
  const relations = [];
  for (const field of FRONTMATTER_RELATION_FIELDS) {
    const raw = frontmatter[field];
    for (const value of toStringArray(raw)) {
      const normalized = normalizeWikiTarget(value);
      if (normalized) relations.push({ field, target: normalized });
    }
  }
  return relations;
}
function buildNoteRegistry(relativePaths) {
  const byLowerPath = /* @__PURE__ */ new Map();
  const byLowerBasename = /* @__PURE__ */ new Map();
  for (const relativePath of relativePaths) {
    const noteKey = toNoteKey(relativePath);
    const lowerKey = noteKey.toLowerCase();
    if (!byLowerPath.has(lowerKey)) {
      byLowerPath.set(lowerKey, noteKey);
    }
    const base = noteKey.split("/").pop() ?? noteKey;
    const lowerBase = base.toLowerCase();
    const existing = byLowerBasename.get(lowerBase) ?? [];
    existing.push(noteKey);
    byLowerBasename.set(lowerBase, existing);
  }
  return { byLowerPath, byLowerBasename };
}
function resolveTargetNodeId(rawTarget, registry) {
  const normalized = normalizeWikiTarget(rawTarget);
  if (!normalized) {
    return toUnresolvedNodeId(rawTarget);
  }
  const lowerTarget = normalized.toLowerCase();
  const direct = registry.byLowerPath.get(lowerTarget);
  if (direct) {
    return toNoteNodeId(direct);
  }
  if (!normalized.includes("/")) {
    const basenameMatches = registry.byLowerBasename.get(lowerTarget) ?? [];
    if (basenameMatches.length === 1) {
      return toNoteNodeId(basenameMatches[0]);
    }
  }
  return toUnresolvedNodeId(normalized);
}
function createEdgeId(type, source, target, label) {
  const suffix = label ? `:${label}` : "";
  return `${type}:${source}->${target}${suffix}`;
}
function buildFragmentNode(id, title, type, category, pathValue, tags, missing, modifiedAt) {
  return {
    id,
    title,
    type,
    category,
    path: pathValue,
    tags,
    missing,
    degree: 0,
    modifiedAt
  };
}
function parseFileFragment(vaultPath, relativePath, mtimeMs, registry) {
  const absolutePath = path.join(vaultPath, relativePath);
  const raw = fs.readFileSync(absolutePath, "utf-8");
  const parsed = matter(raw);
  const frontmatter = parsed.data ?? {};
  const noteKey = toNoteKey(relativePath);
  const noteNodeId = toNoteNodeId(noteKey);
  const noteType = inferNodeType(relativePath, frontmatter);
  const tags = collectTags(frontmatter, parsed.content);
  const modifiedAt = new Date(mtimeMs).toISOString();
  const nodes = /* @__PURE__ */ new Map();
  const edges = /* @__PURE__ */ new Map();
  nodes.set(
    noteNodeId,
    buildFragmentNode(
      noteNodeId,
      typeof frontmatter.title === "string" && frontmatter.title.trim() ? frontmatter.title.trim() : titleFromNoteKey(noteKey),
      noteType,
      noteType,
      normalizeRelativePath(relativePath),
      tags,
      false,
      modifiedAt
    )
  );
  for (const tag of tags) {
    const tagNodeId = toTagNodeId(tag);
    if (!nodes.has(tagNodeId)) {
      nodes.set(tagNodeId, buildFragmentNode(tagNodeId, `#${tag}`, "tag", "tag", null, [], false, null));
    }
    const edgeId = createEdgeId("tag", noteNodeId, tagNodeId);
    edges.set(edgeId, {
      id: edgeId,
      source: noteNodeId,
      target: tagNodeId,
      type: "tag"
    });
  }
  const wikiTargets = extractWikiTargets(parsed.content);
  for (const target of wikiTargets) {
    const targetNodeId = resolveTargetNodeId(target, registry);
    if (targetNodeId.startsWith("unresolved:") && !nodes.has(targetNodeId)) {
      nodes.set(
        targetNodeId,
        buildFragmentNode(targetNodeId, titleFromNoteKey(normalizeUnresolvedKey(target)), "unresolved", "unresolved", null, [], true, null)
      );
    }
    const edgeId = createEdgeId("wiki_link", noteNodeId, targetNodeId);
    edges.set(edgeId, {
      id: edgeId,
      source: noteNodeId,
      target: targetNodeId,
      type: "wiki_link"
    });
  }
  for (const relation of extractFrontmatterRelations(frontmatter)) {
    const targetNodeId = resolveTargetNodeId(relation.target, registry);
    if (targetNodeId.startsWith("unresolved:") && !nodes.has(targetNodeId)) {
      nodes.set(
        targetNodeId,
        buildFragmentNode(
          targetNodeId,
          titleFromNoteKey(normalizeUnresolvedKey(relation.target)),
          "unresolved",
          "unresolved",
          null,
          [],
          true,
          null
        )
      );
    }
    const edgeId = createEdgeId("frontmatter_relation", noteNodeId, targetNodeId, relation.field);
    edges.set(edgeId, {
      id: edgeId,
      source: noteNodeId,
      target: targetNodeId,
      type: "frontmatter_relation",
      label: relation.field
    });
  }
  return {
    relativePath: normalizeRelativePath(relativePath),
    mtimeMs,
    nodes: [...nodes.values()],
    edges: [...edges.values()]
  };
}
function combineFragments(fragments, generatedAt) {
  const nodes = /* @__PURE__ */ new Map();
  const edges = /* @__PURE__ */ new Map();
  for (const fragment of Object.values(fragments)) {
    for (const node of fragment.nodes) {
      const existing = nodes.get(node.id);
      if (!existing) {
        nodes.set(node.id, { ...node, degree: 0 });
      } else if (node.modifiedAt && (!existing.modifiedAt || node.modifiedAt > existing.modifiedAt)) {
        nodes.set(node.id, { ...existing, ...node, degree: 0 });
      }
    }
    for (const edge of fragment.edges) {
      edges.set(edge.id, edge);
    }
  }
  const degreeByNode = /* @__PURE__ */ new Map();
  for (const edge of edges.values()) {
    degreeByNode.set(edge.source, (degreeByNode.get(edge.source) ?? 0) + 1);
    degreeByNode.set(edge.target, (degreeByNode.get(edge.target) ?? 0) + 1);
  }
  for (const node of nodes.values()) {
    node.degree = degreeByNode.get(node.id) ?? 0;
  }
  const nodeTypeCounts = {};
  for (const node of nodes.values()) {
    nodeTypeCounts[node.type] = (nodeTypeCounts[node.type] ?? 0) + 1;
  }
  const edgeTypeCounts = {};
  for (const edge of edges.values()) {
    edgeTypeCounts[edge.type] = (edgeTypeCounts[edge.type] ?? 0) + 1;
  }
  const sortedNodes = [...nodes.values()].sort((a, b) => a.id.localeCompare(b.id));
  const sortedEdges = [...edges.values()].sort((a, b) => a.id.localeCompare(b.id));
  return {
    schemaVersion: MEMORY_GRAPH_SCHEMA_VERSION,
    nodes: sortedNodes,
    edges: sortedEdges,
    stats: {
      generatedAt,
      nodeCount: sortedNodes.length,
      edgeCount: sortedEdges.length,
      nodeTypeCounts,
      edgeTypeCounts
    }
  };
}
function isValidIndex(index) {
  if (!index || typeof index !== "object") return false;
  const typed = index;
  return typed.schemaVersion === MEMORY_GRAPH_SCHEMA_VERSION && typeof typed.vaultPath === "string" && typeof typed.generatedAt === "string" && Boolean(typed.files && typeof typed.files === "object") && Boolean(typed.graph && typeof typed.graph === "object");
}
function loadMemoryGraphIndex(vaultPath) {
  const indexPath = getGraphIndexPath(path.resolve(vaultPath));
  if (!fs.existsSync(indexPath)) {
    return null;
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(indexPath, "utf-8"));
    if (!isValidIndex(parsed)) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}
async function buildOrUpdateMemoryGraphIndex(vaultPathInput, options = {}) {
  const vaultPath = path.resolve(vaultPathInput);
  ensureClawvaultDir(vaultPath);
  const existing = options.forceFull ? null : loadMemoryGraphIndex(vaultPath);
  const markdownFiles = await glob("**/*.md", {
    cwd: vaultPath,
    ignore: ["**/node_modules/**", "**/.git/**", "**/.obsidian/**", "**/.trash/**", "**/ledger/archive/**"]
  });
  const normalizedFiles = markdownFiles.map(normalizeRelativePath).sort((a, b) => a.localeCompare(b));
  const registry = buildNoteRegistry(normalizedFiles);
  const nextFragments = {};
  const existingFragments = existing?.files ?? {};
  const currentFileSet = new Set(normalizedFiles);
  for (const relativePath of normalizedFiles) {
    const absolutePath = path.join(vaultPath, relativePath);
    const stat = fs.statSync(absolutePath);
    const existingFragment = existingFragments[relativePath];
    if (!options.forceFull && existingFragment && existingFragment.mtimeMs === stat.mtimeMs) {
      nextFragments[relativePath] = existingFragment;
      continue;
    }
    nextFragments[relativePath] = parseFileFragment(vaultPath, relativePath, stat.mtimeMs, registry);
  }
  for (const [relativePath, fragment] of Object.entries(existingFragments)) {
    if (!currentFileSet.has(relativePath)) {
      continue;
    }
    if (!nextFragments[relativePath]) {
      nextFragments[relativePath] = fragment;
    }
  }
  const generatedAt = (/* @__PURE__ */ new Date()).toISOString();
  const graph = combineFragments(nextFragments, generatedAt);
  const nextIndex = {
    schemaVersion: MEMORY_GRAPH_SCHEMA_VERSION,
    vaultPath,
    generatedAt,
    files: nextFragments,
    graph
  };
  fs.writeFileSync(getGraphIndexPath(vaultPath), JSON.stringify(nextIndex, null, 2));
  return nextIndex;
}
async function getMemoryGraph(vaultPath, options = {}) {
  if (options.refresh === true) {
    return (await buildOrUpdateMemoryGraphIndex(vaultPath, { forceFull: true })).graph;
  }
  return (await buildOrUpdateMemoryGraphIndex(vaultPath)).graph;
}

export {
  MEMORY_GRAPH_SCHEMA_VERSION,
  loadMemoryGraphIndex,
  buildOrUpdateMemoryGraphIndex,
  getMemoryGraph
};
