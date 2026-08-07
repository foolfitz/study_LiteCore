#!/usr/bin/env python3
"""Judge the finding 021 native caret-tracking run from its raw callback stream.

Applies the same freshness rule the WASM harness uses: a format value only
counts as a reading of the paragraph the caret is in if a STATE_CHANGED payload
for that command arrived while the caret was there.  Anything else is the
previous paragraph's value still sitting in the cache.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

WATCHED = (".uno:DefaultBullet", ".uno:DefaultNumbering", ".uno:StyleApply")

# Judged as transitions, not as absolute per-paragraph values.
#
# Two reasons.  Core only broadcasts STATE_CHANGED when a value changes, so
# moving between two items of the same list legitimately produces no callback
# and "not fresh" there means nothing is wrong.  And the heading's own list
# state is not something to assert from the fixture: a Heading 1 paragraph can
# report DefaultNumbering true through outline numbering.  The first version of
# this table asserted heading.inList == False, which is the same guessed-constant
# mistake this experiment exists to correct.
#
# These two moves are the ones the fixture guarantees must change, and they are
# exactly what the WASM run failed to observe.
TRANSITIONS = (
    {"name": "into-list", "frm": "body-paragraph", "to": "list-item", "inList": True},
    {"name": "out-of-list", "frm": "list-item", "to": "after-list", "inList": False},
)


def parse_state(payload: str) -> tuple[str, Any] | None:
    for command in WATCHED:
        if payload == f"{command}=true":
            return command, True
        if payload == f"{command}=false":
            return command, False
        if payload.startswith(f"{command}="):
            return command, payload[len(command) + 1:]
    return None


def analyze(path: Path) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    phase = None
    cache: dict[str, Any] = {}

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        stage = record.get("stage")
        if stage == "phase":
            phase = record.get("name")
            continue
        if stage in ("observe", "dispatch"):
            if stage == "observe":
                current = {
                    "phase": phase,
                    "method": record.get("method", phase),
                    "position": record.get("position"),
                    "arrivals": [],
                }
                steps.append(current)
            continue
        if stage in ("measured", "observed"):
            if current is not None:
                current["cacheAfter"] = dict(cache)
                current = None
            continue

        if record.get("name") == "LOK_CALLBACK_STATE_CHANGED":
            parsed = parse_state(record.get("payload", ""))
            if parsed is None:
                continue
            command, value = parsed
            cache[command] = value
            if current is not None:
                current["arrivals"].append({"command": command, "value": value})

    for step in steps:
        step["fresh"] = len(step["arrivals"]) > 0
        step.setdefault("cacheAfter", {})
        bullet = step["cacheAfter"].get(".uno:DefaultBullet")
        number = step["cacheAfter"].get(".uno:DefaultNumbering")
        step["readInList"] = bool(bullet) or bool(number)
        step["style"] = step["cacheAfter"].get(".uno:StyleApply")

    by_method: dict[str, Any] = {}
    for step in steps:
        method = step["method"] or "unknown"
        entry = by_method.setdefault(method, {
            "steps": 0,
            "fresh": 0,
            "positions": [],
            "tracksListMembership": None,
        })
        entry["steps"] += 1
        entry["fresh"] += 1 if step["fresh"] else 0
        entry["positions"].append({
            "position": step["position"],
            "fresh": step["fresh"],
            "arrivals": len(step["arrivals"]),
            "readInList": step["readInList"],
            "style": step["style"],
        })

    for entry in by_method.values():
        by_position = {item["position"]: item for item in entry["positions"]}
        results = []
        for transition in TRANSITIONS:
            source = by_position.get(transition["frm"])
            target = by_position.get(transition["to"])
            if source is None or target is None:
                results.append({"name": transition["name"], "observed": False,
                                "reason": "position not visited"})
                continue
            results.append({
                "name": transition["name"],
                "observed": True,
                # The move must both produce a reading and produce the right
                # one; a correct value with no callback behind it is the
                # previous paragraph's value, not a reading of this one.
                "fresh": target["fresh"],
                "readInList": target["readInList"],
                "expectedInList": transition["inList"],
                "met": bool(target["fresh"])
                and target["readInList"] == transition["inList"],
            })
        entry["transitions"] = results
        judged = [item for item in results if item.get("observed")]
        entry["tracksListMembership"] = (
            bool(judged) and all(item["met"] for item in judged)
        )
        entry["transitionsJudged"] = len(judged)

    return {
        "schemaVersion": 1,
        "release": "E2-A-finding-021-native-caret-tracking",
        "source": str(path),
        "steps": steps,
        "byMethod": by_method,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("callbacks", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.callbacks)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"{'method':22} {'steps':>5} {'fresh':>5}  tracksListMembership")
    for method, entry in result["byMethod"].items():
        print(f"{method:22} {entry['steps']:>5} {entry['fresh']:>5}  "
              f"{entry['tracksListMembership']}")
    print()
    for step in result["steps"]:
        print(f"  {str(step['method']):22} {str(step['position']):15} "
              f"fresh={str(step['fresh']):5} arrivals={len(step['arrivals']):2} "
              f"inList={step['readInList']} style={step['style']!r}")


if __name__ == "__main__":
    main()
