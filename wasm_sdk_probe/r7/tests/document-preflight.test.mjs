import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { DocumentPreflightError, preflightDocument } from "../document-preflight.js";

const project = new URL("../../", import.meta.url);

test("valid project ODT passes closed-format preflight", async () => {
  const bytes = await readFile(new URL("test-docs/t1-plain-zh.odt", project));
  const result = preflightDocument(bytes, { name: "fixture.odt" });
  assert.equal(result.format, "odt");
  assert.ok(result.archive.entryCount > 0);
});

test("public DOCX name and disguised DOCX bytes are rejected", async () => {
  const bytes = await readFile(new URL("test-docs/r7/r7-plain.docx", project));
  assert.throws(
    () => preflightDocument(bytes, { name: "fixture.docx" }),
    (error) => error instanceof DocumentPreflightError && error.code === "UNSUPPORTED_FORMAT",
  );
  assert.throws(
    () => preflightDocument(bytes, { name: "fixture.odt" }),
    (error) => error.code === "UNSUPPORTED_FORMAT" && error.details.detectedFormat === "docx",
  );
});

test("truncated ODT and unsafe names receive typed failures", async () => {
  const bytes = await readFile(new URL("test-docs/r7/r7-corrupt-truncated.odt", project));
  assert.throws(
    () => preflightDocument(bytes, { name: "corrupt.odt" }),
    (error) => error.code === "CORRUPT_DOCUMENT",
  );
  for (const name of ["../escape.odt", "dir/file.odt", "bad\0.odt"])
    assert.throws(() => preflightDocument(new Uint8Array(), { name }),
      (error) => error.code === "INVALID_DOCUMENT_NAME");
});

test("compressed file limit rejects before parsing and does not truncate", () => {
  assert.throws(
    () => preflightDocument(new Uint8Array(9), {
      name: "large.odt", limits: { maxFileBytes: 8 },
    }),
    (error) => error.code === "DOCUMENT_TOO_LARGE" && error.details.bytes === 9,
  );
});
