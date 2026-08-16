#!/usr/bin/env python3
"""SPEC E2-C phase D5: serve the operator round, or run the machine half.

Two modes, and the second is the point of this file existing before an operator
is ever asked for time:

  --serve         print a URL and wait.  The operator drives the real product
                  page in their own browser; the D5 page observes it.
  --machine-half  drive the same page headlessly, dispatch SYNTHETIC events, and
                  prove the harness records them as untrusted and the analyzer
                  refuses to pass a cell backed by them.

A harness that cannot be shown to reject a fake gesture is a harness that would
accept one, and D5 is the only phase whose entire subject is `isTrusted`.
"""

from __future__ import annotations

import argparse
import base64
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e1_support import sha256, write_json  # noqa: E402
from r7_support import evaluate, wait_page  # noqa: E402
from run_browser_probe import ChromeSession, FirefoxSession, free_port  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
# The CURRENT generation: this file attests what a round ran on, so it moves
# with the shell.  v3 was the generation D5's machine half and the first two
# operator rounds ran on; v6 is what the four established operator cells ran on;
# v7 carries finding 051's fix and v8 finding 052's.
BUNDLE = PROJECT / "e2" / "editor-shell-v2-bundle-v9.json"


def bundle_digest() -> str | None:
    """The digest the round has to leave alone.

    Read from the manifest the E2-C bundle tool writes, not recomputed here: a
    second implementation of the digest is a second thing that can drift.
    """
    if not BUNDLE.is_file():
        return None
    return json.loads(BUNDLE.read_text(encoding="utf-8")).get("bundleSha256")


def artifact_hashes(profile: str) -> dict[str, str]:
    directory = PROJECT / "dist" / "profiles" / profile
    return {
        "profile": profile,
        "wasmSha256": sha256(directory / "probe.wasm"),
        "loaderSha256": sha256(directory / "probe.js"),
        "workerSha256": sha256(directory / "sdk-worker.js"),
    }


SYNTHETIC = r"""
(() => {
  const win = globalThis.__e2c_d5_frame();
  const doc = win.document;
  const canvas = doc.querySelector("#canvas");
  const rect = canvas.getBoundingClientRect();
  const at = (dx, dy) => ({ clientX: rect.left + dx, clientY: rect.top + dy,
                            bubbles: true, cancelable: true, pointerId: 1,
                            pointerType: "mouse", isPrimary: true, buttons: 1 });
  // A synthetic drag: down, three moves, up.  Every one of these is
  // isTrusted:false by construction -- that is the whole point.
  canvas.dispatchEvent(new win.PointerEvent("pointerdown", at(40, 40)));
  for (const step of [60, 90, 120])
    canvas.dispatchEvent(new win.PointerEvent("pointermove", at(step, 40)));
  canvas.dispatchEvent(new win.PointerEvent("pointerup", at(120, 40)));
  const sink = doc.querySelector("#sink");
  sink.dispatchEvent(new win.KeyboardEvent("keydown",
    { key: "c", ctrlKey: true, bubbles: true }));
  sink.dispatchEvent(new win.CompositionEvent("compositionstart",
    { data: "", bubbles: true }));
  sink.dispatchEvent(new win.CompositionEvent("compositionend",
    { data: "測試", bubbles: true }));
  return true;
})()
"""

SYNTHETIC_SAVE = r"""
(() => {
  const win = globalThis.__e2c_d5_frame();
  // Not the product's save -- that needs a loaded document and an operator's
  // pace.  This proves the CAPTURE PATH: a Blob handed to createObjectURL in
  // the product's realm reaches the harness.  If this does not work, no
  // operator round can produce a saved document either.
  const blob = new win.Blob([new Uint8Array([80, 75, 3, 4, 1, 2, 3, 4])],
                            { type: "application/vnd.oasis.opendocument.text" });
  win.URL.createObjectURL(blob);
  return true;
})()
"""


def machine_half(args) -> int:
    digest_before = bundle_digest()
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    session = None
    metrics = None
    exported = None
    saves: list[dict] = []
    try:
        base = f"http://127.0.0.1:{port}/e2-c-d5.html"
        wait_page(base)
        session_class = ChromeSession if args.browser == "chrome" else FirefoxSession
        session = session_class("cold")
        session.navigate(f"{base}?profile={args.profile}&machine=half")
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            state = evaluate(session, "globalThis.__e2c_d5 || null")
            if state and state.get("ready"):
                break
            time.sleep(0.5)
        else:
            raise SystemExit("the D5 page never became ready")

        # One cell's worth of synthetic gestures, recorded under a real cell id
        # so the analyzer judges them exactly as it would judge an operator's.
        evaluate(session, "globalThis.__e2c_d5_begin('d5-pointer-drag-single')")
        evaluate(session, SYNTHETIC)
        evaluate(session, SYNTHETIC_SAVE)
        time.sleep(1.0)
        evaluate(session, "globalThis.__e2c_d5_end('d5-pointer-drag-single')")
        evaluate(session, "globalThis.__e2c_d5_finish()")
        metrics = evaluate(session, "globalThis.__e2c_d5 || null")
        # The operator's hand-back path, exercised by the machine half.  The
        # export button is the last step of a session driven by a person at
        # 1am; a button nobody ever pressed in a test is a button that fails
        # then.  Checked here because this is the only run that is automated.
        exported = evaluate(
            session,
            "(() => { const p = globalThis.__e2c_d5_export_payload?.(); "
            "return p ? {cells: Object.keys(p.cells || {}).length, "
            "events: (p.events || []).length, "
            "capturedSaves: (p.capturedSaves || []).length, "
            "hasShims: Array.isArray(p.shims)} : null; })()")
        count = evaluate(session, "globalThis.__e2c_d5_save_count()") or 0
        for index in range(int(count)):
            saves.append(evaluate(session, f"globalThis.__e2c_d5_save({index})"))
    finally:
        if session is not None:
            session.close()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    digest_after = bundle_digest()
    metrics = metrics or {}
    metrics["artifact"] = artifact_hashes(args.profile)
    metrics["browserName"] = args.browser
    metrics["shellBundle"] = {
        "before": digest_before, "after": digest_after,
        "unchanged": digest_before == digest_after,
    }
    evidence = args.output / "machine-half" / args.browser
    # Evidence is written once.  The default --output is D5's own directory, so
    # a second machine-half run would silently replace the result a verdict
    # cites -- and it would be bound to a DIFFERENT shell generation than the
    # one that verdict was made on, which is the whole reason a re-run exists.
    # Same rule as session-attestation: append, never replace.
    if (evidence / "result.json").exists() and not args.allow_overwrite:
        raise SystemExit(
            f"{evidence / 'result.json'} already exists.  Point --output at a "
            f"new directory (one per shell generation), or pass "
            f"--allow-overwrite if replacing it is what you mean.")
    (evidence / "saved").mkdir(parents=True, exist_ok=True)
    written = []
    for entry in saves:
        if not entry or not entry.get("b64"):
            continue
        name = f"{entry['label']}.bin"
        (evidence / "saved" / name).write_bytes(base64.b64decode(entry["b64"]))
        written.append({"label": entry["label"], "file": f"saved/{name}"})
    metrics["capturedSaves"] = written
    metrics["operatorExport"] = exported
    write_json(evidence / "result.json", metrics)
    print(json.dumps({
        "evidence": str(evidence),
        "events": len(metrics.get("events") or []),
        "capturedSaves": len(written),
        "shellBundleUnchanged": metrics["shellBundle"]["unchanged"],
    }, indent=2, ensure_ascii=False))
    return 0


def serve(args) -> int:
    port = free_port()
    # A fixed port when asked, because an operator session is a human at a
    # window: a URL that changes every time the server restarts is a URL that
    # gets mistyped.
    if args.port:
        port = args.port
    url = (f"http://127.0.0.1:{port}/e2-c-d5.html?profile={args.profile}")
    print(json.dumps({
        "operatorUrl": url,
        "note": "Open this in a REAL browser window.  The product page runs "
                "unmodified in the iframe; every gesture is recorded with its "
                "isTrusted flag.  Per cell: press the begin button, do the "
                "gesture WITH REAL INPUT, press the done button.  When all four "
                "are done press 'finish' and then the export button -- it saves "
                "one JSON file with the metrics and every captured document.  "
                "Hand that file back; nothing else needs collecting.",
        "runbook": "handoff/RUNBOOK-operator-d5.md",
        "evidence": str(args.output / "operator"),
    }, indent=2, ensure_ascii=False), flush=True)
    # The operator round has no attestation of its own otherwise: the machine
    # half records the shell bundle digest before and after, and a round driven
    # by a person deserves the same claim -- "observing it did not change it" is
    # not something the page can say about itself.
    digest_before = bundle_digest()
    evidence = args.output / "operator"
    # Ctrl+C already runs the finally below (KeyboardInterrupt), but a plain
    # SIGTERM would not, and "the attestation is missing" is a bad thing to
    # discover after the operator has gone to bed.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        subprocess.run(
            [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port)],
            cwd=PROJECT, check=False)
    finally:
        digest_after = bundle_digest()
        evidence.mkdir(parents=True, exist_ok=True)
        # One file per server session, never an overwrite.  This used to write a
        # single `session-attestation.json`, and on 2026-08-16 a server that was
        # still alive from an earlier round exited AFTER the shell bundle had
        # moved v4 -> v6 and rewrote the file with v6's digest.  The value was
        # not wrong for the round that had just run, but it was decided by when
        # a background process happened to die rather than by what any round ran
        # on -- and it is evidence a verdict cites.  Evidence is appended to, not
        # replaced.
        target = evidence / "session-attestation.json"
        index = 2
        while target.exists():
            target = evidence / f"session-attestation-{index}.json"
            index += 1
        write_json(target, {
            "schemaVersion": 1,
            "release": "spec-e2c-d5",
            "mode": "operator",
            "profile": args.profile,
            "artifact": artifact_hashes(args.profile),
            "shellBundle": {"before": digest_before, "after": digest_after,
                            "unchanged": digest_before == digest_after},
            "note": "Written when the operator's server stops.  The round's own "
                    "result.json comes from the page's export button; this file "
                    "is what the harness can attest to from outside it.",
        })
        print(json.dumps({
            "attestation": str(target),
            "shellBundleUnchanged": digest_before == digest_after,
        }, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine-half", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--browser", choices=("chrome", "firefox"), default="chrome")
    parser.add_argument("--profile", default="e2-editor-v2")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--port", type=int, default=0,
                        help="fixed port for --serve, so the operator's URL is "
                             "stable across restarts")
    parser.add_argument("--allow-overwrite", action="store_true",
                        help="replace an existing machine-half result instead "
                             "of refusing; evidence is written once by default")
    parser.add_argument("--output", type=Path,
                        default=PROJECT.parent / "findings" / "evidence" / "sdk-e2"
                        / "e2-c-validation" / "d5")
    args = parser.parse_args()
    if args.machine_half:
        return machine_half(args)
    if args.serve:
        return serve(args)
    parser.error("pass --machine-half or --serve")


if __name__ == "__main__":
    sys.exit(main())
