#!/usr/bin/env python3
"""Does a document saved on the candidate open on the profile we would revert to?

Revert condition 2 of `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`. A
revert is only a pointer flip if nothing written under the candidate is
unreadable by the incumbent.  Grepped first, so the question could be narrowed
before it was driven: the shell uses no localStorage, no sessionStorage and no
indexedDB, and the checkpoint lives in memory -- so the ONLY cross-version
artifact is the saved ODT.

Both directions are driven, because a revert is not the only crossing: a user
who saved under the incumbent before the cutover opens that file under the
candidate afterwards.

Everything goes through the product's own buttons -- the file input and the save
button -- because a round-trip performed by the harness would be a round-trip
nobody ships.

## Provenance

This is the 2026-08-28 probe from
`findings/evidence/queue-v11-cutover-soak-not-started/probe_odt_roundtrip.py`,
which hard-coded `e2-editor-v11`, lifted into `tools/` and parameterised when
the candidate became `e2-editor-v12`.  **That copy is not edited**: it is the
record of what the 2026-08-28 measurement ran, and evidence in this tree is not
rewritten to serve a later run.

## The trap this probe was built around, kept verbatim

Wait on the document NAME, not on `ready`.  The page is ALREADY ready before the
file input is touched, so a predicate of `state == "ready"` returns instantly and
the probe reports on the boot fixture -- which is what the first run of this did:
`doc` came back `list-contexts.odt` in BOTH directions and nothing had been
opened at all.  It reported the sentinel lost both ways, which would have been a
cross-version incompatibility finding, the most expensive kind, because it argues
against a cutover with evidence that is not about the cutover.  *Which document
is in front of you* and *are you ready* are different sentences, and `doc` is the
only field that answers the first.

Usage:
  probe_odt_roundtrip.py --candidate e2-editor-v12 [--out report.json]
"""
import argparse
import base64
import json
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

MARK = "ROUNDTRIP-SENTINEL"


def serve(root: Path):
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
         "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_page(f"http://127.0.0.1:{port}/e2-editor.html")
    return port, proc


def ready(session, timeout=180):
    deadline = time.monotonic() + timeout
    state = {}
    while time.monotonic() < deadline:
        state = evaluate(session, P.READ_STATE) or {}
        if state.get("state") == "ready":
            return state
        time.sleep(0.5)
    return state


def open_page(session, port):
    navigate(session, f"http://127.0.0.1:{port}/e2-editor.html")
    evaluate(session, P.INSTALL)
    return ready(session)


def type_and_save(session, text):
    """Type through the product's own commit path, then press its save button."""
    ink = evaluate(session, P.LINE_INK.replace("ARG_Y", "0.28")) or {}
    clicks = P.caret_click_fractions(ink)
    P.place_caret_and_settle(session, P.POINT_AT, clicks["near"], "0.28")
    floor = P.revision_of(evaluate(session, P.READ_STATE))
    evaluate(session, P.COMPOSE.replace("ARG_TEXT", text))
    P.wait_for(session,
               lambda s, f=floor: P.revision_of(s) is not None and f is not None
               and P.revision_of(s) > f, 60)
    return P.capture_save(session, evaluate(session, P.SAVE_COUNT) or 0)


def latest_save_b64(session) -> str:
    index = (evaluate(session, P.SAVE_COUNT) or 1) - 1
    return evaluate(session, P.READ_SAVE.replace("ARG_INDEX", str(index)))["b64"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default="e2-editor-v12")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    candidate = args.candidate
    manifest = PROJECT / "dist" / "profiles" / candidate / "sdk-manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"no manifest for {candidate} at {manifest}")

    scratch = Path(tempfile.mkdtemp(prefix="odt-roundtrip-"))
    candidate_root = scratch / "candidate"
    shipped_page = (PROJECT / "dist" / "e2-editor-app.js").read_text(
        encoding="utf-8")
    page, pin_before, wasm = P.repointed_page(shipped_page, candidate, manifest)
    P.build_mirror(PROJECT / "dist", candidate_root,
                   {"e2-editor-app.js": page.encode("utf-8")})

    import hashlib
    report = {
        "mark": MARK,
        "candidate": candidate,
        # SAY WHICH BYTES. A round-trip result quoted against a candidate whose
        # page hash nobody recorded is a result about an unnamed thing.
        "candidatePageSha256": hashlib.sha256(page.encode("utf-8")).hexdigest(),
        "shippedPageSha256": hashlib.sha256(
            shipped_page.encode("utf-8")).hexdigest(),
        "pinBefore": pin_before, "pinAfter": wasm[:16],
    }
    session = None
    servers = []
    try:
        cand_port, s1 = serve(candidate_root); servers.append(s1)
        ship_port, s2 = serve(PROJECT / "dist"); servers.append(s2)
        session = ChromeSession("cold")

        # --- written on the CANDIDATE -----------------------------------
        report["candidateOpened"] = open_page(session, cand_port).get("state")
        saved_on_candidate = type_and_save(session, MARK + "-FROM-CANDIDATE")
        report["savedOnCandidate"] = {
            "isOdt": P.is_an_odt(saved_on_candidate),
            "bytes": saved_on_candidate.get("bytes"),
            "hasMark": (MARK + "-FROM-CANDIDATE")
                       in (saved_on_candidate.get("content") or ""),
        }
        b64_candidate = latest_save_b64(session)

        # --- opened on the SHIPPED page, which is what a revert means ----
        report["shippedOpened"] = open_page(session, ship_port).get("state")
        report["candidateToShippedDispatch"] = evaluate(
            session, P.OPEN_BYTES.replace("ARG_B64", b64_candidate)
            .replace("ARG_NAME", "from-candidate.odt"))
        after = P.wait_for(session,
                           lambda s: (s.get("doc") or "") == "from-candidate.odt"
                           and s.get("state") == "ready", 300) or {}
        report["candidateToShipped"] = {"state": after.get("state"),
                                        "doc": after.get("doc"),
                                        "toast": after.get("toast")}
        resaved = P.capture_save(session, evaluate(session, P.SAVE_COUNT) or 0)
        report["candidateToShipped"].update({
            "reopenedIsOdt": P.is_an_odt(resaved),
            "markSurvived": (MARK + "-FROM-CANDIDATE")
                            in (resaved.get("content") or ""),
            "lines": [l["text"][:40] for l in P.document_lines(resaved)][:6],
        })

        # --- the other crossing: saved on the incumbent, opened on the
        #     candidate -- the user who saved before the cutover.
        saved_on_shipped = type_and_save(session, MARK + "-FROM-SHIPPED")
        report["savedOnShipped"] = {"isOdt": P.is_an_odt(saved_on_shipped),
                                    "bytes": saved_on_shipped.get("bytes")}
        b64_shipped = latest_save_b64(session)
        report["candidateReopened"] = open_page(session,
                                                cand_port).get("state")
        report["shippedToCandidateDispatch"] = evaluate(
            session, P.OPEN_BYTES.replace("ARG_B64", b64_shipped)
            .replace("ARG_NAME", "from-shipped.odt"))
        after = P.wait_for(session,
                           lambda s: (s.get("doc") or "") == "from-shipped.odt"
                           and s.get("state") == "ready", 300) or {}
        report["shippedToCandidate"] = {"state": after.get("state"),
                                        "doc": after.get("doc"),
                                        "toast": after.get("toast")}
        resaved = P.capture_save(session, evaluate(session, P.SAVE_COUNT) or 0)
        report["shippedToCandidate"].update({
            "reopenedIsOdt": P.is_an_odt(resaved),
            "markSurvived": (MARK + "-FROM-SHIPPED")
                            in (resaved.get("content") or ""),
            "lines": [l["text"][:40] for l in P.document_lines(resaved)][:6],
        })

        # The verdict, computed here rather than left to a reader's eye.
        both = (report["candidateToShipped"], report["shippedToCandidate"])
        report["ok"] = all(
            d.get("doc") and d.get("state") == "ready"
            and d.get("reopenedIsOdt") and d.get("markSurvived")
            for d in both) and report["savedOnCandidate"]["isOdt"]
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
        for s in servers:
            s.terminate()
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
