import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { CollaborationClient } from "../collaboration-client.js";
import { createDomainAdapter, runConformance } from "../conformance.js";
import { CollaborationDomain, DeterministicClock } from "../domain.js";
import { startReferenceService } from "../reference-service.js";

const fixture = JSON.parse(await readFile(new URL("../fixtures/canonical.json", import.meta.url), "utf8"));
const initialBytes = await readFile(new URL("../../test-docs/t1-plain-zh.odt", import.meta.url));

test("all 12 R6-B scenarios pass through the pure domain adapter", async () => {
  const domain = new CollaborationDomain({
    fixture,
    initialBytes,
    clock: new DeterministicClock(),
  });
  const summary = await runConformance(createDomainAdapter(domain), fixture);
  assert.equal(summary.pass, true, JSON.stringify(summary.scenarios.filter((item) => !item.pass), null, 2));
  assert.equal(summary.passed, 12);
});

test("all 12 R6-B scenarios pass through the loopback HTTP adapter", async (context) => {
  const service = await startReferenceService({
    fixture,
    initialBytes,
    clock: new DeterministicClock(),
  });
  context.after(() => service.close());
  const client = new CollaborationClient({ baseUrl: service.url });
  client.kind = "http";
  const summary = await runConformance(client, fixture);
  assert.equal(summary.pass, true, JSON.stringify(summary.scenarios.filter((item) => !item.pass), null, 2));
  assert.equal(summary.passed, 12);
});
