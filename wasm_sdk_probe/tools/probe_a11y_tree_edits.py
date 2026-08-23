#!/usr/bin/env python3
"""What does the accessibility tree do WHILE the document is being edited?

The last unmeasured thing before roadmap 3.4's projection can be designed, and
it decides the projection's SHAPE: if the tree tracks edits, the projection can
walk it on demand; if it goes stale or unsafe, the projection has to be rebuilt
from events instead.  Two different programs.

Every snapshot in `TREE-SHAPE.md` was taken at rest.  This one is not.

IT ALSO RUNS A PRE-REGISTERED FALSIFICATION, and that is worth stating before
the result exists.  Roadmap 3.4's route A rested on "when the document's
skeleton changes, it changes because of an action WE dispatched, so the shell
knows".  fable's adjudication called that false and named three counter-cases,
predicting **3/3 would change structure with no structure action from us**:

  * typing `- ` at the start of a paragraph (autocorrect makes it a list);
  * pressing Enter at the end of a heading (follow-on style);
  * undo/redo across a paragraph split (redo is document-level, no wire id).

The prediction is in `research/DESIGN-2026-08-22-aria-projection.md` §8.6,
written before this file existed.  The verdict does not depend on the outcome
-- route A is already dead on the collision measurement -- so this is the
record for the next person who proposes it, not a tie-breaker.

Usage:
  probe_a11y_tree_edits.py --browser chrome [--profile a11y-tree] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate  # noqa: E402
from probe_a11y_gate0 import READ_A11Y, gate_mirror, wait_until  # noqa: E402
from run_e2_c_product_path import (  # noqa: E402
    LINE_INK, POINT_AT, PRESS, TYPE_KEY, TYPE_WHEREVER_FOCUS_IS,
    caret_click_fractions, place_caret_and_settle, stable_bands,
)

PROJECT = Path(__file__).resolve().parent.parent

FOCUS_SINK = "(() => { document.querySelector('#sink').focus(); return true; })()"


def snapshot(session, label: str) -> dict:
    """The tree as the engine reports it right now, reduced to its shape.

    The nodes themselves are not kept: this asks whether the tree TRACKS the
    document, and that is answered by counts and by the focused node, not by
    three hundred records per step.
    """
    raw = evaluate(session, READ_A11Y) or {}
    a11y = raw.get("a11y") if isinstance(raw, dict) else None
    tree = (a11y or {}).get("tree")
    out: dict = {"label": label}
    if not isinstance(tree, dict):
        out["tree"] = repr(tree)[:120]
        return out
    if "unavailable" in tree:
        out["unavailable"] = tree["unavailable"]
        return out
    nodes = tree.get("nodes", [])
    depth1 = [n for n in nodes if n.get("depth") == 1]
    root = next((n for n in nodes if n.get("depth") == 0), {})
    focused = [n for n in nodes if n.get("focused")]
    out.update({
        "emitted": tree.get("emitted"),
        "rootChildCount": root.get("childCount"),
        "depth1": len(depth1),
        "headings": sum(1 for n in depth1 if n.get("role") == 26),
        "paragraphs": sum(1 for n in depth1 if n.get("role") == 41),
        "numbered": sum(1 for n in depth1 if n.get("isNumbered")),
        "focusedCount": len(focused),
        "focused": ({
            "role": focused[0].get("role"),
            "textLength": focused[0].get("textLength"),
            "textHead": focused[0].get("textHead"),
            "numberingLevel": focused[0].get("numberingLevel"),
            "isNumbered": focused[0].get("isNumbered"),
        } if focused else None),
        "paragraphTextFromLok": (a11y or {}).get("paragraphText"),
        # The bounds travel with the reading, so a reader can tell the
        # document's edge from the probe's without opening the source.
        "caps": {k: tree.get(k) for k in
                 ("maxNodes", "maxChildrenPerNode", "maxDepth")},
    })
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome",), default="chrome")
    parser.add_argument("--profile", default="a11y-tree")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    record: dict = {
        "schemaVersion": 1,
        "release": "a11y-tree-under-edit",
        "question": "does the accessibility tree track the document while it "
                    "is edited, and is walking it then safe?",
        "prediction": "research/DESIGN-2026-08-22-aria-projection.md 8.6 -- "
                      "fable, before this ran: 3/3 of the counter-cases change "
                      "structure with no structure action dispatched by us",
        "profile": args.profile,
        "steps": [],
    }

    scratch = Path(tempfile.mkdtemp(prefix="a11y-edits-"))
    record["mirror"] = gate_mirror(scratch, args.profile)
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"),
         "--port", str(port), "--root", record["mirror"]["root"]],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/e2-editor.html"
    wait_page(base)
    session = ChromeSession("cold")
    try:
        navigate(session, base)
        state = wait_until(session, lambda s: s.get("state") == "ready", 180)
        if state.get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = "the page never reached ready"
            return finish(record, args)
        time.sleep(1.0)
        record["steps"].append(snapshot(session, "at-rest"))

        scan, bands = stable_bands(session)
        targets = [b for b in bands if (b["last"] - b["first"]) > 40]
        if len(targets) < 4:
            record["outcome"] = "NOT_ESTABLISHED"
            record["why"] = f"only {len(targets)} bands to aim at"
            return finish(record, args)

        def put_caret(index: int) -> None:
            band = targets[index]
            ink = evaluate(session, LINE_INK.replace(
                "ARG_Y", f"{band['centreFraction']:.5f}")) or {}
            clicks = caret_click_fractions(ink)
            place_caret_and_settle(session, POINT_AT, clicks["near"],
                                   f"{band['centreFraction']:.5f}")
            time.sleep(1.2)

        # 1. TYPING -- does the tree see the new character?
        put_caret(2)
        record["steps"].append(snapshot(session, "caret-placed"))
        evaluate(session, FOCUS_SINK)
        evaluate(session, TYPE_WHEREVER_FOCUS_IS.replace("ARG_TEXT", "ZZ"))
        time.sleep(2.5)
        record["steps"].append(snapshot(session, "after-typing-ZZ"))

        # 2. SPLITTING -- a structure change we DID dispatch. The control for
        #    the two below: if the tree does not move here, it does not track
        #    structure at all and nothing after this means anything.
        record["breakPressed"] = evaluate(
            session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
        time.sleep(2.5)
        record["steps"].append(snapshot(session, "after-paragraph-break"))

        # 3. A LIST STYLE we dispatched -- the second control.
        record["listPressed"] = evaluate(
            session, PRESS.replace("ARG_ACTION", "set-list-unordered"))
        time.sleep(2.5)
        record["steps"].append(snapshot(session, "after-set-list-unordered"))

        # 4. THE FALSIFICATION: type "- " at the start of a plain paragraph and
        #    dispatch NO structure action. If the paragraph becomes a list, the
        #    engine changed the skeleton on its own.
        put_caret(1)
        # HOME FIRST, and the first run of this arm is why it is here.
        #
        # Without it the caret sat wherever the click landed and `- ` went
        # into the MIDDLE of the line (`E- 1-LC-ISOLATED...`). Autocorrect
        # turns `- ` into a list only at the START of a paragraph, so the arm
        # measured nothing and would have read as "autocorrect does not
        # happen" -- a conclusion about LibreOffice produced by where a click
        # landed.
        evaluate(session, FOCUS_SINK)
        record["homePressed"] = evaluate(
            session, TYPE_KEY.replace("ARG_KEY", "Home").replace("ARG_CTRL", "false"))
        time.sleep(1.0)
        record["steps"].append(snapshot(session, "before-autocorrect"))
        evaluate(session, FOCUS_SINK)
        evaluate(session, TYPE_WHEREVER_FOCUS_IS.replace("ARG_TEXT", "- "))
        time.sleep(3.0)
        record["steps"].append(snapshot(session, "after-typing-dash-space"))
        # Autocorrect fires on the NEXT word boundary, not on the space that
        # completes `- `. Typing a word and a space is what commits it.
        evaluate(session, TYPE_WHEREVER_FOCUS_IS.replace("ARG_TEXT", "x "))
        time.sleep(3.0)
        record["steps"].append(snapshot(session, "after-typing-x-space"))

        # 5. FOLLOW-ON STYLE -- the counter-case our own insert path DOES
        #    reach. We dispatch `insert-paragraph-break` at the end of a
        #    HEADING and ask what the new paragraph's ROLE is. We asked for a
        #    break; if what we get is a paragraph of a different kind, a shell
        #    keeping its own shadow would have to have guessed that, and
        #    "the shell knows because it dispatched the action" is false for
        #    the part that matters -- the STRUCTURE, not the split.
        put_caret(0)
        evaluate(session, FOCUS_SINK)
        evaluate(session, TYPE_KEY.replace("ARG_KEY", "End").replace("ARG_CTRL", "false"))
        time.sleep(1.2)
        record["steps"].append(snapshot(session, "caret-at-end-of-heading"))
        record["headingBreakPressed"] = evaluate(
            session, PRESS.replace("ARG_ACTION", "insert-paragraph-break"))
        time.sleep(2.5)
        record["steps"].append(snapshot(session, "after-break-on-heading"))

        record["outcome"] = "SEE_STEPS"
        record["howToRead"] = (
            "`after-paragraph-break` and `after-set-list-unordered` are the "
            "CONTROLS: they are structure changes this harness dispatched, so "
            "if the tree does not move there it does not track structure and "
            "nothing else here can be read. "
            "`after-typing-dash-space` is the falsification: a list appearing "
            "with no structure action dispatched means the engine changed the "
            "skeleton by itself.")
    finally:
        try:
            session.close()
        finally:
            server.terminate()
    return finish(record, args)


def finish(record: dict, args) -> int:
    text = json.dumps(record, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
