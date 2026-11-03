#!/usr/bin/env python3
"""The red cases of tests/document_format_test.cpp against src/document_format.hpp (specs/SPEC-P-ms-formats.md 6.1 F1).

The mutations are GENERATED from the header's table, not listed by hand: every entry of kWriter and kCalc gets a
`drop` (the line removed) and a `flip` (its savable inverted), and every table gets an `add` (a `.doc` entry appended),
so an entry added to the header later gets its red cases without anyone editing this file.  Six rule mutations are
written out below.  The test is built once against the header as it is (the control, which must pass) and once per
mutation, each of which must fail in the named check family.  Each edit must match exactly once; a table with no
entries is refused (a census of nothing is not a pass).

Usage: python3 -I tests/document_format_mutations.py [--cxx g++]
Exit 0 only when the control passes and every mutation is red as required.
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent.parent
HEADER = HERE / "src" / "document_format.hpp"
TEST = HERE / "tests" / "document_format_test.cpp"

RULES = {
    "case-sensitive": (
        "  for (char &c : text)\n    c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));\n", "", "A1"),
    "no-stem-required": ("lowered.size() > suffix.size() &&", "lowered.size() >= suffix.size() &&", "R1"),
    "suffix-anywhere": (
        "lowered.compare(lowered.size() - suffix.size(), suffix.size(), suffix) == 0)",
        "lowered.find(suffix) != std::string::npos)", "R1"),
    "profiles-swapped": ("  if (profile == Profile::Calc) {", "  if (profile != Profile::Calc) {", "T1"),
    "save-ignores-savable": ("if (entries[i].savable && format == entries[i].format)",
                             "if (format == entries[i].format)", "S1"),
    "save-any-case": ("if (entries[i].savable && format == entries[i].format)",
                      "if (entries[i].savable && lower(format) == entries[i].format)", "S1"),
}


def table_mutations(text):
    out = {}
    for table in ("kWriter", "kCalc"):
        block = re.search(r"inline constexpr Entry %s\[\] = \{\n(.*?)\n\};" % table, text, re.S)
        if not block:
            raise SystemExit(f"{table} not found in the header")
        lines = [l for l in block.group(1).split("\n") if l.strip().startswith("{")]
        if not lines:
            raise SystemExit(f"{table} has no entries")
        for line in lines:
            suffix = re.search(r'\{"([^"]+)"', line).group(1)
            out[f"{table}-drop{suffix}"] = (line + "\n", "", "T1")
            flipped = line.replace("true}", "FLIP}").replace("false}", "true}").replace("FLIP}", "false}")
            out[f"{table}-flip{suffix}"] = (line + "\n", flipped + "\n", "T1")
        last = lines[-1]
        out[f"{table}-add.doc"] = (last + "\n", last + "\n" + '    {".doc", "doc", true},\n', "T1")
    return out


def build_and_run(cxx, header_text, work):
    src = work / "src"
    src.mkdir(exist_ok=True)
    (src / "document_format.hpp").write_text(header_text)
    exe = work / "t"
    compiled = subprocess.run([cxx, "-std=c++17", "-I", str(src), str(TEST), "-o", str(exe)], capture_output=True, text=True)
    if compiled.returncode:
        return "compile", compiled.stderr[-600:]
    ran = subprocess.run([str(exe)], capture_output=True, text=True)
    return ran.returncode, ran.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cxx", default="g++")
    args = parser.parse_args()
    text = HEADER.read_text()
    mutations = {**table_mutations(text), **RULES}
    results, ok = {}, True
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        code, output = build_and_run(args.cxx, text, work)
        control = code == 0 and output.strip().endswith("ok")
        results["control"] = {"exit": code, "pass": control}
        ok &= control
        for name, (old, new, family) in mutations.items():
            if text.count(old) != 1:
                results[name] = {"red": False, "why": f"anchor matches {text.count(old)} times"}
                ok = False
                continue
            code, output = build_and_run(args.cxx, text.replace(old, new), work)
            red = code not in (0, "compile") and f"FAIL {family} " in output
            results[name] = {"red": red, "exit": code, "family": family,
                             "firstFailure": next((l for l in str(output).splitlines() if l.startswith("FAIL")), None)}
            ok &= red
    for name, r in results.items():
        print(f"{name}: {r}")
    print(f"{len(mutations)} mutations; {'ALL RED, control green' if ok else 'NOT ALL RED or control red'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
