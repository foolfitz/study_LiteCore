#!/usr/bin/env python3
"""R0b (SPEC-M3-paragraph-merge 13.1): does the selection's anchor-side
rectangle, which Writer sends in the unit's own flush, agree with the caret the
user had placed?

The engine's fence compares the two: the anchor side of the one-unit selection
(TEXT_SELECTION_START for Shift+Right, TEXT_SELECTION_END for Shift+Left) is
where the caret was when Writer processed the Shift press, whatever was still
queued before it; the caret callback delivered before the selection is what
the engine believes.  The fence only works if, with nothing queued, the two
rectangles agree -- and they come from different code (the caret from
SwVisibleCursor::SetPos with width 0 and the cursor height, the selection ends
from SwShellCursor::FillStartEnd -> GetCharRect).  This reader says, for every
arm whose unit holds a paragraph or line separator, whether they agree on x,
on y and on height, and exits 1 unless every such unit agrees on all three.

It also reports, without changing the exit status, the mapping PREDICTION-R0b
registered before the run in case the three do not agree: equal x, and the
caret's vertical span inside the anchor rectangle's (anchor y <= caret y and
caret y + caret height <= anchor y + anchor height + 1; the anchor is printed
from SwRect::SVRect, which takes one off the height, the caret is not).

Usage: check_merge_anchor_rect.py [--json OUT] ROUND_DIR [ROUND_DIR ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SEPARATORS = {10, 13, 0x2028, 0x2029}


def rect(payload: str) -> tuple[int, ...] | None:
    if not payload or payload == "EMPTY":
        return None
    first = payload.split(";", 1)[0]
    try:
        values = tuple(int(v.strip()) for v in first.split(","))
    except ValueError:
        return None
    return values if len(values) == 4 else None


def main(argv: list[str]) -> int:
    out = None
    if argv[:1] == ["--json"]:
        out, argv = Path(argv[1]), argv[2:]
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    rows, failures = [], []
    for round_dir in map(Path, argv):
        lines = (round_dir / "arms.jsonl").read_text(encoding="utf-8").splitlines()
        for line in lines[1:]:
            arm = json.loads(line)
            if arm.get("arm") not in ("select", "b") or "fatal" in arm:
                continue
            unit = arm.get("unit") or {}
            if "selectionStart" not in unit:
                failures.append(f"{round_dir.name} {arm['case']} r{arm['round']} {arm['arm']}: "
                                "no selectionStart field (probe without the R0b patch)")
                continue
            if not any(cp in SEPARATORS for cp in unit.get("codePoints") or []):
                continue
            origin = (arm.get("typedAt") if arm.get("pretype") else arm.get("placed")) or {}
            caret = rect(origin.get("cursor", ""))
            anchor = rect(unit.get("selectionEnd" if arm.get("backward") else "selectionStart", ""))
            row = {"roundDir": round_dir.name, "case": arm["case"], "round": arm["round"],
                   "arm": arm["arm"], "backward": arm.get("backward"),
                   "caret": caret, "anchor": anchor}
            if caret is None or anchor is None:
                row["verdict"] = "absent"
            else:
                row["x"] = caret[0] == anchor[0]
                row["y"] = caret[1] == anchor[1]
                row["height"] = caret[3] == anchor[3]
                row["verdict"] = "agree" if row["x"] and row["y"] and row["height"] else "differ"
                row["mapping"] = (row["x"] and anchor[1] <= caret[1]
                                  and caret[1] + caret[3] <= anchor[1] + anchor[3] + 1)
            rows.append(row)
            if row["verdict"] != "agree":
                failures.append(f"{round_dir.name} {arm['case']} r{arm['round']} {arm['arm']}: "
                                f"{row['verdict']} caret={caret} anchor={anchor}")
    if not rows:
        failures.append("no arm with a separator unit was compared")
    summary = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("agree", "differ", "absent")}
    for axis in ("x", "y", "height"):
        summary[f"{axis}Differs"] = sum(1 for r in rows if r.get(axis) is False)
    summary["mappingHolds"] = sum(1 for r in rows if r.get("mapping") is True)
    summary["mappingFails"] = sum(1 for r in rows if r.get("mapping") is False)
    if out:
        out.write_text(json.dumps({"summary": summary, "rows": rows, "failures": failures},
                                  indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary))
    for failure in failures:
        print("FAIL " + failure)
    for r in rows:
        if r.get("mapping") is False:
            print(f"MAPPING-FAILS {r['roundDir']} {r['case']} r{r['round']} {r['arm']}: "
                  f"caret={r['caret']} anchor={r['anchor']}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
