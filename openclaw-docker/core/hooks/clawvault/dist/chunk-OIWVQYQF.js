import {
  formatAge
} from "./chunk-7ZRP733D.js";
import {
  checkDirtyDeath,
  clearDirtyFlag
} from "./chunk-F55HGNU4.js";

// src/commands/recover.ts
import * as fs from "fs";
import * as path from "path";
var CLAWVAULT_DIR = ".clawvault";
var CHECKPOINT_FILE = "last-checkpoint.json";
var CHECKPOINT_HISTORY_DIR = "checkpoints";
function parseCheckpointFile(filePath) {
  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, "utf-8"));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return null;
    }
    const record = parsed;
    const timestamp = typeof record.timestamp === "string" ? record.timestamp.trim() : "";
    if (!timestamp) {
      return null;
    }
    const checkpoint = {
      timestamp,
      workingOn: typeof record.workingOn === "string" ? record.workingOn : null,
      focus: typeof record.focus === "string" ? record.focus : null,
      blocked: typeof record.blocked === "string" ? record.blocked : null
    };
    if (typeof record.sessionId === "string") {
      checkpoint.sessionId = record.sessionId;
    }
    if (typeof record.sessionKey === "string") {
      checkpoint.sessionKey = record.sessionKey;
    }
    if (typeof record.model === "string") {
      checkpoint.model = record.model;
    }
    if (typeof record.tokenEstimate === "number" && Number.isFinite(record.tokenEstimate)) {
      checkpoint.tokenEstimate = record.tokenEstimate;
    }
    if (typeof record.sessionStartedAt === "string") {
      checkpoint.sessionStartedAt = record.sessionStartedAt;
    }
    if (typeof record.urgent === "boolean") {
      checkpoint.urgent = record.urgent;
    }
    return checkpoint;
  } catch {
    return null;
  }
}
function compareByTimestampDesc(left, right) {
  const leftTime = Date.parse(left.timestamp);
  const rightTime = Date.parse(right.timestamp);
  if (!Number.isNaN(leftTime) && !Number.isNaN(rightTime)) {
    return rightTime - leftTime;
  }
  return right.timestamp.localeCompare(left.timestamp);
}
async function checkRecoveryStatus(vaultPath) {
  const { died, checkpoint, deathTime } = await checkDirtyDeath(vaultPath);
  return { died, checkpoint, deathTime };
}
function listCheckpoints(vaultPath) {
  const resolvedVaultPath = path.resolve(vaultPath);
  const clawvaultDir = path.join(resolvedVaultPath, CLAWVAULT_DIR);
  const historyDir = path.join(clawvaultDir, CHECKPOINT_HISTORY_DIR);
  const checkpoints = [];
  if (fs.existsSync(historyDir)) {
    const files = fs.readdirSync(historyDir).filter((entry) => entry.endsWith(".json")).sort().reverse();
    for (const fileName of files) {
      const absolutePath = path.join(historyDir, fileName);
      const parsed = parseCheckpointFile(absolutePath);
      if (!parsed) {
        continue;
      }
      checkpoints.push({
        ...parsed,
        filePath: absolutePath
      });
    }
  }
  if (checkpoints.length === 0) {
    const latestCheckpointPath = path.join(clawvaultDir, CHECKPOINT_FILE);
    if (fs.existsSync(latestCheckpointPath)) {
      const fallback = parseCheckpointFile(latestCheckpointPath);
      if (fallback) {
        checkpoints.push({
          ...fallback,
          filePath: latestCheckpointPath
        });
      }
    }
  }
  return checkpoints.sort(compareByTimestampDesc);
}
async function recover(vaultPath, options = {}) {
  const { clearFlag = false } = options;
  const { died, checkpoint, deathTime } = await checkRecoveryStatus(vaultPath);
  if (!died) {
    return {
      died: false,
      deathTime: null,
      checkpoint: null,
      handoffPath: null,
      handoffContent: null,
      recoveryMessage: "No context death detected. Clean startup."
    };
  }
  const handoffsDir = path.join(vaultPath, "handoffs");
  let handoffPath = null;
  let handoffContent = null;
  if (fs.existsSync(handoffsDir)) {
    const files = fs.readdirSync(handoffsDir).filter((f) => f.startsWith("handoff-") && f.endsWith(".md")).sort().reverse();
    if (files.length > 0) {
      handoffPath = path.join(handoffsDir, files[0]);
      handoffContent = fs.readFileSync(handoffPath, "utf-8");
    }
  }
  let message = "\u26A0\uFE0F **CONTEXT DEATH DETECTED**\n\n";
  message += `Your previous session died at ${deathTime}.

`;
  if (checkpoint) {
    message += "**Last known state:**\n";
    if (checkpoint.workingOn) {
      message += `- Working on: ${checkpoint.workingOn}
`;
    }
    if (checkpoint.focus) {
      message += `- Focus: ${checkpoint.focus}
`;
    }
    if (checkpoint.blocked) {
      message += `- Blocked: ${checkpoint.blocked}
`;
    }
    message += "\n";
  }
  if (handoffPath) {
    message += `**Last handoff:** ${path.basename(handoffPath)}
`;
    message += "Review and resume from where you left off.\n";
  } else {
    message += "**No handoff found.** You may have lost context.\n";
  }
  if (clearFlag) {
    await clearDirtyFlag(vaultPath);
  }
  return {
    died: true,
    deathTime,
    checkpoint,
    handoffPath,
    handoffContent,
    recoveryMessage: message
  };
}
function formatRecoveryCheckStatus(info) {
  if (!info.died) {
    return "\u2713 Dirty death flag is clear.";
  }
  let output = "\u26A0\uFE0F Dirty death flag is set.\n";
  output += `Death time: ${info.deathTime}
`;
  if (info.checkpoint?.timestamp) {
    const age = formatAge(Date.now() - new Date(info.checkpoint.timestamp).getTime());
    output += `Last checkpoint: ${info.checkpoint.timestamp} (${age} ago)
`;
  } else {
    output += "Last checkpoint: unavailable\n";
  }
  output += "Use `clawvault recover --clear` after reviewing recovery details.";
  return output;
}
function formatCheckpointList(checkpoints) {
  if (checkpoints.length === 0) {
    return "No checkpoints found.";
  }
  const headers = ["TIMESTAMP", "WORKING_ON", "FOCUS", "FILE"];
  const rows = checkpoints.map((checkpoint) => ({
    timestamp: checkpoint.timestamp,
    workingOn: checkpoint.workingOn ?? "-",
    focus: checkpoint.focus ?? "-",
    file: path.basename(checkpoint.filePath)
  }));
  const timestampWidth = Math.max(headers[0].length, ...rows.map((row) => row.timestamp.length));
  const workingOnWidth = Math.max(headers[1].length, ...rows.map((row) => row.workingOn.length));
  const focusWidth = Math.max(headers[2].length, ...rows.map((row) => row.focus.length));
  const fileWidth = Math.max(headers[3].length, ...rows.map((row) => row.file.length));
  const lines = [];
  lines.push(
    `${headers[0].padEnd(timestampWidth)}  ${headers[1].padEnd(workingOnWidth)}  ${headers[2].padEnd(focusWidth)}  ${headers[3].padEnd(fileWidth)}`
  );
  lines.push(
    `${"-".repeat(timestampWidth)}  ${"-".repeat(workingOnWidth)}  ${"-".repeat(focusWidth)}  ${"-".repeat(fileWidth)}`
  );
  for (const row of rows) {
    lines.push(
      `${row.timestamp.padEnd(timestampWidth)}  ${row.workingOn.padEnd(workingOnWidth)}  ${row.focus.padEnd(focusWidth)}  ${row.file}`
    );
  }
  return lines.join("\n");
}
function formatRecoveryInfo(info, options = {}) {
  const { verbose = false } = options;
  if (!info.died) {
    return "\u2713 Clean startup - no context death detected.";
  }
  let output = "\n\u26A0\uFE0F  CONTEXT DEATH DETECTED\n";
  output += "\u2550".repeat(40) + "\n\n";
  output += `Death time: ${info.deathTime}
`;
  if (info.checkpoint?.timestamp) {
    const age = formatAge(Date.now() - new Date(info.checkpoint.timestamp).getTime());
    output += `Checkpoint: ${info.checkpoint.timestamp} (${age} ago)
`;
  }
  output += "\n";
  if (info.checkpoint) {
    output += "Last checkpoint:\n";
    if (info.checkpoint.workingOn) {
      output += `  \u2022 Working on: ${info.checkpoint.workingOn}
`;
    }
    if (info.checkpoint.focus) {
      output += `  \u2022 Focus: ${info.checkpoint.focus}
`;
    }
    if (info.checkpoint.blocked) {
      output += `  \u2022 Blocked: ${info.checkpoint.blocked}
`;
    }
    if (info.checkpoint.sessionKey || info.checkpoint.model || info.checkpoint.tokenEstimate !== void 0) {
      output += "  \u2022 Session:\n";
      if (info.checkpoint.sessionKey) {
        output += `    - Key: ${info.checkpoint.sessionKey}
`;
      }
      if (info.checkpoint.model) {
        output += `    - Model: ${info.checkpoint.model}
`;
      }
      if (info.checkpoint.tokenEstimate !== void 0) {
        output += `    - Token estimate: ${info.checkpoint.tokenEstimate}
`;
      }
    }
    output += "\n";
  } else {
    output += "No checkpoint data found.\n\n";
  }
  if (info.handoffPath) {
    output += `Last handoff: ${path.basename(info.handoffPath)}
`;
  } else {
    output += "No handoff found - context may be lost.\n";
  }
  if (verbose) {
    if (info.checkpoint) {
      output += "\nCheckpoint JSON:\n";
      output += JSON.stringify(info.checkpoint, null, 2) + "\n";
    }
    if (info.handoffContent) {
      output += "\nHandoff content:\n";
      output += info.handoffContent.trim() + "\n";
    }
  }
  output += "\n" + "\u2550".repeat(40) + "\n";
  output += "Run `clawvault recap` to see full context.\n";
  return output;
}

export {
  checkRecoveryStatus,
  listCheckpoints,
  recover,
  formatRecoveryCheckStatus,
  formatCheckpointList,
  formatRecoveryInfo
};
