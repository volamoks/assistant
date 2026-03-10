import {
  runReflection
} from "./chunk-T76H47ZS.js";
import {
  resolveVaultPath
} from "./chunk-MXSSG3QU.js";

// src/commands/reflect.ts
function parsePositiveInteger(raw, label) {
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`Invalid ${label}: ${raw}`);
  }
  return parsed;
}
async function reflectCommand(options) {
  const vaultPath = resolveVaultPath({ explicitPath: options.vaultPath });
  const result = await runReflection({
    vaultPath,
    days: options.days,
    dryRun: options.dryRun
  });
  if (result.writtenWeeks === 0) {
    console.log("No new reflections promoted.");
    return;
  }
  if (result.dryRun) {
    console.log(`Dry run: ${result.writtenWeeks} reflection file(s) would be written.`);
    return;
  }
  console.log(`Reflection complete: ${result.writtenWeeks} week file(s) updated.`);
  if (result.archive) {
    console.log(`Archive pass: ${result.archive.archived} observation file(s) archived.`);
  }
}
function registerReflectCommand(program) {
  program.command("reflect").description("Promote stable observation patterns into weekly reflections").option("--days <n>", "Observation window in days (default 14)", "14").option("--dry-run", "Show what would be reflected without writing").option("-v, --vault <path>", "Vault path").action(async (rawOptions) => {
    await reflectCommand({
      vaultPath: rawOptions.vault,
      days: parsePositiveInteger(rawOptions.days, "days"),
      dryRun: rawOptions.dryRun
    });
  });
}

export {
  reflectCommand,
  registerReflectCommand
};
