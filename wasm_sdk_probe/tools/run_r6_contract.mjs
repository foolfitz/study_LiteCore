#!/usr/bin/env node

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

import { CollaborationClient } from "../collaboration/collaboration-client.js";
import { createDomainAdapter, runConformance } from "../collaboration/conformance.js";
import { CollaborationDomain, DeterministicClock } from "../collaboration/domain.js";
import { startReferenceService } from "../collaboration/reference-service.js";

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

const project = resolve(new URL("..", import.meta.url).pathname);
const evidenceDirectory = resolve(project, argument(
  "--evidence-dir", "../findings/evidence/sdk-r6/contract",
));
const fixture = JSON.parse(await readFile(
  resolve(project, "collaboration/fixtures/canonical.json"), "utf8",
));
const initialBytes = await readFile(resolve(project, "test-docs/t1-plain-zh.odt"));
await mkdir(evidenceDirectory, { recursive: true });

const domain = new CollaborationDomain({
  fixture,
  initialBytes,
  clock: new DeterministicClock(),
});
const domainSummary = await runConformance(createDomainAdapter(domain), fixture);
await writeFile(
  resolve(evidenceDirectory, "domain-summary.json"),
  `${JSON.stringify(domainSummary, null, 2)}\n`,
);

const service = await startReferenceService({
  fixture,
  initialBytes,
  clock: new DeterministicClock(),
});
let httpSummary;
try {
  const client = new CollaborationClient({ baseUrl: service.url });
  client.kind = "http";
  httpSummary = await runConformance(client, fixture);
  await writeFile(
    resolve(evidenceDirectory, "http-summary.json"),
    `${JSON.stringify(httpSummary, null, 2)}\n`,
  );
  await writeFile(
    resolve(evidenceDirectory, "http-audit.json"),
    `${JSON.stringify(service.domain.audit, null, 2)}\n`,
  );
} finally {
  await service.close();
}

const summary = {
  schemaVersion: 1,
  release: "R6-B",
  contractVersion: fixture.contractVersion,
  domain: { passed: domainSummary.passed, failed: domainSummary.failed, pass: domainSummary.pass },
  http: { passed: httpSummary.passed, failed: httpSummary.failed, pass: httpSummary.pass },
  adaptersEquivalent: domainSummary.scenarios.every((scenario, index) =>
    scenario.pass === httpSummary.scenarios[index]?.pass),
};
summary.pass = summary.domain.pass && summary.http.pass && summary.adaptersEquivalent;
await writeFile(
  resolve(evidenceDirectory, "summary.json"),
  `${JSON.stringify(summary, null, 2)}\n`,
);
console.log(JSON.stringify(summary, null, 2));
if (!summary.pass)
  process.exitCode = 1;
