#!/usr/bin/env bash
# Finding 159: red cases for read_159.py. Each doctors one thing in a copy of run-01 (in a temp dir) and shows that the
# reader turns red in that case and nowhere else. Writes reader-red-cases.txt next to itself.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
cd "$HERE"
python3 -I - "$T" <<'EOF'
import copy, json, sys
T = sys.argv[1]
r = json.load(open('run-01/R-en-US.json'))
def cell(d, i): return [x for x in d['cells']['cells'] if x['id'] == i][0]
a = copy.deepcopy(r); cell(a, 'I1')['typed']['error'] = 519
json.dump(a, open(f'{T}/a-I1-typed-519.json', 'w'))
b = copy.deepcopy(r)
[x for x in b['direct'] if x['id'] == 'D4'][0]['exception']['target']['message'] = \
    'Wasm bridge cannot call virtual function with signature diii'
json.dump(b, open(f'{T}/b-D4-wrong-signature.json', 'w'))
c = copy.deepcopy(r); cell(c, 'A3')['api'].update(error=0, value=0.4958904109589041, string='0.495890410958904')
json.dump(c, open(f'{T}/c-A3-api-gives-value.json', 'w'))
d = copy.deepcopy(r); d['cells']['cells'] = d['cells']['cells'][:-1]
json.dump(d, open(f'{T}/d-last-row-missing.json', 'w'))
open(f'{T}/sig-all-in-table.tsv', 'w').writelines(l.replace('\tABSENT', '\tIN_TABLE') for l in open('sig-stock-186R.tsv'))
EOF
{
  echo "# read_159.py red cases, $(date -Is); reader sha256 $(sha256sum read_159.py | cut -c1-16)"
  echo "# expected: a, b, c exit 1 with exactly the doctored id NO; d exit 2 (VACUOUS);"
  echo "# e (the unmodified stock run judged against a table where every method is IN_TABLE) exit 1 with A1-A8, D4-D6 NO"
  for f in a-I1-typed-519 b-D4-wrong-signature c-A3-api-gives-value d-last-row-missing; do
    python3 -I read_159.py cases.json oracle-native.json sig-stock-186R.tsv "$T/$f.json" > "$T/$f.out" 2>&1; rc=$?
    echo "$f: exit=$rc NO=[$(grep ' NO$' "$T/$f.out" | awk '{print $1}' | tr '\n' ' ')] $(grep -o 'VACUOUS.*' "$T/$f.out")"
  done
  python3 -I read_159.py cases.json oracle-native.json "$T/sig-all-in-table.tsv" run-01/R-en-US.json > "$T/e.out" 2>&1; rc=$?
  echo "e-stock-run-vs-all-in-table: exit=$rc NO=[$(grep ' NO$' "$T/e.out" | awk '{print $1}' | tr '\n' ' ')]"
} > reader-red-cases.txt
cat reader-red-cases.txt
