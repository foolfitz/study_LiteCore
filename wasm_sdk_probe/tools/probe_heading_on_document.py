#!/usr/bin/env python3
"""Press the product's 標題 button on a chosen paragraph of a chosen document.

Written 2026-09-03, during the manual round of the v12 cutover gate, because
the operator pressed 標題 on an ordinary paragraph of an ordinary document and
the session went to `recoverable-error` with:

    標題：MUTATION_OUTCOME_UNKNOWN：the postcondition read describes a
    different paragraph from the one this action was dispatched on

while `format-a-paragraph-changes-that-paragraph` PASSES on all eight banked
soak runs.

THE QUESTION THIS ANSWERS IS THE CONTROL, not the reproduction.  The
reproduction is already had -- a human did it.  What decides whether the
cutover is in trouble is whether the SHIPPED profile does the same thing with
the same document and the same paragraph: if it does, the candidate inherits a
defect; if it does not, the candidate introduces one.  So this runs the same
keystrokes on whichever profile it is pointed at, and the two runs are the
measurement.

It drives the product's own buttons -- the file input and the toolbar -- because
a barrier reached through the harness's own calls is not the barrier the
operator met.

Usage:
  probe_heading_on_document.py --document FILE.odt --anchor "在那之前" \
      [--candidate-profile e2-editor-v12 | --shipped] --out report.json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))
from r7_support import evaluate, wait_page                            # noqa: E402
from run_browser_probe import ChromeSession, free_port                # noqa: E402
from run_e2_c_page_smoke import navigate                              # noqa: E402
import run_e2_c_product_path as P                                     # noqa: E402


def serve(root: Path):
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
         "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_page(f"http://127.0.0.1:{port}/e2-editor.html")
    return port, proc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--anchor", required=True,
                        help="text at the start of the paragraph to act on")
    parser.add_argument("--candidate-profile", default=None)
    parser.add_argument("--shipped", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    if bool(args.candidate_profile) == bool(args.shipped):
        raise SystemExit("pass exactly one of --candidate-profile / --shipped")

    scratch = Path(tempfile.mkdtemp(prefix="heading-probe-"))
    root = scratch / "root"
    record = {
        "schemaVersion": 1, "release": "heading-on-a-real-document",
        "document": str(args.document),
        "documentSha256": hashlib.sha256(
            args.document.read_bytes()).hexdigest(),
        "anchor": args.anchor,
    }
    if args.shipped:
        shutil.copytree(PROJECT / "dist", root, symlinks=True,
                        ignore=shutil.ignore_patterns("profiles"))
        (root / "profiles").symlink_to(PROJECT / "dist" / "profiles")
        record["arm"] = {"kind": "shipped", "page": "dist/e2-editor-app.js"}
    else:
        manifest = (PROJECT / "dist" / "profiles"
                    / args.candidate_profile / "sdk-manifest.json")
        source = (PROJECT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
        page, pin_before, wasm = P.repointed_page(
            source, args.candidate_profile, manifest)
        P.build_mirror(PROJECT / "dist", root,
                       {"e2-editor-app.js": page.encode("utf-8")})
        record["arm"] = {
            "kind": "candidate", "profile": args.candidate_profile,
            "pageSha256": hashlib.sha256(page.encode("utf-8")).hexdigest(),
            "pinBefore": pin_before, "pinAfter": wasm[:16]}

    # A REPORT IS WRITTEN ON EVERY PATH.  The first version raised SystemExit
    # on its two early exits, which runs `finally` and then leaves before the
    # write -- so a probe that could not place the caret produced NO FILE and
    # an exit code of 0. That is finding 081's shape one layer up: the run that
    # explains itself is exactly the run that writes nothing.
    class _Abort(Exception):
        pass

    session = None
    server = None
    scan = []
    try:
        port, server = serve(root)
        session = ChromeSession("cold")
        navigate(session, f"http://127.0.0.1:{port}/e2-editor.html")
        evaluate(session, P.INSTALL)
        P.wait_for(session, lambda s: s.get("state") == "ready", 300)

        b64 = base64.b64encode(args.document.read_bytes()).decode()
        name = args.document.name
        evaluate(session, P.OPEN_BYTES.replace("ARG_B64", b64)
                 .replace("ARG_NAME", name))
        # WAIT ON THE DOCUMENT NAME, not on `ready`: the page is already ready
        # before the file is handed over. That trap cost this tree a false
        # cross-version finding once already.
        opened = P.wait_for(session, lambda s: (s.get("doc") or "") == name
                            and s.get("state") == "ready", 300) or {}
        record["opened"] = {"doc": opened.get("doc"),
                            "state": opened.get("state"),
                            "revision": opened.get("revision")}
        if opened.get("doc") != name:
            record["error"] = "the document never became the open one"
            record["verdict"] = "NOT MEASURED — the document never opened"
            raise _Abort()

        # Scan for the line whose ink starts where the anchor is; the product
        # path's own helpers do the geometry.
        # SETTLE FIRST. The document is `ready` before the canvas has painted,
        # and a scan run against an unpainted canvas finds no ink anywhere and
        # reports "the caret never reached the anchor" -- an instrument result
        # wearing a product result's words. Measured 2026-09-03: the first run
        # of this probe scanned fifteen positions and found ink at none.
        for _ in range(60):
            probe_ink = evaluate(session, P.LINE_INK.replace("ARG_Y", "0.20")) or {}
            if probe_ink.get("found"):
                break
            time.sleep(0.5)
        record["canvasPainted"] = bool(probe_ink.get("found"))

        placed = None
        for fraction in [f"{y:.3f}" for y in
                         [0.06 * i for i in range(1, 16)]]:
            ink = evaluate(session, P.LINE_INK.replace("ARG_Y", fraction)) or {}
            if not ink.get("found"):
                scan.append({"yFraction": fraction, "ink": "none"})
                continue
            clicks = P.caret_click_fractions(ink)
            P.place_caret_and_settle(session, P.POINT_AT, clicks["near"], fraction)
            para = evaluate(
                session,
                "(() => { const el = document.querySelector('#a11y-para'); "
                "return el ? el.textContent : null; })()")
            scan.append({"yFraction": fraction, "paragraph": (para or "")[:60]})
            if para and args.anchor in para:
                placed = {"yFraction": fraction, "paragraph": para[:120]}
                break
        record["caret"] = placed
        record["scan"] = scan
        if not placed:
            record["error"] = ("the anchor paragraph was never under the caret; "
                               "nothing was pressed")
            record["verdict"] = "NOT MEASURED — the caret never reached the anchor"
            record["scan"] = scan
            raise _Abort()

        evaluate(session, P.CLEAR_TOAST)
        evaluate(session, P.CLEAR_LATENCY)
        before = evaluate(session, P.READ_STATE) or {}
        record["before"] = {k: before.get(k) for k in
                            ("state", "revision", "checkpoint", "latency")}
        evaluate(session, P.PRESS.replace("ARG_ACTION", "set-paragraph-heading"))
        deadline = time.monotonic() + 60
        after = {}
        while time.monotonic() < deadline:
            after = evaluate(session, P.READ_STATE) or {}
            if "標題" in (after.get("latency") or ""):
                break
            if after.get("state") == "recoverable-error":
                break
            time.sleep(0.5)
        record["after"] = {k: after.get(k) for k in
                           ("state", "revision", "checkpoint", "latency",
                            "toast")}
        record["notice"] = evaluate(
            session,
            "(() => { const el = document.querySelector('#notice-text'); "
            "return el ? el.textContent : null; })()")
        record["verdict"] = (
            "FAILED — the session went to recoverable-error"
            if after.get("state") == "recoverable-error"
            else "the press completed without a recovery prescription")
    except _Abort:
        pass
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
        if server is not None:
            server.terminate()
        shutil.rmtree(scratch, ignore_errors=True)

    text = json.dumps(record, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
