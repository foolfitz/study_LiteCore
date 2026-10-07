#!/bin/bash
# Red cases for judge.py on the v16 net's 12 reports (../../v16-shakedown/product-path-b003534c/).
# Expected: A all HIT under v16's own label and page; B P2 MISS (v17's page against v16's reports);
# C P3 MISS (one PASS turned into FAIL in a scratch copy, so 1 red cell).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
D=$HERE/../../v16-shakedown/product-path-b003534c
V16=b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d
S=$(mktemp -d)
cp "$D"/*.json "$D"/chain.log "$S"/
python3 - "$S" <<'PY'
import json, sys
from pathlib import Path
f = Path(sys.argv[1]) / 'e2-editor-v16-chrome-r2.json'; r = json.loads(f.read_text())
r['checks'][0]['outcome'] = 'FAIL'; f.write_text(json.dumps(r)); print('mutated', r['checks'][0]['id'])
PY
echo "### A positive"; python3 "$HERE/judge.py" --dir "$D" --candidate v16 --candidate-page $V16 | grep -E '^SUMMARY'
echo "### B wrong page"; python3 "$HERE/judge.py" --dir "$D" --candidate v16 | grep -E '^SUMMARY'
echo "### C one FAIL"; python3 "$HERE/judge.py" --dir "$S" --candidate v16 --candidate-page $V16 | grep -E 'RED:|^SUMMARY'
