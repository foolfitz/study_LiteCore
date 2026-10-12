#!/usr/bin/env python3
"""Reader for criterion 133-B (SPEC-M3-autosave §9.20), written before any 133-B run.

Reads one or more reports of `wasm_sdk_probe/tools/probe_k8_frozen_recovery.py` and
applies, to every run:
  (a) positive control: `autosaveNow hidden` and `req save` both before freezeAt + 1000
      (a save really was in flight across the freeze);
  (b) save1State.state == "ready"; host.saves[-1] is manual, its last attempt 204;
      serverAfter.sha256 == host.saves[-1].sha256; copiesAfter == []; every earlier
      save is auto;
  (c) no `blockQueue` and no `fail` of a `save` in the diag;
  (d) a `rearm` followed within 10 000 ms by a reply to the same request id
      (`respIn`/`resp`) = the guard burned in this run.
Series: every run passes (a)-(c) and the guard burned >= 1 -> HOLDS; all pass but 0
burns -> EXTEND (run 6 more, at most 12 in all); 12 or more runs, all pass, 0 burns ->
NOT_ESTABLISHED; any run failing (a)-(c) -> FAIL.

Times: diag rows carry Date.now(); freezeAt/thawAt are host-relative (Date.now() -
host.started), so a row's time is converted with the run's own host.started.

Red case (committed before any 133-B run): the first probe report,
../m3-locks/k8-recoverable-2026-10-12/probe-2026-10-12T121440+0000.json, must read FAIL
(runs 1 and 3 fail (b) and (c)).

Usage:  python3 -I judge_133b.py REPORT.json [REPORT.json ...]
Prints one line per run and a SUMMARY line; exit 0 only for HOLDS.  Writes nothing.
"""
import json
import sys
from pathlib import Path


def rows(run):
    started = (run.get("host") or {}).get("started")
    out = []
    for row in run.get("diag") or []:
        t = row[1] if len(row) > 1 else None
        rel = t - started if isinstance(t, (int, float)) and isinstance(started, (int, float)) else None
        out.append((row[0].replace("LCDIAG ", ""), rel, row[2:]))
    return out


def judge_run(run):
    problems = []
    diag = rows(run)
    freeze = run.get("freezeAt")
    if not isinstance(freeze, (int, float)):
        problems.append("no freezeAt")
        freeze = None
    # (a)
    hidden = [t for kind, t, args in diag if kind == "autosaveNow" and args[:1] == ["hidden"]]
    reqs = [(t, args[1]) for kind, t, args in diag if kind == "req" and args[:1] == ["save"]]
    if freeze is None or not any(t is not None and t < freeze + 1000 for t in hidden):
        problems.append(f"(a) no autosaveNow hidden before freezeAt+1000 (hidden at {hidden})")
    early = [(t, rid) for t, rid in reqs if t is not None and freeze is not None and t < freeze + 1000]
    if not early:
        problems.append(f"(a) no req save before freezeAt+1000 (save requests at {[t for t, _ in reqs]})")
    # (b)
    state = (run.get("save1State") or {}).get("state")
    if state != "ready":
        problems.append(f"(b) save1State.state {state!r}")
    saves = (run.get("host") or {}).get("saves") or []
    if not saves:
        problems.append("(b) host.saves empty")
    else:
        last = saves[-1]
        attempts = last.get("attempts") or []
        if last.get("trigger") != "manual":
            problems.append(f"(b) last save trigger {last.get('trigger')!r}")
        if not attempts or attempts[-1].get("status") != 204:
            problems.append(f"(b) last attempt {attempts[-1].get('status') if attempts else None}")
        if (run.get("serverAfter") or {}).get("sha256") != last.get("sha256"):
            problems.append("(b) serverAfter.sha256 != last save's sha256")
        if any(s.get("trigger") != "auto" for s in saves[:-1]):
            problems.append(f"(b) earlier triggers {[s.get('trigger') for s in saves[:-1]]}")
    if run.get("copiesAfter") != []:
        problems.append(f"(b) copiesAfter {run.get('copiesAfter')!r}")
    # (c)
    if any(kind == "blockQueue" for kind, _, _ in diag):
        problems.append("(c) blockQueue in diag")
    if any(kind == "fail" and args[:1] == ["save"] for kind, _, args in diag):
        problems.append("(c) fail save in diag")
    # (d)
    burned = 0
    for kind, t, args in diag:
        if kind != "rearm" or t is None:
            continue
        rid = args[1] if len(args) > 1 else None
        replies = [t2 for k2, t2, a2 in diag
                   if t2 is not None and t <= t2 <= t + 10000
                   and ((k2 == "respIn" and a2[:1] == [rid]) or (k2 == "resp" and len(a2) > 1 and a2[1] == rid))]
        if replies:
            burned += 1
    return problems, burned, len([1 for kind, _, _ in diag if kind == "rearm"])


def main(paths):
    runs = []
    for path in paths:
        report = json.loads(Path(path).read_text())
        for index, run in enumerate(report.get("runs", [])):
            runs.append((Path(path).name, index + 1, run))
    failed, burns = 0, 0
    for name, index, run in runs:
        problems, burned, rearms = judge_run(run)
        failed += bool(problems)
        burns += burned
        print(f"{name} run {index}: {'PASS' if not problems else 'FAIL'}  rearm {rearms}  guard burned {burned}"
              f"  thaw {run.get('thawAt')}" + ("" if not problems else "  :: " + "; ".join(problems)))
    if not runs:
        verdict = "FAIL (no runs)"
    elif failed:
        verdict = "FAIL"
    elif burns >= 1 and len(runs) >= 6:
        verdict = "HOLDS"
    elif len(runs) >= 12:
        verdict = "NOT_ESTABLISHED (12+ runs, the reply won every race)"
    else:
        verdict = "EXTEND" if burns == 0 else "INCOMPLETE (fewer than 6 runs)"
    print(f"SUMMARY 133-B: {verdict}  runs {len(runs)}  failing {failed}  guard burns {burns}")
    return 0 if verdict == "HOLDS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
