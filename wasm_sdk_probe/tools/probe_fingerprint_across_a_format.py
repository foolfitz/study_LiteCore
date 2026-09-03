#!/usr/bin/env python3
"""Does the paragraph fingerprint change when the action under test changes it?

Finding 086's hypothesis, measured rather than argued.

The format barrier decides "is the readback the paragraph I dispatched on?" by
comparing `a11yContentHash` at dispatch against `a11yContentHash` at readback.
That hash is taken over the paragraph's content **with `listPrefixLength`
characters stripped** (`src/probe_engine.cpp`, and the comment there says so).

`set-paragraph-heading` turns a body paragraph into an outline-numbered heading,
and finding 074 established that LOK's reported `listPrefixLength` for such a
heading is not the prefix length. **So the action under test may change the very
input the identity is computed from** -- in which case the barrier is not
detecting a wrong paragraph, it is detecting its own oracle moving.

This reads `paragraphFingerprint`, `listPrefixLength`, `contentLength` and the
projected paragraph text for ONE paragraph, before the press and after it, with
the caret returned to the same place. It presses through the product's own
toolbar button.

It asserts nothing: two numbers and their inputs, before and after. The
conclusion is in the numbers or it is not there.

Usage:
  probe_fingerprint_across_a_format.py --document FILE.odt --anchor "在那之前" \
      --profile e2-editor-v12 --out report.json
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

READ_A11Y = """(() => {
  const state = window.__pp?.lastState || null;
  const para = document.querySelector('#a11y-para');
  return JSON.stringify({paraText: para ? para.textContent : null});
})()"""


def read_editor_state(session) -> dict:
    """The engine's own editor state, read through the page's SDK handle."""
    raw = evaluate(session, "window.__fpProbe ? "
                            "JSON.stringify(window.__fpProbe) : null")
    return json.loads(raw) if raw else {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--profile", default="e2-editor-v12")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    scratch = Path(tempfile.mkdtemp(prefix="fingerprint-"))
    root = scratch / "root"
    manifest = PROJECT / "dist" / "profiles" / args.profile / "sdk-manifest.json"
    source = (PROJECT / "web" / "e2-editor-app.js").read_text(encoding="utf-8")
    page, pin_before, wasm = P.repointed_page(source, args.profile, manifest)
    # PUBLISH THE ENGINE'S EDITOR STATE, in the mirror only.
    #
    # The page keeps it in a module-scoped `session`, unreachable from CDP. The
    # accessor is APPENDED TO THE SAME MODULE, where that variable is in scope,
    # and only into the scratch mirror -- `dist/`, `web/` and `sdk/` are
    # untouched, and the running cutover gate does not see it.
    #
    # This makes the page bytes differ from the shipping page, which is why the
    # report is stamped diagnostic. It reads state and changes none: a
    # `setInterval` copying a reference.
    probe_page = page + (
        "\n\n// APPENDED BY tools/probe_fingerprint_across_a_format.py "
        "(diagnostic; mirror only)\n"
        "setInterval(() => {\n"
        "  try { window.__fpProbe = session?.state?.snapshot?.editorState "
        "?? null; }\n"
        "  catch (error) { window.__fpProbeError = String(error); }\n"
        "}, 100);\n")
    record_page_differs = True
    P.build_mirror(PROJECT / "dist", root,
                   {"e2-editor-app.js": probe_page.encode("utf-8")})

    record = {
        "schemaVersion": 1, "release": "fingerprint-across-a-format",
        "profile": args.profile,
        "shippingPageSha256": hashlib.sha256(page.encode("utf-8")).hexdigest(),
        "evidenceClass": "diagnostic",
        "why": "an accessor for the engine's editorState is appended to the "
               "mirrored page, so these bytes are NOT the page a cutover would "
               "ship. It reads and changes nothing, but the stamp is not "
               "optional.",
        "document": str(args.document),
        "documentSha256": hashlib.sha256(args.document.read_bytes()).hexdigest(),
        "anchor": args.anchor,
        "hypothesis": "the fingerprint is hash(content[listPrefixLength:]) and "
                      "set-paragraph-heading changes listPrefixLength, so the "
                      "same paragraph fingerprints differently before and after",
        "reads": [],
    }
    session = None
    server = None
    try:
        port = free_port()
        server = subprocess.Popen(
            [sys.executable, str(PROJECT / "web" / "serve.py"),
             "--port", str(port), "--root", str(root)],
            cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_page(f"http://127.0.0.1:{port}/e2-editor.html")
        session = ChromeSession("cold")
        navigate(session, f"http://127.0.0.1:{port}/e2-editor.html")
        evaluate(session, P.INSTALL)
        P.wait_for(session, lambda s: s.get("state") == "ready", 300)

        b64 = base64.b64encode(args.document.read_bytes()).decode()
        evaluate(session, P.OPEN_BYTES.replace("ARG_B64", b64)
                 .replace("ARG_NAME", args.document.name))
        opened = P.wait_for(session,
                            lambda s: (s.get("doc") or "") == args.document.name
                            and s.get("state") == "ready", 300) or {}
        record["opened"] = {"doc": opened.get("doc"), "state": opened.get("state")}
        time.sleep(2.0)
        record["accessor"] = {
            "present": evaluate(session, "typeof window.__fpProbe"),
            "error": evaluate(session, "window.__fpProbeError || null"),
            "keys": evaluate(session, "window.__fpProbe ? "
                                      "JSON.stringify(Object.keys(window.__fpProbe)) "
                                      ": null"),
            "appendedMarker": evaluate(
                session,
                "(async () => { const r = await fetch('./e2-editor-app.js'); "
                "const t = await r.text(); "
                "return t.includes('__fpProbe'); })()"),
        }

        # FIND THE ANCHOR'S LINE. `LINE_INK` reports `available`, not `found` --
        # the first version of this probe invented the second name and concluded
        # the canvas had never painted. It had; the reader was wrong.
        def place(fraction: str):
            ink = evaluate(session, P.LINE_INK.replace("ARG_Y", fraction)) or {}
            if not ink.get("available"):
                return None
            clicks = P.caret_click_fractions(ink)
            P.place_caret_and_settle(session, P.POINT_AT, clicks["near"], fraction)
            # The accessor republishes on a 100 ms timer; reading in the same
            # breath as the click reads the state before the click. The first
            # version did, saw an empty paragraph at all 58 positions, and
            # reported "the anchor was never reached" -- about a document that
            # was right there.
            time.sleep(0.35)
            state = read_editor_state(session)
            return ((state.get("caretParagraph") or {}).get("text")) or None

        target = None
        scan = []
        for i in range(2, 60):
            fraction = f"{i * 0.02:.3f}"
            para = place(fraction)
            scan.append({"y": fraction, "para": (para or "")[:40]})
            if para and args.anchor in para:
                target = fraction
                break
        record["scan"] = scan
        record["targetFraction"] = target
        if target is None:
            record["error"] = "anchor never reached"
            raise _Abort()

        def snapshot(label: str) -> dict:
            # THE FIELDS LIVE UNDER `a11y`, not at the top of `editorState`.
            # The first version of this probe read them from the top level, got
            # `null` for every one, and would have reported "the fingerprint did
            # not change" -- the answer the hypothesis wanted, produced by
            # reading nothing.
            state = read_editor_state(session)
            a11y = state.get("a11y") or {}
            caret_para = state.get("caretParagraph") or {}
            row = {
                "label": label,
                "paragraphFingerprint": a11y.get("paragraphFingerprint"),
                "fingerprintUsable": a11y.get("fingerprintUsable"),
                "listPrefixLength": a11y.get("listPrefixLength"),
                "contentLength": a11y.get("contentLength"),
                "paragraphFresh": a11y.get("paragraphFresh"),
                "position": a11y.get("position"),
                "caretParagraphFingerprint": caret_para.get("fingerprint"),
                "caretParagraphLength": caret_para.get("length"),
                "paragraphText": (caret_para.get("text") or "")[:80],
            }
            record["reads"].append(row)
            return row

        time.sleep(0.35)
        before = snapshot("before-the-press")
        evaluate(session, P.CLEAR_TOAST)
        evaluate(session, P.CLEAR_LATENCY)
        evaluate(session, P.PRESS.replace("ARG_ACTION", "set-paragraph-heading"))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            st = evaluate(session, P.READ_STATE) or {}
            if "標題" in (st.get("latency") or "") or st.get("state") == "recoverable-error":
                break
            time.sleep(0.5)
        record["afterPress"] = {k: (evaluate(session, P.READ_STATE) or {}).get(k)
                                for k in ("state", "revision", "latency", "toast")}
        # RETURN THE CARET TO THE SAME PLACE and read again. If the paragraph is
        # now a heading and its fingerprint moved, the identity is a function of
        # the formatting the action changed.
        place(target)
        time.sleep(0.35)
        after = snapshot("after-the-press-same-caret")

        record["verdict"] = {
            "fingerprintChanged":
                before["paragraphFingerprint"] != after["paragraphFingerprint"],
            "listPrefixLengthChanged":
                before["listPrefixLength"] != after["listPrefixLength"],
            "sameParagraphText":
                before["paragraphText"] == after["paragraphText"],
        }
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


class _Abort(Exception):
    pass


if __name__ == "__main__":
    raise SystemExit(main())
