#!/usr/bin/env python3
"""PL-1-v28 (SPEC-M3-v28-last-line-fallback 7.2): before the link, on the shipped v27 product, the 083 recipe on a
multi-paragraph document reaches the trigger v28's fallback is gated on.

The procedure is S3's (tools/check_v81_blank_line_bullet.py, imported, not edited), every input real: open the
two-plain ODT (`Plain first` / `E1-EMPTY-AFTER`), click in the page BELOW the text (CLICK, a fraction of #paper:
Writer puts the caret at the end of the last paragraph), press Enter (a new empty LAST paragraph), click the toolbar
bullet.  S3's procedure then types a marker and saves; that is recorded, not judged.  Two module globals are set
before the runs, which S3 reads at call time: LINE_END (the click point) and BARRIER_KEYS (+ selectionResultSeen).
Product: generation 81 as dist/ serves it (v81_f_products "after", profile e2-editor-v27, identity checked file by
file), with one check replaced: v81_f_products compares the served page with the TREE's, which was generation
81's candidate then and is v28's shell now; here it is compared with generation 81's frozen page
(e2/editor-shell-v2-bundle-v81.json).

A run HOLDS when the bullet's reply row is an error whose formatBarrier is exactly the trigger:
`failureShape == select-text-returned-none`, `route == collapsed`, `dispatched == true`, `selectionResultSeen ==
true`.  PL1_V28_HOLDS: every run of both browsers holds, full count.  This pins only that the trigger fires on WASM;
what v28's fallback then reads cannot be predicted from v27, and is not claimed (ruling 4 section 4 item 7).

  check_v28_pl1_last_line.py --out DIR [--browsers chrome,firefox] [--repetitions 3]
  check_v28_pl1_last_line.py --self-test REPORT     (each clause mutated on a holding report must be red)

--out must not exist.  Nothing under dist/ is written.  Not a timing measurement.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_v81_blank_line_bullet as s3  # noqa: E402

CLICK = (0.80, 0.15)
GENERATION_81 = s3.PROJECT / "e2/editor-shell-v2-bundle-v81.json"


def identity(mirror: Path) -> dict:
    result = s3.products.identity("after", mirror)
    frozen = {e["path"]: e["sha256"] for e in json.loads(GENERATION_81.read_text())["included"]}
    checks = dict(result["checks"])
    checks.pop("pageEqualsTree")
    checks["pageEqualsGeneration81"] = result["page"] == frozen[s3.products.PAGE]
    return {**result, "checks": checks, "ok": all(checks.values()), "generation81": str(GENERATION_81.name)}
TRIGGER = {"failureShape": "select-text-returned-none", "route": "collapsed", "dispatched": True,
           "selectionResultSeen": True}


def holds(run) -> bool:
    row = s3.press_row(run) or {}
    barrier = row.get("formatBarrier") or {}
    return (not run.get("fatal") and row.get("ok") is False
            and all(barrier.get(k) == v for k, v in TRIGGER.items()))


def verdict(report) -> tuple[str, list[str]]:
    problems = []
    config = report["config"]
    want = len(config["browsers"]) * config["repetitions"]
    runs = report["runs"]
    if not report["products"].get("after", {}).get("ok"):
        problems.append("generation 81 identity failed")
    if len(runs) != want:
        problems.append(f"{len(runs)} runs, wanted {want}")
    for run in runs:
        if not holds(run):
            row = s3.press_row(run) or {}
            problems.append(f"{run['browser']} {run['repetition']}: not the trigger: ok {row.get('ok')}, "
                            f"barrier {row.get('formatBarrier')}, fatal {bool(run.get('fatal'))}")
    return ("PL1_V28_HOLDS" if not problems else "PL1_V28_RED"), problems


def self_test(path: Path) -> int:
    report = json.loads(path.read_text())
    base, problems = verdict(report)
    cases = []
    if base != "PL1_V28_HOLDS":
        print(json.dumps({"selfTest": "NOT_APPLICABLE", "why": "the report does not hold", "problems": problems}))
        return 1

    def barrier_of(r):
        return s3.press_row(r)["formatBarrier"]
    for name, mutate in [
        ("route range-single", lambda r: barrier_of(r[0]).__setitem__("route", "range-single")),
        ("046's shape", lambda r: barrier_of(r[0]).__setitem__("failureShape", "multi-block-readback")),
        ("select result not seen", lambda r: barrier_of(r[-1]).__setitem__("selectionResultSeen", False)),
        ("not dispatched", lambda r: barrier_of(r[1]).__setitem__("dispatched", False)),
        ("the reply ok (verified)", lambda r: s3.press_row(r[0]).__setitem__("ok", True)),
        ("one run missing", lambda r: r.pop()),
    ]:
        mutated = copy.deepcopy(report)
        mutate(mutated["runs"])
        got, _ = verdict(mutated)
        cases.append({"case": name, "verdict": got, "ok": got == "PL1_V28_RED"})
    result = "ALL_AS_EXPECTED" if all(c["ok"] for c in cases) else "UNEXPECTED"
    print(json.dumps({"selfTest": result, "cases": cases}, indent=1))
    return 0 if result == "ALL_AS_EXPECTED" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", type=Path, metavar="REPORT")
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test)
    if not args.out:
        parser.error("--out is required")
    args.out.mkdir(parents=True, exist_ok=False)
    s3.LINE_END = CLICK
    s3.BARRIER_KEYS = s3.BARRIER_KEYS + ("selectionResultSeen",)
    raw_doc = s3.FIXTURE.read_bytes()
    if hashlib.sha256(raw_doc).hexdigest() != s3.FIXTURE_SHA256:
        raise SystemExit("two-plain.odt changed")
    config = {"products": ["after"], "browsers": [x for x in args.browsers.split(",") if x],
              "repetitions": args.repetitions}
    report = {"argv": sys.argv, "tool": "check_v28_pl1_last_line", "config": config, "click": CLICK,
              "trigger": TRIGGER, "fixture": {"path": str(s3.FIXTURE.relative_to(s3.REPO)),
                                              "sha256": s3.FIXTURE_SHA256}, "products": {}, "runs": []}
    scratch = Path(tempfile.mkdtemp(prefix="pl1-v28-", dir=s3.PROJECT / "build"))
    try:
        with s3.common.browser_lock("check_v28_pl1_last_line"):
            report["preRun"] = s3.common.pre_run_checks()
            if report["preRun"]["refuse"]:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            mirror = scratch / "after"
            s3.pp.build_mirror(s3.common.DIST, mirror, s3.products.overrides("after", [s3.OBSERVER]))
            report["products"]["after"] = identity(mirror)
            if report["products"]["after"]["ok"]:
                with s3.common.served(mirror) as base:
                    for browser in config["browsers"]:
                        for n in range(1, args.repetitions + 1):
                            run, session = {"product": "after", "browser": browser, "repetition": n}, None
                            try:
                                session = s3.common.open_browser(browser)
                                run["browserVersion"] = getattr(session, "version", None)
                                run.update(s3.one(session, browser, base, raw_doc, "set-list-unordered"))
                            except Exception:  # noqa: BLE001 -- recorded
                                run["fatal"] = traceback.format_exc()
                            finally:
                                if session is not None:
                                    run["cleanup"] = s3.common.close_browser(session)
                            report["runs"].append(run)
                            row = s3.press_row(run) or {}
                            print(browser, n, row.get("ok"), row.get("formatBarrier"),
                                  ((run.get("press") or {}).get("toast") or "")[:30], file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report["verdict"], report["problems"] = verdict(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], report["problems"], file=sys.stderr)
    return 0 if report["verdict"] == "PL1_V28_HOLDS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
