import {
  CANVAS_COLORS,
  LAYOUT,
  createGroupWithNodes,
  createTextNode,
  flattenGroups,
  positionGroupsVertically,
  truncateText
} from "../chunk-MDIH26GC.js";
import {
  loadMemoryGraphIndex
} from "../chunk-ZZA73MFY.js";
import {
  listObservationFiles
} from "../chunk-Z2XBWN7A.js";
import {
  listTasks
} from "../chunk-QWQ3TIKS.js";
import "../chunk-MFAWT5O5.js";
import "../chunk-7766SIJP.js";

// src/commands/canvas.ts
import * as fs2 from "fs";
import * as path2 from "path";

// src/lib/canvas-default-template.ts
import * as fs from "fs";
import * as path from "path";
var STATUS_ORDER = ["in-progress", "open", "blocked", "done"];
var STATUS_LABELS = {
  "in-progress": "In Progress",
  open: "Open",
  blocked: "Blocked",
  done: "Done"
};
var STATUS_COLORS = {
  "in-progress": CANVAS_COLORS.ORANGE,
  open: void 0,
  blocked: CANVAS_COLORS.RED,
  done: CANVAS_COLORS.GREEN
};
function groupTasksByStatus(tasks) {
  const grouped = {
    open: [],
    "in-progress": [],
    blocked: [],
    done: []
  };
  for (const task of tasks) {
    grouped[task.frontmatter.status].push(task);
  }
  return grouped;
}
function readObservationTitle(filePath) {
  try {
    const content = fs.readFileSync(filePath, "utf-8");
    const headingMatch = content.match(/^#\s+(.+)$/m);
    if (headingMatch?.[1]) {
      return truncateText(headingMatch[1].trim(), 44);
    }
    const firstBodyLine = content.split(/\r?\n/).map((line) => line.trim()).find((line) => line.length > 0 && line !== "---" && !line.includes(":"));
    return firstBodyLine ? truncateText(firstBodyLine, 44) : null;
  } catch {
    return null;
  }
}
function buildTaskStatusGroup(tasks) {
  const grouped = groupTasksByStatus(tasks);
  const summaryLines = STATUS_ORDER.map((status) => `${STATUS_LABELS[status]}: ${grouped[status].length}`);
  const childNodes = [
    createTextNode(
      0,
      0,
      LAYOUT.DEFAULT_NODE_WIDTH,
      LAYOUT.SMALL_NODE_HEIGHT + 24,
      `**Tasks by Status**

Total: ${tasks.length}
${summaryLines.join("\n")}`
    )
  ];
  for (const status of STATUS_ORDER) {
    const bucket = grouped[status];
    const lines = bucket.length === 0 ? ["- none"] : bucket.slice(0, 6).map((task) => `- ${truncateText(task.title, 42)}`);
    if (bucket.length > 6) {
      lines.push(`- ... and ${bucket.length - 6} more`);
    }
    childNodes.push(
      createTextNode(
        0,
        0,
        LAYOUT.DEFAULT_NODE_WIDTH,
        LAYOUT.SMALL_NODE_HEIGHT + lines.length * 18,
        `**${STATUS_LABELS[status]} (${bucket.length})**

${lines.join("\n")}`,
        STATUS_COLORS[status]
      )
    );
  }
  return createGroupWithNodes(
    LAYOUT.LEFT_COLUMN_X,
    0,
    LAYOUT.LEFT_COLUMN_WIDTH,
    "Vault Status",
    childNodes,
    CANVAS_COLORS.CYAN
  );
}
function buildRecentObservationsGroup(vaultPath) {
  const observations = listObservationFiles(vaultPath, { includeLegacy: true, includeArchive: false });
  const recent = observations.slice(-8).reverse();
  const lines = recent.length === 0 ? ["- none"] : recent.map((entry) => {
    const title = readObservationTitle(entry.path);
    return title ? `- ${entry.date}: ${title}` : `- ${entry.date}`;
  });
  const text = [
    "**Recent Observations**",
    "",
    `Total days: ${observations.length}`,
    "",
    ...lines
  ].join("\n");
  return createGroupWithNodes(
    LAYOUT.LEFT_COLUMN_X,
    0,
    LAYOUT.LEFT_COLUMN_WIDTH,
    "Recent Observations",
    [createTextNode(0, 0, LAYOUT.DEFAULT_NODE_WIDTH, LAYOUT.DEFAULT_NODE_HEIGHT + lines.length * 18, text)],
    CANVAS_COLORS.CYAN
  );
}
function buildGraphStatsGroup(vaultPath) {
  const graph = loadMemoryGraphIndex(vaultPath)?.graph;
  const textLines = ["**Graph Stats**", ""];
  if (!graph) {
    textLines.push("Graph index not found.");
    textLines.push("Run `clawvault graph --build` to populate it.");
  } else {
    textLines.push(`Nodes: ${graph.stats.nodeCount}`);
    textLines.push(`Edges: ${graph.stats.edgeCount}`);
    textLines.push("");
    textLines.push("Node types:");
    const nodeTypeLines = Object.entries(graph.stats.nodeTypeCounts).sort((left, right) => right[1] - left[1]).slice(0, 6).map(([type, count]) => `- ${type}: ${count}`);
    textLines.push(...nodeTypeLines.length > 0 ? nodeTypeLines : ["- none"]);
  }
  return createGroupWithNodes(
    LAYOUT.LEFT_COLUMN_X,
    0,
    LAYOUT.LEFT_COLUMN_WIDTH,
    "Graph Stats",
    [
      createTextNode(
        0,
        0,
        LAYOUT.DEFAULT_NODE_WIDTH,
        LAYOUT.DEFAULT_NODE_HEIGHT + (textLines.length - 1) * 16,
        textLines.join("\n")
      )
    ],
    CANVAS_COLORS.PURPLE
  );
}
function generateDefaultCanvas(vaultPath) {
  const resolvedPath = path.resolve(vaultPath);
  const tasks = listTasks(resolvedPath);
  const groups = positionGroupsVertically([
    buildTaskStatusGroup(tasks),
    buildRecentObservationsGroup(resolvedPath),
    buildGraphStatsGroup(resolvedPath)
  ]);
  return {
    nodes: flattenGroups(groups),
    edges: []
  };
}

// src/lib/canvas-templates.ts
function generateCanvas(vaultPath) {
  return generateDefaultCanvas(vaultPath);
}

// src/commands/canvas.ts
function generateCanvas2(vaultPath) {
  return generateCanvas(path2.resolve(vaultPath));
}
async function canvasCommand(vaultPath, options = {}) {
  const resolvedPath = path2.resolve(vaultPath);
  const outputPath = options.output || path2.join(resolvedPath, "dashboard.canvas");
  const canvas = generateCanvas(resolvedPath);
  fs2.writeFileSync(outputPath, JSON.stringify(canvas, null, 2));
  console.log(`\u2713 Generated canvas: ${outputPath}`);
  console.log(`  Nodes: ${canvas.nodes.length}`);
  console.log(`  Edges: ${canvas.edges.length}`);
}
export {
  canvasCommand,
  generateCanvas2 as generateCanvas
};
