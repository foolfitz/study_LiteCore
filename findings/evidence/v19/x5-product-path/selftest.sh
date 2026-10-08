#!/bin/bash
# Red cases for census_recovery_cell.py (spec §36): a copy of the committed Firefox reports in a temporary
# directory, then (1) unchanged -> exit 0; (2) one PASS turned into FAIL -> 1; (3) one NE whose 038 inducer is
# marked as fired -> 1; (4) an empty directory -> 2.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
EV=$(cd "$HERE/../.." && pwd)
S=$(mktemp -d)
git -C "$EV" ls-files -z -- '**/e2-editor-*-firefox-r*.json' | (cd "$EV" && xargs -0 cp --parents -t "$S")
C="python3 -I $HERE/census_recovery_cell.py --dir"
echo "### (1) the committed reports, copied (expect exit 0)"; $C "$S" | tail -1; echo "exit ${PIPESTATUS[0]}"
python3 -I - "$S" <<'PY'
import json, sys, pathlib
S = pathlib.Path(sys.argv[1])
def edit(name, change):
    p = next(S.rglob(name)); d = json.loads(p.read_text())
    c = next(c for c in d["checks"] if c["id"] == "recovery-returns-what-the-product-promised"); change(c)
    p.write_text(json.dumps(d, ensure_ascii=False))
edit("e2-editor-v18-firefox-r1.json", lambda c: c.update(outcome="FAIL", ok=False))
PY
echo "### (2) v18 firefox r1 turned into FAIL (expect exit 1)"; $C "$S" | /usr/bin/grep -E "^FLAG|^CENSUS"; echo "exit ${PIPESTATUS[0]}"
python3 -I - "$S" <<'PY'
import json, sys, pathlib
S = pathlib.Path(sys.argv[1])
p = next(S.rglob("e2-editor-v18-firefox-r1.json")); d = json.loads(p.read_text())
next(c for c in d["checks"] if c["id"] == "recovery-returns-what-the-product-promised").update(outcome="PASS", ok=True)
p.write_text(json.dumps(d, ensure_ascii=False))
p = next(S.rglob("v19/x5-product-path/e2-editor-v19-firefox-r1.json")); d = json.loads(p.read_text())
next(c for c in d["checks"] if c["id"] == "recovery-returns-what-the-product-promised")["observed"]["finding038Reproduced"] = True
p.write_text(json.dumps(d, ensure_ascii=False))
PY
echo "### (3) v19 firefox r1's NE with 038 marked as reproduced (expect exit 1)"; $C "$S" | /usr/bin/grep -E "^FLAG|^CENSUS"; echo "exit ${PIPESTATUS[0]}"
E=$(mktemp -d)
echo "### (4) an empty directory (expect exit 2)"; $C "$E" | tail -1; echo "exit ${PIPESTATUS[0]}"
rm -rf "$S" "$E"
