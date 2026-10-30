#!/usr/bin/env python3
"""S2′ (SPEC-M3-v27-finding-176 7.3): finding 083's path stays a toast, and the status strip says 待確認, not 失敗 --
the owner's path (a bullet in a NEW blank document).

Derived from tools/check_v80_blank_bullet.py (S2), which is IMPORTED and not edited (S2-80's evidence binds it), as
it imports B1 (tools/check_v79_blank_bullet.py, bound by B1-79).  B1's procedure (the host's blank template through
the page's file input, arms noclick/click, the real bullet click, real keys, the product's save) and B1's four
clauses and S2's three run unchanged, through S2's `judge_after`.  The differences are a closed list:
  1. Products (tools/v81_f_products.py): before = generation 80 (page from git 7745a26e9, profile v26); after =
     dist/ as served (generation-81 candidate, profile v27).  Identity checked, not assumed.
  2. after adds `press.latency == typed.latency == "• 項目符號：待確認"` (typing does not go through run(), so the
     strip keeps the press's text; S2 run-02 recorded typed.latency equal to press.latency).
  3. before is red FOR 176's SHELL ITEM when S2's judge_after PASSes (B1's and S2's conditions hold: the same path,
     the same toast) AND press.latency == "• 項目符號 失敗".  Red for any other reason fails the verdict.

  check_v81_blank_bullet.py --out DIR [--browsers chrome,firefox] [--arms noclick,click] [--repetitions 3]
  check_v81_blank_bullet.py --self-test REPORT

Verdict S2P_HOLDS iff both identities hold, every after run PASSes and every before run is red for 176's shell
item, with the full count.  --out must not exist.  Nothing under dist/ is written.  Not a timing measurement.
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

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
import check_v80_blank_bullet as s2  # noqa: E402  (assigns its toastBad read onto B1's PAGE on import)
import check_v79_blank_bullet as b1  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v81_f_products as products  # noqa: E402

PRODUCTS = ("before", "after")
REVIEW_STRIP, FAILED_STRIP = "• 項目符號：待確認", "• 項目符號 失敗"
assert "toastBad" in b1.PAGE, "S2's page read is not on B1's PAGE; S2′ needs S2's clauses"


def judge_after(run):
    outcome, why = s2.judge_after(run)
    if outcome != "PASS":
        return outcome, why
    press, typed = run.get("press") or {}, run.get("typed") or {}
    if press.get("latency") != REVIEW_STRIP:
        why.append(f"press strip {press.get('latency')!r}")
    if typed.get("latency") != REVIEW_STRIP:
        why.append(f"typed strip {typed.get('latency')!r}")
    return ("PASS" if not why else "FAIL"), why


def red_for_176_shell(run):
    outcome, _ = s2.judge_after(run)
    return outcome == "PASS" and (run.get("press") or {}).get("latency") == FAILED_STRIP


def verdict(report):
    browsers, arms, n = (report["config"][k] for k in ("browsers", "arms", "repetitions"))
    expected = len(browsers) * len(arms) * n
    problems = [f"{name}: identity failed" for name in PRODUCTS if not report["products"].get(name, {}).get("ok")]
    after = [r for r in report["runs"] if r["product"] == "after"]
    before = [r for r in report["runs"] if r["product"] == "before"]
    for r in after:
        r["outcome"], r["why"] = judge_after(r)
    for r in before:
        r["redFor176Shell"] = red_for_176_shell(r)
    if not (len(after) == expected and all(r["outcome"] == "PASS" for r in after)):
        problems.append(f"after: {sum(r['outcome'] == 'PASS' for r in after)}/{expected} PASS")
    if not (len(before) == expected and all(r["redFor176Shell"] for r in before)):
        problems.append(f"before: {sum(r['redFor176Shell'] for r in before)}/{expected} red for 176's shell item")
    return ("S2P_HOLDS" if not problems else "S2P_RED"), problems


def self_test(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    base, _ = verdict(copy.deepcopy(report))
    if base != "S2P_HOLDS":
        print(f"self-test needs a holding report; this one is {base}", file=sys.stderr)
        return 2

    def first(r, product):
        return next(x for x in r["runs"] if x["product"] == product)

    def after_press(r):
        return first(r, "after")["press"]

    mutations = {
        # S2's and B1's clauses, through S2's judge_after
        "after-toast-bad": lambda r: after_press(r).__setitem__("toastBad", True),
        "after-shows-code": lambda r: after_press(r).__setitem__("toast", f"• 項目符號：{s2.CODE}：" + after_press(r)["toast"]),
        "after-notice-shown": lambda r: after_press(r)["notice"].__setitem__("show", "1"),
        "after-marker-out-of-list": lambda r: first(r, "after")["saved"].__setitem__("markerInList", False),
        "after-other-shape": lambda r: b1.bullet_row(first(r, "after"))["barrier"].__setitem__("failureShape", "multi-block-readback"),
        # S2′'s own
        "after-press-strip-failed": lambda r: after_press(r).__setitem__("latency", FAILED_STRIP),
        "after-typed-strip-moved": lambda r: first(r, "after")["typed"].__setitem__("latency", "• 項目符號 12 ms"),
        "before-strip-review": lambda r: first(r, "before")["press"].__setitem__("latency", REVIEW_STRIP),
        "before-toast-bad-lost": lambda r: first(r, "before")["press"].__setitem__("toast", ""),
        "one-run-missing": lambda r: r["runs"].remove(first(r, "after")),
        "identity-failed": lambda r: r["products"]["after"].__setitem__("ok", False),
    }
    results = {}
    for name, mutate in mutations.items():
        mutated = copy.deepcopy(report)
        mutate(mutated)
        got, problems = verdict(mutated)
        results[name] = {"verdict": got, "problems": problems}
    red = all(v["verdict"] != "S2P_HOLDS" for v in results.values())
    print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "mutations": results},
                     indent=1, ensure_ascii=False))
    return 0 if red else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", type=Path, metavar="REPORT")
    parser.add_argument("--browsers", default="chrome,firefox")
    parser.add_argument("--arms", default="noclick,click")
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.self_test)
    if not args.out:
        parser.error("--out is required")
    args.out.mkdir(parents=True, exist_ok=False)
    raw_blank = b1.BLANK.read_bytes()
    config = {"products": list(PRODUCTS), "browsers": [x for x in args.browsers.split(",") if x],
              "arms": [x for x in args.arms.split(",") if x], "repetitions": args.repetitions}
    report = {"argv": sys.argv, "tool": "check_v81_blank_bullet", "config": config, "marker": b1.MARKER,
              "blank": {"path": str(b1.BLANK), "sha256": hashlib.sha256(raw_blank).hexdigest()},
              "products": {}, "runs": []}
    if report["blank"]["sha256"] != b1.BLANK_SHA256:
        raise SystemExit(f"blank template changed: {report['blank']['sha256']}")
    scratch = Path(tempfile.mkdtemp(prefix="s2p-blank-bullet-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("check_v81_blank_bullet"):
            report["preRun"] = common.pre_run_checks()
            if report["preRun"]["refuse"]:
                raise SystemExit(f"pre-run refused: {report['preRun']['refuse']}")
            for name in PRODUCTS:
                mirror = scratch / name
                pp.build_mirror(common.DIST, mirror, products.overrides(name, [b1.OBSERVER]))
                report["products"][name] = products.identity(name, mirror)
                if not report["products"][name]["ok"]:
                    print(name, "identity FAILED, not run:", report["products"][name]["checks"], file=sys.stderr, flush=True)
                    continue
                with common.served(mirror) as base:
                    for browser in config["browsers"]:
                        for arm in config["arms"]:
                            for n in range(1, args.repetitions + 1):
                                run, session = {"product": name, "browser": browser, "arm": arm, "repetition": n}, None
                                try:
                                    session = common.open_browser(browser)
                                    run["browserVersion"] = getattr(session, "version", None)
                                    run.update(b1.one(session, browser, base, arm, raw_blank, "after"))
                                except Exception:  # noqa: BLE001 -- recorded
                                    run["fatal"] = traceback.format_exc()
                                finally:
                                    if session is not None:
                                        run["cleanup"] = common.close_browser(session)
                                report["runs"].append(run)
                                press, typed = run.get("press") or {}, run.get("typed") or {}
                                print(name, browser, arm, n, press.get("pill"), repr(press.get("latency")),
                                      repr(typed.get("latency")), (press.get("toast") or "")[:40],
                                      "saved-in-list" if (run.get("saved") or {}).get("markerInList") else "",
                                      (run.get("fatal") or "").strip().splitlines()[-1:] or "", file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report["verdict"], report["problems"] = verdict(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], report["problems"], file=sys.stderr)
    return 0 if report["verdict"] == "S2P_HOLDS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
