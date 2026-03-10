// src/lib/config.ts
import * as fs from "fs";
import * as path from "path";
function getVaultPath() {
  const vaultPath = process.env.CLAWVAULT_PATH;
  if (!vaultPath) {
    throw new Error("CLAWVAULT_PATH environment variable not set");
  }
  return path.resolve(vaultPath);
}
function findNearestVaultPath(startPath = process.cwd()) {
  let current = path.resolve(startPath);
  while (true) {
    if (fs.existsSync(path.join(current, ".clawvault.json"))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      return null;
    }
    current = parent;
  }
}
function resolveVaultPath(options = {}) {
  if (options.explicitPath) {
    return path.resolve(options.explicitPath);
  }
  if (process.env.CLAWVAULT_PATH) {
    return path.resolve(process.env.CLAWVAULT_PATH);
  }
  const discovered = findNearestVaultPath(options.cwd ?? process.cwd());
  if (discovered) {
    return discovered;
  }
  throw new Error("No vault path found. Set CLAWVAULT_PATH, use --vault, or run inside a vault.");
}

export {
  getVaultPath,
  findNearestVaultPath,
  resolveVaultPath
};
