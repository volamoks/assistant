import {
  createBacklogItem,
  listBacklogItems,
  promoteBacklogItem
} from "../chunk-QWQ3TIKS.js";
import "../chunk-MFAWT5O5.js";
import "../chunk-7766SIJP.js";

// src/commands/backlog.ts
function toDateStr(val) {
  if (!val) return "unknown";
  if (val instanceof Date) return val.toISOString().split("T")[0];
  const s = String(val);
  if (s.includes("T")) return s.split("T")[0];
  return s;
}
function backlogAdd(vaultPath, title, options = {}) {
  return createBacklogItem(vaultPath, title, {
    source: options.source,
    project: options.project,
    content: options.content,
    tags: options.tags
  });
}
function backlogList(vaultPath, options = {}) {
  const filters = {};
  if (options.project) filters.project = options.project;
  return listBacklogItems(vaultPath, filters);
}
function backlogPromote(vaultPath, slug, options = {}) {
  return promoteBacklogItem(vaultPath, slug, {
    owner: options.owner,
    priority: options.priority,
    due: options.due
  });
}
function formatBacklogList(items) {
  if (items.length === 0) {
    return "No backlog items found.\n";
  }
  const headers = ["SOURCE", "PROJECT", "CREATED", "TITLE"];
  const widths = [12, 16, 12, 40];
  let output = headers.map((h, i) => h.padEnd(widths[i])).join("  ") + "\n";
  for (const item of items) {
    const source = item.frontmatter.source || "-";
    const project = item.frontmatter.project || "-";
    const created = toDateStr(item.frontmatter.created);
    const title = item.title.length > widths[3] ? item.title.slice(0, widths[3] - 3) + "..." : item.title;
    const row = [
      source.padEnd(widths[0]),
      project.padEnd(widths[1]),
      created.padEnd(widths[2]),
      title
    ];
    output += row.join("  ") + "\n";
  }
  return output;
}
function formatBacklogDetails(item) {
  let output = "";
  output += `# ${item.title}
`;
  output += "-".repeat(40) + "\n";
  if (item.frontmatter.source) {
    output += `Source: ${item.frontmatter.source}
`;
  }
  if (item.frontmatter.project) {
    output += `Project: ${item.frontmatter.project}
`;
  }
  if (item.frontmatter.tags && item.frontmatter.tags.length > 0) {
    output += `Tags: ${item.frontmatter.tags.join(", ")}
`;
  }
  output += `Created: ${item.frontmatter.created}
`;
  output += `File: ${item.path}
`;
  output += "-".repeat(40) + "\n";
  const contentWithoutTitle = item.content.replace(/^#\s+.+\n/, "").trim();
  if (contentWithoutTitle) {
    output += "\n" + contentWithoutTitle + "\n";
  }
  return output;
}
async function backlogCommand(vaultPath, action, args) {
  const options = args.options || {};
  switch (action) {
    case "add": {
      if (!args.title) {
        throw new Error("Title is required for backlog add");
      }
      const item = backlogAdd(vaultPath, args.title, options);
      console.log(`\u2713 Added to backlog: ${item.slug}`);
      console.log(`  Path: ${item.path}`);
      break;
    }
    case "list": {
      const items = backlogList(vaultPath, options);
      if (options.json) {
        console.log(JSON.stringify(items, null, 2));
      } else {
        console.log(formatBacklogList(items));
      }
      break;
    }
    case "promote": {
      if (!args.slug) {
        throw new Error("Backlog item slug is required for promote");
      }
      const task = backlogPromote(vaultPath, args.slug, options);
      console.log(`\u2713 Promoted to task: ${task.slug}`);
      console.log(`  Path: ${task.path}`);
      break;
    }
    default:
      throw new Error(`Unknown backlog action: ${action}`);
  }
}
export {
  backlogAdd,
  backlogCommand,
  backlogList,
  backlogPromote,
  formatBacklogDetails,
  formatBacklogList
};
