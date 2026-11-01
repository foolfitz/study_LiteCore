// The Markdown paste on the page (SPEC-M3-link-batch-v21 4.2, 9.3, 9.12-9.14,
// 10.4; 11.2 M8 and M11), entry A: a toolbar button, a dialog with a text box,
// 「插入」 and 「取消」.
//
//   * M8 (page layer) -- SPEC-M3-link-batch-v22 §11.2 (b) (fable ruling 5):
//     v22 ships item 2, so M8 reads as SPEC-M3-link-batch-v21 §11.2 writes it
//     again -- the entry is shown, and the dialog opens, exactly when the
//     profile declares the paste.  In v21 §12.3 (e) (finding 153) the shell
//     showed no entry whatever the profile said; that reading was v21's only.
//     The page's `PASTE_MARKDOWN_ENTRY_SHIPS` is the switch (v21 §9.2): the
//     "as shipped" tests compile the page's own value, the "switch on" tests
//     replace it, and the dialog's own tests (M11, 9.14, the refusal
//     sentences) keep turning it on explicitly so they test the dialog
//     whichever way the switch is set.  The SDK and worker layers of the same
//     matrix are in sdk/tests/paste-markdown.test.mjs and
//     sdk/tests/sdk-worker-v21.test.mjs;
//   * finding 152, fix 3 (v22 §11.3) -- closing the dialog blurs the sink and
//     then focuses it (Chrome otherwise drops the next typed key);
//   * finding 154, the page's half (v22 §11.1) -- a closed dialog is hidden by
//     the page's own rule, not only by the browser's built-in one, which a
//     host's reset stylesheet overrides;
//   * M11 -- 「取消」 (and Escape) after typing enqueues nothing and leaves the
//     document alone;
//   * 9.14 -- 「插入」 with a range selected says 「請先取消選取」 and sends
//     nothing;
//   * the refusal sentences of 9.3 / 10.4 / 9.14, said in the dialog with the
//     text kept when nothing was dispatched (`recovery: "none"`), and a
//     post-dispatch failure closing the dialog with the rollback advice.
//
// Sliced from the page source and driven with fakes.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Client } from "../narrow-editor-v2-client.js";
import { selectionShapeOf } from "../narrow-editor-v2-session.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const SOURCE = readFileSync(process.env.PAGE_SOURCE || here("../../web/e2-editor-app.js"), "utf8");
const HTML = readFileSync(here("../../web/e2-editor.html"), "utf8");
const V20 = JSON.parse(readFileSync(here("../../dist/profiles/e2-editor-v20/sdk-manifest.json"), "utf8"));
const DECLARED = { ...V20, editorContract: { ...V20.editorContract, pasteMarkdown: "document-sdk-paste-markdown" } };
const V21 = JSON.parse(readFileSync(here("../../dist/profiles/e2-editor-v21/sdk-manifest.json"), "utf8"));
const V22 = JSON.parse(readFileSync(here("../../dist/profiles/e2-editor-v22/sdk-manifest.json"), "utf8"));
// The shell's switch for the entry (§12.3 (e)); absent on a page from before it.
const ENTRY_SWITCH = /^const PASTE_MARKDOWN_ENTRY_SHIPS = (?:true|false);$/m;

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const fn = (name) => slice(new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);

const offersFor = (manifest) => new NarrowEditorV2Client({
  handle: 1, revision: 0, _assertUsable() {}, _engine: { manifest, async _request() { return null; } },
}).offersPasteMarkdown();

/**
 * The dialog's functions over fake elements and a fake session; `paste(text)` is the session's answer.
 * `entryShips`: null compiles the page's own switch as it stands; true or false replaces it -- true is
 * the kept dialog as the batch that ships item 2 will turn it on.
 */
function dialog({ manifest = DECLARED, editorState = { selection: { collapsed: true } }, paste = () => ({ revision: 1 }),
                  entryShips = null } = {}) {
  const listeners = [];
  const element = (extra = {}) => ({ addEventListener: (type, l) => listeners.push([extra.id, type, l]), ...extra });
  const el = {
    toolbar: { querySelector: (selector) => (selector === '[data-action="paste-markdown"]' ? el.button : null) },
    button: { hidden: true },
    markdownDialog: element({ id: "dialog", open: false, showModal() { this.open = true; }, close() { this.open = false; } }),
    markdownText: { value: "", focused: false, focus() { this.focused = true; } },
    markdownMessage: { textContent: "", hidden: true },
    markdownInsert: element({ id: "insert", disabled: false }),
    markdownCancel: element({ id: "cancel" }),
    sink: { focused: 0, calls: [], focus() { this.calls.push("focus"); this.focused += 1; }, blur() { this.calls.push("blur"); } },
  };
  const offered = offersFor(manifest);
  const pasted = [];
  const asked = { offers: 0 };
  const session = {
    document: {},
    enqueueCount: 0,
    state: { snapshot: { editorState } },
    offersPasteMarkdown: () => { asked.offers += 1; return offered; },
    pasteMarkdown(text) {
      this.enqueueCount += 1;
      pasted.push(text);
      return Promise.resolve().then(() => {
        const outcome = paste(text);
        if (outcome instanceof Error) throw outcome;
        return outcome;
      });
    },
  };
  const toasts = [];
  // run(): the page's, as far as the dialog sees it -- the operation, and (unless quiet) a toast on failure.
  const run = async (label, operation, { quiet = false } = {}) => {
    try {
      return await operation();
    } catch (error) {
      if (!quiet) toasts.push(`${label}：${error.code}`);
      throw error;
    }
  };
  // eslint-disable-next-line no-new-func
  const api = new Function("el", "session", "run", "toast", "describeError", "selectionShapeOf", `
    let lastSelectionShape = "collapsed";
    ${entryShips === null ? (SOURCE.match(ENTRY_SWITCH) || [""])[0] : `const PASTE_MARKDOWN_ENTRY_SHIPS = ${entryShips};`}
    ${slice(/^const MARKDOWN_REFUSAL_TEXT = \{[\s\S]*?\n\};$/m, "MARKDOWN_REFUSAL_TEXT")}
    ${["updatePasteMarkdownAffordance", "markdownRefusalText", "showMarkdownMessage", "openMarkdownDialog",
       "closeMarkdownDialog", "cancelMarkdownDialog", "insertMarkdownFromDialog"].map(fn).join("\n")}
    ${slice(/^el\.markdownCancel\.addEventListener\("click", cancelMarkdownDialog\);$/m, "the cancel registration")}
    ${slice(/^el\.markdownDialog\.addEventListener\("cancel", \(event\) => \{[\s\S]*?\n\}\);$/m, "the Escape registration")}
    ${slice(/^el\.markdownInsert\.addEventListener\("click", [^\n]*\);$/m, "the insert registration")}
    return { updatePasteMarkdownAffordance, openMarkdownDialog, markdownRefusalText };
  `)(el, session, run, (text, bad) => toasts.push(text), (error) => `${error.code}：${error.message}`, selectionShapeOf);
  const fire = (id, type, event = { preventDefault() { this.prevented = true; } }) => {
    for (const [target, t, l] of listeners) if (target === id && t === type) l(event);
    return event;
  };
  const settle = async () => { for (let i = 0; i < 6; i += 1) await new Promise((r) => setImmediate(r)); };
  return { el, session, api, pasted, toasts, fire, settle, asked };
}

/** The page's toolbar click handler over the same fakes: `click(action)` presses that button. */
function toolbar(d) {
  let handler = null;
  const el = { ...d.el, toolbar: { ...d.el.toolbar, addEventListener: (type, l) => { if (type === "click") handler = l; } } };
  const session = { ...d.session, undo() {}, redo() {} };
  const routed = [];
  // eslint-disable-next-line no-new-func
  new Function("el", "session", "run", "insertText", "saveDocument", "editorAction", "EDITOR_V2_ACTIONS",
               "openMarkdownDialog", `
    ${slice(/^el\.toolbar\.addEventListener\("click", \(event\) => \{[\s\S]*?\n\}\);$/m, "the toolbar click handler")}
  `)(el, session, async (label, operation) => operation(), () => routed.push("insert-text"), () => routed.push("save"),
     (action) => routed.push(action), [], d.api.openMarkdownDialog);
  const click = (action) => handler({ target: { closest: () => ({ dataset: { action } }) } });
  return { click, routed };
}

const refusal = (code, extra = {}) => Object.assign(new Error(code), { code, recovery: "none", details: { dispatched: false, ...extra } });

// ------------------------------------------------------------------ M8

test("M8 (page): the button is in the markup HIDDEN, before anything has said the profile has it", () => {
  // The icon toolbar (2c807bb25) wraps the label in a span and adds data-tip; what this holds is `hidden` on the button itself.
  assert.match(HTML, /<button data-action="paste-markdown" hidden[ >](?:(?!<\/button>)[\s\S])*>貼上為 Markdown…<(?:(?!<\/button>)[\s\S])*<\/button>/);
  assert.match(HTML, /<dialog id="markdown-dialog"/);
});

test("v22 §11.2 (b): the v22 profile offers the paste, and the shipped shell shows the entry and routes it to the dialog", async () => {
  // Finding 153 is fixed in the v22 link (C1), so v22 ships item 2: the switch
  // is on in the page as it stands, and M8 reads "declared -> shown" again.
  assert.equal(V22.editorContract.pasteMarkdown, "document-sdk-paste-markdown", "the v22 manifest no longer declares it");
  assert.equal(offersFor(V22), true, "the client no longer offers the paste on v22: the SDK side moved");
  const d = dialog({ manifest: V22 });
  d.el.button.hidden = true;   // the opposite of what is expected: the update must set it
  d.api.updatePasteMarkdownAffordance();
  assert.equal(d.el.button.hidden, false, "the shipped shell hides 「貼上為 Markdown…」 on v22");
  // The page asks the session on every state update; v21_page_hook.py captures
  // the page's session through that call.
  assert.ok(d.asked.offers > 0, "updatePasteMarkdownAffordance no longer asks the session");
  // The toolbar's route to the dialog, and nothing pasted by opening it.
  const t = toolbar(d);
  t.click("paste-markdown");
  await d.settle();
  assert.equal(d.el.markdownDialog.open, true, "the toolbar's paste-markdown route did not open the dialog");
  assert.deepEqual(d.pasted, [], "opening the dialog pasted Markdown");
  assert.equal(d.session.enqueueCount, 0);
});

const M8_PROFILES = [
  ["the real v20 manifest", V20, false],
  ["the field with another value", { ...V20, editorContract: { ...V20.editorContract, pasteMarkdown: "paste-markdown" } }, false],
  ["the field as a boolean", { ...V20, editorContract: { ...V20.editorContract, pasteMarkdown: true } }, false],
  ["declared", DECLARED, true],
  ["the real v21 manifest", V21, true],
  ["the real v22 manifest", V22, true],
];

// v22 §11.2 (b): the page's own switch, as shipped -- shown exactly when declared.
for (const [label, manifest, declared] of M8_PROFILES) {
  test(`M8 (page, ${label}, as shipped): the entry is ${declared ? "shown" : "hidden"} and the dialog ${declared ? "opens" : "does not open"}`, () => {
    const d = dialog({ manifest });
    d.el.button.hidden = declared;   // the opposite of what is expected: the update must set it
    d.api.updatePasteMarkdownAffordance();
    assert.equal(d.el.button.hidden, !declared);
    d.api.openMarkdownDialog();
    assert.equal(d.el.markdownDialog.open, declared);
  });
}

// The same with the switch replaced by `true`: the code path, whatever the page sets.
for (const [label, manifest, declared] of M8_PROFILES) {
  test(`M8 (page, ${label}, switch on): the entry is ${declared ? "shown" : "hidden"} and the dialog ${declared ? "opens" : "does not open"}`, () => {
    const d = dialog({ manifest, entryShips: true });
    d.el.button.hidden = !declared;   // the opposite of what is expected: the update must set it
    d.api.updatePasteMarkdownAffordance();
    assert.equal(d.el.button.hidden, !declared);
    d.api.openMarkdownDialog();
    assert.equal(d.el.markdownDialog.open, declared);
  });
}

test("M8 (page): no session is no entry, with the switch on too", () => {
  for (const entrySwitch of [(SOURCE.match(ENTRY_SWITCH) || [""])[0], "const PASTE_MARKDOWN_ENTRY_SHIPS = true;"]) {
    const d = dialog();
    // eslint-disable-next-line no-new-func
    const update = new Function("el", "session", `${entrySwitch}\n${fn("updatePasteMarkdownAffordance")}\nreturn updatePasteMarkdownAffordance;`)(d.el, null);
    d.el.button.hidden = false;
    update();
    assert.equal(d.el.button.hidden, true, entrySwitch);
  }
});

test("M8 (page): the toolbar routes the button to the dialog, and only there", () => {
  const click = slice(/^el\.toolbar\.addEventListener\("click", \(event\) => \{[\s\S]*?\n\}\);$/m, "the toolbar click handler");
  assert.match(click, /: action === "paste-markdown" \? \(\) => openMarkdownDialog\(\)\n/);
});

// ------------------------------------------------------------------ M11
//
// From here on, the dialog itself: each test turns the shell's switch on
// explicitly (`entryShips: true`), so it tests the dialog whichever way the
// page sets the switch (v22 ships it on, v22 §11.2 (b)).

test("M11: typing in the dialog and pressing 取消 enqueues nothing, and the text is gone", async () => {
  const d = dialog({ entryShips: true });
  d.api.openMarkdownDialog();
  assert.equal(d.el.markdownDialog.open, true);
  assert.equal(d.el.markdownText.focused, true, "the box does not have the focus, so Ctrl+V goes elsewhere");
  d.el.markdownText.value = "# 打了一些字\n\n**粗體**";
  d.fire("cancel", "click");
  await d.settle();
  assert.deepEqual(d.pasted, []);
  assert.equal(d.session.enqueueCount, 0);
  assert.equal(d.el.markdownDialog.open, false);
  assert.equal(d.el.markdownText.value, "");
  assert.equal(d.el.sink.focused, 1, "the document's sink did not get the focus back");
});

// ------------------------------------------------------------------ finding 152, fix 3 (v22 §11.3)
//
// Chrome drops the first typed key after a modal <dialog> closes if the sink is
// only focused (finding 152, diag-dirty-move V5 / V11c); blur first, then focus.

for (const [label, close] of [
  ["取消", async (d) => { d.fire("cancel", "click"); await d.settle(); }],
  ["插入 on a caret", async (d) => { d.el.markdownText.value = "# a"; d.fire("insert", "click"); await d.settle(); }],
]) {
  test(`finding 152 fix 3: closing the dialog by ${label} blurs the sink, then focuses it`, async () => {
    const d = dialog({ entryShips: true });
    d.api.openMarkdownDialog();
    assert.equal(d.el.markdownDialog.open, true);
    await close(d);
    assert.equal(d.el.markdownDialog.open, false);
    assert.deepEqual(d.el.sink.calls, ["blur", "focus"], "the sink is not blurred before it is focused");
  });
}

// ------------------------------------------------------------------ finding 154, the page's half (v22 §11.1)

test("finding 154: the page hides a closed dialog with its own rule, which a host's reset cannot undo", () => {
  // Nextcloud's core/css/server.css resets `dialog { display: block }`, which beats the
  // browser's built-in `dialog:not([open]) { display: none }`; an id selector beats both.
  assert.match(HTML, /\n  #markdown-dialog:not\(\[open\]\) \{ display: none; \}\n/);
});

test("M11: Escape is 取消 too -- nothing enqueued, and the browser's own close is replaced by the page's", async () => {
  const d = dialog({ entryShips: true });
  d.api.openMarkdownDialog();
  d.el.markdownText.value = "# x";
  const event = d.fire("dialog", "cancel");
  await d.settle();
  assert.equal(event.prevented, true);
  assert.deepEqual(d.pasted, []);
  assert.equal(d.session.enqueueCount, 0);
  assert.equal(d.el.markdownText.value, "");
});

// ------------------------------------------------------------------ 9.14

test("9.14: 插入 with a range selected says 請先取消選取 and sends nothing; the text is kept", async () => {
  for (const rectangles of [[{}], [{}, {}]]) {
    const d = dialog({ editorState: { selection: { collapsed: false, rectangles } }, entryShips: true });
    d.api.openMarkdownDialog();
    d.el.markdownText.value = "# x";
    d.fire("insert", "click");
    await d.settle();
    assert.deepEqual(d.pasted, []);
    assert.equal(d.session.enqueueCount, 0);
    assert.equal(d.el.markdownMessage.hidden, false);
    assert.equal(d.el.markdownMessage.textContent, "請先取消選取");
    assert.equal(d.el.markdownDialog.open, true);
    assert.equal(d.el.markdownText.value, "# x");
  }
});

test("插入 on a caret sends the box's text once, closes the dialog and says so", async () => {
  const d = dialog({ entryShips: true });
  d.api.openMarkdownDialog();
  d.el.markdownText.value = "# 標題\n\n- 第一項";
  d.fire("insert", "click");
  await d.settle();
  assert.deepEqual(d.pasted, ["# 標題\n\n- 第一項"]);
  assert.equal(d.el.markdownDialog.open, false);
  assert.equal(d.el.markdownText.value, "");
  assert.deepEqual(d.toasts, ["已貼上 Markdown"]);
});

// ------------------------------------------------------- refusal sentences

for (const [code, sentence] of [
  ["MARKDOWN_REMOTE_IMAGE", "Markdown 裡有網路圖片，尚不支援；請先移除圖片"],            // 9.3
  ["MARKDOWN_NEEDS_CARET", "請先取消選取"],                                              // 9.14
]) {
  test(`${code}: said in the dialog as the spec words it, the text kept for fixing`, async () => {
    const d = dialog({ paste: () => refusal(code), entryShips: true });
    d.api.openMarkdownDialog();
    d.el.markdownText.value = "![a](https://example.test/a.png)";
    d.fire("insert", "click");
    await d.settle();
    assert.equal(d.el.markdownMessage.textContent, sentence);
    assert.equal(d.el.markdownMessage.hidden, false);
    assert.equal(d.el.markdownDialog.open, true);
    assert.equal(d.el.markdownText.value, "![a](https://example.test/a.png)");
    assert.equal(d.el.markdownInsert.disabled, false, "insert stayed disabled after the refusal");
    assert.deepEqual(d.toasts, [], "a refusal in the dialog was also toasted");
  });
}

test("MARKDOWN_HTML_UNSUPPORTED: the sentence tells the user to wrap it in backticks (10.4)", () => {
  const d = dialog();
  const text = d.api.markdownRefusalText({ code: "MARKDOWN_HTML_UNSUPPORTED" });
  assert.match(text, /請用反引號把它包起來/);
  assert.match(text, /List<T>/);
});

test("every pre-dispatch code the page can meet has its own sentence, never a raw code", () => {
  const d = dialog();
  for (const code of ["MARKDOWN_ENCODING_UNSUPPORTED", "MARKDOWN_NEEDS_CARET", "MARKDOWN_REMOTE_IMAGE",
                      "MARKDOWN_HTML_UNSUPPORTED", "MARKDOWN_UNDO_UNREADABLE", "MARKDOWN_CHECKPOINT_FAILED",
                      "INVALID_ARGUMENT"]) {
    const text = d.api.markdownRefusalText({ code });
    assert.ok(text && !text.includes(code), `${code}: ${text}`);
  }
  assert.match(d.api.markdownRefusalText({ code: "INVALID_ARGUMENT",
                                           details: { limitBytes: 65536, utf8Bytes: 70000 } }),
               /70000 位元組，上限 65536/);
});

test("a post-dispatch failure closes the dialog and advises the checkpoint (the notice bar does the rest)", async () => {
  const unknown = Object.assign(new Error("unverified"), { code: "MUTATION_OUTCOME_UNKNOWN", recovery: "rollback" });
  const d = dialog({ paste: () => unknown, entryShips: true });
  d.api.openMarkdownDialog();
  d.el.markdownText.value = "# x";
  d.fire("insert", "click");
  await d.settle();
  assert.equal(d.el.markdownDialog.open, false);
  assert.equal(d.toasts.length, 1);
  assert.match(d.toasts[0], /請回到檢查點/);
});
