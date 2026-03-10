import {
  getSessionsDir
} from "./chunk-HRLWZGMA.js";
import {
  Observer
} from "./chunk-Q2J5YTUF.js";

// src/observer/active-session-observer.ts
import * as fs from "fs";
import * as path from "path";
var ONE_KIB = 1024;
var ONE_MIB = ONE_KIB * ONE_KIB;
var SMALL_SESSION_THRESHOLD_BYTES = 50 * ONE_KIB;
var MEDIUM_SESSION_THRESHOLD_BYTES = 150 * ONE_KIB;
var LARGE_SESSION_THRESHOLD_BYTES = 300 * ONE_KIB;
var DEFAULT_AGENT_ID = "main";
var AGENT_ID_RE = /^[a-zA-Z0-9_-]{1,100}$/;
var SESSION_ID_RE = /^[a-zA-Z0-9._-]{1,200}$/;
var CURSOR_FILE_NAME = "observe-cursors.json";
var STALE_CURSOR_THRESHOLD_MS = 12 * 60 * 60 * 1e3;
function isFiniteNonNegative(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}
function normalizeAgentId(input) {
  const raw = (input ?? process.env.OPENCLAW_AGENT_ID ?? DEFAULT_AGENT_ID).trim();
  if (!AGENT_ID_RE.test(raw)) {
    return DEFAULT_AGENT_ID;
  }
  return raw;
}
function resolveSessionsDirectory(agentId, override) {
  if (override?.trim()) {
    return path.resolve(override.trim());
  }
  return getSessionsDir(agentId);
}
function getCursorPath(vaultPath) {
  return path.join(vaultPath, ".clawvault", CURSOR_FILE_NAME);
}
function getScaledObservationThresholdBytes(fileSizeBytes) {
  if (fileSizeBytes < ONE_MIB) {
    return SMALL_SESSION_THRESHOLD_BYTES;
  }
  if (fileSizeBytes <= 5 * ONE_MIB) {
    return MEDIUM_SESSION_THRESHOLD_BYTES;
  }
  return LARGE_SESSION_THRESHOLD_BYTES;
}
function parseCursorStore(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return {};
  }
  const input = raw;
  const store = {};
  for (const [sessionId, value] of Object.entries(input)) {
    if (!SESSION_ID_RE.test(sessionId)) continue;
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    const entry = value;
    if (!isFiniteNonNegative(entry.lastObservedOffset)) continue;
    if (!isFiniteNonNegative(entry.lastFileSize)) continue;
    if (typeof entry.lastObservedAt !== "string" || !entry.lastObservedAt.trim()) continue;
    if (typeof entry.sessionKey !== "string" || !entry.sessionKey.trim()) continue;
    store[sessionId] = {
      lastObservedOffset: entry.lastObservedOffset,
      lastObservedAt: entry.lastObservedAt,
      sessionKey: entry.sessionKey,
      lastFileSize: entry.lastFileSize
    };
  }
  return store;
}
function loadObserveCursorStore(vaultPath) {
  const cursorPath = getCursorPath(vaultPath);
  if (!fs.existsSync(cursorPath)) {
    return {};
  }
  try {
    const raw = JSON.parse(fs.readFileSync(cursorPath, "utf-8"));
    return parseCursorStore(raw);
  } catch {
    return {};
  }
}
function saveObserveCursorStore(vaultPath, store) {
  const cursorPath = getCursorPath(vaultPath);
  fs.mkdirSync(path.dirname(cursorPath), { recursive: true });
  fs.writeFileSync(cursorPath, `${JSON.stringify(store, null, 2)}
`, "utf-8");
}
function parseAgentIdFromSessionKey(sessionKey) {
  const match = /^agent:([^:]+):/.exec(sessionKey);
  if (!match?.[1]) {
    return null;
  }
  const candidate = match[1].trim();
  if (!AGENT_ID_RE.test(candidate)) {
    return null;
  }
  return candidate;
}
function resolveSessionFileForCursor(sessionId, cursor, sessionsDirOverride) {
  const candidates = /* @__PURE__ */ new Set();
  if (sessionsDirOverride?.trim()) {
    candidates.add(path.join(path.resolve(sessionsDirOverride.trim()), `${sessionId}.jsonl`));
  }
  const agentId = parseAgentIdFromSessionKey(cursor.sessionKey) ?? DEFAULT_AGENT_ID;
  candidates.add(path.join(getSessionsDir(agentId), `${sessionId}.jsonl`));
  for (const filePath of candidates) {
    try {
      const stat = fs.statSync(filePath);
      if (stat.isFile()) {
        return filePath;
      }
    } catch {
      continue;
    }
  }
  return null;
}
function getObserverStaleness(vaultPath, options = {}) {
  const nowDate = options.now ? options.now() : /* @__PURE__ */ new Date();
  const nowMs = nowDate.getTime();
  if (!Number.isFinite(nowMs)) {
    return {
      staleCount: 0,
      oldestMs: 0,
      newestMs: 0
    };
  }
  const cursorStore = loadObserveCursorStore(path.resolve(vaultPath));
  let staleCount = 0;
  let oldestMs = 0;
  let newestMs = Number.POSITIVE_INFINITY;
  for (const [sessionId, cursor] of Object.entries(cursorStore)) {
    const observedAtMs = Date.parse(cursor.lastObservedAt);
    if (!Number.isFinite(observedAtMs)) {
      continue;
    }
    const ageMs = Math.max(0, nowMs - observedAtMs);
    if (ageMs <= STALE_CURSOR_THRESHOLD_MS) {
      continue;
    }
    const sessionFilePath = resolveSessionFileForCursor(sessionId, cursor, options.sessionsDir);
    if (!sessionFilePath) {
      continue;
    }
    let sessionStat;
    try {
      sessionStat = fs.statSync(sessionFilePath);
    } catch {
      continue;
    }
    if (!sessionStat.isFile()) {
      continue;
    }
    if (cursor.lastFileSize >= sessionStat.size) {
      continue;
    }
    staleCount += 1;
    oldestMs = Math.max(oldestMs, ageMs);
    newestMs = Math.min(newestMs, ageMs);
  }
  return {
    staleCount,
    oldestMs: staleCount > 0 ? oldestMs : 0,
    newestMs: staleCount > 0 ? newestMs : 0
  };
}
function loadSessionIndex(sessionsDir) {
  const indexPath = path.join(sessionsDir, "sessions.json");
  if (!fs.existsSync(indexPath)) {
    return {};
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(indexPath, "utf-8"));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    return parsed;
  } catch {
    return {};
  }
}
function resolveTranscriptPath(sessionsDir, sessionId) {
  return path.join(sessionsDir, `${sessionId}.jsonl`);
}
function discoverSessionDescriptors(sessionsDir, fallbackAgentId) {
  const descriptors = [];
  const seen = /* @__PURE__ */ new Set();
  const index = loadSessionIndex(sessionsDir);
  const indexedEntries = Object.entries(index).sort((left, right) => {
    const leftUpdated = Number(left[1]?.updatedAt ?? 0);
    const rightUpdated = Number(right[1]?.updatedAt ?? 0);
    return rightUpdated - leftUpdated;
  });
  for (const [sessionKey, entry] of indexedEntries) {
    if (!entry || typeof entry !== "object") continue;
    const sessionId = typeof entry.sessionId === "string" ? entry.sessionId.trim() : "";
    if (!SESSION_ID_RE.test(sessionId) || seen.has(sessionId)) continue;
    const filePath = resolveTranscriptPath(sessionsDir, sessionId);
    try {
      const stat = fs.statSync(filePath);
      if (!stat.isFile()) continue;
      seen.add(sessionId);
      descriptors.push({ sessionId, sessionKey, filePath });
    } catch {
      continue;
    }
  }
  const fallbackPrefix = `agent:${fallbackAgentId}:`;
  for (const fileName of fs.readdirSync(sessionsDir)) {
    if (!fileName.endsWith(".jsonl") || fileName.includes(".backup") || fileName.includes(".deleted")) {
      continue;
    }
    const sessionId = fileName.slice(0, -".jsonl".length);
    if (!SESSION_ID_RE.test(sessionId) || seen.has(sessionId)) continue;
    const filePath = path.join(sessionsDir, fileName);
    try {
      const stat = fs.statSync(filePath);
      if (!stat.isFile()) continue;
      seen.add(sessionId);
      descriptors.push({
        sessionId,
        sessionKey: `${fallbackPrefix}unknown:${sessionId}`,
        filePath
      });
    } catch {
      continue;
    }
  }
  return descriptors;
}
function normalizeWhitespace(value) {
  return value.replace(/\s+/g, " ").trim();
}
function extractContentText(value) {
  if (typeof value === "string") {
    return normalizeWhitespace(value);
  }
  if (Array.isArray(value)) {
    const parts = value.map((item) => extractContentText(item)).filter(Boolean);
    return normalizeWhitespace(parts.join(" "));
  }
  if (!value || typeof value !== "object") {
    return "";
  }
  const input = value;
  if (typeof input.text === "string") {
    return normalizeWhitespace(input.text);
  }
  if (typeof input.content === "string") {
    return normalizeWhitespace(input.content);
  }
  return "";
}
function normalizeRole(role) {
  if (typeof role !== "string") {
    return "";
  }
  return role.trim().toLowerCase();
}
function parseOpenClawJsonLine(line) {
  if (!line.trim()) {
    return "";
  }
  let parsed;
  try {
    parsed = JSON.parse(line);
  } catch {
    return "";
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return "";
  }
  const entry = parsed;
  if ("role" in entry && "content" in entry) {
    const role = normalizeRole(entry.role);
    const content = extractContentText(entry.content);
    if (!content) return "";
    return role ? `${role}: ${content}` : content;
  }
  if (entry.type === "message" && entry.message && typeof entry.message === "object") {
    const message = entry.message;
    const role = normalizeRole(message.role);
    const content = extractContentText(message.content);
    if (!content) return "";
    return role ? `${role}: ${content}` : content;
  }
  return "";
}
function decodeLineBuffer(lineBuffer) {
  if (lineBuffer.length === 0) {
    return "";
  }
  const normalized = lineBuffer[lineBuffer.length - 1] === 13 ? lineBuffer.subarray(0, lineBuffer.length - 1) : lineBuffer;
  return normalized.toString("utf-8").trim();
}
async function readIncrementalMessages(filePath, startOffset) {
  const messages = [];
  let nextOffset = startOffset;
  let remainder = Buffer.alloc(0);
  const stream = fs.createReadStream(filePath, {
    start: startOffset
  });
  for await (const chunk of stream) {
    const chunkBuffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    const combined = remainder.length > 0 ? Buffer.concat([remainder, chunkBuffer]) : chunkBuffer;
    let lineStart = 0;
    for (let index = 0; index < combined.length; index += 1) {
      if (combined[index] !== 10) continue;
      const lineBuffer = combined.subarray(lineStart, index);
      const line = decodeLineBuffer(lineBuffer);
      const parsed = parseOpenClawJsonLine(line);
      if (parsed) {
        messages.push(parsed);
      }
      nextOffset += index - lineStart + 1;
      lineStart = index + 1;
    }
    remainder = combined.subarray(lineStart);
  }
  if (remainder.length > 0) {
    const trailing = decodeLineBuffer(remainder);
    if (trailing) {
      const parsed = parseOpenClawJsonLine(trailing);
      if (parsed) {
        messages.push(parsed);
        nextOffset += remainder.length;
      }
    }
  }
  return { messages, nextOffset };
}
function parseSessionSourceLabel(sessionKey) {
  const parts = sessionKey.split(":");
  if (parts.length < 3 || parts[0] !== "agent") {
    return "session";
  }
  const scope = parts.slice(2);
  if (scope[0] === "main") {
    return "main";
  }
  if (scope[0] === "telegram" && scope[1] === "dm") {
    return "telegram-dm";
  }
  if (scope[0] === "telegram" && scope[1] === "group") {
    return "telegram-group";
  }
  if (scope[0] === "discord") {
    return "discord";
  }
  if (scope[0] === "telegram") {
    return "telegram";
  }
  if (scope[0] === "slack") {
    return "slack";
  }
  return scope[0] || "session";
}
function createDefaultObserver(vaultPath, options) {
  return new Observer(vaultPath, options);
}
function parseRoutingCounts(routingSummary) {
  const counts = {};
  const [, categorySection = ""] = routingSummary.split("\u2192");
  const summaryCategories = categorySection.split("(")[0] ?? "";
  if (!summaryCategories) {
    return counts;
  }
  for (const match of summaryCategories.matchAll(/\b([a-z][a-z0-9-]*):\s*(\d+)\b/gi)) {
    const category = match[1].toLowerCase();
    const count = Number.parseInt(match[2], 10);
    if (!Number.isFinite(count) || count <= 0) {
      continue;
    }
    counts[category] = (counts[category] ?? 0) + count;
  }
  return counts;
}
function mergeRoutingCounts(target, incoming) {
  for (const [category, count] of Object.entries(incoming)) {
    target[category] = (target[category] ?? 0) + count;
  }
}
function stringifyError(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return String(error);
}
function selectCandidates(descriptors, cursors, minNewBytes) {
  const candidates = [];
  for (const descriptor of descriptors) {
    let stat;
    try {
      stat = fs.statSync(descriptor.filePath);
    } catch {
      continue;
    }
    if (!stat.isFile()) continue;
    const fileSize = stat.size;
    const cursor = cursors[descriptor.sessionId];
    const previousOffset = cursor && isFiniteNonNegative(cursor.lastObservedOffset) ? cursor.lastObservedOffset : 0;
    const startOffset = previousOffset <= fileSize ? previousOffset : 0;
    const newBytes = Math.max(0, fileSize - startOffset);
    const thresholdBytes = minNewBytes ?? getScaledObservationThresholdBytes(fileSize);
    if (newBytes < thresholdBytes) {
      continue;
    }
    candidates.push({
      sessionId: descriptor.sessionId,
      sessionKey: descriptor.sessionKey,
      sourceLabel: parseSessionSourceLabel(descriptor.sessionKey),
      filePath: descriptor.filePath,
      fileSize,
      startOffset,
      newBytes,
      thresholdBytes
    });
  }
  return candidates;
}
async function observeActiveSessions(options, dependencies = {}) {
  const vaultPath = path.resolve(options.vaultPath);
  const agentId = normalizeAgentId(options.agentId);
  const sessionsDir = resolveSessionsDirectory(agentId, options.sessionsDir);
  const dryRun = Boolean(options.dryRun);
  if (!fs.existsSync(sessionsDir) || !fs.statSync(sessionsDir).isDirectory()) {
    return {
      agentId,
      sessionsDir,
      checkedSessions: 0,
      candidateSessions: 0,
      observedSessions: 0,
      cursorUpdates: 0,
      dryRun,
      totalNewBytes: 0,
      observedNewBytes: 0,
      routedCounts: {},
      failedSessionCount: 0,
      failedSessions: [],
      candidates: []
    };
  }
  const now = dependencies.now ?? (() => /* @__PURE__ */ new Date());
  const cursors = loadObserveCursorStore(vaultPath);
  const descriptors = discoverSessionDescriptors(sessionsDir, agentId);
  const candidates = selectCandidates(descriptors, cursors, options.minNewBytes);
  if (dryRun || candidates.length === 0) {
    return {
      agentId,
      sessionsDir,
      checkedSessions: descriptors.length,
      candidateSessions: candidates.length,
      observedSessions: 0,
      cursorUpdates: 0,
      dryRun,
      totalNewBytes: candidates.reduce((sum, candidate) => sum + candidate.newBytes, 0),
      observedNewBytes: 0,
      routedCounts: {},
      failedSessionCount: 0,
      failedSessions: [],
      candidates
    };
  }
  const observerFactory = dependencies.createObserver ?? createDefaultObserver;
  const observerOptions = {
    tokenThreshold: options.threshold,
    reflectThreshold: options.reflectThreshold,
    model: options.model,
    extractTasks: options.extractTasks
  };
  let observedSessions = 0;
  let cursorUpdates = 0;
  let observedNewBytes = 0;
  const routedCounts = {};
  const failedSessions = [];
  for (const candidate of candidates) {
    try {
      const observer = observerFactory(vaultPath, observerOptions);
      const { messages, nextOffset } = await readIncrementalMessages(candidate.filePath, candidate.startOffset);
      const taggedMessages = messages.map((message) => `[${candidate.sourceLabel}] ${message}`);
      if (taggedMessages.length > 0) {
        await observer.processMessages(taggedMessages, {
          source: "openclaw",
          sessionKey: candidate.sessionKey,
          transcriptId: candidate.sessionId
        });
        const flushResult = await observer.flush();
        mergeRoutingCounts(routedCounts, parseRoutingCounts(flushResult.routingSummary));
        observedSessions += 1;
        observedNewBytes += candidate.newBytes;
      }
      if (nextOffset > candidate.startOffset) {
        cursors[candidate.sessionId] = {
          lastObservedOffset: nextOffset,
          lastObservedAt: now().toISOString(),
          sessionKey: candidate.sessionKey,
          lastFileSize: candidate.fileSize
        };
        cursorUpdates += 1;
      }
    } catch (error) {
      const reason = stringifyError(error);
      failedSessions.push({
        sessionId: candidate.sessionId,
        sessionKey: candidate.sessionKey,
        sourceLabel: candidate.sourceLabel,
        error: reason
      });
      console.error(
        `[observer] failed to observe session ${candidate.sessionKey} (${candidate.sessionId}): ${reason}`
      );
    }
  }
  if (cursorUpdates > 0) {
    saveObserveCursorStore(vaultPath, cursors);
  }
  return {
    agentId,
    sessionsDir,
    checkedSessions: descriptors.length,
    candidateSessions: candidates.length,
    observedSessions,
    cursorUpdates,
    dryRun,
    totalNewBytes: candidates.reduce((sum, candidate) => sum + candidate.newBytes, 0),
    observedNewBytes,
    routedCounts,
    failedSessionCount: failedSessions.length,
    failedSessions,
    candidates
  };
}

export {
  getScaledObservationThresholdBytes,
  getObserverStaleness,
  parseSessionSourceLabel,
  observeActiveSessions
};
