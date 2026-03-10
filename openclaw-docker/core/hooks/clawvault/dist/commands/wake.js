import {
  recover
} from "../chunk-OIWVQYQF.js";
import "../chunk-7ZRP733D.js";
import {
  ClawVault
} from "../chunk-RCBMXTWS.js";
import {
  parseObservationMarkdown
} from "../chunk-FHFUXL6G.js";
import "../chunk-MAKNAHAW.js";
import "../chunk-2CDEETQN.js";
import "../chunk-ZZA73MFY.js";
import {
  listObservationFiles
} from "../chunk-Z2XBWN7A.js";
import {
  clearDirtyFlag
} from "../chunk-F55HGNU4.js";

// src/commands/wake.ts
import * as fs from "fs";
import * as path from "path";
var DEFAULT_HANDOFF_LIMIT = 3;
var MAX_WAKE_RED_OBSERVATIONS = 20;
var MAX_WAKE_YELLOW_OBSERVATIONS = 10;
var MAX_WAKE_OUTPUT_LINES = 100;
function formatSummaryItems(items, maxItems = 2) {
  const cleaned = items.map((item) => item.trim()).filter(Boolean);
  if (cleaned.length === 0) return "";
  if (cleaned.length <= maxItems) return cleaned.join(", ");
  return `${cleaned.slice(0, maxItems).join(", ")} +${cleaned.length - maxItems} more`;
}
function buildWakeSummary(recovery, recap) {
  let workSummary = "";
  if (recovery.checkpoint?.workingOn) {
    workSummary = recovery.checkpoint.workingOn;
  } else {
    const latestHandoff = recap.recentHandoffs[0];
    if (latestHandoff?.workingOn?.length) {
      workSummary = formatSummaryItems(latestHandoff.workingOn);
    } else if (recap.activeProjects.length > 0) {
      workSummary = formatSummaryItems(recap.activeProjects);
    }
  }
  return workSummary || "No recent work summary found.";
}
function readRecentObservationHighlights(vaultPath) {
  const now = /* @__PURE__ */ new Date();
  const today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const fileByDate = new Map(
    listObservationFiles(vaultPath, {
      includeLegacy: true,
      includeArchive: false,
      dedupeByDate: true
    }).map((entry) => [entry.date, entry.path])
  );
  const highlights = [];
  for (let daysAgo = 0; daysAgo < 7; daysAgo++) {
    const date = new Date(today);
    date.setUTCDate(today.getUTCDate() - daysAgo);
    const dateKey = date.toISOString().slice(0, 10);
    const filePath = fileByDate.get(dateKey);
    if (!filePath || !fs.existsSync(filePath)) continue;
    const content = fs.readFileSync(filePath, "utf-8");
    const parsed = parseObservationMarkdown(content).filter((record) => record.importance >= 0.4);
    const dayStructural = [];
    const dayPotential = [];
    for (const record of parsed) {
      const item = {
        date: dateKey,
        type: record.type,
        importance: record.importance,
        text: record.content.trim()
      };
      if (record.importance >= 0.8) {
        dayStructural.push(item);
      } else {
        dayPotential.push(item);
      }
    }
    if (daysAgo === 0) {
      highlights.push(...dayStructural, ...dayPotential);
    } else if (daysAgo === 1) {
      highlights.push(...dayStructural, ...dayPotential.slice(0, 5));
    } else if (daysAgo <= 3) {
      highlights.push(...dayStructural);
    } else {
      highlights.push(...dayStructural.slice(0, 3));
    }
  }
  return highlights;
}
function timeFromObservationText(text) {
  const match = text.match(/^([01]\d|2[0-3]):([0-5]\d)\b/);
  if (!match) {
    return -1;
  }
  return Number.parseInt(match[1], 10) * 60 + Number.parseInt(match[2], 10);
}
function compareByRecency(left, right) {
  if (left.date !== right.date) {
    return right.date.localeCompare(left.date);
  }
  if (left.importance !== right.importance) {
    return right.importance - left.importance;
  }
  return timeFromObservationText(right.text) - timeFromObservationText(left.text);
}
function formatRecentObservations(highlights) {
  if (highlights.length === 0) {
    return "_No structural or potentially important observations from the recent window._";
  }
  const sorted = [...highlights].sort(compareByRecency);
  const structural = sorted.filter((item) => item.importance >= 0.8).slice(0, MAX_WAKE_RED_OBSERVATIONS);
  const potential = sorted.filter((item) => item.importance >= 0.4 && item.importance < 0.8).slice(0, MAX_WAKE_YELLOW_OBSERVATIONS);
  const visible = [...structural, ...potential].sort(compareByRecency);
  const omittedCount = Math.max(0, highlights.length - visible.length);
  const byDate = /* @__PURE__ */ new Map();
  for (const item of visible) {
    const bucket = byDate.get(item.date) ?? [];
    bucket.push(item);
    byDate.set(item.date, bucket);
  }
  const lines = [];
  const bodyLineBudget = Math.max(1, MAX_WAKE_OUTPUT_LINES - (omittedCount > 0 ? 1 : 0));
  for (const [date, items] of byDate.entries()) {
    if (lines.length >= bodyLineBudget) {
      break;
    }
    lines.push(`### ${date}`);
    for (const item of items) {
      if (lines.length >= bodyLineBudget) {
        break;
      }
      lines.push(`- [${item.type}|i=${item.importance.toFixed(2)}] ${item.text}`);
    }
    if (lines.length < bodyLineBudget) {
      lines.push("");
    }
  }
  if (omittedCount > 0) {
    lines.push(`... and ${omittedCount} more observations (use \`clawvault context\` to query)`);
  }
  return lines.join("\n").trim();
}
async function generateExecutiveSummary(recovery, recap, highlights) {
  if (process.env.CLAWVAULT_NO_LLM || process.env.VITEST) return null;
  const apiKey = process.env.GEMINI_API_KEY || process.env.ANTHROPIC_API_KEY || process.env.OPENAI_API_KEY;
  if (!apiKey) return null;
  const structuralItems = highlights.filter((h) => h.importance >= 0.8).map((h) => h.text).slice(0, 10);
  const potentialItems = highlights.filter((h) => h.importance >= 0.4 && h.importance < 0.8).map((h) => h.text).slice(0, 5);
  const projects = recap.activeProjects.slice(0, 8);
  const commitments = recap.pendingCommitments.slice(0, 5);
  const lastWork = recovery.checkpoint?.workingOn || recap.recentHandoffs[0]?.workingOn?.join(", ") || "";
  const blockers = recovery.checkpoint?.blocked || recap.recentHandoffs[0]?.blocked?.join(", ") || "";
  const nextSteps = recap.recentHandoffs[0]?.nextSteps?.join(", ") || "";
  const prompt = [
    "You are a chief of staff briefing an AI agent waking up for a new session.",
    "Write a 3-5 sentence executive summary answering: What matters RIGHT NOW?",
    "Be direct and specific. No headers, no bullets \u2014 just a tight paragraph.",
    "Mention the most urgent item first. Include deadlines if any.",
    "",
    `Last working on: ${lastWork || "(unknown)"}`,
    `Blockers: ${blockers || "(none)"}`,
    `Next steps: ${nextSteps || "(none)"}`,
    `Active projects (${projects.length}): ${projects.join(", ") || "(none)"}`,
    `Pending commitments: ${commitments.join(", ") || "(none)"}`,
    `Structural observations: ${structuralItems.join(" | ") || "(none)"}`,
    `Potential observations: ${potentialItems.join(" | ") || "(none)"}`,
    "",
    "Write the briefing now. Be concise."
  ].join("\n");
  try {
    if (process.env.GEMINI_API_KEY) {
      const model = "gemini-2.0-flash";
      const resp = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,
        {
          method: "POST",
          headers: { "content-type": "application/json", "x-goog-api-key": process.env.GEMINI_API_KEY },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
            generationConfig: { temperature: 0.3, maxOutputTokens: 300 }
          })
        }
      );
      if (!resp.ok) return null;
      const data = await resp.json();
      return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || null;
    }
  } catch {
    return null;
  }
  return null;
}
async function wake(options) {
  const vaultPath = path.resolve(options.vaultPath);
  const recovery = await recover(vaultPath, { clearFlag: true });
  await clearDirtyFlag(vaultPath);
  const vault = new ClawVault(vaultPath);
  await vault.load();
  const recap = await vault.generateRecap({
    handoffLimit: options.handoffLimit ?? DEFAULT_HANDOFF_LIMIT,
    brief: options.brief ?? true
  });
  const highlights = readRecentObservationHighlights(vaultPath);
  const observations = formatRecentObservations(highlights);
  const execSummary = options.noSummary ? null : await generateExecutiveSummary(recovery, recap, highlights);
  const highlightSummaryItems = highlights.map(
    (item) => `[${item.type}|i=${item.importance.toFixed(2)}] ${item.text}`
  );
  const wakeSummary = formatSummaryItems(highlightSummaryItems);
  const baseSummary = buildWakeSummary(recovery, recap);
  const fullBaseSummary = wakeSummary ? `${baseSummary} | ${wakeSummary}` : baseSummary;
  const summary = execSummary || fullBaseSummary;
  const baseRecapMarkdown = vault.formatRecap(recap, { brief: options.brief ?? true }).trimEnd();
  const execSection = execSummary ? `## \u{1F4CB} Executive Summary

${execSummary}

` : "";
  const recapMarkdown = `${execSection}${baseRecapMarkdown}

## Recent Observations
${observations}`;
  return {
    recovery,
    recap,
    recapMarkdown,
    summary,
    observations
  };
}
export {
  buildWakeSummary,
  wake
};
