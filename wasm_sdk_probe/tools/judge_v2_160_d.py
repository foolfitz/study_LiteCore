#!/usr/bin/env python3
"""V2-160-D (SPEC-M4-viewer-v2 8.3): the engine's redispatch record against LOK's own, per file.

For every case of a Phase E report, from the worker stderr the harness keeps (`messages`, distinct texts
with counts):
  lok     = the count of LOK's `Failed to dispatch .uno:SelectAll` lines
  engine  = the sum of N x count over the engine's `oxsdk part-text: .uno:SelectAll not dispatched N time(s), ...`
Holds for the case when lok == engine; and when lok > 0, every read of the case is `selectAllConfirmed: true`
and no engine line says `never dispatched`.  A case whose distinct messages reached the harness's cap (200)
may have lost a line: NOT_JUDGED for that case, never a pass.  A report with no cases is refused.

  judge_v2_160_d.py REPORT.json [REPORT.json ...]     exit 0: holds everywhere; 1: does not; 2: not judgeable
  judge_v2_160_d.py --selftest
"""
from __future__ import annotations

import json
import re
import sys

LOK = "lok exception 'Failed to dispatch .uno:SelectAll'"
ENGINE = re.compile(r"oxsdk part-text: \.uno:SelectAll not dispatched (\d+) time\(s\), (then|never) dispatched")
CAP = 200


def judge_case(case: dict) -> dict:
    messages = case.get("messages") or []
    lok = sum(m.get("count", 0) for m in messages if LOK in m.get("message", ""))
    engine, never = 0, False
    for m in messages:
        hit = ENGINE.search(m.get("message", ""))
        if hit:
            engine += int(hit.group(1)) * m.get("count", 0)
            never |= hit.group(2) == "never"
    reads = [s.get("text") or {} for s in case.get("sheets") or [] if s.get("text")]
    unconfirmed = sum(1 for t in reads if t.get("selectAllConfirmed") is False)
    if len(messages) >= CAP:
        verdict = "NOT_JUDGED"
    elif lok != engine or (lok > 0 and (unconfirmed or never)):
        verdict = "FAIL"
    else:
        verdict = "PASS"
    return {"case": case.get("name"), "lok": lok, "engine": engine, "never": never,
            "unconfirmed": unconfirmed, "verdict": verdict}


def judge_report(report: dict) -> dict:
    cases = report.get("cases") or []
    if not cases:
        return {"verdict": "NOT_JUDGED", "reason": "no cases", "cases": []}
    rows = [judge_case(c) for c in cases]
    verdicts = {r["verdict"] for r in rows}
    verdict = "FAIL" if "FAIL" in verdicts else "NOT_JUDGED" if "NOT_JUDGED" in verdicts else "PASS"
    return {"verdict": verdict, "lokLines": sum(r["lok"] for r in rows),
            "casesWithFailedDispatch": sum(1 for r in rows if r["lok"]),
            "cases": [r for r in rows if r["lok"] or r["engine"] or r["verdict"] != "PASS"]}


def selftest() -> int:
    def case(messages, confirmed=True, n=1):
        return {"name": "x.ods", "messages": messages,
                "sheets": [{"text": {"selectAllConfirmed": confirmed}} for _ in range(n)]}
    lok = lambda count: {"message": f"warn:lok:42:1:desktop/source/lib/init.cxx:285: {LOK}", "count": count}
    eng = lambda n, how, count=1: {"message": f"oxsdk part-text: .uno:SelectAll not dispatched {n} time(s), {how} dispatched", "count": count}
    cases = {
        "nothing happened": ([], True, "PASS"),
        "two failures, one read redispatched twice": ([lok(2), eng(2, "then")], True, "PASS"),
        "two reads, one failure each": ([lok(2), eng(1, "then", 2)], True, "PASS"),
        "LOK says 2, the engine 1": ([lok(2), eng(1, "then")], True, "FAIL"),
        "the engine counts one LOK did not log": ([eng(1, "then")], True, "FAIL"),
        "never dispatched": ([lok(3), eng(3, "never")], True, "FAIL"),
        "consistent but a read unconfirmed": ([lok(1), eng(1, "then")], False, "FAIL"),
        "messages at the cap": ([{"message": f"m{i}", "count": 1} for i in range(CAP)], True, "NOT_JUDGED"),
    }
    ok = True
    for name, (messages, confirmed, want) in cases.items():
        got = judge_case(case(messages, confirmed))["verdict"]
        ok &= got == want
        print(f"{'PASS' if got == want else 'FAIL'} {name}: {got} (want {want})")
    empty = judge_report({"cases": []})["verdict"]
    ok &= empty == "NOT_JUDGED"
    print(f"{'PASS' if empty == 'NOT_JUDGED' else 'FAIL'} a report with no cases: {empty} (want NOT_JUDGED)")
    print("selftest PASS" if ok else "selftest FAIL")
    return 0 if ok else 1


def main(paths: list[str]) -> int:
    if paths == ["--selftest"]:
        return selftest()
    if not paths:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    worst = 0
    for path in paths:
        result = judge_report(json.load(open(path, encoding="utf-8")))
        print(json.dumps({"report": path.rsplit("/", 1)[-1], **result}, ensure_ascii=False))
        worst = max(worst, {"PASS": 0, "FAIL": 1, "NOT_JUDGED": 2}[result["verdict"]])
    return worst


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
