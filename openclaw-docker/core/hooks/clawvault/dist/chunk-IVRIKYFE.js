// src/lib/webdav.ts
import * as fs from "fs";
import * as path from "path";
var WEBDAV_PREFIX = "/webdav";
var BLOCKED_PATHS = [
  ".clawvault",
  ".git",
  ".obsidian",
  "node_modules"
];
var SUPPORTED_METHODS = ["GET", "PUT", "DELETE", "MKCOL", "PROPFIND", "OPTIONS", "HEAD", "MOVE", "COPY"];
function toRequestSegments(requestPath) {
  return requestPath.replace(/\\/g, "/").split("/").filter(Boolean);
}
function isWithinRoot(fullPath, rootPath) {
  const resolvedRoot = path.resolve(rootPath);
  const relative2 = path.relative(resolvedRoot, fullPath);
  return !(relative2.startsWith("..") || path.isAbsolute(relative2));
}
function isPathSafe(requestPath, rootPath) {
  const pathParts = toRequestSegments(requestPath);
  if (pathParts.includes("..")) {
    return false;
  }
  const normalizedRelativePath = path.normalize(pathParts.join(path.sep));
  const fullPath = path.resolve(rootPath, normalizedRelativePath);
  if (!isWithinRoot(fullPath, rootPath)) {
    return false;
  }
  for (const part of pathParts) {
    if (BLOCKED_PATHS.includes(part)) {
      return false;
    }
  }
  return true;
}
function resolveWebDAVPath(requestPath, rootPath) {
  const pathParts = toRequestSegments(requestPath);
  if (pathParts.includes("..")) {
    return null;
  }
  const normalizedRelativePath = path.normalize(pathParts.join(path.sep));
  const fullPath = path.resolve(rootPath, normalizedRelativePath);
  if (!isWithinRoot(fullPath, rootPath)) {
    return null;
  }
  return fullPath;
}
function checkAuth(req, auth) {
  if (!auth) {
    return true;
  }
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith("Basic ")) {
    return false;
  }
  const base64Credentials = authHeader.slice(6);
  const credentials = Buffer.from(base64Credentials, "base64").toString("utf-8");
  const [username, password] = credentials.split(":");
  return username === auth.username && password === auth.password;
}
function escapeXml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
}
function formatWebDAVDate(date) {
  return date.toUTCString();
}
function generatePropfindEntry(href, stats, isCollection) {
  const resourceType = isCollection ? "<D:resourcetype><D:collection/></D:resourcetype>" : "<D:resourcetype/>";
  const contentLength = stats && !isCollection ? `<D:getcontentlength>${stats.size}</D:getcontentlength>` : "";
  const lastModified = stats ? `<D:getlastmodified>${formatWebDAVDate(stats.mtime)}</D:getlastmodified>` : "";
  const etag = stats ? `<D:getetag>"${stats.mtime.getTime().toString(16)}-${stats.size.toString(16)}"</D:getetag>` : "";
  const contentType = !isCollection ? "<D:getcontenttype>application/octet-stream</D:getcontenttype>" : "";
  return `  <D:response>
    <D:href>${escapeXml(href)}</D:href>
    <D:propstat>
      <D:prop>
        ${resourceType}
        ${contentLength}
        ${lastModified}
        ${etag}
        ${contentType}
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>`;
}
function generatePropfindResponse(entries) {
  const responseEntries = entries.map(
    (e) => generatePropfindEntry(e.href, e.stats, e.isCollection)
  ).join("\n");
  return `<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:">
${responseEntries}
</D:multistatus>`;
}
function handleOptions(res, prefix) {
  res.writeHead(200, {
    "Allow": SUPPORTED_METHODS.join(", "),
    "DAV": "1, 2",
    "Content-Length": "0",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": SUPPORTED_METHODS.join(", "),
    "Access-Control-Allow-Headers": "Content-Type, Depth, Destination, Overwrite, Authorization",
    "MS-Author-Via": "DAV"
  });
  res.end();
}
function handleHead(res, filePath) {
  try {
    const stats = fs.statSync(filePath);
    if (stats.isDirectory()) {
      res.writeHead(200, {
        "Content-Type": "httpd/unix-directory",
        "Last-Modified": formatWebDAVDate(stats.mtime),
        "ETag": `"${stats.mtime.getTime().toString(16)}"`,
        "Access-Control-Allow-Origin": "*"
      });
    } else {
      res.writeHead(200, {
        "Content-Type": "application/octet-stream",
        "Content-Length": stats.size.toString(),
        "Last-Modified": formatWebDAVDate(stats.mtime),
        "ETag": `"${stats.mtime.getTime().toString(16)}-${stats.size.toString(16)}"`,
        "Access-Control-Allow-Origin": "*"
      });
    }
    res.end();
  } catch (err) {
    res.writeHead(404, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end("Not Found");
  }
}
function handleGet(res, filePath) {
  try {
    const stats = fs.statSync(filePath);
    if (stats.isDirectory()) {
      const entries = fs.readdirSync(filePath);
      const listing = entries.join("\n");
      res.writeHead(200, {
        "Content-Type": "text/plain",
        "Content-Length": Buffer.byteLength(listing).toString(),
        "Access-Control-Allow-Origin": "*"
      });
      res.end(listing);
    } else {
      const content = fs.readFileSync(filePath);
      res.writeHead(200, {
        "Content-Type": "application/octet-stream",
        "Content-Length": content.length.toString(),
        "Last-Modified": formatWebDAVDate(stats.mtime),
        "ETag": `"${stats.mtime.getTime().toString(16)}-${stats.size.toString(16)}"`,
        "Access-Control-Allow-Origin": "*"
      });
      res.end(content);
    }
  } catch (err) {
    res.writeHead(404, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end("Not Found");
  }
}
function handlePut(res, filePath, body) {
  try {
    const exists = fs.existsSync(filePath);
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(filePath, body);
    const status = exists ? 204 : 201;
    res.writeHead(status, {
      "Content-Length": "0",
      "Access-Control-Allow-Origin": "*"
    });
    res.end();
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end(`Error: ${err}`);
  }
}
function handleDelete(res, filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      res.writeHead(404, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Not Found");
      return;
    }
    const stats = fs.statSync(filePath);
    if (stats.isDirectory()) {
      fs.rmSync(filePath, { recursive: true });
    } else {
      fs.unlinkSync(filePath);
    }
    res.writeHead(204, {
      "Content-Length": "0",
      "Access-Control-Allow-Origin": "*"
    });
    res.end();
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end(`Error: ${err}`);
  }
}
function handleMkcol(res, filePath) {
  try {
    if (fs.existsSync(filePath)) {
      res.writeHead(405, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Resource already exists");
      return;
    }
    const parent = path.dirname(filePath);
    if (!fs.existsSync(parent)) {
      res.writeHead(409, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Parent directory does not exist");
      return;
    }
    fs.mkdirSync(filePath);
    res.writeHead(201, {
      "Content-Length": "0",
      "Access-Control-Allow-Origin": "*"
    });
    res.end();
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end(`Error: ${err}`);
  }
}
function handlePropfind(res, filePath, webdavPath, prefix, depth) {
  try {
    if (!fs.existsSync(filePath)) {
      res.writeHead(404, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Not Found");
      return;
    }
    const stats = fs.statSync(filePath);
    const entries = [];
    const normalizedWebdavPath = webdavPath.startsWith("/") ? webdavPath : "/" + webdavPath;
    const href = prefix + normalizedWebdavPath;
    entries.push({
      href: href.endsWith("/") || stats.isDirectory() ? href : href,
      stats,
      isCollection: stats.isDirectory()
    });
    if (stats.isDirectory() && depth !== "0") {
      try {
        const children = fs.readdirSync(filePath);
        for (const child of children) {
          if (BLOCKED_PATHS.includes(child)) {
            continue;
          }
          const childPath = path.join(filePath, child);
          const childWebdavPath = normalizedWebdavPath.endsWith("/") ? normalizedWebdavPath + child : normalizedWebdavPath + "/" + child;
          try {
            const childStats = fs.statSync(childPath);
            entries.push({
              href: prefix + childWebdavPath,
              stats: childStats,
              isCollection: childStats.isDirectory()
            });
          } catch {
          }
        }
      } catch {
      }
    }
    const xml = generatePropfindResponse(entries);
    res.writeHead(207, {
      "Content-Type": "application/xml; charset=utf-8",
      "Content-Length": Buffer.byteLength(xml).toString(),
      "Access-Control-Allow-Origin": "*"
    });
    res.end(xml);
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end(`Error: ${err}`);
  }
}
function handleMove(res, sourcePath, destinationPath, overwrite) {
  try {
    if (!fs.existsSync(sourcePath)) {
      res.writeHead(404, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Source not found");
      return;
    }
    if (!destinationPath) {
      res.writeHead(400, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Destination header required");
      return;
    }
    const destExists = fs.existsSync(destinationPath);
    if (destExists && !overwrite) {
      res.writeHead(412, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Destination exists and Overwrite is F");
      return;
    }
    const destDir = path.dirname(destinationPath);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }
    if (destExists) {
      const destStats = fs.statSync(destinationPath);
      if (destStats.isDirectory()) {
        fs.rmSync(destinationPath, { recursive: true });
      } else {
        fs.unlinkSync(destinationPath);
      }
    }
    fs.renameSync(sourcePath, destinationPath);
    const status = destExists ? 204 : 201;
    res.writeHead(status, {
      "Content-Length": "0",
      "Access-Control-Allow-Origin": "*"
    });
    res.end();
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end(`Error: ${err}`);
  }
}
function handleCopy(res, sourcePath, destinationPath, overwrite) {
  try {
    if (!fs.existsSync(sourcePath)) {
      res.writeHead(404, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Source not found");
      return;
    }
    if (!destinationPath) {
      res.writeHead(400, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Destination header required");
      return;
    }
    const destExists = fs.existsSync(destinationPath);
    if (destExists && !overwrite) {
      res.writeHead(412, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Destination exists and Overwrite is F");
      return;
    }
    const destDir = path.dirname(destinationPath);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }
    const sourceStats = fs.statSync(sourcePath);
    if (sourceStats.isDirectory()) {
      copyDirRecursive(sourcePath, destinationPath);
    } else {
      fs.copyFileSync(sourcePath, destinationPath);
    }
    const status = destExists ? 204 : 201;
    res.writeHead(status, {
      "Content-Length": "0",
      "Access-Control-Allow-Origin": "*"
    });
    res.end();
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
    res.end(`Error: ${err}`);
  }
}
function copyDirRecursive(src, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}
function parseDestinationHeader(destinationHeader, prefix, rootPath) {
  if (!destinationHeader) {
    return null;
  }
  try {
    let destPath;
    if (destinationHeader.startsWith("http://") || destinationHeader.startsWith("https://")) {
      const url = new URL(destinationHeader);
      destPath = decodeURIComponent(url.pathname);
    } else {
      destPath = decodeURIComponent(destinationHeader);
    }
    if (destPath.startsWith(prefix)) {
      destPath = destPath.slice(prefix.length);
    }
    return resolveWebDAVPath(destPath, rootPath);
  } catch {
    return null;
  }
}
function createWebDAVHandler(config) {
  const { rootPath, prefix = WEBDAV_PREFIX, auth } = config;
  return async (req, res) => {
    const rawUrl = req.url || "/";
    if (rawUrl.includes("..")) {
      if (rawUrl.startsWith(prefix)) {
        res.writeHead(403, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
        res.end("Forbidden");
        return true;
      }
    }
    const url = new URL(rawUrl, `http://${req.headers.host || "localhost"}`);
    const pathname = decodeURIComponent(url.pathname);
    if (!pathname.startsWith(prefix)) {
      return false;
    }
    let webdavPath = pathname.slice(prefix.length);
    if (!webdavPath.startsWith("/")) {
      webdavPath = "/" + webdavPath;
    }
    if (req.method === "OPTIONS") {
      handleOptions(res, prefix);
      return true;
    }
    if (!checkAuth(req, auth)) {
      res.writeHead(401, {
        "WWW-Authenticate": 'Basic realm="ClawVault WebDAV"',
        "Content-Type": "text/plain",
        "Access-Control-Allow-Origin": "*"
      });
      res.end("Unauthorized");
      return true;
    }
    if (!isPathSafe(webdavPath, rootPath)) {
      res.writeHead(403, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Forbidden");
      return true;
    }
    const filePath = resolveWebDAVPath(webdavPath, rootPath);
    if (!filePath) {
      res.writeHead(403, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
      res.end("Forbidden");
      return true;
    }
    const depth = req.headers.depth || "infinity";
    const overwrite = req.headers.overwrite?.toUpperCase() !== "F";
    const destinationHeader = req.headers.destination;
    switch (req.method) {
      case "HEAD":
        handleHead(res, filePath);
        return true;
      case "GET":
        handleGet(res, filePath);
        return true;
      case "PUT": {
        const chunks = [];
        for await (const chunk of req) {
          chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
        }
        const body = Buffer.concat(chunks);
        handlePut(res, filePath, body);
        return true;
      }
      case "DELETE":
        handleDelete(res, filePath);
        return true;
      case "MKCOL":
        handleMkcol(res, filePath);
        return true;
      case "PROPFIND":
        handlePropfind(res, filePath, webdavPath, prefix, depth);
        return true;
      case "MOVE": {
        const destPath = parseDestinationHeader(destinationHeader, prefix, rootPath);
        if (destPath && destinationHeader) {
          const destWebdavPath = destinationHeader.includes(prefix) ? destinationHeader.slice(destinationHeader.indexOf(prefix) + prefix.length) : destinationHeader;
          if (!isPathSafe(destWebdavPath, rootPath)) {
            res.writeHead(403, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
            res.end("Forbidden");
            return true;
          }
        }
        handleMove(res, filePath, destPath, overwrite);
        return true;
      }
      case "COPY": {
        const destPath = parseDestinationHeader(destinationHeader, prefix, rootPath);
        if (destPath && destinationHeader) {
          const destWebdavPath = destinationHeader.includes(prefix) ? destinationHeader.slice(destinationHeader.indexOf(prefix) + prefix.length) : destinationHeader;
          if (!isPathSafe(destWebdavPath, rootPath)) {
            res.writeHead(403, { "Content-Type": "text/plain", "Access-Control-Allow-Origin": "*" });
            res.end("Forbidden");
            return true;
          }
        }
        handleCopy(res, filePath, destPath, overwrite);
        return true;
      }
      default:
        res.writeHead(405, {
          "Allow": SUPPORTED_METHODS.join(", "),
          "Content-Type": "text/plain",
          "Access-Control-Allow-Origin": "*"
        });
        res.end("Method Not Allowed");
        return true;
    }
  };
}

export {
  WEBDAV_PREFIX,
  isPathSafe,
  resolveWebDAVPath,
  checkAuth,
  generatePropfindResponse,
  handleOptions,
  handleHead,
  handleGet,
  handlePut,
  handleDelete,
  handleMkcol,
  handlePropfind,
  handleMove,
  handleCopy,
  createWebDAVHandler
};
