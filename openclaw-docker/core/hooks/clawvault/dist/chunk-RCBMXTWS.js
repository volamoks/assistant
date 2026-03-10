import {
  QmdUnavailableError,
  SearchEngine,
  extractTags,
  extractWikiLinks,
  hasQmd,
  qmdEmbed,
  qmdUpdate
} from "./chunk-MAKNAHAW.js";
import {
  DEFAULT_CATEGORIES,
  TYPE_TO_CATEGORY
} from "./chunk-2CDEETQN.js";
import {
  buildOrUpdateMemoryGraphIndex
} from "./chunk-ZZA73MFY.js";

// src/lib/vault.ts
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import matter from "gray-matter";
import { glob } from "glob";
var CONFIG_FILE = ".clawvault.json";
var INDEX_FILE = ".clawvault-index.json";
var ClawVault = class {
  config;
  search;
  initialized = false;
  constructor(vaultPath) {
    if (!hasQmd()) {
      throw new QmdUnavailableError();
    }
    this.config = {
      path: path.resolve(vaultPath),
      name: path.basename(vaultPath),
      categories: DEFAULT_CATEGORIES,
      qmdCollection: void 0,
      qmdRoot: void 0
    };
    this.search = new SearchEngine();
    this.applyQmdConfig();
  }
  /**
   * Initialize a new vault
   */
  async init(options = {}, initFlags) {
    if (!hasQmd()) {
      throw new QmdUnavailableError();
    }
    const vaultPath = this.config.path;
    const flags = initFlags || {};
    this.config = { ...this.config, ...options };
    this.applyQmdConfig();
    if (flags.skipTasks) {
      this.config.categories = this.config.categories.filter(
        (c) => !["tasks", "backlog"].includes(c)
      );
    }
    if (!fs.existsSync(vaultPath)) {
      fs.mkdirSync(vaultPath, { recursive: true });
    }
    for (const category of this.config.categories) {
      const catPath = path.join(vaultPath, category);
      if (!fs.existsSync(catPath)) {
        fs.mkdirSync(catPath, { recursive: true });
      }
    }
    const ledgerDirs = ["ledger/raw", "ledger/observations", "ledger/reflections"];
    for (const dir of ledgerDirs) {
      const dirPath = path.join(vaultPath, dir);
      if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true });
      }
    }
    await this.createTemplates();
    const readmePath = path.join(vaultPath, "README.md");
    if (!fs.existsSync(readmePath)) {
      fs.writeFileSync(readmePath, this.generateReadme());
    }
    await this.createWelcomeNote();
    const configPath = path.join(vaultPath, CONFIG_FILE);
    const meta = {
      name: this.config.name,
      version: "1.0.0",
      created: (/* @__PURE__ */ new Date()).toISOString(),
      lastUpdated: (/* @__PURE__ */ new Date()).toISOString(),
      categories: this.config.categories,
      documentCount: 0,
      qmdCollection: this.getQmdCollection(),
      qmdRoot: this.getQmdRoot()
    };
    fs.writeFileSync(configPath, JSON.stringify(meta, null, 2));
    if (!flags.skipBases && this.config.categories.includes("tasks")) {
      this.createBasesFiles();
    }
    if (!flags.skipGraph) {
      await this.syncMemoryGraphIndex({ forceFull: true });
    }
    this.initialized = true;
  }
  createBasesFiles() {
    const vaultPath = this.config.path;
    const basesFiles = {
      "all-tasks.base": [
        "filters:",
        "  and:",
        '    - file.inFolder("tasks")',
        '    - status != "done"',
        "formulas:",
        "  age: (now() - file.ctime).days",
        '  status_icon: if(status == "blocked", "\u{1F534}", if(status == "in-progress", "\u{1F528}", if(status == "open", "\u26AA", "\u2705")))',
        "views:",
        "  - type: table",
        "    name: All Active Tasks",
        "    groupBy:",
        "      property: status",
        "      direction: ASC",
        "    order:",
        "      - formula.status_icon",
        "      - file.name",
        "      - status",
        "      - owner",
        "      - project",
        "      - priority",
        "      - blocked_by",
        "      - formula.age",
        "  - type: cards",
        "    name: Task Board",
        "    groupBy:",
        "      property: status",
        "      direction: ASC",
        "    order:",
        "      - file.name",
        "      - owner",
        "      - project",
        "      - priority"
      ].join("\n"),
      "blocked.base": [
        "filters:",
        "  and:",
        '    - file.inFolder("tasks")',
        '    - status == "blocked"',
        "formulas:",
        "  days_blocked: (now() - file.ctime).days",
        "views:",
        "  - type: table",
        "    name: Blocked Tasks",
        "    order:",
        "      - file.name",
        "      - owner",
        "      - project",
        "      - blocked_by",
        "      - formula.days_blocked",
        "      - priority"
      ].join("\n"),
      "by-project.base": [
        "filters:",
        "  and:",
        '    - file.inFolder("tasks")',
        '    - status != "done"',
        "formulas:",
        '  status_icon: if(status == "blocked", "\u{1F534}", if(status == "in-progress", "\u{1F528}", "\u26AA"))',
        "views:",
        "  - type: table",
        "    name: By Project",
        "    groupBy:",
        "      property: project",
        "      direction: ASC",
        "    order:",
        "      - formula.status_icon",
        "      - file.name",
        "      - status",
        "      - owner",
        "      - priority"
      ].join("\n"),
      "backlog.base": [
        "filters:",
        "  and:",
        '    - file.inFolder("backlog")',
        "views:",
        "  - type: table",
        "    name: Backlog",
        "    order:",
        "      - file.name",
        "      - source",
        "      - project",
        "      - file.ctime"
      ].join("\n")
    };
    for (const [filename, content] of Object.entries(basesFiles)) {
      const filePath = path.join(vaultPath, filename);
      if (!fs.existsSync(filePath)) {
        fs.writeFileSync(filePath, content);
      }
    }
  }
  /**
   * Load an existing vault
   */
  async load() {
    if (!hasQmd()) {
      throw new QmdUnavailableError();
    }
    const vaultPath = this.config.path;
    const configPath = path.join(vaultPath, CONFIG_FILE);
    if (!fs.existsSync(configPath)) {
      throw new Error(`Not a ClawVault: ${vaultPath} (missing ${CONFIG_FILE})`);
    }
    const meta = JSON.parse(fs.readFileSync(configPath, "utf-8"));
    this.config.name = meta.name;
    this.config.categories = meta.categories;
    this.config.qmdCollection = meta.qmdCollection;
    this.config.qmdRoot = meta.qmdRoot;
    if (!meta.qmdCollection || !meta.qmdRoot) {
      meta.qmdCollection = meta.qmdCollection || meta.name;
      meta.qmdRoot = meta.qmdRoot || this.config.path;
      fs.writeFileSync(configPath, JSON.stringify(meta, null, 2));
    }
    this.applyQmdConfig(meta);
    await this.reindex();
    this.initialized = true;
  }
  /**
   * Reindex all documents
   */
  async reindex() {
    this.search.clear();
    const files = await glob("**/*.md", {
      cwd: this.config.path,
      ignore: ["**/node_modules/**", "**/.*", "**/ledger/archive/**"]
    });
    for (const file of files) {
      const doc = await this.loadDocument(file);
      if (doc) {
        this.search.addDocument(doc);
      }
    }
    await this.saveIndex();
    await this.syncMemoryGraphIndex();
    return this.search.size;
  }
  /**
   * Load a document from disk
   */
  async loadDocument(relativePath) {
    try {
      const fullPath = path.join(this.config.path, relativePath);
      const content = fs.readFileSync(fullPath, "utf-8");
      const { data: frontmatter, content: body } = matter(content);
      const stats = fs.statSync(fullPath);
      const parts = relativePath.split(path.sep);
      const category = parts.length > 1 ? parts[0] : "root";
      const filename = path.basename(relativePath, ".md");
      return {
        id: relativePath.replace(/\.md$/, ""),
        path: fullPath,
        category,
        title: frontmatter.title || filename,
        content: body,
        frontmatter,
        links: extractWikiLinks(body),
        tags: extractTags(body),
        modified: stats.mtime
      };
    } catch (err) {
      console.error(`Error loading ${relativePath}:`, err);
      return null;
    }
  }
  /**
   * Store a new document
   */
  async store(options) {
    const {
      category,
      title,
      content,
      frontmatter = {},
      overwrite = false,
      qmdUpdate: triggerUpdate = false,
      qmdEmbed: triggerEmbed = false,
      qmdIndexName
    } = options;
    const filename = this.slugify(title) + ".md";
    const relativePath = path.join(category, filename);
    const fullPath = path.join(this.config.path, relativePath);
    if (fs.existsSync(fullPath) && !overwrite) {
      throw new Error(`Document already exists: ${relativePath}. Use overwrite: true to replace.`);
    }
    const categoryPath = path.join(this.config.path, category);
    if (!fs.existsSync(categoryPath)) {
      fs.mkdirSync(categoryPath, { recursive: true });
    }
    const fm = {
      title,
      date: (/* @__PURE__ */ new Date()).toISOString().split("T")[0],
      ...frontmatter
    };
    const fileContent = matter.stringify(content, fm);
    fs.writeFileSync(fullPath, fileContent);
    const doc = await this.loadDocument(relativePath);
    if (doc) {
      this.search.addDocument(doc);
      await this.saveIndex();
      await this.syncMemoryGraphIndex();
    }
    if (triggerUpdate || triggerEmbed) {
      qmdUpdate(this.getQmdCollection(), qmdIndexName);
      if (triggerEmbed) {
        qmdEmbed(this.getQmdCollection(), qmdIndexName);
      }
    }
    return doc;
  }
  /**
   * Quick store to inbox
   */
  async capture(note, title) {
    const autoTitle = title || `note-${Date.now()}`;
    return this.store({
      category: "inbox",
      title: autoTitle,
      content: note
    });
  }
  /**
   * Search the vault (BM25 via qmd)
   */
  async find(query, options = {}) {
    return this.search.search(query, options);
  }
  /**
   * Semantic/vector search (via qmd vsearch)
   */
  async vsearch(query, options = {}) {
    return this.search.vsearch(query, options);
  }
  /**
   * Combined search with query expansion (via qmd query)
   */
  async query(query, options = {}) {
    return this.search.query(query, options);
  }
  /**
   * Get a document by ID or path
   */
  async get(idOrPath) {
    const normalized = idOrPath.replace(/\.md$/, "");
    const docs = this.search.getAllDocuments();
    return docs.find((d) => d.id === normalized) || null;
  }
  /**
   * List documents in a category
   */
  async list(category) {
    const docs = this.search.getAllDocuments();
    if (category) {
      return docs.filter((d) => d.category === category);
    }
    return docs;
  }
  /**
   * Sync vault to another location (for Obsidian on Windows, etc.)
   */
  async sync(options) {
    const { target, deleteOrphans = false, dryRun = false } = options;
    const result = {
      copied: [],
      deleted: [],
      unchanged: [],
      errors: []
    };
    const sourceFiles = await glob("**/*.md", {
      cwd: this.config.path,
      ignore: ["**/node_modules/**"]
    });
    if (!dryRun && !fs.existsSync(target)) {
      fs.mkdirSync(target, { recursive: true });
    }
    for (const file of sourceFiles) {
      const sourcePath = path.join(this.config.path, file);
      const targetPath = path.join(target, file);
      try {
        const sourceStats = fs.statSync(sourcePath);
        let shouldCopy = true;
        if (fs.existsSync(targetPath)) {
          const targetStats = fs.statSync(targetPath);
          if (sourceStats.mtime <= targetStats.mtime) {
            result.unchanged.push(file);
            shouldCopy = false;
          }
        }
        if (shouldCopy) {
          if (!dryRun) {
            const targetDir = path.dirname(targetPath);
            if (!fs.existsSync(targetDir)) {
              fs.mkdirSync(targetDir, { recursive: true });
            }
            fs.copyFileSync(sourcePath, targetPath);
          }
          result.copied.push(file);
        }
      } catch (err) {
        result.errors.push(`${file}: ${err}`);
      }
    }
    if (deleteOrphans) {
      const targetFiles = await glob("**/*.md", { cwd: target });
      const sourceSet = new Set(sourceFiles);
      for (const file of targetFiles) {
        if (!sourceSet.has(file)) {
          if (!dryRun) {
            fs.unlinkSync(path.join(target, file));
          }
          result.deleted.push(file);
        }
      }
    }
    return result;
  }
  /**
   * Get vault statistics
   */
  async stats() {
    const docs = this.search.getAllDocuments();
    const categories = {};
    const allTags = /* @__PURE__ */ new Set();
    let totalLinks = 0;
    for (const doc of docs) {
      categories[doc.category] = (categories[doc.category] || 0) + 1;
      totalLinks += doc.links.length;
      doc.tags.forEach((t) => allTags.add(t));
    }
    return {
      documents: docs.length,
      categories,
      links: totalLinks,
      tags: [...allTags].sort()
    };
  }
  /**
   * Get all categories
   */
  getCategories() {
    return this.config.categories;
  }
  /**
   * Check if vault is initialized
   */
  isInitialized() {
    return this.initialized;
  }
  /**
   * Get vault path
   */
  getPath() {
    return this.config.path;
  }
  /**
   * Get vault name
   */
  getName() {
    return this.config.name;
  }
  /**
   * Get qmd collection name
   */
  getQmdCollection() {
    return this.config.qmdCollection || this.config.name;
  }
  /**
   * Get qmd collection root
   */
  getQmdRoot() {
    return this.config.qmdRoot || this.config.path;
  }
  // === Memory Type System ===
  /**
   * Store a memory with type classification
   * Automatically routes to correct category based on type
   */
  async remember(type, title, content, frontmatter = {}) {
    const category = TYPE_TO_CATEGORY[type];
    return this.store({
      category,
      title,
      content,
      frontmatter: { ...frontmatter, memoryType: type }
    });
  }
  // === Handoff System ===
  /**
   * Create a session handoff document
   * Call this before context death or long pauses
   */
  async createHandoff(handoff) {
    const now = /* @__PURE__ */ new Date();
    const dateStr = now.toISOString().split("T")[0];
    const timeStr = now.toISOString().split("T")[1].slice(0, 5).replace(":", "");
    const fullHandoff = {
      ...handoff,
      created: now.toISOString()
    };
    const content = this.formatHandoff(fullHandoff);
    const frontmatter = {
      type: "handoff",
      workingOn: handoff.workingOn,
      blocked: handoff.blocked,
      nextSteps: handoff.nextSteps
    };
    if (handoff.sessionKey) frontmatter.sessionKey = handoff.sessionKey;
    if (handoff.feeling) frontmatter.feeling = handoff.feeling;
    if (handoff.decisions) frontmatter.decisions = handoff.decisions;
    if (handoff.openQuestions) frontmatter.openQuestions = handoff.openQuestions;
    return this.store({
      category: "handoffs",
      title: `handoff-${dateStr}-${timeStr}`,
      content,
      frontmatter
    });
  }
  /**
   * Format handoff as readable markdown
   */
  formatHandoff(h) {
    let md = `# Session Handoff

`;
    md += `**Created:** ${h.created}
`;
    if (h.sessionKey) md += `**Session:** ${h.sessionKey}
`;
    if (h.feeling) md += `**Feeling:** ${h.feeling}
`;
    md += `
`;
    md += `## Working On
`;
    h.workingOn.forEach((w) => md += `- ${w}
`);
    md += `
`;
    md += `## Blocked
`;
    if (h.blocked.length === 0) md += `- Nothing currently blocked
`;
    else h.blocked.forEach((b) => md += `- ${b}
`);
    md += `
`;
    md += `## Next Steps
`;
    h.nextSteps.forEach((n) => md += `- ${n}
`);
    if (h.decisions && h.decisions.length > 0) {
      md += `
## Decisions Made
`;
      h.decisions.forEach((d) => md += `- ${d}
`);
    }
    if (h.openQuestions && h.openQuestions.length > 0) {
      md += `
## Open Questions
`;
      h.openQuestions.forEach((q) => md += `- ${q}
`);
    }
    return md;
  }
  // === Session Recap (Bootstrap Hook) ===
  /**
   * Generate a session recap - who I was
   * Call this on bootstrap to restore context
   */
  async generateRecap(options = {}) {
    const { handoffLimit = 3, brief = false } = options;
    const handoffDocs = await this.list("handoffs");
    const recentHandoffs = handoffDocs.sort((a, b) => b.modified.getTime() - a.modified.getTime()).slice(0, handoffLimit).map((doc) => this.parseHandoff(doc));
    const projectDocs = await this.list("projects");
    const activeProjects = projectDocs.filter((d) => d.frontmatter.status !== "completed" && d.frontmatter.status !== "archived").map((d) => d.title);
    const commitmentDocs = await this.list("commitments");
    const pendingCommitments = commitmentDocs.filter((d) => d.frontmatter.status !== "done").map((d) => d.title);
    const decisionDocs = await this.list("decisions");
    const recentDecisions = decisionDocs.sort((a, b) => b.modified.getTime() - a.modified.getTime()).slice(0, brief ? 3 : 5).map((d) => d.title);
    const lessonDocs = await this.list("lessons");
    const recentLessons = lessonDocs.sort((a, b) => b.modified.getTime() - a.modified.getTime()).slice(0, brief ? 3 : 5).map((d) => d.title);
    let keyRelationships = [];
    if (!brief) {
      const peopleDocs = await this.list("people");
      keyRelationships = peopleDocs.filter((d) => d.frontmatter.importance === "high" || d.frontmatter.role).map((d) => `${d.title}${d.frontmatter.role ? ` (${d.frontmatter.role})` : ""}`);
    }
    const feelings = recentHandoffs.map((h) => h.feeling).filter(Boolean);
    const emotionalArc = feelings.length > 0 ? feelings.join(" \u2192 ") : void 0;
    return {
      generated: (/* @__PURE__ */ new Date()).toISOString(),
      recentHandoffs,
      activeProjects,
      pendingCommitments,
      recentDecisions,
      recentLessons,
      keyRelationships,
      emotionalArc
    };
  }
  /**
   * Format recap as readable markdown for injection
   */
  formatRecap(recap, options = {}) {
    const { brief = false } = options;
    let md = `# Who I Was

`;
    md += `*Generated: ${recap.generated}*

`;
    if (recap.emotionalArc) {
      md += `**Emotional arc:** ${recap.emotionalArc}

`;
    }
    if (recap.recentHandoffs.length > 0) {
      md += `## Recent Sessions
`;
      for (const h of recap.recentHandoffs) {
        const datePart = this.extractDatePart(h.created);
        if (brief) {
          md += `- **${datePart}:** ${h.workingOn.slice(0, 2).join(", ")}`;
          if (h.nextSteps.length > 0) md += ` \u2192 ${h.nextSteps[0]}`;
          md += `
`;
        } else {
          md += `
### ${datePart}
`;
          md += `**Working on:** ${h.workingOn.join(", ")}
`;
          if (h.blocked.length > 0) md += `**Blocked:** ${h.blocked.join(", ")}
`;
          md += `**Next:** ${h.nextSteps.join(", ")}
`;
        }
      }
      md += `
`;
    }
    if (recap.activeProjects.length > 0) {
      md += `## Active Projects
`;
      recap.activeProjects.forEach((p) => md += `- ${p}
`);
      md += `
`;
    }
    if (recap.pendingCommitments.length > 0) {
      md += `## Pending Commitments
`;
      recap.pendingCommitments.forEach((c) => md += `- ${c}
`);
      md += `
`;
    }
    if (recap.recentDecisions && recap.recentDecisions.length > 0) {
      md += `## Recent Decisions
`;
      recap.recentDecisions.forEach((d) => md += `- ${d}
`);
      md += `
`;
    }
    if (recap.recentLessons.length > 0) {
      md += `## Recent Lessons
`;
      recap.recentLessons.forEach((l) => md += `- ${l}
`);
      md += `
`;
    }
    if (!brief && recap.keyRelationships.length > 0) {
      md += `## Key People
`;
      recap.keyRelationships.forEach((r) => md += `- ${r}
`);
    }
    return md;
  }
  /**
   * Parse a handoff document back into structured form
   */
  parseHandoff(doc) {
    return {
      created: this.toDateString(doc.frontmatter.date, doc.modified.toISOString()),
      sessionKey: doc.frontmatter.sessionKey,
      workingOn: doc.frontmatter.workingOn || [],
      blocked: doc.frontmatter.blocked || [],
      nextSteps: doc.frontmatter.nextSteps || [],
      decisions: doc.frontmatter.decisions,
      openQuestions: doc.frontmatter.openQuestions,
      feeling: doc.frontmatter.feeling
    };
  }
  // === Private helpers ===
  /**
   * Safely convert a date value to ISO string format.
   * Handles Date objects, strings, and undefined values.
   */
  toDateString(value, fallback) {
    if (value instanceof Date) {
      return value.toISOString();
    }
    if (typeof value === "string" && value.length > 0) {
      return value;
    }
    return fallback || (/* @__PURE__ */ new Date()).toISOString();
  }
  /**
   * Extract the date portion (YYYY-MM-DD) from an ISO date string or Date object.
   * Provides safe handling for various date formats.
   */
  extractDatePart(value) {
    const dateStr = this.toDateString(value);
    if (dateStr.includes("T")) {
      return dateStr.split("T")[0];
    }
    return dateStr.slice(0, 10);
  }
  applyQmdConfig(meta) {
    const collection = meta?.qmdCollection || this.config.qmdCollection || this.config.name;
    const root = meta?.qmdRoot || this.config.qmdRoot || this.config.path;
    this.config.qmdCollection = collection;
    this.config.qmdRoot = root;
    this.search.setVaultPath(this.config.path);
    this.search.setCollection(collection);
    this.search.setCollectionRoot(root);
  }
  slugify(text) {
    return text.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-").trim();
  }
  async saveIndex() {
    const indexPath = path.join(this.config.path, INDEX_FILE);
    const data = this.search.export();
    fs.writeFileSync(indexPath, JSON.stringify(data, null, 2));
    const configPath = path.join(this.config.path, CONFIG_FILE);
    if (fs.existsSync(configPath)) {
      const meta = JSON.parse(fs.readFileSync(configPath, "utf-8"));
      meta.lastUpdated = (/* @__PURE__ */ new Date()).toISOString();
      meta.documentCount = this.search.size;
      fs.writeFileSync(configPath, JSON.stringify(meta, null, 2));
    }
  }
  async createTemplates() {
    const templatesPath = path.join(this.config.path, "templates");
    if (!fs.existsSync(templatesPath)) {
      fs.mkdirSync(templatesPath, { recursive: true });
    }
    const moduleDir = path.dirname(fileURLToPath(import.meta.url));
    const candidates = [
      path.resolve(moduleDir, "../templates"),
      path.resolve(moduleDir, "../../templates")
    ];
    const builtinDir = candidates.find((dir) => fs.existsSync(dir) && fs.statSync(dir).isDirectory());
    if (!builtinDir) return;
    for (const entry of fs.readdirSync(builtinDir, { withFileTypes: true })) {
      if (!entry.isFile() || !entry.name.endsWith(".md")) continue;
      if (entry.name === "daily.md") continue;
      const sourcePath = path.join(builtinDir, entry.name);
      const targetPath = path.join(templatesPath, entry.name);
      if (!fs.existsSync(targetPath)) {
        fs.copyFileSync(sourcePath, targetPath);
      }
    }
  }
  async createWelcomeNote() {
    if (!this.config.categories.includes("inbox")) return;
    const inboxPath = path.join(this.config.path, "inbox", "welcome.md");
    if (fs.existsSync(inboxPath)) return;
    const now = (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
    const content = `---
title: "Welcome to ${this.config.name}"
date: ${now}
type: fact
tags: [welcome, getting-started]
---

# Welcome to ${this.config.name}

Your vault is ready. Here's what you can do:

## Quick Start

- **Capture a thought:** \`clawvault capture "your note here"\`
- **Store structured memory:** \`clawvault store --category decisions --title "My Choice" --content "..."\`
- **Search your vault:** \`clawvault search "query"\`
- **See your knowledge graph:** \`clawvault graph\`
- **Get context for a topic:** \`clawvault context "topic"\`

## Vault Structure

Your vault organizes memories by type \u2014 decisions, lessons, people, projects, and more.
Each category is a folder. Each memory is a markdown file with frontmatter.

## Observational Memory

When connected to an AI agent (like OpenClaw), your vault can automatically observe
conversations and extract important memories \u2014 decisions, lessons, commitments \u2014 without
manual effort.

## Wiki-Links

Use \`[[double brackets]]\` to link between notes. Your memory graph tracks these
connections, building a knowledge network that grows with you.

---

*Delete this file anytime. It's just here to say hello.*
`;
    fs.writeFileSync(inboxPath, content);
  }
  async syncMemoryGraphIndex(options = {}) {
    try {
      await buildOrUpdateMemoryGraphIndex(this.config.path, options);
    } catch {
    }
  }
  generateReadme() {
    const coreCategories = this.config.categories.filter((c) => !["templates", "tasks", "backlog"].includes(c));
    const workCategories = this.config.categories.filter((c) => ["tasks", "backlog"].includes(c));
    return `# ${this.config.name}

An elephant never forgets.

## Structure

### Memory Categories
${coreCategories.map((c) => `- \`${c}/\` \u2014 ${this.getCategoryDescription(c)}`).join("\n")}

### Work Tracking
${workCategories.map((c) => `- \`${c}/\` \u2014 ${this.getCategoryDescription(c)}`).join("\n")}

### Observational Memory
- \`ledger/raw/\` \u2014 Raw session transcripts (source of truth)
- \`ledger/observations/\` \u2014 Compressed observations with importance scores
- \`ledger/reflections/\` \u2014 Weekly reflection summaries

## Quick Reference

\`\`\`bash
# Capture a thought
clawvault capture "important insight about X"

# Store structured memory
clawvault store --category decisions --title "Choice" --content "We chose X because..."

# Search
clawvault search "query"
clawvault vsearch "semantic query"    # vector search

# Knowledge graph
clawvault graph                       # vault stats
clawvault context "topic"             # graph-aware context retrieval

# Session lifecycle
clawvault checkpoint --working-on "task"
clawvault sleep "what I did" --next "what's next"
clawvault wake                        # restore context on startup
\`\`\`

---

*Managed by [ClawVault](https://clawvault.dev)*
`;
  }
  getCategoryDescription(category) {
    const descriptions = {
      // Memory type categories (Benthic's taxonomy)
      facts: "Raw information, data points, things that are true",
      feelings: "Emotional states, reactions, energy levels",
      decisions: "Choices made with context and reasoning",
      rules: "Injectable operational constraints, guardrails, and runbooks",
      lessons: "What I learned, insights, patterns observed",
      commitments: "Promises, goals, obligations to fulfill",
      preferences: "Likes, dislikes, how I want things",
      people: "Relationships, one file per person",
      projects: "Active work, ventures, ongoing efforts",
      // System categories
      handoffs: "Session bridges \u2014 what I was doing, what comes next",
      transcripts: "Session summaries and logs",
      goals: "Long-term and short-term objectives",
      patterns: "Recurring behaviors (\u2192 lessons)",
      inbox: "Quick capture \u2192 process later",
      templates: "Templates for each document type",
      agents: "Other agents \u2014 capabilities, trust levels, coordination notes",
      research: "Deep dives, analysis, reference material",
      tasks: "Active work items with status and context",
      backlog: "Future work \u2014 ideas and tasks not yet started"
    };
    return descriptions[category] || category;
  }
};
async function findVault(startPath = process.cwd()) {
  let current = path.resolve(startPath);
  while (current !== path.dirname(current)) {
    const configPath = path.join(current, CONFIG_FILE);
    if (fs.existsSync(configPath)) {
      const vault = new ClawVault(current);
      await vault.load();
      return vault;
    }
    current = path.dirname(current);
  }
  return null;
}
async function createVault(vaultPath, options = {}, initFlags) {
  const vault = new ClawVault(vaultPath);
  await vault.init(options, initFlags);
  return vault;
}

export {
  ClawVault,
  findVault,
  createVault
};
