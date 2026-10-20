#!/usr/bin/env python3
"""ONE short browser smoke of the read-only ODS viewer DRAFT (plan W9, gate G9).

What it does: mirrors `dist/` into a scratch root with symlinks (the pattern of
`probe_ods_on_profile.py`), writes the draft viewer into the MIRROR only, serves
it, and drives the page's own file input (CDP `DOM.setFileInputFiles`) with
`three-sheets-distinct.ods` and then, in the same page and the same run,
`empty-one-sheet.ods`.  Nothing under `dist/` is written, no profile is touched,
and the product page's import graph does not reach any of these files.

What it does NOT claim: the viewer opens the spreadsheet under a spoofed `.odt`
name because W7 (engine `documentType`, `set_part`, `part_name`, ods open) does
not exist.  Every report is `nameSpoofed: true` / `evidenceClass: "diagnostic"`
and can never be quoted as the product opening an ODS.  The first-tile
comparison is RECORDED, not a gate.

Preconditions are checked here and the run REFUSES to start otherwise: another
agent's timing-sensitive measurement must not share the machine with this one.
  - the KDE wallet is unlocked (`b false`), else headless Chrome hangs;
  - no other Chrome is running;
  - the 1-minute load average is below 1.0.

  run_ods_viewer_draft_smoke.py --check-only      preconditions only, exit 3 if busy
  run_ods_viewer_draft_smoke.py --selftest        the judge against synthetic red cases
  run_ods_viewer_draft_smoke.py [--profile e2-editor-v14] [--out report.json]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))

PAGE_FILES = {
    # published path in the mirror -> source file
    "ods-viewer.html": PROJECT / "web" / "ods-viewer.html",
    "ods-viewer-app.js": PROJECT / "web" / "ods-viewer-app.js",
    "viewer-shell/ods-viewer-session.js": PROJECT / "viewer-shell" / "ods-viewer-session.js",
    "viewer-shell/w7-adapter.js": PROJECT / "viewer-shell" / "w7-adapter.js",
    "viewer-shell/viewer-error.js": PROJECT / "viewer-shell" / "viewer-error.js",
    # 2026-10-20 (SPEC-M4 §5.2): the session reads the package before the engine.
    "viewer-shell/odf-package-probe.js": PROJECT / "viewer-shell" / "odf-package-probe.js",
}
# SPEC-M4 §5.1: the page hard-codes the engine it is for.  A mirror run on
# another, already linked profile rewrites that ONE literal in the MIRROR's copy
# of the page -- never in web/ -- and records both hashes.
WORKER_LITERAL = 'workerUrl: "./profiles/ods-viewer-v1/sdk-worker.js"'


def retarget_page(payload: bytes, profile: str) -> bytes:
    text = payload.decode("utf-8")
    if text.count(WORKER_LITERAL) != 1:
        raise SystemExit(f"ods-viewer-app.js: {WORKER_LITERAL!r} occurs "
                         f"{text.count(WORKER_LITERAL)} times, want exactly 1")
    return text.replace(WORKER_LITERAL,
                        f'workerUrl: "./profiles/{profile}/sdk-worker.js"').encode("utf-8")

FIXTURES = [
    PROJECT / "test-docs" / "ods" / "ladder" / "three-sheets-distinct.ods",
    PROJECT / "test-docs" / "ods" / "ladder" / "empty-one-sheet.ods",
]
DEFAULT_OUT = (PROJECT.parent / "findings" / "evidence" / "m4-ods"
               / "W9-viewer-draft" / "smoke-report.json")
WALLET_CMD = ["busctl", "--user", "get-property", "org.freedesktop.secrets",
              "/org/freedesktop/secrets/collection/kdewallet",
              "org.freedesktop.Secret.Collection", "Locked"]

DOM_EXPR = """(() => {
  const tabs = [...document.querySelectorAll('#tab-strip [role="tab"]')].map((t) => ({
    text: t.textContent, enabled: !t.disabled, part: t.dataset.part,
    selected: t.getAttribute('aria-selected') === 'true', title: t.title || null }));
  const fields = Object.fromEntries([...document.querySelectorAll('#status [data-field]')]
    .map((n) => [n.dataset.field, n.textContent]));
  return { tabs, fields,
    banner: [...document.querySelectorAll('#diagnostic-banner [data-fallback]')]
      .map((n) => n.dataset.fallback),
    bannerHidden: document.getElementById('diagnostic-banner').hidden,
    canvases: document.querySelectorAll('#tiles canvas').length,
    message: document.getElementById('message').textContent };
})()"""

RUN_EXPR = """(() => {
  const r = window.__odsViewer.runs[INDEX];
  if (!r) return null;
  return { settled: r.settled, file: r.file, inputBytes: r.inputBytes ?? null,
           inputSha256: r.inputSha256 ?? null, opened: r.opened, refused: r.refused,
           error: r.error, tileDraws: r.tileDraws, engineEvents: r.engineEvents,
           firstTile: r.firstTile, finalState: r.finalState ?? null };
})()"""


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def preconditions() -> dict:
    """Facts about the machine, and whether the run may start."""
    wallet = subprocess.run(WALLET_CMD, capture_output=True, text=True)
    wallet_text = wallet.stdout.strip() or wallet.stderr.strip()
    listing = subprocess.run(["pgrep", "-af", "[c]hrom"], capture_output=True, text=True)
    mine = Path(__file__).name
    chromes = [line for line in listing.stdout.splitlines() if line and mine not in line]
    load1 = os.getloadavg()[0]
    reasons = []
    if wallet_text != "b false":
        reasons.append(f"KDE wallet is not 'b false': {wallet_text!r}")
    if chromes:
        reasons.append(f"{len(chromes)} Chrome process(es) already running")
    if not load1 < 1.0:
        reasons.append(f"1-minute load {load1:.2f} is not below 1.0")
    return {"wallet": wallet_text, "chromeProcessCount": len(chromes),
            "chromeProcessesSample": [c[:140] for c in chromes[:3]],
            "load1": round(load1, 2), "ok": not reasons, "reasons": reasons}


# ---------------------------------------------------------------- the judge --
def expectation(identifier: str, ok: bool, detail) -> dict:
    return {"id": identifier, "ok": bool(ok), "detail": detail}


def judge(report: dict) -> list[dict]:
    """The pass/fail expectations.  A pure function of the report, so it can be
    shown red on synthetic input (--selftest) without a browser."""
    runs = report.get("runs") or []
    three = next((r for r in runs if r.get("file") == "three-sheets-distinct.ods"), None)
    one = next((r for r in runs if r.get("file") == "empty-one-sheet.ods"), None)
    out = []
    if three is None or one is None:
        # Zero runs must be RED, never "zero problems".
        return [expectation("both-fixtures-were-run", False,
                            f"runs seen: {[r.get('file') for r in runs]}")]
    out.append(expectation("both-fixtures-were-run", True, [r["file"] for r in runs]))

    def opened(r):
        return bool(r.get("opened")) and not r.get("error") and not r.get("refused")

    out.append(expectation("opened", opened(three) and opened(one),
                           {r["file"]: bool(r.get("opened")) for r in (three, one)}))

    def parts(r):
        return (r.get("opened") or {}).get("parts")

    out.append(expectation("parts-3-and-1", parts(three) == 3 and parts(one) == 1,
                           {"three-sheets-distinct": parts(three), "empty-one-sheet": parts(one)}))

    def tabs(r):
        return (r.get("dom") or {}).get("tabs") or []

    out.append(expectation(
        "tab-count-equals-parts",
        len(tabs(three)) == parts(three) and len(tabs(one)) == parts(one)
        and parts(three) is not None and parts(one) is not None,
        {"three": len(tabs(three)), "one": len(tabs(one))}))

    def names(r):
        return ((r.get("finalState") or {}).get("partNames")) or []

    out.append(expectation(
        "tab-text-equals-part-name",
        all([t.get("text") for t in tabs(r)] == names(r) and names(r) for r in (three, one)),
        {"three": [t.get("text") for t in tabs(three)], "one": [t.get("text") for t in tabs(one)],
         "stateNames": names(three)}))

    out.append(expectation(
        "pre-w7-names-are-synthesised-and-say-so",
        all((r.get("finalState") or {}).get("namesFromEngine") is False
            and [t.get("text") for t in tabs(r)] == [f"工作表 {i + 1}" for i in range(len(tabs(r)))]
            and tabs(r) for r in (three, one)),
        {r["file"]: (r.get("finalState") or {}).get("namesFromEngine") for r in (three, one)}))

    out.append(expectation(
        "only-the-current-tab-is-enabled-and-disabled-ones-say-why",
        [t.get("enabled") for t in tabs(three)] == [True, False, False]
        and [t.get("enabled") for t in tabs(one)] == [True]
        and all(t.get("title") for t in tabs(three) if not t.get("enabled")),
        {"three": [t.get("enabled") for t in tabs(three)],
         "one": [t.get("enabled") for t in tabs(one)]}))

    states = [(r.get("finalState") or {}) for r in (three, one)]
    doms = [(r.get("dom") or {}) for r in (three, one)]
    out.append(expectation(
        "name-spoofed-true-and-shown",
        all(s.get("nameSpoofed") is True for s in states)
        and all("name-spoofed" in (d.get("banner") or []) for d in doms)
        and all(not d.get("bannerHidden", True) for d in doms),
        {"state": [s.get("nameSpoofed") for s in states],
         "banner": [d.get("banner") for d in doms]}))
    out.append(expectation(
        "evidence-class-diagnostic",
        all(s.get("evidenceClass") == "diagnostic" for s in states)
        and all((d.get("fields") or {}).get("evidenceClass") == "diagnostic" for d in doms),
        [s.get("evidenceClass") for s in states]))
    out.append(expectation(
        "current-part-read-back-is-null-not-echoed",
        all(s.get("currentPartReadBack") is None for s in states)
        and all((d.get("fields") or {}).get("currentPartReadBack") == "未提供" for d in doms),
        [s.get("currentPartReadBack") for s in states]))
    out.append(expectation(
        "document-type-is-unknown-pre-w7",
        all(s.get("documentType") == "unknown (pre-W7)" and s.get("documentTypeKnown") is False
            for s in states),
        [s.get("documentType") for s in states]))

    refusal = (three.get("showPart1") or {})
    out.append(expectation(
        "show-part-1-is-refused-and-nothing-repaints",
        (refusal.get("error") or {}).get("code") == "PART_SWITCH_UNAVAILABLE"
        and refusal.get("part") == 0
        and refusal.get("tilesDrawnBefore") is not None
        and refusal.get("tilesDrawnBefore") == refusal.get("tilesDrawnAfter"),
        refusal))

    out.append(expectation(
        "a-first-tile-was-painted-for-each-fixture",
        all((r.get("firstTile") or {}).get("sha256") for r in (three, one))
        and all((r.get("dom") or {}).get("canvases", 0) >= 1 for r in (three, one)),
        {r["file"]: (r.get("firstTile") or {}).get("sha256", "")[:16] for r in (three, one)}))
    return out


def selftest() -> int:
    """Show the judge red: each broken report must flip the named expectation."""
    def good_run(file, parts, tab_enabled, sha):
        names = [f"工作表 {i + 1}" for i in range(parts)]
        run = {
            "file": file, "opened": {"parts": parts}, "error": None, "refused": None,
            "dom": {"tabs": [{"text": n, "enabled": e, "title": None if e else "why"}
                              for n, e in zip(names, tab_enabled)],
                    "banner": ["name-spoofed"], "bannerHidden": False, "canvases": 4,
                    "fields": {"evidenceClass": "diagnostic", "currentPartReadBack": "未提供"}},
            "finalState": {"partNames": names, "namesFromEngine": False, "nameSpoofed": True,
                           "evidenceClass": "diagnostic", "currentPartReadBack": None,
                           "documentType": "unknown (pre-W7)", "documentTypeKnown": False},
            "firstTile": {"sha256": sha},
        }
        return run

    base = {"runs": [good_run("three-sheets-distinct.ods", 3, [True, False, False], "a" * 64),
                     good_run("empty-one-sheet.ods", 1, [True], "b" * 64)]}
    base["runs"][0]["showPart1"] = {"error": {"code": "PART_SWITCH_UNAVAILABLE"}, "part": 0,
                                    "tilesDrawnBefore": 7, "tilesDrawnAfter": 7}

    def mutate(label, flips, edit):
        broken = copy.deepcopy(base)
        edit(broken)
        verdicts = {e["id"]: e["ok"] for e in judge(broken)}
        red = sorted(k for k, v in verdicts.items() if not v)
        return {"case": label, "expectedRed": flips, "actualRed": red,
                "pass": all(f in red for f in flips)}

    control = judge(base)
    results = [{"case": "control (all expectations met)",
                "pass": all(e["ok"] for e in control),
                "actualRed": [e["id"] for e in control if not e["ok"]]}]
    three = lambda b: b["runs"][0]       # noqa: E731
    one = lambda b: b["runs"][1]         # noqa: E731
    cases = [
        ("no runs at all", ["both-fixtures-were-run"], lambda b: b.update(runs=[])),
        ("only one fixture was run", ["both-fixtures-were-run"], lambda b: b["runs"].pop()),
        ("three-sheet file did not open", ["opened"], lambda b: three(b).update(opened=None)),
        ("open reported an error", ["opened"], lambda b: three(b).update(error={"code": "X"})),
        ("parts 2 instead of 3", ["parts-3-and-1"], lambda b: three(b)["opened"].update(parts=2)),
        ("one tab short", ["tab-count-equals-parts"], lambda b: three(b)["dom"]["tabs"].pop()),
        ("tab text differs from the part name", ["tab-text-equals-part-name"],
         lambda b: three(b)["dom"]["tabs"][1].update(text="Sheet2")),
        ("names claim to be the engine's", ["pre-w7-names-are-synthesised-and-say-so"],
         lambda b: three(b)["finalState"].update(namesFromEngine=True)),
        ("every tab enabled", ["only-the-current-tab-is-enabled-and-disabled-ones-say-why"],
         lambda b: [t.update(enabled=True) for t in three(b)["dom"]["tabs"]]),
        ("a disabled tab with no reason", ["only-the-current-tab-is-enabled-and-disabled-ones-say-why"],
         lambda b: three(b)["dom"]["tabs"][2].update(title=None)),
        ("spoof flag false", ["name-spoofed-true-and-shown"],
         lambda b: three(b)["finalState"].update(nameSpoofed=False)),
        ("spoof banner missing", ["name-spoofed-true-and-shown"],
         lambda b: one(b)["dom"].update(banner=[])),
        ("evidence class not diagnostic", ["evidence-class-diagnostic"],
         lambda b: one(b)["finalState"].update(evidenceClass="unbound")),
        ("read-back echoes the request", ["current-part-read-back-is-null-not-echoed"],
         lambda b: three(b)["finalState"].update(currentPartReadBack=0)),
        ("document type claimed known", ["document-type-is-unknown-pre-w7"],
         lambda b: three(b)["finalState"].update(documentType="spreadsheet", documentTypeKnown=True)),
        ("showPart(1) was accepted", ["show-part-1-is-refused-and-nothing-repaints"],
         lambda b: three(b).update(showPart1={"error": None, "part": 1,
                                              "tilesDrawnBefore": 7, "tilesDrawnAfter": 9})),
        ("showPart(1) refused but repainted", ["show-part-1-is-refused-and-nothing-repaints"],
         lambda b: three(b)["showPart1"].update(tilesDrawnAfter=9)),
        ("no first tile for the empty sheet", ["a-first-tile-was-painted-for-each-fixture"],
         lambda b: one(b).update(firstTile=None)),
        ("no canvas in the DOM", ["a-first-tile-was-painted-for-each-fixture"],
         lambda b: three(b)["dom"].update(canvases=0)),
    ]
    for label, flips, edit in cases:
        results.append(mutate(label, flips, edit))
    ok = all(r["pass"] for r in results)
    for r in results:
        print(("PASS " if r["pass"] else "FAIL ") + r["case"]
              + (f"  red={r['actualRed']}" if r.get("actualRed") else ""))
    print(f"selftest: {sum(r['pass'] for r in results)}/{len(results)}")
    return 0 if ok else 1


# ------------------------------------------------------------- the browser --
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="e2-editor-v14")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--per-file-timeout", type=float, default=240)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    gate = preconditions()
    if args.check_only:
        print(json.dumps(gate, ensure_ascii=False))
        return 0 if gate["ok"] else 3
    if not gate["ok"]:
        print(json.dumps(gate, ensure_ascii=False, indent=2))
        raise SystemExit("preconditions not met: this run would share the machine "
                         "with another measurement, or hang on the wallet")

    # Imported late so --selftest and --check-only need neither Chrome nor the
    # (large) product-path module.
    from r7_support import evaluate, wait_page                       # noqa: E402
    from run_browser_probe import ChromeSession, free_port           # noqa: E402
    from run_e2_c_page_smoke import navigate                         # noqa: E402
    from run_e2_c_product_path import build_mirror                   # noqa: E402

    manifest = PROJECT / "dist" / "profiles" / args.profile / "sdk-manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"no manifest for {args.profile} at {manifest}")
    for fixture in FIXTURES:
        if not fixture.is_file():
            raise SystemExit(f"missing fixture {fixture}")

    overrides = {path: source.read_bytes() for path, source in PAGE_FILES.items()}
    page_source_sha256 = sha256_of(overrides["ods-viewer-app.js"])
    overrides["ods-viewer-app.js"] = retarget_page(overrides["ods-viewer-app.js"], args.profile)
    scratch = Path(tempfile.mkdtemp(prefix="ods-viewer-draft-"))
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root, overrides)
    # build_mirror materialises an override only when it MEETS that path while
    # walking dist, so every file this draft adds is silently dropped (measured
    # 2026-09-03 by the decisive probe).  Written after the mirror, then checked.
    for relative, payload in overrides.items():
        target = root / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    for relative, payload in overrides.items():
        served = (root / relative).read_bytes()
        if served != payload:
            raise SystemExit(f"mirror serves different bytes for {relative}")

    record: dict = {
        "schemaVersion": 1,
        "release": "m4-ods-w9-viewer-draft-smoke",
        "profile": args.profile,
        "nameSpoofed": None, "evidenceClass": None,   # derived from the runs below
        "why": "diagnostic: the viewer hands the spreadsheet to the engine under a "
               ".odt name (finding 013) because W7 does not exist; this is not the "
               "product opening an ODS",
        "preconditions": gate,
        "pageFiles": {path: sha256_of(payload) for path, payload in overrides.items()},
        "pageSourceSha256": {"ods-viewer-app.js": page_source_sha256,
                             "retargetedTo": args.profile},
        "servedUnmodified": {
            # The two files the plan says must be imported UNMODIFIED, as served.
            "reader-shell/tile-scheduler.js":
                sha256_of((root / "reader-shell" / "tile-scheduler.js").read_bytes()),
            "sdk/document-sdk.js":
                sha256_of((root / "sdk" / "document-sdk.js").read_bytes()),
        },
        "profileManifestSha256": sha256_of(manifest.read_bytes()),
        "runs": [],
    }
    session = None
    server = None
    started = time.monotonic()
    try:
        port = free_port()
        server = subprocess.Popen(
            [sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
             "--root", str(root)],
            cwd=PROJECT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_page(f"http://127.0.0.1:{port}/ods-viewer.html")
        session = ChromeSession("cold")
        record["chrome"] = session.version
        navigate(session, f"http://127.0.0.1:{port}/ods-viewer.html"
                          f"?openTimeoutMs=120000")
        for index, fixture in enumerate(FIXTURES):
            session.set_file("#file-input", fixture)
            deadline = time.monotonic() + args.per_file_timeout
            run = None
            while time.monotonic() < deadline:
                run = evaluate(session, RUN_EXPR.replace("INDEX", str(index)))
                if run and run.get("settled"):
                    break
                time.sleep(1.0)
            if not run:
                record["runs"].append({"file": fixture.name, "fatal": "the page never "
                                       "started a run for this file"})
                break
            run["timedOut"] = not run.get("settled")
            run["fixtureSha256"] = sha256_of(fixture.read_bytes())
            run["dom"] = evaluate(session, DOM_EXPR)
            if fixture.name == "three-sheets-distinct.ods" and not run["timedOut"]:
                # The page's own tab path, tried on part 1: pre-W7 it must be a
                # typed refusal and the screen must not change.
                run["showPart1"] = evaluate(session, "window.__odsViewer.switchPart(1)")
            record["runs"].append(run)
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
        if server is not None:
            server.terminate()
        shutil.rmtree(scratch, ignore_errors=True)

    states = [(r.get("finalState") or {}) for r in record["runs"]]
    record["nameSpoofed"] = bool(states) and all(s.get("nameSpoofed") is True for s in states)
    record["evidenceClass"] = ("diagnostic" if states and all(
        s.get("evidenceClass") == "diagnostic" for s in states) else "NOT-DIAGNOSTIC")
    by_name = {r.get("file"): r for r in record["runs"]}
    three_tile = (by_name.get("three-sheets-distinct.ods") or {}).get("firstTile") or {}
    empty_tile = (by_name.get("empty-one-sheet.ods") or {}).get("firstTile") or {}
    record["firstTileComparison"] = {
        "gate": False,
        "expected": "not equal (the three-sheet file has content, the control is empty)",
        "threeSheetSha256": three_tile.get("sha256"),
        "emptySheetSha256": empty_tile.get("sha256"),
        "byteEqual": (three_tile.get("sha256") == empty_tile.get("sha256")
                      if three_tile.get("sha256") and empty_tile.get("sha256") else None),
        "threeSheetNonPaperPixels": three_tile.get("nonPaperPixels"),
        "emptySheetNonPaperPixels": empty_tile.get("nonPaperPixels"),
        "sameTileSize": (three_tile.get("width"), three_tile.get("height"))
                        == (empty_tile.get("width"), empty_tile.get("height")),
    }
    record["expectations"] = judge(record)
    failed = [e["id"] for e in record["expectations"] if not e["ok"]]
    record["verdict"] = ("DRAFT SMOKE: every expectation met (diagnostic, not gate evidence)"
                         if not failed else f"DRAFT SMOKE RED: {failed}")
    record["elapsedSeconds"] = round(time.monotonic() - started, 1)
    text = json.dumps(record, indent=2, ensure_ascii=False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text + "\n", encoding="utf-8")
    print(record["verdict"])
    print(json.dumps({k: record[k] for k in ("nameSpoofed", "evidenceClass", "firstTileComparison")},
                     ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
