#!/usr/bin/env python3
"""SPEC-M3-link-batch-v21 11.2 M0 (with 12.1): the model test's red cases.

tests/markdown_paste_model_test.cpp is built against a scratch copy of src/
holding src/markdown_paste.hpp as it is (the control, which must pass) and
then once per mutation of that header (each of which must fail).  The
mutations are edits to the header's SOURCE TEXT, not switches in it: the
product header carries no test knobs.  Each edit must match exactly once, so a
refactor that moves the line makes this script fail loudly instead of
"mutating" nothing.

The five mutations (M0's three, 12.1's one, and one on NUL):
  rule-1-case-sensitive        data: compared case-sensitively
  rule-2-removed               raw HTML no longer refused
  rule-3-replaced-by-old-no-text  "no block" replaced by the old 9.3 "no text"
  utf8-rule-removed            invalid UTF-8 no longer refused
  nul-rule-removed             a 0x00 byte no longer refused

and one that is not about bytes, for the interface's order of codes 1-5:
  order-caret-before-encoding  the caret read before the encoding check
which must turn the model test red without flipping any fixture item (the
fixture is byte-level; the order is checked by the test's own cases).

For the first four the fixture's own `mutations` lists (computed by the M0
builder from md4c facts, before any scanner code existed) name exactly which
items must flip, and to what; this script requires the model test to report
exactly that set.  For the NUL mutation the fixture has no list: every item
that flips must be one the fixture calls NUL, and at least one must flip.

The md4c compiled here must be the one the fixture names (md4c.c sha256 in its
`parser` record): a different md4c would be a different oracle.

Usage (from wasm_sdk_probe/): python3 tests/markdown_paste_mutations.py [--md4c DIR]
Exit 0 only when the control passes and every mutation is red as required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
FIXTURE = HERE / "tests" / "markdown_paste_expected.json"
CORPUS = HERE / "tests" / "markdown_paste_corpus"
HEADER = "markdown_paste.hpp"
DEFAULT_MD4C = HERE.parent / "wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c/src"

MUTATIONS = {
    "rule-1-case-sensitive": (
        "    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c - 'A' + 'a');\n",
        ""),
    "rule-2-removed": (
        "  if (facts.htmlBlocks != 0 || facts.htmlText != 0)\n    return Verdict::Html;\n",
        ""),
    "rule-3-replaced-by-old-no-text": (
        "  if (facts.blocks == 0)\n    return Verdict::NoBlock;\n",
        "  if (facts.textOutsideImages == 0)\n    return Verdict::NoBlock;\n"),
    "utf8-rule-removed": (
        "  if (!isValidUtf8(data, size))\n    return Verdict::InvalidUtf8;\n",
        ""),
    "nul-rule-removed": (
        "  if (size != 0 && std::memchr(data, 0, size) != nullptr)\n    return Verdict::Nul;\n",
        ""),
}
ENCODING = ("  if (!encodingIsUtf8())\n    return {kCodeEncodingUnsupported,\n"
            "            \"the engine's text encoding is not UTF-8, so the Markdown would be \"\n"
            "            \"decoded wrongly\"};\n")
CARET = ("  if (!collapsed())\n    return {kCodeNeedsCaret,\n"
         "            \"Markdown is pasted only at a caret; remove the selection first\"};\n")
MUTATIONS["order-caret-before-encoding"] = (ENCODING + CARET, CARET + ENCODING)
NOT_BYTE_LEVEL = {"order-caret-before-encoding"}
# The fixture's `mutations` key for each, where the fixture has one.
FIXTURE_LIST = {
    "rule-1-case-sensitive": "rule-1-case-sensitive",
    "rule-2-removed": "rule-2-removed",
    "rule-3-replaced-by-old-no-text": "rule-3-replaced-by-old-no-text",
    "utf8-rule-removed": "utf8-rule-removed",
}
FAIL_ITEM = re.compile(r"^FAIL (\S+): expected (\S+), got (\S+) ")


def build(src: Path, md4c_object: Path, out: Path, md4c: Path) -> None:
    cxx = os.environ.get("HOST_CXX", "g++")
    subprocess.run([cxx, "-std=c++17", "-O2", "-Wall", f"-I{src}", f"-I{md4c}",
                    "-DOXSDK_E2_V21_LINK_BATCH", "-o", str(out),
                    str(HERE / "tests" / "markdown_paste_model_test.cpp"), str(md4c_object),
                    "-Wl,--wrap=malloc,--wrap=realloc"], check=True)


def run(binary: Path) -> tuple[int, str]:
    p = subprocess.run([str(binary), str(FIXTURE), str(CORPUS)], capture_output=True, text=True)
    return p.returncode, p.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md4c", type=Path, default=DEFAULT_MD4C)
    a = ap.parse_args()

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    want_sha = re.search(r"md4c\.c sha256 ([0-9a-f]{64})", fixture["parser"]["md4c"]).group(1)
    have_sha = hashlib.sha256((a.md4c / "md4c.c").read_bytes()).hexdigest()
    if have_sha != want_sha:
        print(f"md4c.c is {have_sha}, the fixture names {want_sha}")
        return 2
    labels = {item["path"]: item["verdict"] for item in fixture["items"]}

    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        md4c_object = tmp / "md4c-native.o"
        subprocess.run(["gcc", "-std=c99", "-O2", "-c", str(a.md4c / "md4c.c"),
                        "-o", str(md4c_object)], check=True)
        header = (HERE / "src" / HEADER).read_text(encoding="utf-8")

        def tree(name: str, text: str) -> Path:
            src = tmp / name / "src"
            shutil.copytree(HERE / "src", src, ignore=shutil.ignore_patterns("*.o"))
            (src / HEADER).write_text(text, encoding="utf-8")
            return src

        control = tree("control", header)
        build(control, md4c_object, tmp / "control.bin", a.md4c)
        code, out = run(tmp / "control.bin")
        last = out.strip().splitlines()[-1] if out.strip() else ""
        print(f"control: exit {code}, {last}")
        if code != 0:
            failures.append("the control (the header as it is) is not green")
            print(out)

        for name, (old, new) in MUTATIONS.items():
            count = header.count(old)
            if count != 1:
                failures.append(f"{name}: the edit matches {count} times, not once")
                continue
            src = tree(name, header.replace(old, new))
            binary = tmp / f"{name}.bin"
            build(src, md4c_object, binary, a.md4c)
            code, out = run(binary)
            flipped = sorted(f"{m.group(1)}: {m.group(2)} -> {m.group(3)}"
                             for line in out.splitlines() if (m := FAIL_ITEM.match(line)))
            summary = out.strip().splitlines()[-1] if out.strip() else ""
            print(f"{name}: exit {code}, {summary}; fixture items flipped: {len(flipped)}")
            for f in flipped:
                print(f"    {f}")
            if code == 0:
                failures.append(f"{name}: the model test stayed green")
            key = FIXTURE_LIST.get(name)
            if name in NOT_BYTE_LEVEL:
                fails = [line[5:] for line in out.splitlines() if line.startswith("FAIL ")]
                for line in fails:
                    print(f"    {line}")
                if flipped:
                    failures.append(f"{name}: fixture items flipped: {flipped}")
            elif key is not None:
                expected = sorted(fixture["mutations"][key])
                if flipped != expected:
                    failures.append(f"{name}: flipped {flipped}, the fixture predicts {expected}")
            else:
                if not flipped:
                    failures.append(f"{name}: no fixture item flipped")
                odd = [f for f in flipped if labels[f.split(":", 1)[0]] != "NUL"]
                if odd:
                    failures.append(f"{name}: items that are not NUL flipped: {odd}")

    for f in failures:
        print("FAIL", f)
    print("ok" if not failures else f"FAILED {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
