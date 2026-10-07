#!/usr/bin/env python3
"""Reader for the product-path net run in this directory (PREDICTION.md P1-P4).

Re-run:  python3 judge.py            (reads the 12 reports next to this file)
         python3 judge.py --dir DIR  (reads the reports in another directory; used for the red-case self-test)

It reads only the *.json reports (and chain.log for exit codes). It writes nothing.
Per-check outcomes live in report["checks"][i]["outcome"] (PASS / FAIL / NOT_ESTABLISHED), id in ["id"].
If a report does not have exactly 42 checks, or the id lists differ between reports, it says so and stops.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=str(Path(__file__).resolve().parent))
args = ap.parse_args()
D = Path(args.dir)

# ---- values from PREDICTION.md (committed 8e43c087) -----------------------------------------
V8_ENTRY = "e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f"
V16_PAGE = "b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d"
V16_BEFORE_REPOINT = "a3fd9ac1d057eea22fa1af0d359d1760b5f211dead6af1db8ac010cc473aa7bc"
EXPECT_CHECKS = 42
ORDER = [(b, p, n) for b in ("chrome", "firefox") for n in (1, 2, 3) for p in ("v8", "v16")]
PROFILES = ("v8", "v16")
BROWSERS = ("chrome", "firefox")

rep = {}
missing = []
for b, p, n in ORDER:
    f = D / f"e2-editor-{p}-{b}-r{n}.json"
    if not f.is_file() or f.stat().st_size == 0:
        missing.append(f.name)
        continue
    rep[(b, p, n)] = json.loads(f.read_text())
if missing:
    print("MISSING REPORTS:", missing)
    sys.exit(3)


def short(s, k=16):
    return (s or "None")[:k]


# ---- chain.log exit codes ---------------------------------------------------------------------
exitcode = {}
runner_lines = []
log = D / "chain.log"
if log.is_file():
    for line in log.read_text().splitlines():
        m = re.match(r"(\S+ \S+ \S+) END\s+(v8|v16) (chrome|firefox) r(\d) exit=(\d+) report_exists=(\w+)", line)
        if m:
            exitcode[(m.group(3), m.group(2), int(m.group(4)))] = int(m.group(5))
        if "CHAIN START" in line or "CHAIN DONE" in line:
            runner_lines.append(line)
        if "WAIT" in line or "ABORT" in line:
            runner_lines.append(line)

# ---- 42 checks per report -----------------------------------------------------------------------
ids0 = None
for key, r in rep.items():
    ids = [c["id"] for c in r["checks"]]
    if len(ids) != EXPECT_CHECKS:
        print(f"STOP: {key} has {len(ids)} checks, expected {EXPECT_CHECKS}. Not adjusting the reader.")
        sys.exit(4)
    if len(set(ids)) != len(ids):
        print(f"STOP: {key} has duplicate check ids. Not adjusting the reader.")
        sys.exit(4)
    if ids0 is None:
        ids0 = ids
    elif ids != ids0:
        print(f"STOP: check id list of {key} differs from the first report. Not adjusting the reader.")
        sys.exit(4)
print(f"All {len(rep)} reports carry exactly {EXPECT_CHECKS} checks with the same ids in the same order.")
other = {c["outcome"] for r in rep.values() for c in r["checks"]} - {"PASS", "FAIL", "NOT_ESTABLISHED"}
if other:
    print("NOTE: outcomes other than PASS/FAIL/NOT_ESTABLISHED present:", other)

# ---- P1 -----------------------------------------------------------------------------------------
print("\n## P1  complete / liveness.lastState / pageErrors\n")
print("| report | started | completed | PASS | FAIL | NE | ok | complete | lastState | pageErrors | exit |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
p1_ok = True
for key in ORDER:
    b, p, n = key
    r = rep[key]
    cnt = {"PASS": 0, "FAIL": 0, "NOT_ESTABLISHED": 0}
    for c in r["checks"]:
        cnt[c["outcome"]] = cnt.get(c["outcome"], 0) + 1
    good = (r.get("complete") is True and (r.get("liveness") or {}).get("lastState") == "ready" and r.get("pageErrors") is None)
    p1_ok &= good
    print(f"| `e2-editor-{p}-{b}-r{n}.json` | {r.get('startedAt','')[11:19]} | {r.get('completedAt','')[11:19]} | "
          f"{cnt['PASS']} | {cnt['FAIL']} | {cnt['NOT_ESTABLISHED']} | {r.get('ok')} | {r.get('complete')} | "
          f"{(r.get('liveness') or {}).get('lastState')} | {r.get('pageErrors')} | {exitcode.get(key, '?')} |")
print(f"\nP1 per-report condition (complete is True, lastState == 'ready', pageErrors is None) holds in "
      f"{sum(1 for k in ORDER if rep[k].get('complete') is True and (rep[k].get('liveness') or {}).get('lastState') == 'ready' and rep[k].get('pageErrors') is None)} of {len(ORDER)} reports.")
print("P1:", "HIT" if p1_ok else "MISS")

# ---- P2 -----------------------------------------------------------------------------------------
print("\n## P2  served page / candidate fields\n")
print("| report | servedShell.entrypointSha256 | candidateSource.page | sha256BeforeRepoint | distPageWasTheSame | restOfShellEqualsSource | candidateCutover.pageSha256 | profile | pinBefore | pinAfter |")
print("|---|---|---|---|---|---|---|---|---|---|")
p2_ok = True
p2_notes = []
for key in ORDER:
    b, p, n = key
    r = rep[key]
    ss = r.get("servedShell") or {}
    ep = ss.get("entrypointSha256")
    cs = r.get("candidateSource")
    cc = r.get("candidateCutover")
    if p == "v8":
        good = ep == V8_ENTRY and cs is None and cc is None
        if ep != V8_ENTRY:
            p2_notes.append(f"{key}: entrypointSha256 {ep}")
        if cs is not None or cc is not None:
            p2_notes.append(f"{key}: v8 report carries candidateSource/candidateCutover")
        print(f"| `v8-{b}-r{n}` | `{ep}` | (no key) | | | | (no key) | | | |")
    else:
        cs = cs or {}
        cc = cc or {}
        good = (cs.get("page") == "web/e2-editor-app.js"
                and cs.get("sha256BeforeRepoint") == V16_BEFORE_REPOINT
                and cs.get("distPageWasTheSame") is False
                and cs.get("restOfShellEqualsSource") is True
                and ep == cc.get("pageSha256") == V16_PAGE)
        print(f"| `v16-{b}-r{n}` | `{ep}` | `{cs.get('page')}` | `{cs.get('sha256BeforeRepoint')}` | {cs.get('distPageWasTheSame')} | "
              f"{cs.get('restOfShellEqualsSource')} | `{cc.get('pageSha256')}` | {cc.get('profile')} | `{cc.get('pinBefore')}` | `{cc.get('pinAfter')}` |")
        if not good:
            p2_notes.append(f"{key}: v16 fields differ from PREDICTION")
    p2_ok &= good
print(f"\nExpected v8 entrypointSha256        = {V8_ENTRY}")
print(f"Expected v16 page / entrypoint      = {V16_PAGE}")
print(f"Expected v16 sha256BeforeRepoint    = {V16_BEFORE_REPOINT}")
for pr in PROFILES:
    shells = {(rep[(b, pr, n)]["servedShell"]["bundle"], rep[(b, pr, n)]["servedShell"]["declaredSha256"][:16],
               rep[(b, pr, n)]["servedShell"]["servedSha256"][:16],
               tuple(rep[(b, pr, n)]["servedShell"]["differingPaths"]),
               rep[(b, pr, n)]["servedShell"]["differsOnlyInTheEntrypoint"],
               tuple(rep[(b, pr, n)]["servedShell"]["missing"]))
              for b in BROWSERS for n in (1, 2, 3)}
    print(f"servedShell (bundle, declared[:16], served[:16], differingPaths, differsOnlyInTheEntrypoint, missing) distinct values for {pr}: {len(shells)}")
    for s in sorted(shells, key=str):
        print("   ", s)
if p2_notes:
    print("P2 notes:", *p2_notes, sep="\n  ")
print("P2:", "HIT" if p2_ok else "MISS")

# ---- P3 -----------------------------------------------------------------------------------------
def counts(b, p, i):
    c = {"PASS": 0, "FAIL": 0, "NOT_ESTABLISHED": 0}
    for n in (1, 2, 3):
        o = rep[(b, p, n)]["checks"][i]["outcome"]
        c[o] = c.get(o, 0) + 1
    return c


def fmt(c):
    parts = [f"{c[k]} {lab}" for k, lab in (("PASS", "PASS"), ("FAIL", "FAIL"), ("NOT_ESTABLISHED", "NE")) if c.get(k)]
    return ", ".join(parts)


def verdict(c8, c16):
    """spec section 23, verbatim from the task statement."""
    if c8["FAIL"] > 0:
        return c16["FAIL"] <= c8["FAIL"]
    if c8["NOT_ESTABLISHED"] > 0:
        return c16["FAIL"] == 0
    return c16["PASS"] == 3


print("\n## P3  every check, 3 rounds per arm (NE = NOT_ESTABLISHED), spec section 23 verdict per cell\n")
print("| check id | chrome v8 | chrome v16 | chrome | firefox v8 | firefox v16 | firefox |")
print("|---|---|---|---|---|---|---|")
red = []
diff = []
for i, cid in enumerate(ids0):
    row = [f"`{cid}`"]
    for b in BROWSERS:
        c8, c16 = counts(b, "v8", i), counts(b, "v16", i)
        okc = verdict(c8, c16)
        if not okc:
            red.append((b, cid, fmt(c8), fmt(c16)))
        if c8 != c16:
            diff.append((b, cid, fmt(c8), fmt(c16)))
        row += [fmt(c8), fmt(c16), "ok" if okc else "**RED**"]
    print("| " + " | ".join(row) + " |")
print(f"\nCells judged: {EXPECT_CHECKS * len(BROWSERS)}.  Section-23 red cells: {len(red)}")
for r_ in red:
    print("  RED:", r_)
p3_ok = not red
print("P3:", "HIT" if p3_ok else "MISS")

# ---- P4 -----------------------------------------------------------------------------------------
print("\n## P4  count equality (descriptive)\n")
n_cells = EXPECT_CHECKS * len(BROWSERS)
print(f"Cells with equal v8/v16 counts: {n_cells - len(diff)} of {n_cells}.  Cells that differ: {len(diff)}")
for d_ in diff:
    print("  DIFF:", d_)
CF = "clear-format-removes-every-inline-format"
IF = "an-inline-format-reaches-a-selection"
only_cf_firefox = all(d_[0] == "firefox" and d_[1] == CF for d_ in diff)
i_if = ids0.index(IF)
if_fail = {(b, p): counts(b, p, i_if)["FAIL"] for b in BROWSERS for p in PROFILES}
print(f"Firefox {IF}: FAIL rounds v8={if_fail[('firefox','v8')]} v16={if_fail[('firefox','v16')]} (Chrome v8={if_fail[('chrome','v8')]} v16={if_fail[('chrome','v16')]})")
if_ok = if_fail[("firefox", "v8")] > 0 and if_fail[("firefox", "v16")] > 0
p4_ok = (n_cells - len(diff) >= 83) and only_cf_firefox and if_ok
print("\nFirefox clear-format-removes-every-inline-format, per round (observed.allOnWhenTyped bold / italic / underline / strikethrough; everyFormatWasOn):\n")
print("| arm | round | outcome | allOnWhenTyped | everyFormatWasOn |")
print("|---|---|---|---|---|")
i_cf = ids0.index(CF)
for p in PROFILES:
    for n in (1, 2, 3):
        c = rep[("firefox", p, n)]["checks"][i_cf]
        o = c.get("observed") or {}
        a = o.get("allOnWhenTyped") or {}
        print(f"| {p} | r{n} | {c['outcome']} | {a.get('bold')} / {a.get('italic')} / {a.get('underline')} / {a.get('strikethrough')} | {o.get('everyFormatWasOn')} |")
print("\nChrome clear-format, for reference:")
for p in PROFILES:
    print("  ", p, [rep[("chrome", p, n)]["checks"][i_cf]["outcome"] for n in (1, 2, 3)])
print("P4:", "HIT" if p4_ok else "MISS",
      f"(>=83 of 84 equal: {n_cells - len(diff) >= 83}; any differing cell is Firefox {CF}: {only_cf_firefox}; Firefox {IF} FAILs on both profiles: {if_ok})")

print("\n## chain.log lines of interest\n")
for l in runner_lines:
    print(l[:200])
print("\nSUMMARY  P1:", "HIT" if p1_ok else "MISS", " P2:", "HIT" if p2_ok else "MISS",
      " P3:", "HIT" if p3_ok else "MISS", f"(red cells {len(red)})", " P4:", "HIT" if p4_ok else "MISS", f"(differing cells {len(diff)})")
