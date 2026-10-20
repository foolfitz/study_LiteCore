#!/usr/bin/env python3
"""E4b and E9 of SPEC-M4-ods-in-nextcloud (§4, addendum 6 A6.3-A6.4): the real viewer page
(web/ods-viewer.html, whose one worker literal names `ods-viewer-v1`), on a mirror, through the
page's own file input and its own tab buttons.

What it does: mirrors dist/ with symlinks, writes the page and the viewer's shell modules into the
MIRROR only (no retarget, no stack patch: the page is for this profile), serves it, opens it with
`?diagnostics=1`, and hands each fixture to `#file-input`:

  E4b  after the open and its paints: the surface's CSS width against ceil(widthTwips / 15), where
       widthTwips is what the engine reports after the first paint (session.state.widthTwips); then
       the viewport is scrolled to its right edge, the page's own scroll handler paints, and the
       right-most drawn tile edge must reach the surface's width.  Read from the DOM, not from the
       page's `run.fit`, so the red case's page (which has no `run.fit`) is judged the same way.
  E9   three-sheets-distinct.ods only: parts == 3, the three `.ods-tab` texts equal the session's
       partNames and the manifest's names, namesFromEngine, no adapter fallback; each tab is CLICKED
       (DOM click, the user's path), the session's read-back must be k, and the page's live engine is
       then asked for E5's tile ((0,0), 1024x1024, 15 twips/px) whose sha256 must equal the first
       paint of part k in the Phase E report named by --phase-e-report.

Red case (spec §4 injection 7, A6.3): --red-case no-refit rewrites, in the mirror's copy of the page
only, `if (session.refit()) {` into `if (false && session.refit()) {` -- today's page without the
re-measure -- and expects E4b RED on three-sheets-distinct; the report goes to <out>/red-cases/.

  run_ods_viewer_e4b_e9.py --selftest
  run_ods_viewer_e4b_e9.py [--phase-e-report FILE] [--out DIR] [--red-case no-refit]
Report: findings/evidence/m4-ods/phase-e/e4b-e9/report-<UTC>.json
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))
from run_ods_viewer_draft_smoke import PAGE_FILES, preconditions          # noqa: E402
from run_ods_viewer_phase_e import DISTINCT, sha256_bytes, utc_now       # noqa: E402

PROFILE = "ods-viewer-v1"
CORPUS = PROJECT / "test-docs" / "ods"
MANIFEST = CORPUS / "manifest.json"
PHASE_E_DIR = PROJECT.parent / "findings" / "evidence" / "m4-ods" / "phase-e"
DEFAULT_OUT = PHASE_E_DIR / "e4b-e9"
FIXTURES = [DISTINCT, "upstream/tdf149752.ods"]
TWIPS_PER_PX = 15
TILE_PX = 1024
REFIT_ANCHOR = "if (session.refit()) {"
REFIT_MUTATION = "if (false && session.refit()) {"
CLICK_ORDER = [1, 2, 0]

RUN_EXPR = """(() => {
  const r = window.__odsViewer && window.__odsViewer.runs[INDEX];
  if (!r) return null;
  return JSON.stringify({ settled: r.settled, file: r.file, inputSha256: r.inputSha256 ?? null,
    opened: r.opened, refused: r.refused, error: r.error, tileDraws: r.tileDraws,
    engineCreated: r.engineCreated, viewReadyAtMs: r.viewReadyAtMs, refits: r.refits ?? 0,
    fit: r.fit ?? null, finalState: r.finalState ?? null });
})()"""

DOM_EXPR = """(() => {
  const s = window.__odsViewer.session;
  const st = s ? s.state : null;
  const vp = document.querySelector('#viewport');
  const canvases = [...document.querySelectorAll('#tiles canvas')];
  const right = canvases.map((c) => Number.parseFloat(c.style.left) + Number.parseFloat(c.style.width));
  return JSON.stringify({
    surfaceCssWidth: document.querySelector('#surface').getBoundingClientRect().width,
    surfaceStyleWidth: document.querySelector('#surface').style.width,
    widthTwips: st ? st.widthTwips : null, heightTwips: st ? st.heightTwips : null,
    rightmostDrawnPx: right.length ? Math.max(...right) : 0, canvases: canvases.length,
    scrollLeft: vp.scrollLeft, scrollWidth: vp.scrollWidth, clientWidth: vp.clientWidth,
    state: st ? { state: st.state, parts: st.parts, currentPart: st.currentPart,
                  currentPartReadBack: st.currentPartReadBack, partNames: st.partNames,
                  namesFromEngine: st.namesFromEngine, adapterFallbacks: st.adapterFallbacks,
                  documentType: st.documentType, lastRefusal: st.lastRefusal } : null,
    tileDraws: window.__odsViewer.tileDraws,
  });
})()"""

SCROLL_EXPR = """(async () => {
  const vp = document.querySelector('#viewport');
  vp.scrollTop = 0;
  vp.scrollLeft = vp.scrollWidth;
  await new Promise((r) => setTimeout(r, 150));
  const s = window.__odsViewer.session;
  if (s) await s.drain();
  await new Promise((r) => setTimeout(r, 50));
  return true;
})()"""

TABS_EXPR = """JSON.stringify([...document.querySelectorAll('#tab-strip .ods-tab')].map((b) => ({
  part: Number(b.dataset.part), text: b.textContent, selected: b.getAttribute('aria-selected'),
  disabled: b.disabled })))"""

# After a click: wait for the page's own paint, then E5's tile from the page's live engine (A6.4),
# and the page's own (0,0) canvas, hashed.
TILE_EXPR = """(async () => {
  const s = window.__odsViewer.session;
  await s.drain();
  const sha = async (bytes) => [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))]
    .map((b) => b.toString(16).padStart(2, '0')).join('');
  const nonPaper = (view) => { let n = 0; for (let i = 0; i + 3 < view.length; i += 4)
    if (view[i] !== 255 || view[i + 1] !== 255 || view[i + 2] !== 255) n += 1; return n; };
  const region = { xTwips: 0, yTwips: 0, widthTwips: TILE * 15, heightTwips: TILE * 15,
                   canvasWidthPx: TILE, canvasHeightPx: TILE };
  const r = await s._view.render(region, { timeoutMs: 60000 });
  const view = new Uint8Array(r.pixels);
  const out = { tile1024: { sha256: await sha(view), nonPaperPixels: nonPaper(view), width: r.width,
                            height: r.height, documentWidthTwips: r.documentWidthTwips ?? null },
                pageTile: null };
  const first = [...document.querySelectorAll('#tiles canvas')]
    .find((c) => Number.parseFloat(c.style.left) === 0 && Number.parseFloat(c.style.top) === 0);
  if (first) {
    const data = first.getContext('2d').getImageData(0, 0, first.width, first.height).data;
    out.pageTile = { sha256: await sha(data), nonPaperPixels: nonPaper(data), width: first.width,
                     height: first.height, cssWidth: first.style.width };
  }
  return JSON.stringify(out);
})()""".replace("TILE", str(TILE_PX))


def verdict(identifier: str, ok: bool, detail) -> dict:
    return {"id": identifier, "ok": bool(ok), "detail": detail}


def judge_e4b(report: dict) -> list[dict]:
    out = []
    for run in report.get("runs") or []:
        name = run.get("path") or run.get("file")
        after_open = run.get("afterOpen") or {}
        after_scroll = run.get("afterScroll") or {}
        problems = []
        if not run.get("opened") or run.get("error") or run.get("refused"):
            problems.append(f"not opened: error {run.get('error')}, refused {run.get('refused')}")
        width = after_open.get("widthTwips")
        surface = after_open.get("surfaceCssWidth")
        if not isinstance(width, (int, float)) or not isinstance(surface, (int, float)):
            problems.append(f"no width read: widthTwips {width}, surface {surface}")
        else:
            want = math.ceil(width / TWIPS_PER_PX)
            if surface != want:
                problems.append(f"surface {surface} px, ceil({width} / 15) = {want}")
        right = after_scroll.get("rightmostDrawnPx")
        if not isinstance(right, (int, float)) or not isinstance(surface, (int, float)):
            problems.append(f"no right edge read after the scroll: {right}")
        elif right < surface:
            problems.append(f"the right-most drawn edge {right} px is left of the surface width {surface} px")
        out.append(verdict(f"E4b {name}", not problems, problems or {
            "widthTwips": width, "surfaceCssWidth": surface, "rightmostDrawnPx": right,
            "scrollLeft": after_scroll.get("scrollLeft"), "clientWidth": after_scroll.get("clientWidth"),
            "widthTwipsAfterScroll": after_scroll.get("widthTwips"), "refits": run.get("refits")}))
    if not report.get("runs"):
        out.append(verdict("E4b non-empty", False, "no run"))
    return out


def judge_e9(report: dict) -> list[dict]:
    run = next((r for r in report.get("runs") or [] if r.get("path") == DISTINCT), None)
    if run is None:
        return [verdict(f"E9 {DISTINCT}", False, "the fixture was not run")]
    problems = []
    state = (run.get("afterOpen") or {}).get("state") or {}
    names = run.get("manifestSheetNames") or []
    tabs = run.get("tabs") or []
    reference = run.get("e5Reference") or {}
    if not run.get("opened"):
        problems.append("not opened")
    if state.get("parts") != 3 or len(names) != 3:
        problems.append(f"parts {state.get('parts')}, manifest names {names}")
    if [t.get("text") for t in tabs] != state.get("partNames") or state.get("partNames") != names:
        problems.append(f"tabs {[t.get('text') for t in tabs]} / partNames {state.get('partNames')} / manifest {names}")
    if state.get("namesFromEngine") is not True:
        problems.append(f"namesFromEngine {state.get('namesFromEngine')}")
    if state.get("adapterFallbacks") != []:
        problems.append(f"adapterFallbacks {state.get('adapterFallbacks')}")
    if not reference.get("tiles") or len(reference["tiles"]) != 3 or None in reference["tiles"]:
        problems.append(f"no E5 reference for every part: {reference}")
    clicks = run.get("clicks") or []
    if sorted(c.get("requested") for c in clicks) != [0, 1, 2]:
        problems.append(f"clicked parts {[c.get('requested') for c in clicks]}, want every part once")
    for click in clicks:
        k = click.get("requested")
        if click.get("currentPartReadBack") != k:
            problems.append(f"tab {k}: read back {click.get('currentPartReadBack')}")
        if click.get("lastRefusal"):
            problems.append(f"tab {k}: refused {click['lastRefusal']}")
        got = (click.get("tile1024") or {}).get("sha256")
        want = (reference.get("tiles") or [None] * 3)[k] if isinstance(k, int) and 0 <= k < 3 else None
        if got is None or want is None or got != want:
            problems.append(f"tab {k}: the engine's tile {str(got)[:12]} is not E5's {str(want)[:12]}")
    return [verdict(f"E9 {DISTINCT}", not problems, problems[:8] or {
        "tabs": [t.get("text") for t in tabs], "readBacks": [c.get("currentPartReadBack") for c in clicks],
        "reference": reference.get("report")})]


JUDGES = {"E4b": judge_e4b, "E9": judge_e9}


def judge(report: dict) -> dict:
    results = {name: fn(report) for name, fn in JUDGES.items()}
    return {name: {"pass": all(v["ok"] for v in vs) and bool(vs), "failed": [v for v in vs if not v["ok"]],
                   "count": len(vs)} for name, vs in results.items()}


# -------------------------------------------------------------- selftest --
def synthetic() -> dict:
    def run(path, names, parts, width=26775, surface=1785, right=1792, clicks=True):
        return {"path": path, "opened": {"atMs": 1000}, "error": None, "refused": None, "refits": 1,
                "manifestSheetNames": names,
                "afterOpen": {"surfaceCssWidth": surface, "widthTwips": width, "rightmostDrawnPx": 1024,
                              "state": {"parts": parts, "partNames": names, "namesFromEngine": True,
                                        "adapterFallbacks": [], "currentPart": 0, "currentPartReadBack": 0}},
                "afterScroll": {"rightmostDrawnPx": right, "scrollLeft": 1000, "widthTwips": width},
                "tabs": [{"part": k, "text": n} for k, n in enumerate(names)],
                "e5Reference": {"report": "report-x.json", "tiles": ["t0", "t1", "t2"][:parts]},
                "clicks": [{"requested": k, "currentPartReadBack": k, "lastRefusal": None,
                            "tile1024": {"sha256": f"t{k}"}} for k in CLICK_ORDER] if clicks else []}
    return {"runs": [run(DISTINCT, ["Alpha", "Beta", "Gamma"], 3),
                     run("upstream/tdf149752.ods", ["Liste", "Auswertung"], 2, width=30000, surface=2000, right=2048)]}


def selftest() -> int:
    def distinct(b):
        return b["runs"][0]

    mutations = [
        ("E4b", "the surface is narrower than the engine's width (the 12 px)",
         lambda b: distinct(b)["afterOpen"].update(surfaceCssWidth=1773)),
        ("E4b", "the right edge was never painted", lambda b: distinct(b)["afterScroll"].update(rightmostDrawnPx=1536)),
        ("E4b", "the file did not open", lambda b: distinct(b).update(opened=None, error={"code": "X"})),
        ("E4b", "no width was read", lambda b: distinct(b)["afterOpen"].update(widthTwips=None)),
        ("E4b", "the second fixture's surface is off by one",
         lambda b: b["runs"][1]["afterOpen"].update(surfaceCssWidth=1999)),
        ("E9", "two parts", lambda b: distinct(b)["afterOpen"]["state"].update(parts=2)),
        ("E9", "a tab's text is not the part name", lambda b: distinct(b)["tabs"][1].update(text="工作表 2")),
        ("E9", "names were synthesised", lambda b: distinct(b)["afterOpen"]["state"].update(namesFromEngine=False)),
        ("E9", "an adapter fallback", lambda b: distinct(b)["afterOpen"]["state"].update(adapterFallbacks=["x"])),
        ("E9", "a click read back another part", lambda b: distinct(b)["clicks"][0].update(currentPartReadBack=0)),
        ("E9", "a click was refused", lambda b: distinct(b)["clicks"][1].update(lastRefusal={"code": "X"})),
        ("E9", "the engine's tile is not E5's", lambda b: distinct(b)["clicks"][2]["tile1024"].update(sha256="other")),
        ("E9", "the E5 reference is missing", lambda b: distinct(b).update(e5Reference={})),
        ("E9", "a part was never clicked", lambda b: distinct(b)["clicks"].pop()),
        ("E9", "the fixture was not run", lambda b: b["runs"].pop(0)),
    ]
    control = judge(synthetic())
    results = [("control (every criterion met)", all(v["pass"] for v in control.values()),
                [k for k, v in control.items() if not v["pass"]])]
    for criterion, label, edit in mutations:
        broken = copy.deepcopy(synthetic())
        edit(broken)
        verdicts = judge(broken)
        red = [k for k, v in verdicts.items() if not v["pass"]]
        results.append((f"{criterion}: {label}", criterion in red, red))
    for label, ok, red in results:
        print(("PASS " if ok else "FAIL ") + label + (f"  red={red}" if red else ""))
    passed = sum(ok for _, ok, _ in results)
    print(f"selftest: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


# ---------------------------------------------------------------- browser --
def latest_phase_e_report() -> Path | None:
    reports = sorted(PHASE_E_DIR.glob("report-*.json"))
    return reports[-1] if reports else None


def e5_reference(report_path: Path | None, entry_sha: str) -> dict:
    if report_path is None or not report_path.is_file():
        return {"report": str(report_path) if report_path else None, "tiles": None, "why": "no Phase E report"}
    data = json.loads(report_path.read_text(encoding="utf-8"))
    case = next((c for c in data.get("cases") or [] if c.get("inputSha256") == entry_sha), None)
    if case is None:
        return {"report": str(report_path), "reportSha256": sha256_bytes(report_path.read_bytes()),
                "tiles": None, "why": "the entry is not in that report"}
    tiles = [((s.get("tiles") or [{}])[0]).get("sha256") for s in case.get("sheets") or []]
    return {"report": str(report_path), "reportSha256": sha256_bytes(report_path.read_bytes()),
            "probeWasmSha256": data.get("probeWasmSha256"), "tiles": tiles}


def mutate_no_refit(payload: bytes) -> bytes:
    text = payload.decode("utf-8")
    if text.count(REFIT_ANCHOR) != 1:
        raise SystemExit(f"ods-viewer-app.js: {REFIT_ANCHOR!r} occurs {text.count(REFIT_ANCHOR)} times, want exactly 1")
    return text.replace(REFIT_ANCHOR, REFIT_MUTATION).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--phase-e-report", type=Path, default=None, help="E5's tiles (default: the latest)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--red-case", choices=("no-refit",), default=None)
    parser.add_argument("--per-file-timeout", type=float, default=300)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    gate = preconditions()
    if gate["wallet"] != "b false":
        raise SystemExit(f"the KDE wallet is locked ({gate['wallet']!r}): headless Chrome would hang")
    profile_manifest = PROJECT / "dist" / "profiles" / PROFILE / "sdk-manifest.json"
    if not profile_manifest.is_file():
        raise SystemExit(f"{profile_manifest} does not exist: the viewer is not linked")

    from r7_support import evaluate, wait_page                      # noqa: E402
    from run_browser_probe import ChromeSession, free_port          # noqa: E402
    from run_e2_c_page_smoke import navigate                        # noqa: E402
    from run_e2_c_product_path import build_mirror                  # noqa: E402

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_path = {e["path"]: e for e in manifest["entries"]}
    phase_e_report = args.phase_e_report or latest_phase_e_report()

    overrides = {path: source.read_bytes() for path, source in PAGE_FILES.items()}
    page_sha_source = sha256_bytes(overrides["ods-viewer-app.js"])
    if args.red_case == "no-refit":
        overrides["ods-viewer-app.js"] = mutate_no_refit(overrides["ods-viewer-app.js"])
        out_dir = args.out / "red-cases"
    else:
        out_dir = args.out
    literal = overrides["ods-viewer-app.js"].decode("utf-8").count(f'workerUrl: "./profiles/{PROFILE}/sdk-worker.js"')
    if literal != 1:
        raise SystemExit(f"the page names {PROFILE} {literal} times, want exactly 1 (no retarget here)")

    scratch = Path(tempfile.mkdtemp(prefix="ods-e4b-e9-"))
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root, overrides)
    for relative, payload in overrides.items():
        target = root / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    for relative, payload in overrides.items():
        target = root / relative
        if target.is_symlink() or target.read_bytes() != payload:
            raise SystemExit(f"the mirror does not serve the override for {relative} as a real file")

    report = {"schemaVersion": 1, "release": "m4-ods-e4b-e9", "spec": "specs/SPEC-M4-ods-in-nextcloud.md §4 E4b, E9; A6.3-A6.4",
              "evidenceClass": "red-case" if args.red_case else "gate",
              "redCase": args.red_case, "startedAt": utc_now(), "profile": PROFILE, "preconditions": gate,
              "profileManifestSha256": sha256_bytes(profile_manifest.read_bytes()),
              "probeWasmSha256": sha256_bytes((profile_manifest.parent / "probe.wasm").read_bytes()),
              "workerSha256": sha256_bytes((profile_manifest.parent / "sdk-worker.js").read_bytes()),
              "pageSourceSha256": {"ods-viewer-app.js": page_sha_source,
                                   "served": sha256_bytes(overrides["ods-viewer-app.js"])},
              "pageFiles": {p: sha256_bytes(b) for p, b in overrides.items()},
              "fixtures": [{"path": p, "sha256": by_path[p]["sha256"]} for p in FIXTURES],
              "runs": []}
    session = server = None
    started = time.monotonic()
    try:
        port = free_port()
        server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
                                   "--root", str(root)], cwd=PROJECT,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_page(f"http://127.0.0.1:{port}/ods-viewer.html")
        session = ChromeSession("cold")
        report["chrome"] = session.version
        navigate(session, f"http://127.0.0.1:{port}/ods-viewer.html?diagnostics=1&openTimeoutMs=180000")
        report["pageWorkerUrl"] = evaluate(session, "window.__odsViewer && window.__odsViewer.workerUrl")
        report["window"] = evaluate(session, "JSON.stringify({innerWidth, innerHeight, devicePixelRatio})")
        for index, path in enumerate(FIXTURES):
            entry = by_path[path]
            fixture = CORPUS / path
            run = {"path": path, "file": fixture.name, "sha256": entry["sha256"],
                   "manifestSheetNames": entry["sheetNames"], "opened": None, "error": None, "refused": None}
            report["runs"].append(run)
            begun = time.monotonic()
            session.set_file("#file-input", fixture)
            page_run = None
            while time.monotonic() < begun + args.per_file_timeout:
                text = evaluate(session, RUN_EXPR.replace("INDEX", str(index)))
                page_run = json.loads(text) if text else None
                if page_run and page_run.get("settled"):
                    break
                time.sleep(0.5)
            if not page_run:
                run["error"] = {"code": "NO_RUN", "message": "the page never started a run"}
                continue
            run.update({k: page_run.get(k) for k in ("opened", "error", "refused", "inputSha256", "tileDraws",
                                                      "viewReadyAtMs", "refits", "fit", "engineCreated")})
            run["timedOut"] = not page_run.get("settled")
            if run["inputSha256"] != entry["sha256"]:
                run["error"] = run["error"] or {"code": "INPUT_MISMATCH", "message": run["inputSha256"]}
            run["afterOpen"] = json.loads(evaluate(session, DOM_EXPR))
            if not run["opened"]:
                continue
            evaluate(session, SCROLL_EXPR)
            run["afterScroll"] = json.loads(evaluate(session, DOM_EXPR))
            if path != DISTINCT:
                continue
            run["tabs"] = json.loads(evaluate(session, TABS_EXPR))
            run["e5Reference"] = e5_reference(phase_e_report, entry["sha256"])
            run["clicks"] = []
            for k in CLICK_ORDER:
                click = {"requested": k, "clickedAtMs": round((time.monotonic() - started) * 1000)}
                run["clicks"].append(click)
                session.click(f'.ods-tab[data-part="{k}"]')
                state = {}
                until = time.monotonic() + 60
                while time.monotonic() < until:
                    state = (json.loads(evaluate(session, DOM_EXPR)) or {}).get("state") or {}
                    if state.get("currentPartReadBack") == k or state.get("lastRefusal"):
                        break
                    time.sleep(0.25)
                click.update({"currentPart": state.get("currentPart"),
                              "currentPartReadBack": state.get("currentPartReadBack"),
                              "lastRefusal": state.get("lastRefusal")})
                try:
                    click.update(json.loads(evaluate(session, TILE_EXPR)))
                except Exception as error:  # noqa: BLE001 - the error is the evidence
                    click["tileError"] = str(error)[:400]
                click["tabs"] = json.loads(evaluate(session, TABS_EXPR))
        evaluate(session, "(() => { window.__odsViewer.close(); return true; })()")
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                pass
        if server is not None:
            server.terminate()
        shutil.rmtree(scratch, ignore_errors=True)
    report["elapsedSeconds"] = round(time.monotonic() - started, 1)
    report["verdicts"] = judge(report)
    report["completedAt"] = utc_now()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"report-{report['startedAt']}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)
    for name, v in report["verdicts"].items():
        print(f"{name}: {'PASS' if v['pass'] else 'FAIL'} ({v['count']} verdicts, {len(v['failed'])} failed)")
        for f in v["failed"]:
            print(f"    {f['id']}: {json.dumps(f['detail'], ensure_ascii=False)[:300]}")
    if args.red_case:
        e4b_red = any(f["id"] == f"E4b {DISTINCT}" for f in report["verdicts"]["E4b"]["failed"])
        report["redCaseReproduced"] = e4b_red
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"RED CASE {args.red_case}: {'reproduced (E4b red on ' + DISTINCT + ')' if e4b_red else 'NOT reproduced'}")
        return 0 if e4b_red else 1
    return 0 if all(v["pass"] for v in report["verdicts"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
