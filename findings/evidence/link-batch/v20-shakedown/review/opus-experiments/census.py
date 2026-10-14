#!/usr/bin/env python3
"""Q7 census: disable one rule at a time in a copy of the committed judge (and, separately, of the
runner's predicates) and see whether the committed red cases (--self-test and the unit tests) notice.
A rule whose removal leaves every red case green has no red case."""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "head" / "wasm_sdk_probe"
WORK = HERE / "census-work"

JUDGE = [  # (rule, exact old text, replacement)
    ("p1 runnerError -> NE", 'if result.get("runnerError"):\n        return NE, [f"runner error: {result[\'runnerError\']}"]\n    if not result.get("reply") or not positions:',
     'if False:\n        return NE, []\n    if not result.get("reply") or not positions:'),
    ("p1 no reply/no positions -> NE", 'if not result.get("reply") or not positions:', 'if not result.get("reply") and False:'),
    ("p1 expected None -> line", 'if p.get("expected") is None:\n            lines.append', 'if False:\n            lines.append'),
    ("p1 hidden -> line", 'elif p.get("hidden") is not False:', 'elif False:'),
    ("p1 text != expected -> line", 'elif p.get("text") != p.get("expected"):', 'elif False:'),
    ("p1 partsEqualsCount -> line", 'if result.get("partsEqualsCount") is not True:', 'if False:'),
    ("p2 no press -> NE", 'if not add or not add.get("presses"):', 'if not add:'),
    ("p2 remove missing -> line", 'if not part:\n            lines.append(f"{label}: not run")\n            continue',
     'if not part:\n            continue'),
    ("p2 hiddenAt2s -> line", 'if part.get("hiddenAt2s") is not False:', 'if False:'),
    ("p2 text M != expected -> line", 'if text_m != part.get("expectedM"):', 'if False:'),
    ("p2 count != expected -> line", 'if part.get("countAt2s") != part.get("expectedM"):', 'if False:'),
    ("p2 text M != count -> line", 'if text_m is not None and part.get("countAt2s") is not None and text_m != part.get("countAt2s"):', 'if False:'),
    ("p2 parts != expected -> line", 'if part.get("partsAt2s") not in (None, part.get("expectedM")):', 'if False:'),
    ("p3 nonVacuous -> NE", 'if not result.get("nonVacuous"):', 'if False:'),
    ("p3 untriggered -> line", 'if result.get("untriggeredRequests"):', 'if False:'),
    ("c1 nothing judged -> NE", 'if not judged:\n        return NE, [f"no round was judged', 'if False:\n        return NE, [f"no round was judged'),
    ("c1 clause not True -> line", 'for clause, held in r["clauses"].items():\n            if held is not True:', 'for clause, held in r["clauses"].items():\n            if False:'),
    ("c1 fewer than 6 judged -> line", 'if len(judged) < C1_REQUIRED_ROUNDS:', 'if False:'),
    ("e2 nothing judged -> NE", 'if not judged:\n        return NE, ["no refusal', 'if False:\n        return NE, ["no refusal'),
    ("e2 clause not True -> line", 'for clause, held in c["judge"]["clauses"].items():\n            if held is not True:', 'for clause, held in c["judge"]["clauses"].items():\n            if False:'),
    ("e2 the hold is judged", '+ ([hold] if "judge" in hold else [])', '+ []'),
    ("p2c no lok events -> NE (reading)", 'if not result.get("lokEventsSeen"):', 'if False:'),
    ("p2c lone -> ESTABLISHED", 'reading = "ESTABLISHED" if result.get("loneSizeChanges") else NE', 'reading = NE'),
    ("exit: page sha refused", 'if expect_page and ident.get("pageServedSha256") != expect_page:', 'if False:'),
    ("exit: no rule -> FAIL", 'verdicts[(browser, arm)] = FAIL\n                continue', 'continue'),
    ("exit: criterion arm on trace worker -> FAIL", 'if arm not in MEASUREMENT_ARMS and ident.get("instrumentedWorker") is True:', 'if False:'),
    ("exit: missing cell -> FAIL", 'verdict = PASS if not failures and not missing else FAIL', 'verdict = PASS if not failures else FAIL'),
    ("exit: runnerError in any arm -> not PASS (via c1)", 'if result.get("runnerError"):\n        return NE, [f"runner error: {result[\'runnerError\']}"]\n    rounds',
     'if False:\n        return NE, []\n    rounds'),
]

RUNNER = [
    ("span_of strict < (y)", 'r["y"] < ry1 and ry0 < r["y"] + r["height"]', 'r["y"] <= ry1 and ry0 <= r["y"] + r["height"]'),
    ("span_of first/last in string order", 'return {"first": hits[0], "last": hits[-1]', 'return {"first": min(hits), "last": max(hits)'),
    ("region_of uses paperHeight scale", 'scale = doc_h / geometry["paperHeight"]', 'scale = doc_h / (geometry["paperHeight"] + 40)'),
    ("parse_rects refuses a torn piece", 'if len(numbers) != 4:\n            return None', 'if len(numbers) < 4:\n            return None'),
    ("caret_equal compares all four fields", 'for k in ("x", "y", "width", "height"))', 'for k in ("x", "y"))'),
    ("reference_caret same generation", 'and e.get("g") == request_entry.get("g")', ''),
    ("reference_caret before the request", 'and e["t"] <= request_entry["t"]]', ']'),
    ("judge_refusal sequence <=", 'and cb["sourceSequence"] <= ref["seq"])', ')'),
    ("lok_summary window 25 -> 39", 'LONE_WINDOW_MS = 25 ', 'LONE_WINDOW_MS = 39 '),
    ("lok_summary window 25 -> 3", 'LONE_WINDOW_MS = 25 ', 'LONE_WINDOW_MS = 3 '),
    ("NOT_LONE_IDS -> (0,)", 'NOT_LONE_IDS = (0, 1, 2, 3, 4)', 'NOT_LONE_IDS = (0,)'),
    ("P3 untriggered window 2000 -> 60000", '<= 2000 for tr in triggers)', '<= 60000 for tr in triggers)'),
    ("P3 nonVacuous needs reached_bottom", '"nonVacuous": bool(paints) and reached_bottom', '"nonVacuous": bool(paints)'),
]


def red_cases_green(workdir: Path) -> bool:
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}
    a = subprocess.run([sys.executable, "tools/judge_v20_shakedown.py", "--self-test"], cwd=workdir,
                       capture_output=True, text=True, env=env)
    b = subprocess.run([sys.executable, "-m", "unittest", "tests.test_v20_shakedown_judge"], cwd=workdir,
                       capture_output=True, text=True, env=env)
    return a.returncode == 0 and b.returncode == 0


def census(name: str, target: str, mutations) -> None:
    print(f"== {name}")
    survivors = 0
    for rule, old, new in mutations:
        if WORK.exists():
            shutil.rmtree(WORK)
        shutil.copytree(SRC, WORK)
        path = WORK / "tools" / target
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            print(f"   ?? anchor not unique/absent ({text.count(old)}): {rule}")
            continue
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        green = red_cases_green(WORK)
        survivors += green
        print(f"   {'SURVIVES (no red case)' if green else 'killed               '}  {rule}")
    print(f"   {survivors}/{len(mutations)} rules have no red case")


if __name__ == "__main__":
    if not red_cases_green(SRC):
        raise SystemExit("the unmutated red cases are not green; census meaningless")
    census("judge_v20_shakedown.py rules", "judge_v20_shakedown.py", JUDGE)
    census("run_v20_shakedown.py predicates the judge relies on", "run_v20_shakedown.py", RUNNER)
    shutil.rmtree(WORK, ignore_errors=True)
