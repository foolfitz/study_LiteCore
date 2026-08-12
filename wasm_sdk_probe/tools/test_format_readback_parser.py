#!/usr/bin/env python3
"""Run the engine's own readback parser over the stored M2 captures.

Every tag classification published for finding 035 so far was produced by a
Python reimplementation of the scanner.  The scanner that ships is the C++ one
in probe_engine.cpp, and it had never been executed against a single one of the
21 payloads the decision rests on.  "Both are written from the same rules" is an
inference, and the rules are exactly what changed.

This does not copy the parser.  It slices it out of probe_engine.cpp between two
markers and compiles that text, so an edit to the engine is picked up here with
no second copy to keep in step.  Pass --revision to slice the same region out of
a git revision instead of the working tree, which is what makes a before/after
comparison possible at all.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ENGINE = PROJECT / "src" / "probe_engine.cpp"

BEGIN = "// The structural set, and every member of it was measured at body level"
BEGIN_OLD = "// The closed set of block tags this build will accept"
END = "FormatReadback parseFormatReadback"

HARNESS = r"""
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

%(slice)s

int main(int argc, char **argv) {
  for (int index = 1; index < argc; ++index) {
    std::ifstream input(argv[index], std::ios::binary);
    std::ostringstream buffer;
    buffer << input.rdbuf();
    const FormatReadback readback = parseFormatReadback(buffer.str());
    std::cout << argv[index] << '\t'
              << (readback.parsed ? 1 : 0) << '\t'
              << (readback.unknownTag ? 1 : 0) << '\t'
              << (readback.unknownTagName.empty() ? "-" : readback.unknownTagName)
              << '\t' << (readback.malformedNesting ? 1 : 0) << '\t'
              << (readback.footnoteApparatus ? 1 : 0) << '\t'
              << (readback.multiBlock ? 1 : 0) << '\t'
              << readback.blockCount << '\t' << readback.itemCount << '\t'
              << (readback.listTag.empty() ? "-" : readback.listTag) << '\t'
              << (readback.blockTag.empty() ? "-" : readback.blockTag) << '\n';
  }
  return 0;
}
"""

# The pre-change parser has neither field, so the harness has to be told which
# shape it is compiling against rather than guessing from a compile failure.
HARNESS_OLD = HARNESS.replace(
    '<< (readback.unknownTagName.empty() ? "-" : readback.unknownTagName)\n'
    "              << '\\t' << (readback.malformedNesting ? 1 : 0) << '\\t'\n"
    "              << (readback.footnoteApparatus ? 1 : 0) << '\\t'",
    "<< \"-\" << '\\t' << 0 << '\\t' << 0 << '\\t'",
)


def engine_text(revision: str | None) -> str:
    if revision is None:
        return ENGINE.read_text(encoding="utf-8")
    relative = ENGINE.relative_to(PROJECT.parent)
    return subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=PROJECT.parent, check=True, capture_output=True, text=True,
    ).stdout


def slice_parser(text: str) -> tuple[str, bool]:
    begin = text.find(BEGIN)
    modern = begin != -1
    if not modern:
        begin = text.find(BEGIN_OLD)
    if begin == -1:
        raise SystemExit("parser region not found: the marker comment moved")
    body = text.find(END, begin)
    if body == -1:
        raise SystemExit("parseFormatReadback not found after the marker")
    # The function ends at the first line that is exactly "}" after its body.
    end = text.find("\n}\n", body)
    if end == -1:
        raise SystemExit("could not find the end of parseFormatReadback")
    return text[begin:end + 3], modern


def build(text: str, modern: bool, out: Path) -> Path:
    source = out / "readback_parser_test.cpp"
    template = HARNESS if modern else HARNESS_OLD
    source.write_text(template % {"slice": text}, encoding="utf-8")
    binary = out / "readback_parser_test"
    subprocess.run(
        ["g++", "-std=c++17", "-O1", str(source), "-o", str(binary)],
        check=True,
    )
    return binary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--captures", type=Path,
        default=PROJECT / "build" / "e2-a-paragraph-content" / "results.jsonl",
    )
    parser.add_argument("--revision", help="slice the parser from this git revision")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    records = [
        json.loads(line)
        for line in args.captures.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    payloads = [
        record for record in records
        if record.get("probe") == "readback" and isinstance(record.get("html"), str)
        and record["html"]
    ]
    if not payloads:
        raise SystemExit(f"no readback payloads in {args.captures}")

    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory)
        text, modern = slice_parser(engine_text(args.revision))
        binary = build(text, modern, out)
        files = []
        for record in payloads:
            path = out / (record["anchor"].replace("/", "_") + ".html")
            path.write_text(record["html"], encoding="utf-8")
            files.append(path)
        completed = subprocess.run(
            [str(binary), *[str(path) for path in files]],
            check=True, capture_output=True, text=True,
        )

    rows = []
    for line, record in zip(completed.stdout.splitlines(), payloads):
        fields = line.split("\t")
        rows.append({
            "anchor": record["anchor"],
            "parsed": fields[1] == "1",
            "unknownTag": fields[2] == "1",
            "unknownTagName": None if fields[3] == "-" else fields[3],
            "malformedNesting": fields[4] == "1",
            "footnoteApparatus": fields[5] == "1",
            "multiBlock": fields[6] == "1",
            "blockCount": int(fields[7]),
            "itemCount": int(fields[8]),
            "listTag": None if fields[9] == "-" else fields[9],
            "blockTag": None if fields[10] == "-" else fields[10],
        })

    report = {
        "parserFrom": args.revision or "working tree",
        "parserShape": "structural-depth" if modern else "closed-tag-set",
        "captures": str(args.captures),
        "payloads": len(rows),
        "rows": rows,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
