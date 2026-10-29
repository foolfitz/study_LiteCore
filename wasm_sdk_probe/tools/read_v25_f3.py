#!/usr/bin/env python3
"""SPEC-M3-link-batch-v25 section 16: F3's verdict, read from the runner's report.json files only.

  python3 tools/read_v25_f3.py --v25 <f3 run dir>      (expects <dir>/{chrome,firefox}/report.json)
  python3 tools/read_v25_f3.py --v25 <dir> --self-test  (mutations of the real inputs must each turn red)

Population (form two), per browser, generated from the BASELINE report -- v24 T4's verdict run, run-02:
  P        the rows of k-nine-cells/DISPOSITIONS.md whose disposition starts with **product**, parsed
           from the table (today rows 1-6): v25 must be PASS.
  excluded check ids starting with `v23-product-` (the four arms; F4 judges them).
  others   v24 PASS -> v25 PASS; v24 not PASS -> v25 the same outcome or PASS.  Every move to PASS
           is listed by name (`improved`), never passed over silently.
The two reports' id sets must be equal per browser; an empty report or zero P rows is red.

--rule correction-1 (the default; spec 16.1, written after run-01 and before run-02): the cell
`notice-action-recovers-the-session` leaves the no-regression group and is read from the SAME report's
`recoveryPairing` (the runner's record of the pair): `held` true; its `bulleting` equal to the
`bulleting-a-blank-line-does-not-demand-a-rollback` cell's outcome and its `noticeAction` equal to this
cell's; and when bulleting is PASS this cell must be NOT_ESTABLISHED (the designed abstain, the 0.2.26
anchor's reading).  A missing record is red.  --rule pinned reproduces section 16 as written (read-01).
Exit 0 iff F3_HOLDS.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
BASELINE = REPO / "findings/evidence/link-batch-v24/pre-count/t4/run-02"
DISPOSITIONS = REPO / "findings/evidence/host-0.2.39/k-nine-cells/DISPOSITIONS.md"
BROWSERS = ("chrome", "firefox")
NOTICE = "notice-action-recovers-the-session"
BULLETING = "bulleting-a-blank-line-does-not-demand-a-rollback"
ROW = re.compile(r"^\| (\d+) \| (chrome|firefox) \| ([a-z0-9-]+) \| (.*?) \|")


def product_rows(text: str) -> list[tuple[int, str, str]]:
    out = []
    for line in text.splitlines():
        m = ROW.match(line)
        if m and m.group(4).startswith("**product"):
            out.append((int(m.group(1)), m.group(2), m.group(3)))
    return out


def outcomes(report: dict) -> dict[str, str]:
    return {c["id"]: c.get("outcome") for c in report.get("checks", [])}


def read(baseline: dict[str, dict], v25: dict[str, dict], dispositions: str, rule: str = "correction-1") -> dict:
    problems, rows, improved = [], [], []
    p_rows = product_rows(dispositions)
    if not p_rows:
        problems.append("DISPOSITIONS has no product rows: P is empty")
    for browser in BROWSERS:
        base, new = outcomes(baseline.get(browser, {})), outcomes(v25.get(browser, {}))
        if not base or not new:
            problems.append(f"{browser}: {'baseline' if not base else 'v25'} report has no checks")
            continue
        if set(base) != set(new):
            problems.append(f"{browser}: id sets differ: only v24 {sorted(set(base) - set(new))}, "
                            f"only v25 {sorted(set(new) - set(base))}")
        p_ids = {check for _, b, check in p_rows if b == browser}
        for check in sorted(p_ids - set(base)):
            problems.append(f"{browser}: P row {check} is not in the baseline report")
        for check in sorted(set(base) & set(new)):
            was, now = base[check], new[check]
            if check.startswith("v23-product-"):
                group, ok = "excluded", True
            elif rule == "correction-1" and check == NOTICE:
                group = "recovery-pairing"
                pairing = v25.get(browser, {}).get("recoveryPairing")
                why = []
                if not isinstance(pairing, dict):
                    why.append("no recoveryPairing record")
                else:
                    if pairing.get("held") is not True:
                        why.append(f"held {pairing.get('held')!r}")
                    if pairing.get("bulleting") != new.get(BULLETING):
                        why.append(f"record bulleting {pairing.get('bulleting')!r} != check {new.get(BULLETING)!r}")
                    if pairing.get("noticeAction") != now:
                        why.append(f"record noticeAction {pairing.get('noticeAction')!r} != check {now!r}")
                    if new.get(BULLETING) == "PASS" and now != "NOT_ESTABLISHED":
                        why.append(f"bulleting PASS but this cell is {now}, not the designed abstain")
                ok = not why
                if why:
                    problems.append(f"{browser} {check} [recovery-pairing]: {'; '.join(why)}")
            elif check in p_ids:
                group, ok = "P", now == "PASS"
            elif was == "PASS":
                group, ok = "no-regression", now == "PASS"
            else:
                group, ok = "same-or-pass", now in (was, "PASS")
            if ok and group != "excluded" and was != "PASS" and now == "PASS":
                improved.append(f"{browser} {check}: {was} -> PASS ({group})")
            rows.append({"browser": browser, "check": check, "group": group, "v24": was, "v25": now, "ok": ok})
            if not ok and group != "recovery-pairing":
                problems.append(f"{browser} {check} [{group}]: v24 {was} -> v25 {now}")
    counts = {b: {g: sum(1 for r in rows if r["browser"] == b and r["group"] == g)
                  for g in ("P", "no-regression", "same-or-pass", "excluded")
                  + (("recovery-pairing",) if rule == "correction-1" else ())} for b in BROWSERS}
    head = {"verdict": "F3_HOLDS" if not problems else "F3_RED"} | ({"rule": rule} if rule == "correction-1" else {})
    return {**head, "productRows": p_rows, "counts": counts,
            "improved": improved, "problems": problems, "rows": rows}


def load(directory: Path) -> dict[str, dict]:
    return {b: json.loads((directory / b / "report.json").read_text(encoding="utf-8")) for b in BROWSERS}


def mutations(v25: dict[str, dict], baseline: dict[str, dict], dispositions: str):
    def checks(r, b):
        return r[b]["checks"]

    def regress(r):  # a v24-PASS, non-P, non-excluded check turned FAIL
        base = outcomes(baseline["chrome"])
        p = {c for _, b, c in product_rows(dispositions) if b == "chrome"}
        victim = next(c for c in checks(r, "chrome")
                      if base.get(c["id"]) == "PASS" and c["id"] not in p and c["id"] != NOTICE
                      and not c["id"].startswith("v23-product-"))
        victim["outcome"] = "FAIL"

    def p_not_established(r):
        p = next(c for _, b, c in product_rows(dispositions) if b == "firefox")
        next(c for c in checks(r, "firefox") if c["id"] == p)["outcome"] = "NOT_ESTABLISHED"

    def same_or_pass_moved(r):  # a v24 non-PASS (not P) that moves to another non-PASS outcome
        base = outcomes(baseline["firefox"])
        p = {c for _, b, c in product_rows(dispositions) if b == "firefox"}
        victim = next(c for c in checks(r, "firefox") if base.get(c["id"]) == "NOT_ESTABLISHED"
                      and c["id"] not in p and not c["id"].startswith("v23-product-"))
        victim["outcome"] = "FAIL"

    def missing(r):
        checks(r, "chrome").pop()

    def extra(r):
        checks(r, "firefox").append({"id": "a-check-v24-never-had", "outcome": "PASS"})

    def empty(r):
        r["chrome"]["checks"] = []

    def pairing_not_held(r):
        r["chrome"]["recoveryPairing"]["held"] = False

    def pairing_disagrees(r):  # the record says PASS, the check says NE
        r["firefox"]["recoveryPairing"]["noticeAction"] = "PASS"

    def notice_pass_while_bulleting_pass(r):  # record and check agree, but the abstain is missing
        next(c for c in checks(r, "chrome") if c["id"] == NOTICE)["outcome"] = "PASS"
        r["chrome"]["recoveryPairing"]["noticeAction"] = "PASS"

    def pairing_missing(r):
        del r["firefox"]["recoveryPairing"]

    out = []
    for fn in (regress, p_not_established, same_or_pass_moved, missing, extra, empty, pairing_not_held,
               pairing_disagrees, notice_pass_while_bulleting_pass, pairing_missing):
        mutated = copy.deepcopy(v25)
        fn(mutated)
        out.append((fn.__name__, mutated, dispositions))
    no_product = re.sub(r"\*\*product", "product", dispositions)
    out.append(("no_product_rows", v25, no_product))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--v25", type=Path, required=True, help="F3 run dir with chrome/ and firefox/ report.json")
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--dispositions", type=Path, default=DISPOSITIONS)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--rule", choices=("correction-1", "pinned"), default="correction-1")
    args = parser.parse_args()
    baseline, v25 = load(args.baseline), load(args.v25)
    dispositions = args.dispositions.read_text(encoding="utf-8")
    result = read(baseline, v25, dispositions, args.rule)
    if args.self_test:
        outcomes_ = {name: read(baseline, mutated, text, args.rule)["verdict"]
                     for name, mutated, text in mutations(v25, baseline, dispositions)}
        report = {"base": result["verdict"], "mutations": outcomes_,
                  "selfTest": "PASS" if result["verdict"] == "F3_HOLDS"
                  and all(v == "F3_RED" for v in outcomes_.values()) else "FAIL"}
        print(json.dumps(report, indent=1))
        return 0 if report["selfTest"] == "PASS" else 1
    result["inputs"] = {"baseline": str(args.baseline), "v25": str(args.v25), "dispositions": str(args.dispositions)}
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if result["verdict"] == "F3_HOLDS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
