import {
  DEFAULT_CATEGORIES
} from "./chunk-2CDEETQN.js";

// src/lib/config-manager.ts
import * as fs from "fs";
import * as path from "path";
var CONFIG_FILE = ".clawvault.json";
var OBSERVE_PROVIDERS = ["anthropic", "openai", "gemini"];
var OBSERVER_COMPRESSION_PROVIDERS = [
  "anthropic",
  "openai",
  "gemini",
  "openai-compatible",
  "ollama"
];
var THEMES = ["neural", "minimal", "none"];
var CONTEXT_PROFILES = ["default", "planning", "incident", "handoff", "auto"];
var SUPPORTED_CONFIG_KEYS = [
  "name",
  "categories",
  "theme",
  "observe.model",
  "observe.provider",
  "observer.compression.provider",
  "observer.compression.model",
  "observer.compression.baseUrl",
  "observer.compression.apiKey",
  "context.maxResults",
  "context.defaultProfile",
  "graph.maxHops",
  "inject.maxResults",
  "inject.useLlm",
  "inject.scope"
];
var DEFAULT_THEME = "none";
var DEFAULT_OBSERVE_MODEL = "gemini-2.0-flash";
var DEFAULT_OBSERVE_PROVIDER = "gemini";
var DEFAULT_CONTEXT_MAX_RESULTS = 5;
var DEFAULT_CONTEXT_PROFILE = "default";
var DEFAULT_GRAPH_MAX_HOPS = 2;
var DEFAULT_INJECT_MAX_RESULTS = 8;
var DEFAULT_INJECT_USE_LLM = true;
var DEFAULT_INJECT_SCOPE = ["global"];
function configPathFor(vaultPath) {
  return path.join(path.resolve(vaultPath), CONFIG_FILE);
}
function readConfigDocument(vaultPath) {
  const configPath = configPathFor(vaultPath);
  if (!fs.existsSync(configPath)) {
    throw new Error(`No ClawVault config found at ${configPath}`);
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(configPath, "utf-8"));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Config root must be a JSON object.");
    }
    return { ...parsed };
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`Failed to parse ${CONFIG_FILE}: ${error.message}`);
    }
    throw new Error(`Failed to parse ${CONFIG_FILE}.`);
  }
}
function writeConfigDocument(vaultPath, config) {
  const configPath = configPathFor(vaultPath);
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
}
function asStringArray(value) {
  if (!Array.isArray(value)) {
    return null;
  }
  const output = value.map((entry) => typeof entry === "string" ? entry.trim() : "").filter(Boolean);
  return output.length > 0 ? output : null;
}
function asPositiveInteger(value) {
  if (typeof value === "number" && Number.isInteger(value) && value > 0) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseInt(value, 10);
    if (Number.isInteger(parsed) && parsed > 0) {
      return parsed;
    }
  }
  return null;
}
function asBoolean(value) {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["true", "1", "yes", "on"].includes(normalized)) {
      return true;
    }
    if (["false", "0", "no", "off"].includes(normalized)) {
      return false;
    }
  }
  return null;
}
function isObserveProvider(value) {
  return typeof value === "string" && OBSERVE_PROVIDERS.includes(value);
}
function isObserverCompressionProvider(value) {
  return typeof value === "string" && OBSERVER_COMPRESSION_PROVIDERS.includes(value);
}
function isTheme(value) {
  return typeof value === "string" && THEMES.includes(value);
}
function isContextProfile(value) {
  return typeof value === "string" && CONTEXT_PROFILES.includes(value);
}
function normalizeRouteTarget(target) {
  const trimmed = target.trim().replace(/^\/+/, "").replace(/\/+$/, "");
  if (!trimmed) {
    throw new Error("Route target cannot be empty.");
  }
  const segments = trimmed.split("/").map((segment) => segment.trim()).filter(Boolean);
  if (segments.length === 0) {
    throw new Error("Route target cannot be empty.");
  }
  if (segments.some((segment) => segment === "." || segment === "..")) {
    throw new Error(`Route target cannot contain relative path segments: ${target}`);
  }
  return segments.join("/");
}
function normalizeRouteRule(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return null;
  }
  const record = raw;
  const pattern = typeof record.pattern === "string" ? record.pattern.trim() : "";
  const target = typeof record.target === "string" ? record.target.trim() : "";
  const priority = asPositiveInteger(record.priority);
  if (!pattern || !target || priority === null) {
    return null;
  }
  return {
    pattern,
    target: normalizeRouteTarget(target),
    priority
  };
}
function normalizeRoutes(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((entry) => normalizeRouteRule(entry)).filter((entry) => entry !== null).sort((left, right) => right.priority - left.priority || left.pattern.localeCompare(right.pattern));
}
function getNestedValue(source, dottedPath) {
  const parts = dottedPath.split(".");
  let cursor = source;
  for (const part of parts) {
    if (!cursor || typeof cursor !== "object" || Array.isArray(cursor)) {
      return void 0;
    }
    cursor = cursor[part];
  }
  return cursor;
}
function setNestedValue(source, dottedPath, value) {
  const parts = dottedPath.split(".");
  let cursor = source;
  for (let index = 0; index < parts.length - 1; index += 1) {
    const part = parts[index];
    const current = cursor[part];
    if (!current || typeof current !== "object" || Array.isArray(current)) {
      cursor[part] = {};
    }
    cursor = cursor[part];
  }
  cursor[parts[parts.length - 1]] = value;
}
function parseRegexLiteral(pattern) {
  const match = pattern.match(/^\/(.+)\/([a-z]*)$/i);
  if (!match) {
    return null;
  }
  try {
    return new RegExp(match[1], match[2]);
  } catch (error) {
    throw new Error(`Invalid route regex pattern "${pattern}": ${error instanceof Error ? error.message : "parse error"}`);
  }
}
function withDefaults(vaultPath, config) {
  const resolvedPath = path.resolve(vaultPath);
  const defaults = {
    name: path.basename(resolvedPath),
    categories: [...DEFAULT_CATEGORIES],
    theme: DEFAULT_THEME,
    observe: {
      model: DEFAULT_OBSERVE_MODEL,
      provider: DEFAULT_OBSERVE_PROVIDER
    },
    observer: {
      compression: {}
    },
    context: {
      maxResults: DEFAULT_CONTEXT_MAX_RESULTS,
      defaultProfile: DEFAULT_CONTEXT_PROFILE
    },
    graph: {
      maxHops: DEFAULT_GRAPH_MAX_HOPS
    },
    inject: {
      maxResults: DEFAULT_INJECT_MAX_RESULTS,
      useLlm: DEFAULT_INJECT_USE_LLM,
      scope: [...DEFAULT_INJECT_SCOPE]
    },
    routes: []
  };
  const observeRecord = config.observe && typeof config.observe === "object" && !Array.isArray(config.observe) ? config.observe : {};
  const contextRecord = config.context && typeof config.context === "object" && !Array.isArray(config.context) ? config.context : {};
  const observerRecord = config.observer && typeof config.observer === "object" && !Array.isArray(config.observer) ? config.observer : {};
  const compressionRecord = observerRecord.compression && typeof observerRecord.compression === "object" && !Array.isArray(observerRecord.compression) ? observerRecord.compression : {};
  const graphRecord = config.graph && typeof config.graph === "object" && !Array.isArray(config.graph) ? config.graph : {};
  const compressionProvider = isObserverCompressionProvider(compressionRecord.provider) ? compressionRecord.provider : void 0;
  const compressionModel = typeof compressionRecord.model === "string" && compressionRecord.model.trim() ? compressionRecord.model.trim() : void 0;
  const compressionBaseUrl = typeof compressionRecord.baseUrl === "string" && compressionRecord.baseUrl.trim() ? compressionRecord.baseUrl.trim() : void 0;
  const compressionApiKey = typeof compressionRecord.apiKey === "string" && compressionRecord.apiKey.trim() ? compressionRecord.apiKey.trim() : void 0;
  const normalizedCompression = {};
  if (compressionProvider) {
    normalizedCompression.provider = compressionProvider;
  }
  if (compressionModel) {
    normalizedCompression.model = compressionModel;
  }
  if (compressionBaseUrl) {
    normalizedCompression.baseUrl = compressionBaseUrl;
  }
  if (compressionApiKey) {
    normalizedCompression.apiKey = compressionApiKey;
  }
  const injectRecord = config.inject && typeof config.inject === "object" && !Array.isArray(config.inject) ? config.inject : {};
  return {
    ...config,
    name: typeof config.name === "string" && config.name.trim() ? config.name.trim() : defaults.name,
    categories: asStringArray(config.categories) ?? defaults.categories,
    theme: isTheme(config.theme) ? config.theme : defaults.theme,
    observe: {
      ...observeRecord,
      model: typeof observeRecord.model === "string" && observeRecord.model.trim() ? observeRecord.model.trim() : defaults.observe.model,
      provider: isObserveProvider(observeRecord.provider) ? observeRecord.provider : defaults.observe.provider
    },
    observer: {
      ...observerRecord,
      compression: normalizedCompression
    },
    context: {
      ...contextRecord,
      maxResults: asPositiveInteger(contextRecord.maxResults) ?? defaults.context.maxResults,
      defaultProfile: isContextProfile(contextRecord.defaultProfile) ? contextRecord.defaultProfile : defaults.context.defaultProfile
    },
    graph: {
      ...graphRecord,
      maxHops: asPositiveInteger(graphRecord.maxHops) ?? defaults.graph.maxHops
    },
    inject: {
      ...injectRecord,
      maxResults: asPositiveInteger(injectRecord.maxResults) ?? defaults.inject.maxResults,
      useLlm: asBoolean(injectRecord.useLlm) ?? defaults.inject.useLlm,
      scope: asStringArray(injectRecord.scope) ?? (typeof injectRecord.scope === "string" ? injectRecord.scope.split(",").map((entry) => entry.trim()).filter(Boolean) : null) ?? [...defaults.inject.scope]
    },
    routes: normalizeRoutes(config.routes)
  };
}
function coerceManagedValue(key, value) {
  if (key === "name") {
    if (typeof value !== "string" || !value.trim()) {
      throw new Error('Config key "name" must be a non-empty string.');
    }
    return value.trim();
  }
  if (key === "categories") {
    if (Array.isArray(value)) {
      const normalized = value.map((entry) => typeof entry === "string" ? entry.trim() : "").filter(Boolean);
      if (normalized.length === 0) {
        throw new Error('Config key "categories" must include at least one category.');
      }
      return normalized;
    }
    if (typeof value !== "string") {
      throw new Error('Config key "categories" must be a comma-separated string.');
    }
    const categories = value.split(",").map((entry) => entry.trim()).filter(Boolean);
    if (categories.length === 0) {
      throw new Error('Config key "categories" must include at least one category.');
    }
    return categories;
  }
  if (key === "theme") {
    if (!isTheme(value)) {
      throw new Error(`Config key "theme" must be one of: ${THEMES.join(", ")}`);
    }
    return value;
  }
  if (key === "observe.provider") {
    if (!isObserveProvider(value)) {
      throw new Error(`Config key "observe.provider" must be one of: ${OBSERVE_PROVIDERS.join(", ")}`);
    }
    return value;
  }
  if (key === "observe.model") {
    if (typeof value !== "string" || !value.trim()) {
      throw new Error('Config key "observe.model" must be a non-empty string.');
    }
    return value.trim();
  }
  if (key === "observer.compression.provider") {
    if (!isObserverCompressionProvider(value)) {
      throw new Error(
        `Config key "observer.compression.provider" must be one of: ${OBSERVER_COMPRESSION_PROVIDERS.join(", ")}`
      );
    }
    return value;
  }
  if (key === "observer.compression.model") {
    if (typeof value !== "string" || !value.trim()) {
      throw new Error('Config key "observer.compression.model" must be a non-empty string.');
    }
    return value.trim();
  }
  if (key === "observer.compression.baseUrl") {
    if (typeof value !== "string" || !value.trim()) {
      throw new Error('Config key "observer.compression.baseUrl" must be a non-empty string.');
    }
    return value.trim();
  }
  if (key === "observer.compression.apiKey") {
    if (typeof value !== "string") {
      throw new Error('Config key "observer.compression.apiKey" must be a string.');
    }
    return value.trim();
  }
  if (key === "context.maxResults") {
    const parsed = asPositiveInteger(value);
    if (parsed === null) {
      throw new Error('Config key "context.maxResults" must be a positive integer.');
    }
    return parsed;
  }
  if (key === "context.defaultProfile") {
    if (!isContextProfile(value)) {
      throw new Error(`Config key "context.defaultProfile" must be one of: ${CONTEXT_PROFILES.join(", ")}`);
    }
    return value;
  }
  if (key === "graph.maxHops") {
    const parsed = asPositiveInteger(value);
    if (parsed === null) {
      throw new Error('Config key "graph.maxHops" must be a positive integer.');
    }
    return parsed;
  }
  if (key === "inject.maxResults") {
    const parsed = asPositiveInteger(value);
    if (parsed === null) {
      throw new Error('Config key "inject.maxResults" must be a positive integer.');
    }
    return parsed;
  }
  if (key === "inject.useLlm") {
    const parsed = asBoolean(value);
    if (parsed === null) {
      throw new Error('Config key "inject.useLlm" must be a boolean.');
    }
    return parsed;
  }
  if (key === "inject.scope") {
    const normalized = Array.isArray(value) ? value.map((entry) => typeof entry === "string" ? entry.trim() : "").filter(Boolean) : typeof value === "string" ? value.split(",").map((entry) => entry.trim()).filter(Boolean) : [];
    if (normalized.length === 0) {
      throw new Error('Config key "inject.scope" must be a non-empty string list.');
    }
    return normalized;
  }
  throw new Error(`Unsupported config key: ${key}`);
}
function toComparablePattern(pattern) {
  return pattern.trim().toLowerCase();
}
function listConfig(vaultPath) {
  const config = readConfigDocument(vaultPath);
  return withDefaults(vaultPath, config);
}
function getConfig(vaultPath) {
  return listConfig(vaultPath);
}
function getConfigValue(vaultPath, key) {
  if (!SUPPORTED_CONFIG_KEYS.includes(key)) {
    throw new Error(`Unsupported config key: ${key}`);
  }
  const config = listConfig(vaultPath);
  return getNestedValue(config, key);
}
function setConfigValue(vaultPath, key, value) {
  if (!SUPPORTED_CONFIG_KEYS.includes(key)) {
    throw new Error(`Unsupported config key: ${key}`);
  }
  const document = readConfigDocument(vaultPath);
  const coerced = coerceManagedValue(key, value);
  setNestedValue(document, key, coerced);
  if (typeof document.lastUpdated === "string") {
    document.lastUpdated = (/* @__PURE__ */ new Date()).toISOString();
  }
  writeConfigDocument(vaultPath, document);
  return {
    value: coerced,
    config: withDefaults(vaultPath, document)
  };
}
function resetConfig(vaultPath) {
  const document = readConfigDocument(vaultPath);
  const defaultName = path.basename(path.resolve(vaultPath));
  document.name = defaultName;
  document.categories = [...DEFAULT_CATEGORIES];
  document.theme = DEFAULT_THEME;
  document.observe = {
    model: DEFAULT_OBSERVE_MODEL,
    provider: DEFAULT_OBSERVE_PROVIDER
  };
  const observerRecord = document.observer && typeof document.observer === "object" && !Array.isArray(document.observer) ? document.observer : {};
  document.observer = {
    ...observerRecord,
    compression: {}
  };
  document.context = {
    maxResults: DEFAULT_CONTEXT_MAX_RESULTS,
    defaultProfile: DEFAULT_CONTEXT_PROFILE
  };
  document.graph = {
    maxHops: DEFAULT_GRAPH_MAX_HOPS
  };
  document.inject = {
    maxResults: DEFAULT_INJECT_MAX_RESULTS,
    useLlm: DEFAULT_INJECT_USE_LLM,
    scope: [...DEFAULT_INJECT_SCOPE]
  };
  document.routes = [];
  if (typeof document.lastUpdated === "string") {
    document.lastUpdated = (/* @__PURE__ */ new Date()).toISOString();
  }
  writeConfigDocument(vaultPath, document);
  return withDefaults(vaultPath, document);
}
function listRouteRules(vaultPath) {
  const config = listConfig(vaultPath);
  return normalizeRoutes(config.routes);
}
function addRouteRule(vaultPath, pattern, target) {
  const normalizedPattern = pattern.trim();
  if (!normalizedPattern) {
    throw new Error("Route pattern cannot be empty.");
  }
  const normalizedTarget = normalizeRouteTarget(target);
  const document = readConfigDocument(vaultPath);
  const existingRoutes = normalizeRoutes(document.routes);
  const duplicate = existingRoutes.find(
    (rule) => toComparablePattern(rule.pattern) === toComparablePattern(normalizedPattern)
  );
  if (duplicate) {
    throw new Error(`Route pattern already exists: ${pattern}`);
  }
  const maxPriority = existingRoutes.reduce((max, rule) => Math.max(max, rule.priority), 0);
  const nextRule = {
    pattern: normalizedPattern,
    target: normalizedTarget,
    priority: maxPriority + 1
  };
  document.routes = [...existingRoutes, nextRule];
  if (typeof document.lastUpdated === "string") {
    document.lastUpdated = (/* @__PURE__ */ new Date()).toISOString();
  }
  writeConfigDocument(vaultPath, document);
  return nextRule;
}
function removeRouteRule(vaultPath, pattern) {
  const normalizedPattern = toComparablePattern(pattern);
  const document = readConfigDocument(vaultPath);
  const existingRoutes = normalizeRoutes(document.routes);
  const nextRoutes = existingRoutes.filter(
    (rule) => toComparablePattern(rule.pattern) !== normalizedPattern
  );
  if (nextRoutes.length === existingRoutes.length) {
    return false;
  }
  document.routes = nextRoutes;
  if (typeof document.lastUpdated === "string") {
    document.lastUpdated = (/* @__PURE__ */ new Date()).toISOString();
  }
  writeConfigDocument(vaultPath, document);
  return true;
}
function matchRouteRule(text, routes) {
  for (const route of routes) {
    const regex = parseRegexLiteral(route.pattern);
    if (regex) {
      if (regex.test(text)) {
        return route;
      }
      continue;
    }
    if (text.toLowerCase().includes(route.pattern.toLowerCase())) {
      return route;
    }
  }
  return null;
}
function testRouteRule(vaultPath, text) {
  const routes = listRouteRules(vaultPath);
  return matchRouteRule(text, routes);
}

export {
  SUPPORTED_CONFIG_KEYS,
  listConfig,
  getConfig,
  getConfigValue,
  setConfigValue,
  resetConfig,
  listRouteRules,
  addRouteRule,
  removeRouteRule,
  matchRouteRule,
  testRouteRule
};
