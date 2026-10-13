#!/usr/bin/env python3
"""Build the two synthetic reports of review 1 (findings/evidence/136/review/review-1.md, S1 and N1),
the reds for the judge edit of ruling-3 addendum 4 (continued) and addendum 5.  Each copies a real
report and changes only the fields named below; nothing else is touched.

  M1 (S1)  acceptance-0.2.17/table/report.json (page aebef525, every press/hold arm PASS) with
           cell-press-type's reader fields moved to paragraph 0, as if the ArrowDown had not moved
           the caret: controlParagraphs [0], markParagraphs [0], controlThenMark true.  Before the
           edit those rounds PASS (the hole); after it they must FAIL.
  M2 (N1)  baseline-0.2.16/held/report.json (page 6470dec0) with, on every end round, the jump to 0
           inside the reopen window replaced by `pre` (so the window holds), and one sample at 0
           inserted right after the closing 「已重新載入」 sample plus one back at `pre` 700 ms later.
           Before the edit the report exits 0; after it, it must exit 1.

  build_synthetic_m1_m2.py OUTDIR
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
RELOADED = "已重新載入"


def m1() -> dict:
    report = json.loads((EVIDENCE / "acceptance-0.2.17" / "table" / "report.json").read_text())
    for run in report["runs"]:
        if run["arm"] == "cell-press-type":
            run["server"].update(controlParagraphs=[0], markParagraphs=[0], controlThenMark=True)
    report["synthetic"] = "M1: cell-press-type's control+mark moved to paragraph 0 (review 1, S1)"
    return report


def m2() -> dict:
    report = json.loads((EVIDENCE / "baseline-0.2.16" / "held" / "report.json").read_text())
    for run in report["runs"]:
        if run["arm"] not in ("end-hold", "end-press-type"):
            continue
        log = run["log"]
        states = [k for k, e in enumerate(log) if e.get("what") == "state"]
        first = next(k for k in states if log[k]["state"] == "restart-required")
        pre = log[max(k for k in states if k < first)]["scroll"]
        close = next(k for k in states if k >= first and RELOADED in (log[k].get("toast") or ""))
        for k in states:
            if first <= k <= close and log[k]["scroll"] < pre:
                log[k]["scroll"] = pre
        at = log[close]
        dip = copy.deepcopy(at) | {"t": round(at["t"] + 1.0, 1), "scroll": 0}
        back = copy.deepcopy(at) | {"t": round(at["t"] + 701.0, 1), "scroll": pre}
        log[close + 1:close + 1] = [dip, back]
    report["synthetic"] = "M2: window held at pre, one 0 sample after the closing toast (review 1, N1)"
    return report


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    (out / "synthetic-M1.json").write_text(json.dumps(m1(), ensure_ascii=False, indent=1))
    (out / "synthetic-M2.json").write_text(json.dumps(m2(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
