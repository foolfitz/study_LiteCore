#!/usr/bin/env python3
"""Opus seat, review 1, A9: in out-n1's d4 (uni1ai: one op per poll, anyInput = reply pending), where does
the .uno:Bold state and the UNO_COMMAND_RESULT for the Bold op land relative to the op's first poll?
Usage: python3 -I a9_bold_state.py <ordered-commands dir>"""
import json, pathlib, sys
oc = pathlib.Path(sys.argv[1])
for r in range(1, 6):
    rec = [json.loads(x) for x in (oc / 'out-n1' / 'd4' / f'uni1ai-r{r}.jsonl').read_text().splitlines() if '"measured"' in x][0]
    for o in rec['ops']:
        if not o['op'].startswith('U.uno:Bold'):
            continue
        fp = o['returnedMs'] + o['firstPollAfterReturnMs']
        before = [(round(c['t'] - o['returnedMs'], 3), c['type'][13:], c['payload'][:70]) for c in rec['callbacks']
                  if o['startMs'] <= c['t'] <= fp + 2.0 and c['type'] in ('LOK_CALLBACK_UNO_COMMAND_RESULT', 'LOK_CALLBACK_STATE_CHANGED')]
        late = [(round(c['t'], 1), c['payload'][:40]) for c in o['lateCallbacks'] if 'Bold' in c['payload']]
        print(f'r{r} {o["op"][:12]} firstPollAfterReturn={o["firstPollAfterReturnMs"]:.3f} ms')
        print(f'   before the first poll (ms after return, type, payload): {before}')
        print(f'   late .uno:Bold STATE_CHANGED (ms after the first poll): {late}')
