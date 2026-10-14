#!/usr/bin/env python3
"""Per-run table and per-criterion verdicts for the host-0.2.23 flagged-hold measurement.

Reads the raw `report-host-<browser>-owner16630.json` files in this directory (read, not retyped) and prints one row
per run plus a verdict per criterion of the fixed prediction.  `--self-test` feeds the same checks deliberately
broken copies of a real run and requires each criterion to turn red (a green from this tool alone proves nothing).

  python3 -I summarize_hold.py [--part first|followup]   # table + verdicts, exit 1 if any criterion is red or a run is missing/fatal
  python3 -I summarize_hold.py --self-test [--part first|followup]

Part `first` is the 3 s hold (README first section); part `followup` is the worst case `hold-2300` (README appended section).
`first` prints exactly what it printed when it was committed (summary-table.txt, self-test.txt).
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
FOLLOWUP = [("firefox", "control", "firefox-control2/report-host-firefox-owner16630.json", 1),
            ("firefox", "hold-2300", "firefox-hold2300/report-host-firefox-owner16630.json", 3),
            ("chrome", "control", "chrome-control2/report-host-chrome-owner16630.json", 1),
            ("chrome", "hold-2300", "chrome-hold2300/report-host-chrome-owner16630.json", 3)]
ARM_OF = {"control": "owner-sequence", "hold-3s": "hold-3s", "hold-2300": "hold-2300"}

# the prediction's numbers
MAX_REQUESTS = 2
MAX_READY_AFTER_KEYUP_MS = 2400
MAX_READY_FROM_KEYDOWN_MS = 5400
# the control: one press, the engine's named window (2,253-2,259 ms measured on 0.2.20-0.2.23)
CONTROL_WINDOW_MS = (2200, 2400)
# follow-up (hold-2300), fixed before its first run: ready 2.10-2.30 s after keyup, and in every run <= 2.4 s
W_READY_AFTER_KEYUP_BAND_MS = (2100, 2300)


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


def second_request_before_keyup(f: dict) -> bool:
    return len(f["requestTimes"]) >= 2 and f["releaseMs"] is not None and f["requestTimes"][1] < f["releaseMs"]


def keyup_minus_second_request(f: dict):
    return round(f["releaseMs"] - f["requestTimes"][1], 1) if len(f["requestTimes"]) >= 2 and f["releaseMs"] is not None else None


def hold2300_criteria(f: dict) -> dict[str, bool]:
    after = readyAfterKeyup(f)
    return {
        "W1 exactly 2 engine delete requests": f["requests"] == 2 and f["otherRequests"] == 0,
        "W2 worst case exercised: the 2nd request was sent before the keyup": second_request_before_keyup(f),
        "W3 0 characters deleted": f["verifiedDeletes"] == 0 and f["changedTrue"] == 0,
        "W4 0 refusals (no error, one generation, no toast)": f["refusals"] == 0 and f["generations"] == ["1"] and not f["toasts"],
        "W5 document unchanged (revision start == end)": f["revStart"] is not None and f["revStart"] == f["revEnd"],
        "W6 ready 2.10-2.30 s after keyup": after is not None and W_READY_AFTER_KEYUP_BAND_MS[0] <= after <= W_READY_AFTER_KEYUP_BAND_MS[1],
        "W7 ready <= 2.4 s after keyup": after is not None and after <= MAX_READY_AFTER_KEYUP_MS,
    }


def criteria_of(kind: str):
    return {"control": control_criteria, "hold-3s": hold_criteria, "hold-2300": hold2300_criteria}[kind]


def control_criteria(f: dict) -> dict[str, bool]:
    return {
        "K1 exactly 1 request, answered verified-boundary-noop": f["requests"] == 1 and f["noops"] == 1 and f["responses"] == 1,
        "K2 the engine's window is the ~2.25 s one": bool(f["waitedMs"]) and all(CONTROL_WINDOW_MS[0] <= (w or 0) <= CONTROL_WINDOW_MS[1] for w in f["waitedMs"]),
        "K3 page ready after the window (2.2-2.4 s from keydown)": f["finalReadyMs"] is not None and CONTROL_WINDOW_MS[0] <= f["finalReadyMs"] <= CONTROL_WINDOW_MS[1],
    }


def load(sets=SETS) -> list[tuple[str, str, list[dict]]]:
    out = []
    for browser, kind, rel, want in sets:
        path = HERE / rel
        report = json.loads(path.read_text())
        runs = [r for r in report["runs"]]
        if len(runs) != want or any(r["arm"] != ARM_OF[kind] for r in runs):
            raise SystemExit(f"{rel}: expected {want} {kind} run(s), found {[r['arm'] for r in runs]}")
        out.append((browser, kind, [facts(r) for r in runs]))
    return out


def table(sets) -> bool:
    ok = True
    followup = any(kind == "hold-2300" for _, kind, _ in sets)
    hdr = ("browser", "arm", "#", "keydowns(flagged)", "beforeinput", "engine req", "no-ops", "refusals", "deleted", "rev s->e",
           "keyup ms", "1st ready", "final ready", "ready<-keyup", "req at ms", "answers at ms")
    print(" | ".join(hdr + (("keyup-2nd req ms",) if followup else ())))
    for browser, kind, rows in sets:
        for f in rows:
            crit = criteria_of(kind)(f)
            ok &= (not f["fatal"]) and all(crit.values())
            print(" | ".join(str(v) for v in (
                browser, f["arm"], f["round"], f"{f['keydowns']}({f['flagged']})", f["beforeinput"], f["requests"], f["noops"], f["refusals"],
                f["verifiedDeletes"], f"{f['revStart']}->{f['revEnd']}", f["releaseMs"], f["firstReadyMs"], f["finalReadyMs"], readyAfterKeyup(f),
                f["requestTimes"], f["responseTimes"]) + ((keyup_minus_second_request(f),) if followup else ())))
    print()
    for browser, kind, rows in sets:
        names = criteria_of(kind)
        for name in names(rows[0]):
            res = [names(f)[name] for f in rows]
            print(f"{browser:8s} {kind:{9 if followup else 8}s} {name}: {'PASS' if all(res) else 'FAIL'} ({sum(res)}/{len(res)})")
        if kind == "hold-2300":
            for f in rows:
                if not second_request_before_keyup(f):
                    print(f"{browser:8s} {kind:9s} run {f['round']}: NOT EXERCISED (keyup {f['releaseMs']} ms is not after the 2nd request {f['requestTimes'][1:2]}); reported as such, not as a pass")
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


def self_test_followup(sets) -> bool:
    base = next(rows[0] for b, k, rows in sets if k == "hold-2300")
    ctl = next(rows[0] for b, k, rows in sets if k == "control")
    assert all(hold2300_criteria(base).values()) and all(control_criteria(ctl).values()), "the unbroken real runs must be green first"
    cases = [("W1 exactly 2 engine delete requests", lambda f: f.update(requests=3)),
             ("W1 exactly 2 engine delete requests", lambda f: f.update(requests=1)),
             ("W2 worst case exercised: the 2nd request was sent before the keyup", lambda f: f.update(releaseMs=f["requestTimes"][1] - 5)),
             ("W3 0 characters deleted", lambda f: f.update(verifiedDeletes=1)),
             ("W4 0 refusals (no error, one generation, no toast)", lambda f: f.update(refusals=1)),
             ("W5 document unchanged (revision start == end)", lambda f: f.update(revEnd="1")),
             ("W6 ready 2.10-2.30 s after keyup", lambda f: f.update(finalReadyMs=f["releaseMs"] + 2000)),
             ("W6 ready 2.10-2.30 s after keyup", lambda f: f.update(finalReadyMs=f["releaseMs"] + 2350)),
             ("W7 ready <= 2.4 s after keyup", lambda f: f.update(finalReadyMs=f["releaseMs"] + 2450))]
    good = True
    for name, mutate in cases:
        f = copy.deepcopy(base)
        mutate(f)
        red = not hold2300_criteria(f)[name]
        good &= red
        print(f"self-test {name}: {'red as required' if red else 'STAYED GREEN'}")
    f = copy.deepcopy(ctl)
    f.update(requests=0, noops=0, responses=0, finalReadyMs=40.0, waitedMs=[])
    red = all(not v for v in control_criteria(f).values())
    good &= red
    print(f"self-test control with no engine request at all (the instrument did not exercise C): {'red as required' if red else 'STAYED GREEN'}")
    # a run whose keyup comes before its second request must be printed NOT EXERCISED and make the whole table red
    import contextlib
    import io
    broken = [(b_, k_, [dict(copy.deepcopy(r), releaseMs=r["requestTimes"][1] - 5) if k_ == "hold-2300" and i == 0 else r for i, r in enumerate(rows)])
              for b_, k_, rows in sets]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        table_ok = table(broken)
    shown = "NOT EXERCISED" in buf.getvalue()
    red = (not table_ok) and shown
    good &= red
    print(f"self-test a hold-2300 run whose keyup precedes its second request: table red={not table_ok}, prints NOT EXERCISED={shown}: {'red as required' if red else 'STAYED GREEN'}")
    return good


if __name__ == "__main__":
    part = sys.argv[sys.argv.index("--part") + 1] if "--part" in sys.argv else "first"
    if part not in ("first", "followup"):
        raise SystemExit("--part must be first or followup")
    sets = load(SETS if part == "first" else FOLLOWUP)
    if "--self-test" in sys.argv:
        sys.exit(0 if (self_test(sets) if part == "first" else self_test_followup(sets)) else 1)
    sys.exit(0 if table(sets) else 1)
