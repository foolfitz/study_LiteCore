#!/usr/bin/env python3
"""What does a screen reader actually get from the editor page?

Roadmap section 3.4's baseline, and the instrument its gate needs.

WHY THIS IS NOT A HUMAN-ONLY QUESTION.  "A screen reader has to read it, so a
person has to try it" is a *falsifiable claim*, not a category -- finding 073
made exactly that mistake about IME composition and CDP's
`Input.imeSetComposition` refuted it.  The accessibility tree is what every
screen reader consumes, the browser builds it, and CDP exposes it
(`Accessibility.getFullAXTree`).  So the before-picture is measurable, and so
is any projection built to replace it.

This tool does NOT judge.  It reports the tree, because section 3.4's own gate
(G3.4-1, research/DESIGN-2026-08-22-aria-projection.md) is not written against a
threshold yet and inventing one from the first output is the order this tree
refuses.

Usage:
  probe_aria_projection.py --browser chrome [--profile a11y-gate0] [--out FILE]
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
from probe_a11y_gate0 import gate_mirror, wait_until  # noqa: E402
from run_e2_c_product_path import (  # noqa: E402
    LINE_INK, POINT_AT, caret_click_fractions, place_caret_and_settle,
    stable_bands,
)

# What the projection put in the tree, read from the tree rather than from the
# DOM.  The two differ -- that difference is the whole reason this instrument
# was chosen over `document.querySelector`, and reading the DOM here would be
# the 068 mistake again (measuring the page and calling it the other side).
READ_REGION = """(() => {
const el = document.querySelector('#a11y-para');
return el ? { text: el.textContent, reason: el.dataset.reason,
              offers: document.querySelector('#a11y-doc')?.dataset.offers }
          : { missing: true };
})()"""

PROJECT = Path(__file__).resolve().parent.parent


def ax_tree(session) -> list[dict]:
    """The tree the browser hands to assistive technology, flattened."""
    session.call("Accessibility.enable")
    result = session.call("Accessibility.getFullAXTree") or {}
    nodes = []
    for node in result.get("nodes", []):
        if node.get("ignored"):
            continue
        nodes.append({
            "nodeId": node.get("nodeId"),
            "role": (node.get("role") or {}).get("value"),
            "name": (node.get("name") or {}).get("value"),
            "description": (node.get("description") or {}).get("value"),
            "value": (node.get("value") or {}).get("value"),
            "childIds": node.get("childIds") or [],
        })
    return nodes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chrome",), default="chrome",
                        help="chrome only: Firefox's WebDriver session has no "
                             "CDP here, and the AX tree is a CDP domain")
    parser.add_argument("--profile", default="a11y-gate0")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    record: dict = {
        "schemaVersion": 1,
        "release": "aria-projection-baseline",
        "question": "what does a screen reader get from the editor page today?",
        "design": "research/DESIGN-2026-08-22-aria-projection.md",
        "profile": args.profile,
        "judges": None,
        "why": "Reported, not scored. G3.4-1 has no threshold yet and writing "
               "one from this output would make the highest-uncertainty "
               "question in section 3.4 a formality -- the same order the a11y "
               "gate 0 prediction was written to avoid.",
    }

    scratch = Path(tempfile.mkdtemp(prefix="aria-baseline-"))
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
        record["booted"] = state.get("state")
        if state.get("state") != "ready":
            record["outcome"] = "NOT_ESTABLISHED"
            record["why2"] = "the page never reached ready"
            return finish(record, args)
        time.sleep(1.0)

        nodes = ax_tree(session)
        record["nodeCount"] = len(nodes)
        record["nodes"] = nodes
        record["regionAtLoad"] = evaluate(session, READ_REGION)

        # G3.4-1 terms 2 and 3: three placements, and each reading has to match
        # the paragraph it was aimed at.  Three different strings would also be
        # produced by a counter -- the MATCH is what a page doing nothing
        # cannot fake, which is why it carries the conjunction (PREDICTION.md).
        scan, bands = stable_bands(session)
        targets = [b for b in bands if (b["last"] - b["first"]) > 40][:3]
        record["bandsFound"] = len(bands)
        record["placements"] = []
        for index, band in enumerate(targets):
            ink = evaluate(session, LINE_INK.replace(
                "ARG_Y", f"{band['centreFraction']:.5f}")) or {}
            clicks = caret_click_fractions(ink)
            place_caret_and_settle(session, POINT_AT, clicks["near"],
                                   f"{band['centreFraction']:.5f}")
            time.sleep(1.0)
            placed = ax_tree(session)
            carried = [n for n in placed
                       if "E1-LC" in str(n.get("name") or "")
                       or "E1-LC" in str(n.get("value") or "")]
            record["placements"].append({
                "index": index,
                "yFraction": round(band["centreFraction"], 5),
                "region": evaluate(session, READ_REGION),
                "axNodesCarryingText": carried,
                "axReading": (carried[0].get("name") if carried else None),
            })
        readings = [p["axReading"] for p in record["placements"]]
        record["distinctAxReadings"] = len(set(r for r in readings if r))
        record["axReadings"] = readings
        # THE NUMBER SECTION 3.4 IS ABOUT.  A screen reader reads the document
        # through this tree; if nothing in it carries document text, the
        # document is not readable no matter what the canvas draws.
        fixture_marker = "E1-LC"
        record["nodesCarryingDocumentText"] = [
            n for n in nodes
            if fixture_marker in str(n.get("name") or "")
            or fixture_marker in str(n.get("value") or "")
        ]
        record["documentTextInTree"] = bool(record["nodesCarryingDocumentText"])
        record["roles"] = sorted({str(n.get("role")) for n in nodes})
        record["outcome"] = "SEE_NODES"
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
    summary = {k: v for k, v in record.items() if k != "nodes"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
