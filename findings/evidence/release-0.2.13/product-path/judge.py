#!/usr/bin/env python3
"""Reader for the product-path net of the 0.2.13 release (autosave, findings 127-130; SPEC-M3-autosave §9.4 「計數」).
Copied from ../../release-0.2.12/product-path/judge.py 2026-10-12; changed: the two page constants below and this
paragraph, nothing else (every hard-coded expectation re-read, rule ee: 42 checks, roles, row 1' stand as in 0.2.12;
the product-path runner serves dist/ without a host, so the page's autosave -- host only, §9.2 -- never runs in it).
0.2.12's note follows (its constants then read 8909564e... and 0660beaf...); this copy's read c7f904fa... and
2609266a... (the v8 repoint computed with the runner's own repointed_page(); the same call on 0.2.12's page gives
0660beaf..., checked 2026-10-12).  Re-bound 2026-10-12 after finding 131's rule A (SPEC-M3-autosave §9.19), the
two constants only: d761f1ce... and fac708d0... (same call; on c7f904fa... it still gives 2609266a..., re-checked).
(0.2.12's paragraph: copied from ../../release-0.2.11/product-path/judge.py; changed the two page constants only.)
(0.2.11's paragraph: copied from ../../release-0.2.10/product-path/judge.py; changed the two page constants only.)
(0.2.10's paragraph: copied from ../../release-0.2.9/product-path/judge.py; changed the two page constants only.)

Copied from ../../v19/x5-product-path/judge.py 2026-10-09.  Changed, every hard-coded expectation read (rule ee):
  * ROLES SWAPPED.  After the cutover dist/ serves the v19 page, so the v19 arm is the PLAIN run (dist as served,
    no candidate keys) and the v8 arm is the candidate (`--candidate-profile e2-editor-v8`: the new page source
    repointed to v8).  X5 had it the other way round.  P2 below checks each arm's provenance accordingly.
  * Constants: the new page 537d62d7... (web = dist, shell generation v58), the v8-repointed page 4d3f3bd6...
  * §36.2 row 1' implemented BEFORE the run (spec §36.2 condition 4) for `recovery-returns-what-the-product-promised`
    only (§36.4: not used to re-read other cells): when v8 passes every round here but the window -- git-tracked
    e2-editor-v8-<browser>-r*.json whose record carries observed.finding038Reproduced -- has an NE, the candidate
    is judged by row 3 (no FAIL).  The window is counted at read time and printed.
P1-P4 are ./PREDICTION.md's; the verdict is the SUMMARY line (spec 34.7), not the exit code.

Re-run:  python3 judge.py            (reads the 12 reports next to this file)
It reads only the *.json reports (and chain.log for exit codes). It writes nothing.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=str(Path(__file__).resolve().parent))
# Self-test only: read another directory's candidate arm under its own label and page.
ap.add_argument("--candidate", default="v19")
ap.add_argument("--candidate-page", default="d761f1cee9d26c50c0b152348d74c3d05f540e9228927815d93ad6ec161e7dcd")
args = ap.parse_args()
D = Path(args.dir)

# ---- values from this directory's PREDICTION.md (spec §17.22) ----------------------------------
CAND = args.candidate                  # "v19": the PLAIN arm, dist as served
CAND_PAGE = args.candidate_page        # d761f1ce...: the page dist serves (web = dist, shell v62); was c7f904fa...
V8_REPOINTED = "fac708d061d5da508e2aa9838b95112b85f9b1ca93459d64fbfcff8fab82cb42"   # the same source repointed to v8; was 2609266a...
BEFORE_REPOINT = CAND_PAGE             # the v8 arm's source before repointing is the page dist serves
EXPECT_CHECKS = 42
ORDER = [(b, p, n) for b in ("chrome", "firefox") for n in (1, 2, 3) for p in ("v8", CAND)]
PROFILES = ("v8", CAND)
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
        m = re.match(r"(\S+ \S+ \S+) END\s+(v8|" + CAND + r") (chrome|firefox) r(\d) exit=(\d+) report_exists=(\w+)", line)
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
        # Roles swapped (docstring): v8 is the candidate here.
        cs = cs or {}
        cc = cc or {}
        good = (cs.get("page") == "web/e2-editor-app.js"
                and cs.get("sha256BeforeRepoint") == BEFORE_REPOINT
                and cs.get("restOfShellEqualsSource") is True
                and ep == cc.get("pageSha256") == V8_REPOINTED
                and cc.get("profile") == "e2-editor-v8")
        print(f"| `v8-{b}-r{n}` | `{ep}` | `{cs.get('page')}` | `{cs.get('sha256BeforeRepoint')}` | {cs.get('distPageWasTheSame')} | "
              f"{cs.get('restOfShellEqualsSource')} | `{cc.get('pageSha256')}` | {cc.get('profile')} | `{cc.get('pinBefore')}` | `{cc.get('pinAfter')}` |")
        if not good:
            p2_notes.append(f"{key}: v8 (repointed) fields differ from PREDICTION")
    else:
        good = ep == CAND_PAGE and cs is None and cc is None
        if ep != CAND_PAGE:
            p2_notes.append(f"{key}: entrypointSha256 {ep}")
        if cs is not None or cc is not None:
            p2_notes.append(f"{key}: the plain {CAND} report carries candidateSource/candidateCutover")
        print(f"| `{CAND}-{b}-r{n}` | `{ep}` | (no key) | | | | (no key) | | | |")
    p2_ok &= good
print(f"\nExpected {CAND} (plain) entrypoint      = {CAND_PAGE}")
print(f"Expected v8 (repointed) page/entrypoint = {V8_REPOINTED}")
print(f"Expected v8 sha256BeforeRepoint         = {BEFORE_REPOINT}")
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


RECOVERY = "recovery-returns-what-the-product-promised"


def window_ne(browser):
    """§36.2's window for RECOVERY: git-tracked v8 reports whose record carries observed.finding038Reproduced."""
    import subprocess
    evidence = Path(__file__).resolve().parents[2]
    listed = subprocess.run(["git", "-C", str(evidence), "ls-files", "-z", "--", f"**/e2-editor-v8-{browser}-r*.json"],
                            capture_output=True, check=True).stdout.decode().split("\0")
    total = ne = 0
    for name in filter(None, listed):
        try:
            report = json.loads((evidence / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rec = next((c for c in report.get("checks") or [] if isinstance(c, dict) and c.get("id") == RECOVERY), None)
        if rec is None or "finding038Reproduced" not in (rec.get("observed") or {}):
            continue
        total += 1
        ne += rec.get("outcome") == "NOT_ESTABLISHED"
    return total, ne


WINDOW = {b: window_ne(b) for b in BROWSERS}


def verdict(c8, c16, cid=None, browser=None):
    """spec section 23, with §36.2's row 1' for RECOVERY."""
    if c8["FAIL"] > 0:
        return c16["FAIL"] <= c8["FAIL"]
    if c8["NOT_ESTABLISHED"] > 0:
        return c16["FAIL"] == 0
    if cid == RECOVERY and WINDOW[browser][1] > 0:
        return c16["FAIL"] == 0          # row 1' (second line): v8 passed here but abstained in the window
    return c16["PASS"] == 3


print("\n## P3  every check, 3 rounds per arm (NE = NOT_ESTABLISHED), spec section 23 verdict per cell\n")
print(f"| check id | chrome v8 | chrome {CAND} | chrome | firefox v8 | firefox {CAND} | firefox |")
print("|---|---|---|---|---|---|---|")
red = []
diff = []
for i, cid in enumerate(ids0):
    row = [f"`{cid}`"]
    for b in BROWSERS:
        c8, c16 = counts(b, "v8", i), counts(b, CAND, i)
        okc = verdict(c8, c16, cid, b)
        if not okc:
            red.append((b, cid, fmt(c8), fmt(c16)))
        if c8 != c16:
            diff.append((b, cid, fmt(c8), fmt(c16)))
        row += [fmt(c8), fmt(c16), "ok" if okc else "**RED**"]
    print("| " + " | ".join(row) + " |")
print(f"\nCells judged: {EXPECT_CHECKS * len(BROWSERS)}.  Section-23 red cells: {len(red)}")
print(f"Row 1' window for {RECOVERY} (v8 records with finding038Reproduced, NE among them): "
      + ", ".join(f"{b} {WINDOW[b][1]} of {WINDOW[b][0]}" for b in BROWSERS))
for r_ in red:
    print("  RED:", r_)
p3_ok = not red
print("P3:", "HIT" if p3_ok else "MISS")

# ---- P4 -----------------------------------------------------------------------------------------
print("\n## P4  count equality (descriptive)\n")
n_cells = EXPECT_CHECKS * len(BROWSERS)
print(f"Cells with equal v8/{CAND} counts: {n_cells - len(diff)} of {n_cells}.  Cells that differ: {len(diff)}")
for d_ in diff:
    print("  DIFF:", d_)
CF = "clear-format-removes-every-inline-format"
IF = "an-inline-format-reaches-a-selection"
i_if = ids0.index(IF)
if_fail = {(b, p): counts(b, p, i_if)["FAIL"] for b in BROWSERS for p in PROFILES}
print(f"Firefox {IF}: FAIL rounds v8={if_fail[('firefox','v8')]} {CAND}={if_fail[('firefox',CAND)]} "
      f"(Chrome v8={if_fail[('chrome','v8')]} {CAND}={if_fail[('chrome',CAND)]})")
# PREDICTION P4 is descriptive: differences are allowed only on zh-TW / default-Asian paragraphs whose
# Asian font the profile lacks; which fixtures those are is listed from the fixtures after the run.
# So this reader prints the differing cells and makes no HIT/MISS call on P4.
p4_ok = None
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
print("P4: descriptive (no HIT/MISS by this reader); differing cells listed above")

print("\n## chain.log lines of interest\n")
for l in runner_lines:
    print(l[:200])
print("\nSUMMARY  P1:", "HIT" if p1_ok else "MISS", " P2:", "HIT" if p2_ok else "MISS",
      " P3:", "HIT" if p3_ok else "MISS", f"(red cells {len(red)})", " P4: descriptive", f"(differing cells {len(diff)})")
