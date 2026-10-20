#!/usr/bin/env python3
"""Opus seat, review 1, A10: STATE_CHANGED keys on time (before an op's first poll) vs late (after it), uni1ai.
Usage: python3 -I a10_state_split.py <ordered-commands dir>"""
import collections, json, pathlib, sys
oc = pathlib.Path(sys.argv[1])
ontime, late = collections.Counter(), collections.Counter()
for f in sorted((oc / 'out-n1').glob('*/uni1ai-r*.jsonl')):
    rec = [json.loads(x) for x in f.read_text().splitlines() if '"measured"' in x][0]
    for o in rec['ops']:
        hi = o['returnedMs'] + o['firstPollAfterReturnMs'] + 2.0
        for c in rec['callbacks']:
            if c['type'] == 'LOK_CALLBACK_STATE_CHANGED' and o['startMs'] <= c['t'] <= hi:
                ontime[c['payload'].split('=')[0][:40]] += 1
        for c in o['lateCallbacks']:
            if c['type'] == 'LOK_CALLBACK_STATE_CHANGED':
                late[c['payload'].split('=')[0][:40]] += 1
print('on time (before the first poll):', dict(ontime.most_common()))
print('late (after the first poll):    ', dict(late.most_common(25)))
print('keys in both:', sorted(set(ontime) & set(late)))
