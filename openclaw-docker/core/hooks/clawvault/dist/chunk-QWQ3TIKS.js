import {
  loadSchemaTemplateDefinition,
  renderDocumentFromTemplate
} from "./chunk-MFAWT5O5.js";

// src/lib/task-utils.ts
import * as fs2 from "fs";
import * as path2 from "path";
import matter from "gray-matter";

// src/lib/transition-ledger.ts
import * as fs from "fs";
import * as path from "path";
var REGRESSION_PAIRS = [
  ["done", "open"],
  ["done", "blocked"],
  ["in-progress", "blocked"]
];
function isRegression(from, to) {
  return REGRESSION_PAIRS.some(([f, t]) => f === from && t === to);
}
function getLedgerDir(vaultPath) {
  return path.join(path.resolve(vaultPath), "ledger", "transitions");
}
function getTodayLedgerPath(vaultPath) {
  const date = (/* @__PURE__ */ new Date()).toISOString().split("T")[0];
  return path.join(getLedgerDir(vaultPath), `${date}.jsonl`);
}
var RETRYABLE_APPEND_CODES = /* @__PURE__ */ new Set(["ENOENT", "EAGAIN", "EBUSY"]);
var MAX_APPEND_RETRIES = 2;
function asErrno(error) {
  if (!error || typeof error !== "object") {
    return null;
  }
  return error;
}
function formatLedgerWriteError(filePath, error) {
  const errno = asErrno(error);
  const message = error instanceof Error ? error.message : String(error);
  if (errno?.code === "ENOSPC") {
    return new Error(`Failed to write transition ledger at ${filePath}: no space left on device.`);
  }
  if (errno?.code === "EACCES" || errno?.code === "EPERM") {
    return new Error(`Failed to write transition ledger at ${filePath}: permission denied.`);
  }
  return new Error(`Failed to write transition ledger at ${filePath}: ${message}`);
}
function appendTransition(vaultPath, event) {
  const ledgerDir = getLedgerDir(vaultPath);
  try {
    fs.mkdirSync(ledgerDir, { recursive: true });
  } catch (error) {
    throw formatLedgerWriteError(ledgerDir, error);
  }
  const filePath = getTodayLedgerPath(vaultPath);
  const payload = JSON.stringify(event) + "\n";
  for (let attempt = 0; attempt <= MAX_APPEND_RETRIES; attempt += 1) {
    try {
      fs.appendFileSync(filePath, payload);
      return;
    } catch (error) {
      const errno = asErrno(error);
      const code = errno?.code;
      if (code === "ENOENT") {
        try {
          fs.mkdirSync(ledgerDir, { recursive: true });
        } catch (mkdirError) {
          throw formatLedgerWriteError(filePath, mkdirError);
        }
      }
      if (code && RETRYABLE_APPEND_CODES.has(code) && attempt < MAX_APPEND_RETRIES) {
        continue;
      }
      throw formatLedgerWriteError(filePath, error);
    }
  }
}
function buildTransitionEvent(taskId, fromStatus, toStatus, options = {}) {
  const agentId = process.env.OPENCLAW_AGENT_ID || "manual";
  const costTokensRaw = process.env.OPENCLAW_TOKEN_ESTIMATE;
  const costTokens = costTokensRaw ? parseInt(costTokensRaw, 10) : null;
  return {
    task_id: taskId,
    agent_id: agentId,
    from_status: fromStatus,
    to_status: toStatus,
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    confidence: options.confidence ?? (agentId === "manual" ? 1 : 1),
    cost_tokens: costTokens !== null && !isNaN(costTokens) ? costTokens : null,
    reason: options.reason || null
  };
}
function readAllTransitions(vaultPath) {
  const ledgerDir = getLedgerDir(vaultPath);
  if (!fs.existsSync(ledgerDir)) return [];
  let files = [];
  try {
    files = fs.readdirSync(ledgerDir).filter((f) => f.endsWith(".jsonl")).sort();
  } catch {
    return [];
  }
  const events = [];
  for (const file of files) {
    let lines = [];
    try {
      lines = fs.readFileSync(path.join(ledgerDir, file), "utf-8").split("\n").filter((l) => l.trim());
    } catch {
      continue;
    }
    for (const line of lines) {
      try {
        events.push(JSON.parse(line));
      } catch {
      }
    }
  }
  return events;
}
function queryTransitions(vaultPath, filters = {}) {
  let events = readAllTransitions(vaultPath);
  if (filters.taskId) {
    events = events.filter((e) => e.task_id === filters.taskId);
  }
  if (filters.agent) {
    events = events.filter((e) => e.agent_id === filters.agent);
  }
  if (filters.failed) {
    events = events.filter((e) => isRegression(e.from_status, e.to_status));
  }
  return events;
}
function countBlockedTransitions(vaultPath, taskId) {
  const events = readAllTransitions(vaultPath);
  return events.filter((e) => e.task_id === taskId && e.to_status === "blocked").length;
}
function formatTransitionsTable(events) {
  if (events.length === 0) return "No transitions found.\n";
  const headers = ["TIMESTAMP", "TASK", "FROM\u2192TO", "AGENT", "REASON"];
  const widths = [20, 20, 24, 16, 30];
  let output = headers.map((h, i) => h.padEnd(widths[i])).join("  ") + "\n";
  output += "-".repeat(widths.reduce((a, b) => a + b + 2, 0)) + "\n";
  for (const e of events) {
    const ts = e.timestamp.replace("T", " ").slice(0, 19);
    const taskId = e.task_id.length > widths[1] ? e.task_id.slice(0, widths[1] - 3) + "..." : e.task_id;
    const transition = `${e.from_status} \u2192 ${e.to_status}`;
    const reason = e.reason ? e.reason.length > widths[4] ? e.reason.slice(0, widths[4] - 3) + "..." : e.reason : "-";
    output += [
      ts.padEnd(widths[0]),
      taskId.padEnd(widths[1]),
      transition.padEnd(widths[2]),
      e.agent_id.padEnd(widths[3]),
      reason
    ].join("  ") + "\n";
  }
  return output;
}

// src/lib/task-utils.ts
function slugify(text) {
  return text.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-").replace(/^-+|-+$/g, "").trim();
}
function getTasksDir(vaultPath) {
  return path2.join(path2.resolve(vaultPath), "tasks");
}
function getBacklogDir(vaultPath) {
  return path2.join(path2.resolve(vaultPath), "backlog");
}
function ensureTasksDir(vaultPath) {
  const tasksDir = getTasksDir(vaultPath);
  if (!fs2.existsSync(tasksDir)) {
    fs2.mkdirSync(tasksDir, { recursive: true });
  }
}
function ensureBacklogDir(vaultPath) {
  const backlogDir = getBacklogDir(vaultPath);
  if (!fs2.existsSync(backlogDir)) {
    fs2.mkdirSync(backlogDir, { recursive: true });
  }
}
function getTaskPath(vaultPath, slug) {
  return path2.join(getTasksDir(vaultPath), `${slug}.md`);
}
function getBacklogPath(vaultPath, slug) {
  return path2.join(getBacklogDir(vaultPath), `${slug}.md`);
}
function extractTitle(content) {
  const match = content.match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : "";
}
function parseDueDate(value) {
  if (!value) return null;
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) return null;
  return timestamp;
}
function startOfToday() {
  const now = /* @__PURE__ */ new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
}
function buildTaskFrontmatterFallback(now, options) {
  const frontmatter = {
    status: "open",
    created: now,
    updated: now
  };
  if (options.source) frontmatter.source = options.source;
  if (options.owner) frontmatter.owner = options.owner;
  if (options.project) frontmatter.project = options.project;
  if (options.priority) frontmatter.priority = options.priority;
  if (options.due) frontmatter.due = options.due;
  if (options.tags && options.tags.length > 0) frontmatter.tags = options.tags;
  if (options.description) frontmatter.description = options.description;
  if (options.estimate) frontmatter.estimate = options.estimate;
  if (options.parent) frontmatter.parent = options.parent;
  if (options.depends_on && options.depends_on.length > 0) frontmatter.depends_on = options.depends_on;
  return frontmatter;
}
function buildTaskContentFallback(title, options) {
  let content = `# ${title}
`;
  const links = [];
  if (options.owner) links.push(`[[${options.owner}]]`);
  if (options.project) links.push(`[[${options.project}]]`);
  if (links.length > 0) {
    content += `
${links.join(" | ")}
`;
  }
  if (options.content) {
    content += `
${options.content}
`;
  }
  return content;
}
function buildTaskTemplateOverrides(options) {
  const overrides = {};
  if (options.source) overrides.source = options.source;
  if (options.owner) overrides.owner = options.owner;
  if (options.project) overrides.project = options.project;
  if (options.priority) overrides.priority = options.priority;
  if (options.due) overrides.due = options.due;
  if (options.tags && options.tags.length > 0) overrides.tags = options.tags;
  if (options.description) overrides.description = options.description;
  if (options.estimate) overrides.estimate = options.estimate;
  if (options.parent) overrides.parent = options.parent;
  if (options.depends_on && options.depends_on.length > 0) overrides.depends_on = options.depends_on;
  return overrides;
}
function buildTaskTemplateVariables(title, slug, options) {
  const ownerLink = options.owner ? `[[${options.owner}]]` : "";
  const projectLink = options.project ? `[[${options.project}]]` : "";
  const linksLine = [ownerLink, projectLink].filter(Boolean).join(" | ");
  return {
    title,
    slug,
    source: options.source ?? "",
    owner: options.owner ?? "",
    project: options.project ?? "",
    priority: options.priority ?? "",
    due: options.due ?? "",
    tags_csv: (options.tags || []).join(", "),
    description: options.description ?? "",
    estimate: options.estimate ?? "",
    parent: options.parent ?? "",
    depends_on_csv: (options.depends_on || []).join(", "),
    content: options.content ?? "",
    owner_link: ownerLink,
    project_link: projectLink,
    links_line: linksLine
  };
}
var VALID_TASK_STATUSES = /* @__PURE__ */ new Set([
  "open",
  "in-progress",
  "blocked",
  "done"
]);
function isTaskStatus(value) {
  return typeof value === "string" && VALID_TASK_STATUSES.has(value);
}
function persistTaskFrontmatter(task, frontmatter) {
  fs2.writeFileSync(task.path, matter.stringify(task.content, frontmatter));
}
function resolveStatusTransition(previousStatus, nextStatus) {
  if (!isTaskStatus(previousStatus) || !isTaskStatus(nextStatus)) {
    return null;
  }
  if (previousStatus === nextStatus) {
    return null;
  }
  return { fromStatus: previousStatus, toStatus: nextStatus };
}
function logStatusTransition({
  vaultPath,
  task,
  fromStatus,
  toStatus,
  frontmatter,
  options
}) {
  const normalizedReason = typeof options.reason === "string" ? options.reason.trim() : "";
  const reason = normalizedReason || (isRegression(fromStatus, toStatus) ? `regression: ${fromStatus} -> ${toStatus}` : void 0);
  const event = buildTransitionEvent(task.slug, fromStatus, toStatus, {
    confidence: options.confidence,
    reason
  });
  try {
    appendTransition(vaultPath, event);
  } catch {
    return frontmatter;
  }
  if (toStatus !== "blocked" || frontmatter.escalation) {
    return frontmatter;
  }
  let blockedCount = 0;
  try {
    blockedCount = countBlockedTransitions(vaultPath, task.slug);
  } catch {
    return frontmatter;
  }
  if (blockedCount < 3) {
    return frontmatter;
  }
  const escalatedFrontmatter = {
    ...frontmatter,
    escalation: true
  };
  try {
    persistTaskFrontmatter(task, escalatedFrontmatter);
    return escalatedFrontmatter;
  } catch {
    return frontmatter;
  }
}
function readTask(vaultPath, slug) {
  const taskPath = getTaskPath(vaultPath, slug);
  if (!fs2.existsSync(taskPath)) {
    return null;
  }
  try {
    const raw = fs2.readFileSync(taskPath, "utf-8");
    const { data, content } = matter(raw);
    const title = extractTitle(content) || slug;
    return {
      slug,
      title,
      content,
      frontmatter: data,
      path: taskPath
    };
  } catch {
    return null;
  }
}
function readBacklogItem(vaultPath, slug) {
  const backlogPath = getBacklogPath(vaultPath, slug);
  if (!fs2.existsSync(backlogPath)) {
    return null;
  }
  try {
    const raw = fs2.readFileSync(backlogPath, "utf-8");
    const { data, content } = matter(raw);
    const title = extractTitle(content) || slug;
    return {
      slug,
      title,
      content,
      frontmatter: data,
      path: backlogPath
    };
  } catch {
    return null;
  }
}
function listTasks(vaultPath, filters) {
  const tasksDir = getTasksDir(vaultPath);
  if (!fs2.existsSync(tasksDir)) {
    return [];
  }
  const tasks = [];
  const entries = fs2.readdirSync(tasksDir, { withFileTypes: true });
  const today = startOfToday();
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith(".md")) {
      continue;
    }
    const slug = entry.name.replace(/\.md$/, "");
    const task = readTask(vaultPath, slug);
    if (!task) continue;
    if (filters) {
      if (filters.status && task.frontmatter.status !== filters.status) continue;
      if (filters.owner && task.frontmatter.owner !== filters.owner) continue;
      if (filters.project && task.frontmatter.project !== filters.project) continue;
      if (filters.priority && task.frontmatter.priority !== filters.priority) continue;
      if (filters.due && !task.frontmatter.due) continue;
      if (filters.tag) {
        const tags = task.frontmatter.tags || [];
        const hasTag = tags.some((tag) => tag.toLowerCase() === filters.tag?.toLowerCase());
        if (!hasTag) continue;
      }
      if (filters.overdue) {
        const dueTime = parseDueDate(task.frontmatter.due);
        if (task.frontmatter.status === "done" || dueTime === null || dueTime >= today) continue;
      }
    }
    tasks.push(task);
  }
  const priorityOrder = {
    critical: 0,
    high: 1,
    medium: 2,
    low: 3
  };
  if (filters?.due || filters?.overdue) {
    return tasks.sort((a, b) => {
      const aDue = parseDueDate(a.frontmatter.due);
      const bDue = parseDueDate(b.frontmatter.due);
      if (aDue !== null && bDue !== null && aDue !== bDue) {
        return aDue - bDue;
      }
      if (aDue !== null && bDue === null) return -1;
      if (aDue === null && bDue !== null) return 1;
      return new Date(b.frontmatter.created).getTime() - new Date(a.frontmatter.created).getTime();
    });
  }
  return tasks.sort((a, b) => {
    const aPriority = priorityOrder[a.frontmatter.priority || "low"];
    const bPriority = priorityOrder[b.frontmatter.priority || "low"];
    if (aPriority !== bPriority) {
      return aPriority - bPriority;
    }
    return new Date(b.frontmatter.created).getTime() - new Date(a.frontmatter.created).getTime();
  });
}
function listBacklogItems(vaultPath, filters) {
  const backlogDir = getBacklogDir(vaultPath);
  if (!fs2.existsSync(backlogDir)) {
    return [];
  }
  const items = [];
  const entries = fs2.readdirSync(backlogDir, { withFileTypes: true });
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith(".md")) {
      continue;
    }
    const slug = entry.name.replace(/\.md$/, "");
    const item = readBacklogItem(vaultPath, slug);
    if (!item) continue;
    if (filters) {
      if (filters.project && item.frontmatter.project !== filters.project) continue;
      if (filters.source && item.frontmatter.source !== filters.source) continue;
    }
    items.push(item);
  }
  return items.sort((a, b) => {
    return new Date(b.frontmatter.created).getTime() - new Date(a.frontmatter.created).getTime();
  });
}
function createTask(vaultPath, title, options = {}) {
  ensureTasksDir(vaultPath);
  const slug = slugify(title);
  const taskPath = getTaskPath(vaultPath, slug);
  if (fs2.existsSync(taskPath)) {
    throw new Error(`Task already exists: ${slug}`);
  }
  const now = (/* @__PURE__ */ new Date()).toISOString();
  const template = loadSchemaTemplateDefinition("task", {
    vaultPath: path2.resolve(vaultPath)
  });
  let frontmatter;
  let content;
  if (template) {
    const rendered = renderDocumentFromTemplate(template, {
      title,
      type: "task",
      now: new Date(now),
      variables: buildTaskTemplateVariables(title, slug, options),
      overrides: buildTaskTemplateOverrides(options),
      frontmatter: { pruneEmpty: true }
    });
    const templateFrontmatter = rendered.frontmatter;
    frontmatter = {
      ...templateFrontmatter,
      status: isTaskStatus(templateFrontmatter.status) ? templateFrontmatter.status : "open",
      created: typeof templateFrontmatter.created === "string" && templateFrontmatter.created ? templateFrontmatter.created : now,
      updated: typeof templateFrontmatter.updated === "string" && templateFrontmatter.updated ? templateFrontmatter.updated : now
    };
    content = rendered.content;
  } else {
    frontmatter = buildTaskFrontmatterFallback(now, options);
    content = buildTaskContentFallback(title, options);
  }
  const fileContent = matter.stringify(content, frontmatter);
  fs2.writeFileSync(taskPath, fileContent);
  return {
    slug,
    title,
    content,
    frontmatter,
    path: taskPath
  };
}
function updateTask(vaultPath, slug, updates, options = {}) {
  const task = readTask(vaultPath, slug);
  if (!task) {
    throw new Error(`Task not found: ${slug}`);
  }
  if (updates.status !== void 0 && !isTaskStatus(updates.status)) {
    throw new Error(`Invalid task status: ${String(updates.status)}`);
  }
  const previousStatus = task.frontmatter.status;
  const now = (/* @__PURE__ */ new Date()).toISOString();
  let newFrontmatter = {
    ...task.frontmatter,
    updated: now
  };
  if (updates.status !== void 0) {
    newFrontmatter.status = updates.status;
    if (updates.status === "done" && !newFrontmatter.completed) {
      newFrontmatter.completed = now;
    }
    if (updates.status !== "done") {
      delete newFrontmatter.completed;
    }
  }
  if (updates.source !== void 0) {
    if (updates.source === null || updates.source.trim() === "") {
      delete newFrontmatter.source;
    } else {
      newFrontmatter.source = updates.source;
    }
  }
  if (updates.owner !== void 0) {
    if (updates.owner === null || updates.owner.trim() === "") {
      delete newFrontmatter.owner;
    } else {
      newFrontmatter.owner = updates.owner;
    }
  }
  if (updates.project !== void 0) {
    if (updates.project === null || updates.project.trim() === "") {
      delete newFrontmatter.project;
    } else {
      newFrontmatter.project = updates.project;
    }
  }
  if (updates.priority !== void 0) {
    if (updates.priority === null) {
      delete newFrontmatter.priority;
    } else {
      newFrontmatter.priority = updates.priority;
    }
  }
  if (updates.due !== void 0) {
    if (updates.due === null || updates.due.trim() === "") {
      delete newFrontmatter.due;
    } else {
      newFrontmatter.due = updates.due;
    }
  }
  if (updates.tags !== void 0) {
    if (updates.tags === null) {
      delete newFrontmatter.tags;
    } else {
      const normalizedTags = updates.tags.map((tag) => tag.trim()).filter(Boolean);
      if (normalizedTags.length === 0) {
        delete newFrontmatter.tags;
      } else {
        newFrontmatter.tags = normalizedTags;
      }
    }
  }
  if (updates.completed !== void 0) {
    if (updates.completed === null || updates.completed.trim() === "") {
      delete newFrontmatter.completed;
    } else {
      newFrontmatter.completed = updates.completed;
    }
  }
  if (updates.escalation !== void 0) {
    if (updates.escalation === null) {
      delete newFrontmatter.escalation;
    } else {
      newFrontmatter.escalation = updates.escalation;
    }
  }
  if (updates.confidence !== void 0) {
    if (updates.confidence === null) {
      delete newFrontmatter.confidence;
    } else {
      newFrontmatter.confidence = updates.confidence;
    }
  }
  if (updates.reason !== void 0) {
    if (updates.reason === null || updates.reason.trim() === "") {
      delete newFrontmatter.reason;
    } else {
      newFrontmatter.reason = updates.reason;
    }
  }
  if (updates.description !== void 0) {
    if (updates.description === null || updates.description.trim() === "") {
      delete newFrontmatter.description;
    } else {
      newFrontmatter.description = updates.description;
    }
  }
  if (updates.estimate !== void 0) {
    if (updates.estimate === null || updates.estimate.trim() === "") {
      delete newFrontmatter.estimate;
    } else {
      newFrontmatter.estimate = updates.estimate;
    }
  }
  if (updates.parent !== void 0) {
    if (updates.parent === null || updates.parent.trim() === "") {
      delete newFrontmatter.parent;
    } else {
      newFrontmatter.parent = updates.parent;
    }
  }
  if (updates.depends_on !== void 0) {
    if (updates.depends_on === null) {
      delete newFrontmatter.depends_on;
    } else {
      const normalizedDeps = updates.depends_on.map((dep) => dep.trim()).filter(Boolean);
      if (normalizedDeps.length === 0) {
        delete newFrontmatter.depends_on;
      } else {
        newFrontmatter.depends_on = normalizedDeps;
      }
    }
  }
  if (updates.blocked_by !== void 0) {
    if (updates.blocked_by === null || updates.blocked_by.trim() === "") {
      delete newFrontmatter.blocked_by;
    } else {
      newFrontmatter.blocked_by = updates.blocked_by;
    }
  } else if (updates.status !== void 0 && updates.status !== "blocked") {
    delete newFrontmatter.blocked_by;
  }
  persistTaskFrontmatter(task, newFrontmatter);
  const transition = options.skipTransition ? null : resolveStatusTransition(previousStatus, newFrontmatter.status);
  if (transition) {
    const confidence = options.confidence ?? (typeof updates.confidence === "number" ? updates.confidence : void 0);
    const reason = options.reason ?? updates.reason ?? null;
    newFrontmatter = logStatusTransition({
      vaultPath,
      task,
      fromStatus: transition.fromStatus,
      toStatus: transition.toStatus,
      frontmatter: newFrontmatter,
      options: {
        confidence,
        reason
      }
    });
  }
  return {
    ...task,
    frontmatter: newFrontmatter
  };
}
function completeTask(vaultPath, slug, options = {}) {
  return updateTask(vaultPath, slug, { status: "done" }, options);
}
function createBacklogItem(vaultPath, title, options = {}) {
  ensureBacklogDir(vaultPath);
  const slug = slugify(title);
  const backlogPath = getBacklogPath(vaultPath, slug);
  if (fs2.existsSync(backlogPath)) {
    throw new Error(`Backlog item already exists: ${slug}`);
  }
  const now = (/* @__PURE__ */ new Date()).toISOString();
  const frontmatter = {
    created: now
  };
  if (options.source) frontmatter.source = options.source;
  if (options.project) frontmatter.project = options.project;
  if (options.tags && options.tags.length > 0) frontmatter.tags = options.tags;
  let content = `# ${title}
`;
  const links = [];
  if (options.source) links.push(`[[${options.source}]]`);
  if (options.project) links.push(`[[${options.project}]]`);
  if (links.length > 0) {
    content += `
${links.join(" | ")}
`;
  }
  if (options.content) {
    content += `
${options.content}
`;
  }
  const fileContent = matter.stringify(content, frontmatter);
  fs2.writeFileSync(backlogPath, fileContent);
  return {
    slug,
    title,
    content,
    frontmatter,
    path: backlogPath
  };
}
function updateBacklogItem(vaultPath, slug, updates) {
  const backlogItem = readBacklogItem(vaultPath, slug);
  if (!backlogItem) {
    throw new Error(`Backlog item not found: ${slug}`);
  }
  const newFrontmatter = {
    ...backlogItem.frontmatter
  };
  if (updates.source !== void 0) newFrontmatter.source = updates.source;
  if (updates.project !== void 0) newFrontmatter.project = updates.project;
  if (updates.tags !== void 0) newFrontmatter.tags = updates.tags;
  if (updates.lastSeen !== void 0) newFrontmatter.lastSeen = updates.lastSeen;
  const fileContent = matter.stringify(backlogItem.content, newFrontmatter);
  fs2.writeFileSync(backlogItem.path, fileContent);
  return {
    ...backlogItem,
    frontmatter: newFrontmatter
  };
}
function promoteBacklogItem(vaultPath, slug, options = {}) {
  const backlogItem = readBacklogItem(vaultPath, slug);
  if (!backlogItem) {
    throw new Error(`Backlog item not found: ${slug}`);
  }
  const task = createTask(vaultPath, backlogItem.title, {
    owner: options.owner,
    project: backlogItem.frontmatter.project,
    priority: options.priority,
    due: options.due,
    content: backlogItem.content.replace(/^#\s+.+\n/, "").trim(),
    // Remove title from content
    tags: backlogItem.frontmatter.tags
  });
  fs2.unlinkSync(backlogItem.path);
  return task;
}
function getBlockedTasks(vaultPath, project) {
  const filters = { status: "blocked" };
  if (project) filters.project = project;
  return listTasks(vaultPath, filters);
}
function getActiveTasks(vaultPath, filters) {
  const allTasks = listTasks(vaultPath, filters);
  return allTasks.filter((t) => t.frontmatter.status === "open" || t.frontmatter.status === "in-progress");
}
function listSubtasks(vaultPath, parentSlug) {
  return listTasks(vaultPath).filter((task) => task.frontmatter.parent === parentSlug);
}
function listDependentTasks(vaultPath, dependencySlug) {
  return listTasks(vaultPath).filter((task) => {
    const dependencies = task.frontmatter.depends_on || [];
    return dependencies.includes(dependencySlug);
  });
}
function getRecentlyCompletedTasks(vaultPath, limit = 10) {
  const allTasks = listTasks(vaultPath, { status: "done" });
  return allTasks.filter((t) => t.frontmatter.completed).sort((a, b) => {
    const aCompleted = new Date(a.frontmatter.completed || 0).getTime();
    const bCompleted = new Date(b.frontmatter.completed || 0).getTime();
    return bCompleted - aCompleted;
  }).slice(0, limit);
}
function getStatusIcon(status) {
  switch (status) {
    case "in-progress":
      return "\u25CF";
    case "blocked":
      return "\u25A0";
    case "open":
      return "\u25CB";
    case "done":
      return "\u2713";
    default:
      return "\u25CB";
  }
}
function getStatusDisplay(status) {
  switch (status) {
    case "in-progress":
      return "active";
    case "blocked":
      return "blocked";
    case "open":
      return "open";
    case "done":
      return "done";
    default:
      return status;
  }
}

export {
  isRegression,
  appendTransition,
  buildTransitionEvent,
  readAllTransitions,
  queryTransitions,
  countBlockedTransitions,
  formatTransitionsTable,
  slugify,
  getTasksDir,
  getBacklogDir,
  ensureTasksDir,
  ensureBacklogDir,
  getTaskPath,
  getBacklogPath,
  readTask,
  readBacklogItem,
  listTasks,
  listBacklogItems,
  createTask,
  updateTask,
  completeTask,
  createBacklogItem,
  updateBacklogItem,
  promoteBacklogItem,
  getBlockedTasks,
  getActiveTasks,
  listSubtasks,
  listDependentTasks,
  getRecentlyCompletedTasks,
  getStatusIcon,
  getStatusDisplay
};
