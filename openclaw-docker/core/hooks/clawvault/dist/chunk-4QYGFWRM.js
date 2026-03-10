import {
  QmdUnavailableError,
  hasQmd,
  qmdEmbed
} from "./chunk-MAKNAHAW.js";
import {
  resolveVaultPath
} from "./chunk-MXSSG3QU.js";

// src/lib/vault-qmd-config.ts
import * as fs from "fs";
import * as path from "path";
var CONFIG_FILE = ".clawvault.json";
function readTrimmedString(value) {
  if (typeof value !== "string") return void 0;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : void 0;
}
function loadVaultQmdConfig(vaultPath) {
  const resolvedVaultPath = path.resolve(vaultPath);
  const fallbackName = path.basename(resolvedVaultPath);
  const fallbackRoot = resolvedVaultPath;
  const configPath = path.join(resolvedVaultPath, CONFIG_FILE);
  if (!fs.existsSync(configPath)) {
    return {
      vaultPath: resolvedVaultPath,
      qmdCollection: fallbackName,
      qmdRoot: fallbackRoot
    };
  }
  try {
    const raw = JSON.parse(fs.readFileSync(configPath, "utf-8"));
    const configuredName = readTrimmedString(raw.name) ?? fallbackName;
    const qmdCollection = readTrimmedString(raw.qmdCollection) ?? configuredName;
    const rawRoot = readTrimmedString(raw.qmdRoot) ?? fallbackRoot;
    const qmdRoot = path.isAbsolute(rawRoot) ? path.resolve(rawRoot) : path.resolve(resolvedVaultPath, rawRoot);
    return {
      vaultPath: resolvedVaultPath,
      qmdCollection,
      qmdRoot
    };
  } catch {
    return {
      vaultPath: resolvedVaultPath,
      qmdCollection: fallbackName,
      qmdRoot: fallbackRoot
    };
  }
}

// src/commands/embed.ts
async function embedCommand(options = {}) {
  if (!hasQmd()) {
    throw new QmdUnavailableError();
  }
  const vaultPath = resolveVaultPath({ explicitPath: options.vaultPath });
  const qmdConfig = loadVaultQmdConfig(vaultPath);
  const startedAt = (/* @__PURE__ */ new Date()).toISOString();
  if (!options.quiet) {
    console.log(
      `Embedding pending documents for collection "${qmdConfig.qmdCollection}" (root: ${qmdConfig.qmdRoot})...`
    );
  }
  qmdEmbed(qmdConfig.qmdCollection);
  const finishedAt = (/* @__PURE__ */ new Date()).toISOString();
  if (!options.quiet) {
    console.log(`\u2713 Embedding complete for "${qmdConfig.qmdCollection}"`);
  }
  return {
    vaultPath,
    qmdCollection: qmdConfig.qmdCollection,
    qmdRoot: qmdConfig.qmdRoot,
    startedAt,
    finishedAt
  };
}
function registerEmbedCommand(program) {
  program.command("embed").description("Run qmd embedding for pending vault documents").option("-v, --vault <path>", "Vault path").action(async (rawOptions) => {
    await embedCommand({
      vaultPath: rawOptions.vault
    });
  });
}

export {
  embedCommand,
  registerEmbedCommand
};
