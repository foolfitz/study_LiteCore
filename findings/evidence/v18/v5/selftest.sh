#!/bin/bash
# Red cases for judge.py, built from v17's committed owner's-document report (../../v17/v5/shakedown-chrome-v5.json,
# whose RESULT.md reads V5 clauses 1 and 2 HIT).  Each case writes a changed copy into a fresh temporary directory
# and expects judge.py to miss exactly the line it changed.  Output: selftest-output.txt, filtered by J() to the
# SUMMARY and the lines that went false; re-run for the full output.  The owner's saves are read from
# wasm_sdk_probe/build/merge-wasm-private/shakedown-chrome-v5.docs (not in the repository).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
R17=$HERE/../../v17/v5/shakedown-chrome-v5.json
D17=$HERE/../../../../wasm_sdk_probe/build/merge-wasm-private/shakedown-chrome-v5.docs
P17=4c0088c7a518bc36b9cc999d2e67796d20a58525355b68ae67881228dc95b498
J() { python3 -I "$HERE/judge.py" --private-docs "$D17" "$@" | grep -E "^SUMMARY|: False$|outside v17's UI words: \[|^NOT DONE|<- not as predicted|not passing: \[|M2-0 reducedBytesEqual: .*False"; echo "exit ${PIPESTATUS[0]}"; }
mut() { # python statement over r -> path of the changed copy
  local s; s=$(mktemp -d)
  python3 -I - "$R17" "$s/r.json" "$1" <<'PY'
import json, sys
src, dst, stmt = sys.argv[1:4]
r = json.load(open(src)); own = {c["case"]: c for c in r["cases"] if c["fixture"] == "pmpc"}; exec(stmt)
json.dump(r, open(dst, "w"), ensure_ascii=False)
PY
  echo "$s/r.json"
}
V17ARGS="--profile e2-editor-v17 --page $P17"

echo "### 0. v17 as recorded, v17's profile and page (expect pre, O1, O2 HIT, exit 0)"
J --report "$R17" $V17ARGS

echo "### 1. v17 as recorded, read as v18 (expect pre MISS: profile, page)"
J --report "$R17"

echo "### 2. E10's engine caret height 230 (v16's value) (expect O1 MISS)"
J --report "$(mut 'own["E10"]["place"]["engineCaret"][3] = 230')" $V17ARGS

echo "### 3. E05 placed by a key (keyed true) (expect O1 MISS)"
J --report "$(mut 'own["E05"]["place"]["keyed"] = True')" $V17ARGS

echo "### 4. P62's engine x off by one twip (expect O1 MISS)"
J --report "$(mut 'own["P62"]["place"]["engineCaret"][0] += 1')" $V17ARGS

echo "### 5. an owner row carries a search string (expect pre MISS)"
J --report "$(mut 'own["E13"]["search"] = "M13"')" $V17ARGS

echo "### 6. an owner row carries a CJK string that is not a page UI word (expect pre MISS)"
J --report "$(mut 'own["T01"]["afterKey"]["toast"] = "測試段落"')" $V17ARGS

echo "### 7. one synthetic case not passing (expect O2 MISS)"
J --report "$(mut 'next(c for c in r["cases"] if c["fixture"] != "pmpc")["pass"] = False')" $V17ARGS

echo "### 8. M2-0 false on the owner's document (expect O2 MISS)"
J --report "$(mut 'next(m for m in r["m2_0"] if m["fixture"] == "pmpc")["document"]["reducedBytesEqual"] = False')" $V17ARGS

echo "### 9. report missing (expect NOT DONE, exit 3)"
J --report "$(mktemp -d)/absent.json" $V17ARGS
