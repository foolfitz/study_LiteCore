#!/usr/bin/env python3
"""Finding 059, the WASM half: does the shipped build APPLY the command it
reports as failed?

Native says core applies the parameterised inline format and reports
`success: false` (findings/evidence/059/native/). The product turns that into
LOK_COMMAND_FAILED and blocks the session, so on WASM the document effect has
never been read. Finding 059 records that gap as "未確立的一格,而且它很重要":
if the WASM build also applies it, today's product asks the user to roll back a
change that succeeded.

Why it cannot be measured through the product as it ships
---------------------------------------------------------
The four inline formats are not paragraph actions, so their failure carries no
`formatBarrier` field; `formatFailureDisposition()` falls through to
`unknown-rollback`, `recoveryFor()` returns "rollback", and
`_blockQueueIfDispatched()` blocks the queue. Nothing can be typed or saved
after that, so the document is unreadable exactly where the answer is.

The shim, declared
------------------
This serves a symlink MIRROR of dist/ -- dist itself is never written, the same
mechanism `--mutate` uses -- with exactly one override:
`editor-shell-v2/paragraph-editor-client.js`, so that a barrier-less
LOK_COMMAND_FAILED reports `dispatched-unverified` instead of
`unknown-rollback`. That keeps the queue open; nothing else is changed and the
WASM artifact is untouched.

**What the shim costs this measurement**: it does not measure the product's real
disposition, which is still `rollback`. It answers one question only -- what
happened to the document -- and any statement about what the product does to a
user must come from an unshimmed run.

The shim self-revokes, and that is not incidental: the sentinel path asks the
engine for a state before resolving, and if the engine is wedged that raises
TIMEOUT, which is in the frozen base class's RECOVERY_ERRORS. A TIMEOUT arm
therefore looks like a blocked session, not like "bold did not apply", and is
reported as unanswered rather than scored.

Oracle
------
A COLLAPSED caret, then a marker inserted through the product's own insert
button, then save.

The first round of this probe used a RANGE selection, on the reasoning that a
range styles existing text and needs no typing.  **That round measured nothing**:
the v3 manifest declares `gestures: ["collapsed"]` for all four inline formats
(dist/profiles/e2-editor-v3/sdk-manifest.json), so the page disables those
buttons whenever the selection is a range (updateGestureAffordance,
web/e2-editor-app.js:131) and `button.click()` on a disabled button fires
nothing.  Every arm came back with an empty toast and an unstyled document --
which is indistinguishable from "core did nothing", and is exactly the false
negative this probe exists to avoid.  So the button's `disabled` state is now
recorded on every arm and an arm that could not dispatch is not scored.

What the collapsed caret costs, stated because it is asymmetric:

  * **A styled marker is decisive.**  Core applied the command AND the insert
    path carried it; the answer is yes.
  * **An unstyled marker is NOT decisive.**  `handleInsertText` pastes first and
    only falls back to postKeyEvent (probe_engine.cpp), and whether a paste
    carries the caret's pending character attributes is unmeasured.  A null
    result therefore needs a native control on the same insert mechanism before
    it may be read as "core did not apply it".

The fixture is the one built for the native round: every paragraph unstyled, so
any styled run in the saved file was produced by this run.

Usage:
  run_f059_wasm_predicate.py [--browser chrome|firefox] [--out REPORT.json]
  run_f059_wasm_predicate.py --self-test
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_f059_predicate import NS, SLOT_PROPERTY, automatic_styles, slot_is_on  # noqa: E402
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from run_e2_c_product_path import (  # noqa: E402
    CLEAR_TOAST, DRAG, INSTALL, OPEN_FILE, POINT_AT, PRESS, READ_SAVE,
    READ_TOAST,
    SAVE_COUNT, build_mirror, served_shell_identity, wait_for, wait_saves,
    zip_report,
)

PROJECT = Path(__file__).resolve().parent.parent
FIXTURE = PROJECT / "test-docs" / "f059-predicate-wide.odt"
BOLD_SOURCE = PROJECT / "test-docs" / "f059-predicate-bold-source.odt"

# A SECOND declared shim, added 2026-08-18 after the marker oracle was measured
# to be unusable on this product.
#
# The v3 manifest declares `gestures: ["collapsed"]` for all four inline
# formats, so the page disables those buttons for a range selection and the
# document effect can only be reached through an inserted marker -- and the
# `insert-path-carries-formatting` control showed a marker inserted at a caret
# the ENGINE reports as bold comes back unstyled, so that route measures the
# insert path rather than core.
#
# Lifting the gesture mask lets a range selection reach the same dispatch, where
# the effect lands on text that already exists and the saved ODT answers
# directly.  What this costs: it measures what CORE does with a range dispatch,
# not what the product offers a user -- the product does not offer this, and no
# statement about the product may cite it.
MASK_FILE = "e2-editor-app.js"
MASK_FIND = "    const offered = !Array.isArray(gestures) || gestures.includes(lastSelectionShape);"
MASK_REPLACE = ("    // DECLARED SHIM (tools/run_f059_wasm_predicate.py): the gesture mask is\n"
                "    // lifted so a range dispatch can reach core.  Not product behaviour.\n"
                "    const offered = true;")

SHIM_FILE = "editor-shell-v2/paragraph-editor-client.js"
SHIM_FIND = """  if (PRE_DISPATCH_CODES.has(error?.code))
    return "refused-no-mutation";"""
SHIM_REPLACE = """  // DECLARED SHIM (tools/run_f059_wasm_predicate.py, finding 059's WASM half).
  // Not part of the product.  Every dispatched failure reports
  // `dispatched-unverified`, so the queue stays open long enough to save the
  // document and read what core actually did.  A refusal that says it
  // dispatched NOTHING is left alone, because that one is not a measurement
  // problem.  The product's real disposition for all of these is rollback.
  if (!(barrier && barrier.dispatched === false))
    return "dispatched-unverified";
  if (PRE_DISPATCH_CODES.has(error?.code))
    return "refused-no-mutation";"""

# The four, with the toolbar action id the product uses and the argument name
# the engine sends.
# Whether the toolbar would even deliver the press.  `button.click()` on a
# DISABLED button fires nothing, so an arm that pressed a masked-off button
# would show an unstyled document and read as "core did nothing" -- the exact
# false negative this measurement exists to avoid.  The page disables a button
# when the manifest does not declare that action for the current selection
# shape (updateGestureAffordance, web/e2-editor-app.js:131).
MARKER = "MARKERZZ"

READ_PRESSED = ("(() => { const b = document.querySelector('#toolbar "
                "button[data-action=\"ARG_ACTION\"]'); "
                "return b ? b.getAttribute('aria-pressed') : null; })()")

TYPE_MARKER = """(() => {
const field = document.querySelector('#text');
field.value = "ARG_TEXT";
field.dispatchEvent(new Event('input', { bubbles: true }));
return field.value;
})()"""

READ_BUTTON = """(() => {
const button = document.querySelector('#toolbar button[data-action="ARG_ACTION"]');
if (!button) return { present: false };
return { present: true, disabled: button.disabled, title: button.title };
})()"""

SLOTS = [
    ("set-bold", "Bold"),
    ("set-italic", "Italic"),
    ("set-underline", "Underline"),
    ("set-strikethrough", "Strikeout"),
]


def styled_runs(content: bytes, slot: str) -> list[dict]:
    """Every text run in the document whose own style has `slot` on."""
    styles = automatic_styles(content)
    root = ElementTree.fromstring(content)
    out = []
    for paragraph in root.iter("{%s}p" % NS["text"]):
        for span in paragraph.iter("{%s}span" % NS["text"]):
            name = span.get("{%s}style-name" % NS["text"])
            if slot_is_on(styles.get(name or "", {}), slot):
                out.append({
                    "text": span.text,
                    "style": name,
                    "paragraph": "".join(paragraph.itertext()),
                })
    return out


def place_selection(session, selection):
    """Put the document into the state the arm needs, and prove it happened.

    Returns (status, point, placed, state).  `placed` False means the arm's
    PRECONDITION never held and nothing downstream of it may be scored -- the
    third round of this probe reported `定位游標 失敗` on every arm, because
    x=0.30 fell past the end of an eight-character line (finding 052's shape),
    and read as "core did nothing".
    """
    if selection == "range":
        # Existing text, so the effect needs no insertion to become visible.
        evaluate(session, DRAG.replace("ARG_X1", "0.10").replace("ARG_Y1", "0.20")
                 .replace("ARG_X2", "0.55").replace("ARG_Y2", "0.20"))
        settled = wait_for(
            session,
            lambda s: s.get("state") in ("ready", "recoverable-error"), 60)
        status = (settled or {}).get("latency")
        return status, ("drag", "0.20"), True, evaluate(session, READ_STATE)

    # A collapsed caret, tried at several points rather than one: where a click
    # has to land is a property of the layout, not something to hard-code.
    status, point = None, None
    for point in (("0.12", "0.20"), ("0.12", "0.16"), ("0.20", "0.24"),
                  ("0.12", "0.28"), ("0.20", "0.32")):
        evaluate(session, POINT_AT.replace("ARG_X", point[0])
                 .replace("ARG_Y", point[1]))
        settled = wait_for(
            session,
            lambda s: s.get("state") in ("ready", "recoverable-error")
            and "定位游標" in (s.get("latency") or ""),
            60)
        status = (settled or {}).get("latency")
        if status and "失敗" not in status:
            break
    return (status, point, bool(status and "失敗" not in status),
            evaluate(session, READ_STATE))


def run_arm(session, base, slot_action, slot_name, press,
            fixture="f059-predicate-wide.odt", selection="collapsed") -> dict:
    """One arm, in a page of its own so the session is never reused."""
    navigate(session, base)
    deadline = time.monotonic() + 300
    state = None
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if state and state.get("state") == "ready":
            break
        time.sleep(0.5)
    if not state or state.get("state") != "ready":
        return {"reached": False, "why": "the page never became ready"}

    evaluate(session, INSTALL)
    opened = evaluate(session, OPEN_FILE
                      .replace("ARG_URL", f"./{fixture}")
                      .replace("ARG_NAME", fixture))
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        state = evaluate(session, READ_STATE)
        if (state or {}).get("doc") == fixture:
            break
        time.sleep(0.4)
    else:
        return {"reached": False, "why": f"the fixture never opened ({opened})"}
    # The label is set from the name the page was HANDED, so it says nothing
    # about the bytes: when the fetch 404'd, the product opened the error page
    # under this exact name and every downstream check agreed.  The witness is
    # text that exists only in the fixture -- the same rule
    # product-opens-a-document-the-user-chose already follows.
    witness = ("F059-BOLD-SOURCE" if "bold-source" in fixture else "F059-P00")
    time.sleep(1.5)

    caret_status, caret_point, caret_placed, selected = place_selection(
        session, selection)

    evaluate(session, CLEAR_TOAST)
    button = evaluate(session, READ_BUTTON.replace("ARG_ACTION", slot_action))
    toast = ""
    if press:
        evaluate(session, PRESS.replace("ARG_ACTION", slot_action))
        # Either the product says something, or it settles.  Both are answers;
        # a fixed sleep is not.
        wait_for(session,
                 lambda s: bool(s.get("toast"))
                 or s.get("state") == "recoverable-error",
                 60)
        toast = evaluate(session, READ_TOAST) or ""
    after = wait_for(session,
                     lambda s: s.get("state") in ("ready", "recoverable-error"),
                     60) or evaluate(session, READ_STATE) or {}
    # What the ENGINE says about the slot after the press, read off the
    # product's own aria-pressed.  Only bold and italic are answerable -- the
    # page deliberately renders no state for the other two.
    pressed_state = evaluate(session, READ_PRESSED.replace("ARG_ACTION",
                                                           slot_action))
    # The marker goes in through the product's own insert button, which is the
    # only text-entry path the product has.
    evaluate(session, TYPE_MARKER.replace("ARG_TEXT", MARKER))
    evaluate(session, PRESS.replace("ARG_ACTION", "insert-text"))
    wait_for(session, lambda s: s.get("state") in ("ready", "recoverable-error"),
             60)

    # A blocked session cannot save, and that is a result rather than a failure
    # of the probe: it means the shim did not hold for this arm.
    saves_before = evaluate(session, SAVE_COUNT) or 0
    evaluate(session, PRESS.replace("ARG_ACTION", "save"))
    captured = wait_saves(session, saves_before + 1)
    document = {}
    if captured:
        raw = evaluate(session, READ_SAVE.replace("ARG_INDEX", str(saves_before)))
        if raw:
            document = zip_report(base64.b64decode(raw["b64"]))

    content = document.get("content") or ""
    # An arm that could not be scored still reports everything it saw.  The
    # previous round returned early here and discarded the toast, the state and
    # the button -- so "the save produced nothing" arrived with no way to tell
    # whether the queue had blocked, and if so on which error.
    return {
        "reached": witness in content,
        "witness": witness,
        "why": None if witness in content else (
            f"the saved document does not contain {witness!r}"
            + (" -- nothing was saved at all" if not content
               else f"; it starts {content[:120]!r}")),
        "pressed": press,
        "toast": toast,
        "stateAfter": after.get("state"),
        "caretStatus": caret_status,
        "caretPoint": caret_point,
        "caretPlaced": bool(caret_status and "失敗" not in caret_status),
        "formatStateAfter": pressed_state,
        "markerInDocument": MARKER in (document.get("content") or ""),
        "button": button,
        # An arm whose button was disabled, or which produced no toast at all,
        # did not reach the engine and must not be read as "core did nothing".
        "dispatchReached": bool(press and button and button.get("present")
                                and not button.get("disabled") and toast),
        "saved": bool(captured),
        # zip_report puts the raw content.xml text under `content`.
        "contentXml": document.get("content"),
    }


def self_test() -> int:
    """The style reader has to be able to say no."""
    failures: list[str] = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    def doc(spans):
        styles = "".join(
            f'<style:style style:name="{n}" style:family="text">'
            f'<style:text-properties {a}/></style:style>' for n, a in spans["styles"])
        body = "".join(
            f'<text:p>{p}<text:span text:style-name="{n}">{t}</text:span></text:p>'
            for p, n, t in spans["paras"])
        return (
            '<?xml version="1.0"?><office:document-content '
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
            'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
            'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0">'
            f'<office:automatic-styles>{styles}</office:automatic-styles>'
            f'<office:body><office:text>{body}</office:text></office:body>'
            '</office:document-content>').encode()

    bold_doc = doc({"styles": [("T1", 'fo:font-weight="bold"')],
                    "paras": [("F059-P01", "T1", "hello")]})
    verify("a bold run is found", len(styled_runs(bold_doc, "Bold")) == 1)
    verify("that run reports its paragraph",
           styled_runs(bold_doc, "Bold")[0]["paragraph"] == "F059-P01hello")
    verify("a bold run is not read as italic",
           styled_runs(bold_doc, "Italic") == [])

    plain_doc = doc({"styles": [("T1", 'fo:language="zxx"')],
                     "paras": [("F059-P01", "T1", "hello")]})
    verify("an unstyled run is not found", styled_runs(plain_doc, "Bold") == [])

    # The control that matters: a style DECLARED but not used by any run.
    unused = doc({"styles": [("T1", 'fo:language="zxx"'),
                             ("E1Bold", 'fo:font-weight="bold"')],
                  "paras": [("F059-P01", "T1", "hello")]})
    verify("a declared-but-unused bold style is not found",
           styled_runs(unused, "Bold") == [])

    verify("the disposition shim patches exactly one place",
           (PROJECT / "dist" / SHIM_FILE).read_text(encoding="utf-8")
           .count(SHIM_FIND) == 1)
    verify("the gesture-mask shim patches exactly one place",
           (PROJECT / "dist" / MASK_FILE).read_text(encoding="utf-8")
           .count(MASK_FIND) == 1)

    for slot in ("Bold", "Italic", "Underline", "Strikeout"):
        verify(f"{slot} has a document property to read",
               slot in SLOT_PROPERTY)

    total = 11
    print(f"\nself-test: {total - len(failures)}/{total} checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    original = (PROJECT / "dist" / SHIM_FILE).read_text(encoding="utf-8")
    if original.count(SHIM_FIND) != 1:
        raise SystemExit(
            f"the shim expects exactly one occurrence of its pattern in "
            f"dist/{SHIM_FILE}; the tree moved under it")
    shimmed = original.replace(SHIM_FIND, SHIM_REPLACE)

    page = (PROJECT / "dist" / MASK_FILE).read_text(encoding="utf-8")
    if page.count(MASK_FIND) != 1:
        raise SystemExit(
            f"the gesture-mask shim expects exactly one occurrence of its "
            f"pattern in dist/{MASK_FILE}; the tree moved under it")
    masked = page.replace(MASK_FIND, MASK_REPLACE)

    scratch = Path(tempfile.mkdtemp(prefix="f059-wasm-"))
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root, {
        SHIM_FILE: shimmed.encode("utf-8"),
        MASK_FILE: masked.encode("utf-8"),
    })
    # Written directly, NOT through build_mirror's overrides.  build_mirror
    # walks the SOURCE tree and materialises an override only when it meets
    # that path there, so an override for a file dist/ does not contain is
    # silently dropped -- the product then fetches a 404 page and opens THAT as
    # the document.  Two rounds of this probe ran against
    # "Error response / Error code: 404" and produced plausible-looking nulls.
    for fixture in (FIXTURE, BOLD_SOURCE):
        (root / fixture.name).write_bytes(fixture.read_bytes())

    report: dict = {
        "schemaVersion": 1,
        "release": "f059-wasm-predicate",
        "browser": args.browser,
        "isTrusted": False,
        "shims": [{
            "file": SHIM_FILE,
            "what": "a barrier-less LOK_COMMAND_FAILED reports "
                    "dispatched-unverified instead of unknown-rollback, so the "
                    "queue stays open and the document can be saved",
            "cost": "this run does NOT measure the product's real disposition, "
                    "which is still rollback",
        }, {
            "file": MASK_FILE,
            "what": "the gesture mask is lifted, so a RANGE selection can reach "
                    "the same dispatch",
            "cost": "the product does not offer these actions on a range "
                    "(gestures: ['collapsed']); no statement about what a user "
                    "can do may cite this run",
        }],
        "servedShell": served_shell_identity(root),
        "arms": [],
    }

    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    try:
        base = f"http://127.0.0.1:{port}/e2-editor.html"
        wait_page(base)

        # Preflight: are the fixtures actually SERVED?
        #
        # Cheap, and it exists because the alternative cost two ~15-minute
        # browser rounds.  When the fixtures were missing from the mirror the
        # page fetched a 404 error page, LibreOffice imported that HTML as a
        # document, the status line showed the fixture's NAME because the page
        # is handed the name rather than reading it, and every arm produced a
        # plausible null.  Three seconds here answers it.
        import urllib.request
        for fixture in (FIXTURE, BOLD_SOURCE):
            url = f"http://127.0.0.1:{port}/{fixture.name}"
            with urllib.request.urlopen(url, timeout=30) as response:
                head = response.read(4)
                if response.status != 200 or head != b"PK\x03\x04":
                    raise SystemExit(
                        f"{fixture.name} is not served as a ZIP: status "
                        f"{response.status}, first bytes {head!r} -- the mirror "
                        "does not carry it and every arm would open a 404 page")
        report["preflight"] = "both fixtures are served and begin with PK\\x03\\x04"
        session = (ChromeSession if args.browser == "chrome"
                   else FirefoxSession)("f059-wasm")

        # `insert-path-carries-formatting` runs FIRST and uses a different
        # fixture: text that is ALREADY bold, with no command involved.  It is
        # what makes a null in the other arms mean something.  If a marker
        # inserted inside already-bold text comes back unstyled, then this
        # product's insert path does not carry caret formatting at all and no
        # arm below can say anything about what core did.
        # Collapsed-caret arms, and the control that makes their null mean
        # something.
        #
        # The range route is closed, and measured closed: with the page's
        # gesture mask lifted, all four dispatches came back
        # EDITOR_FORMAT_GESTURE_UNSUPPORTED -- the mask is enforced in the
        # ENGINE as well (editorGesturePermitted; relink queue item
        # p1-2-gesture-mask-inherited), so nothing reaches core and the document
        # cannot answer.  On a collapsed caret the format is a pending
        # attribute, so the only way to see it is to insert something.
        #
        # `insert-path-carries-formatting` runs FIRST, on a fixture whose text is
        # ALREADY bold, with no command involved.  If a marker inserted there
        # comes back unstyled, this product's insert path does not carry the
        # caret's formatting and no arm below can say anything about core.
        arms = [("insert-path-carries-formatting", None, "Bold", False,
                 "collapsed", "f059-predicate-bold-source.odt"),
                ("control", None, None, False, "collapsed",
                 "f059-predicate-wide.odt")]
        arms += [(f"collapsed-{action}", action, name, True, "collapsed",
                  "f059-predicate-wide.odt") for action, name in SLOTS]

        for label, action, slot_name, press, selection, fixture in arms:
            result = run_arm(session, base, action or "set-bold",
                             slot_name or "Bold", press, fixture, selection)
            result["fixture"] = fixture
            result["selection"] = selection
            # Every slot is read on every arm, so the control proves the
            # fixture is clean for all four rather than only for the one the
            # arm pressed.
            found = {}
            if result.get("contentXml"):
                for _, name in SLOTS:
                    found[name] = styled_runs(
                        result["contentXml"].encode("utf-8"), name)
            result["styledRuns"] = found
            result["arm"] = label
            result["slot"] = slot_name
            report["arms"].append(result)
            print(json.dumps({k: result.get(k) for k in
                              ("arm", "slot", "pressed", "reached", "stateAfter",
                               "saved", "dispatchReached", "button")},
                             ensure_ascii=False))
            print("   styled runs: " + json.dumps(
                {k: [r["text"] for r in v] for k, v in found.items()},
                ensure_ascii=False))
    finally:
        if session:
            try:
                session.close()
            except Exception:
                pass
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
