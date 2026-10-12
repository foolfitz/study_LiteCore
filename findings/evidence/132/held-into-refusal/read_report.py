#!/usr/bin/env python3
"""One line per round of probe_held_into_refusal.py's report.json, plus the static lines.

  read_report.py DIR/report.json
"""

from __future__ import annotations

import json
import sys

report = json.load(open(sys.argv[1]))
for key in ("static", "staticAfter"):
    s = report.get(key) or {}
    print(key, {k: s.get(k) for k in ("hostVersion", "hostCommit", "buildId", "servedPage", "distPage")})
print("hold", report.get("hold"), "desk", report.get("deskRepeat"))
for run in report["runs"]:
    head = f'{run["browser"]:8} {run["arm"]:11} r{run["round"]}'
    if run.get("fatal"):
        print(head, "FATAL", run["fatal"].strip().splitlines()[-1])
        continue
    s, srv, lim = run["summary"], run.get("server", {}), run.get("limit", {})
    print(head,
          f'keys {s["keydowns"]} (repeat {s["repeatsFlagged"]}, sink {s["keydownsIntoSink"]}, else {s["keydownsElsewhere"]})',
          f'beforeinput {s["beforeinputs"]} deletes {s["deletesSeen"]}',
          f'refusals {s["refusals"]} at {s["refusalsMs"]} ready-new-gen {s["readyInNewGenerationMs"]}',
          f'gens {s["generations"]} limit {lim.get("limit")} saved-at {s["limitSavedMs"]}',
          f'| server marks {srv.get("marks")} firstDiff {srv.get("firstDiffFromOriginal")} '
          f'charDelta {srv.get("charDelta")} paras {srv.get("paragraphs")}/{srv.get("paragraphsOriginal")} '
          f'same {srv.get("sameAsOriginal")}',
          f'| settle {run.get("settle")} save {(run.get("save") or {}).get("outcome")}')
    for toast in s["toasts"]:
        print("    toast:", toast)
