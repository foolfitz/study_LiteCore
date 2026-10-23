#!/usr/bin/env python3
"""finding 164's work item (SPEC-M4-viewer-v2 §11): growth WITHIN one open, measured by count.  Record-only.

What it does: mirrors dist/ with symlinks, writes the probe page (web/ods-viewer-growth-probe{.html,-app.js}),
the viewer's shell modules, two ladder files and the plan into the MIRROR only, serves it, and lets the page
run every planned run: a fresh OdsViewerEngine, one open, K operations, close, dispose.

  paint    ladder/numeric-100k.ods          K 256 px tiles along a scroll path      K = 0, 200, 800, 3200
  switch   ladder/three-sheets-distinct.ods K x (setPart(i mod 3) + one 256 px tile) K = 0, 60, 240, 960
  control  ladder/three-sheets-distinct.ods one 4096x4096 px tile (64 MiB calloc)  K = 1

each --repeats times.  G(K) = sbrk at document-destroy-enter minus the same at K = 0 (same file, same repeat;
the control is compared with the switch arm's K = 0).  The `reading` block applies §11.3's pinned rules to the
numbers; it is a description, not a verdict, and the exit code is 0 whenever the page completed.

  probe_ods_viewer_intra_open_growth.py --selftest
  probe_ods_viewer_intra_open_growth.py [--profile ods-viewer-v2] [--repeats 2] [--out DIR]
Report: findings/evidence/m4-ods/viewer-v2/164-intra-open/report-<UTC>.json
"""
from __future__ import annotations

import argparse
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
from run_ods_viewer_phase_e import KILL_LINE, PROFILES, sha256_bytes, utc_now  # noqa: E402

PROFILE = "ods-viewer-v2"
HARNESS_LITERAL = b'"./profiles/ods-viewer-v2/sdk-worker.js"'
CORPUS = PROJECT / "test-docs" / "ods"
MANIFEST = CORPUS / "manifest.json"
DEFAULT_OUT = PROJECT.parent / "findings" / "evidence" / "m4-ods" / "viewer-v2" / "164-intra-open"
HARNESS = {"ods-viewer-growth-probe.html": PROJECT / "web" / "ods-viewer-growth-probe.html",
           "ods-viewer-growth-probe-app.js": PROJECT / "web" / "ods-viewer-growth-probe-app.js"}
NS = "__odsGrowth"
ARMS = {"paint": ("ladder/numeric-100k.ods", [0, 200, 800, 3200]),
        "switch": ("ladder/three-sheets-distinct.ods", [0, 60, 240, 960]),
        "control": ("ladder/three-sheets-distinct.ods", [1])}
CONTROL_BYTES = 4096 * 4096 * 4
FLAT_BYTES = 4 * 1024 * 1024
LINEAR_FLOOR = 8 * 1024 * 1024


def destroy_enter(run: dict) -> int | None:
    start = run.get("opsStartStage") or 0
    return next((s.get("sbrk") for s in (run.get("stages") or [])[start:]
                 if s.get("name") == "document-destroy-enter" and isinstance(s.get("sbrk"), int)), None)


def summarise(report: dict) -> dict:
    """G(K) per arm and repeat, then §11.3's readings on it."""
    runs = report.get("runs") or []
    by = {(r.get("arm"), r.get("repeat"), r.get("k")): r for r in runs}
    table, problems = {}, []
    for run in runs:
        if run.get("error") or run.get("workerCrashed") or run.get("operations") != run.get("k"):
            problems.append(f"{run.get('arm')} k={run.get('k')} r={run.get('repeat')}: error {run.get('error')}, "
                            f"crashed {run.get('workerCrashed')}, operations {run.get('operations')}")
        elif destroy_enter(run) is None:
            problems.append(f"{run.get('arm')} k={run.get('k')} r={run.get('repeat')}: no document-destroy-enter after the operations")
    repeats = sorted({r.get("repeat") for r in runs})
    for arm in ARMS:
        table[arm] = {}
        for rep in repeats:
            base = by.get(("switch" if arm == "control" else arm, rep, 0))
            base_de = destroy_enter(base) if base else None
            row = {}
            for k in ARMS[arm][1]:
                run = by.get((arm, rep, k))
                de = destroy_enter(run) if run else None
                row[str(k)] = {"destroyEnter": de, "G": (de - base_de) if de is not None and base_de is not None else None,
                               "peak": max([s["sbrk"] for s in (run or {}).get("stages") or [] if isinstance(s.get("sbrk"), int)],
                                           default=None)}
            table[arm][str(rep)] = row
    reading = {"rules": "SPEC-M4-viewer-v2 11.3", "problems": problems}
    control = [table["control"][str(rep)]["1"]["G"] for rep in repeats]
    reading["control"] = {"G": control, "holds": bool(control) and all(isinstance(g, int) and g >= CONTROL_BYTES
                                                                        for g in control)}
    reading["deterministic"] = {}
    for arm in ARMS:
        for k in ARMS[arm][1]:
            values = [table[arm][str(rep)][str(k)]["destroyEnter"] for rep in repeats]
            reading["deterministic"][f"{arm}/{k}"] = len(set(values)) == 1
    if not reading["control"]["holds"] or problems:
        reading["arms"] = "NOT READ: the positive control did not hold or a run failed (11.3, first rule)"
        return {"table": table, "reading": reading}
    reading["arms"] = {}
    for arm in ("paint", "switch"):
        ks = ARMS[arm][1]
        kmid, kmax = ks[-2], ks[-1]
        # Two repeats that differ: read the larger (11.3, second rule).
        gmid = max(table[arm][str(rep)][str(kmid)]["G"] for rep in repeats)
        gmax = max(table[arm][str(rep)][str(kmax)]["G"] for rep in repeats)
        rise = gmax - gmid
        if all(table[arm][str(rep)][str(kmax)]["G"] - table[arm][str(rep)][str(kmid)]["G"] <= FLAT_BYTES for rep in repeats):
            shape, extra = "flat", {"resolutionBytesPerOp": round(FLAT_BYTES / (kmax - kmid))}
        elif gmax >= LINEAR_FLOOR and gmid > 0 and 2 <= gmax / gmid <= 8:
            slope = rise / (kmax - kmid)
            peak = max(table[arm][str(rep)][str(kmax)]["peak"] or 0 for rep in repeats)
            shape, extra = "linear", {"slopeBytesPerOp": round(slope),
                                      "opsToKillLine": round((KILL_LINE - peak) / slope) if slope > 0 else None}
        else:
            shape, extra = "other", {}
        reading["arms"][arm] = {"shape": shape, "Kmid": kmid, "Kmax": kmax, "Gmid": gmid, "Gmax": gmax,
                                "rise": rise, **extra}
    return {"table": table, "reading": reading}


# -------------------------------------------------------------- selftest --
def synthetic(control_g=CONTROL_BYTES, paint=(0, 0, 0, 0), switch=(0, 0, 0, 0), repeats=(1, 2)) -> dict:
    runs = []
    base = 50_000_000

    def run(arm, rep, k, g):
        return {"arm": arm, "repeat": rep, "k": k, "operations": k, "error": None, "workerCrashed": False,
                "opsStartStage": 1, "stages": [{"name": "open.begin", "sbrk": base},
                                               {"name": "document-destroy-enter", "sbrk": base + g}]}
    for rep in repeats:
        runs += [run("paint", rep, k, g) for k, g in zip(ARMS["paint"][1], paint)]
        runs += [run("switch", rep, k, g) for k, g in zip(ARMS["switch"][1], switch)]
        runs.append(run("control", rep, 1, control_g))
    return {"runs": runs}


def selftest() -> int:
    mib = 1024 * 1024
    cases = [
        ("everything flat", synthetic(), lambda s: s["reading"]["arms"]["paint"]["shape"] == "flat"
         and s["reading"]["arms"]["switch"]["shape"] == "flat"),
        ("the control below 64 MiB stops every reading", synthetic(control_g=60 * mib),
         lambda s: isinstance(s["reading"]["arms"], str) and not s["reading"]["control"]["holds"]),
        ("a run with an error stops every reading",
         (lambda r: (r["runs"][2].update(error={"code": "X"}), r)[1])(synthetic()),
         lambda s: isinstance(s["reading"]["arms"], str)),
        ("8 KB per paint reads linear", synthetic(paint=(0, 2 * mib, 6 * mib, 25 * mib)),
         lambda s: s["reading"]["arms"]["paint"]["shape"] == "linear"
         and 7_000 < s["reading"]["arms"]["paint"]["slopeBytesPerOp"] < 9_000),
        ("a one-off 4 MiB step reads flat, not linear", synthetic(paint=(0, 4 * mib, 4 * mib, 4 * mib)),
         lambda s: s["reading"]["arms"]["paint"]["shape"] == "flat"),
        ("a jump that is not proportional reads other", synthetic(switch=(0, 0, 1 * mib, 90 * mib)),
         lambda s: s["reading"]["arms"]["switch"]["shape"] == "other"),
        ("two repeats that differ are flagged",
         (lambda r: (r["runs"][1]["stages"][1].update(sbrk=50_008_192), r)[1])(synthetic()),
         lambda s: s["reading"]["deterministic"]["paint/200"] is False and not isinstance(s["reading"]["arms"], str)),
        ("a run without document-destroy-enter stops every reading",
         (lambda r: (r["runs"][3].update(stages=r["runs"][3]["stages"][:1]), r)[1])(synthetic()),
         lambda s: isinstance(s["reading"]["arms"], str) and s["reading"]["problems"]),
    ]
    passed = 0
    for label, report, check in cases:
        ok = bool(check(summarise(report)))
        passed += ok
        print(("PASS " if ok else "FAIL ") + label)
    print(f"selftest: {passed}/{len(cases)}")
    return 0 if passed == len(cases) else 1


# ---------------------------------------------------------------- browser --
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--profile", choices=PROFILES, default=PROFILE)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--timeout", type=float, default=3600)
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    gate = preconditions()
    profile_manifest = PROJECT / "dist" / "profiles" / args.profile / "sdk-manifest.json"
    if not profile_manifest.is_file():
        raise SystemExit(f"{profile_manifest} does not exist: the viewer is not linked")

    from r7_support import evaluate, wait_page                      # noqa: E402
    from run_browser_probe import ChromeSession, free_port          # noqa: E402
    from run_e2_c_page_smoke import navigate                        # noqa: E402
    from run_e2_c_product_path import build_mirror                  # noqa: E402

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_path = {e["path"]: e for e in manifest["entries"]}
    overrides = {path: source.read_bytes() for path, source in PAGE_FILES.items() if path.startswith("viewer-shell/")}
    overrides.update({path: source.read_bytes() for path, source in HARNESS.items()})
    app = overrides["ods-viewer-growth-probe-app.js"]
    if app.count(HARNESS_LITERAL) != 1:
        raise SystemExit(f"the probe page has {app.count(HARNESS_LITERAL)} worker literals, not 1")
    if args.profile != PROFILE:
        overrides["ods-viewer-growth-probe-app.js"] = app.replace(
            HARNESS_LITERAL, f'"./profiles/{args.profile}/sdk-worker.js"'.encode())
    staged, rel_of = [], {}
    for index, path in enumerate(sorted({f for f, _ in ARMS.values()})):
        payload = (CORPUS / path).read_bytes()
        if sha256_bytes(payload) != by_path[path]["sha256"]:
            raise SystemExit(f"{path}: the file's sha differs from the manifest")
        rel = f"ods-growth-cases/{index:03d}/{Path(path).name}"
        overrides[rel] = payload
        rel_of[path] = rel
        staged.append({"path": path, "sha256": by_path[path]["sha256"], "bytes": len(payload)})
    plan = [{"arm": arm, "path": path, "name": Path(path).name, "file": "./" + rel_of[path], "k": k, "repeat": rep}
            for rep in range(1, args.repeats + 1) for arm, (path, ks) in ARMS.items() for k in ks]
    overrides["ods-growth-plan.json"] = json.dumps(plan, ensure_ascii=False).encode("utf-8")

    scratch = Path(tempfile.mkdtemp(prefix="ods-growth-"))
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

    report = {"schemaVersion": 1, "release": "m4-ods-growth-probe", "spec": "specs/SPEC-M4-viewer-v2.md §11",
              "evidenceClass": "probe (record-only)", "level": "sdk",
              "startedAt": utc_now(), "profile": args.profile, "preconditions": gate,
              "profileManifestSha256": sha256_bytes(profile_manifest.read_bytes()),
              "probeWasmSha256": sha256_bytes((profile_manifest.parent / "probe.wasm").read_bytes()),
              "workerSha256": sha256_bytes((profile_manifest.parent / "sdk-worker.js").read_bytes()),
              "pageFiles": {p: sha256_bytes(b) for p, b in overrides.items() if not p.startswith("ods-growth-cases")},
              "repeats": args.repeats, "arms": {a: {"path": p, "k": ks} for a, (p, ks) in ARMS.items()},
              "staged": staged, "plan": plan, "runs": []}
    session = server = None
    started = time.monotonic()
    try:
        port = free_port()
        server = subprocess.Popen([sys.executable, str(PROJECT / "web" / "serve.py"), "--port", str(port),
                                   "--root", str(root)], cwd=PROJECT,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_page(f"http://127.0.0.1:{port}/ods-viewer-growth-probe.html")
        session = ChromeSession("cold")
        report["chrome"] = session.version
        navigate(session, f"http://127.0.0.1:{port}/ods-viewer-growth-probe.html")
        deadline = time.monotonic() + args.timeout
        head = {}
        while time.monotonic() < deadline:
            head = evaluate(session, f"(() => {{ const r = window.{NS}; return r ? "
                                     f"{{ done: r.done, seen: r.runs.length, fatal: r.fatal }} : null; }})()") or {}
            if head.get("done"):
                break
            time.sleep(2)
        report["timedOut"] = not head.get("done")
        report["pageFatal"] = head.get("fatal")
        report["workerUrl"] = evaluate(session, f"window.{NS}.workerUrl")
        for index in range(int(head.get("seen") or 0)):
            text = evaluate(session, f"JSON.stringify(window.{NS}.runs[{index}])")
            report["runs"].append(json.loads(text) if text else {"fatal": "not retrieved"})
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
    report.update(summarise(report))
    report["completedAt"] = utc_now()
    args.out.mkdir(parents=True, exist_ok=True)
    out = args.out / f"report-{report['startedAt']}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)
    for arm, reps in report["table"].items():
        for rep, row in reps.items():
            print(f"{arm} r{rep}: " + "  ".join(f"K={k} G={v['G']} dE={v['destroyEnter']}" for k, v in row.items()))
    print(json.dumps(report["reading"], ensure_ascii=False))
    return 0 if not report["timedOut"] and not report["pageFatal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
