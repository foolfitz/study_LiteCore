#!/usr/bin/env python3
"""Codex seat 1, question 1 (the recording blind spot): in the committed N1 run, does any reply-type
callback arrive after an op's first poll but OUTSIDE the op's 1500 ms `lateCallbacks` window?

Reads every uni1ai cell's measured record.  Its `callbacks` list is the whole measured step, timed from
the step's start (the clock of the ops' startMs/returnedMs).  Inside the window the reader's own
index-based `lateCallbacks` is authoritative; this script only looks past it.

The first poll's time is estimated as returnedMs + firstPollAfterReturnMs.  That estimate is EARLY by
the time of the at-return reads: `returnedMs` is stamped when the LOK call returns (oc_native.cpp:303),
`firstPollAfterReturnMs` is measured from `opReturnedMs`, stamped after readSel()/undoValues()
(oc_native.cpp:479).  The first version of this script counted callbacks just after the estimate as
"inside the window" and found 115 that the reader's index places before the first poll; that count
was this script's error (kept in the disposition).  An early estimate only widens the window here, so
OUTSIDE (later than estimate + 1500 ms) stays conservative.

  python3 -I n1_outside_window.py OUT_N1_DIR
"""
import json
import pathlib
import sys

REPLY_TYPES = {'LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR', 'LOK_CALLBACK_TEXT_SELECTION',
               'LOK_CALLBACK_TEXT_SELECTION_START', 'LOK_CALLBACK_TEXT_SELECTION_END',
               'LOK_CALLBACK_UNO_COMMAND_RESULT', 'LOK_CALLBACK_INVALIDATE_TILES'}


def main(out):
    cells = sorted(out.glob('*/uni1ai-r*.jsonl'))
    if not cells:
        print(f'no uni1ai cells under {out}')
        return 2
    ops_seen = outside = later = 0
    for path in cells:
        for line in path.read_text().splitlines():
            rec = json.loads(line)
            if rec.get('rec') != 'measured':
                continue
            ops = rec['ops']
            for i, op in enumerate(ops):
                ops_seen += 1
                first = op['returnedMs'] + op['firstPollAfterReturnMs']
                end = ops[i + 1]['startMs'] if i + 1 < len(ops) else float('inf')
                for c in rec['callbacks']:
                    if not (first < c['t'] < end) or c['type'] not in REPLY_TYPES:
                        continue
                    if c['t'] - first > 1500:
                        outside += 1
                        print(f'OUTSIDE {path.parent.name}/{path.name} op {i} {c["type"]} +{c["t"] - first:.1f} ms')
                    else:
                        later += 1
    print(f'cells {len(cells)}, ops {ops_seen}; reply-type callbacks later than the estimated first poll + 1500 ms: '
          f'{outside} (those within it, {later}, are the reader\'s domain: its index-based lateCallbacks)')
    return 0


if __name__ == '__main__':
    sys.exit(main(pathlib.Path(sys.argv[1])))
