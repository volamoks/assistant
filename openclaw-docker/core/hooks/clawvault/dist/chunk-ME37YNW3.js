import {
  parseSessionFile
} from "./chunk-P5EPF6MB.js";
import {
  observeActiveSessions
} from "./chunk-IEVLHNLU.js";
import {
  Observer
} from "./chunk-Q2J5YTUF.js";
import {
  resolveVaultPath
} from "./chunk-MXSSG3QU.js";
import {
  getObservationPath
} from "./chunk-Z2XBWN7A.js";

// src/commands/observe.ts
import * as fs2 from "fs";
import * as path2 from "path";
import { spawn } from "child_process";

// src/observer/watcher.ts
import * as fs from "fs";
import * as path from "path";
import chokidar from "chokidar";
var DEFAULT_FLUSH_THRESHOLD_CHARS = 500;
var SessionWatcher = class {
  watchPath;
  observer;
  ignoreInitial;
  debounceMs;
  flushThresholdChars;
  watcher = null;
  fileOffsets = /* @__PURE__ */ new Map();
  pendingPaths = /* @__PURE__ */ new Set();
  debounceTimer = null;
  processingQueue = Promise.resolve();
  bufferedChars = 0;
  constructor(watchPath, observer, options = {}) {
    this.watchPath = path.resolve(watchPath);
    this.observer = observer;
    this.ignoreInitial = options.ignoreInitial ?? false;
    this.debounceMs = options.debounceMs ?? 500;
    this.flushThresholdChars = Math.max(1, options.flushThresholdChars ?? DEFAULT_FLUSH_THRESHOLD_CHARS);
  }
  async start() {
    if (!fs.existsSync(this.watchPath)) {
      throw new Error(`Watch path does not exist: ${this.watchPath}`);
    }
    this.watcher = chokidar.watch(this.watchPath, {
      persistent: true,
      ignoreInitial: this.ignoreInitial,
      awaitWriteFinish: {
        stabilityThreshold: 120,
        pollInterval: 30
      }
    });
    const enqueue = (changedPath) => {
      this.pendingPaths.add(path.resolve(changedPath));
      this.scheduleDrain();
    };
    this.watcher.on("add", enqueue);
    this.watcher.on("change", enqueue);
    this.watcher.on("unlink", (deletedPath) => {
      const resolved = path.resolve(deletedPath);
      this.fileOffsets.delete(resolved);
      this.pendingPaths.delete(resolved);
    });
    await new Promise((resolve3, reject) => {
      this.watcher?.once("ready", () => resolve3());
      this.watcher?.once("error", (error) => reject(error));
    });
    if (this.ignoreInitial) {
      this.primeInitialOffsets();
    }
  }
  async stop() {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
      this.drainPendingPaths();
    }
    await this.processingQueue.catch(() => void 0);
    if (this.bufferedChars > 0) {
      await this.observer.flush();
      this.bufferedChars = 0;
    }
    this.pendingPaths.clear();
    await this.watcher?.close();
    this.watcher = null;
  }
  scheduleDrain() {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    this.debounceTimer = setTimeout(() => {
      this.debounceTimer = null;
      this.drainPendingPaths();
    }, this.debounceMs);
  }
  drainPendingPaths() {
    const nextPaths = [...this.pendingPaths];
    this.pendingPaths.clear();
    for (const changedPath of nextPaths) {
      this.processingQueue = this.processingQueue.then(() => this.consumeFile(changedPath)).catch(() => void 0);
    }
  }
  async consumeFile(filePath) {
    const resolved = path.resolve(filePath);
    if (!fs.existsSync(resolved)) {
      return;
    }
    const stats = fs.statSync(resolved);
    if (!stats.isFile()) {
      return;
    }
    const previousOffset = this.fileOffsets.get(resolved) ?? 0;
    const startOffset = stats.size < previousOffset ? 0 : previousOffset;
    if (stats.size <= startOffset) {
      this.fileOffsets.set(resolved, stats.size);
      return;
    }
    const bytesToRead = stats.size - startOffset;
    const buffer = Buffer.alloc(bytesToRead);
    const fd = fs.openSync(resolved, "r");
    try {
      fs.readSync(fd, buffer, 0, bytesToRead, startOffset);
    } finally {
      fs.closeSync(fd);
    }
    this.fileOffsets.set(resolved, stats.size);
    const chunk = buffer.toString("utf-8");
    const messages = chunk.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (messages.length === 0) {
      return;
    }
    await this.observer.processMessages(messages);
    this.bufferedChars += chunk.length;
    if (this.bufferedChars >= this.flushThresholdChars) {
      await this.observer.flush();
      this.bufferedChars = 0;
    }
  }
  primeInitialOffsets() {
    for (const filePath of this.collectFiles(this.watchPath)) {
      try {
        const stats = fs.statSync(filePath);
        if (stats.isFile()) {
          this.fileOffsets.set(filePath, stats.size);
        }
      } catch {
      }
    }
  }
  collectFiles(targetPath) {
    if (!fs.existsSync(targetPath)) {
      return [];
    }
    const resolved = path.resolve(targetPath);
    const stats = fs.statSync(resolved);
    if (stats.isFile()) {
      return [resolved];
    }
    if (!stats.isDirectory()) {
      return [];
    }
    const collected = [];
    for (const entry of fs.readdirSync(resolved, { withFileTypes: true })) {
      const childPath = path.join(resolved, entry.name);
      if (entry.isDirectory()) {
        collected.push(...this.collectFiles(childPath));
      } else if (entry.isFile()) {
        collected.push(path.resolve(childPath));
      }
    }
    return collected;
  }
};

// src/commands/observe.ts
var ONE_KIB = 1024;
var ONE_MIB = ONE_KIB * ONE_KIB;
function parsePositiveInteger(raw, optionName) {
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`Invalid ${optionName}: ${raw}`);
  }
  return parsed;
}
function buildDaemonArgs(options) {
  const cliPath = process.argv[1];
  if (!cliPath) {
    throw new Error("Unable to resolve CLI script path for daemon mode.");
  }
  const args = [cliPath, "observe"];
  if (options.watch) {
    args.push("--watch", options.watch);
  }
  if (options.threshold) {
    args.push("--threshold", String(options.threshold));
  }
  if (options.reflectThreshold) {
    args.push("--reflect-threshold", String(options.reflectThreshold));
  }
  if (options.model) {
    args.push("--model", options.model);
  }
  if (options.extractTasks === false) {
    args.push("--no-extract-tasks");
  }
  if (options.vaultPath) {
    args.push("--vault", options.vaultPath);
  }
  return args;
}
function formatByteSummary(bytes) {
  const normalized = Number.isFinite(bytes) ? Math.max(0, bytes) : 0;
  if (normalized === 0) {
    return "0KB";
  }
  if (normalized >= ONE_MIB) {
    return `${(normalized / ONE_MIB).toFixed(1)}MB`;
  }
  return `${Math.max(1, Math.round(normalized / ONE_KIB))}KB`;
}
function formatCronSummary(result) {
  const decisionCount = result.routedCounts.decisions ?? 0;
  return `observed ${result.observedSessions} sessions, ${formatByteSummary(result.observedNewBytes)} new content, ${decisionCount} decision${decisionCount === 1 ? "" : "s"} extracted`;
}
async function runOneShotCompression(observer, sourceFile, vaultPath) {
  const resolved = path2.resolve(sourceFile);
  if (!fs2.existsSync(resolved) || !fs2.statSync(resolved).isFile()) {
    throw new Error(`Conversation file not found: ${resolved}`);
  }
  const messages = parseSessionFile(resolved);
  const transcriptStat = fs2.statSync(resolved);
  await observer.processMessages(messages, {
    source: "openclaw",
    transcriptId: path2.basename(resolved),
    timestamp: transcriptStat.mtime
  });
  const { observations, routingSummary } = await observer.flush();
  const outputPath = getObservationPath(vaultPath, /* @__PURE__ */ new Date());
  console.log(`Observations updated: ${outputPath}`);
  if (routingSummary) {
    console.log(routingSummary);
  }
}
async function watchSessions(observer, watchPath) {
  const watcher = new SessionWatcher(watchPath, observer);
  await watcher.start();
  console.log(`Watching session updates: ${watchPath}`);
  await new Promise((resolve3) => {
    const shutdown = async () => {
      process.off("SIGINT", onSigInt);
      process.off("SIGTERM", onSigTerm);
      await watcher.stop();
      resolve3();
    };
    const onSigInt = () => {
      void shutdown();
    };
    const onSigTerm = () => {
      void shutdown();
    };
    process.once("SIGINT", onSigInt);
    process.once("SIGTERM", onSigTerm);
  });
}
async function observeCommand(options) {
  if (options.cron && (options.active || options.watch || options.compress || options.daemon)) {
    throw new Error("--cron cannot be combined with --active, --watch, --compress, or --daemon.");
  }
  if (options.cron && options.dryRun) {
    throw new Error("--cron cannot be combined with --dry-run.");
  }
  if (options.active && (options.watch || options.compress || options.daemon)) {
    throw new Error("--active cannot be combined with --watch, --compress, or --daemon.");
  }
  if (options.compress && options.daemon) {
    throw new Error("--compress cannot be combined with --daemon.");
  }
  const vaultPath = resolveVaultPath({ explicitPath: options.vaultPath });
  if (options.active || options.cron) {
    const result = await observeActiveSessions({
      vaultPath,
      agentId: options.agent,
      minNewBytes: options.minNew,
      sessionsDir: options.sessionsDir,
      dryRun: options.dryRun,
      threshold: options.threshold,
      reflectThreshold: options.reflectThreshold,
      model: options.model,
      extractTasks: options.extractTasks
    });
    const failedSessionCount = result.failedSessionCount ?? 0;
    if (options.cron) {
      if (failedSessionCount > 0) {
        const firstFailure = result.failedSessions[0];
        if (firstFailure) {
          throw new Error(
            `observer failed for ${failedSessionCount} session(s); first error: ${firstFailure.sessionKey} - ${firstFailure.error}`
          );
        }
        throw new Error(`observer failed for ${failedSessionCount} session(s).`);
      }
      if (result.candidateSessions === 0) {
        console.log("nothing new");
        return;
      }
      console.log(formatCronSummary({
        observedSessions: result.observedSessions,
        observedNewBytes: result.observedNewBytes ?? result.totalNewBytes,
        routedCounts: result.routedCounts ?? {}
      }));
      return;
    }
    if (result.candidateSessions === 0) {
      console.log(`No active sessions crossed threshold (${result.checkedSessions} checked).`);
      return;
    }
    if (result.dryRun) {
      console.log(
        `Dry run: ${result.candidateSessions} session(s) would be observed (${result.totalNewBytes} new bytes).`
      );
      for (const candidate of result.candidates) {
        console.log(
          `- ${candidate.sessionKey} [${candidate.sourceLabel}] \u0394${candidate.newBytes}B (threshold ${candidate.thresholdBytes}B)`
        );
      }
      return;
    }
    console.log(
      `Active observation complete: ${result.observedSessions}/${result.candidateSessions} session(s) observed.${failedSessionCount > 0 ? ` ${failedSessionCount} failed.` : ""}`
    );
    if (failedSessionCount > 0) {
      for (const failure of result.failedSessions) {
        console.error(
          `[observer] session failed ${failure.sessionKey} (${failure.sessionId}): ${failure.error}`
        );
      }
    }
    return;
  }
  const observer = new Observer(vaultPath, {
    tokenThreshold: options.threshold,
    reflectThreshold: options.reflectThreshold,
    model: options.model,
    extractTasks: options.extractTasks
  });
  if (options.compress) {
    await runOneShotCompression(observer, options.compress, vaultPath);
    return;
  }
  let watchPath = options.watch ? path2.resolve(options.watch) : "";
  if (!watchPath && options.daemon) {
    watchPath = path2.join(vaultPath, "sessions");
  }
  if (!watchPath) {
    throw new Error("Either --watch or --compress must be provided.");
  }
  if (!fs2.existsSync(watchPath)) {
    if (options.daemon && !options.watch) {
      fs2.mkdirSync(watchPath, { recursive: true });
    } else {
      throw new Error(`Watch path does not exist: ${watchPath}`);
    }
  }
  if (options.daemon) {
    const daemonArgs = buildDaemonArgs({ ...options, watch: watchPath, vaultPath });
    const child = spawn(process.execPath, daemonArgs, {
      detached: true,
      stdio: "ignore"
    });
    child.unref();
    console.log(`Observer daemon started (pid: ${child.pid})`);
    return;
  }
  await watchSessions(observer, watchPath);
}
function registerObserveCommand(program) {
  program.command("observe").description("Observe session files and build observational memory").option("--watch <path>", "Watch session file or directory").option("--active", "Observe active OpenClaw sessions incrementally").option("--cron", "Run one-shot active observation for cron hooks").option("--agent <id>", "OpenClaw agent ID (default: OPENCLAW_AGENT_ID or clawdious)").option("--min-new <bytes>", "Override minimum new-content threshold in bytes").option("--sessions-dir <path>", "Override OpenClaw sessions directory").option("--dry-run", "Show active observation candidates without compressing").option("--threshold <n>", "Compression token threshold", "30000").option("--reflect-threshold <n>", "Reflection token threshold", "40000").option("--model <model>", "LLM model override").option("--extract-tasks", "Extract task-like observations into backlog", true).option("--no-extract-tasks", "Disable task extraction from observations").option("--compress <file>", "One-shot compression for a conversation file").option("--daemon", "Run in detached background mode").option("-v, --vault <path>", "Vault path").action(async (rawOptions) => {
    await observeCommand({
      watch: rawOptions.watch,
      active: rawOptions.active,
      cron: rawOptions.cron,
      agent: rawOptions.agent,
      minNew: rawOptions.minNew ? parsePositiveInteger(rawOptions.minNew, "min-new") : void 0,
      sessionsDir: rawOptions.sessionsDir,
      dryRun: rawOptions.dryRun,
      threshold: parsePositiveInteger(rawOptions.threshold, "threshold"),
      reflectThreshold: parsePositiveInteger(rawOptions.reflectThreshold, "reflect-threshold"),
      model: rawOptions.model,
      extractTasks: rawOptions.extractTasks,
      compress: rawOptions.compress,
      daemon: rawOptions.daemon,
      vaultPath: rawOptions.vault
    });
  });
}

export {
  SessionWatcher,
  observeCommand,
  registerObserveCommand
};
