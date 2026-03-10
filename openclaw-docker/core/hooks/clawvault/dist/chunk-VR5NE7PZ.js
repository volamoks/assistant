import {
  archiveObservations
} from "./chunk-MQUJNOHK.js";
import {
  resolveVaultPath
} from "./chunk-MXSSG3QU.js";

// src/commands/archive.ts
function parsePositiveInteger(raw, label) {
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`Invalid ${label}: ${raw}`);
  }
  return parsed;
}
async function archiveCommand(options) {
  const vaultPath = resolveVaultPath({ explicitPath: options.vaultPath });
  const result = archiveObservations(vaultPath, {
    olderThanDays: options.olderThan,
    dryRun: options.dryRun
  });
  if (result.archived === 0) {
    console.log("No observations matched archive criteria.");
    return;
  }
  if (result.dryRun) {
    console.log(`Dry run: ${result.archived} observation file(s) would be archived.`);
    return;
  }
  console.log(`Archived ${result.archived} observation file(s).`);
}
function registerArchiveCommand(program) {
  program.command("archive").description("Archive old observations into ledger/archive").option("--older-than <days>", "Archive observations older than this many days", "14").option("--dry-run", "Show archive candidates without moving files").option("-v, --vault <path>", "Vault path").action(async (rawOptions) => {
    await archiveCommand({
      vaultPath: rawOptions.vault,
      olderThan: parsePositiveInteger(rawOptions.olderThan, "older-than"),
      dryRun: rawOptions.dryRun
    });
  });
}

export {
  archiveCommand,
  registerArchiveCommand
};
