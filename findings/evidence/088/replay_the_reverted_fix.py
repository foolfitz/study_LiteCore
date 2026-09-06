#!/usr/bin/env python3
"""Does the reverted 088 residue fix still fail 4a, now that the instrument
has been corrected?

The fix -- emptying the live region when `aria-activedescendant` already points
at a node carrying the same text -- was reverted on 2026-09-04 because it turned
4a terms 4 and 8 red.  The finding recorded that at least one of those two reds
was the INSTRUMENT, and left the disposition to adjudication rather than letting
the drafting party change a probe to make its own fix pass.

Adjudication happened (plan amendment 2026-09-05, Rulings 1 and 2).  This asks
the question the finding left open, over the record that was already held.

IT IS A REPLAY, NOT A RUN.  The held record predates Ruling 1 and carries no
`target.axNodeId`, so `hydrate()` -- imported from the red-case script, not
retyped -- reconstructs it from `activeDescendantRef`.  A fresh run would move
the product page's sha256 and void the banked soak runs, so it must not be taken
while the cutover gate is counting.

Re-runnable:  python3 findings/evidence/088/replay_the_reverted_fix.py
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "red_cases", ROOT / "findings/evidence/gate-4a-reading-rule/red_cases.py")
RC = importlib.util.module_from_spec(spec)
sys.modules["red_cases"] = RC
spec.loader.exec_module(RC)

HELD = ROOT / "findings/evidence/088/4a-with-live-region-silenced-TERM4-AND-8-RED.json"


def verdict(record: dict) -> dict:
    control = json.loads(RC.CONTROL.read_text(encoding="utf-8"))
    return RC.CHECK.judge([record] * 3, control, None)


def main() -> int:
    held = json.loads(HELD.read_text(encoding="utf-8"))
    rows = [
        ("the record as taken, under today's judge", held),
        ("the same record, hydrated and reread under Ruling 1",
         RC.reread(RC.hydrate(held))),
    ]
    failed = False
    for label, record in rows:
        v = verdict(record)
        reds = [k for k, t in v["terms"].items() if not t.get("ok")]
        print(f"{label}")
        print(f"    ok={v['ok']}  red={reds or 'none'}")
        print(f"    readings: {record.get('axReadings')}")
    # Non-vacuity: the two rows must DISAGREE, or this script is measuring
    # nothing and would print the same thing whatever the judge did.
    a = verdict(rows[0][1])["ok"]
    b = verdict(rows[1][1])["ok"]
    if a == b:
        print("\nREFUSED: both rows agree, so this replay distinguishes "
              "nothing about the amendment")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
