#!/usr/bin/env python3
"""K ruling item 5 (revision 1) for host 0.2.45 (SPEC-M3-K-0.2.45 section 2, SPEC-M3-K-0.2.44 section 3; derived from tools/read_k_0245_product_path.py, not edited): the plain v29 arm, 3 rounds x 2
browsers, read against the committed 0.2.26 v21 records.  Reports: DIR/{chrome,firefox}-r{1,2,3}/report.json and
shell-manifest-override.json (run_k_0245_path.py's --out).

  P1  every report: exactly the population's 46 ids in order (else STOP), complete, last state ready, no page errors
  P2  entrypoint 022d0cd0..., no candidateCutover, override used = v83 with the frozen file sha, bound runner 7ba30235...
  P3  the anchor: release-0.2.26's e2-editor-v21 records under the old verdict() unchanged (v21 FAIL n => FAIL <= n, v21 NE
      => 0 FAIL, row 1' for recovery-returns-what-the-product-promised, else PASS 3/3); ids with no 0.2.26 row PASS 3/3;
      and exactly these cells read by their own rule (SPEC-M3-K-0.2.44 section 3):
        rows 1, 2  bulleting (both browsers): retired, every round FAIL with v27's shape
        row 7      boundary arrow (chrome): I-worker-inducer-single-shot, ruling Q3
        row 8      Enter (chrome): I-enter-raw-substring + the span-aware replay report on v29
        row 9      long document (both browsers): ruling Q4
  P5  report level: recoveryPairing held false, ok false, the verdict's prefix (F3-81's and F3-82's, spec v27 8 item 3)

  read_k_0245_product_path.py --dir DIR --enter-report REPORT         exit 0 iff K_PATH_HOLDS
  read_k_0245_product_path.py --dir DIR --enter-report REPORT --self-test

Exit 3 on STOP (the population differs: nothing is adjusted to fit).  It reads and writes nothing else.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
EVIDENCE = REPO / "findings/evidence"
POPULATION = EVIDENCE / "v28-083/f3-82/run-01"
ANCHOR = EVIDENCE / "release-0.2.26/product-path"
PAGE = "022d0cd0b5152f1ee9cabc74b10f5af2eb55935299228119a419ab717957759b"
MANIFEST, MANIFEST_SHA256 = "e2/editor-shell-v2-bundle-v83.json", "98371d7f7479021dc2b859bf78db796571d7070b8509548edf7db977bc214174"
BOUND_RUNNER = "7ba302353dd67d5f4c7643e1abc0e5c06105e7b7ebbb191b3c29b24b8e90a6a2"
BROWSERS, ROUNDS = ("chrome", "firefox"), (1, 2, 3)
RECOVERY = "recovery-returns-what-the-product-promised"
BULLETING = "bulleting-a-blank-line-does-not-demand-a-rollback"
BOUNDARY = "a-boundary-arrow-press-does-not-cost-the-work"
ENTER = "the-enter-key-reaches-the-document"
LONG = "editing-a-long-document-stays-responsive"
PAIR_VERDICT = "the recovery pair disagrees"
WHY = "auto-attach delivered no session for a document worker"


class Stop(Exception):
    pass


def outcome_counts(reports, cid):
    counts = {"PASS": 0, "FAIL": 0, "NOT_ESTABLISHED": 0}
    for r in reports:
        o = next(c for c in r["checks"] if c["id"] == cid).get("outcome")
        counts[o] = counts.get(o, 0) + 1
    return counts


def window_ne(browser):
    """The old judge's row 1' window, unchanged: git-tracked v8 reports whose record carries finding038Reproduced."""
    listed = subprocess.run(["git", "-C", str(EVIDENCE), "ls-files", "-z", "--", f"**/e2-editor-v8-{browser}-r*.json"],
                            capture_output=True, check=True).stdout.decode().split("\0")
    total = ne = 0
    for name in filter(None, listed):
        try:
            report = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rec = next((c for c in report.get("checks") or [] if isinstance(c, dict) and c.get("id") == RECOVERY), None)
        if rec is None or "finding038Reproduced" not in (rec.get("observed") or {}):
            continue
        total += 1
        ne += rec.get("outcome") == "NOT_ESTABLISHED"
    return total, ne


def verdict(old, new, cid, window):
    """The old judge's verdict() with old = the v21 counts."""
    if old["FAIL"] > 0:
        return new["FAIL"] <= old["FAIL"]
    if old["NOT_ESTABLISHED"] > 0:
        return new["FAIL"] == 0
    if cid == RECOVERY and window[1] > 0:
        return new["FAIL"] == 0
    return new["PASS"] == 3


def retired_shape(cell):
    observed = cell.get("observed") or {}
    return (cell.get("outcome") == "FAIL" and observed.get("state") == "ready" and observed.get("toast") == ""
            and observed.get("unverifiedSentence") is None)


def single_shot(cell):
    if cell.get("outcome") == "PASS":
        return True
    observed = cell.get("observed") or {}
    v, fallback = observed.get("verdict") or {}, observed.get("fallbackInducer") or {}
    return (cell.get("outcome") == "FAIL" and v.get("B1") is True and v.get("B2") is True and v.get("B3") is True
            and v.get("B4") is None and fallback.get("fired") is False and fallback.get("why") == WHY
            and fallback.get("attachedTypes") == [])


def raw_substring(cell):
    if cell.get("outcome") == "PASS":
        return True
    arms = (cell.get("observed") or {}).get("arms") or []
    if cell.get("outcome") != "FAIL" or len(arms) != 2:
        return False
    plain, shift = arms
    return (plain.get("outcome") == "PASS" and shift.get("shift") is True and shift.get("firstLanded") is True
            and shift.get("secondLanded") is True and shift.get("together") is True and shift.get("lineBreaksBetween") is False
            and shift.get("paragraphsAfter") == shift.get("paragraphsBefore") and shift.get("savedIsOdt") is True)


def long_document(cells):
    """Ruling Q4: (holds, signature fails)."""
    signatures, others = 0, 0
    for cell in cells:
        arms = (cell.get("observed") or {}).get("perArm") or []
        passing = [a for a in arms if (a.get("seconds") or 9) <= 1.0 and a.get("revisionAdvanced") is True]
        if len(arms) == 3 and len(passing) == 3 and cell.get("outcome") == "PASS":
            continue
        fast_dead = [a for a in arms if (a.get("seconds") or 9) < 0.08 and a.get("revisionAdvanced") is False]
        if len(arms) == 3 and len(fast_dead) == 1 and len(passing) == 2:
            signatures += 1
        else:
            others += 1
    return others == 0 and signatures <= 1, signatures


def read(reports, overrides, enter, anchor, population, windows):
    problems, special = [], {}
    # P1
    for browser in BROWSERS:
        want = population[browser]
        for n in ROUNDS:
            r = reports.get((browser, n))
            if r is None:
                raise Stop(f"{browser} r{n}: report missing")
            ids = [c["id"] for c in r.get("checks") or []]
            if ids != want:
                raise Stop(f"{browser} r{n}: {len(ids)} ids, not the population's {len(want)} in order")
            if r.get("complete") is not True or (r.get("liveness") or {}).get("lastState") != "ready" or r.get("pageErrors") is not None:
                problems.append(f"{browser} r{n}: P1 complete {r.get('complete')} lastState "
                                f"{(r.get('liveness') or {}).get('lastState')} pageErrors {r.get('pageErrors')}")
            # P2
            shell, override = r.get("servedShell") or {}, overrides.get((browser, n)) or {}
            if shell.get("entrypointSha256") != PAGE or r.get("candidateCutover") is not None or r.get("candidateSource") is not None:
                problems.append(f"{browser} r{n}: P2 page {shell.get('entrypointSha256')}")
            if override.get("used") != MANIFEST or (override.get("derivedFrom") or {}).get("sha256") != BOUND_RUNNER:
                problems.append(f"{browser} r{n}: P2 override {override.get('used')}")
            # P5
            pair = (r.get("recoveryPairing") or {}).get("held")
            if pair is not False or r.get("ok") is not False or not str(r.get("verdict") or "").startswith(PAIR_VERDICT):
                problems.append(f"{browser} r{n}: P5 held {pair} ok {r.get('ok')} verdict {str(r.get('verdict'))[:40]}")
    # P3
    for browser in BROWSERS:
        rs = [reports[(browser, n)] for n in ROUNDS]
        olds = anchor[browser]
        for cid in population[browser]:
            cells = [next(c for c in r["checks"] if c["id"] == cid) for r in rs]
            if cid == BULLETING:
                special[f"{browser} {cid}"] = "retired"
                if not all(retired_shape(c) for c in cells):
                    problems.append(f"{browser} {cid}: not v27's FAIL shape in every round")
                continue
            if cid == BOUNDARY and browser == "chrome":
                special[f"{browser} {cid}"] = "I-worker-inducer-single-shot"
                if not all(single_shot(c) for c in cells):
                    problems.append(f"{browser} {cid}: a FAIL that is not the single-shot shape (product RED)")
                continue
            if cid == ENTER and browser == "chrome":
                special[f"{browser} {cid}"] = "I-enter-raw-substring"
                if not all(raw_substring(c) for c in cells):
                    problems.append(f"{browser} {cid}: a FAIL that is not the raw-substring shape (product RED)")
                if (enter or {}).get("verdict") != "V24_ENTER_HOLDS":
                    problems.append(f"{browser} {cid}: the span-aware replay on v29 is {(enter or {}).get('verdict')}")
                continue
            if cid == LONG:
                held, signatures = long_document(cells)
                special[f"{browser} {cid}"] = f"ruling Q4, {signatures} signature FAIL"
                if not held:
                    problems.append(f"{browser} {cid}: Q4 red")
                continue
            new = outcome_counts(rs, cid)
            if cid not in olds:
                if new["PASS"] != 3:
                    problems.append(f"{browser} {cid}: no 0.2.26 row and {new}")
                continue
            old = olds[cid]
            if not verdict(old, new, cid, windows[browser]):
                problems.append(f"{browser} {cid}: v21 {old} -> v29 {new}")
    return ("K_PATH_HOLDS" if not problems else "K_PATH_RED"), problems, special


def load(directory):
    reports, overrides = {}, {}
    for browser in BROWSERS:
        for n in ROUNDS:
            d = directory / f"{browser}-r{n}"
            if (d / "report.json").is_file():
                reports[(browser, n)] = json.loads((d / "report.json").read_text(encoding="utf-8"))
            if (d / "shell-manifest-override.json").is_file():
                overrides[(browser, n)] = json.loads((d / "shell-manifest-override.json").read_text(encoding="utf-8"))
    return reports, overrides


def inputs():
    population = {b: [c["id"] for c in json.loads((POPULATION / b / "report.json").read_text(encoding="utf-8"))["checks"]]
                  for b in BROWSERS}
    anchor = {}
    for b in BROWSERS:
        rs = [json.loads((ANCHOR / f"e2-editor-v21-{b}-r{n}.json").read_text(encoding="utf-8")) for n in ROUNDS]
        anchor[b] = {c["id"]: outcome_counts(rs, c["id"]) for c in rs[0]["checks"]}
    return population, anchor, {b: window_ne(b) for b in BROWSERS}


def cell(reports, key, cid):
    return next(c for c in reports[key]["checks"] if c["id"] == cid)


def mutations():

    def flip_v21_3of3(reports):
        next(c for c in reports[("chrome", 2)]["checks"] if c["id"] == "product-save-button-writes-a-real-odt")["outcome"] = "FAIL"

    def new_id_not_3of3(reports):
        next(c for c in reports[("firefox", 1)]["checks"] if c["id"].startswith("v23-product-"))["outcome"] = "NOT_ESTABLISHED"

    def bulleting_rollback(reports):
        cell(reports, ("chrome", 1), BULLETING)["observed"]["state"] = "recoverable-error"

    def bulleting_pass(reports):
        cell(reports, ("firefox", 3), BULLETING)["outcome"] = "PASS"

    def boundary_b2_false(reports):
        cell(reports, ("chrome", 1), BOUNDARY)["observed"]["verdict"]["B2"] = False

    def boundary_other_inducer(reports):
        cell(reports, ("chrome", 3), BOUNDARY)["observed"]["fallbackInducer"]["fired"] = True

    def enter_plain_arm_fails(reports):
        cell(reports, ("chrome", 2), ENTER)["observed"]["arms"][0]["outcome"] = "FAIL"

    def enter_marker_lost(reports):
        cell(reports, ("chrome", 1), ENTER)["observed"]["arms"][1]["together"] = False

    def long_half_second_dead(reports):
        c = cell(reports, ("chrome", 1), LONG)
        c["outcome"] = "FAIL"
        c["observed"]["perArm"][0].update({"seconds": 0.5, "revisionAdvanced": False})

    def long_two_signatures(reports):
        for n in (1, 2):
            c = cell(reports, ("firefox", n), LONG)
            c["outcome"] = "FAIL"
            c["observed"]["perArm"][0].update({"seconds": 0.061, "revisionAdvanced": False})

    def page_moved(reports):
        reports[("chrome", 1)]["servedShell"]["entrypointSha256"] = "0" * 64

    def a_cutover(reports):
        reports[("firefox", 2)]["candidateCutover"] = {"profile": "e2-editor-v27"}

    def pairing_held(reports):
        reports[("chrome", 3)]["recoveryPairing"]["held"] = True

    def incomplete(reports):
        reports[("firefox", 1)]["complete"] = False

    return [flip_v21_3of3, new_id_not_3of3, bulleting_rollback, bulleting_pass, boundary_b2_false, boundary_other_inducer,
            enter_plain_arm_fails, enter_marker_lost, long_half_second_dead, long_two_signatures, page_moved, a_cutover,
            pairing_held, incomplete]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--enter-report", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    reports, overrides = load(args.dir)
    enter = json.loads(args.enter_report.read_text(encoding="utf-8")) if args.enter_report.is_file() else None
    population, anchor, windows = inputs()
    try:
        got, problems, special = read(reports, overrides, enter, anchor, population, windows)
    except Stop as stop:
        print(json.dumps({"verdict": "STOP", "why": str(stop)}, indent=1))
        return 3
    if args.self_test:
        if got != "K_PATH_HOLDS":
            print(f"self-test needs a holding input; this one is {got}: {problems[:5]}", file=sys.stderr)
            return 2
        results = {}
        for fn in mutations():
            mutated = copy.deepcopy(reports)
            fn(mutated)
            try:
                results[fn.__name__] = read(mutated, overrides, enter, anchor, population, windows)[0]
            except Stop:
                results[fn.__name__] = "STOP"
        def no_replay():
            return read(reports, overrides, {"verdict": "V24_ENTER_FAILS"}, anchor, population, windows)[0]
        results["enter-replay-red"] = no_replay()
        mutated = copy.deepcopy(reports)
        mutated[("chrome", 1)]["checks"].pop()
        try:
            results["one-id-missing"] = read(mutated, overrides, enter, anchor, population, windows)[0]
        except Stop:
            results["one-id-missing"] = "STOP"
        red = all(v != "K_PATH_HOLDS" for v in results.values())
        print(json.dumps({"selfTest": "ALL_RED" if red else "SOME_MUTATION_HELD", "mutations": len(results), "results": results}, indent=1))
        return 0 if red else 1
    print(json.dumps({"verdict": got, "problems": problems, "specialCells": special, "windows": windows,
                      "counts": {b: {cid: outcome_counts([reports[(b, n)] for n in ROUNDS], cid) for cid in population[b]} for b in BROWSERS}},
                     indent=1, ensure_ascii=False))
    return 0 if got == "K_PATH_HOLDS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
