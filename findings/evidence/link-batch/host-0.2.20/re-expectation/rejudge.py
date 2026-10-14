#!/usr/bin/env python3
"""Re-judge every committed held / table report under the judge before and after task 2026-10-14m.

No browser.  The judge before the task is read from git (`BEFORE` commit, the task's starting tree) and run as a
module with `__file__` set to the real judge path, so its probe lookups resolve exactly as they did; the judge after
is the working-tree file.  Both are run with the report's own `servedPage` as `--page` (the page each report was
taken on; the judge requires served == dist == --page, so any other page would only add a `static:` line).

For every report both outputs are kept under `outputs/`, and the comparison strips only the two lines the edited
judge adds (`engine ...`, `expectation ...`): the verdict line and every other line must be identical for a v19-era
report, and the three v20 reports are the witness, whose change is the point.

Red cases (AGENTS.md 6), each written beside the main output:
  R1  the v20 held report doctored into a refusal (start-press: refusals 1, generations ['1','2'], a reopen toast)
      and the v20 table report doctored on cell-start-hold's refusal stage, and the v20 held report with one
      end-hold scroll sample at 0: each must FAIL under C on the clause that was doctored;
  R2  a v19 report (0.2.18 held and table) judged under C anyway (`judge_report(..., declared=True)`): red on every
      10.7 arm, on `no_reopen`;
  R3  the v20 reports judged under the refusal anyway (what the judge before did): the failure lines equal the
      committed witness outputs (`../held/judge-output.txt`, `../table/judge-output.txt`);
  R4  the v20 held report keyed on the 0.2.18 engine package (`--engine`): FAIL on the buildId, nothing judged;
  R5  a scratch package = the 0.2.20 manifest with the 0.2.18 wasm bytes: FAIL on the wasm's sha256, nothing judged.

  rejudge.py [--before COMMIT] [--out-dir DIR] [--scratch DIR]
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]        # findings/evidence/link-batch/host-0.2.20/re-expectation/
JUDGE = ROOT / "findings/evidence/132/held-into-refusal/judge_held_into_refusal.py"
JUDGE_REL = JUDGE.relative_to(ROOT).as_posix()
BEFORE = "00900fdd"
ARCHIVE = ROOT / "wasm_sdk_probe/build/archive"
WITNESS = ROOT / "findings/evidence/link-batch/host-0.2.20"
# Every committed report of the two probes the judge reads (findings/evidence/**/report.json whose `probe` is one
# of them), v19-era first, then the witness.  A fictitious entry here would be caught: a path that is not a file
# STOPS the script.
V19_REPORTS = (
    "findings/evidence/132/held-into-refusal/run-1/report.json",
    "findings/evidence/134/acceptance-0.2.16/report.json",
    "findings/evidence/134/red-d-on-0.2.15/report.json",
    "findings/evidence/134/table/run-1/report.json",
    "findings/evidence/134/table/run-2/report.json",
    "findings/evidence/134/table/run-3/report.json",
    "findings/evidence/136/acceptance-0.2.17/held/report.json",
    "findings/evidence/136/acceptance-0.2.17/table/report.json",
    "findings/evidence/136/acceptance-0.2.18/held/report.json",
    "findings/evidence/136/acceptance-0.2.18/table/report.json",
    "findings/evidence/136/baseline-0.2.16/held/report.json",
    "findings/evidence/136/baseline-0.2.16/table/report.json",
    "findings/evidence/136/cell-start-hold/red-aebef525/report.json",
)
V20_REPORTS = (
    "findings/evidence/link-batch/host-0.2.20/held/report.json",
    "findings/evidence/link-batch/host-0.2.20/table/report.json",
)
# The restore-window reports: the judge reads neither probe (`report['probe']` is not held or table), before or
# after; listed so that the script shows it, not to judge them.
RESTORE_WINDOW_REPORTS = (
    "findings/evidence/134/restore-window/run-1/report.json",
    "findings/evidence/136/guard/restore-window/report.json",
    "findings/evidence/136/guard-r2/restore-window/report.json",
    "findings/evidence/link-batch/host-0.2.20/restore-window/report.json",
)
ADDED_LINES = ("engine ", "expectation ")


def load_before(commit: str) -> types.ModuleType:
    src = subprocess.run(["git", "show", f"{commit}:{JUDGE_REL}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    mod = types.ModuleType("judge_before")
    mod.__file__ = str(JUDGE)
    exec(compile(src, str(JUDGE), "exec"), mod.__dict__)
    return mod, hashlib.sha256(src.encode()).hexdigest()


def load_after() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("judge_after", JUDGE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, hashlib.sha256(JUDGE.read_bytes()).hexdigest()


def run_main(mod: types.ModuleType, argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    old = sys.argv
    sys.argv = ["judge_held_into_refusal.py", *argv]
    try:
        with contextlib.redirect_stdout(buf):
            try:
                code = mod.main()
            except SystemExit as stop:  # argparse
                code = stop.code
    finally:
        sys.argv = old
    return code, buf.getvalue()


def run_judge_report(mod: types.ModuleType, report: dict, page: str, declared: bool) -> tuple[list[str], str]:
    lines: list[str] = []
    failures = mod.judge_report(report, page, "chrome,firefox", declared, out=lines.append)
    return failures, "\n".join(lines) + "\n"


def strip_added(text: str) -> list[str]:
    return [line for line in text.splitlines() if not line.startswith(ADDED_LINES)]


def verdict_of(text: str) -> str:
    return next((line for line in reversed(text.splitlines()) if line.startswith("verdict ")), "(no verdict)")


def failure_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("FAIL ")]


def page_of(report: dict) -> str:
    return (report.get("static") or {}).get("servedPage") or ""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def tag_of(rel: str) -> str:
    parts = Path(rel).parts
    return "-".join(parts[2:-1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", default=BEFORE)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--scratch", type=Path, required=True, help="where doctored reports and the R5 package go")
    args = parser.parse_args()
    out_dir, scratch = args.out_dir, args.scratch
    scratch.mkdir(parents=True, exist_ok=True)
    before, before_sha = load_before(args.before)
    after, after_sha = load_after()
    assert not hasattr(before, "judge_report"), "the judge before the task must be the one without the keying"
    lines: list[str] = [f"judge before: {args.before}:{JUDGE_REL} sha256 {before_sha}",
                        f"judge after:  {JUDGE_REL} sha256 {after_sha}", ""]
    result: dict = {"before": {"commit": args.before, "sha256": before_sha}, "after": {"sha256": after_sha},
                    "reports": [], "red": {}}

    # --- the keying on every archived package: the fragment is in one of them.
    lines.append("## keying per archived engine package (the fragment, read as the judge reads it)")
    for pkg in sorted(ARCHIVE.glob("host-*-engine-*")):
        man = json.loads((pkg / "MANIFEST.json").read_text())
        fake = {"static": {"buildId": man["buildId"], "servedPage": man["files"][after.PAGE_MODULE]["sha256"]}}
        key = after.keying(fake, None)
        lines.append(f"- {pkg.name}: profile {key.get('profile')} wasm {key.get('wasmSha256', '')[:16]} "
                     f"declares C: {key.get('declared')}" + (f" ERROR {key['error']}" if "error" in key else ""))
        result.setdefault("packages", []).append({"package": pkg.name, **{k: v for k, v in key.items() if k != 'package'}})
    lines.append("")

    # --- every report, before and after.
    lines.append("## every committed report of the two probes, judge before vs after")
    lines.append("| report | host | buildId | declares C | verdict before | verdict after | other lines |")
    lines.append("|---|---|---|---|---|---|---|")
    for rel in V19_REPORTS + V20_REPORTS:
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"STOP: {rel} is not a file")
        report = json.loads(path.read_text())
        page = page_of(report)
        tag = tag_of(rel)
        code_b, out_b = run_main(before, [str(path), "--page", page])
        code_a, out_a = run_main(after, [str(path), "--page", page])
        write(out_dir / "outputs" / f"{tag}-before.txt", out_b + f"exit {code_b}\n")
        write(out_dir / "outputs" / f"{tag}-after.txt", out_a + f"exit {code_a}\n")
        same = strip_added(out_b) == strip_added(out_a)
        key = after.keying(report, None)
        row = {"report": rel, "host": (report.get("static") or {}).get("hostVersion"),
               "buildId": (report.get("static") or {}).get("buildId"), "declared": key.get("declared"),
               "verdictBefore": verdict_of(out_b), "verdictAfter": verdict_of(out_a),
               "exitBefore": code_b, "exitAfter": code_a, "otherLinesIdentical": same,
               "failuresBefore": failure_lines(out_b), "failuresAfter": failure_lines(out_a)}
        result["reports"].append(row)
        lines.append(f"| {rel} | {row['host']} | {row['buildId']} | {row['declared']} | {row['verdictBefore']} | "
                     f"{row['verdictAfter']} | {'identical' if same else 'DIFFER'} |")
    lines.append("")
    for rel in RESTORE_WINDOW_REPORTS:
        report = json.loads((ROOT / rel).read_text())
        code_b, out_b = run_main(before, [str(ROOT / rel), "--page", page_of(report)])
        code_a, out_a = run_main(after, [str(ROOT / rel), "--page", page_of(report)])
        lines.append(f"- {rel}: before `{verdict_of(out_b)}` exit {code_b}; after `{verdict_of(out_a)}` exit {code_a} "
                     f"(`{out_a.splitlines()[0]}`)")
    lines.append("")

    # --- the witness under C, in full, beside this file.
    held = json.loads((WITNESS / "held/report.json").read_text())
    table = json.loads((WITNESS / "table/report.json").read_text())
    page20 = page_of(held)
    for name, rep in (("held", held), ("table", table)):
        code, out = run_main(after, [str(WITNESS / name / "report.json"), "--page", page20])
        write(out_dir / f"{name}-under-c.txt", out + f"exit {code}\n")

    # --- R1: doctored v20 reports must be red under C on the doctored clause.
    lines.append("## R1 -- the v20 reports doctored, judged under C (must FAIL on the doctored clause)")
    red1 = []
    d = copy.deepcopy(held)
    run = next(r for r in d["runs"] if r["arm"] == "start-press" and r["browser"] == "chrome")
    run["summary"]["refusals"], run["summary"]["generations"] = 1, ["1", "2"]
    run["summary"]["toasts"] = ["這一下沒有取得可刪除的內容。文件沒有被改動，正在重新載入…"]
    f, text = run_judge_report(after, d, page20, True)
    write(out_dir / "red-R1a-held-start-press-refused-under-c.txt", text)
    red1.append(("R1a start-press refused", f))
    d = copy.deepcopy(held)
    run = next(r for r in d["runs"] if r["arm"] == "end-hold" and r["browser"] == "firefox" and r["round"] == 1)
    states = [e for e in run["log"] if e.get("what") == "state"]
    states[len(states) // 2]["scroll"] = 0
    f, text = run_judge_report(after, d, page20, True)
    write(out_dir / "red-R1b-held-end-hold-scroll-0-under-c.txt", text)
    red1.append(("R1b end-hold one scroll sample 0", f))
    d = copy.deepcopy(table)
    run = next(r for r in d["runs"] if r["arm"] == "cell-start-hold" and r["browser"] == "chrome" and r["round"] == 0)
    run["refusalStage"] = {"stage": "nothing-selected", "stages": ["nothing-selected"]}
    f, text = run_judge_report(after, d, page20, True)
    write(out_dir / "red-R1c-table-cell-start-hold-stage-under-c.txt", text)
    red1.append(("R1c cell-start-hold stage read", f))
    for name, f in red1:
        lines.append(f"- {name}: {len(f)} failure(s): {f}")
    result["red"]["R1"] = {name: f for name, f in red1}
    assert all(f for _, f in red1), "R1: a doctored report passed"
    lines.append("")

    # --- R2: v19 reports under C must be red.
    lines.append("## R2 -- 0.2.18's held and table reports judged under C anyway (must FAIL on every 10.7 arm)")
    result["red"]["R2"] = {}
    for rel in ("findings/evidence/136/acceptance-0.2.18/held/report.json",
                "findings/evidence/136/acceptance-0.2.18/table/report.json"):
        rep = json.loads((ROOT / rel).read_text())
        f, text = run_judge_report(after, rep, page_of(rep), True)
        write(out_dir / f"red-R2-{tag_of(rel)}-under-c.txt", text)
        arms_red = sorted({line.split(":")[0].split(" ")[1] for line in f if line.split(" ")[0] in ("chrome", "firefox")})
        lines.append(f"- {rel}: {verdict_of(text)}; red arms {arms_red}; "
                     f"no_reopen lines {sum('!= 0 (C' in x for x in f)}")
        result["red"]["R2"][rel] = {"verdict": verdict_of(text), "redArms": arms_red, "failures": f}
        assert f, f"R2: {rel} passed under C"
    lines.append("")

    # --- R3: the v20 reports under the refusal reproduce the witness outputs.
    lines.append("## R3 -- the v20 reports judged under the refusal anyway (what the judge before did): equals the witness")
    result["red"]["R3"] = {}
    for name, rep in (("held", held), ("table", table)):
        f, text = run_judge_report(after, rep, page20, False)
        witness = (WITNESS / name / "judge-output.txt").read_text()
        same = failure_lines(text) == failure_lines(witness) and verdict_of(text) == verdict_of(witness)
        lines.append(f"- {name}: {verdict_of(text)}; failure lines equal the committed witness: {same}")
        result["red"]["R3"][name] = {"verdict": verdict_of(text), "equalsWitness": same}
        assert same, f"R3: {name} under the refusal differs from the witness"
    lines.append("")

    # --- R4: the v20 held report keyed on the 0.2.18 package.
    lines.append("## R4 -- the v20 held report keyed on the 0.2.18 engine package (--engine): FAIL, nothing judged")
    pkg18 = next(ARCHIVE.glob("host-0.2.18-engine-*"))
    code, text = run_main(after, [str(WITNESS / "held/report.json"), "--page", page20, "--engine", str(pkg18)])
    write(out_dir / "red-R4-held-keyed-on-0.2.18-package.txt", text + f"exit {code}\n")
    lines.append(f"- exit {code}; `{text.splitlines()[0]}`; lines {len(text.splitlines())}")
    result["red"]["R4"] = {"exit": code, "first": text.splitlines()[0], "lines": len(text.splitlines())}
    assert code == 1 and len(text.splitlines()) == 2 and "buildId" in text, "R4 did not stop on the buildId"
    lines.append("")

    # --- R5: the 0.2.20 manifest over the 0.2.18 wasm bytes.
    lines.append("## R5 -- a package with 0.2.20's manifest and 0.2.18's wasm bytes: FAIL on the wasm sha256, nothing judged")
    pkg20 = next(ARCHIVE.glob("host-0.2.20-engine-*"))
    man20 = json.loads((pkg20 / "MANIFEST.json").read_text())
    man18 = json.loads((pkg18 / "MANIFEST.json").read_text())
    wasm20 = next(p for p in man20["files"] if p.endswith("/probe.wasm"))
    wasm18 = next(p for p in man18["files"] if p.endswith("/probe.wasm"))
    fake = scratch / "fake-package"
    if fake.exists():
        shutil.rmtree(fake)
    (fake / "files" / Path(wasm20).parent).mkdir(parents=True)
    shutil.copy(pkg20 / "MANIFEST.json", fake / "MANIFEST.json")
    shutil.copy(pkg18 / "files" / (wasm18 + ".gz"), fake / "files" / (wasm20 + ".gz"))
    code, text = run_main(after, [str(WITNESS / "held/report.json"), "--page", page20, "--engine", str(fake)])
    write(out_dir / "red-R5-held-keyed-on-swapped-wasm.txt", text.replace(str(scratch), "<scratch>") + f"exit {code}\n")
    lines.append(f"- exit {code}; `{text.splitlines()[0].replace(str(scratch), '<scratch>')}`; lines {len(text.splitlines())}")
    result["red"]["R5"] = {"exit": code, "first": text.splitlines()[0].replace(str(scratch), "<scratch>")}
    assert code == 1 and len(text.splitlines()) == 2 and "sha256" in text, "R5 did not stop on the wasm bytes"
    lines.append("")

    # --- the constant is the runner's.
    spec = importlib.util.spec_from_file_location("merge_runner", ROOT / "wasm_sdk_probe/tools/run_merge_wasm_shakedown.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    same_fragment = runner.BOUNDARY_NOOP_FRAGMENT == after.BOUNDARY_NOOP_FRAGMENT
    lines.append(f"fragment equals run_merge_wasm_shakedown.BOUNDARY_NOOP_FRAGMENT: {same_fragment}")
    result["fragmentEqualsRunner"] = same_fragment
    assert same_fragment

    # --- summary.
    v19_rows = [r for r in result["reports"] if r["report"] in V19_REPORTS]
    v20_rows = [r for r in result["reports"] if r["report"] in V20_REPORTS]
    unchanged = sum(r["verdictBefore"] == r["verdictAfter"] and r["otherLinesIdentical"] for r in v19_rows)
    lines.append("")
    lines.append(f"v19-era reports: {unchanged}/{len(v19_rows)} identical (verdict and every line but the two added)")
    lines.append(f"v20 reports: " + "; ".join(f"{tag_of(r['report'])} {r['verdictBefore']} -> {r['verdictAfter']}" for r in v20_rows))
    assert unchanged == len(v19_rows), "a v19-era report changed"
    assert all(r["verdictAfter"] == "verdict PASS" for r in v20_rows), "a v20 report is not PASS under C"
    text = "\n".join(lines) + "\n"
    write(out_dir / "rejudge-output.txt", text)
    write(out_dir / "rejudge.json", json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
