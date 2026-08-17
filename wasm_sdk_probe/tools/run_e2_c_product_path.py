#!/usr/bin/env python3
"""Drive the E2-C product page down the paths a USER takes, not the ones a
harness takes.

Why this exists
---------------
On 2026-08-16 three product defects were found in one day, by a person, in the
D5 operator round -- and not one of them was reachable by any automated round
this tree had:

  * finding 049: the product's own save button wrote 15 bytes of
    "[object Object]".  Every harness calls `session.save()` itself and
    destructures `{bytes}`, so every harness measured the SHELL's save and none
    of them ever pressed the button.
  * finding 050: every IME commit after the first in a session was rejected as a
    buffer mismatch.  Every harness calls `session.commitText()` directly, so
    none of them ever went through the adapter's composition path, and none of
    them ever typed a SECOND time.
  * Ctrl+C never asked the engine for the selection.  Nothing called
    `copySelection()`; the shell had it all along.

The shape they share is one sentence: **where the harness's path and the user's
path differ, only the user's path is unmeasured.**  This runner closes that gap
for the three known shapes and leaves a place to add the next one.

What this is NOT
----------------
The events here are synthesised, so `isTrusted` is false throughout.  **This is
not D5 and no cell may cite it.**  D5's entire subject is trusted input and
needs a human; this is a regression net underneath it.  What the two have in
common is only the path -- the product's own handlers.

Declared shims (SPEC E2-C 6: a harness that patches the page it observes says so
where the evidence can see it):

  * `URL.createObjectURL` -- the product saves by handing a Blob to a download
    link, and nothing outside the page can read a download.
  * `HTMLAnchorElement.prototype.click` for anchors carrying `download` -- so a
    headless browser is never asked to open a save dialog, which would block
    every subsequent command.  What this leaves unmeasured is the download
    plumbing itself (href/download/click); an operator established that by hand
    on 2026-08-16 (findings/evidence/049/verified-by-operator/).
  * `#toast.textContent` is cleared before a step, so that "the product said
    nothing" is distinguishable from "the product said something earlier".

Being able to fail
------------------
`--mutate` reintroduces one of the three defects into a symlink mirror of dist/
(dist itself is never written) and requires the matching check to go RED while
the others stay green.  A check that cannot be shown to fail is not a check --
this tree has recorded that lesson often enough to build it into the tool.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

# The three texts committed through the composition path.  Distinct, and absent
# from every fixture, so finding them in the saved ODT is a statement about this
# run.
IME_TEXTS = ["甲一", "乙二", "丙三"]

# The marker the insert button types.  Distinct from IME_TEXTS and absent from
# every fixture, so finding it in a saved ODT is a statement about the press
# that put it there.
INSERT_MARK = "插入鈕標記"

# The fixture's own text, used as a witness that a check did not destroy the
# document around what it was measuring.  It is only ever REQUIRED if a previous
# capture in the same run showed it present, so a different --fixture degrades to
# the IME witnesses rather than to a false red.
FIXTURE_SENTINEL = "E1-LC-END"


def surviving_witnesses(previous_content: str) -> list[str]:
    """What the run has already SEEN in the document, and may therefore require.

    Adjudicated 2026-08-16.  The first version of these clauses required the
    three IME strings outright, and the `ime` mutation -- which drops two of
    them by design -- turned two unrelated checks red.  A check must not require
    content whose presence is another check's SUBJECT; it may require content
    whose presence IT verified, in its own prior capture.

    Deriving the set costs nothing: the saves are already captured.  A mutation
    can shrink this set but can never make a check red for another check's
    reason.
    """
    return [w for w in (*IME_TEXTS, FIXTURE_SENTINEL) if w in previous_content]

# --------------------------------------------------------------------- shims

INSTALL = """(() => {
// `window`, not `globalThis`: geckodriver evaluates each script in a
// Marionette sandbox whose global is recreated per call, so a shim
// installed on `globalThis` is gone by the next evaluate.  Reads of page
// globals work either way, which is what made this look fine in Chrome.
if (window.__pp) return "already";
const pp = { saves: [], anchorClicks: 0, error: null };
window.__pp = pp;
const nativeCreate = window.URL.createObjectURL.bind(window.URL);
window.URL.createObjectURL = (blob) => {
  const url = nativeCreate(blob);
  void (async () => {
    try {
      const bytes = new Uint8Array(await blob.arrayBuffer());
      let binary = "";
      for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i]);
      pp.saves.push({ bytes: bytes.length, type: blob.type, b64: btoa(binary) });
    } catch (error) { pp.error = String(error); }
  })();
  return url;
};
const nativeClick = window.HTMLAnchorElement.prototype.click;
window.HTMLAnchorElement.prototype.click = function () {
  if (this.hasAttribute("download")) { pp.anchorClicks += 1; return; }
  return nativeClick.call(this);
};
return "installed";
})()"""

CLEAR_TOAST = """(() => {
document.querySelector('#toast').textContent = '';
return true;
})()"""

READ_TOAST = "(() => document.querySelector('#toast').textContent)()"

# Hand the product a file through its own <input type=file>, the way a chooser
# would.  The File is synthesised because neither driver can operate a native
# file dialog -- so this exercises the page's change handler and NOT the picker,
# which the check records as its own limit rather than leaving implied.
OPEN_FILE = """(() => {
const input = document.querySelector('#file');
if (!input) return "no-input";
void (async () => {
  const bytes = await (await fetch("ARG_URL", { cache: "no-cache" })).arrayBuffer();
  const file = new File([bytes], "ARG_NAME",
                        { type: "application/vnd.oasis.opendocument.text" });
  const transfer = new DataTransfer();
  transfer.items.add(file);
  input.files = transfer.files;
  input.dispatchEvent(new Event("change", { bubbles: true }));
})();
return "dispatched";
})()"""

SAVE_COUNT = "(() => (window.__pp ? window.__pp.saves.length : -1))()"

READ_SAVE = "(() => (window.__pp ? window.__pp.saves[ARG_INDEX] : null) || null)()"

PRESS = """(() => {
const button = document.querySelector('#toolbar button[data-action="ARG_ACTION"]');
if (!button) return false;
button.click();
return true;
})()"""

POINT_AT = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const x = box.left + box.width * ARG_X;
const y = box.top + box.height * ARG_Y;
canvas.dispatchEvent(new PointerEvent('pointerdown', {
  clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, bubbles: true }));
canvas.dispatchEvent(new PointerEvent('pointerup', {
  clientX: x, clientY: y, button: 0, buttons: 0, pointerId: 1, bubbles: true }));
return true;
})()"""

DRAG = """(() => {
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const at = (fx, fy) => ({ x: box.left + box.width * fx, y: box.top + box.height * fy });
const a = at(ARG_X1, ARG_Y1);
const b = at(ARG_X2, ARG_Y2);
const send = (type, point, buttons) => canvas.dispatchEvent(new PointerEvent(type, {
  clientX: point.x, clientY: point.y, button: 0, buttons, pointerId: 1, bubbles: true }));
send('pointerdown', a, 1);
send('pointermove', { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, 1);
send('pointermove', b, 1);
send('pointerup', b, 0);
return true;
})()"""

# One composition, through the product page's own input sink.
#
# The line that matters is `sink.value += TEXT`.  A real IME does not write that
# line -- the browser does, as the default action of `beforeinput` with
# inputType `insertCompositionText`, which is NOT cancelable during composition.
# Synthetic events run no default action, so without this the textarea would
# stay empty, the adapter's buffer comparison would short-circuit on an empty
# string, and finding 050 would be invisible to this harness exactly as it was
# invisible to every other one.  Appending (not assigning) is what the browser
# does, and it is what makes the fix's absence observable: nothing in this tree
# clears that buffer except the fix.
COMPOSE = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
sink.dispatchEvent(new CompositionEvent('compositionstart', { data: '', bubbles: true }));
sink.dispatchEvent(new CompositionEvent('compositionupdate', { data: 'ARG_TEXT', bubbles: true }));
sink.dispatchEvent(new InputEvent('beforeinput', {
  inputType: 'insertCompositionText', data: 'ARG_TEXT', bubbles: true, cancelable: false }));
sink.value += 'ARG_TEXT';
sink.dispatchEvent(new CompositionEvent('compositionend', { data: 'ARG_TEXT', bubbles: true }));
return sink.value;
})()"""

SET_TEXT = """(() => {
const field = document.querySelector('#text');
field.value = 'ARG_TEXT';
return field.value;
})()"""

# Is the product OFFERING its recovery, or is the button merely in the DOM?
# `#notice` is `display: none` until `data-show="1"`, so a click on a hidden
# button drives a path the user cannot reach -- which is what the first version
# of this check did.
# Finding 047's recipe, with nothing in between -- which is the whole of it.
#
# Driving it as three WebDriver calls does not reproduce: each round trip plus
# the poll that waits for the caret toast spends more than the ~2 s after which
# 047's own controls show the failure stops happening.  Pressed from inside the
# page, the three land in the session's FIFO back to back, which is the sequence
# the finding measured.
INDUCE_047 = """(() => {
const toolbar = document.querySelector('#toolbar');
const press = (action) => toolbar
  .querySelector(`[data-action="${action}"]`).click();
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const x = box.left + box.width * ARG_X;
const y = box.top + box.height * ARG_Y;
press('save');
canvas.dispatchEvent(new PointerEvent('pointerdown', {
  clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, bubbles: true }));
canvas.dispatchEvent(new PointerEvent('pointerup', {
  clientX: x, clientY: y, button: 0, buttons: 0, pointerId: 1, bubbles: true }));
press('set-list-unordered');
return true;
})()"""

# Finding 053's own route into a dispatched failure, and the only one that does
# not depend on 047 still reproducing.
#
# Click past the end of a line -- measured natively: below/past the text the
# clamp saturates at the end-of-line offset -- then break the paragraph, which
# leaves the caret in a NEW EMPTY paragraph.  A list action there is finding
# 046's cell: `.uno:SelectText` overshoots into the neighbour, the barrier
# refuses a mutation that succeeded, and the error is
# EDITOR_FORMAT_POSTCONDITION_FAILED with `dispatched: true`.
#
# That is the error whose prescription the product could not carry out.  It also
# drives `action:insert-paragraph-break`, which nothing had driven either.
INDUCE_EMPTY_PARAGRAPH = """(() => {
const toolbar = document.querySelector('#toolbar');
const press = (action) => toolbar
  .querySelector(`[data-action="${action}"]`).click();
const canvas = document.querySelector('#canvas');
const box = canvas.getBoundingClientRect();
const x = box.left + box.width * ARG_X;
const y = box.top + box.height * ARG_Y;
canvas.dispatchEvent(new PointerEvent('pointerdown', {
  clientX: x, clientY: y, button: 0, buttons: 1, pointerId: 1, bubbles: true }));
canvas.dispatchEvent(new PointerEvent('pointerup', {
  clientX: x, clientY: y, button: 0, buttons: 0, pointerId: 1, bubbles: true }));
return true;
})()"""

BREAK_THEN_LIST = """(() => {
const toolbar = document.querySelector('#toolbar');
const press = (action) => toolbar
  .querySelector(`[data-action="${action}"]`).click();
press('insert-paragraph-break');
return true;
})()"""

READ_NOTICE = """(() => {
const notice = document.querySelector('#notice');
const button = document.querySelector('#notice-action');
return {
  shown: notice ? notice.dataset.show === "1" : null,
  text: document.querySelector('#notice-text').textContent,
  label: button ? button.textContent : null,
  disabled: button ? button.disabled : null,
};
})()"""

# The product's recovery path.  The button lives outside #toolbar and has no
# data-action, so PRESS cannot reach it -- which is part of why no round ever
# had.  `.click()` fires the listener whether or not #notice is displayed.
CLICK_NOTICE = """(() => {
const button = document.querySelector('#notice-action');
if (!button) return false;
button.click();
return true;
})()"""

COPY = """(() => {
const sink = document.querySelector('#sink');
sink.focus();
const notPrevented = sink.dispatchEvent(
  new ClipboardEvent('copy', { bubbles: true, cancelable: true }));
return { handlerRan: !notPrevented };
})()"""

# ----------------------------------------------------------------- mutations

MUTATIONS = {
    # The failure this check exists to catch is not "opening crashes" -- it is
    # opening that LOOKS right: the filename updates, the state goes ready, and
    # the document the engine holds is still the old one.  So the mutation keeps
    # every visible signal and swaps only the bytes.  A check that asked whether
    # the label changed would pass this mutation, which is why it does not ask.
    "open-file": {
        "check": "product-opens-a-document-the-user-chose",
        "path": "e2-editor-app.js",
        "find": "    .then((bytes) => openDocument(bytes, file.name))",
        "replace": ('    .then(() => fetch("./e1-fixtures/list-contexts.odt")\n'
                    '      .then((r) => r.arrayBuffer())\n'
                    '      .then((b) => openDocument(b, file.name)))'),
        "reintroduces": "a product that can only open its own samples",
        # Nothing else: the open runs last, after every other check has already
        # been judged, so this mutation cannot reach them.
        "alsoRed": [],
    },
    "save": {
        "check": "product-save-button-writes-a-real-odt",
        "path": "e2-editor-app.js",
        "find": 'const { bytes } = await run("儲存", () => session.save());',
        "replace": 'const bytes = await run("儲存", () => session.save());',
        "reintroduces": "finding 049",
        # Breaking the save button also blinds the IME check, whose document
        # half is read THROUGH the product's own save -- there is no other way
        # out of the page, which is the reason finding 049 could hide for as
        # long as it did.  Declared rather than papered over: the alternative
        # is an IME check that asks only whether the revision moved, and that
        # is exactly the criterion round 5 passed while two thirds of a user's
        # typing was being dropped.
        # The insert and undo oracles are guarded by `is_an_odt` too, so a
        # broken save takes them down with it.  Declared, for the same reason
        # as above.
        #
        # The rollback check is deliberately NOT here: it is NOT_ESTABLISHED on
        # every run today, so requiring it to go red would require a check that
        # never runs to fail, and the 2026-08-16 save-mutation round reported
        # NOT DETECTED for exactly that reason.  Listing it would have been the
        # declaration claiming more than the harness does.
        # The recovery check ends by requiring the product to save a real ODT
        # after recovering -- that is how it shows the session is usable and not
        # merely in a good-looking state -- so a broken save takes it down too.
        # Added 2026-08-16 after the run said so: this is the coupling being
        # declared, not the check being weakened.
        "alsoRed": ["every-ime-commit-reaches-the-document",
                    "notice-action-recovers-the-session"],
        # Both of these read their outcome out of the document, and this
        # mutation removes the only way to read it -- so neither can go red,
        # they can only fail to run.  Declared as such rather than left out: a
        # declaration that omits a coupling stops being falsifiable, and the run
        # verifies this outcome and reports the declaration stale if either
        # check ever runs at all.
        #
        # `product-insert-...` moved here from `alsoRed` on 2026-08-16, and the
        # machine check is what moved it: once the witnesses became DERIVED from
        # the previous save, a broken save leaves an empty witness set, and an
        # empty witness set is NOT_ESTABLISHED by construction.  The declaration
        # had gone on claiming a red the harness could no longer deliver.
        "alsoNotEstablished": ["product-insert-button-inserts-what-the-field-holds",
                               "product-undo-button-reverses-the-last-edit"],
    },
    "ime": {
        "check": "every-ime-commit-reaches-the-document",
        "path": "input/input-adapter.js",
        "find": '      this._target.value = "";',
        "replace": "      /* mutation: finding 050 reintroduced */;",
        "reintroduces": "finding 050",
    },
    "copy": {
        "check": "ctrl-c-asks-the-engine",
        "path": "e2-editor-app.js",
        "find": 'el.sink.addEventListener("copy", (event) => {',
        "replace": 'el.sink.addEventListener("copy-removed-by-mutation", (event) => {',
        "reintroduces": "the Ctrl+C gap found in the D5 operator round",
    },
    # The three paths the coverage audit named HIGH on 2026-08-16.  Each
    # mutation is the shape the defect would actually take on that path.
    "undo": {
        "check": "product-undo-button-reverses-the-last-edit",
        "path": "e2-editor-app.js",
        "find": '    action === "undo" ? () => run("復原", () => session.undo())',
        "replace": '    action === "undo" ? () => run("復原", () => Promise.resolve())',
        "reintroduces": "finding 049's shape on the undo path: the button runs, "
                        "the toast reports a time, and the document is untouched",
    },
    "insert-text": {
        "check": "product-insert-button-inserts-what-the-field-holds",
        "path": "e2-editor-app.js",
        "find": "  const text = el.text.value;",
        "replace": "  const text = el.text.placeholder;",
        "reintroduces": "finding 049 exactly: the handler reads the wrong "
                        "property off the right element",
        # Same shape as the save mutation: this destroys the undo check's
        # precondition (the marker is never inserted, so there is nothing whose
        # removal undo could be judged on).  Precondition-destruction is a
        # general property of mutations upstream of a check's setup.
        "alsoNotEstablished": ["product-undo-button-reverses-the-last-edit"],
    },
    "rollback": {
        "check": "notice-action-recovers-the-session",
        "path": "e2-editor-app.js",
        "find": '  void run("回到檢查點", () => session.rollback())',
        "replace": '  void run("回到檢查點", () => session.undo())',
        "reintroduces": "the recovery path wired to undo instead of rollback -- "
                        "which SPEC E2-B 5.13 rules out explicitly, because undo "
                        "goes through the queue a post-dispatch failure has just "
                        "blocked and would only return EDITOR_NOT_READY",
        # This was declared `expectedToBeDetected: False` while the check could
        # not run at all -- the product offers the button only from
        # `recoverable-error`, and nothing could induce that state from the
        # page.  Once the 053 route existed, the run reported the declaration
        # STALE and detected the mutation, which is what the self-reporting
        # limit was built to do.  The declaration is gone; this is a live
        # verification now.
    },
    # Undo that takes back MORE than the last edit.  Before the witnesses were
    # derived, the `ime` mutation's collateral was the accidental proof that the
    # survival clauses could fire; decoupling them removed that proof, so this
    # restores it deliberately.  A second undo reverses the last IME commit too,
    # which is in the witness set derived from the save before it.
    "undo-twice": {
        "check": "product-undo-button-reverses-the-last-edit",
        "path": "e2-editor-app.js",
        "find": '    action === "undo" ? () => run("復原", () => session.undo())',
        "replace": ('    action === "undo" ? () => run("復原",'
                    " () => session.undo().then(() => session.undo()))"),
        "reintroduces": "nothing that has happened; an undo that reverses two "
                        "edits, which is what the survival witnesses exist to "
                        "notice",
    },
    # The narrowest mutation that stops the 047 recipe from doing anything: the
    # toolbar ignores the one action it dispatches.  It exists so that
    # "NOT_ESTABLISHED because the queue did not block" can be shown to be
    # different from "NOT_ESTABLISHED because the toolbar is broken" -- the
    # hiding place an adversarial review named on 2026-08-16.  Narrow on
    # purpose: no other check presses this button.
    "toolbar-drops-the-list-action": {
        "check": "notice-action-recovers-the-session",
        "path": "e2-editor-app.js",
        "find": "    : EDITOR_V2_ACTIONS.includes(action) ? () => editorAction(action)",
        "replace": ('    : (EDITOR_V2_ACTIONS.includes(action)'
                    ' && action !== "set-list-unordered")'
                    " ? () => editorAction(action)"),
        "reintroduces": "nothing that has happened; a toolbar that silently "
                        "drops one action, which is what the guard on the "
                        "NOT_ESTABLISHED branch exists to notice",
    },
    # Not a defect this tree has had: a handler that runs, prevents the default
    # and reports success WITHOUT asking the engine.  It is here because
    # adversarial review named it as something this check might not catch, and
    # the answer belongs in the evidence rather than in an assumption.
    "copy-lies": {
        "check": "ctrl-c-asks-the-engine",
        "path": "e2-editor-app.js",
        "find": '  void run("複製", () => session.copySelection())\n    .then((result) => toast(`已複製 ${result?.codePoints ?? "?"} 字`))\n    .catch(() => {});',
        "replace": '  toast(`已複製 1 字`);   /* mutation: never asks the engine */',
        "reintroduces": "nothing that has happened; a hypothetical handler that "
                        "reports success without calling copySelection",
        "expectedToBeDetected": False,
        "why": "From outside the page, 'the engine was asked' is not observable: "
               "the product's only outward signal is its own toast, and a lying "
               "handler writes the same toast. Recorded as a named limit of this "
               "harness. What would close it is the shell's clipboard trace being "
               "reported somewhere a harness can read, which is a product change "
               "and therefore a decision, not a detail.",
    },
}


def build_mirror(source: Path, target: Path, overrides: dict[str, bytes]) -> None:
    """Mirror `source` into `target` with symlinks, materialising `overrides`.

    dist/ is 7.5 GB and holds every frozen profile; copying it to break one file
    would be both slow and a way to accidentally write to a frozen artifact.
    Everything is a symlink except the directories leading to an override.
    """
    real_dirs: set[str] = set()
    for relative in overrides:
        parent = Path(relative).parent
        while parent != Path("."):
            real_dirs.add(parent.as_posix())
            parent = parent.parent

    def walk(relative: Path) -> None:
        source_dir = source / relative
        target_dir = target / relative
        target_dir.mkdir(parents=True, exist_ok=True)
        for entry in source_dir.iterdir():
            child = relative / entry.name if relative != Path(".") else Path(entry.name)
            key = child.as_posix()
            if key in overrides:
                (target / child).write_bytes(overrides[key])
            elif entry.is_dir() and key in real_dirs:
                walk(child)
            else:
                os.symlink(entry.resolve(), target / child)

    walk(Path("."))


def apply_mutation(name: str, scratch: Path) -> tuple[Path, dict]:
    spec = MUTATIONS[name]
    original = (PROJECT / "dist" / spec["path"]).read_text(encoding="utf-8")
    hits = original.count(spec["find"])
    if hits != 1:
        raise SystemExit(
            f"mutation '{name}' expects exactly one occurrence of its pattern in "
            f"dist/{spec['path']}, found {hits}.  The tree moved under the "
            f"mutation; fix the pattern rather than the count.")
    mutated = original.replace(spec["find"], spec["replace"])
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root,
                 {spec["path"]: mutated.encode("utf-8")})
    return root, {"mutation": name, "file": spec["path"],
                  "reintroduces": spec["reintroduces"],
                  "mustGoRed": spec["check"]}


# ------------------------------------------------------------------- helpers


def wait_for(session, predicate, timeout, poll=0.4):
    deadline = time.monotonic() + timeout
    state = None
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and predicate(state):
            return state
        time.sleep(poll)
    return state


def revision_of(state) -> int | None:
    text = (state or {}).get("revision") or ""
    return int(text) if text.isdigit() else None


def wait_saves(session, count, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if (evaluate(session, SAVE_COUNT) or 0) >= count:
            return True
        time.sleep(0.3)
    return False


def capture_save(session, index: int, timeout=90) -> dict:
    """Press the product's own save button and report what the bytes were.

    `index` is the position in the shim's capture list, which is also the number
    of saves this run has already taken.  Returns {} if nothing arrived, and the
    callers treat that as a failed check rather than as an absence of evidence.
    """
    evaluate(session, CLEAR_TOAST)
    evaluate(session, PRESS.replace("ARG_ACTION", "save"))
    if not wait_saves(session, index + 1, timeout):
        return {}
    raw = evaluate(session, READ_SAVE.replace("ARG_INDEX", str(index)))
    return zip_report(base64.b64decode(raw["b64"])) if raw else {}


def zip_report(raw: bytes) -> dict:
    """What the bytes are, in enough detail to refuse a ZIP that is not an ODT.

    Adversarial review, 2026-08-16: the first version of the save check asked
    only for the ZIP magic and a clean CRC, so a valid ZIP containing one text
    file passed it -- as would a DOCX.  `content.xml` was read into the report
    and the read's failure recorded in `zipError`, which nothing looked at.  A
    field the verdict does not read is not a check.
    """
    out = {"bytes": len(raw), "magic": raw[:4].hex(), "isZip": raw[:4] == b"PK\x03\x04"}
    if not out["isZip"]:
        out["head"] = raw[:64].decode("utf-8", "replace")
        return out
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = archive.namelist()
            out["entries"] = len(names)
            out["badEntry"] = archive.testzip()
            out["hasContentXml"] = "content.xml" in names
            out["mimetype"] = (archive.read("mimetype").decode("utf-8", "replace")
                               if "mimetype" in names else None)
            out["content"] = archive.read("content.xml").decode("utf-8", "replace")
    except Exception as error:            # noqa: BLE001 -- reported, not raised
        out["zipError"] = str(error)
    if out.get("content"):
        try:
            ElementTree.fromstring(out["content"])
            out["contentXmlParses"] = True
        except ElementTree.ParseError as error:
            out["contentXmlParses"] = False
            out["xmlError"] = str(error)
    return out


def is_an_odt(report: dict) -> bool:
    """Every condition the name claims, and each one able to fail on its own."""
    return (bool(report.get("isZip")) and report.get("badEntry") is None
            and report.get("zipError") is None
            and bool(report.get("hasContentXml"))
            and report.get("contentXmlParses") is True
            and report.get("mimetype")
            == "application/vnd.oasis.opendocument.text")


# ---------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--fixture", default="list-contexts")
    parser.add_argument("--mutate", choices=tuple(MUTATIONS) + ("none",), default="none")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--out", default=None, help="write the report here as JSON")
    args = parser.parse_args()

    report: dict = {
        "schemaVersion": 1,
        "release": "e2-c-product-path",
        "browser": args.browser,
        "fixture": args.fixture,
        "isTrusted": False,
        "notD5": "synthetic events; SPEC E2-C D5 requires trusted input and a human",
        "shims": ["URL.createObjectURL",
                  "HTMLAnchorElement.prototype.click (download anchors)",
                  "#toast.textContent cleared between steps"],
        "mutation": args.mutate if args.mutate != "none" else None,
        "checks": [],
        "steps": [],
    }

    scratch = Path(tempfile.mkdtemp(prefix="e2c-product-path-"))
    root = PROJECT / "dist"
    if args.mutate != "none":
        root, mutation_report = apply_mutation(args.mutate, scratch)
        report["mutationDetail"] = mutation_report

    def check(cid, ok, outcome=None, **fields):
        """One check, with three outcomes rather than two.

        NOT_ESTABLISHED is for a check whose PRECONDITION could not be reached
        -- not for one that failed.  A harness that reports those as failures
        teaches its readers to ignore red, and one that reports them as passes
        is worse.  `finish()` counts them as neither.
        """
        report["checks"].append({
            "id": cid, "ok": bool(ok),
            "outcome": outcome or ("PASS" if ok else "FAIL"), **fields})

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        navigate(session, base)

        booted = wait_for(session, lambda s: s.get("state") in ("ready", "stopped",
                                                               "expired"),
                          args.timeout)
        report["steps"].append({"step": "boot", "state": booted})
        if not booted or booted.get("state") != "ready":
            report["failedAt"] = "boot"
            return finish(report, args)

        report["steps"].append({"step": "install-shims",
                                "result": evaluate(session, INSTALL)})

        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        caret = wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        report["steps"].append({"step": "place-caret", "state": caret})
        if not caret or "失敗" in (caret.get("latency") or ""):
            report["failedAt"] = "place-caret"
            return finish(report, args)

        # ------------------------------------------------ 049: the save button
        evaluate(session, CLEAR_TOAST)
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        captured = wait_saves(session, 1)
        toast_after_save = evaluate(session, READ_TOAST) or ""
        saved = evaluate(session, READ_SAVE.replace("ARG_INDEX", "0")) if captured else None
        first = zip_report(base64.b64decode(saved["b64"])) if saved else {}
        check("product-save-button-writes-a-real-odt",
              is_an_odt(first) and "NaN" not in toast_after_save,
              observed={"capturedBytes": first.get("bytes"),
                        "magic": first.get("magic"),
                        "head": first.get("head"),
                        "entries": first.get("entries"),
                        "hasContentXml": first.get("hasContentXml"),
                        "contentXmlParses": first.get("contentXmlParses"),
                        "mimetype": first.get("mimetype"),
                        "zipError": first.get("zipError"),
                        "toast": toast_after_save,
                        "anchorClicks": evaluate(session,
                                                 "(() => window.__pp.anchorClicks)()")},
              oracle="the bytes the product hands to the download ARE an ODT -- ZIP "
                     "magic, clean CRC, an ODT mimetype entry and a content.xml "
                     "that parses -- and its own toast reports a size rather than "
                     "NaN")

        # -------------------------------------- 050: three commits, three edits
        before = revision_of(evaluate(session, READ_STATE))
        commits = []
        last = before if before is not None else 0
        for text in IME_TEXTS:
            evaluate(session, CLEAR_TOAST)
            sink = evaluate(session, COMPOSE.replace("ARG_TEXT", text))
            # A commit that is going to be dropped is dropped silently, so this
            # waits for the revision it expects and gives up rather than hanging.
            settled = wait_for(session,
                               lambda s, floor=last: revision_of(s) is not None
                               and revision_of(s) > floor,
                               8)
            observed = revision_of(settled)
            commits.append({"text": text, "sinkAfter": sink, "revision": observed,
                            "toast": evaluate(session, READ_TOAST)})
            if observed is not None:
                last = max(last, observed)
        after = revision_of(evaluate(session, READ_STATE))
        report["steps"].append({"step": "ime-commits", "commits": commits,
                                "revisionBefore": before, "revisionAfter": after})

        # The document, not only the counter: the counter is what round 5's
        # analyzer looked at, and it reported success while two thirds of a
        # user's typing was being dropped.
        evaluate(session, CLEAR_TOAST)
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        wait_saves(session, 2)
        second_raw = evaluate(session, READ_SAVE.replace("ARG_INDEX", "1"))
        second = zip_report(base64.b64decode(second_raw["b64"])) if second_raw else {}
        content = second.get("content") or ""
        present = [t for t in IME_TEXTS if t in content]
        advanced = (after - before) if (after is not None and before is not None) else None
        # Per commit, not only in total.  Adversarial review, 2026-08-16: a
        # product that committed all three texts on the FIRST compositionend and
        # dropped the other two would still show +3 overall with all three
        # strings present.  The per-commit revisions were already being recorded
        # and simply were not being judged.
        stepwise = []
        expected = before
        for entry in commits:
            expected = None if expected is None else expected + 1
            stepwise.append({"text": entry["text"], "expected": expected,
                             "observed": entry["revision"],
                             "ok": expected is not None
                             and entry["revision"] == expected})
        each_landed = bool(stepwise) and all(row["ok"] for row in stepwise)
        check("every-ime-commit-reaches-the-document",
              advanced == len(IME_TEXTS) and len(present) == len(IME_TEXTS)
              and each_landed,
              observed={"revisionBefore": before, "revisionAfter": after,
                        "advancedBy": advanced, "committed": IME_TEXTS,
                        "foundInSavedOdt": present,
                        "perCommitRevision": stepwise,
                        "savedBytes": second.get("bytes")},
              oracle="three commits through the product's composition path each "
                     "advance the revision by exactly one, IN TURN, and all three "
                     "strings are in the saved ODT")

        # ------------------------------------------------------ Ctrl+C reaches
        evaluate(session, DRAG.replace("ARG_X1", "0.20").replace("ARG_Y1", "0.28")
                 .replace("ARG_X2", "0.75").replace("ARG_Y2", "0.28"))
        time.sleep(1.5)
        evaluate(session, CLEAR_TOAST)
        copy_result = evaluate(session, COPY)
        time.sleep(1.5)
        copy_toast = evaluate(session, READ_TOAST) or ""
        # The outcome is classified by WHERE in copySelection it came from, not
        # by whether the product said something.  Read against
        # input/clipboard-adapter.js:
        #   已複製 N 字             -- selection read, clipboard written
        #   CLIPBOARD_DENIED        -- raised only by typedClipboardError(_, "write"),
        #                              i.e. AFTER getSelection returned a non-empty
        #                              text/plain selection.  The engine answered;
        #                              WebDriver refused the OS clipboard.
        #   CLIPBOARD_EMPTY_SELECTION -- the engine was asked and had nothing
        #   CLIPBOARD_UNAVAILABLE   -- never reached the engine
        #   (silence)               -- the defect: no handler at all
        if "已複製" in copy_toast:
            outcome = "copied"
        elif "CLIPBOARD_DENIED" in copy_toast:
            outcome = "selection-read-clipboard-write-denied"
        elif "CLIPBOARD_EMPTY_SELECTION" in copy_toast:
            outcome = "engine-asked-nothing-selected"
        elif copy_toast.strip():
            outcome = "other-failure"
        else:
            outcome = "silent"
        check("ctrl-c-asks-the-engine",
              bool(copy_result and copy_result.get("handlerRan"))
              and outcome in ("copied", "selection-read-clipboard-write-denied"),
              observed={"handlerRan": (copy_result or {}).get("handlerRan"),
                        "toast": copy_toast, "outcome": outcome},
              oracle="a copy event on the product page is handled by the product "
                     "(default prevented) and the ENGINE returns a non-empty "
                     "selection for it -- proved by which error the clipboard "
                     "adapter raises, since CLIPBOARD_DENIED on the copy path is "
                     "reachable only after getSelection has succeeded",
              notEstablished="whether the OS clipboard received the text; WebDriver "
                             "refuses clipboard access, so that half belongs to D5")

        # ------------------------------------------- the three HIGH-risk paths
        #
        # `e2/product-path-coverage.json` named `action:undo`,
        # `action:insert-text` and `listener:click#notice-action` HIGH and driven
        # by nothing.  The last of those is the product's RECOVERY path, and a
        # recovery path nobody has ever pressed is a recovery path nobody knows
        # works.  They run after the checks above so those keep the exact flow
        # they were written for.

        # --- action:insert-text -------------------------------------------
        #
        # Collapse the caret first.  The copy check above leaves the drag's
        # selection live, and `commitText` REPLACES a selection -- correctly, and
        # measured: the first run of the witness clause below went red with all
        # three IME texts gone, because the insert had replaced the line they
        # were on.  The product was right and the check's premise was wrong.
        evaluate(session, POINT_AT.replace("ARG_X", "0.35").replace("ARG_Y", "0.28"))
        wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
        evaluate(session, CLEAR_TOAST)
        field = evaluate(session, SET_TEXT.replace("ARG_TEXT", INSERT_MARK))
        before_insert = revision_of(evaluate(session, READ_STATE))
        evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
        inserted_state = wait_for(
            session,
            lambda s, floor=before_insert: revision_of(s) is not None
            and floor is not None and revision_of(s) > floor, 20)
        after_insert = revision_of(inserted_state)
        insert_toast = evaluate(session, READ_TOAST) or ""
        third = capture_save(session, 2)
        insert_content = third.get("content") or ""
        # Witnesses that the insert ADDED the marker rather than replacing the
        # document with it -- "the marker is somewhere in content.xml" is also
        # true of a button that inserts it and destroys everything else.  The
        # set is DERIVED from the save this run already took, so a mutation
        # aimed at another check cannot make this one red (see
        # surviving_witnesses).
        expected_witnesses = surviving_witnesses(content)
        kept_witnesses = [w for w in expected_witnesses if w in insert_content]
        check("product-insert-button-inserts-what-the-field-holds",
              field == INSERT_MARK and is_an_odt(third)
              and INSERT_MARK in insert_content
              and kept_witnesses == expected_witnesses
              and before_insert is not None and after_insert == before_insert + 1,
              outcome=None if expected_witnesses else "NOT_ESTABLISHED",
              observed={"fieldAfterSet": field, "revisionBefore": before_insert,
                        "revisionAfter": after_insert,
                        "markInSavedOdt": INSERT_MARK in insert_content,
                        "witnessesExpected": expected_witnesses,
                        "witnessesKept": kept_witnesses,
                        "toast": insert_toast, "savedBytes": third.get("bytes")},
              oracle="the text standing in the product's own field, inserted by "
                     "the product's own button, advances the revision by exactly "
                     "one and is in the document the product then saves")

        # --- action:undo ---------------------------------------------------
        before_undo = revision_of(evaluate(session, READ_STATE))
        evaluate(session, CLEAR_TOAST)
        evaluate(session, PRESS.replace("ARG_ACTION", "undo"))
        undone_state = wait_for(
            session,
            lambda s, floor=before_undo: revision_of(s) is not None
            and revision_of(s) != floor, 20)
        undo_toast = evaluate(session, READ_TOAST) or ""
        fourth = capture_save(session, 3)
        undo_content = fourth.get("content") or ""
        # `is_an_odt` is not decoration here.  Every oracle below is an ABSENCE,
        # and a save that produced nothing would satisfy an absence for the
        # wrong reason -- which is the exact shape finding 049 hid behind.
        #
        # Nor is the precondition.  The `insert-text` mutation run of
        # 2026-08-16 showed this check going GREEN while undo was untested: the
        # marker was never inserted, so "the marker is gone" was true before
        # undo ran.  An absence is only evidence if the thing was there first.
        was_inserted = INSERT_MARK in insert_content
        # And not MORE than the last edit.  Adversarial review, 2026-08-16: the
        # oracle "the marker is gone" is equally satisfied by a button that
        # deletes the paragraph, empties the document, or rolls the whole
        # session back -- the same confusion SPEC E2-B 5.13 warns about, in the
        # other direction.  The IME commits went in before the marker, so they
        # are the witnesses that undo stopped where it should have.
        undo_witnesses = surviving_witnesses(insert_content)
        undo_kept = [w for w in undo_witnesses if w in undo_content]
        check("product-undo-button-reverses-the-last-edit",
              is_an_odt(fourth) and INSERT_MARK not in undo_content
              and undo_kept == undo_witnesses
              and revision_of(undone_state) != before_undo,
              outcome=None if (was_inserted and undo_witnesses)
              else "NOT_ESTABLISHED",
              observed={"revisionBefore": before_undo,
                        "revisionAfter": revision_of(undone_state),
                        "markWasThereBeforeUndo": was_inserted,
                        "markStillInSavedOdt": INSERT_MARK in undo_content,
                        "witnessesExpected": undo_witnesses,
                        "witnessesKept": undo_kept,
                        "toast": undo_toast, "savedBytes": fourth.get("bytes")},
              oracle="pressing the product's own undo button takes the text the "
                     "insert button just added back OUT of the document -- read "
                     "from the saved ODT, not from the revision counter, because "
                     "D1 covers undo through the shell and this is the button")

        # --- listener:click#notice-action, the recovery path ----------------
        #
        # The first version of this check pressed the button from `ready` and
        # went red with `editor cannot restart from ready`.  That was the check
        # being wrong, not the product: `#notice` is displayed only for
        # `recoverable-error` and `restart-required`, which is exactly the set
        # `EditorSession.restart()` accepts.  Pressing a button the product is
        # not offering measures nothing.
        #
        # So the state has to be reached first, and finding 047 is how: save,
        # then a click-placed caret, then a format action, with nothing in
        # between, produces `MUTATION_OUTCOME_UNKNOWN` -- which IS in
        # RECOVERY_ERRORS, so the queue blocks, the state becomes
        # `recoverable-error`, and the product puts the notice up.  100%
        # reproducible on this artifact, both browsers, four controlled arms.
        evaluate(session, CLEAR_TOAST)
        evaluate(session, INDUCE_047.replace("ARG_X", "0.30").replace("ARG_Y", "0.34"))
        blocked = wait_for(
            session, lambda s: s.get("state") in ("recoverable-error",
                                                  "restart-required"), 60)
        attempts = [{"recipe": "finding 047: save, click, format",
                     "state": (blocked or {}).get("state"),
                     "latency": (blocked or {}).get("latency")}]

        # Finding 053's own route, tried when 047's does not block.  It rests on
        # a defect that is current and reproducible (046) rather than on one
        # whose sequence stopped reproducing, and it is also 053's end-to-end
        # reproduction: the error whose prescription the product could not carry
        # out, produced by the product's own buttons.
        if (blocked or {}).get("state") not in ("recoverable-error",
                                                "restart-required"):
            evaluate(session, CLEAR_TOAST)
            evaluate(session, INDUCE_EMPTY_PARAGRAPH
                     .replace("ARG_X", "0.92").replace("ARG_Y", "0.28"))
            wait_for(session, lambda s: "定位游標" in (s.get("latency") or ""), 60)
            evaluate(session, BREAK_THEN_LIST)
            wait_for(session, lambda s: "斷行" in (s.get("latency") or "")
                     or "段落" in (s.get("latency") or ""), 30)
            evaluate(session, CLEAR_TOAST)
            evaluate(session, PRESS.replace("ARG_ACTION", "set-list-unordered"))
            blocked = wait_for(
                session, lambda s: s.get("state") in ("recoverable-error",
                                                      "restart-required"), 60)
            attempts.append({
                "recipe": "finding 053: click past the line end, break the "
                          "paragraph, list the empty one (finding 046's cell)",
                "state": (blocked or {}).get("state"),
                "latency": (blocked or {}).get("latency"),
                "toast": evaluate(session, READ_TOAST)})
        offered = evaluate(session, READ_NOTICE)
        report["steps"].append({"step": "induce-dispatched-failure",
                                "state": blocked, "notice": offered,
                                "attempts": attempts})

        pressed_notice = evaluate(session, CLICK_NOTICE)
        # rollback() is restart(): a fresh Worker reopened from the newest of
        # the checkpoint and authority bytes.  The document goes away and comes
        # back, so this waits for `ready` rather than for a revision.
        restarted = wait_for(session, lambda s: s.get("state") == "ready", 180)
        notice_toast = evaluate(session, READ_TOAST) or ""
        # The session is not merely in a good-looking state: it can still do the
        # thing the user came for.
        after_rollback = capture_save(session, 5)
        reached = (blocked or {}).get("state") in ("recoverable-error",
                                                   "restart-required")
        # Adversarial review, 2026-08-16: NOT_ESTABLISHED must not become a
        # place for regressions to hide.  "The recipe did not block the queue"
        # is the expected outcome today, but it is ALSO what a removed
        # `set-list-unordered` handler or a broken toolbar would produce.  So
        # the recipe has to have visibly done something: either it blocked the
        # queue, or the format action it dispatched completed.
        latency = (blocked or {}).get("latency") or ""
        recipe_ran = "項目符號" in latency
        if not reached and not recipe_ran:
            check("notice-action-recovers-the-session", False,
                  observed={"stateAfterRecipe": (blocked or {}).get("state"),
                            "latency": (blocked or {}).get("latency"),
                            "notice": offered},
                  oracle="finding 047's recipe must either block the queue or"
                         " complete the format action it dispatches; neither"
                         " happened, so the product path itself is broken --"
                         " this is NOT the 'precondition unreachable' case")
            return finish(report, args)
        if not reached:
            # Finding 047's sequence did not block the queue here.  That is NOT
            # a verdict on 047: it was measured on 2026-08-15 through a
            # different harness and a shell generation before finding 048
            # changed what placeCaret waits for -- and 047's own diagnosis was
            # that placeCaret's confirmation did not guarantee the next action.
            # Whether 048's fix closed 047 is a question for its own round, not
            # something to conclude from a run that was trying to do something
            # else.  Filed as `queue-047-may-have-closed-under-048`.
            check("notice-action-recovers-the-session", False,
                  outcome="NOT_ESTABLISHED",
                  observed={"stateAfterRecipe": (blocked or {}).get("state"),
                            "latency": (blocked or {}).get("latency"),
                            "notice": offered,
                            "pressedAnyway": evaluate(session, CLICK_NOTICE),
                            "toastFromPressingItAnyway":
                                evaluate(session, READ_TOAST)},
                  why="the product offers this button only in "
                      "`recoverable-error` or `restart-required`, which is the "
                      "same set EditorSession.restart() accepts, and finding "
                      "047's recipe -- the one documented route into that state "
                      "from the product's own UI -- did not block the queue in "
                      "this run.  Pressing the hidden button anyway is recorded "
                      "above and measures nothing about the recovery path.",
                  oracle="a dispatched failure blocks the queue, the product "
                         "OFFERS its recovery button, pressing it returns the "
                         "session to ready, and the product can save afterwards")
            return finish(report, args)
        check("notice-action-recovers-the-session",
              reached and bool((offered or {}).get("shown"))
              and (offered or {}).get("disabled") is False
              and bool(pressed_notice)
              and (restarted or {}).get("state") == "ready"
              and is_an_odt(after_rollback),
              observed={"stateAfterFailure": (blocked or {}).get("state"),
                        "noticeOffered": offered,
                        "buttonFound": pressed_notice,
                        "stateAfterPress": (restarted or {}).get("state"),
                        "toast": notice_toast,
                        "savedBytesAfter": after_rollback.get("bytes"),
                        "savedIsOdt": is_an_odt(after_rollback)},
              oracle="a dispatched failure blocks the queue, the product OFFERS "
                     "its recovery button, pressing it returns the session to "
                     "ready, and the product can save a real ODT afterwards -- "
                     "undo in its place would return EDITOR_NOT_READY on the "
                     "queue the failure just blocked, which is why SPEC E2-B "
                     "5.13 prescribes rollback and not undo",
              notEstablished="WHICH bytes came back.  A save moves the authority "
                             "bytes and there is no way to read the document out "
                             "of the page except by saving, so an edit made after "
                             "the failure cannot be shown to have been discarded "
                             "without destroying the thing being measured")

        # --------------------------------- opening a document the user chose
        # Until 2026-08-17 the product could only open the samples in its own
        # dropdown, which makes it a demo of an editor rather than an editor.
        # The oracle is deliberately NOT "the filename changed" -- a page that
        # ignored the bytes entirely would still pass that.  It saves afterwards
        # and looks for text that exists ONLY in the file that was handed over.
        evaluate(session, CLEAR_TOAST)
        opened = evaluate(session, OPEN_FILE
                          .replace("ARG_URL", "./e1-fixtures/markdown-syntax.odt")
                          .replace("ARG_NAME", "chosen-by-the-user.odt"))
        shown = wait_for(session,
                         lambda s: (s.get("doc") or "") == "chosen-by-the-user.odt",
                         60)
        saves_before = evaluate(session, SAVE_COUNT)
        evaluate(session, PRESS.replace("ARG_ACTION", "save"))
        captured_open = wait_saves(session, (saves_before or 0) + 1)
        after_open = (zip_report(base64.b64decode(
            evaluate(session, READ_SAVE.replace(
                "ARG_INDEX", str((saves_before or 0))))["b64"]))
            if captured_open else {})
        text_after = (after_open.get("content") or "")
        check("product-opens-a-document-the-user-chose",
              opened == "dispatched" and bool(shown)
              and is_an_odt(after_open)
              and "MD-CONTROL" in text_after
              and "E1-LC-HEADING" not in text_after,
              observed={"dispatch": opened,
                        "docLabel": (shown or {}).get("doc"),
                        "savedIsOdt": is_an_odt(after_open),
                        "hasChosenFilesText": "MD-CONTROL" in text_after,
                        "stillHasFixtureText": "E1-LC-HEADING" in text_after},
              oracle="a file handed to the product's own file input is the "
                     "document the engine now holds: saving afterwards returns "
                     "text that exists only in THAT file and none of the text "
                     "from the fixture that was open before",
              notEstablished="that a real OS file picker reaches this handler. "
                             "The File is synthesised and assigned to the input, "
                             "which exercises the page's change handler and not "
                             "the chooser -- the same class of gap D5 exists for")
        return finish(report, args)
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        shutil.rmtree(scratch, ignore_errors=True)


def finish(report: dict, args) -> int:
    checks = report["checks"]
    # A check whose precondition was never reached is neither evidence for the
    # product nor against it.  It is counted separately so that a run does not
    # go green on a path it did not exercise, and does not go red on one it
    # could not.
    unestablished = [c["id"] for c in checks
                     if c.get("outcome") == "NOT_ESTABLISHED"]
    report["notEstablishedChecks"] = unestablished
    judged = [c for c in checks if c.get("outcome") != "NOT_ESTABLISHED"]
    spec = MUTATIONS[args.mutate] if args.mutate != "none" else None
    if spec and spec.get("expectedToBeDetected") is False:
        # A mutation this harness does NOT claim to catch.  Recorded with its
        # reason, so the limit lives in the evidence instead of in somebody's
        # head -- and if it ever IS caught, the run says the limit is stale.
        # `judged`, not `checks`: a NOT_ESTABLISHED check has ok False, and
        # reading that as "detected" would turn a check that never ran into a
        # declaration that the limit is stale.
        red = [c for c in judged if c["id"] == spec["check"] and not c["ok"]]
        # Adversarial review, 2026-08-16: this branch used to set ok True
        # unconditionally, so a run with a declared-undetectable mutation exited
        # 0 even when the SAVE, IME, insert and undo checks were all failing.
        # A declaration about one check is not a pass for the others.
        others_ok = all(c["ok"] for c in judged if c["id"] != spec["check"])
        report["mustGoRed"] = []
        report["ok"] = bool(others_ok)
        report["verdict"] = (
            "this mutation is DETECTED after all -- the recorded limit is out of "
            "date and should be removed" if red
            else ("not detected, as declared: " + spec.get("why", "")
                  if others_ok else
                  "the declared-undetectable mutation was not detected, AS "
                  "DECLARED, but another check failed in the same run"))
    elif spec:
        # The declared NOT_ESTABLISHED collateral, verified rather than assumed:
        # a check declared here that RAN (red or green) means the declaration is
        # stale, and the run says so instead of quietly agreeing with itself.
        declared_void = spec.get("alsoNotEstablished", [])
        stale_void = [c["id"] for c in checks
                      if c["id"] in declared_void
                      and c.get("outcome") != "NOT_ESTABLISHED"]
        report["declaredNotEstablished"] = declared_void
        report["staleNotEstablishedDeclarations"] = stale_void
        must_be_red = {spec["check"], *spec.get("alsoRed", [])}
        report["mustGoRed"] = sorted(must_be_red)
        # A must-go-red check that was NOT_ESTABLISHED did not detect anything:
        # it never ran.  Counting it as a detection would be the exact failure
        # this whole mechanism exists to prevent, so `judged` is used here.
        reds = [c for c in judged if c["id"] in must_be_red]
        others_ok = all(c["ok"] for c in judged
                        if c["id"] not in must_be_red
                        and c["id"] not in declared_void)
        report["ok"] = bool(len(reds) == len(must_be_red)
                            and all(not c["ok"] for c in reds) and others_ok
                            and not stale_void)
        report["verdict"] = (
            "the mutation was detected by the check that owns it"
            if report["ok"] else
            ("a check declared NOT_ESTABLISHED for this mutation ran after all:"
             f" {stale_void} -- the declaration is stale" if stale_void else
             "THE MUTATION WAS NOT DETECTED -- the check cannot fail, did not "
             "run, or another check failed with it"))
    else:
        report["ok"] = bool(judged) and all(c["ok"] for c in judged)
        report["verdict"] = (
            ("every product path this covers behaves"
             + (f"; {len(unestablished)} not established" if unestablished else ""))
            if report["ok"] else "a product path is broken")
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
