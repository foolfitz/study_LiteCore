#!/usr/bin/env python3
"""Per-run table and per-criterion verdicts for the host-0.2.23 flagged-hold measurement.

Reads the raw `report-host-<browser>-owner16630.json` files in this directory (read, not retyped) and prints one row
per run plus a verdict per criterion of the fixed prediction.  `--self-test` feeds the same checks deliberately
broken copies of a real run and requires each criterion to turn red (a green from this tool alone proves nothing).

  python3 -I summarize_hold.py            # table + verdicts, exit 1 if any criterion is red or a run is missing/fatal
  python3 -I summarize_hold.py --self-test
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SETS = [("firefox", "control", "firefox-control/report-host-firefox-owner16630.json", 1),
        ("firefox", "hold-3s", "firefox-hold/report-host-firefox-owner16630.json", 3),
        ("chrome", "control", "chrome-control/report-host-chrome-owner16630.json", 1),
        ("chrome", "hold-3s", "chrome-hold/report-host-chrome-owner16630.json", 3)]

# the prediction's numbers
MAX_REQUESTS = 2
MAX_READY_AFTER_KEYUP_MS = 2400
MAX_READY_FROM_KEYDOWN_MS = 5400
# the control: one press, the engine's named window (2,253-2,259 ms measured on 0.2.20-0.2.23)
CONTROL_WINDOW_MS = (2200, 2400)


def facts(run: dict) -> dict:
    s = run["summary"]
    resp = s["editorResponses"]
    reqs = [r for r in s["nonPaintRequests"] if (r.get("op") or "").startswith("editor")]
    other = [r for r in s["nonPaintRequests"] if not (r.get("op") or "").startswith("editor")]
    last = (run.get("settle") or {}).get("last") or {}
    ready = s["readyAgainMs"]
    return {
        "arm": run["arm"], "round": run["round"], "fatal": bool(run.get("fatal")),
        "keydowns": s["keydowns"], "flagged": s["repeatsFlagged"], "beforeinput": s["beforeinputs"],
        "requests": len(reqs), "otherRequests": len(other), "responses": len(resp),
        "noops": sum(1 for r in resp if r.get("completion") == "verified-boundary-noop"),
        "refusals": sum(1 for r in resp if r.get("ok") is False or r.get("err")),
        "verifiedDeletes": s["verifiedDeletes"], "changedTrue": sum(1 for r in resp if r.get("changed")),
        "revEnd": last.get("rev"), "revStart": (run.get("stateBeforeKey") or {}).get("rev"),
        "releaseMs": s["releaseMs"], "firstReadyMs": ready[0] if ready else None, "finalReadyMs": ready[-1] if ready else None,
        "generations": s["generations"], "toasts": s["toasts"], "limit": last.get("limit"),
        "waitedMs": [(r.get("boundaryNoop") or {}).get("waitedMs") for r in resp],
        "requestTimes": [r["t"] for r in reqs], "responseTimes": [r["t"] for r in resp],
    }


def readyAfterKeyup(f: dict):
    return None if f["finalReadyMs"] is None or f["releaseMs"] is None else round(f["finalReadyMs"] - f["releaseMs"], 1)


def hold_criteria(f: dict) -> dict[str, bool]:
    after = readyAfterKeyup(f)
    return {
        "C1 engine delete requests <= 2": f["requests"] <= MAX_REQUESTS and f["otherRequests"] == 0,
        "C2 0 characters deleted": f["verifiedDeletes"] == 0 and f["changedTrue"] == 0,
        "C3 0 refusals (no error, one generation, no toast)": f["refusals"] == 0 and f["generations"] == ["1"] and not f["toasts"],
        "C4 document unchanged (revision start == end)": f["revStart"] is not None and f["revStart"] == f["revEnd"],
        "C5 ready <= 2.4 s after keyup": after is not None and after <= MAX_READY_AFTER_KEYUP_MS,
        "C6 ready <= 5.4 s from keydown": f["finalReadyMs"] is not None and f["finalReadyMs"] <= MAX_READY_FROM_KEYDOWN_MS,
    }


def control_criteria(f: dict) -> dict[str, bool]:
    return {
        "K1 exactly 1 request, answered verified-boundary-noop": f["requests"] == 1 and f["noops"] == 1 and f["responses"] == 1,
        "K2 the engine's window is the ~2.25 s one": bool(f["waitedMs"]) and all(CONTROL_WINDOW_MS[0] <= (w or 0) <= CONTROL_WINDOW_MS[1] for w in f["waitedMs"]),
        "K3 page ready after the window (2.2-2.4 s from keydown)": f["finalReadyMs"] is not None and CONTROL_WINDOW_MS[0] <= f["finalReadyMs"] <= CONTROL_WINDOW_MS[1],
    }


def load() -> list[tuple[str, str, list[dict]]]:
    out = []
    for browser, kind, rel, want in SETS:
        path = HERE / rel
        report = json.loads(path.read_text())
        runs = [r for r in report["runs"]]
        if len(runs) != want or any(r["arm"] != ("owner-sequence" if kind == "control" else "hold-3s") for r in runs):
            raise SystemExit(f"{rel}: expected {want} {kind} run(s), found {[r['arm'] for r in runs]}")
        out.append((browser, kind, [facts(r) for r in runs]))
    return out


def table(sets) -> bool:
    ok = True
    hdr = ("browser", "arm", "#", "keydowns(flagged)", "beforeinput", "engine req", "no-ops", "refusals", "deleted", "rev s->e",
           "keyup ms", "1st ready", "final ready", "ready<-keyup", "req at ms", "answers at ms")
    print(" | ".join(hdr))
    for browser, kind, rows in sets:
        for f in rows:
            crit = control_criteria(f) if kind == "control" else hold_criteria(f)
            ok &= (not f["fatal"]) and all(crit.values())
            print(" | ".join(str(v) for v in (
                browser, f["arm"], f["round"], f"{f['keydowns']}({f['flagged']})", f["beforeinput"], f["requests"], f["noops"], f["refusals"],
                f["verifiedDeletes"], f"{f['revStart']}->{f['revEnd']}", f["releaseMs"], f["firstReadyMs"], f["finalReadyMs"], readyAfterKeyup(f),
                f["requestTimes"], f["responseTimes"])))
    print()
    for browser, kind, rows in sets:
        names = (control_criteria if kind == "control" else hold_criteria)
        for name in names(rows[0]):
            res = [names(f)[name] for f in rows]
            print(f"{browser:8s} {kind:8s} {name}: {'PASS' if all(res) else 'FAIL'} ({sum(res)}/{len(res)})")
    return ok


def self_test(sets) -> bool:
    base = next(rows[0] for b, k, rows in sets if k == "hold-3s")
    ctl = next(rows[0] for b, k, rows in sets if k == "control")
    assert all(hold_criteria(base).values()) and all(control_criteria(ctl).values()), "the unbroken real runs must be green first"
    cases = [("C1 engine delete requests <= 2", lambda f: f.update(requests=3)),
             ("C2 0 characters deleted", lambda f: f.update(verifiedDeletes=1)),
             ("C3 0 refusals (no error, one generation, no toast)", lambda f: f.update(refusals=1)),
             ("C4 document unchanged (revision start == end)", lambda f: f.update(revEnd="1")),
             ("C5 ready <= 2.4 s after keyup", lambda f: f.update(finalReadyMs=f["releaseMs"] + 2500)),
             ("C6 ready <= 5.4 s from keydown", lambda f: f.update(finalReadyMs=5500, releaseMs=3100))]
    good = True
    for name, mutate in cases:
        f = copy.deepcopy(base)
        mutate(f)
        red = not hold_criteria(f)[name]
        good &= red
        print(f"self-test {name}: {'red as required' if red else 'STAYED GREEN'}")
    f = copy.deepcopy(ctl)
    f.update(requests=0, noops=0, responses=0, finalReadyMs=40.0, waitedMs=[])
    red = all(not v for v in control_criteria(f).values())
    good &= red
    print(f"self-test control with no engine request at all (the instrument did not exercise C): {'red as required' if red else 'STAYED GREEN'}")
    return good


if __name__ == "__main__":
    sets = load()
    if "--self-test" in sys.argv:
        sys.exit(0 if self_test(sets) else 1)
    sys.exit(0 if table(sets) else 1)
