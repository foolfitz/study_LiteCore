import copy, json, subprocess, sys
from pathlib import Path
EV = Path("/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/typing-latency")
S = Path(sys.argv[1])
PAGE = "18c8afbe29e8a5472a7a5eb0fdfae8f94a3e7a95147972c83e192fc69ebeef1a"
def load(n): return json.loads((EV / "p-release" / n).read_text())
def letters(r): return [k for k in r["raw"]["r2"]["keys"] if len(k[0]) == 1]
def repair_p1(r):
    r = copy.deepcopy(r); start = letters(r)[0][2]["staleBytes"]; n = 0
    for k in r["raw"]["r2"]["keys"]:
        if len(k[0]) == 1: k[2]["staleBytes"] = start + 400 * n; n += 1
    r["raw"]["r2"]["final"]["staleBytes"] = start + 400 * n; return r
def repair_123b(r):
    r = copy.deepcopy(r); raw = r["raw"]
    raw["r2"]["toasts"] = [t for t in raw["r2"]["toasts"] if "TILE_NOT_PAINTED" not in t[1]]
    lk = [t for k, t in raw["keys"] if len(k) == 1][-1]
    raw["blits"].append([round(lk + 700.0, 1), 35805, 1042, int(r["startRevision"]) + r["chars"]])
    r["allCurrentAfterLastKeyMs"] = 700.0; return r
base = {}
for b in ("chrome", "firefox"):
    base[(b, "p1")] = repair_p1(load(f"shipped-{b}-p1.json"))
    base[(b, "123b")] = repair_123b(load(f"shipped-{b}-123b.json"))
def run(name, change, use_base=True):
    reps = copy.deepcopy(base) if use_base else {(b, s): load(f"shipped-{b}-{s}.json") for b in ("chrome","firefox") for s in ("p1","123b")}
    change(reps)
    d = S / name; d.mkdir(parents=True, exist_ok=True)
    for (b, s), r in reps.items(): (d / f"m-{b}-{s}.json").write_text(json.dumps(r))
    out = subprocess.run([sys.executable, str(EV / "judge_p.py"), "--page", PAGE, "--dir", str(d), "--prefix", "m"], capture_output=True, text=True)
    lines = [l for l in out.stdout.splitlines() if ("FAIL" in l or "REFUSED" in l or l.startswith("PASS")) and "RECORD" not in l]
    print(f"=== {name}: exit {out.returncode}"); [print("   ", l[:230]) for l in lines]
# M1: Firefox 123b report from the 800-wide run (real, unchanged) -> window binding
def m1(r): r[("firefox","123b")] = load("shipped-firefox-123b-window800.json")
run("M1-ff-window800-real", m1, use_base=False)
# M2: drift: same real 800-wide content (canvas 1496x36996) but window recorded as 797 -> what an honest run gives if 797 stops yielding 745 css px
def m2(r):
    x = load("shipped-firefox-123b-window800.json"); x["windowRequested"] = [797, 1000]; r[("firefox","123b")] = x
run("M2-ff-drift-unfixed-page", m2, use_base=False)
# M3: 123b raw.keys missing one letter (gated cell with no red case)
def m3(r):
    k = r[("chrome","123b")]["raw"]["keys"]; del k[[i for i, (n, _) in enumerate(k) if len(n) == 1][1]]
run("M3-123b-key-missing", m3)
# M4: raw.dpr as float 2.0 / 1.0
def m4(r): r[("chrome","123b")]["raw"]["dpr"] = 2.0; r[("chrome","p1")]["raw"]["dpr"] = 1.0
run("M4-dpr-float", m4)
# M4b: raw.dpr 1.25 on p1 (host scaling) -> REFUSED
def m4b(r): r[("firefox","p1")]["raw"]["dpr"] = 1.25
run("M4b-dpr-1.25", m4b)
# M5: whole-band re-blit every key classified fresh (save-under / re-wrapped ImageData) -> reader cannot see it
def m5(r):
    x = r[("chrome","p1")]; band = 725 * 1023 * 4; n = 0
    for k in x["raw"]["r2"]["keys"]:
        if len(k[0]) == 1: k[2]["freshBytes"] += band * 6 * n; k[2]["freshCalls"] += 6 * n; n += 1
    x["raw"]["r2"]["final"]["freshBytes"] += band * 6 * n; x["raw"]["r2"]["final"]["freshCalls"] += 6 * n
run("M5-whole-band-as-fresh", m5)
# M6: boundary exactly 2 % (pass) and 2 % + 4 bytes (fail) on chrome p1 key 4
def bump(r, extra):
    x = r[("chrome","p1")]; c = 725 * 17929 * 4; ks = letters(x); add = int(c * 0.02) - 400 + extra
    for k in ks[5:]: k[2]["staleBytes"] += add
    x["raw"]["r2"]["final"]["staleBytes"] += add
run("M6a-exactly-2pct", lambda r: bump(r, 0))
run("M6b-2pct-plus-4", lambda r: bump(r, 4))
# M7: last key's window: stale bytes after the last key but before final -> counted
def m7(r):
    x = r[("firefox","p1")]; x["raw"]["r2"]["final"]["staleBytes"] += int(900*22257*4*0.03)
run("M7-last-key-window", m7)
