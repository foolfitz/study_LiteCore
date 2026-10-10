#!/usr/bin/env python3
"""Red cases for compare.py (spec §17.5 C5), on scratch copies of committed reports.  Writes nothing in the tree."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
EV = HERE.parents[1]
PP11 = EV / "release-0.2.11/product-path"
SCRATCH = Path(tempfile.mkdtemp(prefix="c5-red-"))

def copy_set(name):
    d = SCRATCH / name / "product-path"; d.mkdir(parents=True)
    for f in PP11.glob("e2-editor-v*-r?.json"):
        shutil.copy(f, d / f.name)
    return d

def edit(d, arm, browser, n, check, outcome):
    f = d / f"e2-editor-{arm}-{browser}-r{n}.json"; j = json.loads(f.read_text())
    c = next(c for c in j["checks"] if c["id"] == check); c["outcome"] = outcome; f.write_text(json.dumps(j))

def run(*args):
    p = subprocess.run([sys.executable, str(HERE / "compare.py"), *map(str, args)], capture_output=True, text=True)
    lines = [l for l in p.stdout.splitlines() if l.startswith(("SUMMARY", "  DIFF", "REFUSED"))]
    return p.returncode, lines

cases = []
d = copy_set("same"); cases.append(("the 0.2.11 set against itself -> 0", (0,), run("--product-path", PP11, d)))
d = copy_set("flip"); edit(d, "v19", "chrome", 2, "product-save-button-writes-a-real-odt", "FAIL")
cases.append(("chrome v19 r2 product-save-button... PASS->FAIL -> 1 (forward)", (1,), run("--product-path", PP11, d)))
d = copy_set("fixed"); [edit(d, "v19", "firefox", n, "an-inline-format-reaches-a-selection", "PASS") for n in (1, 2, 3)]
cases.append(("firefox v19 an-inline-format... FFF->PPP -> 1 (reverse: a port that turns a red check green)", (1,), run("--product-path", PP11, d)))
d = copy_set("noise"); edit(d, "v19", "firefox", 1, "clear-format-removes-every-inline-format", "PASS")
cases.append(("firefox v19 clear-format NNN->PNN, a noise cell -> 0", (0,), run("--product-path", PP11, d)))
d = copy_set("missing"); (d / "e2-editor-v8-firefox-r3.json").unlink()
cases.append(("one report missing -> REFUSED", (2,), run("--product-path", PP11, d)))
locks = sorted((EV / "m3-locks/runs").glob("2026-10-10T04*.json"))[-1]
cases.append(("locks counted report against itself -> 0", (0,), run("--m3", "locks", locks, locks)))
j = json.loads(locks.read_text()); first = next(iter(j["score"]["tally"])); j["score"]["tally"][first]["pass"] -= 1
bad = SCRATCH / "locks-one-fewer.json"; bad.write_text(json.dumps(j))
cases.append((f"locks {first} one pass fewer -> 1", (1,), run("--m3", "locks", locks, bad)))
j = json.loads(locks.read_text()); j["score"]["verdict"] = "LOCKS DO NOT LAND"
bad2 = SCRATCH / "locks-verdict.json"; bad2.write_text(json.dumps(j))
cases.append(("locks verdict changed -> 1", (1,), run("--m3", "locks", locks, bad2)))
he = sorted((EV / "m3-host-entry/runs").glob("2026-10-10T05*.json"))[-1]
j = json.loads(he.read_text()); j["score"]["browsers"]["firefox"]["conflict"]["passed"] = 2
bad3 = SCRATCH / "he.json"; bad3.write_text(json.dumps(j))
cases.append(("host entry firefox conflict 3/3 -> 2/3 (passed/of shape) -> 1", (1,), run("--m3", "host_entry", he, bad3)))
pu = EV / "m3-production-ui/runs-0.2.11/counted-KR-x3.json"
j = json.loads(pu.read_text()); j["score"]["cells"]["Kbs/firefox"]["pass"] = 2
bad4 = SCRATCH / "pu.json"; bad4.write_text(json.dumps(j))
cases.append(("production UI Kbs/firefox 3/3 -> 2/3 -> 1", (1,), run("--m3", "production_ui", pu, bad4)))
ok = True
for name, want, (code, lines) in cases:
    good = code in want and (code != 1 or sum(1 for l in lines if l.startswith("  DIFF")) == 1)
    ok &= good
    print(f"{'red ' if good else 'MISS'}  {name}: exit {code}")
    for l in lines: print("        " + l[:200])
print("red cases:", "all as required" if ok else "NOT all as required")
sys.exit(0 if ok else 1)
