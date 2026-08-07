import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { HostInputAdapter } from "../../input/input-adapter.js";
import { PlainTextClipboardAdapter } from "../../input/clipboard-adapter.js";
import { EDITOR_V1_ACTIONS } from "../editor-client.js";

function event(properties = {}) {
  return {
    isTrusted: false,
    cancelable: true,
    preventDefault() {},
    ...properties,
  };
}

test("composition replaces one selected unit exactly once and suppresses duplicate beforeinput", async () => {
  let text = "甲乙丙";
  let selection = [2, 3];
  let revision = 0;
  const input = new HostInputAdapter({
    commit: async (committed) => {
      text = `${text.slice(0, selection[0])}${committed}${text.slice(selection[1])}`;
      selection = [selection[0] + committed.length, selection[0] + committed.length];
      revision += 1;
      return { revision };
    },
  });
  input._target = { value: "臺灣😀" };
  input.handleCompositionStart(event({ data: "" }));
  input.handleCompositionUpdate(event({ data: "臺灣😀" }));
  const committed = input.handleCompositionEnd(event({ data: "臺灣😀" }));
  const duplicate = input.handleBeforeInput(event({
    inputType: "insertText",
    data: "臺灣😀",
  }));
  const [result, duplicateResult] = await Promise.all([committed, duplicate]);
  assert.equal(result.committed, true);
  assert.equal(duplicateResult.committed, false);
  assert.equal(text, "甲乙臺灣😀");
  assert.equal(revision, 1);
});

test("cancel after caret navigation causes zero mutation", async () => {
  const commits = [];
  const input = new HostInputAdapter({
    commit: async (text) => { commits.push(text); return { revision: commits.length }; },
  });
  input._target = { value: "" };
  input.handleCompositionStart(event({ data: "" }));
  input.handleCompositionUpdate(event({ data: "不得提交" }));
  const result = await input.handleCompositionEnd(event({ data: "" }));
  assert.equal(result.committed, false);
  assert.deepEqual(commits, []);
});

test("HTML plus plain clipboard replaces selection only with plain text", async () => {
  let documentText = "ABCD";
  const input = new HostInputAdapter({
    commit: async (text) => {
      documentText = `${documentText.slice(0, 1)}${text}${documentText.slice(2)}`;
      return { revision: 1 };
    },
  });
  const clipboard = new PlainTextClipboardAdapter({ inputAdapter: input, secureContext: true });
  await clipboard.pasteEvent({
    preventDefault() {},
    clipboardData: {
      types: ["text/html", "text/plain"],
      getData(type) { return type === "text/plain" ? "臺灣😀" : "<b>forbidden</b>"; },
    },
  });
  assert.equal(documentText, "A臺灣😀CD");
  assert.equal(documentText.includes("forbidden"), false);
});

test("E1-C frozen matrix matches the product action list and bounded manual policy", () => {
  const matrixPath = fileURLToPath(new URL("../../e1/validation-matrix-v1.json", import.meta.url));
  const matrix = JSON.parse(readFileSync(matrixPath, "utf8"));
  assert.deepEqual(matrix.productActions, EDITOR_V1_ACTIONS);
  assert.deepEqual(matrix.browsers, ["chrome", "firefox"]);
  assert.equal(matrix.corpus.length, 5);
  assert.equal(matrix.thresholds.maximumWorkerGenerationsPerPage, 3);
  assert.equal(matrix.manual.runsPerBrowser, 1);
  assert.equal(matrix.manual.onlyAfterAutomaticPass, true);
  assert.equal(matrix.unsupported.includes("arbitrary-uno-command"), true);
  assert.equal(matrix.unsupported.includes("arbitrary-key-code"), true);
});

test("manual input sink exposes commit feedback and refreshes the rendered document", () => {
  const pagePath = fileURLToPath(new URL("../../web/e1-editor-validation.html", import.meta.url));
  const appPath = fileURLToPath(new URL("../../web/e1-editor-validation-app.js", import.meta.url));
  const page = readFileSync(pagePath, "utf8");
  const app = readFileSync(appPath, "utf8");
  assert.match(page, /id="input-feedback"/);
  assert.match(app, /event\.type === "commit-end"/);
  assert.match(app, /scheduleManualRender\(\)/);
  assert.match(app, /elements\.input\.value = ""/);
});
