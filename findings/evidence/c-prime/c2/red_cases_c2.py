#!/usr/bin/env python3
"""Red cases for judge_c2.py (spec §17.5 "C2 的判讀工具"), re-runnable: each case's command is printed with
its output into red-cases.txt.  Reads committed reports only; writes nothing else.

The fifth ruling's four reports, two verdicts (three FAIL, one PASS -- the PASS is under overrides, so it must
say so since the codex review of 2026-10-11), and a P3 report under the counted binding (REFUSED: the page
constant is still the placeholder and the runner differs).  The review's case (a narrowed --slots printing
"PASS: both browsers, every cell") is the fourth: it passes under overrides, so it must now say so.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TL = HERE.parents[1] / "typing-latency"
JUDGE = HERE / "judge_c2.py"


def bound_to(path: Path) -> list[str]:
    r = json.loads(path.read_text())
    return ["--page", r["page"], "--runner", r["runner"]]


CASES = []
for name, browser, window, want in (("wide-base-chrome-owner-gap80.json", "chrome", "1400x1000", 1),
                                    ("wide-skip-firefox-owner-gap80.json", "firefox", "1400x1000", 1),
                                    ("dpr2-base-firefox-owner-gap80.json", "firefox", "none", 1),
                                    ("dpr2-skip-chrome-owner-gap80.json", "chrome", "none", 0)):
    path = TL / "r2-blit-bytes" / name
    CASES.append((f"{name} (window {window})", want,
                  ["--report", f"{browser}:owner-gap80={path}", "--browsers", browser, "--slots", "owner-gap80",
                   "--window", window, *bound_to(path)], "under OVERRIDE" if want == 0 else None))
p3 = TL / "p-release" / "p3-dpr2wide-firefox-owner-gap80.json"
CASES.append(("counted binding on a P3 report (REFUSED: page placeholder, runner differs)", 2,
              ["--report", f"firefox:owner-gap80={p3}", "--browsers", "firefox", "--slots", "owner-gap80"], None))

ok = True
for title, want, args, must in CASES:
    p = subprocess.run([sys.executable, str(JUDGE), *args], capture_output=True, text=True)
    good = p.returncode == want and (must is None or must in p.stdout) and "PASS: both browsers, every cell" not in (
        p.stdout if must else "")
    ok &= good
    print(f"## red case: {title}")
    print(f"$ judge_c2.py {' '.join(a if ' ' not in a else repr(a) for a in args)}")
    print(p.stdout.rstrip())
    print(f"exit {p.returncode} (wanted {want}{', and the words ' + repr(must) if must else ''}) -> {'as required' if good else 'NOT as required'}")
print("red cases:", "all as required" if ok else "NOT all as required")
sys.exit(0 if ok else 1)
