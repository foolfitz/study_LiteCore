import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";

import {
  COLLABORATION_CONTRACT_VERSION,
  CollaborationError,
  assertContractVersion,
  publicError,
} from "./contract.js";
import { CollaborationDomain } from "./domain.js";

const STATUS_BY_CODE = {
  INVALID_ARGUMENT: 400,
  CONTRACT_VERSION_MISMATCH: 400,
  HASH_MISMATCH: 400,
  NOT_FOUND: 404,
  VERSION_CONFLICT: 409,
  LEASE_HELD: 409,
  LEASE_EXPIRED: 409,
  INVALID_LEASE: 403,
  IDEMPOTENCY_CONFLICT: 409,
  EVENT_GAP: 409,
  FAULT_INJECTED: 503,
  RESPONSE_INTERRUPTED: 503,
};

const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".wasm": "application/wasm",
  ".data": "application/octet-stream",
  ".odt": "application/vnd.oasis.opendocument.text",
  ".png": "image/png",
};

function commonHeaders(response) {
  response.setHeader("Cross-Origin-Opener-Policy", "same-origin");
  response.setHeader("Cross-Origin-Embedder-Policy", "require-corp");
  response.setHeader("Cross-Origin-Resource-Policy", "same-origin");
  response.setHeader("Cache-Control", "no-store");
}

function sendJson(response, status, payload, headers = {}) {
  commonHeaders(response);
  response.writeHead(status, { "content-type": "application/json; charset=utf-8", ...headers });
  response.end(`${JSON.stringify(payload)}\n`);
}

async function readBody(request, maximumBytes) {
  const chunks = [];
  let total = 0;
  let exceeded = false;
  for await (const chunk of request) {
    total += chunk.byteLength;
    if (total > maximumBytes) {
      exceeded = true;
    } else {
      chunks.push(chunk);
    }
  }
  if (exceeded)
    throw new CollaborationError("INVALID_ARGUMENT", "request body exceeds configured limit");
  return Buffer.concat(chunks);
}

async function readJson(request, maximumBytes) {
  const body = await readBody(request, maximumBytes);
  try {
    return JSON.parse(body.toString("utf8"));
  } catch {
    throw new CollaborationError("INVALID_ARGUMENT", "request body is not valid JSON");
  }
}

function decode(segment) {
  try {
    return decodeURIComponent(segment);
  } catch {
    throw new CollaborationError("INVALID_ARGUMENT", "invalid URL encoding");
  }
}

function header(request, name, required = true) {
  const value = request.headers[name];
  if (required && (typeof value !== "string" || value.length === 0))
    throw new CollaborationError("INVALID_ARGUMENT", `missing ${name} header`);
  return value;
}

async function serveStatic(response, staticRoot, pathname) {
  if (!staticRoot)
    return false;
  const relative = pathname === "/" ? "r6-reference.html" : pathname.replace(/^\/+/, "");
  const root = resolve(staticRoot);
  const target = resolve(root, relative);
  if (target !== root && !target.startsWith(`${root}${sep}`))
    throw new CollaborationError("NOT_FOUND", "static path is outside the application root");
  try {
    const bytes = await readFile(target);
    commonHeaders(response);
    response.writeHead(200, { "content-type": CONTENT_TYPES[extname(target)] || "application/octet-stream" });
    response.end(bytes);
    return true;
  } catch (error) {
    if (error?.code === "ENOENT")
      return false;
    throw error;
  }
}

export async function startReferenceService(options) {
  const domain = options?.domain || new CollaborationDomain({
    fixture: options.fixture,
    initialBytes: options.initialBytes,
    clock: options.clock,
  });
  const fixture = domain.fixture;
  const server = createServer(async (request, response) => {
    const url = new URL(request.url, "http://127.0.0.1");
    const pathname = url.pathname;
    let context = {};
    try {
      let match;
      if (request.method === "POST" && pathname === "/__test/reset") {
        const body = await readJson(request, fixture.limits.jsonBytes);
        const { fixtureName, ...resetOptions } = body;
        let replacementBytes = null;
        if (fixtureName !== undefined) {
          replacementBytes = options.documentFixtures?.[fixtureName];
          if (!replacementBytes)
            throw new CollaborationError("INVALID_ARGUMENT", "unknown reset fixture", { fixtureName });
        }
        return sendJson(response, 200, domain.reset(resetOptions, replacementBytes));
      }
      if (request.method === "POST" && pathname === "/__test/clock") {
        const body = await readJson(request, fixture.limits.jsonBytes);
        return sendJson(response, 200, domain.advanceClock(body.milliseconds));
      }
      if (request.method === "POST" && pathname === "/__test/fault") {
        const body = await readJson(request, fixture.limits.jsonBytes);
        domain.armFault(body.phase);
        return sendJson(response, 200, { armed: body.phase });
      }
      if (request.method === "GET" && (match = pathname.match(/^\/__test\/state\/([^/]+)$/))) {
        const documentId = decode(match[1]);
        context = { documentId };
        return sendJson(response, 200, domain.debugState(documentId));
      }
      if (request.method === "GET" && (match = pathname.match(/^\/api\/documents\/([^/]+)$/))) {
        const documentId = decode(match[1]);
        context = { documentId };
        const result = domain.getDocument(documentId);
        return sendJson(response, 200, result, { ETag: result.data.current.etag });
      }
      if (request.method === "GET" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/versions\/([^/]+)\/blob$/))) {
        const documentId = decode(match[1]);
        const version = decode(match[2]);
        context = { documentId };
        const result = domain.getBlob(documentId, version);
        commonHeaders(response);
        response.writeHead(200, {
          "content-type": result.metadata.mediaType,
          "content-length": result.bytes.byteLength,
          ETag: result.metadata.etag,
          "x-blob-sha256": result.metadata.blobSha256,
          "x-document-version": result.metadata.version,
        });
        response.end(result.bytes);
        return;
      }
      if (request.method === "GET" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/collaboration$/))) {
        const documentId = decode(match[1]);
        context = { documentId };
        return sendJson(response, 200, domain.collaborationSnapshot(documentId));
      }
      if (request.method === "GET" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/events$/))) {
        const documentId = decode(match[1]);
        context = { documentId };
        const last = Number(url.searchParams.get("lastEventSequence") || 0);
        const result = domain.eventsSince(documentId, last);
        if ((request.headers.accept || "").includes("text/event-stream")) {
          commonHeaders(response);
          response.writeHead(200, { "content-type": "text/event-stream; charset=utf-8" });
          const events = result.data.events || [result.data.event];
          for (const event of events)
            response.write(`id: ${event.eventSequence}\nevent: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`);
          response.end();
          return;
        }
        return sendJson(response, 200, result);
      }
      if (request.method === "POST" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/presence$/))) {
        const documentId = decode(match[1]);
        const body = await readJson(request, fixture.limits.jsonBytes);
        context = { documentId, requestId: body.requestId };
        return sendJson(response, 200, domain.heartbeat(documentId, body));
      }
      if (request.method === "POST" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/comments$/))) {
        const documentId = decode(match[1]);
        const body = await readJson(request, fixture.limits.jsonBytes);
        context = { documentId, requestId: body.requestId };
        return sendJson(response, 201, domain.createComment(documentId, body));
      }
      if (request.method === "POST" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/comments\/([^/]+)\/resolve$/))) {
        const documentId = decode(match[1]);
        const commentId = decode(match[2]);
        const body = await readJson(request, fixture.limits.jsonBytes);
        context = { documentId, requestId: body.requestId };
        return sendJson(response, 200, domain.resolveComment(documentId, commentId, body));
      }
      if (request.method === "POST" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/suggestions$/))) {
        const documentId = decode(match[1]);
        const body = await readJson(request, fixture.limits.jsonBytes);
        context = { documentId, requestId: body.requestId };
        return sendJson(response, 201, domain.createSuggestion(documentId, body));
      }
      if (request.method === "POST" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/mutations$/))) {
        const documentId = decode(match[1]);
        const body = await readJson(request, fixture.limits.jsonBytes);
        context = { documentId, requestId: body.requestId };
        assertContractVersion(body.contractVersion);
        throw new CollaborationError("INVALID_ARGUMENT", "unknown mutation kind", { kind: body.kind });
      }
      if (request.method === "POST" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/suggestions\/([^/]+)\/decision$/))) {
        const documentId = decode(match[1]);
        const suggestionId = decode(match[2]);
        const body = await readJson(request, fixture.limits.jsonBytes);
        context = { documentId, requestId: body.requestId };
        return sendJson(response, 200, domain.decideSuggestion(documentId, suggestionId, body));
      }
      if (request.method === "POST" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/lease$/))) {
        const documentId = decode(match[1]);
        const body = await readJson(request, fixture.limits.jsonBytes);
        context = { documentId, requestId: body.requestId };
        return sendJson(response, 201, domain.acquireLease(documentId, body));
      }
      if (request.method === "POST" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/lease\/([^/]+)\/renew$/))) {
        const documentId = decode(match[1]);
        const leaseId = decode(match[2]);
        const body = await readJson(request, fixture.limits.jsonBytes);
        context = { documentId, requestId: body.requestId };
        return sendJson(response, 200, domain.renewLease(documentId, leaseId, body));
      }
      if (request.method === "DELETE" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/lease\/([^/]+)$/))) {
        const documentId = decode(match[1]);
        const leaseId = decode(match[2]);
        const body = await readJson(request, fixture.limits.jsonBytes);
        context = { documentId, requestId: body.requestId };
        return sendJson(response, 200, domain.releaseLease(documentId, leaseId, body));
      }
      if (request.method === "PUT" && (match = pathname.match(/^\/api\/documents\/([^/]+)\/blob$/))) {
        const documentId = decode(match[1]);
        const body = await readBody(request, fixture.limits.blobBytes);
        const mutation = {
          contractVersion: header(request, "x-contract-version") || COLLABORATION_CONTRACT_VERSION,
          requestId: header(request, "x-request-id"),
          baseVersion: header(request, "x-base-version"),
          ifMatch: header(request, "if-match"),
          leaseId: header(request, "x-lease-id"),
          token: header(request, "x-lease-token"),
          blobSha256: header(request, "x-blob-sha256"),
          createdBy: header(request, "x-created-by"),
          ...(header(request, "x-suggestion-id", false)
            ? { suggestionId: header(request, "x-suggestion-id", false) }
            : {}),
        };
        context = { documentId, requestId: mutation.requestId };
        return sendJson(response, 201, domain.putBlob(documentId, mutation, body));
      }
      if (request.method === "GET" && await serveStatic(response, options.staticRoot, pathname))
        return;
      throw new CollaborationError("NOT_FOUND", "route not found", { method: request.method, pathname });
    } catch (error) {
      let snapshotVersion = 0;
      let eventSequence = 0;
      if (context.documentId && domain.documents.has(context.documentId)) {
        const state = domain.debugState(context.documentId);
        snapshotVersion = state.versionCount;
        eventSequence = state.eventSequence;
      }
      const payload = publicError(error, { ...context, snapshotVersion, eventSequence });
      sendJson(response, STATUS_BY_CODE[payload.error.code] || 500, payload);
    }
  });
  await new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(options?.port ?? 0, "127.0.0.1", resolveListen);
  });
  const address = server.address();
  return {
    domain,
    server,
    port: address.port,
    url: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolveClose, reject) =>
      server.close((error) => error ? reject(error) : resolveClose())),
  };
}
