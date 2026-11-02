// SPEC-P-demo-batch-4: the client and the session accept what a v32 manifest offers, a manifest without it offers nothing, and what the
// toolbar may show comes from one function with the two rules cache-freshness/run-02 measured.
import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { EDITOR_ACCEPTED_ACTIONS, NarrowEditorV2Client, postconditionClassOf } from "../narrow-editor-v2-client.js";
import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";
import { EDITOR_TOGGLE_ACTIONS, formatFailureDisposition, paragraphFormatShown } from "../paragraph-editor-client.js";

function client(actions) {
  const requests = [];
  const document = {
    revision: 7, handle: 1, _assertUsable() {},
    _engine: {
      manifest: {capabilities: ["narrow-editor-v2"], editorContract: {version: 2, abiVersion: 6, actions}},
      async _request(operation, payload) {
        requests.push({operation, ...payload});
        return {action: payload.action, beforeRevision: payload.expectedRevision, revision: payload.expectedRevision + 1,
                changed: null, completion: "verified-format-readback"};
      },
    },
  };
  return {requests, client: new NarrowEditorV2Client(document), document};
}

test("all six are accepted, classed as paragraph actions and reach the wire with both flags false", async () => {
  const actions = Object.fromEntries(EDITOR_TOGGLE_ACTIONS.map((name, i) => [name, {id: 28 + i, gestures: ["collapsed", "range-single", "range-cross"], limits: []}]));
  for (const action of EDITOR_TOGGLE_ACTIONS) {
    const {client: c, requests} = client(actions);
    assert.equal(c.offers(action), true);
    assert.ok(EDITOR_ACCEPTED_ACTIONS.includes(action));
    assert.equal(postconditionClassOf(action), "paragraph");
    assert.equal(NarrowEditorV2Session.isParagraphAction(action), true);
    await c.action(action);
    assert.deepEqual(requests.map((r) => [r.operation, r.action, r.extendSelection, r.enabled]), [["editorActionV2", action, false, false]]);
  }
});

test("a manifest without them does not offer them", () => {
  const {client: c} = client({"set-bold": {id: 7, gestures: ["collapsed"], limits: []}});
  for (const action of EDITOR_TOGGLE_ACTIONS) assert.equal(c.offers(action), false);
});

test("a flag on a toggle is refused before the wire", async () => {
  const {client: c, requests} = client({"toggle-list-ordered": {id: 33, gestures: ["collapsed"], limits: []}});
  await assert.rejects(c.action("toggle-list-ordered", {extendSelection: true}), {code: "INVALID_ARGUMENT"});
  assert.equal(requests.length, 0);
});

test("what the toolbar shows: the level, the bullet, and the number where it means something", () => {
  assert.deepEqual(paragraphFormatShown({paragraphStyle: "Heading 3", listBullet: false, listNumber: true}, true), {level: 3, bullet: false, number: null});
  assert.deepEqual(paragraphFormatShown({paragraphStyle: "Body Text", listBullet: false, listNumber: true}, true), {level: 0, bullet: false, number: true});
  assert.deepEqual(paragraphFormatShown({paragraphStyle: "Standard", listBullet: true, listNumber: false}, undefined), {level: 0, bullet: true, number: false});
  assert.equal(paragraphFormatShown({paragraphStyle: "Heading 3"}, false), null, "a range shows nothing");
  assert.equal(paragraphFormatShown({paragraphStyle: null}, true), null, "no style, nothing known");
  assert.equal(paragraphFormatShown(null, true), null);
  assert.equal(paragraphFormatShown({paragraphStyle: "Heading 12"}, true).level, 0, "only a style named exactly that is a level");
  assert.equal(paragraphFormatShown({paragraphStyle: "My Heading 2"}, true).level, 0);
  assert.equal(paragraphFormatShown({paragraphStyle: "Heading 2", formatStale: true}, true).level, 2, "formatStale is not read: it stays true over right values");
});

test("the paragraph read's three shapes keep the queue open on every route, and v31's keeps its rollback", () => {
  for (const route of ["collapsed", "range-single", "range-cross"])
    for (const failureShape of ["paragraph-read-failed", "paragraph-text-changed", "paragraph-target-not-met"])
      assert.equal(formatFailureDisposition({details: {formatBarrier: {dispatched: true, route, failureShape}}}), "dispatched-unverified");
  assert.equal(formatFailureDisposition({details: {formatBarrier: {dispatched: true, route: "collapsed", failureShape: "postcondition-not-met"}}}), "dispatched-rollback");
  assert.equal(formatFailureDisposition({details: {formatBarrier: {dispatched: false, route: "collapsed", failureShape: "paragraph-read-failed"}}}), "refused-no-mutation");
  assert.equal(formatFailureDisposition({details: {formatBarrier: {dispatched: false, route: "collapsed", failureShape: "selection-too-long"}}}), "refused-no-mutation");
});

const html = readFileSync(fileURLToPath(new URL("../../web/e2-editor.html", import.meta.url)), "utf8");

test("the heading menu offers body and four levels, each a closed action, and each toggle has a control", () => {
  const items = [...html.matchAll(/role="menuitemradio"[^>]*data-level="(\d)" data-action="([a-z0-9-]+)"/g)].map((m) => [m[1], m[2]]);
  assert.deepEqual(items, [["0", "set-paragraph-body"], ["1", "toggle-heading-1"], ["2", "toggle-heading-2"], ["3", "toggle-heading-3"], ["4", "toggle-heading-4"]]);
  for (const action of EDITOR_TOGGLE_ACTIONS) assert.match(html, new RegExp(`data-action="${action}"`));
});

test("the five setter buttons stay in the page for a profile without the toggles, and every div child of the toolbar keeps its place", () => {
  for (const action of ["set-paragraph-heading", "set-paragraph-body", "set-list-unordered", "set-list-ordered", "set-list-none"])
    assert.match(html, new RegExp(`<button data-setter-group data-action="${action}"`));
  const toolbar = html.slice(html.indexOf('id="toolbar"'), html.indexOf("</div>\n", html.indexOf('id="heading-menu"')));
  assert.equal((toolbar.match(/<span class="heading-menu-wrap"/g) ?? []).length, 1, "a span: the host hides .sep by nth-of-type among the toolbar's divs");
  assert.doesNotMatch(html.slice(html.indexOf('class="heading-menu-wrap"'), html.indexOf('data-action="toggle-list-unordered"')), /<div/);
});
