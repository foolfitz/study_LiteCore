#!/usr/bin/env python3
"""Opus seat 1 Q6(2)/Q7.1 (undo grouping): per op of the measured step, does the .uno:Undo payload read at
return differ from the one read at the previous op's return (or, for the first op, the step's `before`)?
Prints, per op: whether the payload changed, the action count and the top comment.

  python3 -I read_grouping.py CELL.jsonl
"""
import json
import sys


def top(payload):
    try:
        acts = json.loads(payload).get('actions') or []
    except Exception:  # noqa: BLE001
        return None, f'<unparsed {payload[:40]!r}>'
    if not acts:
        return 0, None
    return len(acts), acts[0].get('comment')


def main(path):
    recs = [json.loads(line) for line in open(path) if line.strip()]
    by = {}
    for r in recs:
        by.setdefault(r['rec'], []).append(r)
    if 'fatal' in by or 'done' not in by or 'measured' not in by:
        print(f'{path}: unclean ({sorted(by)})')
        return 1
    m = by['measured'][0]
    prev = m['before']['undo']
    same = 0
    for i, op in enumerate(m['ops']):
        cur = op['atReturn']['undo']
        n, comment = top(cur)
        changed = cur != prev
        same += not changed
        print(f'  op {i + 1:2} {op["op"]}: undo payload {"CHANGED  " if changed else "UNCHANGED"} actions {n} top {comment!r}')
        prev = cur
    saved = (by.get('saved') or [{}])[0]
    print(f'{path.split("/")[-1]}: {len(m["ops"])} ops, {same} with the payload byte-identical to the previous read; '
          f'saved ok {saved.get("ok")}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
