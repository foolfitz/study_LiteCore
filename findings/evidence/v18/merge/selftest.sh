#!/bin/bash
# Red cases for judge.py, built from v17's committed merge run (../../v17/merge, judged HIT on every line in its
# RESULT.md).  Each case copies that directory into a fresh temporary directory, changes one thing, and expects
# judge.py to miss exactly the line and browser it changed.  Output: selftest-output.txt, filtered by J() to the SUMMARY
# and the lines that went false; re-run this script for the full reader output of any case.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
V17=$HERE/../../v17/merge
P17=4c0088c7a518bc36b9cc999d2e67796d20a58525355b68ae67881228dc95b498
P18=cfc8ba1d54dc4bef52baebc34f9d5f60ffe9cc4af9bee8c7a326bb02b2221cda
J() { python3 -I "$HERE/judge.py" "$@" | grep -E "^SUMMARY|FAILS|-> False|not true: \[|anywhere in the reports: \[|off the expected outcome or not passing: [1-9]|: False$|NOT DONE"; echo "exit ${PIPESTATUS[0]}"; }
fresh() { local s; s=$(mktemp -d); cp -r "$V17"/. "$s"/; echo "$s"; }
edit() { # dir, file, python statement over r (the parsed report)
  python3 -I - "$1/$2" "$3" <<'PY'
import json, sys
p, stmt = sys.argv[1], sys.argv[2]
r = json.load(open(p)); exec(stmt); json.dump(r, open(p, "w"), ensure_ascii=False)
PY
}

echo "### 0. v17 as recorded, v17's profile and page (expect every line HIT, exit 0)"
J --dir "$V17" --profile e2-editor-v17 --page $P17

echo "### 1. v17 as recorded, read as v18 (expect M1 MISS on both browsers: profile and page)"
J --dir "$V17"

S=$(fresh)
edit "$S" shakedown-chrome.json 'r["cases"][7]["pass"] = False'
echo "### 2. one case's pass flag false, shakedown-chrome (expect chrome M2 MISS only)"
J --dir "$S" --profile e2-editor-v17 --page $P17

S=$(fresh)
edit "$S" shakedown-chrome.json 'c = next(c for c in r["cases"] if c["case"] == "C15"); c["stage"] = "anchor-mismatch"'
echo "### 3. C15's stage changed, its pass flag left true (expect chrome M2 MISS only: the reader does not trust pass)"
J --dir "$S" --profile e2-editor-v17 --page $P17

S=$(fresh)
edit "$S" shakedown-firefox.json 'r["m2_0"][2]["document"]["reducedBytesEqual"] = False'
echo "### 4. M2-0 false on text-frame, shakedown-firefox (expect firefox M2 MISS only)"
J --dir "$S" --profile e2-editor-v17 --page $P17

S=$(fresh)
rm "$S"/control-firefox.docs/C01-r1-follow.odt
echo "### 5. one kept follow document removed from control-firefox.docs, pair output untouched (expect firefox M3 MISS only)"
J --dir "$S" --profile e2-editor-v17 --page $P17

S=$(fresh)
edit "$S" control-chrome.json 'c = next(c for c in r["cases"] if c["case"] == "C15"); c["toastWindow"]["toasts"].append("重繪失敗")'
echo "### 6. 「重繪失敗」 added to one toast list in control-chrome, clauses untouched (expect chrome M4 MISS only)"
J --dir "$S" --profile e2-editor-v17 --page $P17

S=$(fresh)
rm "$S"/pair-firefox.stdout.txt
echo "### 7. pair-firefox.stdout.txt missing (expect NOT DONE firefox, exit 3)"
J --dir "$S" --profile e2-editor-v17 --page $P17
