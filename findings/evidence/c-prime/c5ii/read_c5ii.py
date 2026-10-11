# Ad-hoc reading of C5 (ii) per PREDICTION.md's rule. Reads each run's own report; mutation declarations
# (check / alsoRed / expectedToBeDetected) are taken from the report's own mutationDetail where present,
# and from the runner's MUTATIONS as a cross-check.
import json, sys, os
E = sys.argv[1]; TOOLS = sys.argv[2]
sys.path.insert(0, TOOLS)
import run_e2_c_product_path as pp
SPECIAL = {'caret-ignores-x', 'checkpoint-write-fails', 'copy-lies', 'a11y-projection-at-its-static-position'}
rows = []
for name, m in pp.MUTATIONS.items():
    p = os.path.join(E, f'mutation-{name}-chrome.json')
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        rows.append((name, 'NO-REPORT', '', '', '')); continue
    r = json.load(open(p))
    if r.get('mutation') != name:
        rows.append((name, 'WRONG-MUTATION', r.get('mutation'), '', '')); continue
    if r.get('complete') is not True:
        rows.append((name, 'INCOMPLETE', repr(r.get('complete')), '', '')); continue
    by = {c['id']: c.get('outcome') for c in r['checks']}
    decl = m['check']
    md = r.get('mutationDetail') or {}
    if md.get('mustGoRed') not in (None, decl):
        print('DECL MISMATCH', name, md.get('mustGoRed'), decl)
    own = by.get(decl, 'ABSENT')
    fails = sorted(k for k, v in by.items() if v == 'FAIL')
    if name == 'caret-ignores-x':
        red = own == 'FAIL' or (own == 'NOT_ESTABLISHED' and by.get('the-caret-is-drawn-where-it-was-placed') == 'FAIL')
        cls = 'RED(§17.10)' if red else 'NOT-RED(§17.10)'
    elif m.get('expectedToBeDetected') is False:
        cls = 'DECLARED-UNDETECTABLE verdict=' + ('detected' if own == 'FAIL' else 'not-detected')
    elif name == 'a11y-projection-at-its-static-position':
        cls = 'RECORDED ' + ('red' if own == 'FAIL' else 'survives')
    else:
        cls = 'RED' if own == 'FAIL' else 'NOT-RED'
    also = m.get('alsoRed') or []
    also_s = ','.join(f'{a}={by.get(a,"ABSENT")}' for a in also)
    rows.append((name, cls, f'{decl}={own}', also_s, 'FAIL=' + ','.join(fails) + f' | ok={r.get("ok")}'))
for row in rows:
    print(' | '.join(str(x) for x in row))
