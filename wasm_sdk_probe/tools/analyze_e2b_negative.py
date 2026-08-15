#!/usr/bin/env python3
"""SPEC E2-B 5.10: judge the negative matrix.

Two criteria per row, and the second is the one that matters:

  1. the refusal carried one of the codes the row registered, and
  2. the document did not change -- judged by comparing `<office:body>` BYTE FOR
     BYTE between the save taken before the attempt and the save taken after.

A row that only checked the code would pass just as happily if the engine had
refused loudly and mutated anyway.  The byte criterion is not a new invention
either: task #50 used it for the undo check and it held there (heading -> undo
and list-removal -> undo were both byte-identical), so it is a threshold with a
track record rather than one chosen today to fit.

Separate from the runner on purpose, same as the other analyzers here: it reads
only saved files, so the verdict can be recomputed without a browser.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

BODY_OPEN = b"<office:body>"
BODY_CLOSE = b"</office:body>"


def body_bytes(odt: Path) -> bytes | None:
    """The <office:body> element, verbatim.

    Not the whole content.xml: the automatic-styles section renumbers on its own
    (P1, P2, L1 ...) and the meta section carries timestamps, so comparing the
    file would report differences that are not mutations.  The body is what a
    reader would call the document.
    """
    with zipfile.ZipFile(odt) as archive:
        content = archive.read("content.xml")
    start = content.find(BODY_OPEN)
    end = content.find(BODY_CLOSE)
    if start < 0 or end < 0:
        return None
    return content[start:end + len(BODY_CLOSE)]


def controls() -> list[str]:
    """The comparison must be able to report a difference."""
    problems = []
    a = b"<office:body><office:text><text:p>a</text:p></office:text></office:body>"
    b = b"<office:body><office:text><text:p>b</text:p></office:text></office:body>"
    if a == b:
        problems.append("byte comparison is not comparing")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path,
                        help="directory holding result.json and saved/")
    args = parser.parse_args()

    problems = controls()
    if problems:
        print(json.dumps({"controlsFailed": problems}))
        return 2

    result = json.loads((args.evidence / "result.json").read_text(encoding="utf-8"))
    verdicts = []
    for row in result.get("rows") or []:
        verdict = {"id": row.get("id"), "name": row.get("name"),
                   "round": row.get("round"), "profile": row.get("profile")}
        if row.get("void"):
            verdict["void"] = row["void"]
            verdicts.append(verdict)
            continue
        if row.get("fatal"):
            verdict["void"] = ["fatal", row["fatal"]]
            verdicts.append(verdict)
            continue

        observed = (row.get("observed") or {}).get("code")
        expected = row.get("expect") or []
        reasons = []
        if not row.get("refused"):
            reasons.append("the attempt was NOT refused")
        elif observed not in expected:
            reasons.append(f"refused with {observed}, registered {expected}")
        verdict["observedCode"] = observed

        # Zero mutation, on bytes.
        before = args.evidence / "saved" / f"{row['id']}-round{row['round']}-before.odt"
        after = args.evidence / "saved" / f"{row['id']}-round{row['round']}-after.odt"
        if row.get("zeroMutationBy") == "no document was opened":
            verdict["zeroMutation"] = True
            verdict["zeroMutationBy"] = "no document was opened"
        elif not before.exists() or not after.exists():
            reasons.append("no saved documents: zero mutation is unproven")
            verdict["zeroMutation"] = None
        else:
            body_before = body_bytes(before)
            body_after = body_bytes(after)
            same = body_before is not None and body_before == body_after
            verdict["zeroMutation"] = same
            verdict["zeroMutationBy"] = "office:body byte comparison"
            verdict["bodyBytes"] = len(body_before or b"")
            if not same:
                reasons.append("the document CHANGED despite the refusal")

        verdict["pass" if not reasons else "fail"] = reasons or True
        verdicts.append(verdict)

    by_row: dict[str, dict] = {}
    for verdict in verdicts:
        entry = by_row.setdefault(verdict["id"], {"rounds": 0, "passed": 0,
                                                  "failed": 0, "void": 0})
        entry["rounds"] += 1
        entry["passed"] += 1 if verdict.get("pass") else 0
        entry["failed"] += 1 if verdict.get("fail") else 0
        entry["void"] += 1 if verdict.get("void") else 0

    summary = {
        "artifact": result.get("artifact"),
        "browser": result.get("browser"),
        "attribution": result.get("attribution"),
        "byRow": by_row,
        "verdicts": verdicts,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    (args.evidence / "verdict.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = (bool(by_row)
          and all(v["rounds"] > 0 and v["failed"] == 0 and v["void"] == 0
                  for v in by_row.values())
          and (result.get("attribution") or {}).get("consistent") is True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
