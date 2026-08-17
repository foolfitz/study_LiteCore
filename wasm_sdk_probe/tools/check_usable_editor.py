#!/usr/bin/env python3
"""Does the acceptance checklist point at things that exist?

Written 2026-08-17, after the short-term goal was described as 零碎 and the
stocktake found no written definition of done.

The obvious response -- write a prose page listing what a usable editor needs --
is the wrong one, and this tree already knows why: a document that cannot be
shown to be wrong is not evidence.  A checklist whose lines are prose drifts the
moment the code moves, and nobody notices, which is the same failure mode as the
`summary.json` that still said "no verdict" a day after the verdict (finding
044).

So the checklist is data, and every line has to name something real:

  * `check`   -- a check id in tools/run_e2_c_product_path.py
  * `queue`   -- an item id in e2/relink-queue-v3.json
  * `finding` -- a numbered file under findings/

This tool resolves all three, and fails when a reference does not resolve.
"Done" for the product goal then means: this is green, every `done` row's check
is green in the runner, and the `blocked` rows' queue items have shipped.

Usage:
  check_usable_editor.py             # resolve every reference, exit 1 on a miss
  check_usable_editor.py --self-test # prove it can say no
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
WORKSPACE = PROJECT.parent

CHECKLIST = PROJECT / "e2" / "usable-editor-checklist.json"
RUNNER = PROJECT / "tools" / "run_e2_c_product_path.py"
QUEUE = PROJECT / "e2" / "relink-queue-v3.json"
FINDINGS = WORKSPACE / "findings"

# The vocabulary lives in the checklist's own `statuses` block, not here.  It
# was duplicated for about ten minutes on 2026-08-17 and immediately drifted:
# adding `partial` to the file left the tool rejecting it, which is the right
# failure but for the wrong reason -- two sources of truth for one list.
def valid_statuses(checklist: dict) -> tuple:
    return tuple(checklist.get("statuses", {}))


def check_ids(runner_text: str) -> set[str]:
    """Every check id the product-path runner can emit.

    Read out of the source rather than by running it: the runner needs a browser
    and several minutes, and this has to be cheap enough to sit in the static
    suite.
    """
    return set(re.findall(r'''\bcheck\(\s*["']([a-z0-9-]+)["']''', runner_text))


def resolve(checklist: dict, runner_text: str, queue: dict,
            findings_dir: Path) -> dict:
    known_checks = check_ids(runner_text)
    known_queue = {item["id"] for item in queue.get("items", [])}
    known_findings = {path.name[:3] for path in findings_dir.glob("*.md")
                      if path.name[:3].isdigit()}

    statuses = valid_statuses(checklist)
    rows, problems = [], []
    if not statuses:
        problems.append("the checklist declares no `statuses` vocabulary")
    for capability in checklist.get("capabilities", []):
        cid = capability.get("id", "?")
        if capability.get("status") not in statuses:
            problems.append(f"{cid}: status {capability.get('status')!r} is not "
                            f"one of {statuses}")
        evidence = capability.get("evidence") or []
        if not evidence:
            # A row with no evidence is the prose this file exists to prevent.
            problems.append(f"{cid}: names no check, queue item or finding")
        resolved = []
        for item in evidence:
            (kind, name), = item.items()
            if kind == "check":
                ok = name in known_checks
                where = "tools/run_e2_c_product_path.py"
            elif kind == "queue":
                ok = name in known_queue
                where = "e2/relink-queue-v3.json"
            elif kind == "finding":
                ok = name in known_findings
                where = "findings/"
            else:
                ok, where = False, "unknown evidence kind"
            if not ok:
                problems.append(f"{cid}: {kind} {name!r} does not exist in {where}")
            resolved.append({"kind": kind, "name": name, "resolves": ok})
        rows.append({"id": cid, "status": capability.get("status"),
                     "evidence": resolved})

    by_status = {s: [r["id"] for r in rows if r["status"] == s]
                 for s in statuses}
    return {
        "schemaVersion": 1,
        "release": "usable-editor-acceptance",
        "capabilities": rows,
        "byStatus": by_status,
        "problems": problems,
        "ok": not problems,
    }


def load() -> tuple[dict, str, dict]:
    return (json.loads(CHECKLIST.read_text(encoding="utf-8")),
            RUNNER.read_text(encoding="utf-8"),
            json.loads(QUEUE.read_text(encoding="utf-8")))


def self_test() -> int:
    failures: list[str] = []

    def verify(name: str, condition: bool, detail: str = "") -> None:
        print(f"  {'ok  ' if condition else 'FAIL'}  {name}"
              + (f"  -- {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(name)

    checklist, runner_text, queue = load()
    report = resolve(checklist, runner_text, queue, FINDINGS)
    verify("the checklist as it stands resolves", report["ok"],
           json.dumps(report["problems"], ensure_ascii=False))

    # The extractor has to actually find checks, or every `check:` reference
    # would resolve to nothing and the run above would be red for one reason
    # while looking red for another.
    found = check_ids(runner_text)
    verify("the runner's check ids are extractable", len(found) >= 5,
           f"found {len(found)}")

    # Three negative controls, one per evidence kind.  Each must be REJECTED --
    # a reference that resolves to nothing is exactly what this tool exists to
    # catch, and if any of them passes, the corresponding kind is unchecked.
    for kind, bogus in (("check", "no-such-check-anywhere"),
                        ("queue", "no-such-queue-item"),
                        ("finding", "999")):
        broken = json.loads(json.dumps(checklist))
        broken["capabilities"][0]["evidence"] = [{kind: bogus}]
        verify(f"a {kind} that does not exist is caught",
               not resolve(broken, runner_text, queue, FINDINGS)["ok"])

    # And a row with no evidence at all -- prose wearing a checklist's clothes.
    empty = json.loads(json.dumps(checklist))
    empty["capabilities"][0]["evidence"] = []
    verify("a row with no evidence is caught",
           not resolve(empty, runner_text, queue, FINDINGS)["ok"])

    # A status outside the declared set, so the vocabulary cannot drift either.
    drifted = json.loads(json.dumps(checklist))
    drifted["capabilities"][0]["status"] = "mostly-fine"
    verify("an undeclared status is caught",
           not resolve(drifted, runner_text, queue, FINDINGS)["ok"])

    # And the vocabulary itself: with `statuses` removed there is nothing to
    # validate against, and silently accepting every status would be worse than
    # rejecting every one.
    vocabulary_gone = json.loads(json.dumps(checklist))
    vocabulary_gone.pop("statuses", None)
    verify("a checklist with no status vocabulary is caught",
           not resolve(vocabulary_gone, runner_text, queue, FINDINGS)["ok"])

    total = 8
    print(f"\nself-test: {total - len(failures)}/{total} checks moved the verdict")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    checklist, runner_text, queue = load()
    report = resolve(checklist, runner_text, queue, FINDINGS)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
