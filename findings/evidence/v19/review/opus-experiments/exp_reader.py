"""Adversarial experiments on judge_counted_m2.py, run against the scratch mirror (writes only to temp dirs)."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MIRROR = Path(__file__).resolve().parent / "mirror" / "wasm_sdk_probe"
sys.path.insert(0, str(MIRROR / "tools"))
sys.path.insert(0, str(MIRROR / "tests"))
import judge_counted_m2 as j  # noqa: E402
import run_merge_wasm_shakedown as m  # noqa: E402
import test_judge_counted_m2 as t  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="opus-review-"))
green = tmp / "green"
green.mkdir()
for b in j.BROWSERS:
    t.build(green, b)


def fresh(name):
    d = tmp / name
    shutil.copytree(green, d)
    return d


def edit(d, stem, change):
    p = d / f"{stem}.json"
    r = json.loads(p.read_text())
    change(r)
    p.write_text(json.dumps(r, ensure_ascii=False))


def show(label, d, browsers=j.BROWSERS, uncounted=False):
    code, lines = j.judge(d, t.PROFILE, list(browsers), uncounted)
    print(f"{label}: exit {code} | {lines[-1]}")
    return code, lines


print("m.BINDING =", m.BINDING)
show("E0 synthetic green, both browsers", green)

# E1: Firefox reports deleted entirely; reader asked for chrome only.
d = fresh("e1")
for p in d.glob("*firefox*"):
    shutil.rmtree(p) if p.is_dir() else p.unlink()
show("E1 no firefox report at all, --browsers chrome", d, ["chrome"])
show("E1b same dir, default browsers", d)
# and through the CLI the way the runbook would invoke it
cli = subprocess.run([sys.executable, "-B", str(MIRROR / "tools/judge_counted_m2.py"), "--dir", str(d),
                      "--profile", t.PROFILE, "--browsers", "chrome"], capture_output=True, text=True)
print("E1c CLI --browsers chrome: exit", cli.returncode, "|", cli.stdout.strip().splitlines()[-1])

# E2: every report carries a binding that is not the committed one (m.BINDING is None), and a runner hash
# that is not the runner file's; bound == binding throughout.
d = fresh("e2")
other = {k: "0" * 64 for k in t.BINDING}
other_red = {**other, "wasmSha256": "8" * 64, "workerSha256": "9" * 64, "pageSha256": "a" * 64}
for stem in [p.stem for p in d.glob("*.json")]:
    def change(r, stem=stem):
        r["binding"] = other
        r["bound"] = other_red if stem.startswith("red-") else other
        r["runner"] = "not-the-runner00"
        r["candidate"]["pageSha256"] = (other_red if stem.startswith("red-") else other)["pageSha256"]
    edit(d, stem, change)
print("runner file sha16:", __import__("hashlib").sha256((MIRROR / "tools/run_merge_wasm_shakedown.py").read_bytes()).hexdigest()[:16])
show("E2 binding != committed BINDING, runner hash != runner file", d)

# E3: an M2-3 record whose session was reopened TWICE (generation 1 -> 3 after the window closed).
d = fresh("e3")
def twice(r):
    rec = next(c for c in r["cases"] if c["case"] == "C29" and c["round"] == 2)
    rec["generation"] = [rec["generation"][0], str(int(rec["generation"][0]) + 2)]
edit(d, "counted-chrome", twice)
code, lines = show("E3 C29 r2 reopened twice (generation +2 after the window), chrome", d, ["chrome"])

# E5: a negative runner latency (a response taken from before the key) on one M2-1 record and one M2-4 press.
d = fresh("e5")
edit(d, "counted-chrome", lambda r: next(c for c in r["cases"] if c["case"] == "C01" and c["round"] == 1)
     .update(keyToResponseMs=-250.0))
edit(d, "m2-4-chrome", lambda r: r["cases"][0]["presses"][10].update(keyToResponseMs=-3.0))
show("E5 negative runner latency on C01 r1 and M2-4 press 11", d, ["chrome"])

# E6: what the green contains in the way of stderr files
print("E6 stderr files in green:", sorted(p.name for p in green.glob("*.stderr.txt")))
print("tmp:", tmp)
