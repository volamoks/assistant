import {
  runReflection
} from "./chunk-T76H47ZS.js";
import {
  Observer
} from "./chunk-Q2J5YTUF.js";
import {
  resolveVaultPath
} from "./chunk-MXSSG3QU.js";

// src/commands/replay.ts
import * as fs from "fs";
import * as path from "path";

// src/replay/normalizers/chatgpt.ts
function normalizeText(value) {
  if (typeof value === "string") {
    return value.replace(/\s+/g, " ").trim();
  }
  if (Array.isArray(value)) {
    return value.map((entry) => normalizeText(entry)).filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
  }
  if (!value || typeof value !== "object") {
    return "";
  }
  const record = value;
  if (Array.isArray(record.parts)) {
    return normalizeText(record.parts);
  }
  if (typeof record.text === "string") {
    return normalizeText(record.text);
  }
  if (typeof record.content === "string") {
    return normalizeText(record.content);
  }
  return "";
}
function asTimestamp(input) {
  if (typeof input === "number" && Number.isFinite(input) && input > 0) {
    const millis = input < 1e10 ? Math.floor(input * 1e3) : Math.floor(input);
    const parsed = new Date(millis);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toISOString();
    }
  }
  if (typeof input === "string" && input.trim()) {
    const parsed = new Date(input.trim());
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toISOString();
    }
  }
  return void 0;
}
function normalizeChatGptExport(input) {
  if (!Array.isArray(input)) {
    return [];
  }
  const messages = [];
  for (const conversation of input) {
    if (!conversation || typeof conversation !== "object") {
      continue;
    }
    const record = conversation;
    const conversationId = typeof record.id === "string" ? record.id : void 0;
    const mapping = record.mapping;
    if (!mapping || typeof mapping !== "object" || Array.isArray(mapping)) {
      continue;
    }
    const ordered = Object.values(mapping).filter((entry) => entry && typeof entry === "object").map((entry) => entry).sort((left, right) => {
      const leftTime = Number(left.message && typeof left.message === "object" ? left.message.create_time : 0);
      const rightTime = Number(right.message && typeof right.message === "object" ? right.message.create_time : 0);
      return leftTime - rightTime;
    });
    for (const node of ordered) {
      const message = node.message;
      if (!message || typeof message !== "object") {
        continue;
      }
      const messageRecord = message;
      const author = messageRecord.author;
      const role = author && typeof author === "object" ? String(author.role ?? "").trim().toLowerCase() : "";
      const text = normalizeText(messageRecord.content);
      if (!text) {
        continue;
      }
      messages.push({
        source: "chatgpt",
        conversationId,
        role: role || void 0,
        text,
        timestamp: asTimestamp(messageRecord.create_time)
      });
    }
  }
  return messages;
}

// src/replay/normalizers/claude.ts
function normalizeText2(value) {
  if (typeof value === "string") {
    return value.replace(/\s+/g, " ").trim();
  }
  if (Array.isArray(value)) {
    return value.map((entry) => normalizeText2(entry)).filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
  }
  if (!value || typeof value !== "object") {
    return "";
  }
  const record = value;
  if (typeof record.text === "string") return normalizeText2(record.text);
  if (typeof record.content === "string") return normalizeText2(record.content);
  return "";
}
function extractTimestamp(record) {
  const candidates = [record.timestamp, record.created_at, record.createdAt, record.time];
  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      const parsed = new Date(candidate);
      if (!Number.isNaN(parsed.getTime())) {
        return parsed.toISOString();
      }
    }
    if (typeof candidate === "number" && Number.isFinite(candidate) && candidate > 0) {
      const millis = candidate < 1e10 ? Math.floor(candidate * 1e3) : Math.floor(candidate);
      const parsed = new Date(millis);
      if (!Number.isNaN(parsed.getTime())) {
        return parsed.toISOString();
      }
    }
  }
  return void 0;
}
function pushMessage(destination, conversationId, record) {
  const text = normalizeText2(record.content ?? record.text);
  if (!text) {
    return;
  }
  const role = typeof record.role === "string" ? record.role.trim().toLowerCase() : void 0;
  destination.push({
    source: "claude",
    conversationId,
    role: role || void 0,
    text,
    timestamp: extractTimestamp(record)
  });
}
function normalizeClaudeExport(input) {
  const messages = [];
  if (Array.isArray(input)) {
    for (const item of input) {
      if (!item || typeof item !== "object") continue;
      const record = item;
      const conversationId = typeof record.id === "string" ? record.id : typeof record.uuid === "string" ? record.uuid : void 0;
      if (Array.isArray(record.messages)) {
        for (const message of record.messages) {
          if (!message || typeof message !== "object") continue;
          pushMessage(messages, conversationId, message);
        }
        continue;
      }
      pushMessage(messages, conversationId, record);
    }
    return messages;
  }
  if (input && typeof input === "object") {
    const root = input;
    if (Array.isArray(root.conversations)) {
      return normalizeClaudeExport(root.conversations);
    }
    if (Array.isArray(root.messages)) {
      return normalizeClaudeExport([{ id: root.id, messages: root.messages }]);
    }
  }
  return messages;
}

// src/replay/normalizers/opencode.ts
function normalizeText3(value) {
  if (typeof value === "string") {
    return value.replace(/\s+/g, " ").trim();
  }
  if (Array.isArray(value)) {
    return value.map((entry) => normalizeText3(entry)).filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
  }
  if (!value || typeof value !== "object") {
    return "";
  }
  const record = value;
  if (typeof record.text === "string") return normalizeText3(record.text);
  if (typeof record.content === "string") return normalizeText3(record.content);
  return "";
}
function toTimestamp(value) {
  if (typeof value === "string" && value.trim()) {
    const parsed = new Date(value.trim());
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString();
  }
  if (typeof value === "number" && Number.isFinite(value) && value > 0) {
    const millis = value < 1e10 ? Math.floor(value * 1e3) : Math.floor(value);
    const parsed = new Date(millis);
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString();
  }
  return void 0;
}
function normalizeRecord(record) {
  const text = normalizeText3(record.content ?? record.text ?? record.message);
  if (!text) return null;
  const role = typeof record.role === "string" ? record.role.trim().toLowerCase() : typeof record.type === "string" ? record.type.trim().toLowerCase() : "";
  return {
    source: "opencode",
    conversationId: typeof record.conversationId === "string" ? record.conversationId : void 0,
    role: role || void 0,
    text,
    timestamp: toTimestamp(record.timestamp ?? record.createdAt ?? record.created_at ?? record.time)
  };
}
function normalizeOpenCodeExport(input) {
  if (typeof input === "string") {
    return input.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line) => {
      try {
        return normalizeRecord(JSON.parse(line));
      } catch {
        return null;
      }
    }).filter((value) => value !== null);
  }
  if (Array.isArray(input)) {
    return input.map((item) => item && typeof item === "object" ? normalizeRecord(item) : null).filter((value) => value !== null);
  }
  if (input && typeof input === "object") {
    const root = input;
    if (Array.isArray(root.messages)) {
      return normalizeOpenCodeExport(root.messages);
    }
  }
  return [];
}

// src/replay/normalizers/openclaw.ts
function normalizeText4(value) {
  if (typeof value === "string") {
    return value.replace(/\s+/g, " ").trim();
  }
  if (Array.isArray(value)) {
    return value.map((entry) => normalizeText4(entry)).filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
  }
  if (!value || typeof value !== "object") {
    return "";
  }
  const record = value;
  if (typeof record.text === "string") return normalizeText4(record.text);
  if (typeof record.content === "string") return normalizeText4(record.content);
  return "";
}
function toTimestamp2(value) {
  if (typeof value === "string" && value.trim()) {
    const parsed = new Date(value.trim());
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString();
  }
  if (typeof value === "number" && Number.isFinite(value) && value > 0) {
    const millis = value < 1e10 ? Math.floor(value * 1e3) : Math.floor(value);
    const parsed = new Date(millis);
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString();
  }
  return void 0;
}
function normalizeOpenClawRecord(record) {
  let role = "";
  let text = "";
  if (typeof record.role === "string" && "content" in record) {
    role = record.role.trim().toLowerCase();
    text = normalizeText4(record.content);
  } else if (record.type === "message" && record.message && typeof record.message === "object") {
    const message = record.message;
    role = typeof message.role === "string" ? message.role.trim().toLowerCase() : "";
    text = normalizeText4(message.content);
  }
  if (!text) {
    return null;
  }
  return {
    source: "openclaw",
    role: role || void 0,
    text,
    timestamp: toTimestamp2(
      record.timestamp ?? record.createdAt ?? record.created_at ?? (record.message && typeof record.message === "object" ? record.message.timestamp : void 0)
    )
  };
}
function normalizeOpenClawTranscript(input) {
  return input.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line) => {
    try {
      return normalizeOpenClawRecord(JSON.parse(line));
    } catch {
      return null;
    }
  }).filter((entry) => entry !== null);
}

// src/commands/replay.ts
var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
function parseDateFlag(raw, label) {
  if (!raw) return void 0;
  const trimmed = raw.trim();
  if (!DATE_RE.test(trimmed)) {
    throw new Error(`Invalid ${label} date. Expected YYYY-MM-DD: ${raw}`);
  }
  return trimmed;
}
function collectFiles(rootPath, predicate) {
  if (!fs.existsSync(rootPath)) {
    return [];
  }
  const stat = fs.statSync(rootPath);
  if (stat.isFile()) {
    return predicate(rootPath) ? [rootPath] : [];
  }
  if (!stat.isDirectory()) {
    return [];
  }
  const files = [];
  for (const entry of fs.readdirSync(rootPath, { withFileTypes: true })) {
    const absolute = path.join(rootPath, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectFiles(absolute, predicate));
      continue;
    }
    if (entry.isFile() && predicate(absolute)) {
      files.push(absolute);
    }
  }
  return files.sort((left, right) => left.localeCompare(right));
}
function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}
function normalizeReplayMessages(source, inputPath) {
  if (source === "chatgpt") {
    const files2 = collectFiles(inputPath, (filePath) => path.basename(filePath).toLowerCase() === "conversations.json");
    if (files2.length === 0) {
      throw new Error("ChatGPT replay expects conversations.json in --input path.");
    }
    return files2.flatMap((filePath) => normalizeChatGptExport(loadJson(filePath)));
  }
  if (source === "claude") {
    const files2 = collectFiles(inputPath, (filePath) => filePath.toLowerCase().endsWith(".json"));
    if (files2.length === 0) {
      throw new Error("Claude replay expects one or more .json files.");
    }
    return files2.flatMap((filePath) => normalizeClaudeExport(loadJson(filePath)));
  }
  if (source === "opencode") {
    const files2 = collectFiles(
      inputPath,
      (filePath) => filePath.toLowerCase().endsWith(".json") || filePath.toLowerCase().endsWith(".jsonl")
    );
    if (files2.length === 0) {
      throw new Error("OpenCode replay expects .json or .jsonl input files.");
    }
    return files2.flatMap((filePath) => {
      if (filePath.toLowerCase().endsWith(".jsonl")) {
        return normalizeOpenCodeExport(fs.readFileSync(filePath, "utf-8"));
      }
      return normalizeOpenCodeExport(loadJson(filePath));
    });
  }
  const files = collectFiles(inputPath, (filePath) => filePath.toLowerCase().endsWith(".jsonl"));
  if (files.length === 0) {
    throw new Error("OpenClaw replay expects .jsonl session transcript files.");
  }
  return files.flatMap((filePath) => normalizeOpenClawTranscript(fs.readFileSync(filePath, "utf-8")));
}
function normalizeDateFromTimestamp(timestamp, fallbackDate) {
  if (!timestamp) return fallbackDate;
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) {
    return fallbackDate;
  }
  return parsed.toISOString().slice(0, 10);
}
async function replayCommand(options) {
  const source = options.source;
  if (!["chatgpt", "claude", "opencode", "openclaw"].includes(source)) {
    throw new Error(`Unsupported replay source: ${source}`);
  }
  const fromDate = parseDateFlag(options.from, "from");
  const toDate = parseDateFlag(options.to, "to");
  if (fromDate && toDate && fromDate > toDate) {
    throw new Error(`Invalid range: --from ${fromDate} is after --to ${toDate}.`);
  }
  const vaultPath = resolveVaultPath({ explicitPath: options.vaultPath });
  const resolvedInput = path.resolve(options.inputPath);
  if (!fs.existsSync(resolvedInput)) {
    throw new Error(`Replay input path not found: ${resolvedInput}`);
  }
  const allMessages = normalizeReplayMessages(source, resolvedInput);
  const fallbackDate = (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
  const filtered = allMessages.filter((message) => {
    const date = normalizeDateFromTimestamp(message.timestamp, fallbackDate);
    if (fromDate && date < fromDate) return false;
    if (toDate && date > toDate) return false;
    return true;
  });
  if (filtered.length === 0) {
    console.log("Replay found no messages in the requested range.");
    return;
  }
  const grouped = /* @__PURE__ */ new Map();
  for (const message of filtered) {
    const date = normalizeDateFromTimestamp(message.timestamp, fallbackDate);
    const bucket = grouped.get(date) ?? [];
    bucket.push(message);
    grouped.set(date, bucket);
  }
  const dates = [...grouped.keys()].sort((left, right) => left.localeCompare(right));
  if (options.dryRun) {
    console.log(`Dry run: ${filtered.length} message(s) across ${dates.length} day(s) would be replayed.`);
    return;
  }
  let observedDays = 0;
  for (const date of dates) {
    const nowForDate = () => /* @__PURE__ */ new Date(`${date}T12:00:00.000Z`);
    const observer = new Observer(vaultPath, {
      tokenThreshold: 1,
      reflectThreshold: Number.MAX_SAFE_INTEGER,
      now: nowForDate
    });
    const messages = (grouped.get(date) ?? []).map((message) => {
      const role = message.role?.trim().toLowerCase();
      return role ? `${role}: ${message.text}` : message.text;
    }).filter(Boolean);
    if (messages.length === 0) {
      continue;
    }
    await observer.processMessages(messages, {
      source,
      transcriptId: path.basename(resolvedInput),
      timestamp: nowForDate()
    });
    await observer.flush();
    observedDays += 1;
  }
  if (dates.length > 0) {
    const first = /* @__PURE__ */ new Date(`${dates[0]}T00:00:00.000Z`);
    const last = /* @__PURE__ */ new Date(`${dates[dates.length - 1]}T00:00:00.000Z`);
    const spanDays = Math.max(1, Math.floor((last.getTime() - first.getTime()) / (24 * 60 * 60 * 1e3)) + 1);
    await runReflection({
      vaultPath,
      days: spanDays,
      now: () => /* @__PURE__ */ new Date(`${dates[dates.length - 1]}T12:00:00.000Z`),
      dryRun: false
    });
  }
  console.log(`Replay complete: ${filtered.length} message(s) ingested across ${observedDays} day(s).`);
}
function registerReplayCommand(program) {
  program.command("replay").description("Replay historical exports into ClawVault observations").requiredOption("--source <platform>", "Source platform (chatgpt|claude|opencode|openclaw)").requiredOption("--input <path>", "Export file or directory").option("--from <date>", "Start date (YYYY-MM-DD)").option("--to <date>", "End date (YYYY-MM-DD)").option("--dry-run", "Preview replay without writing").option("-v, --vault <path>", "Vault path").action(async (rawOptions) => {
    await replayCommand({
      source: rawOptions.source,
      inputPath: rawOptions.input,
      from: rawOptions.from,
      to: rawOptions.to,
      dryRun: rawOptions.dryRun,
      vaultPath: rawOptions.vault
    });
  });
}

export {
  replayCommand,
  registerReplayCommand
};
