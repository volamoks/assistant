import {
  TEMPLATE_EXTENSION,
  buildTemplateIndex,
  listTemplateDefinitions,
  normalizeTemplateName,
  parseTemplateDefinition,
  renderDocumentFromTemplate
} from "../chunk-MFAWT5O5.js";
import {
  buildTemplateVariables,
  renderTemplate
} from "../chunk-7766SIJP.js";

// src/commands/template.ts
import * as fs from "fs";
import * as path from "path";
var VAULT_CONFIG_FILE = ".clawvault.json";
var TEMPLATE_LIST_IGNORED_BUILTINS = /* @__PURE__ */ new Set(["daily"]);
function findVaultRoot(start) {
  let current = path.resolve(start);
  while (true) {
    if (fs.existsSync(path.join(current, VAULT_CONFIG_FILE))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}
function resolveVaultPath(options) {
  if (options.vaultPath) {
    return path.resolve(options.vaultPath);
  }
  const envPath = process.env.CLAWVAULT_PATH;
  if (envPath) {
    return path.resolve(envPath);
  }
  const cwd = options.cwd ?? process.cwd();
  return findVaultRoot(cwd);
}
function slugify(text) {
  return text.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-").trim();
}
function buildTemplateIndexForContext(options) {
  const vaultPath = resolveVaultPath(options) ?? void 0;
  return buildTemplateIndex({
    vaultPath,
    builtinDir: options.builtinDir,
    ignoreBuiltinNames: TEMPLATE_LIST_IGNORED_BUILTINS
  });
}
function listTemplateDefinitions2(options = {}) {
  const vaultPath = resolveVaultPath(options) ?? void 0;
  return listTemplateDefinitions({
    vaultPath,
    builtinDir: options.builtinDir,
    ignoreBuiltinNames: TEMPLATE_LIST_IGNORED_BUILTINS
  }).map((definition) => ({
    name: definition.name,
    primitive: definition.primitive,
    description: definition.description,
    fields: Object.keys(definition.fields),
    path: definition.path,
    format: definition.format
  }));
}
function listTemplates(options = {}) {
  return listTemplateDefinitions2(options).map((definition) => definition.name);
}
function createFromTemplate(name, options = {}) {
  const templateName = normalizeTemplateName(name);
  if (!templateName) {
    throw new Error("Template name is required.");
  }
  const index = buildTemplateIndexForContext(options);
  const templatePath = index.get(templateName);
  if (!templatePath) {
    const available = [...index.keys()].sort();
    const hint = available.length > 0 ? ` Available: ${available.join(", ")}` : "";
    throw new Error(`Template not found: ${templateName}.${hint}`);
  }
  const raw = fs.readFileSync(templatePath, "utf-8");
  const now = /* @__PURE__ */ new Date();
  const date = now.toISOString().split("T")[0];
  const type = options.type ?? templateName;
  const title = options.title ?? `${type} ${date}`.trim();
  const variables = buildTemplateVariables({ title, type, date }, now);
  const parsedTemplate = parseTemplateDefinition(raw, templateName, templatePath);
  const rendered = parsedTemplate.format === "schema" ? renderDocumentFromTemplate(parsedTemplate, {
    title,
    type,
    now,
    variables: {
      ...variables,
      content: "",
      links_line: "",
      owner_link: "",
      project_link: "",
      team_links_line: ""
    }
  }).markdown : renderTemplate(raw, variables);
  const cwd = options.cwd ?? process.cwd();
  const slug = slugify(title) || slugify(templateName) || `template-${date}`;
  const outputPath = path.join(cwd, `${slug}${TEMPLATE_EXTENSION}`);
  if (fs.existsSync(outputPath)) {
    throw new Error(`File already exists: ${outputPath}`);
  }
  fs.writeFileSync(outputPath, rendered);
  return { outputPath, templatePath, variables };
}
function addTemplate(file, options) {
  const name = normalizeTemplateName(options.name);
  if (!name) {
    throw new Error("Template name is required.");
  }
  const vaultPath = resolveVaultPath(options);
  if (!vaultPath) {
    throw new Error("No vault found. Set CLAWVAULT_PATH or use --vault.");
  }
  const cwd = options.cwd ?? process.cwd();
  const sourcePath = path.resolve(cwd, file);
  if (!fs.existsSync(sourcePath) || !fs.statSync(sourcePath).isFile()) {
    throw new Error(`Template file not found: ${sourcePath}`);
  }
  const templatesDir = path.join(vaultPath, "templates");
  fs.mkdirSync(templatesDir, { recursive: true });
  const targetPath = path.join(templatesDir, `${name}${TEMPLATE_EXTENSION}`);
  if (fs.existsSync(targetPath) && !options.overwrite) {
    throw new Error(`Template already exists: ${targetPath}`);
  }
  fs.copyFileSync(sourcePath, targetPath);
  return { templatePath: targetPath, name };
}
export {
  addTemplate,
  createFromTemplate,
  listTemplateDefinitions2 as listTemplateDefinitions,
  listTemplates
};
