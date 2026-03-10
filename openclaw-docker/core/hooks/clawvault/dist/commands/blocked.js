import {
  getBlockedTasks
} from "../chunk-QWQ3TIKS.js";
import "../chunk-MFAWT5O5.js";
import "../chunk-7766SIJP.js";

// src/commands/blocked.ts
function toDateStr(val) {
  if (!val) return "unknown";
  if (val instanceof Date) return val.toISOString().split("T")[0];
  const s = String(val);
  if (s.includes("T")) return s.split("T")[0];
  return s;
}
function blockedList(vaultPath, options = {}) {
  let tasks = getBlockedTasks(vaultPath, options.project);
  if (options.escalated) {
    tasks = tasks.filter((t) => t.frontmatter.escalation === true);
  }
  return tasks;
}
function formatBlockedList(tasks) {
  if (tasks.length === 0) {
    return "No blocked tasks.\n";
  }
  let output = `BLOCKED TASKS (${tasks.length})

`;
  for (const task of tasks) {
    const owner = task.frontmatter.owner || "unassigned";
    const project = task.frontmatter.project || "no project";
    const blockedBy = task.frontmatter.blocked_by || "unknown";
    const updatedDate = toDateStr(task.frontmatter.updated);
    output += `\u25A0 ${task.title} (${owner}, ${project})
`;
    output += `  Blocked by: ${blockedBy}
`;
    output += `  Since: ${updatedDate}
`;
    output += "\n";
  }
  return output;
}
async function blockedCommand(vaultPath, options = {}) {
  const tasks = blockedList(vaultPath, options);
  if (options.json) {
    console.log(JSON.stringify(tasks, null, 2));
  } else {
    console.log(formatBlockedList(tasks));
  }
}
export {
  blockedCommand,
  blockedList,
  formatBlockedList
};
