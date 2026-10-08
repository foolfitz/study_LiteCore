#!/usr/bin/env python3
"""Reader for the owner's-document run (../PREDICTION.md O1-O3; spec 26.3 V5's clauses).

Re-run:  python3 -I judge.py                          (v18: v5/shakedown-chrome-v18-v5.json)
         python3 -I judge.py --report R --private-docs DIR --profile P --page SHA   (selftest.sh, on v17's run)

Reads the report, and for O3 the owner's saved documents under wasm_sdk_probe/build/ (never in the repository).
Prints case ids, numbers, tags, style names and text LENGTHS, never paragraph text.  Writes nothing.
Exit 0 = preconditions, O1 and O2 HIT; 1 = a MISS; 3 = the report is missing or unreadable (not done).
O3 is descriptive and does not change the exit code.

Written 2026-10-08 while the chain was still in its Firefox merge step, before this run existed; the expected
values are copied from ../PREDICTION.md (committed 15eca506) and v17's RESULT.md, not from any v18 report.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROBE = ROOT / "wasm_sdk_probe"
sys.path.insert(0, str(PROBE / "tools"))
from run_merge_wasm_shakedown import reduce_content  # noqa: E402  (spec 24's reduction, the runner's own)

ap = argparse.ArgumentParser()
ap.add_argument("--report", default=str(Path(__file__).resolve().parent / "shakedown-chrome-v18-v5.json"))
ap.add_argument("--private-docs", default=str(PROBE / "build/merge-wasm-private/shakedown-chrome-v18-v5.docs"))
ap.add_argument("--profile", default="e2-editor-v18")
ap.add_argument("--page", default="cfc8ba1d54dc4bef52baebc34f9d5f60ffe9cc4af9bee8c7a326bb02b2221cda")
ap.add_argument("--v17-docs", default=str(PROBE / "build/merge-wasm-private/shakedown-chrome-v5.docs"),
                help="v17's saves, for the descriptive v17-vs-this comparison of E02 (O3)")
args = ap.parse_args()

# ---- PREDICTION.md O1-O2 --------------------------------------------------------------------------
NATIVE_HEIGHT = {"E01": 348, "E02": 521, "E05": 521, "E10": 348, "T01": 463,
                 "E12": 348, "P27": 348, "E13": 348, "E15": 348, "P62": 348, "P63": 348}
SYNTHETIC = 26
M2_0_FIXTURES = {"boundaries", "boundaries-indent", "pmpc"}
# The CJK strings v17's report carried in its owner-document rows, all of them the page's own UI words
# (v17/v5/RESULT.md, checked there).  A string outside this set is not presumed to be paragraph text, but the
# no-text precondition is not met until someone has looked at it.
UI_WORDS = {"儲存", "刪除", "前刪", "定位游標", "就緒", "已存出", "已開啟", "無"}
NATIVE = PROBE / "build/merge-native-pmpc/r0c/round-20261006T150756Z/docs"
BREAK = "<text:soft-page-break/>"
TOKEN = re.compile(rb"(<[^>]+>)|([^<]+)")
REDACT = re.compile(rb'(text:string-value|office:string-value|xlink:title|xlink:href|text:name|draw:name)="[^"]*"')
CJK = re.compile(r"[㐀-鿿豈-﫿]+")

try:
    r = json.loads(Path(args.report).read_text())
except (OSError, ValueError) as e:
    print(f"NOT DONE: {e}")
    sys.exit(3)

ok = {}
# ---- preconditions ----------------------------------------------------------------------------------
cand = r.get("candidate") or {}
owner = [c for c in r.get("cases", []) if c.get("fixture") == "pmpc"]
synth = [c for c in r.get("cases", []) if c.get("fixture") != "pmpc"]
strings = set()
for c in owner:
    strings |= set(CJK.findall(json.dumps(c, ensure_ascii=False)))
pre = {"profile": cand.get("profile") == args.profile, "page": cand.get("pageSha256") == args.page,
       "restOfShellEqualsSource": r.get("restOfShellEqualsSource") is True,
       "bootReady": (r.get("boot") or {}).get("state") == "ready", "ownerDocument": r.get("ownerDocument") is True,
       "completedAt": bool(r.get("completedAt")), "no runner-error": not any(c.get("outcome") == "runner-error"
                                                                              for c in r.get("cases", [])),
       "11 owner rows": sorted(c["case"] for c in owner) == sorted(NATIVE_HEIGHT),
       "search null in owner rows": all(c.get("search") is None for c in owner),
       "owner-row CJK strings within v17's UI words": strings <= UI_WORDS}
print(f"precondition: profile={cand.get('profile')} page={str(cand.get('pageSha256'))[:16]} "
      f"worker={str(cand.get('workerSha256'))[:16]} pinAfter={cand.get('pinAfter')} boot={(r.get('boot') or {}).get('state')} "
      f"started={r.get('startedAt')} completed={r.get('completedAt')} cases={len(r.get('cases', []))}")
print(f"precondition: owner-row CJK strings {sorted(strings)}; outside v17's UI words: {sorted(strings - UI_WORDS) or 'none'}")
for k, v in pre.items():
    print(f"   {k}: {v}")
ok["pre"] = all(pre.values())

# ---- O1 -----------------------------------------------------------------------------------------------
print("\n| case | native h | engine h | engine x,y = native | keyed | outcome | pass | false clauses | key ms |")
print("|---|---|---|---|---|---|---|---|---|")
o1 = True
for c in sorted(owner, key=lambda c: list(NATIVE_HEIGHT).index(c["case"]) if c["case"] in NATIVE_HEIGHT else 99):
    pl = c.get("place") or {}
    eng, nat = pl.get("engineCaret") or [None] * 4, pl.get("nativeCaret") or [None] * 4
    want = NATIVE_HEIGHT.get(c["case"])
    xy = eng[:2] == nat[:2] and None not in eng[:2]
    row_ok = (nat[3] == want and eng[3] == want and xy and pl.get("keyed") is False and pl.get("ok") is True
              and c.get("outcome") != "placement-mismatch")
    o1 &= row_ok
    false = [k for k, v in (c.get("clauses") or {}).items() if v is False]
    print(f"| {c['case']} | {nat[3]} | {eng[3]} | {xy} | {pl.get('keyed')} | {c.get('outcome')} | {c.get('pass')} "
          f"| {', '.join(false) or '-'} | {c.get('keyToResponseMs')} |" + ("" if row_ok else "  <- not as predicted"))
ok["O1"] = o1 and pre["11 owner rows"]
print(f"O1: {'HIT' if ok['O1'] else 'MISS'}")

# ---- O2 -----------------------------------------------------------------------------------------------
sp = sum(c.get("pass") is True for c in synth)
m20 = {m.get("fixture"): (m.get("document") or {}).get("reducedBytesEqual") for m in r.get("m2_0") or []}
print(f"\nO2 synthetic: {sp} of {len(synth)} pass (expected {SYNTHETIC} of {SYNTHETIC}); "
      f"not passing: {[(c['case'], c.get('outcome')) for c in synth if c.get('pass') is not True] or 'none'}")
print(f"O2 M2-0 reducedBytesEqual: {m20}")
ok["O2"] = (sp == SYNTHETIC and len(synth) == SYNTHETIC and set(m20) == M2_0_FIXTURES
            and all(v is True for v in m20.values()))
print(f"O2: {'HIT' if ok['O2'] else 'MISS'}")

# ---- O3 (descriptive) ------------------------------------------------------------------------------
print("\nO3 (descriptive, finding 115)")
e02 = next((c for c in owner if c["case"] == "E02"), {})
print(f"   E02 false clauses: {[k for k, v in (e02.get('clauses') or {}).items() if v is False]}; "
      f"afterKeyDocument textEqual={(e02.get('afterKeyDocument') or {}).get('textEqual')} "
      f"reducedBytesEqual={(e02.get('afterKeyDocument') or {}).get('reducedBytesEqual')}")


def tokens(path, reduced):
    raw = zipfile.ZipFile(path).read("content.xml")
    if reduced:
        raw = reduce_content(raw)
    return [REDACT.sub(rb'\1="<R>"', tag).decode()[:60] if tag else f"T({len(text.decode())})"
            for tag, text in TOKEN.findall(raw)]


def breaks(path):
    t = tokens(path, reduced=False)
    return [" | ".join(t[max(0, i - 3):i + 4]) for i, x in enumerate(t) if x == BREAK]


P = Path(args.private_docs)
V17 = Path(args.v17_docs)
for label, a, b in (("E02 after-key vs native key arm r1", P / "E02-r1-after-key.odt", NATIVE / "r1-E02-key.odt"),
                    ("E01 after-key vs native key arm r1", P / "E01-r1-after-key.odt", NATIVE / "r1-E01-key.odt"),
                    ("no-edit save vs native original", P / "m2-0-pmpc.odt", NATIVE / "original.odt"),
                    ("E02 after-key vs v17's E02 after-key", P / "E02-r1-after-key.odt", V17 / "E02-r1-after-key.odt")):
    if not (a.is_file() and b.is_file()):
        print(f"   {label}: not read ({'missing ' + a.name if not a.is_file() else 'missing ' + str(b)})")
        continue
    ba, bb = breaks(a), breaks(b)
    differ = [i + 1 for i, (x, y) in enumerate(zip(ba, bb)) if x != y]
    same_reduced = tokens(a, True) == tokens(b, True)
    print(f"   {label}: {len(ba)} vs {len(bb)} soft page breaks; differing by context (1-based): {differ}; "
          f"reduced content.xml token-equal: {same_reduced}")

print(f"\nSUMMARY  pre: {'HIT' if ok['pre'] else 'MISS'}  O1: {'HIT' if ok['O1'] else 'MISS'}  "
      f"O2: {'HIT' if ok['O2'] else 'MISS'}  O3: descriptive")
sys.exit(0 if all(ok.values()) else 1)
