import {
  completeTask,
  createTask,
  formatTransitionsTable,
  getStatusDisplay,
  getStatusIcon,
  listTasks,
  queryTransitions,
  readTask,
  updateTask
} from "./chunk-QWQ3TIKS.js";

// src/commands/task.ts
function taskAdd(vaultPath, title, options = {}) {
  return createTask(vaultPath, title, {
    owner: options.owner,
    project: options.project,
    priority: options.priority,
    due: options.due,
    content: options.content,
    tags: options.tags,
    description: options.description,
    estimate: options.estimate,
    parent: options.parent,
    depends_on: options.dependsOn
  });
}
function taskList(vaultPath, options = {}) {
  const filters = {};
  if (options.status) filters.status = options.status;
  if (options.owner) filters.owner = options.owner;
  if (options.project) filters.project = options.project;
  if (options.priority) filters.priority = options.priority;
  if (options.due) filters.due = true;
  if (options.tag) filters.tag = options.tag;
  if (options.overdue) filters.overdue = true;
  const listed = listTasks(vaultPath, filters);
  if (!options.status && !options.overdue) {
    return listed.filter((t) => t.frontmatter.status !== "done");
  }
  return listed;
}
function taskUpdate(vaultPath, slug, options) {
  return updateTask(vaultPath, slug, {
    status: options.status,
    owner: options.owner,
    project: options.project,
    priority: options.priority,
    blocked_by: options.blockedBy,
    due: options.due,
    tags: options.tags,
    description: options.description,
    estimate: options.estimate,
    parent: options.parent,
    depends_on: options.dependsOn,
    confidence: options.confidence,
    reason: options.reason
  });
}
function taskDone(vaultPath, slug, options = {}) {
  return completeTask(vaultPath, slug, {
    confidence: options.confidence,
    reason: options.reason ?? void 0
  });
}
function taskTransitions(vaultPath, taskId, options = {}) {
  const events = queryTransitions(vaultPath, {
    taskId,
    agent: options.agent,
    failed: options.failed
  });
  if (options.json) {
    return JSON.stringify(events, null, 2);
  }
  return formatTransitionsTable(events);
}
function taskShow(vaultPath, slug) {
  return readTask(vaultPath, slug);
}
function formatTaskList(tasks) {
  if (tasks.length === 0) {
    return "No tasks found.\n";
  }
  const headers = ["STATUS", "OWNER", "PRIORITY", "PROJECT", "META", "TITLE"];
  const widths = [10, 12, 8, 14, 64, 32];
  const truncate = (value, width) => {
    if (value.length <= width) return value;
    return value.slice(0, width - 3) + "...";
  };
  let output = headers.map((h, i) => h.padEnd(widths[i])).join("  ") + "\n";
  for (const task of tasks) {
    const icon = getStatusIcon(task.frontmatter.status);
    const statusDisplay = getStatusDisplay(task.frontmatter.status);
    const status = `${icon} ${statusDisplay}`;
    const owner = task.frontmatter.owner || "-";
    const priority = task.frontmatter.priority || "low";
    const project = task.frontmatter.project || "-";
    const metaParts = [];
    if (task.frontmatter.due) metaParts.push(`due:${task.frontmatter.due.split("T")[0]}`);
    if (task.frontmatter.tags?.length) metaParts.push(task.frontmatter.tags.map((tag) => `#${tag}`).join(","));
    if (task.frontmatter.parent) metaParts.push(`parent:${task.frontmatter.parent}`);
    if (task.frontmatter.depends_on?.length) {
      metaParts.push(`deps:${task.frontmatter.depends_on.join("|")}`);
    }
    const meta = metaParts.length > 0 ? metaParts.join(" ") : "-";
    const title = truncate(task.title, widths[5]);
    const row = [
      status.padEnd(widths[0]),
      owner.padEnd(widths[1]),
      priority.padEnd(widths[2]),
      project.padEnd(widths[3]),
      truncate(meta, widths[4]).padEnd(widths[4]),
      title
    ];
    output += row.join("  ") + "\n";
  }
  return output;
}
function formatTaskDetails(task) {
  let output = "";
  output += `# ${task.title}
`;
  output += "-".repeat(40) + "\n";
  output += `Status: ${getStatusIcon(task.frontmatter.status)} ${getStatusDisplay(task.frontmatter.status)}
`;
  if (task.frontmatter.owner) {
    output += `Owner: ${task.frontmatter.owner}
`;
  }
  if (task.frontmatter.project) {
    output += `Project: ${task.frontmatter.project}
`;
  }
  if (task.frontmatter.priority) {
    output += `Priority: ${task.frontmatter.priority}
`;
  }
  if (task.frontmatter.description) {
    output += `Description: ${task.frontmatter.description}
`;
  }
  if (task.frontmatter.estimate) {
    output += `Estimate: ${task.frontmatter.estimate}
`;
  }
  if (task.frontmatter.parent) {
    output += `Parent: ${task.frontmatter.parent}
`;
  }
  if (task.frontmatter.depends_on && task.frontmatter.depends_on.length > 0) {
    output += `Depends on: ${task.frontmatter.depends_on.join(", ")}
`;
  }
  if (task.frontmatter.due) {
    output += `Due: ${task.frontmatter.due}
`;
  }
  if (task.frontmatter.blocked_by) {
    output += `Blocked by: ${task.frontmatter.blocked_by}
`;
  }
  if (task.frontmatter.tags && task.frontmatter.tags.length > 0) {
    output += `Tags: ${task.frontmatter.tags.join(", ")}
`;
  }
  if (task.frontmatter.escalation) {
    output += "Escalation: true\n";
  }
  if (task.frontmatter.confidence !== void 0) {
    output += `Confidence: ${task.frontmatter.confidence}
`;
  }
  if (task.frontmatter.reason) {
    output += `Reason: ${task.frontmatter.reason}
`;
  }
  output += `Created: ${task.frontmatter.created}
`;
  output += `Updated: ${task.frontmatter.updated}
`;
  if (task.frontmatter.completed) {
    output += `Completed: ${task.frontmatter.completed}
`;
  }
  output += `File: ${task.path}
`;
  output += "-".repeat(40) + "\n";
  const contentWithoutTitle = task.content.replace(/^#\s+.+\n/, "").trim();
  if (contentWithoutTitle) {
    output += "\n" + contentWithoutTitle + "\n";
  }
  return output;
}
async function taskCommand(vaultPath, action, args) {
  const options = args.options || {};
  switch (action) {
    case "add": {
      if (!args.title) {
        throw new Error("Title is required for task add");
      }
      const task = taskAdd(vaultPath, args.title, options);
      console.log(`\u2713 Created task: ${task.slug}`);
      console.log(`  Path: ${task.path}`);
      break;
    }
    case "list": {
      const tasks = taskList(vaultPath, options);
      if (options.json) {
        console.log(JSON.stringify(tasks, null, 2));
      } else {
        console.log(formatTaskList(tasks));
      }
      break;
    }
    case "update": {
      if (!args.slug) {
        throw new Error("Task slug is required for update");
      }
      const task = taskUpdate(vaultPath, args.slug, options);
      console.log(`\u2713 Updated task: ${task.slug}`);
      break;
    }
    case "done": {
      if (!args.slug) {
        throw new Error("Task slug is required for done");
      }
      const task = taskDone(vaultPath, args.slug, {
        confidence: options.confidence,
        reason: options.reason ?? void 0
      });
      console.log(`\u2713 Completed task: ${task.slug}`);
      break;
    }
    case "transitions": {
      const output = taskTransitions(vaultPath, args.slug, {
        agent: options.agent,
        failed: options.failed,
        json: options.json
      });
      console.log(output);
      break;
    }
    case "show": {
      if (!args.slug) {
        throw new Error("Task slug is required for show");
      }
      const task = taskShow(vaultPath, args.slug);
      if (!task) {
        throw new Error(`Task not found: ${args.slug}`);
      }
      if (options.json) {
        console.log(JSON.stringify(task, null, 2));
      } else {
        console.log(formatTaskDetails(task));
      }
      break;
    }
    default:
      throw new Error(`Unknown task action: ${action}`);
  }
}

export {
  taskAdd,
  taskList,
  taskUpdate,
  taskDone,
  taskTransitions,
  taskShow,
  formatTaskList,
  formatTaskDetails,
  taskCommand
};
