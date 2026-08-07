#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { DeterministicClock } from "../collaboration/domain.js";
import { startReferenceService } from "../collaboration/reference-service.js";

function option(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

const project = resolve(new URL("..", import.meta.url).pathname);
const fixture = JSON.parse(await readFile(
  resolve(project, "collaboration/fixtures/canonical.json"), "utf8",
));
const fixtures = {
  "t1-plain-zh.odt": await readFile(resolve(project, "test-docs/t1-plain-zh.odt")),
  "t3-long.odt": await readFile(resolve(project, "test-docs/t3-long.odt")),
};
const service = await startReferenceService({
  fixture,
  initialBytes: fixtures["t1-plain-zh.odt"],
  documentFixtures: fixtures,
  clock: new DeterministicClock(),
  port: Number(option("--port", 0)),
  staticRoot: resolve(project, "dist"),
});

console.log(JSON.stringify({ ready: true, url: service.url, pid: process.pid }));

let closing = false;
async function close() {
  if (closing)
    return;
  closing = true;
  await service.close();
}
process.on("SIGTERM", () => close().finally(() => process.exit(0)));
process.on("SIGINT", () => close().finally(() => process.exit(0)));
