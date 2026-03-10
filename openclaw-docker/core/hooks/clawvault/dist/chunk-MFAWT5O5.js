import {
  buildTemplateVariables,
  renderTemplate
} from "./chunk-7766SIJP.js";

// src/lib/primitive-templates.ts
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";
import matter from "gray-matter";
var TEMPLATE_EXTENSION = ".md";
function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function normalizeTemplateName(name) {
  const base = path.basename(name, path.extname(name));
  return base.trim();
}
function resolveBuiltinTemplatesDir(override) {
  if (override) {
    const resolved = path.resolve(override);
    return fs.existsSync(resolved) && fs.statSync(resolved).isDirectory() ? resolved : null;
  }
  const moduleDir = path.dirname(fileURLToPath(import.meta.url));
  const candidates = [
    path.resolve(moduleDir, "../templates"),
    path.resolve(moduleDir, "../../templates")
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
      return candidate;
    }
  }
  return null;
}
function listTemplateFiles(dir, ignore) {
  const entries = /* @__PURE__ */ new Map();
  if (!fs.existsSync(dir)) return entries;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith(TEMPLATE_EXTENSION)) continue;
    const name = normalizeTemplateName(entry.name);
    if (!name) continue;
    if (ignore?.has(name)) continue;
    entries.set(name, path.join(dir, entry.name));
  }
  return entries;
}
function buildTemplateIndex(options = {}) {
  const index = /* @__PURE__ */ new Map();
  const builtinDir = resolveBuiltinTemplatesDir(options.builtinDir);
  if (builtinDir) {
    for (const [name, filePath] of listTemplateFiles(builtinDir, options.ignoreBuiltinNames)) {
      index.set(name, filePath);
    }
  }
  if (options.vaultPath) {
    const vaultTemplatesDir = path.join(path.resolve(options.vaultPath), "templates");
    for (const [name, filePath] of listTemplateFiles(vaultTemplatesDir)) {
      index.set(name, filePath);
    }
  }
  return index;
}
function inferFieldType(defaultValue) {
  if (Array.isArray(defaultValue)) {
    const uniqueItemTypes = [...new Set(defaultValue.map((value) => typeof value))];
    if (uniqueItemTypes.length === 1 && uniqueItemTypes[0] === "string") {
      return "string[]";
    }
    return "array";
  }
  switch (typeof defaultValue) {
    case "string":
      return "string";
    case "number":
      return "number";
    case "boolean":
      return "boolean";
    case "object":
      if (defaultValue === null) return "string";
      return "object";
    default:
      return "string";
  }
}
function normalizeFieldDefinition(rawField) {
  if (!isRecord(rawField)) {
    return {
      type: inferFieldType(rawField),
      default: rawField
    };
  }
  const rawType = typeof rawField.type === "string" ? rawField.type.trim() : "";
  const normalized = {
    type: rawType || inferFieldType(rawField.default)
  };
  if (typeof rawField.description === "string" && rawField.description.trim()) {
    normalized.description = rawField.description.trim();
  }
  if (typeof rawField.required === "boolean") {
    normalized.required = rawField.required;
  }
  if (Object.prototype.hasOwnProperty.call(rawField, "default")) {
    normalized.default = rawField.default;
  }
  if (Array.isArray(rawField.enum)) {
    normalized.enum = rawField.enum;
  }
  return normalized;
}
function normalizeFieldDefinitions(rawFields) {
  const normalized = {};
  for (const [fieldName, rawField] of Object.entries(rawFields)) {
    const normalizedName = String(fieldName).trim();
    if (!normalizedName) continue;
    normalized[normalizedName] = normalizeFieldDefinition(rawField);
  }
  return normalized;
}
function extractSchemaDefinition(frontmatter) {
  const primitive = typeof frontmatter.primitive === "string" ? frontmatter.primitive.trim() : "";
  const description = typeof frontmatter.description === "string" ? frontmatter.description.trim() : void 0;
  if (primitive && isRecord(frontmatter.fields)) {
    return {
      primitive,
      description,
      fields: frontmatter.fields
    };
  }
  const containerCandidates = [frontmatter.schema, frontmatter.template];
  for (const candidate of containerCandidates) {
    if (!isRecord(candidate)) continue;
    const nestedPrimitive = typeof candidate.primitive === "string" ? candidate.primitive.trim() : primitive;
    if (!nestedPrimitive || !isRecord(candidate.fields)) continue;
    const nestedDescription = typeof candidate.description === "string" ? candidate.description.trim() : description;
    return {
      primitive: nestedPrimitive,
      description: nestedDescription,
      fields: candidate.fields
    };
  }
  return null;
}
function inferLegacyFieldDefinitions(frontmatter) {
  const normalized = {};
  const ignoredKeys = /* @__PURE__ */ new Set(["primitive", "fields", "schema", "template"]);
  for (const [key, value] of Object.entries(frontmatter)) {
    if (ignoredKeys.has(key)) continue;
    normalized[key] = {
      type: inferFieldType(value),
      default: value
    };
  }
  return normalized;
}
function parseTemplateDefinition(rawTemplate, templateName, sourcePath) {
  const normalizedName = normalizeTemplateName(templateName);
  const { data, content } = matter(rawTemplate);
  const frontmatter = isRecord(data) ? data : {};
  const extractedSchema = extractSchemaDefinition(frontmatter);
  if (extractedSchema) {
    return {
      name: normalizedName,
      primitive: extractedSchema.primitive,
      description: extractedSchema.description,
      fields: normalizeFieldDefinitions(extractedSchema.fields),
      body: content,
      format: "schema",
      sourcePath
    };
  }
  return {
    name: normalizedName,
    primitive: normalizedName,
    description: typeof frontmatter.description === "string" ? frontmatter.description.trim() : void 0,
    fields: inferLegacyFieldDefinitions(frontmatter),
    body: content,
    format: "legacy",
    sourcePath
  };
}
function readTemplateDefinitionFromPath(filePath, templateName) {
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    return parseTemplateDefinition(raw, templateName, filePath);
  } catch {
    return null;
  }
}
function loadTemplateDefinition(templateName, options = {}) {
  const normalizedName = normalizeTemplateName(templateName);
  if (!normalizedName) return null;
  const index = buildTemplateIndex(options);
  const filePath = index.get(normalizedName);
  if (!filePath) return null;
  return readTemplateDefinitionFromPath(filePath, normalizedName);
}
function loadSchemaTemplateDefinition(templateName, options = {}) {
  const definition = loadTemplateDefinition(templateName, options);
  if (!definition || definition.format !== "schema") {
    return null;
  }
  return definition;
}
function listTemplateDefinitions(options = {}) {
  const index = buildTemplateIndex(options);
  const entries = [];
  for (const [name, filePath] of [...index.entries()].sort(([left], [right]) => left.localeCompare(right))) {
    const definition = readTemplateDefinitionFromPath(filePath, name);
    if (!definition) continue;
    entries.push({
      ...definition,
      path: filePath
    });
  }
  return entries;
}
function resolveInterpolatedValue(value, variables) {
  if (typeof value === "string") {
    return renderTemplate(value, variables);
  }
  if (Array.isArray(value)) {
    return value.map((item) => resolveInterpolatedValue(item, variables));
  }
  if (isRecord(value)) {
    const resolved = {};
    for (const [key, nested] of Object.entries(value)) {
      resolved[key] = resolveInterpolatedValue(nested, variables);
    }
    return resolved;
  }
  return value;
}
function pruneFrontmatter(frontmatter, options) {
  const dropEmptyStrings = options.dropEmptyStrings ?? true;
  const dropEmptyArrays = options.dropEmptyArrays ?? true;
  const pruned = {};
  for (const [key, value] of Object.entries(frontmatter)) {
    if (value === void 0 || value === null) continue;
    if (dropEmptyStrings && typeof value === "string" && value.trim() === "") continue;
    if (dropEmptyArrays && Array.isArray(value) && value.length === 0) continue;
    pruned[key] = value;
  }
  return pruned;
}
function buildFrontmatterFromTemplate(definition, variables, overrides = {}, options = {}) {
  const frontmatter = {};
  for (const [fieldName, schema] of Object.entries(definition.fields)) {
    if (!Object.prototype.hasOwnProperty.call(schema, "default")) continue;
    frontmatter[fieldName] = resolveInterpolatedValue(schema.default, variables);
  }
  for (const [fieldName, value] of Object.entries(overrides)) {
    if (value === void 0) continue;
    if (value === null) {
      delete frontmatter[fieldName];
      continue;
    }
    frontmatter[fieldName] = value;
  }
  if (!options.pruneEmpty) {
    return frontmatter;
  }
  return pruneFrontmatter(frontmatter, options);
}
function renderDocumentFromTemplate(definition, options = {}) {
  const now = options.now ?? /* @__PURE__ */ new Date();
  const variables = {
    ...buildTemplateVariables(
      {
        title: options.title ?? "",
        type: options.type ?? definition.primitive
      },
      now
    ),
    ...options.variables ?? {}
  };
  const frontmatter = buildFrontmatterFromTemplate(
    definition,
    variables,
    options.overrides,
    options.frontmatter
  );
  const content = renderTemplate(definition.body, variables);
  const markdown = matter.stringify(content, frontmatter);
  return {
    frontmatter,
    content,
    markdown,
    variables
  };
}

export {
  TEMPLATE_EXTENSION,
  normalizeTemplateName,
  buildTemplateIndex,
  parseTemplateDefinition,
  loadSchemaTemplateDefinition,
  listTemplateDefinitions,
  renderDocumentFromTemplate
};
