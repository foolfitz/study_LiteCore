"use strict";

const instanceId = crypto.randomUUID();
const lifecycle = [{ event: "script-evaluated", at: Date.now() }];

function hex(bytes) {
  return [...new Uint8Array(bytes)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

async function sha256(buffer) {
  return hex(await crypto.subtle.digest("SHA-256", buffer));
}

async function verifiedResponse(item) {
  const response = await fetch(item.url, {
    cache: "no-store",
    credentials: "omit",
    mode: "cors",
  });
  if (!response.ok)
    throw new Error(`HTTP ${response.status} for ${item.role}`);
  const buffer = await response.arrayBuffer();
  const digest = await sha256(buffer);
  if (buffer.byteLength !== item.rawBytes)
    throw new Error(`size mismatch for ${item.role}: ${buffer.byteLength} != ${item.rawBytes}`);
  if (digest !== item.sha256)
    throw new Error(`SHA-256 mismatch for ${item.role}: ${digest}`);
  const headers = new Headers(response.headers);
  headers.set("X-OXSDK-R8-Verified-SHA256", digest);
  return {
    response: new Response(buffer, {
      status: response.status,
      statusText: response.statusText,
      headers,
    }),
    result: {
      role: item.role,
      url: item.url,
      bytes: buffer.byteLength,
      sha256: digest,
      contentType: response.headers.get("Content-Type") || "",
      contentEncoding: response.headers.get("Content-Encoding") || "identity",
    },
  };
}

async function cacheRoundtrip(payload) {
  const cache = await caches.open(payload.cacheName);
  const stored = [];
  for (const item of payload.artifacts) {
    const verified = await verifiedResponse(item);
    await cache.put(item.url, verified.response);
    stored.push(verified.result);
  }
  return { cacheName: payload.cacheName, stored };
}

async function verifyCache(payload) {
  const cache = await caches.open(payload.cacheName);
  const verified = [];
  for (const item of payload.artifacts) {
    const response = await cache.match(item.url);
    if (!response)
      throw new Error(`cache miss for ${item.role}`);
    const buffer = await response.arrayBuffer();
    const digest = await sha256(buffer);
    verified.push({
      role: item.role,
      url: item.url,
      bytes: buffer.byteLength,
      sha256: digest,
      pass: buffer.byteLength === item.rawBytes && digest === item.sha256,
    });
  }
  return {
    cacheName: payload.cacheName,
    verified,
    pass: verified.every((item) => item.pass),
  };
}

async function handleCommand(command, payload) {
  switch (command) {
    case "status":
      return {
        instanceId,
        lifecycle,
        cacheNames: await caches.keys(),
      };
    case "cache-roundtrip":
      return cacheRoundtrip(payload);
    case "verify-cache":
      return verifyCache(payload);
    case "clear-cache":
      return {
        cacheName: payload.cacheName,
        deleted: await caches.delete(payload.cacheName),
      };
    default:
      throw new Error(`unknown R8 discovery command: ${command}`);
  }
}

self.addEventListener("install", (event) => {
  lifecycle.push({ event: "install", at: Date.now() });
  event.waitUntil(Promise.resolve());
});

self.addEventListener("activate", (event) => {
  lifecycle.push({ event: "activate", at: Date.now() });
  event.waitUntil(Promise.resolve());
});

self.addEventListener("message", (event) => {
  const port = event.ports?.[0];
  if (!port)
    return;
  event.waitUntil((async () => {
    try {
      port.postMessage({
        ok: true,
        result: await handleCommand(event.data?.command, event.data?.payload || {}),
      });
    } catch (error) {
      port.postMessage({
        ok: false,
        error: {
          name: error?.name || "Error",
          message: String(error?.message || error),
        },
      });
    }
  })());
});
