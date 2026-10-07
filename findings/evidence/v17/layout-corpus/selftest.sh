#!/bin/bash
# Red cases for judge.py, on the dry run's files (../../v16-shakedown/layout-corpus/). Writes mutated copies to a
# fresh temporary directory only. Expected: A PASS (48 measured); B RED (7 documents, v15 = finding 113);
# C RED (not-measured sets); D3 RED (+3 px); D2 PASS (+2 px = T); E RED (not-comparable sets); F RED (band count).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
D=$HERE/../../v16-shakedown/layout-corpus
S=$(mktemp -d)
J="python3 $HERE/judge.py"
python3 - "$D" "$S" <<'PY'
import json, sys, copy
from pathlib import Path
D, S = Path(sys.argv[1]), Path(sys.argv[2])
b = json.loads((D / 'layout-1-e2-editor-v16.json').read_text())
k = [k for k, e in sorted(b['documents'].items()) if 'runs' in e and e['runs'] and not e.get('unsettled')][0]
def w(name, mut):
    m = copy.deepcopy(b); mut(m['documents']); (S / name).write_text(json.dumps(m))
w('c-zero.json', lambda d: d[k].__setitem__('runs', []))
w('d-plus3.json', lambda d: d[k]['runs'][1].__setitem__(0, d[k]['runs'][1][0] + 3))
w('d-plus2.json', lambda d: d[k]['runs'][1].__setitem__(0, d[k]['runs'][1][0] + 2))
w('e-nc.json', lambda d: d[k].pop('runs'))
w('f-extra-band.json', lambda d: d[k]['runs'].append([900, 901]))
print('mutated document:', k)
PY
V16="$D/layout-0-e2-editor-v16.json"
echo "### A v16 s1 vs v16 s2 (expect PASS)"; $J --files "$V16" "$D/layout-1-e2-editor-v16.json" --profiles e2-editor-v16 e2-editor-v16 | tail -3; echo "exit ${PIPESTATUS[0]}"
echo "### B v16 vs v15 (expect RED, 7)"; $J --files "$V16" "$D/layout-2-e2-editor-v15.json" --profiles e2-editor-v16 e2-editor-v15 | grep -E 'RED|VERDICT'; echo "exit ${PIPESTATUS[0]}"
for m in c-zero d-plus3 d-plus2 e-nc f-extra-band; do
  echo "### $m"; $J --files "$V16" "$S/$m.json" --profiles e2-editor-v16 e2-editor-v16 | grep -E 'RED|VERDICT'; echo "exit ${PIPESTATUS[0]}"
done
