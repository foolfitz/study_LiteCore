#!/usr/bin/env python3
"""Finding 093, phase 3 side-question: does S2 put a target over the canvas?

S2 moves `#a11y-doc` onto the caret.  `#sink` -- the element 069 already put
there -- carries `pointer-events: none`, and the comment above it says exactly
why (`web/e2-editor.html:92-96`): "moving it over the canvas puts a 1px
transparent target on top of the drawing surface, and the canvas's own
pointerdown is what places the caret".  `.a11y-only` has no such declaration
(`web/e2-editor.html:65-70`), so S2 would put a second element there without
it.

`clip-path: inset(50%)` is on `.a11y-only` and clip-path participates in hit
testing, so the hazard may already be neutralised -- which is a reason to
MEASURE it rather than to assert either way.  `document.elementFromPoint` at
the caret is the question in one call.

Nothing under web/ or dist/ is written; the S2 edit goes on a scratch mirror.

Usage: probe_093_s2_hit_test.py [--profile e2-editor-v12] [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))

from r7_support import evaluate, wait_page                      # noqa: E402
from run_browser_probe import ChromeSession, free_port          # noqa: E402
from run_e2_c_page_smoke import READ_STATE, navigate            # noqa: E402
from run_e2_c_product_path import build_mirror, repointed_page  # noqa: E402
from probe_093_fix_shape_oracle import (                        # noqa: E402
    CLICK_AT, CLEAR_LATENCY, SWITCH_FIXTURE, shape_overrides, wait_state)


HIT_TEST = """(() => {
const sink = document.querySelector('#sink');
const doc = document.querySelector('#a11y-doc');
const canvas = document.querySelector('#canvas');
if (!sink || !doc || !canvas) return null;
const box = sink.getBoundingClientRect();
const x = Math.round(box.left + box.width / 2);
const y = Math.round(box.top + box.height / 2);
const hit = document.elementFromPoint(x, y);
const stack = document.elementsFromPoint(x, y).map(
  (n) => n.id || n.tagName.toLowerCase());
return {
  sinkOffsetTop: sink.offsetTop, sinkOffsetLeft: sink.offsetLeft,
  docOffsetTop: doc.offsetTop, docOffsetLeft: doc.offsetLeft,
  docRidesTheCaret: Math.abs(doc.offsetTop - sink.offsetTop) <= 1
                    && Math.abs(doc.offsetLeft - sink.offsetLeft) <= 1,
  probedAt: { x, y },
  hit: hit ? (hit.id || hit.tagName.toLowerCase()) : null,
  stack,
  docPointerEvents: getComputedStyle(doc).pointerEvents,
  sinkPointerEvents: getComputedStyle(sink).pointerEvents,
  docClipPath: getComputedStyle(doc).clipPath,
};
})()"""


def measure(session, base, fixture, timeout) -> dict:
    navigate(session, base)
    booted = wait_state(session, lambda s: s.get("state") in
                        ("ready", "stopped", "expired"), timeout)
    if not booted or booted.get("state") != "ready":
        return {"outcome": "NOT_ESTABLISHED",
                "why": f"page state {(booted or {}).get('state')!r}"}
    picked = evaluate(session, SWITCH_FIXTURE.replace("ARG_FIXTURE", fixture))
    if not (picked or {}).get("available"):
        return {"outcome": "NOT_ESTABLISHED", "why": "fixture not offered"}
    wait_state(session, lambda s: s.get("state") == "ready", timeout)
    time.sleep(6.0)
    evaluate(session, CLEAR_LATENCY)
    evaluate(session, CLICK_AT.replace("ARG_X", "0.18").replace("ARG_Y", "0.09"))
    settled = wait_state(session,
                         lambda s: "定位游標" in (s.get("latency") or ""), 25)
    latency = (settled or {}).get("latency") or ""
    time.sleep(0.6)
    return {"outcome": "MEASURED", "placementLatency": latency,
            "placementOk": "定位游標" in latency and "失敗" not in latency,
            "hitTest": evaluate(session, HIT_TEST)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-editor-v12")
    parser.add_argument("--fixture", default="a11y-audible")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--out")
    args = parser.parse_args()

    root = PROJECT / "dist"
    page_js_source = (PROJECT / "web" / "e2-editor-app.js").read_text("utf-8")
    page_html = (PROJECT / "web" / "e2-editor.html").read_text("utf-8")
    manifest = root / "profiles" / args.profile / "sdk-manifest.json"
    page_js, _, _ = repointed_page(page_js_source, args.profile, manifest)

    report = {"schemaVersion": 1, "finding": "093", "phase": "phase-3-side",
              "evidenceClass": "diagnostic", "profile": args.profile,
              "question": "does S2 place a hit-testable element over the canvas "
                          "at the caret, the way #sink would without its "
                          "pointer-events: none?",
              "shapes": {}}
    for shape in ("S0", "S2"):
        files, _ = shape_overrides(shape, page_js, page_html)
        mirror = Path(tempfile.mkdtemp(prefix=f"f093hit-{shape}-")) / "root"
        build_mirror(root, mirror, files)
        port = free_port()
        server = subprocess.Popen(
            [sys.executable, str(PROJECT / "web" / "serve.py"),
             "--port", str(port), "--root", str(mirror)],
            cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        session = None
        try:
            base = f"http://127.0.0.1:{port}/e2-editor.html"
            wait_page(base)
            session = ChromeSession("cold")
            session.call("Emulation.setDeviceMetricsOverride",
                         {"width": 1920, "height": 1080,
                          "deviceScaleFactor": 1, "mobile": False})
            report["shapes"][shape] = measure(session, base, args.fixture,
                                              args.timeout)
        finally:
            if session is not None:
                session.close()
            server.terminate()
            server.wait(timeout=10)
        print(f"{shape}: {report['shapes'][shape].get('outcome')}",
              file=sys.stderr)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
