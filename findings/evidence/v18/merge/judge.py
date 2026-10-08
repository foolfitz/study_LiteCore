#!/usr/bin/env python3
"""Reader for the merge WASM shakedown in this directory (../PREDICTION.md M1-M4).

Re-run:  python3 -I judge.py                     (reads shakedown-/control-/pair- files for chrome and firefox here)
         python3 -I judge.py --dir DIR --profile P --page SHA   (another directory; used by selftest.sh on v17's run)

It reads only: shakedown-<b>.json, control-<b>.json, pair-<b>.stdout.txt, the *.stderr.txt next to them, and the
kept documents in shakedown-<b>.docs/ and control-<b>.docs/.  It writes nothing.  Exit 0 = every criterion HIT on
every browser; 1 = a MISS; 3 = a report is missing or unreadable (that part was not done).

Written 2026-10-08 after the Chrome merge step had run and while the Firefox one was running; the expected values
are copied from ../PREDICTION.md (committed 15eca506, before the chain), not from any report.
"""
import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=str(Path(__file__).resolve().parent))
ap.add_argument("--profile", default="e2-editor-v18")
ap.add_argument("--page", default="cfc8ba1d54dc4bef52baebc34f9d5f60ffe9cc4af9bee8c7a326bb02b2221cda")
ap.add_argument("--browsers", nargs="+", default=["chrome", "firefox"])
args = ap.parse_args()
D = Path(args.dir)

# ---- PREDICTION.md M1-M4 -------------------------------------------------------------------------
CASES_PER_REPORT = 56
ROUNDS = (1, 2)
REFUSED = {  # case -> (stage, keyPosted)
    "C15": ("key-deadline", True), "C16": ("key-deadline", True),
    "C17": ("anchor-mismatch", False),
    "C29": ("nothing-selected", False), "C30": ("nothing-selected", False),
    "F01": ("anchor-mismatch", False), "F02": ("anchor-mismatch", False),
}
SELECTION_DELETE = {"G01"}
SPLIT = Counter({"verified-key-undo": 40, "refused": 14, "verified-selection-delete": 2})
M2_0_FIXTURES = {"boundaries", "boundaries-indent", "text-frame"}
KEPT = {"after-key": 42, "follow": 42, "reopened": 14}
REDRAW_FAILED = "重繪失敗"


def expected_outcome(case):
    if case in REFUSED:
        return ("refused",) + REFUSED[case]
    if case in SELECTION_DELETE:
        return ("verified-selection-delete", None, None)
    return ("verified-key-undo", None, None)


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as e:
        return e


def paragraphs(odt):
    """Count of text:p / text:h start tags in content.xml; -1 if unreadable."""
    try:
        with zipfile.ZipFile(odt) as z:
            xml = z.read("content.xml").decode("utf-8")
    except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError):
        return -1
    return len(re.findall(r"<text:[ph][ >/]", xml))


verdicts = {}
not_done = []
for b in args.browsers:
    print(f"\n## {b}\n")
    shake, ctrl = load(D / f"shakedown-{b}.json"), load(D / f"control-{b}.json")
    pair_out = load(D / f"pair-{b}.stdout.txt")
    bad = [n for n, r in (("shakedown", shake), ("control", ctrl), ("pair", pair_out)) if not isinstance(r, dict)]
    if bad:
        print(f"NOT DONE: unreadable or missing {bad}: "
              + "; ".join(f"{n}: {r}" for n, r in (("shakedown", shake), ("control", ctrl), ("pair", pair_out))
                          if not isinstance(r, dict)))
        not_done.append(b)
        continue
    stderr = {n: (D / f"{n}-{b}.stderr.txt") for n in ("shakedown", "control", "pair")}
    stderr_sizes = {n: (p.stat().st_size if p.is_file() else None) for n, p in stderr.items()}

    # ---- M1 ------------------------------------------------------------------------------------
    m1 = []
    for name, r, is_control in (("shakedown", shake, False), ("control", ctrl, True)):
        cand = r.get("candidate") or {}
        cases = r.get("cases") or []
        row = {
            "profile": cand.get("profile") == args.profile,
            "page": cand.get("pageSha256") == args.page,
            "restOfShellEqualsSource": r.get("restOfShellEqualsSource") is True,
            "bootReady": (r.get("boot") or {}).get("state") == "ready",
            "control flag": r.get("control") is is_control,
            "56 records": len(cases) == CASES_PER_REPORT,
            "no runner-error": not any(c.get("outcome") == "runner-error" for c in cases),
            "stderr empty": stderr_sizes[name] == 0,
            "complete (completedAt)": bool(r.get("completedAt")),
        }
        bad_keys = [k for k, v in row.items() if not v]
        print(f"M1 {name}: profile={cand.get('profile')} page={str(cand.get('pageSha256'))[:16]} "
              f"boot={(r.get('boot') or {}).get('state')} records={len(cases)} stderr={stderr_sizes[name]} "
              f"started={r.get('startedAt')} completed={r.get('completedAt')} -> "
              + ("ok" if not bad_keys else f"FAILS {bad_keys}"))
        m1.append(not bad_keys)
    print(f"M1 pair stderr bytes: {stderr_sizes['pair']}")
    m1.append(stderr_sizes["pair"] == 0)

    # ---- M2 ------------------------------------------------------------------------------------
    m2 = []
    cases = shake["cases"]
    keys = Counter((c["case"], c["round"]) for c in cases)
    each_once = all(v == 1 for v in keys.values()) and {r for _, r in keys} == set(ROUNDS)
    print(f"M2 every (case, round) once, rounds {sorted({r for _, r in keys})}: {each_once}")
    m2.append(each_once)
    split = Counter(c.get("outcome") for c in cases)
    print(f"M2 split: {dict(split)} (expected {dict(SPLIT)}) -> {split == SPLIT}")
    m2.append(split == SPLIT)
    wrong = []
    for c in cases:
        got = (c.get("outcome"), c.get("stage"), c.get("keyPosted"))
        if c.get("outcome") != "refused":
            got = (c.get("outcome"), None, None)
        exp = expected_outcome(c["case"])
        if got != exp or c.get("pass") is not True or tuple(c.get("expected") or ()) != exp:
            wrong.append((c["case"], c["round"], got, exp, c.get("pass"),
                          [k for k, v in (c.get("clauses") or {}).items() if v is False], c.get("notEstablished")))
    passed = sum(c.get("pass") is True for c in cases)
    print(f"M2 pass {passed} of {len(cases)}; cases off the expected outcome or not passing: {len(wrong)}")
    for w in wrong:
        print("   ", w)
    m2.append(not wrong and passed == CASES_PER_REPORT)
    ne = [(c["case"], c["round"], c.get("notEstablished")) for c in cases if c.get("notEstablished")]
    print(f"M2 cases with notEstablished clauses: {ne if ne else 'none'}")
    m20 = {m.get("fixture"): (m.get("document") or {}).get("reducedBytesEqual") for m in shake.get("m2_0") or []}
    m20_ok = set(m20) == M2_0_FIXTURES and all(v is True for v in m20.values())
    print(f"M2-0 reducedBytesEqual: {m20} -> {m20_ok}")
    m2.append(m20_ok)
    cpass = sum(c.get("pass") is True for c in ctrl["cases"])
    cout = Counter(c.get("outcome") for c in ctrl["cases"])
    print(f"M2 control pass {cpass} of {len(ctrl['cases'])}, outcomes {dict(cout)}")
    m2.append(cpass == CASES_PER_REPORT and cout == Counter({"control": CASES_PER_REPORT}))

    # ---- M3 ------------------------------------------------------------------------------------
    m3 = []
    pair_ok = (pair_out.get("instrumented") == f"shakedown-{b}.json" and pair_out.get("control") == f"control-{b}.json"
               and pair_out.get("pairs") == CASES_PER_REPORT and pair_out.get("differ") == [])
    print(f"M3 pair: pairs={pair_out.get('pairs')} differ={len(pair_out.get('differ') or [])} -> {pair_ok}")
    m3.append(pair_ok)
    sides = {}
    for name in ("shakedown", "control"):
        docs = D / f"{name}-{b}.docs"
        files = sorted(docs.glob("*.odt")) if docs.is_dir() else []
        per_kind = {k: {f.name[: -len(f"-{k}.odt")] for f in files if f.name.endswith(f"-{k}.odt")} for k in KEPT}
        empty = [f.name for f in files if paragraphs(f) < 1]
        sides[name] = per_kind
        print(f"M3 kept on {name}: " + ", ".join(f"{k} {len(v)}" for k, v in per_kind.items())
              + f"; files with no paragraph or unreadable: {empty if empty else 'none'}")
        m3.append(all(len(per_kind[k]) == n for k, n in KEPT.items()) and not empty)
    same_sets = all(sides["shakedown"][k] == sides["control"][k] for k in KEPT)
    print(f"M3 the same (case, round) set kept on both sides for every kind: {same_sets}")
    m3.append(same_sets)

    # ---- M4 ------------------------------------------------------------------------------------
    m4 = []
    toast_clause_bad = []
    for name, r in (("shakedown", shake), ("control", ctrl)):
        for c in r["cases"]:
            cl = c.get("clauses") or {}
            for k in ("noToast", "onlyTheReopenToasts"):
                if k in cl and cl[k] is not True:
                    toast_clause_bad.append((name, c["case"], c["round"], k, cl[k]))
    print(f"M4 toast clauses (noToast / onlyTheReopenToasts) not true: {toast_clause_bad if toast_clause_bad else 'none'}")
    m4.append(not toast_clause_bad)
    counted = Counter()
    for name, r in (("shakedown", shake), ("control", ctrl)):
        for c in r["cases"]:
            cl = c.get("clauses") or {}
            counted[(name, "noToast" if "noToast" in cl else "onlyTheReopenToasts" if "onlyTheReopenToasts" in cl
                      else "neither")] += 1
    print(f"M4 cases per toast clause: {dict(counted)}")
    redraw = [name for name in (f"shakedown-{b}.json", f"control-{b}.json") if REDRAW_FAILED in (D / name).read_text()]
    print(f"M4 「{REDRAW_FAILED}」 anywhere in the reports: {redraw if redraw else 'no'}")
    m4.append(not redraw)

    verdicts[b] = {"M1": all(m1), "M2": all(m2), "M3": all(m3), "M4": all(m4)}
    print(f"\n{b}: " + "  ".join(f"{k}: {'HIT' if v else 'MISS'}" for k, v in verdicts[b].items()))

print("\nSUMMARY  " + "  ".join(f"{b} " + " ".join(f"{k}:{'HIT' if v else 'MISS'}" for k, v in vs.items())
                                for b, vs in verdicts.items())
      + (f"  NOT DONE: {not_done}" if not_done else ""))
if not_done:
    sys.exit(3)
sys.exit(0 if all(all(v.values()) for v in verdicts.values()) else 1)
