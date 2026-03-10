import {
  DATE_HEADING_RE,
  parseObservationLine,
  renderScoredObservationLine
} from "./chunk-FHFUXL6G.js";
import {
  resolveVaultPath
} from "./chunk-MXSSG3QU.js";
import {
  listObservationFiles
} from "./chunk-Z2XBWN7A.js";

// src/commands/migrate-observations.ts
import * as fs from "fs";
function toBackupPath(filePath) {
  if (filePath.toLowerCase().endsWith(".md")) {
    return `${filePath.slice(0, -3)}.emoji-backup.md`;
  }
  return `${filePath}.emoji-backup`;
}
function convertObservationMarkdown(markdown) {
  const lines = markdown.split(/\r?\n/);
  let currentDate = "";
  let changed = false;
  const nextLines = lines.map((line) => {
    const heading = line.match(DATE_HEADING_RE);
    if (heading) {
      currentDate = heading[1];
      return line;
    }
    if (!currentDate) {
      return line;
    }
    const parsed = parseObservationLine(line.trim(), currentDate);
    if (!parsed || parsed.format !== "emoji") {
      return line;
    }
    changed = true;
    return renderScoredObservationLine({
      type: parsed.type,
      confidence: parsed.confidence,
      importance: parsed.importance,
      content: parsed.content
    });
  });
  return {
    converted: nextLines.join("\n"),
    changed
  };
}
function migrateObservations(vaultPath, options = {}) {
  const dryRun = options.dryRun ?? false;
  const files = listObservationFiles(vaultPath, {
    includeLegacy: true,
    includeArchive: false,
    dedupeByDate: false
  });
  let migrated = 0;
  let backups = 0;
  for (const entry of files) {
    const raw = fs.readFileSync(entry.path, "utf-8");
    const { converted, changed } = convertObservationMarkdown(raw);
    if (!changed) {
      continue;
    }
    migrated += 1;
    if (dryRun) {
      continue;
    }
    const backupPath = toBackupPath(entry.path);
    if (!fs.existsSync(backupPath)) {
      fs.copyFileSync(entry.path, backupPath);
      backups += 1;
    }
    fs.writeFileSync(entry.path, `${converted.trim()}
`, "utf-8");
  }
  return {
    scanned: files.length,
    migrated,
    backups,
    dryRun
  };
}
async function migrateObservationsCommand(options) {
  const vaultPath = resolveVaultPath({ explicitPath: options.vaultPath });
  const result = migrateObservations(vaultPath, { dryRun: options.dryRun });
  if (result.migrated === 0) {
    console.log("No emoji observations found for migration.");
    return;
  }
  if (result.dryRun) {
    console.log(`Dry run: ${result.migrated} file(s) would be migrated.`);
    return;
  }
  console.log(`Migrated ${result.migrated} file(s); created ${result.backups} backup(s).`);
}
function registerMigrateObservationsCommand(program) {
  program.command("migrate-observations").description("Convert legacy emoji observations to scored format with backups").option("--dry-run", "Preview migration without writing files").option("-v, --vault <path>", "Vault path").action(async (rawOptions) => {
    await migrateObservationsCommand({
      vaultPath: rawOptions.vault,
      dryRun: rawOptions.dryRun
    });
  });
}

export {
  migrateObservations,
  migrateObservationsCommand,
  registerMigrateObservationsCommand
};
