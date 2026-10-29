#!/usr/bin/env python3
"""S2 (SPEC-M3-select-all-v26 5.5): finding 174 on the owner's path -- the bullet's review toast is not an error.

Owner, host 0.2.41: a bullet in a NEW blank document worked, and a red box said `MUTATION_OUTCOME_UNKNOWN：the
synchronous selection read did not provide readable text; …` before 083's sentence.  Generation 80 shows a
`review` as the label and the sentence, not in the error style, with the code and the engine's message on the
console.

B1's procedure, unchanged: tools/check_v79_blank_bullet.py is IMPORTED and not edited (B1-79's evidence binds it).
Its `one()` runs every step (the real bullet click, real keys, the product's save) for both products here -- it is
called with its own "after" path for both, because the early return it has for "before" belonged to 173's broken
page, and generation 79's page is the fixed one.  Two differences, a closed list:
  1. Products (tools/v80_f_products.py): before = generation 79 (page, client, session from git 9f084bf06, profile
     v25); after = dist/ as served (generation-80 candidate, profile v26).  Identity checked, not assumed.
  2. The page read adds `toastBad` (`#toast` has the `bad` class -- the error style toast(…, true) sets).

An `after` run PASSes when B1's judge_after PASSes (173's shape reached, ready, no notice, 083's sentence, the
queue open, the marker in a list in the saved ODT) AND the toast is not `bad`, does not contain
`MUTATION_OUTCOME_UNKNOWN`, and does not contain the engine's English (`selection read`).
A `before` run is red FOR 174 when B1's judge_after PASSes (so it is 173-fixed and reached the same path) AND the
toast is `bad` AND contains `MUTATION_OUTCOME_UNKNOWN`.  Red for any other reason fails the verdict.

  check_v80_blank_bullet.py --out DIR [--browsers chrome,firefox] [--arms noclick,click] [--repetitions 3]
  check_v80_blank_bullet.py --self-test REPORT

Verdict S2_HOLDS iff both identities hold, every after run PASSes and every before run is red for 174, with the
full count.  --out must not exist.  Nothing under dist/ is written.  Not a timing measurement: no desk gate.
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
import check_v79_blank_bullet as b1  # noqa: E402
import run_e2_c_product_path as pp  # noqa: E402
import v21_shakedown_common as common  # noqa: E402
import v80_f_products as products  # noqa: E402

CODE, ENGLISH = "MUTATION_OUTCOME_UNKNOWN", "selection read"
PRODUCTS = ("before", "after")
# B1's page read plus the toast's style.  Assigned onto the imported module so its wait() and one() read it.
b1.PAGE = b1.PAGE.replace("toast: document.querySelector('#toast')?.textContent,",
                          "toast: document.querySelector('#toast')?.textContent,\n"
                          "  toastBad: document.querySelector('#toast')?.classList.contains('bad') ?? null,")
assert "toastBad" in b1.PAGE, "B1's page read changed shape; S2 cannot add the toast style to it"


def judge_after(run):
    outcome, why = b1.judge_after(run)
    if outcome != "PASS":
        return outcome, why
    press = run.get("press") or {}
    toast = press.get("toast") or ""
    if press.get("toastBad") is not False:
        why.append(f"toast style bad={press.get('toastBad')!r}")
    if CODE in toast:
        why.append("toast shows the code")
    if ENGLISH in toast:
        why.append("toast shows the engine's English")
    return ("PASS" if not why else "FAIL"), why


def red_for_174(run):
    outcome, _ = b1.judge_after(run)
    press = run.get("press") or {}
    return outcome == "PASS" and press.get("toastBad") is True and CODE in (press.get("toast") or "")


def verdict(report):
    browsers, arms, n = (report["config"][k] for k in ("browsers", "arms", "repetitions"))
    expected = len(browsers) * len(arms) * n
    problems = [f"{name}: identity failed" for name in PRODUCTS if not report["products"].get(name, {}).get("ok")]
    after = [r for r in report["runs"] if r["product"] == "after"]
    before = [r for r in report["runs"] if r["product"] == "before"]
    for r in after:
        r["outcome"], r["why"] = judge_after(r)
    for r in before:
        r["redFor174"] = red_for_174(r)
    if not (len(after) == expected and all(r["outcome"] == "PASS" for r in after)):
        problems.append(f"after: {sum(r['outcome'] == 'PASS' for r in after)}/{expected} PASS")
    if not (len(before) == expected and all(r["redFor174"] for r in before)):
        problems.append(f"before: {sum(r['redFor174'] for r in before)}/{expected} red for 174")
    return ("S2_HOLDS" if not problems else "S2_RED"), problems


def self_test(path: Path) -> int:
    report = json.loads(path.read_text(encoding="utf-8"))
    base, _ = verdict(copy.deepcopy(report))
    if base != "S2_HOLDS":
        print(f"self-test needs a holding report; this one is {base}", file=sys.stderr)
        return 2

    def first(r, product):
        return next(x for x in r["runs"] if x["product"] == product)

    def after_press(r):
        return first(r, "after")["press"]

    mutations = {
        "after-toast-bad": lambda r: after_press(r).__setitem__("toastBad", True),
        "after-toast-style-unread": lambda r: after_press(r).__setitem__("toastBad", None),
        "after-shows-code": lambda r: after_press(r).__setitem__("toast", f"• 項目符號：{CODE}：" + after_press(r)["toast"]),
        "after-shows-english": lambda r: after_press(r).__setitem__("toast", after_press(r)["toast"] + " selection read"),
        "after-notice-shown": lambda r: after_press(r)["notice"].__setitem__("show", "1"),
        "after-marker-out-of-list": lambda r: first(r, "after")["saved"].__setitem__("markerInList", False),
        "before-not-bad": lambda r: first(r, "before")["press"].__setitem__("toastBad", False),
        "before-no-code": lambda r: first(r, "before")["press"].__setitem__(
            "toast", first(r, "before")["press"]["toast"].replace(CODE, "")),
        "one-run-missing": lambda r: r["runs"].remove(first(r, "after")),
        "identity-failed": lambda r: r["products"]["after"].__setitem__("ok", False),
    }
    results = {}
    for name, mutate in mutations.items():
        mutated = copy.deepcopy(report)
        mutate(mutated)
        got, problems = verdict(mutated)
        results[name] = {"verdict": got, "problems": problems}
    red = all(v["verdict"] != "S2_HOLDS" for v in results.values())
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
    report = {"argv": sys.argv, "tool": "check_v80_blank_bullet", "config": config, "marker": b1.MARKER,
              "blank": {"path": str(b1.BLANK), "sha256": hashlib.sha256(raw_blank).hexdigest()},
              "products": {}, "runs": []}
    if report["blank"]["sha256"] != b1.BLANK_SHA256:
        raise SystemExit(f"blank template changed: {report['blank']['sha256']}")
    scratch = Path(tempfile.mkdtemp(prefix="s2-blank-bullet-", dir=PROJECT / "build"))
    try:
        with common.browser_lock("check_v80_blank_bullet"):
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
                                press = run.get("press") or {}
                                print(name, browser, arm, n, press.get("pill"), "bad" if press.get("toastBad") else "plain",
                                      (press.get("toast") or "")[:70],
                                      "saved-in-list" if (run.get("saved") or {}).get("markerInList") else "",
                                      (run.get("fatal") or "").strip().splitlines()[-1:] or "", file=sys.stderr, flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report["verdict"], report["problems"] = verdict(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(report["verdict"], report["problems"], file=sys.stderr)
    return 0 if report["verdict"] == "S2_HOLDS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
