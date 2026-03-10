// src/observer/session-parser.ts
import * as fs from "fs";
import * as path from "path";
var JSONL_SAMPLE_LIMIT = 20;
var MARKDOWN_SIGNAL_RE = /^(#{1,6}\s|[-*+]\s|>\s)/;
var MARKDOWN_INLINE_RE = /(\[[^\]]+\]\([^)]+\)|[*_`~])/;
function normalizeText(value) {
  return value.replace(/\s+/g, " ").trim();
}
function extractText(value) {
  if (typeof value === "string") {
    return normalizeText(value);
  }
  if (Array.isArray(value)) {
    const parts = [];
    for (const part of value) {
      const extracted = extractText(part);
      if (extracted) {
        parts.push(extracted);
      }
    }
    return normalizeText(parts.join(" "));
  }
  if (!value || typeof value !== "object") {
    return "";
  }
  const record = value;
  if (typeof record.text === "string") {
    return normalizeText(record.text);
  }
  if (typeof record.content === "string") {
    return normalizeText(record.content);
  }
  return "";
}
function normalizeRole(role) {
  if (typeof role !== "string") {
    return "";
  }
  const normalized = role.trim().toLowerCase();
  if (!normalized) {
    return "";
  }
  return normalized;
}
function isLikelyJsonMessage(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const record = value;
  if ("role" in record && "content" in record) {
    return true;
  }
  if (record.type === "message" && record.message && typeof record.message === "object") {
    return true;
  }
  return false;
}
function parseJsonLine(line) {
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
    const content = extractText(entry.content);
    if (!content) return "";
    return role ? `${role}: ${content}` : content;
  }
  if (entry.type === "message" && entry.message && typeof entry.message === "object") {
    const message = entry.message;
    const role = normalizeRole(message.role);
    const content = extractText(message.content);
    if (!content) return "";
    return role ? `${role}: ${content}` : content;
  }
  return "";
}
function parseJsonLines(raw) {
  const messages = [];
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const parsed = parseJsonLine(trimmed);
    if (parsed) {
      messages.push(parsed);
    }
  }
  return messages;
}
function stripMarkdownSyntax(text) {
  return normalizeText(
    text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").replace(/[*_`~]/g, "").replace(/<[^>]+>/g, "")
  );
}
function normalizeMarkdownLine(line) {
  return stripMarkdownSyntax(
    line.replace(/^>\s*/, "").replace(/^[-*+]\s+/, "").replace(/^#{1,6}\s+/, "")
  );
}
function parseMarkdown(raw) {
  const withoutCodeBlocks = raw.replace(/```[\s\S]*?```/g, " ");
  const blocks = withoutCodeBlocks.split(/\r?\n\s*\r?\n/).map((block) => block.trim()).filter(Boolean);
  const messages = [];
  for (const block of blocks) {
    const lines = block.split(/\r?\n/).map((line) => normalizeMarkdownLine(line)).filter(Boolean);
    if (lines.length === 0) {
      continue;
    }
    const joined = stripMarkdownSyntax(lines.join(" "));
    if (!joined) continue;
    const roleMatch = /^(user|assistant|system|tool)\s*:?\s*(.+)$/i.exec(joined);
    if (roleMatch) {
      const role = normalizeRole(roleMatch[1]);
      const content = normalizeText(roleMatch[2]);
      if (content) {
        messages.push(`${role}: ${content}`);
      }
      continue;
    }
    messages.push(joined);
  }
  return messages;
}
function parsePlainText(raw) {
  return raw.split(/\r?\n/).map((line) => normalizeText(line)).filter(Boolean);
}
function detectSessionFormat(raw, filePath) {
  const nonEmptyLines = raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (nonEmptyLines.length === 0) {
    return "plain";
  }
  const sample = nonEmptyLines.slice(0, JSONL_SAMPLE_LIMIT);
  const jsonHits = sample.filter((line) => {
    try {
      const parsed = JSON.parse(line);
      return isLikelyJsonMessage(parsed);
    } catch {
      return false;
    }
  }).length;
  if (jsonHits >= Math.max(1, Math.ceil(sample.length * 0.6))) {
    return "jsonl";
  }
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".md" || ext === ".markdown") {
    return "markdown";
  }
  const markdownSignals = sample.filter((line) => MARKDOWN_SIGNAL_RE.test(line) || MARKDOWN_INLINE_RE.test(line)).length;
  if (markdownSignals >= Math.max(2, Math.ceil(sample.length * 0.4))) {
    return "markdown";
  }
  return "plain";
}
function parseSessionFile(filePath) {
  const resolved = path.resolve(filePath);
  const raw = fs.readFileSync(resolved, "utf-8");
  const format = detectSessionFormat(raw, resolved);
  if (format === "jsonl") {
    const parsed = parseJsonLines(raw);
    if (parsed.length > 0) {
      return parsed;
    }
  }
  if (format === "markdown") {
    const parsed = parseMarkdown(raw);
    if (parsed.length > 0) {
      return parsed;
    }
  }
  return parsePlainText(raw);
}

export {
  parseSessionFile
};
