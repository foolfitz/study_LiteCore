#!/usr/bin/env python3
"""The decisive measurement of the ODS milestone.

`handoff/PLAN-2026-09-03-ods-reading.md` §5, work item W2.

ONE QUESTION: does the a11y+calc core, as linked into the cutover candidate,
actually load and render a spreadsheet through LOK -- services, static
constructor map, type detection, headless Calc view, the `view-ready`
handshake, and `setAccessibilityState` at open, all at once?

WHY IT IS FIRST.  Everything else in the milestone assumes the core half is
already paid for by the accessibility work.  If `documentLoad` returns null, or
`view-ready` never arrives, or the accessibility switch wedges a Calc view, this
becomes an owner question and the calendar moves by weeks -- and nothing has
been spent on the shell.

HOW IT AVOIDS THE RUNNING GATE.  `dist/` is mirrored with symlinks into a
scratch root and the probe page is materialised there only; nothing under
`dist/`, `web/` or `sdk/` is written by a run.  The page itself lives in `web/`
in source form but is NOT in the product page's import graph and NOT in the five
bundle-scoped directories, so the shell bundle digest does not move -- verified
2026-09-03 against `e2/editor-shell-v2-bundle-v43.json`, `problems: []`.

THE NAME IS SPOOFED AND SAID SO.  Finding 013: `oxsdk_document_open` rejects any
name not ending `.odt` before the engine queue, while content detection then
reads the zip's own `mimetype`.  Reports carry `nameSpoofed: true` and are
diagnostic; they may never be quoted as the product opening a spreadsheet,
because the product refuses to.

Usage:
  probe_ods_on_profile.py --profile e2-editor-v12 \
      --fixture test-docs/ods/ladder/three-sheets-distinct.ods \
      --control dist/e1-fixtures/... --out report.json
"""
from __future__ import annotations

import argparse
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
from run_e2_c_product_path import build_mirror                        # noqa: E402

PAGE_HTML = PROJECT / "web" / "ods-decisive-probe.html"
PAGE_JS = PROJECT / "web" / "ods-decisive-probe-app.js"
NS = "__odsProbe"

HEAD_EXPR = """(() => {
  const r = window.NS;
  if (!r) return null;
  return { done: r.done, caseCount: r.caseCount ?? null,
           seen: (r.cases || []).length, fatal: r.fatal || null };
})()"""

CHUNK_EXPR = 'JSON.stringify((window.NS.cases || []).slice(START, END))'



def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def serve(root: Path):
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
         "--root", str(root)],
        cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_page(f"http://127.0.0.1:{port}/ods-decisive-probe.html")
    return port, proc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-editor-v12")
    parser.add_argument("--fixture", type=Path, action="append", default=[],
                        help="a spreadsheet to hand over; repeatable")
    parser.add_argument("--control", type=Path, default=None,
                        help="an ODT through the SAME path. Without it, a "
                             "failure cannot be told apart from a broken "
                             "instrument")
    parser.add_argument("--empty", type=Path, default=None,
                        help="an empty one-sheet ODS: its tile is what "
                             "'painted nothing' looks like")
    parser.add_argument("--truncated", type=Path, default=None,
                        help="a corrupt ODS: without it, 'did not open' and "
                             "'the worker died' look the same")
    parser.add_argument("--corpus", type=Path, default=None,
                        help="a manifest.json from tools/create_ods_corpus.py; "
                             "every entry is staged, in manifest order")
    parser.add_argument("--only", default=None,
                        help="with --corpus, keep only entries whose path "
                             "starts with this prefix (e.g. 'ladder/')")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--open-timeout-ms", type=int, default=180000,
                        help="the SDK's own `open` timeout, which is what a "
                             "TIMEOUT row reports. Raise it to tell 'did not "
                             "finish in 180 s' apart from 'does not finish'. "
                             "--timeout must exceed it or the run is cut off "
                             "before the open is")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.corpus is not None:
        manifest = json.loads(args.corpus.read_text(encoding="utf-8"))
        base = args.corpus.parent
        picked = [e for e in manifest["entries"]
                  if args.only is None or e["path"].startswith(args.only)]
        if not picked:
            raise SystemExit(
                f"--corpus selected nothing (--only {args.only!r}). A sweep "
                f"that searched zero files must be RED, not a clean report.")
        args.fixture = [base / e["path"] for e in picked]
        print(f"corpus: {len(args.fixture)} of {len(manifest['entries'])} entries")
    if not args.fixture:
        raise SystemExit("--fixture is required: a probe with nothing to open "
                         "would report cleanly and measure nothing")
    manifest = PROJECT / "dist" / "profiles" / args.profile / "sdk-manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"no manifest for {args.profile} at {manifest}")

    scratch = Path(tempfile.mkdtemp(prefix="ods-decisive-"))
    root = scratch / "root"
    overrides = {
        "ods-decisive-probe.html": PAGE_HTML.read_bytes(),
        "ods-decisive-probe-app.js": PAGE_JS.read_bytes(),
    }
    cases = []

    staged: list[dict] = []

    def stage(path: Path, kind: str, paint: bool = True) -> None:
        rel = f"ods-cases/{path.name}"
        staged.append({"case": path.name, "path": str(path),
                       "sha256": sha256_of(path), "kind": kind})
        overrides[rel] = path.read_bytes()
        spec = {"name": path.name, "file": "./" + rel, "kind": kind}
        if paint is not None:
            spec["paint"] = paint
        cases.append(spec)

    # ORDER IS THE CONTROLS FIRST. If the ODT control fails, the run says so
    # before any spreadsheet result invites a conclusion about Calc.
    if args.control:
        stage(args.control, "control-odt", True)
    if args.empty:
        stage(args.empty, "control-empty-ods", True)
    for fixture in args.fixture:
        stage(fixture, "spreadsheet", True)
    if args.truncated:
        stage(args.truncated, "control-truncated-ods", False)

    overrides["ods-cases.json"] = json.dumps(
        cases, ensure_ascii=False).encode("utf-8")
    build_mirror(PROJECT / "dist", root, overrides)
    # `build_mirror` materialises an override only when it MEETS that path while
    # walking the source, so an override for a file `dist/` does not have is
    # silently dropped -- which is every file this probe adds. Measured
    # 2026-09-03: the first run died with a 404 on its own page. Written after
    # the mirror rather than by changing `build_mirror`, whose contract the
    # product path depends on.
    for relative, payload in overrides.items():
        target = root / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    for relative in overrides:
        if not (root / relative).is_file():
            raise SystemExit(f"mirror is missing {relative}: the probe would "
                             f"have served a 404 and reported it as a product "
                             f"failure")

    record = {
        "schemaVersion": 1,
        "release": "m4-ods-decisive-runner",
        "profile": args.profile,
        "nameSpoofed": True,
        "evidenceClass": "diagnostic",
        # Keyed by case NAME rather than by position: the first version zipped
        # `cases` against a rebuilt list of the same paths, which is a second
        # implementation of the ordering and would mislabel every input the day
        # the two drifted.
        "inputs": staged,
    }
    session = None
    server = None
    try:
        port, server = serve(root)
        session = ChromeSession("cold")
        query = ("?profile=" + args.profile
                 + "&openTimeoutMs=" + str(args.open_timeout_ms))
        navigate(session, f"http://127.0.0.1:{port}/ods-decisive-probe.html"
                          + query)
        # POLL A SUMMARY, FETCH THE BODY IN SLICES.
        #
        # CDP's websocket refuses a frame over 1 MiB, and the first attempt at
        # a 306-fixture sweep pulled the whole accumulated report in one
        # `Runtime.evaluate` -- the connection closed with 1009 and the run
        # died AFTER every measurement had been taken. Nothing about the
        # product was wrong and nothing about it was learned.
        deadline = time.monotonic() + args.timeout
        head = {}
        while time.monotonic() < deadline:
            # Built by substitution, not by an f-string: brace escaping
            # applies only to the f-string PART of an implicit concatenation,
            # so `}}` in a plain continuation survives as two braces and Chrome
            # answers `SyntaxError: Unexpected token '}'`. Measured 2026-09-03.
            head = evaluate(session, HEAD_EXPR.replace("NS", NS)) or {}
            if head.get("done"):
                break
            time.sleep(2.0)
        record["timedOut"] = not head.get("done")
        record["progress"] = head

        cases = []
        total = int(head.get("seen") or 0)
        step = 5
        for start in range(0, total, step):
            chunk = evaluate(
                session,
                CHUNK_EXPR.replace("NS", NS)
                .replace("START", str(start)).replace("END", str(start + step)))
            cases.extend(json.loads(chunk) if chunk else [])
        # NON-EMPTINESS: a sweep that retrieved nothing must not read as a
        # sweep that found nothing wrong.
        if total and len(cases) != total:
            raise SystemExit(f"retrieved {len(cases)} of {total} cases; a "
                             f"partial sweep must not be banked as a sweep")
        record["page"] = {"done": head.get("done"),
                          "caseCount": head.get("caseCount"),
                          "cases": cases}
        # THE OPEN TIMEOUT, CARRIED OUT OF THE PAGE.  The page puts it in its
        # own report object, but this tool does not copy that object -- it
        # projects a few named fields -- so adding it there alone left every
        # saved report without it.  Read from the page, not from `args`: what
        # matters is the value the `open()` call actually used.
        record["openTimeoutMs"] = evaluate(
            session,
            ('window["NS"] ? window["NS"].openTimeoutMs : null'
             .replace("NS", NS)))
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
        if server is not None:
            server.terminate()
        shutil.rmtree(scratch, ignore_errors=True)

    # THE VERDICT IS COMPUTED, not left to a reader's eye -- but it is
    # deliberately narrow: this probe answers "did it load and paint", and
    # nothing about fidelity. G3 is a different measurement.
    page = record.get("page") or {}
    by_kind = {}
    for case in page.get("cases") or []:
        by_kind.setdefault(case.get("kind"), []).append(case)
    control = (by_kind.get("control-odt") or [{}])[0]
    sheets = by_kind.get("spreadsheet") or []
    record["verdict"] = {
        "controlOdtOpened": bool(control.get("opened")),
        "spreadsheetsOpened": [
            {"name": c.get("name"), "opened": bool(c.get("opened")),
             "parts": (c.get("opened") or {}).get("parts"),
             "viewReady": bool(c.get("viewReady")),
             "workerCrashed": bool(c.get("workerCrashed")),
             "error": c.get("error")}
            for c in sheets],
        "note": "If the ODT control did not open, NOTHING here is about Calc: "
                "the instrument is the first suspect and the spreadsheet rows "
                "must not be read.",
    }
    text = json.dumps(record, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
