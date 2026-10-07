#!/bin/bash
# Red cases specific to this copy (28.4 W4), run after ./selftest.sh (the v17 reader's own red cases, unchanged).
# The W4 case builds its mutated input from v17's committed control file into a fresh temporary directory.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
V17=$HERE/../../v17/layout-corpus
S=$(mktemp -d)
python3 - "$V17" "$S" <<'PY'
import json, sys
V17, S = sys.argv[1], sys.argv[2]
d = json.load(open(f"{V17}/layout-1-e2-editor-v17-cjk-r5-ab.json"))
k = [k for k, e in sorted(d["documents"].items()) if "runs" in e and e["runs"] and not e.get("unsettled")][0]
d["documents"][k]["runs"] = []
json.dump(d, open(f"{S}/a.json", "w")); json.dump(d, open(f"{S}/b.json", "w"))
PY
J="python3 $HERE/judge.py"
echo "### v17's counted files (expect RED, paragraph-content only)"; $J --files $V17/layout-0-e2-editor-v17.json $V17/layout-1-e2-editor-v17-cjk-r5-ab.json --profiles e2-editor-v17 e2-editor-v17-cjk-r5-ab | grep -E "RED|VERDICT|28.4"; echo "exit ${PIPESTATUS[0]}"
echo "### control vs control (expect PASS)"; $J --files $V17/layout-1-e2-editor-v17-cjk-r5-ab.json $V17/layout-1-e2-editor-v17-cjk-r5-ab.json --profiles e2-editor-v17-cjk-r5-ab e2-editor-v17-cjk-r5-ab | grep -E "VERDICT|28.4"; echo "exit ${PIPESTATUS[0]}"
echo "### both arms gain the same extra not-measured document (expect RED by W4)"; $J --files $S/a.json $S/b.json --profiles e2-editor-v17-cjk-r5-ab e2-editor-v17-cjk-r5-ab | grep -E "W4|VERDICT"; echo "exit ${PIPESTATUS[0]}"
