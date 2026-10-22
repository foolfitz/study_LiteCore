#!/usr/bin/env python3
"""E6's two halves the Phase E runner does not do (SPEC-M4 §4 E6, addendum 6): the viewer link's
own boot noise B (A6.1) and the reopen series (A6.2), on the entries staged here.

What it does: mirrors dist/ with symlinks, writes the E6 harness page (web/ods-viewer-e6-harness
{.html,-app.js}), the viewer's shell modules and the staged corpus entries into the MIRROR only,
serves it, and lets the page run both arms on `ods-viewer-v1` (the harness's one worker literal):

  boots   N new engines, the same bytes each: open, close, dispose.  B is the largest
          |open.begin[n+1] - open.begin[n]| over the --bound-entry's boots.
  reopen  ONE engine: N x (open, one 1024x1024 tile per part, close).  Delta_n is
          open.begin[n+1] - open.begin[n]; the criterion is every Delta_n <= B.

Both arms are SDK-level and the report says so (the product session disposes its engine on close).

Judged always: the shape of both arms (N cycles, each with `open.begin` and `document-destroy-enter`,
no error; a reopen cycle paints one tile per part).  Judged only with --bound B: every Delta_n <= B.
Without --bound the deltas are RECORDED, listed under notJudged, and the exit code does not cover
them -- a bound not yet pinned in the spec must not produce a green.

  run_ods_viewer_e6_leak.py --selftest
  run_ods_viewer_e6_leak.py [--entries PATH ...] [--bound-entry PATH] [--cycles N] [--bound B] [--out DIR]

Preconditions: the KDE wallet, other Chrome processes and the load are recorded, not refused (no
criterion here is a time; the wallet was refused until the launcher got --password-store=basic,
SPEC-M3-production-ui 17.27).
Report: findings/evidence/m4-ods/phase-e/e6-leak/report-<UTC>.json
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "tools"))
from run_ods_viewer_draft_smoke import PAGE_FILES, preconditions          # noqa: E402
from run_ods_viewer_phase_e import KILL_LINE, sha256_bytes, utc_now      # noqa: E402

PROFILE = "ods-viewer-v1"
CORPUS = PROJECT / "test-docs" / "ods"
MANIFEST = CORPUS / "manifest.json"
DEFAULT_OUT = PROJECT.parent / "findings" / "evidence" / "m4-ods" / "phase-e" / "e6-leak"
HARNESS = {"ods-viewer-e6-harness.html": PROJECT / "web" / "ods-viewer-e6-harness.html",
           "ods-viewer-e6-harness-app.js": PROJECT / "web" / "ods-viewer-e6-harness-app.js"}
BOUND_ENTRY = "ladder/one-cell-a1.ods"
DEFAULT_ENTRIES = [BOUND_ENTRY, "ladder/three-sheets-distinct.ods", "ladder/numeric-100k.ods"]
NS = "__odsE6"
# A7.1: the first two reopen steps raise the high-water mark and are recorded, not judged.
HEAD_STEPS = 2


def verdict(identifier: str, ok: bool, detail) -> dict:
    return {"id": identifier, "ok": bool(ok), "detail": detail}


def open_begins(arm: dict) -> list:
    return [c.get("openBegin") for c in (arm or {}).get("cycles") or []]


def deltas(arm: dict) -> list:
    begins = open_begins(arm)
    if any(not isinstance(b, int) for b in begins):
        return []
    return [b - a for a, b in zip(begins, begins[1:])]


def noise_floor(report: dict) -> dict:
    """B from the bound entry's boots arm: the largest absolute step between consecutive boots."""
    entry = next((e for e in report.get("entries") or [] if e.get("path") == report.get("boundEntry")), None)
    begins = open_begins((entry or {}).get("boots"))
    steps = [abs(d) for d in deltas((entry or {}).get("boots"))]
    complete = (entry is not None and len(begins) == report.get("cycles") and
                all(isinstance(b, int) for b in begins))
    return {"entry": report.get("boundEntry"), "openBegins": begins, "absoluteSteps": steps,
            "B": max(steps) if complete and steps else None, "complete": complete}


def shape_problems(arm: dict | None, cycles: int, *, tiles: bool) -> list[str]:
    problems = []
    if not arm:
        return ["arm missing"]
    if arm.get("engineError"):
        problems.append(f"engine: {arm['engineError']}")
    got = arm.get("cycles") or []
    if len(got) != cycles:
        problems.append(f"{len(got)} cycles, want {cycles}")
    for c in got:
        n = c.get("cycle")
        if c.get("error"):
            problems.append(f"cycle {n}: {c['error']}")
        if c.get("workerCrashed"):
            problems.append(f"cycle {n}: the worker crashed")
        if not isinstance(c.get("openBegin"), int):
            problems.append(f"cycle {n}: no open.begin")
        if not c.get("destroyEnterSeen"):
            problems.append(f"cycle {n}: no document-destroy-enter")
        peak = c.get("peakSbrk")
        if isinstance(peak, int) and peak >= KILL_LINE:
            problems.append(f"cycle {n}: peak sbrk {peak} is not under the kill line")
        if tiles:
            parts = c.get("parts")
            painted = len(c.get("tiles") or [])
            if not isinstance(parts, int) or parts < 1 or painted != parts:
                problems.append(f"cycle {n}: {painted} tiles for {parts} parts")
    return problems


def judge(report: dict) -> dict:
    cycles = report.get("cycles")
    bound = report.get("bound")
    judged, not_judged = [], []
    entries = report.get("entries") or []
    if not entries:
        judged.append(verdict("E6 non-empty", False, "no entry was run"))
    floor = noise_floor(report)
    judged.append(verdict(f"E6 noise floor measured on {floor['entry']}", floor["complete"] and floor["B"] is not None,
                          floor))
    for e in entries:
        path = e.get("path")
        if e.get("fatal"):
            judged.append(verdict(f"E6 {path}", False, {"fatal": e["fatal"]}))
            continue
        judged.append(verdict(f"E6 boots {path}", not (p := shape_problems(e.get("boots"), cycles, tiles=False)),
                              p[:6] or open_begins(e.get("boots"))))
        judged.append(verdict(f"E6 reopen shape {path}", not (p := shape_problems(e.get("reopen"), cycles, tiles=True)),
                              p[:6] or open_begins(e.get("reopen"))))
        series = deltas(e.get("reopen"))
        # Spec addendum 7 (A7.1): the break is a high-water mark (open.begin[n+1] == the previous
        # cycle's peak), so the first two steps build it and are recorded; the criterion is that
        # the series has stopped rising by cycle 3: every step from Delta_3 on is <= B.
        head, tail = series[:HEAD_STEPS], series[HEAD_STEPS:]
        detail = {"openBegins": open_begins(e.get("reopen")), "deltas": series, "recordedHead": head,
                  "judgedTail": tail, "bound": bound}
        if isinstance(bound, int):
            judged.append(verdict(f"E6 reopen bound {path}",
                                  bool(series) and len(series) == cycles - 1 and len(tail) >= 2
                                  and all(d <= bound for d in tail),
                                  detail))
        else:
            not_judged.append({"id": f"E6 reopen bound {path}", "why": "B is not pinned (--bound absent)",
                               "detail": detail})
    return {"judged": judged, "notJudged": not_judged, "pass": all(v["ok"] for v in judged) and bool(judged)}


# -------------------------------------------------------------- selftest --
def synthetic(cycles: int = 5, bound=None) -> dict:
    def cycle(n, begin, parts=1, tiles=True):
        return {"cycle": n, "openBegin": begin, "destroyEnterSeen": True, "error": None, "workerCrashed": False,
                "peakSbrk": begin + 10_000_000, "parts": parts,
                "tiles": [{"part": k, "sha256": f"t{k}"} for k in range(parts)] if tiles else [],
                "stages": [{"name": "open.begin", "sbrk": begin},
                           {"name": "document-destroy-enter", "sbrk": begin + 10_000_000}]}

    def entry(path, boots, reopen, parts=1):
        return {"path": path, "name": Path(path).name, "fatal": None,
                "boots": {"arm": "boots", "cycles": [cycle(n + 1, b, parts, tiles=False) for n, b in enumerate(boots)]},
                "reopen": {"arm": "reopen", "cycles": [cycle(n + 1, b, parts) for n, b in enumerate(reopen)]}}
    return {"cycles": cycles, "bound": bound, "boundEntry": BOUND_ENTRY,
            "entries": [entry(BOUND_ENTRY, [100] * cycles, [100] * cycles),
                        entry("ladder/three-sheets-distinct.ods", [100] * cycles, [100, 100, 100, 100, 100], parts=3)]}


def selftest() -> int:
    def e(b, i):
        return b["entries"][i]

    mutations = [
        ("shape", "four cycles in the boots arm", None, lambda b: e(b, 0)["boots"]["cycles"].pop()),
        ("shape", "a boot without open.begin", None, lambda b: e(b, 0)["boots"]["cycles"][2].update(openBegin=None)),
        ("shape", "a reopen without document-destroy-enter", None,
         lambda b: e(b, 1)["reopen"]["cycles"][1].update(destroyEnterSeen=False)),
        ("shape", "a reopen cycle errored", None, lambda b: e(b, 1)["reopen"]["cycles"][3].update(error={"code": "X"})),
        ("shape", "a reopen cycle painted fewer tiles than parts", None,
         lambda b: e(b, 1)["reopen"]["cycles"][0]["tiles"].pop()),
        ("shape", "the engine never started", None,
         lambda b: e(b, 1)["reopen"].update(engineError={"code": "INIT"}, cycles=[])),
        ("shape", "a peak over the kill line", None, lambda b: e(b, 0)["reopen"]["cycles"][0].update(peakSbrk=KILL_LINE)),
        ("shape", "an entry fatal", None, lambda b: e(b, 1).update(fatal={"code": "FETCH"})),
        ("shape", "no entry at all", None, lambda b: b.update(entries=[])),
        ("floor", "the bound entry was not run", None, lambda b: b["entries"].pop(0)),
        ("bound", "a reopen step over B in the tail (Delta_3)", 0,
         lambda b: e(b, 1)["reopen"]["cycles"][3].update(openBegin=101)),
        ("bound", "a reopen step over a non-zero B in the tail (Delta_4)", 1_000,
         lambda b: e(b, 1)["reopen"]["cycles"][4].update(openBegin=1_101)),
        ("bound", "only four cycles: no two tail steps", 0,
         lambda b: e(b, 1)["reopen"]["cycles"].pop()),
    ]
    results = []
    control = judge(synthetic())
    results.append(("control without a bound: shape passes, bound recorded only",
                    control["pass"] and len(control["notJudged"]) == 2, []))
    with_bound = judge(synthetic(bound=0))
    results.append(("control with B = 0: every delta 0 passes", with_bound["pass"] and not with_bound["notJudged"], []))
    at_bound = synthetic(bound=1_000)
    at_bound["entries"][1]["reopen"]["cycles"][3]["openBegin"] = 1_100
    at_bound["entries"][1]["reopen"]["cycles"][4]["openBegin"] = 1_100
    results.append(("control: a tail step exactly at B passes", judge(at_bound)["pass"], []))
    head_only = synthetic(bound=0)
    for n, begin in enumerate((100, 110, 114, 114, 114)):
        head_only["entries"][1]["reopen"]["cycles"][n]["openBegin"] = begin
    out = judge(head_only)
    results.append(("control: the measured shape (two head steps, then flat) passes with B = 0 and records the head",
                    out["pass"] and any(v["detail"].get("recordedHead") == [10, 4] for v in out["judged"]
                                        if v["id"].startswith("E6 reopen bound")), []))
    for kind, label, bound, edit in mutations:
        broken = synthetic(bound=bound)
        edit(broken)
        out = judge(broken)
        red = [v["id"] for v in out["judged"] if not v["ok"]]
        results.append((f"{kind}: {label}", not out["pass"] and bool(red), red))
    for label, ok, red in results:
        print(("PASS " if ok else "FAIL ") + label + (f"  red={red}" if red else ""))
    passed = sum(ok for _, ok, _ in results)
    print(f"selftest: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


# ---------------------------------------------------------------- browser --
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--entries", nargs="+", default=DEFAULT_ENTRIES, help="manifest paths to stage")
    parser.add_argument("--bound-entry", default=BOUND_ENTRY, help="the entry whose boots define B")
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--bound", type=int, default=None, help="B as pinned in the spec; absent = record only")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=float, default=1800)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    gate = preconditions()
    profile_manifest = PROJECT / "dist" / "profiles" / PROFILE / "sdk-manifest.json"
    if not profile_manifest.is_file():
        raise SystemExit(f"{profile_manifest} does not exist: the viewer is not linked")
    if args.bound_entry not in args.entries:
        args.entries.insert(0, args.bound_entry)

    from r7_support import evaluate, wait_page                      # noqa: E402
    from run_browser_probe import ChromeSession, free_port          # noqa: E402
    from run_e2_c_page_smoke import navigate                        # noqa: E402
    from run_e2_c_product_path import build_mirror                  # noqa: E402

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_path = {e["path"]: e for e in manifest["entries"]}
    missing = [p for p in args.entries if p not in by_path]
    if missing:
        raise SystemExit(f"not in the manifest: {missing}")

    overrides = {path: source.read_bytes() for path, source in PAGE_FILES.items() if path.startswith("viewer-shell/")}
    overrides.update({path: source.read_bytes() for path, source in HARNESS.items()})
    specs, staged = [], []
    for index, path in enumerate(args.entries):
        entry = by_path[path]
        source = CORPUS / path
        rel = f"ods-e6-cases/{index:03d}/{Path(path).name}"
        payload = source.read_bytes()
        if sha256_bytes(payload) != entry["sha256"]:
            raise SystemExit(f"{path}: the file's sha differs from the manifest")
        overrides[rel] = payload
        specs.append({"name": Path(path).name, "path": path, "file": "./" + rel})
        staged.append({"path": path, "sha256": entry["sha256"], "sheets": entry["sheets"], "bytes": entry["bytes"]})
    overrides["ods-e6-cases.json"] = json.dumps(specs, ensure_ascii=False).encode("utf-8")

    scratch = Path(tempfile.mkdtemp(prefix="ods-e6-"))
    root = scratch / "root"
    build_mirror(PROJECT / "dist", root, overrides)
    for relative, payload in overrides.items():
        target = root / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    for relative, payload in overrides.items():
        if (root / relative).read_bytes() != payload:
            raise SystemExit(f"the mirror serves different bytes for {relative}")

    report = {"schemaVersion": 1, "release": "m4-ods-e6-leak", "spec": "specs/SPEC-M4-ods-in-nextcloud.md §4 E6, A6.1-A6.2",
              "level": "sdk (both arms; the product session disposes its engine on close)",
              "startedAt": utc_now(), "profile": PROFILE, "preconditions": gate,
              "profileManifestSha256": sha256_bytes(profile_manifest.read_bytes()),
              "probeWasmSha256": sha256_bytes((profile_manifest.parent / "probe.wasm").read_bytes()),
              "workerSha256": sha256_bytes((profile_manifest.parent / "sdk-worker.js").read_bytes()),
              "pageFiles": {p: sha256_bytes(b) for p, b in overrides.items() if not p.startswith("ods-e6-cases")},
              "cycles": args.cycles, "bound": args.bound, "boundEntry": args.bound_entry,
              "staged": staged, "entries": []}
    session = server = None
    started = time.monotonic()
    try:
        port = free_port()
        server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
                                   "--root", str(root)], cwd=PROJECT,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_page(f"http://127.0.0.1:{port}/ods-viewer-e6-harness.html")
        session = ChromeSession("cold")
        report["chrome"] = session.version
        navigate(session, f"http://127.0.0.1:{port}/ods-viewer-e6-harness.html?cycles={args.cycles}")
        deadline = time.monotonic() + args.timeout
        head = {}
        while time.monotonic() < deadline:
            head = evaluate(session, f"(() => {{ const r = window.{NS}; return r ? "
                                     f"{{ done: r.done, seen: r.entries.length, fatal: r.fatal }} : null; }})()") or {}
            if head.get("done"):
                break
            time.sleep(2)
        report["timedOut"] = not head.get("done")
        report["pageFatal"] = head.get("fatal")
        report["workerUrl"] = evaluate(session, f"window.{NS}.workerUrl")
        for index in range(int(head.get("seen") or 0)):
            text = evaluate(session, f"JSON.stringify(window.{NS}.entries[{index}])")
            report["entries"].append(json.loads(text) if text else {"fatal": "not retrieved"})
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
    report["noiseFloor"] = noise_floor(report)
    report["verdicts"] = judge(report)
    report["completedAt"] = utc_now()
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f"report-{report['startedAt']}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)
    print(f"noise floor on {report['noiseFloor']['entry']}: open.begin {report['noiseFloor']['openBegins']} "
          f"-> B = {report['noiseFloor']['B']}")
    for v in report["verdicts"]["judged"]:
        print(f"{'PASS' if v['ok'] else 'FAIL'} {v['id']}: {json.dumps(v['detail'], ensure_ascii=False)[:200]}")
    for v in report["verdicts"]["notJudged"]:
        print(f"RECORDED {v['id']} ({v['why']}): {json.dumps(v['detail'], ensure_ascii=False)[:200]}")
    return 0 if report["verdicts"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
