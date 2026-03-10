import {
  listTasks,
  slugify
} from "./chunk-QWQ3TIKS.js";
import {
  loadSchemaTemplateDefinition,
  renderDocumentFromTemplate
} from "./chunk-MFAWT5O5.js";

// src/lib/project-utils.ts
import * as fs from "fs";
import * as path from "path";
import matter from "gray-matter";
function extractTitle(content) {
  const match = content.match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : "";
}
function isDateSlug(slug) {
  return /^\d{4}-\d{2}-\d{2}$/.test(slug);
}
function normalizeStringArray(value) {
  return value.map((item) => item.trim()).filter(Boolean);
}
function getProjectsDir(vaultPath) {
  return path.join(path.resolve(vaultPath), "projects");
}
function ensureProjectsDir(vaultPath) {
  const projectsDir = getProjectsDir(vaultPath);
  if (!fs.existsSync(projectsDir)) {
    fs.mkdirSync(projectsDir, { recursive: true });
  }
}
function getProjectPath(vaultPath, slug) {
  return path.join(getProjectsDir(vaultPath), `${slug}.md`);
}
function parseProjectDateValue(filePath) {
  const filename = path.basename(filePath, ".md");
  if (/^\d{4}-\d{2}-\d{2}$/.test(filename)) {
    const dateTs = Date.parse(`${filename}T00:00:00.000Z`);
    if (!Number.isNaN(dateTs)) {
      return dateTs;
    }
  }
  return fs.statSync(filePath).mtime.getTime();
}
function parseSortableTimestamp(value) {
  if (!value) return 0;
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}
function normalizeProjectStatus(value) {
  if (value === "active" || value === "paused" || value === "completed" || value === "archived") {
    return value;
  }
  return "active";
}
function buildProjectFrontmatterFallback(now, options) {
  const frontmatter = {
    type: "project",
    status: options.status ?? "active",
    created: now,
    updated: now
  };
  if (options.owner) frontmatter.owner = options.owner;
  if (options.team && options.team.length > 0) {
    const team = normalizeStringArray(options.team);
    if (team.length > 0) frontmatter.team = team;
  }
  if (options.client) frontmatter.client = options.client;
  if (options.tags && options.tags.length > 0) {
    const tags = normalizeStringArray(options.tags);
    if (tags.length > 0) frontmatter.tags = tags;
  }
  if (options.description) frontmatter.description = options.description;
  if (options.started) frontmatter.started = options.started;
  if (options.deadline) frontmatter.deadline = options.deadline;
  if (options.repo) frontmatter.repo = options.repo;
  if (options.url) frontmatter.url = options.url;
  if (options.completed) frontmatter.completed = options.completed;
  if (options.reason) frontmatter.reason = options.reason;
  return frontmatter;
}
function buildProjectContentFallback(title, options) {
  let content = `# ${title}
`;
  const wikiLinks = /* @__PURE__ */ new Set();
  if (options.owner) wikiLinks.add(options.owner);
  if (options.client) wikiLinks.add(options.client);
  for (const member of options.team || []) {
    const trimmed = member.trim();
    if (trimmed) wikiLinks.add(trimmed);
  }
  if (wikiLinks.size > 0) {
    content += `
${Array.from(wikiLinks).map((link) => `[[${link}]]`).join(" | ")}
`;
  }
  if (options.content) {
    content += `
${options.content}
`;
  }
  return content;
}
function buildProjectTemplateOverrides(options) {
  const overrides = {};
  if (options.status) overrides.status = options.status;
  if (options.owner) overrides.owner = options.owner;
  if (options.team && options.team.length > 0) {
    const team = normalizeStringArray(options.team);
    if (team.length > 0) overrides.team = team;
  }
  if (options.client) overrides.client = options.client;
  if (options.tags && options.tags.length > 0) {
    const tags = normalizeStringArray(options.tags);
    if (tags.length > 0) overrides.tags = tags;
  }
  if (options.description) overrides.description = options.description;
  if (options.started) overrides.started = options.started;
  if (options.deadline) overrides.deadline = options.deadline;
  if (options.repo) overrides.repo = options.repo;
  if (options.url) overrides.url = options.url;
  if (options.completed) overrides.completed = options.completed;
  if (options.reason) overrides.reason = options.reason;
  return overrides;
}
function buildProjectTemplateVariables(title, slug, options) {
  const ownerLink = options.owner ? `[[${options.owner}]]` : "";
  const clientLink = options.client ? `[[${options.client}]]` : "";
  const teamLinks = (options.team || []).map((member) => member.trim()).filter(Boolean).map((member) => `[[${member}]]`);
  const linksLine = [ownerLink, clientLink, ...teamLinks].filter(Boolean).join(" | ");
  return {
    title,
    slug,
    status: options.status ?? "",
    owner: options.owner ?? "",
    client: options.client ?? "",
    team_csv: (options.team || []).join(", "),
    tags_csv: (options.tags || []).join(", "),
    description: options.description ?? "",
    started: options.started ?? "",
    deadline: options.deadline ?? "",
    repo: options.repo ?? "",
    url: options.url ?? "",
    completed: options.completed ?? "",
    reason: options.reason ?? "",
    content: options.content ?? "",
    owner_link: ownerLink,
    client_link: clientLink,
    team_links_line: teamLinks.join(" | "),
    links_line: linksLine
  };
}
function normalizeProjectFrontmatter(frontmatter) {
  const normalizedCreated = typeof frontmatter.created === "string" && frontmatter.created ? frontmatter.created : (/* @__PURE__ */ new Date(0)).toISOString();
  const normalizedUpdated = typeof frontmatter.updated === "string" && frontmatter.updated ? frontmatter.updated : normalizedCreated;
  const normalized = {
    ...frontmatter,
    type: "project",
    status: normalizeProjectStatus(frontmatter.status),
    created: normalizedCreated,
    updated: normalizedUpdated
  };
  if (normalized.team) {
    const team = normalizeStringArray(normalized.team);
    if (team.length === 0) {
      delete normalized.team;
    } else {
      normalized.team = team;
    }
  }
  if (normalized.tags) {
    const tags = normalizeStringArray(normalized.tags);
    if (tags.length === 0) {
      delete normalized.tags;
    } else {
      normalized.tags = tags;
    }
  }
  return normalized;
}
function listProjects(vaultPath, filters) {
  const projectsDir = getProjectsDir(vaultPath);
  if (!fs.existsSync(projectsDir)) {
    return [];
  }
  const projects = [];
  const entries = fs.readdirSync(projectsDir, { withFileTypes: true });
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith(".md")) {
      continue;
    }
    const slug = entry.name.replace(/\.md$/, "");
    if (isDateSlug(slug)) {
      continue;
    }
    const project = readProject(vaultPath, slug);
    if (!project) continue;
    if (filters) {
      if (filters.status && project.frontmatter.status !== filters.status) continue;
      if (filters.owner && project.frontmatter.owner !== filters.owner) continue;
      if (filters.client && project.frontmatter.client !== filters.client) continue;
      if (filters.tag) {
        const tags = project.frontmatter.tags || [];
        const hasTag = tags.some((tag) => tag.toLowerCase() === filters.tag?.toLowerCase());
        if (!hasTag) continue;
      }
    }
    projects.push(project);
  }
  return projects.sort((left, right) => {
    const rightTime = parseSortableTimestamp(right.frontmatter.updated || right.frontmatter.created);
    const leftTime = parseSortableTimestamp(left.frontmatter.updated || left.frontmatter.created);
    return rightTime - leftTime;
  });
}
function readProject(vaultPath, slug) {
  if (!slug || isDateSlug(slug) || slug.includes(path.sep)) {
    return null;
  }
  const projectPath = getProjectPath(vaultPath, slug);
  if (!fs.existsSync(projectPath)) {
    return null;
  }
  try {
    const raw = fs.readFileSync(projectPath, "utf-8");
    const { data, content } = matter(raw);
    if (data.type !== "project") {
      return null;
    }
    const frontmatter = normalizeProjectFrontmatter(data);
    const title = extractTitle(content) || slug;
    return {
      slug,
      title,
      content,
      frontmatter
    };
  } catch {
    return null;
  }
}
function createProject(vaultPath, title, options = {}) {
  ensureProjectsDir(vaultPath);
  const slug = slugify(title);
  const projectPath = getProjectPath(vaultPath, slug);
  if (fs.existsSync(projectPath)) {
    throw new Error(`Project already exists: ${slug}`);
  }
  const now = (/* @__PURE__ */ new Date()).toISOString();
  const template = loadSchemaTemplateDefinition("project", {
    vaultPath: path.resolve(vaultPath)
  });
  let frontmatter;
  let content;
  if (template) {
    const rendered = renderDocumentFromTemplate(template, {
      title,
      type: "project",
      now: new Date(now),
      variables: buildProjectTemplateVariables(title, slug, options),
      overrides: buildProjectTemplateOverrides(options),
      frontmatter: { pruneEmpty: true }
    });
    const templateFrontmatter = rendered.frontmatter;
    frontmatter = normalizeProjectFrontmatter({
      ...templateFrontmatter,
      type: "project",
      status: normalizeProjectStatus(templateFrontmatter.status),
      created: typeof templateFrontmatter.created === "string" && templateFrontmatter.created ? templateFrontmatter.created : now,
      updated: typeof templateFrontmatter.updated === "string" && templateFrontmatter.updated ? templateFrontmatter.updated : now
    });
    content = rendered.content;
  } else {
    frontmatter = buildProjectFrontmatterFallback(now, options);
    content = buildProjectContentFallback(title, options);
  }
  const fileContent = matter.stringify(content, frontmatter);
  fs.writeFileSync(projectPath, fileContent);
  return {
    slug,
    title,
    content,
    frontmatter
  };
}
function updateProject(vaultPath, slug, updates) {
  const project = readProject(vaultPath, slug);
  if (!project) {
    throw new Error(`Project not found: ${slug}`);
  }
  const now = (/* @__PURE__ */ new Date()).toISOString();
  const nextFrontmatter = {
    ...project.frontmatter,
    type: "project",
    updated: now
  };
  if (updates.status !== void 0) {
    nextFrontmatter.status = updates.status;
    if (updates.status === "completed" && !updates.completed && !nextFrontmatter.completed) {
      nextFrontmatter.completed = now;
    }
  }
  if (updates.owner !== void 0) {
    if (updates.owner === null || updates.owner.trim() === "") {
      delete nextFrontmatter.owner;
    } else {
      nextFrontmatter.owner = updates.owner;
    }
  }
  if (updates.team !== void 0) {
    if (updates.team === null) {
      delete nextFrontmatter.team;
    } else {
      const team = normalizeStringArray(updates.team);
      if (team.length === 0) {
        delete nextFrontmatter.team;
      } else {
        nextFrontmatter.team = team;
      }
    }
  }
  if (updates.client !== void 0) {
    if (updates.client === null || updates.client.trim() === "") {
      delete nextFrontmatter.client;
    } else {
      nextFrontmatter.client = updates.client;
    }
  }
  if (updates.tags !== void 0) {
    if (updates.tags === null) {
      delete nextFrontmatter.tags;
    } else {
      const tags = normalizeStringArray(updates.tags);
      if (tags.length === 0) {
        delete nextFrontmatter.tags;
      } else {
        nextFrontmatter.tags = tags;
      }
    }
  }
  if (updates.description !== void 0) {
    if (updates.description === null || updates.description.trim() === "") {
      delete nextFrontmatter.description;
    } else {
      nextFrontmatter.description = updates.description;
    }
  }
  if (updates.started !== void 0) {
    if (updates.started === null || updates.started.trim() === "") {
      delete nextFrontmatter.started;
    } else {
      nextFrontmatter.started = updates.started;
    }
  }
  if (updates.deadline !== void 0) {
    if (updates.deadline === null || updates.deadline.trim() === "") {
      delete nextFrontmatter.deadline;
    } else {
      nextFrontmatter.deadline = updates.deadline;
    }
  }
  if (updates.repo !== void 0) {
    if (updates.repo === null || updates.repo.trim() === "") {
      delete nextFrontmatter.repo;
    } else {
      nextFrontmatter.repo = updates.repo;
    }
  }
  if (updates.url !== void 0) {
    if (updates.url === null || updates.url.trim() === "") {
      delete nextFrontmatter.url;
    } else {
      nextFrontmatter.url = updates.url;
    }
  }
  if (updates.completed !== void 0) {
    if (updates.completed === null || updates.completed.trim() === "") {
      delete nextFrontmatter.completed;
    } else {
      nextFrontmatter.completed = updates.completed;
    }
  }
  if (updates.reason !== void 0) {
    if (updates.reason === null || updates.reason.trim() === "") {
      delete nextFrontmatter.reason;
    } else {
      nextFrontmatter.reason = updates.reason;
    }
  }
  const projectPath = getProjectPath(vaultPath, slug);
  fs.writeFileSync(projectPath, matter.stringify(project.content, nextFrontmatter));
  return {
    ...project,
    frontmatter: nextFrontmatter
  };
}
function archiveProject(vaultPath, slug, reason) {
  return updateProject(vaultPath, slug, {
    status: "archived",
    reason: reason ?? null,
    completed: (/* @__PURE__ */ new Date()).toISOString()
  });
}
function getProjectTasks(vaultPath, slug) {
  return listTasks(vaultPath, { project: slug });
}
function getProjectActivity(vaultPath, slug) {
  const projectActivityDir = path.join(getProjectsDir(vaultPath), slug);
  if (!fs.existsSync(projectActivityDir) || !fs.statSync(projectActivityDir).isDirectory()) {
    return [];
  }
  const entries = fs.readdirSync(projectActivityDir, { withFileTypes: true });
  const files = entries.filter((entry) => entry.isFile() && entry.name.endsWith(".md")).map((entry) => path.join(projectActivityDir, entry.name));
  return files.sort((left, right) => parseProjectDateValue(right) - parseProjectDateValue(left));
}

export {
  listProjects,
  readProject,
  createProject,
  updateProject,
  archiveProject,
  getProjectTasks,
  getProjectActivity
};
