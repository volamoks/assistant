// src/lib/observation-format.ts
var DATE_HEADING_RE = /^##\s+(\d{4}-\d{2}-\d{2})\s*$/;
var SCORED_LINE_RE = /^(?:-\s*)?\[(decision|preference|fact|commitment|task|todo|commitment-unresolved|milestone|lesson|relationship|project)\|c=(0(?:\.\d+)?|1(?:\.0+)?)\|i=(0(?:\.\d+)?|1(?:\.0+)?)\]\s+(.+)$/i;
var EMOJI_LINE_RE = /^(?:-\s*)?(🔴|🟡|🟢)\s+(\d{2}:\d{2})?\s*(.+)$/u;
var DECISION_RE = /\b(decis(?:ion|ions)?|decid(?:e|ed|ing)|chose|selected|opted|went with|picked)\b/i;
var PREFERENCE_RE = /\b(prefer(?:ence|s|red)?|likes?|dislikes?|default to|always use|never use)\b/i;
var COMMITMENT_RE = /\b(commit(?:ment|ted)?|promised|deadline|due|scheduled|will deliver|agreed to)\b/i;
var TODO_RE = /(?:\btodo:\s*|\bwe need to\b|\bdon't forget(?: to)?\b|\bremember to\b|\bmake sure to\b)/i;
var COMMITMENT_TASK_RE = /\b(?:i'?ll|i will|let me|(?:i'?m\s+)?going to|plan to|should)\b/i;
var UNRESOLVED_RE = /\b(?:need to figure out|tbd|to be determined)\b/i;
var DEADLINE_RE = /\b(?:by\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow)|before\s+the\s+\w+|deadline is)\b/i;
var MILESTONE_RE = /\b(released?|shipped|launched|merged|published|milestone|v\d+\.\d+)\b/i;
var LESSON_RE = /\b(learn(?:ed|ing|t)|lesson|insight|realized|discovered|never again)\b/i;
var RELATIONSHIP_RE = /\b(talked to|met with|spoke with|asked|client|partner|teammate|colleague)\b/i;
var PROJECT_RE = /\b(project|feature|service|repo|api|roadmap|sprint)\b/i;
function clamp01(value) {
  if (!Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}
function scoreFromLegacyPriority(priority) {
  if (priority === "\u{1F534}") return 0.9;
  if (priority === "\u{1F7E1}") return 0.6;
  return 0.2;
}
function confidenceFromLegacyPriority(priority) {
  if (priority === "\u{1F534}") return 0.9;
  if (priority === "\u{1F7E1}") return 0.8;
  return 0.7;
}
function inferObservationType(content) {
  if (DECISION_RE.test(content)) return "decision";
  if (UNRESOLVED_RE.test(content)) return "commitment-unresolved";
  if (TODO_RE.test(content)) return "todo";
  if (COMMITMENT_TASK_RE.test(content) || DEADLINE_RE.test(content)) return "task";
  if (COMMITMENT_RE.test(content)) return "commitment";
  if (MILESTONE_RE.test(content)) return "milestone";
  if (PREFERENCE_RE.test(content)) return "preference";
  if (LESSON_RE.test(content)) return "lesson";
  if (RELATIONSHIP_RE.test(content)) return "relationship";
  if (PROJECT_RE.test(content)) return "project";
  return "fact";
}
function formatScore(value) {
  return clamp01(value).toFixed(2);
}
function normalizeObservationContent(content) {
  return content.replace(/^\d{2}:\d{2}\s+/, "").replace(/\s+/g, " ").trim().toLowerCase();
}
function parseObservationLine(line, date) {
  const scored = line.match(SCORED_LINE_RE);
  if (scored) {
    return {
      date,
      type: scored[1].toLowerCase(),
      confidence: clamp01(Number.parseFloat(scored[2])),
      importance: clamp01(Number.parseFloat(scored[3])),
      content: scored[4].trim(),
      format: "scored",
      rawLine: line
    };
  }
  const emoji = line.match(EMOJI_LINE_RE);
  if (!emoji) {
    return null;
  }
  const priority = emoji[1];
  const time = emoji[2]?.trim();
  const text = emoji[3].trim();
  const content = time ? `${time} ${text}` : text;
  return {
    date,
    type: inferObservationType(content),
    confidence: confidenceFromLegacyPriority(priority),
    importance: scoreFromLegacyPriority(priority),
    content,
    format: "emoji",
    priority,
    time,
    rawLine: line
  };
}
function parseObservationMarkdown(markdown) {
  const parsed = [];
  let currentDate = "";
  for (const line of markdown.split(/\r?\n/)) {
    const heading = line.match(DATE_HEADING_RE);
    if (heading) {
      currentDate = heading[1];
      continue;
    }
    if (!currentDate) {
      continue;
    }
    const record = parseObservationLine(line.trim(), currentDate);
    if (record) {
      parsed.push(record);
    }
  }
  return parsed;
}
function renderScoredObservationLine(record) {
  return `- [${record.type}|c=${formatScore(record.confidence)}|i=${formatScore(record.importance)}] ${record.content.trim()}`;
}
function renderObservationMarkdown(sections) {
  const chunks = [];
  const dates = [...sections.keys()].sort((left, right) => left.localeCompare(right));
  for (const date of dates) {
    const lines = sections.get(date) ?? [];
    if (lines.length === 0) continue;
    chunks.push(`## ${date}`);
    chunks.push("");
    for (const line of lines) {
      chunks.push(renderScoredObservationLine(line));
    }
    chunks.push("");
  }
  return chunks.join("\n").trim();
}

export {
  DATE_HEADING_RE,
  inferObservationType,
  normalizeObservationContent,
  parseObservationLine,
  parseObservationMarkdown,
  renderScoredObservationLine,
  renderObservationMarkdown
};
