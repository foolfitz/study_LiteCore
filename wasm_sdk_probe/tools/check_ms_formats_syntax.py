#!/usr/bin/env python3
"""specs/SPEC-P-ms-formats.md 6.1 F2, before the links: em++ -fsyntax-only and -E on the e2-editor-v33 and ods-editor-v5 objects
(nothing produced, no make run; AGENTS.md 2026-10-28).

The compile commands are the Makefile's own, read from `make -n -B` of each profile's probe.js (a dry run prints them, runs
nothing), not rebuilt here.  For every command:

  syntax         `-c SRC -o OBJ` replaced by `-fsyntax-only SRC`, once as written and once without -DOXSDK_MS_FORMATS
                 (the predecessor's shape);
  control        sdk_api.cpp and probe_engine.cpp only: a scratch copy of src/ with an undeclared call inside the new
                 OXSDK_MS_FORMATS block must fail with the define and pass without it, or "green" could mean the block was
                 never compiled;
  exports        `-E -P`: every `_oxsdk_*` name in the profile's export list has a function body in the preprocessed sources
                 (a missing body fails the link and -fsyntax-only cannot see it, memory 2026-11-03).

taskset -c 0; refuses while a make runs.  Receipt: --out/report.json (argv, exit, seconds, first errors).
  check_ms_formats_syntax.py --out DIR
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

SDK = Path(__file__).resolve().parents[1]
PROFILES = {
    "writer": {"target": "build/e2/editor-v33/probe.js", "exports": "build/archive/e2-editor-v32-54e50093-worker-c394302c/exports.txt"},
    "calc": {"target": "build/ods/editor-v5/probe.js", "exports": "build/ods/editor-v4/exports.txt"},
}
CONTROL = {  # a line inside each source's OXSDK_MS_FORMATS block, matched exactly once; the call goes right before it
    "sdk_api.cpp": "    if (probe::docformat::acceptedSuffix(probe::docformat::kThisBuild, name).empty())\n",
    "probe_engine.cpp": "  json << \",\\\"format\\\":\\\"\"\n",
}
CALL = "    thisFunctionDoesNotExist();\n"


def compile_commands(target):
    dry = subprocess.run(["make", "-n", "-B", target], capture_output=True, text=True, cwd=SDK)
    joined = re.sub(r"\\\n", " ", dry.stdout)
    commands = []
    for line in joined.splitlines():
        found = re.search(r"\s-c (src/\S+\.cpp) -o (\S+\.o)\s*$", line)
        if found and "em++" in line.split()[0]:
            commands.append({"source": found.group(1), "argv": line.split()})
    if not commands:
        raise SystemExit(f"no compile command found for {target}: {dry.stderr[-400:]}")
    return commands


def swap(argv, source, replacement):
    i = argv.index("-c")
    assert argv[i + 1] == source and argv[i + 2] == "-o"
    return argv[:i] + replacement + argv[i + 4:]


def run(argv, label, report):
    started = time.monotonic()
    done = subprocess.run(["taskset", "-c", "0", *argv], capture_output=True, text=True, cwd=SDK)
    errors = [line for line in done.stderr.splitlines() if re.search(r"\berror\b", line)]
    report["runs"].append({"label": label, "argv": argv, "exit": done.returncode,
                           "seconds": round(time.monotonic() - started, 1), "errors": errors[:8]})
    print(label, done.returncode, round(time.monotonic() - started, 1), errors[:1], flush=True)
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    makes = subprocess.run(["pgrep", "-a", "make"], capture_output=True, text=True)
    report = {"uptime": subprocess.check_output(["uptime"], text=True).strip(), "makes": makes.stdout, "runs": [], "exports": {}}
    if makes.returncode == 0:
        (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
        raise SystemExit("a make is running; ask the owner first")
    scratch = out / "scratch"
    shutil.copytree(SDK / "src", scratch / "src")
    for name, source in CONTROL.items():
        path = scratch / "src" / name
        text = path.read_text()
        if text.count(source) != 1:
            raise SystemExit(f"control anchor for {name} occurs {text.count(source)} times")
        path.write_text(text.replace(source, CALL + source))
    verdict = {}
    for profile, spec in PROFILES.items():
        commands = compile_commands(spec["target"])
        report.setdefault("commands", {})[profile] = [c["source"] for c in commands]
        defined = set()
        for c in commands:
            argv, src = c["argv"], c["source"]
            name = Path(src).name
            with_define = "-DOXSDK_MS_FORMATS" in argv
            without = [a for a in argv if a != "-DOXSDK_MS_FORMATS"]
            run(swap(argv, src, ["-fsyntax-only", src]), f"{profile}/syntax/{name}", report)
            if with_define:
                run(swap(without, src, ["-fsyntax-only", src]), f"{profile}/syntax-without-define/{name}", report)
            if name in CONTROL and with_define:
                mutated = str(scratch / "src" / name)
                run(swap(argv, src, ["-fsyntax-only", mutated]), f"{profile}/control-with-define/{name}", report)
                run(swap(without, src, ["-fsyntax-only", mutated]), f"{profile}/control-without-define/{name}", report)
            pre = run(swap(argv, src, ["-E", "-P", src]), f"{profile}/preprocess/{name}", report)
            report["runs"][-1].pop("errors", None)
            defined |= set(re.findall(r"\b(oxsdk_[a-z0-9_]+)\s*\([^;{}]*\)\s*\{", pre.stdout))
        exported = sorted({n.lstrip("_") for n in (SDK / spec["exports"]).read_text().split() if n.startswith("_oxsdk_")})
        missing = [n for n in exported if n not in defined]
        report["exports"][profile] = {"list": spec["exports"], "exported": len(exported), "missing": missing}
        by = {r["label"]: r for r in report["runs"] if r["label"].startswith(profile + "/")}
        controls = [n for n in CONTROL if f"{profile}/control-with-define/{n}" in by]
        verdict[profile] = {
            "syntax-clean": all(r["exit"] == 0 for k, r in by.items() if "/syntax" in k),
            "controls-present": sorted(controls) == sorted(CONTROL),
            "control-caught-with-define": all(by[f"{profile}/control-with-define/{n}"]["exit"] != 0 and
                                              any("thisFunctionDoesNotExist" in e for e in by[f"{profile}/control-with-define/{n}"]["errors"])
                                              for n in controls),
            "control-silent-without-define": all(by[f"{profile}/control-without-define/{n}"]["exit"] == 0 for n in controls),
            "exports-have-bodies": bool(exported) and not missing,
        }
    shutil.rmtree(scratch)
    report["verdict"] = verdict
    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(verdict, indent=1))
    return 0 if all(all(v.values()) for v in verdict.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
