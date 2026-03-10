import {
  WEBDAV_PREFIX,
  createWebDAVHandler
} from "./chunk-IVRIKYFE.js";

// src/lib/tailscale.ts
import { spawnSync, spawn } from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as http from "http";
import * as https from "https";
import * as crypto from "crypto";
var DEFAULT_SERVE_PORT = 8384;
var CLAWVAULT_SERVE_PATH = "/.clawvault";
var MANIFEST_ENDPOINT = "/.clawvault/manifest";
var SYNC_ENDPOINT = "/.clawvault/sync";
var FILE_ENDPOINT = "/.clawvault/files";
function hasTailscale() {
  const probe = spawnSync("tailscale", ["version"], {
    stdio: "pipe",
    encoding: "utf-8",
    timeout: 5e3
  });
  return !probe.error && probe.status === 0;
}
function getTailscaleVersion() {
  const result = spawnSync("tailscale", ["version"], {
    stdio: "pipe",
    encoding: "utf-8",
    timeout: 5e3
  });
  if (result.error || result.status !== 0) {
    return null;
  }
  const lines = result.stdout.trim().split("\n");
  return lines[0] || null;
}
function getTailscaleStatus() {
  const status = {
    installed: false,
    running: false,
    connected: false,
    peers: []
  };
  if (!hasTailscale()) {
    status.error = "Tailscale CLI not found. Install from https://tailscale.com/download";
    return status;
  }
  status.installed = true;
  const result = spawnSync("tailscale", ["status", "--json"], {
    stdio: "pipe",
    encoding: "utf-8",
    timeout: 1e4
  });
  if (result.error) {
    status.error = `Failed to get Tailscale status: ${result.error.message}`;
    return status;
  }
  if (result.status !== 0) {
    status.error = result.stderr?.trim() || "Tailscale daemon not running";
    return status;
  }
  try {
    const data = JSON.parse(result.stdout);
    status.running = true;
    status.backendState = data.BackendState;
    status.connected = data.BackendState === "Running";
    status.tailnetName = data.CurrentTailnet?.Name;
    if (data.Self) {
      status.selfIP = data.Self.TailscaleIPs?.[0];
      status.selfHostname = data.Self.HostName;
      status.selfDNSName = data.Self.DNSName;
    }
    if (data.Peer) {
      for (const [_, peerData] of Object.entries(data.Peer)) {
        const peer = {
          hostname: peerData.HostName || "",
          dnsName: peerData.DNSName || "",
          tailscaleIPs: peerData.TailscaleIPs || [],
          online: peerData.Online || false,
          os: peerData.OS,
          exitNode: peerData.ExitNode,
          tags: peerData.Tags,
          lastSeen: peerData.LastSeen
        };
        status.peers.push(peer);
      }
    }
  } catch (err) {
    status.error = `Failed to parse Tailscale status: ${err}`;
  }
  return status;
}
function findPeer(hostname) {
  const status = getTailscaleStatus();
  if (!status.connected) {
    return null;
  }
  const normalizedSearch = hostname.toLowerCase();
  let peer = status.peers.find(
    (p) => p.hostname.toLowerCase() === normalizedSearch
  );
  if (peer) return peer;
  peer = status.peers.find(
    (p) => p.dnsName.toLowerCase().startsWith(normalizedSearch)
  );
  if (peer) return peer;
  peer = status.peers.find(
    (p) => p.hostname.toLowerCase().includes(normalizedSearch)
  );
  return peer || null;
}
function getOnlinePeers() {
  const status = getTailscaleStatus();
  return status.peers.filter((p) => p.online);
}
function resolvePeerIP(hostname) {
  const peer = findPeer(hostname);
  return peer?.tailscaleIPs[0] || null;
}
function calculateChecksum(filePath) {
  const content = fs.readFileSync(filePath);
  return crypto.createHash("sha256").update(content).digest("hex");
}
function generateVaultManifest(vaultPath) {
  const configPath = path.join(vaultPath, ".clawvault.json");
  if (!fs.existsSync(configPath)) {
    throw new Error(`Not a ClawVault: ${vaultPath}`);
  }
  const config = JSON.parse(fs.readFileSync(configPath, "utf-8"));
  const files = [];
  function walkDir(dir, relativePath = "") {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      const relPath = path.join(relativePath, entry.name);
      if (entry.name.startsWith(".") && entry.name !== ".clawvault.json") {
        continue;
      }
      if (entry.name === "node_modules") {
        continue;
      }
      if (entry.isDirectory()) {
        walkDir(fullPath, relPath);
      } else if (entry.isFile() && (entry.name.endsWith(".md") || entry.name === ".clawvault.json")) {
        const stats = fs.statSync(fullPath);
        const category = relativePath.split(path.sep)[0] || "root";
        files.push({
          path: relPath,
          size: stats.size,
          modified: stats.mtime.toISOString(),
          checksum: calculateChecksum(fullPath),
          category
        });
      }
    }
  }
  walkDir(vaultPath);
  return {
    name: config.name,
    version: config.version || "1.0.0",
    lastUpdated: (/* @__PURE__ */ new Date()).toISOString(),
    files
  };
}
function compareManifests(local, remote) {
  const localFiles = new Map(local.files.map((f) => [f.path, f]));
  const remoteFiles = new Map(remote.files.map((f) => [f.path, f]));
  const toPush = [];
  const toPull = [];
  const conflicts = [];
  const unchanged = [];
  for (const [filePath, localFile] of localFiles) {
    const remoteFile = remoteFiles.get(filePath);
    if (!remoteFile) {
      toPush.push(localFile);
    } else if (localFile.checksum === remoteFile.checksum) {
      unchanged.push(filePath);
    } else {
      const localTime = new Date(localFile.modified).getTime();
      const remoteTime = new Date(remoteFile.modified).getTime();
      if (localTime > remoteTime) {
        toPush.push(localFile);
      } else if (remoteTime > localTime) {
        toPull.push(remoteFile);
      } else {
        conflicts.push({ path: filePath, local: localFile, remote: remoteFile });
      }
    }
  }
  for (const [filePath, remoteFile] of remoteFiles) {
    if (!localFiles.has(filePath)) {
      toPull.push(remoteFile);
    }
  }
  return { toPush, toPull, conflicts, unchanged };
}
function serveVault(vaultPath, options = {}) {
  const port = options.port || DEFAULT_SERVE_PORT;
  const pathPrefix = options.pathPrefix || CLAWVAULT_SERVE_PATH;
  if (!fs.existsSync(path.join(vaultPath, ".clawvault.json"))) {
    throw new Error(`Not a ClawVault: ${vaultPath}`);
  }
  const webdavHandler = createWebDAVHandler({
    rootPath: vaultPath,
    prefix: WEBDAV_PREFIX,
    auth: options.webdavAuth
  });
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url || "/", `http://localhost:${port}`);
    const pathname = url.pathname;
    if (pathname.startsWith(WEBDAV_PREFIX)) {
      try {
        const handled = await webdavHandler(req, res);
        if (handled) return;
      } catch (err) {
        res.writeHead(500, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
        res.end(`WebDAV Error: ${err}`);
        return;
      }
    }
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    if (req.method === "OPTIONS") {
      res.writeHead(200);
      res.end();
      return;
    }
    if (pathname === `${pathPrefix}/health`) {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok", vault: path.basename(vaultPath) }));
      return;
    }
    if (pathname === `${pathPrefix}/manifest`) {
      try {
        const manifest = generateVaultManifest(vaultPath);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify(manifest));
      } catch (err) {
        res.writeHead(500, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: String(err) }));
      }
      return;
    }
    if (pathname.startsWith(`${pathPrefix}/files/`)) {
      const relativePath = decodeURIComponent(pathname.slice(`${pathPrefix}/files/`.length));
      const filePath = path.join(vaultPath, relativePath);
      const resolvedPath = path.resolve(filePath);
      const resolvedVault = path.resolve(vaultPath);
      if (!resolvedPath.startsWith(resolvedVault)) {
        res.writeHead(403, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Access denied" }));
        return;
      }
      if (!fs.existsSync(filePath)) {
        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "File not found" }));
        return;
      }
      try {
        const content = fs.readFileSync(filePath, "utf-8");
        const stats = fs.statSync(filePath);
        res.writeHead(200, {
          "Content-Type": "text/markdown",
          "Content-Length": Buffer.byteLength(content),
          "Last-Modified": stats.mtime.toUTCString()
        });
        res.end(content);
      } catch (err) {
        res.writeHead(500, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: String(err) }));
      }
      return;
    }
    if (pathname.startsWith(`${pathPrefix}/upload/`) && req.method === "POST") {
      const relativePath = decodeURIComponent(pathname.slice(`${pathPrefix}/upload/`.length));
      const filePath = path.join(vaultPath, relativePath);
      const resolvedPath = path.resolve(filePath);
      const resolvedVault = path.resolve(vaultPath);
      if (!resolvedPath.startsWith(resolvedVault)) {
        res.writeHead(403, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Access denied" }));
        return;
      }
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
      });
      req.on("end", () => {
        try {
          const dir = path.dirname(filePath);
          if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
          }
          fs.writeFileSync(filePath, body, "utf-8");
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ success: true, path: relativePath }));
        } catch (err) {
          res.writeHead(500, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: String(err) }));
        }
      });
      return;
    }
    if (pathname === pathPrefix || pathname === `${pathPrefix}/`) {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({
        service: "clawvault-sync",
        version: "1.0.0",
        vault: path.basename(vaultPath),
        endpoints: {
          health: `${pathPrefix}/health`,
          manifest: `${pathPrefix}/manifest`,
          files: `${pathPrefix}/files/<path>`,
          upload: `${pathPrefix}/upload/<path>`,
          webdav: `${WEBDAV_PREFIX}/`
        }
      }));
      return;
    }
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Not found" }));
  });
  server.listen(port, "0.0.0.0");
  return {
    server,
    port,
    stop: () => new Promise((resolve2, reject) => {
      server.close((err) => {
        if (err) reject(err);
        else resolve2();
      });
    })
  };
}
async function fetchRemoteManifest(host, port = DEFAULT_SERVE_PORT, useHttps = false) {
  return new Promise((resolve2, reject) => {
    const protocol = useHttps ? https : http;
    const url = `${useHttps ? "https" : "http"}://${host}:${port}${CLAWVAULT_SERVE_PATH}/manifest`;
    const req = protocol.get(url, { timeout: 1e4 }, (res) => {
      let data = "";
      res.on("data", (chunk) => {
        data += chunk;
      });
      res.on("end", () => {
        if (res.statusCode !== 200) {
          reject(new Error(`Failed to fetch manifest: HTTP ${res.statusCode}`));
          return;
        }
        try {
          resolve2(JSON.parse(data));
        } catch (err) {
          reject(new Error(`Invalid manifest response: ${err}`));
        }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Request timed out"));
    });
  });
}
async function fetchRemoteFile(host, filePath, port = DEFAULT_SERVE_PORT, useHttps = false) {
  return new Promise((resolve2, reject) => {
    const protocol = useHttps ? https : http;
    const encodedPath = encodeURIComponent(filePath).replace(/%2F/g, "/");
    const url = `${useHttps ? "https" : "http"}://${host}:${port}${CLAWVAULT_SERVE_PATH}/files/${encodedPath}`;
    const req = protocol.get(url, { timeout: 3e4 }, (res) => {
      let data = "";
      res.on("data", (chunk) => {
        data += chunk;
      });
      res.on("end", () => {
        if (res.statusCode !== 200) {
          reject(new Error(`Failed to fetch file: HTTP ${res.statusCode}`));
          return;
        }
        resolve2(data);
      });
    });
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Request timed out"));
    });
  });
}
async function pushFileToRemote(host, filePath, content, port = DEFAULT_SERVE_PORT, useHttps = false) {
  return new Promise((resolve2, reject) => {
    const protocol = useHttps ? https : http;
    const encodedPath = encodeURIComponent(filePath).replace(/%2F/g, "/");
    const url = new URL(`${useHttps ? "https" : "http"}://${host}:${port}${CLAWVAULT_SERVE_PATH}/upload/${encodedPath}`);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname,
      method: "POST",
      headers: {
        "Content-Type": "text/markdown",
        "Content-Length": Buffer.byteLength(content)
      },
      timeout: 3e4
    };
    const req = protocol.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => {
        data += chunk;
      });
      res.on("end", () => {
        if (res.statusCode !== 200) {
          reject(new Error(`Failed to push file: HTTP ${res.statusCode}`));
          return;
        }
        resolve2();
      });
    });
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("Request timed out"));
    });
    req.write(content);
    req.end();
  });
}
async function syncWithPeer(vaultPath, options) {
  const startTime = Date.now();
  const result = {
    pushed: [],
    pulled: [],
    deleted: [],
    unchanged: [],
    errors: [],
    stats: {
      bytesTransferred: 0,
      filesProcessed: 0,
      duration: 0
    }
  };
  const {
    peer,
    port = DEFAULT_SERVE_PORT,
    direction = "bidirectional",
    dryRun = false,
    deleteOrphans = false,
    categories,
    https: useHttps = false
  } = options;
  let host = peer;
  if (!peer.match(/^\d+\.\d+\.\d+\.\d+$/)) {
    const resolvedIP = resolvePeerIP(peer);
    if (!resolvedIP) {
      result.errors.push(`Could not resolve peer: ${peer}`);
      result.stats.duration = Date.now() - startTime;
      return result;
    }
    host = resolvedIP;
  }
  try {
    const localManifest = generateVaultManifest(vaultPath);
    const remoteManifest = await fetchRemoteManifest(host, port, useHttps);
    let { toPush, toPull, conflicts, unchanged } = compareManifests(localManifest, remoteManifest);
    if (categories && categories.length > 0) {
      const categorySet = new Set(categories);
      toPush = toPush.filter((f) => categorySet.has(f.category));
      toPull = toPull.filter((f) => categorySet.has(f.category));
    }
    result.unchanged = unchanged;
    for (const conflict of conflicts) {
      result.errors.push(`Conflict: ${conflict.path} (local and remote have same timestamp but different content)`);
    }
    if (direction === "push" || direction === "bidirectional") {
      for (const file of toPush) {
        try {
          if (!dryRun) {
            const content = fs.readFileSync(path.join(vaultPath, file.path), "utf-8");
            await pushFileToRemote(host, file.path, content, port, useHttps);
            result.stats.bytesTransferred += file.size;
          }
          result.pushed.push(file.path);
          result.stats.filesProcessed++;
        } catch (err) {
          result.errors.push(`Failed to push ${file.path}: ${err}`);
        }
      }
    }
    if (direction === "pull" || direction === "bidirectional") {
      for (const file of toPull) {
        try {
          if (!dryRun) {
            const content = await fetchRemoteFile(host, file.path, port, useHttps);
            const filePath = path.join(vaultPath, file.path);
            const dir = path.dirname(filePath);
            if (!fs.existsSync(dir)) {
              fs.mkdirSync(dir, { recursive: true });
            }
            fs.writeFileSync(filePath, content, "utf-8");
            result.stats.bytesTransferred += file.size;
          }
          result.pulled.push(file.path);
          result.stats.filesProcessed++;
        } catch (err) {
          result.errors.push(`Failed to pull ${file.path}: ${err}`);
        }
      }
    }
    if (deleteOrphans && direction === "pull") {
      const remoteFiles = new Set(remoteManifest.files.map((f) => f.path));
      for (const file of localManifest.files) {
        if (!remoteFiles.has(file.path)) {
          if (!categories || categories.includes(file.category)) {
            try {
              if (!dryRun) {
                fs.unlinkSync(path.join(vaultPath, file.path));
              }
              result.deleted.push(file.path);
            } catch (err) {
              result.errors.push(`Failed to delete ${file.path}: ${err}`);
            }
          }
        }
      }
    }
  } catch (err) {
    result.errors.push(`Sync failed: ${err}`);
  }
  result.stats.duration = Date.now() - startTime;
  return result;
}
function configureTailscaleServe(localPort, options = {}) {
  if (!hasTailscale()) {
    return null;
  }
  const args = ["serve"];
  if (options.funnel) {
    args.push("--bg");
    args.push("funnel");
  } else if (options.background) {
    args.push("--bg");
  }
  args.push(`localhost:${localPort}`);
  const proc = spawn("tailscale", args, {
    stdio: "inherit",
    detached: options.background
  });
  if (options.background) {
    proc.unref();
  }
  return proc;
}
function stopTailscaleServe() {
  if (!hasTailscale()) {
    return false;
  }
  const result = spawnSync("tailscale", ["serve", "off"], {
    stdio: "pipe",
    encoding: "utf-8",
    timeout: 5e3
  });
  return result.status === 0;
}
async function checkPeerClawVault(host, port = DEFAULT_SERVE_PORT) {
  try {
    const response = await new Promise((resolve2) => {
      const req = http.get(
        `http://${host}:${port}${CLAWVAULT_SERVE_PATH}/health`,
        { timeout: 5e3 },
        (res) => {
          resolve2(res.statusCode === 200);
        }
      );
      req.on("error", () => resolve2(false));
      req.on("timeout", () => {
        req.destroy();
        resolve2(false);
      });
    });
    return response;
  } catch {
    return false;
  }
}
async function discoverClawVaultPeers(port = DEFAULT_SERVE_PORT) {
  const status = getTailscaleStatus();
  if (!status.connected) {
    return [];
  }
  const clawvaultPeers = [];
  const checkPromises = status.peers.filter((p) => p.online).map(async (peer) => {
    const ip = peer.tailscaleIPs[0];
    if (!ip) return;
    const isServing = await checkPeerClawVault(ip, port);
    if (isServing) {
      peer.clawvaultServing = true;
      peer.clawvaultPort = port;
      clawvaultPeers.push(peer);
    }
  });
  await Promise.all(checkPromises);
  return clawvaultPeers;
}

export {
  DEFAULT_SERVE_PORT,
  CLAWVAULT_SERVE_PATH,
  MANIFEST_ENDPOINT,
  SYNC_ENDPOINT,
  FILE_ENDPOINT,
  hasTailscale,
  getTailscaleVersion,
  getTailscaleStatus,
  findPeer,
  getOnlinePeers,
  resolvePeerIP,
  generateVaultManifest,
  compareManifests,
  serveVault,
  fetchRemoteManifest,
  fetchRemoteFile,
  pushFileToRemote,
  syncWithPeer,
  configureTailscaleServe,
  stopTailscaleServe,
  checkPeerClawVault,
  discoverClawVaultPeers
};
