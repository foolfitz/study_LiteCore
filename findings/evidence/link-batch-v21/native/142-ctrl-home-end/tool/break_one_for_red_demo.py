# Deliberately break ONE raw file: in a1-home-mid/r2.jsonl, make the Ctrl+Home
# press land on P2's start instead of the document start (after-cursor and the
# callback payload), as a wrong instrument or a wrong Writer would.
import json, sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'a1-home-mid' / 'r2.jsonl'
lines = p.read_text().splitlines()
for i, l in enumerate(lines):
    r = json.loads(l)
    if r['rec'] == 'press':
        r['after']['cursor'] = '1418, 1694, 0, 276'
        for c in r['callbacks']:
            if c['type'] == 'LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR':
                c['payload'] = '1418, 1694, 0, 276'
        lines[i] = json.dumps(r)
p.write_text('\n'.join(lines) + '\n')
print('broke', p)
