#!/usr/bin/env python3
"""Photograph the canvas on both cores, at rest and after a caret placement.

Finding 075 established by counting that the accessibility core puts a few
stray dark pixels into the far-left and far-right columns after a caret is
placed, and that those pixels bridge two lines into one band which the density
filter then discards -- losing two paragraphs the user can plainly see.

Everything about that is a count.  Counts cannot tell a FOCUS RECTANGLE from
uninitialised memory, and the two would be answered differently: a rectangle is
the engine drawing something real and the harness must exclude it knowingly; a
garbage strip is off-page noise that was never content.

So: take the picture.  The rule this repo keeps re-learning is that pixels
cannot distinguish causes -- but that is about inferring STATE from pixels.
Here the pixels ARE the subject, and looking at them is the measurement.

Usage:
  capture_canvas_edges.py --profile a11y-gate0 --out-dir DIR
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, free_port  # noqa: E402
from run_e2_c_page_smoke import navigate  # noqa: E402
from probe_a11y_gate0 import gate_mirror, wait_until  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent

GRAB = "(() => document.querySelector('#canvas').toDataURL('image/png'))()"


def grab(session, out: Path, label: str) -> dict:
    url = evaluate(session, GRAB)
    if not isinstance(url, str) or not url.startswith("data:image/png;base64,"):
        return {"label": label, "error": repr(url)[:200]}
    blob = base64.b64decode(url.split(",", 1)[1])
    out.write_bytes(blob)
    return {"label": label, "file": str(out), "bytes": len(blob)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="a11y-gate0")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--after-action", default=None,
                    help="dispatch this product action once the caret is "
                         "placed, then capture again. Added 2026-08-23: with "
                         "the off-page garbage excluded the two cores agree at "
                         "rest and after a caret, and disagree only once the "
                         "document has been EDITED -- 9 bands against 10. A "
                         "shot of the state that disagrees is the only thing "
                         "that says whether a line wrapped or something else "
                         "is being drawn")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {"schemaVersion": 1, "profile": args.profile, "shots": []}

    scratch = Path(tempfile.mkdtemp(prefix="canvas-edges-"))
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
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 1
        time.sleep(1.5)
        # AT REST FIRST, and it is the control: both cores agree on 9 bands
        # here, so whatever the picture shows at rest is NOT the difference.
        record["shots"].append(
            grab(session, out_dir / f"{args.profile}-at-rest.png", "at-rest"))
        _s0, bands0 = pp.stable_bands(session)
        record["bandsAtRest"] = len(bands0)

        clicks = pp.caret_click_fractions(
            evaluate(session, pp.LINE_INK.replace("ARG_Y", "0.24")) or {})
        pp.place_caret_and_settle(session, pp.POINT_AT, clicks["near"], "0.24")
        time.sleep(1.2)
        record["shots"].append(
            grab(session, out_dir / f"{args.profile}-after-caret.png",
                 "after-caret"))
        _s1, bands1 = pp.stable_bands(session)
        record["bandsAfterCaret"] = len(bands1)
        record["bandGeometryAfterCaret"] = [
            {k: b[k] for k in ("top", "bottom", "first", "last", "density")}
            for b in bands1]

        if args.after_action:
            record["actionPressed"] = evaluate(
                session, pp.PRESS.replace("ARG_ACTION", args.after_action))
            time.sleep(3.0)
            record["shots"].append(
                grab(session, out_dir / f"{args.profile}-after-action.png",
                     f"after-{args.after_action}"))
            scan2, bands2 = pp.stable_bands(session)
            record["bandsAfterAction"] = len(bands2)
            record["offPageInkAfterAction"] = scan2.get("offPageInk")
            record["pageOpaqueAfterAction"] = scan2.get("pageOpaque")
            record["bandGeometryAfterAction"] = [
                {k: b[k] for k in ("top", "bottom", "first", "last", "density")}
                for b in bands2]
        record["outcome"] = "SEE_SHOTS"
    finally:
        try:
            session.close()
        finally:
            server.terminate()
    (out_dir / f"{args.profile}-capture.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
