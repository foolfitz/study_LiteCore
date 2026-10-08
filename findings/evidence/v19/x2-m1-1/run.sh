#!/bin/bash
# X2 (spec 31.4): M1-1 after the v19 link, green then the three red cases of pre-link/m1-1-after-review/run.sh, unchanged.  Run from wasm_sdk_probe/.
E=../findings/evidence/v19/x2-m1-1
ts() { date +%H:%M:%S; }
one() {
  local name=$1; shift
  python3 tools/check_merge_key_undo_scope.py --base 5d77dc84 "$@" --json $E/$name.json > $E/$name.stdout.txt 2> $E/$name.stderr.txt
  local rc=$?
  echo "$(ts) $name rc=$rc args=$*" >> $E/run.log
}
one green
one red-only-v15 --carrier E2_V15
one red-inject-v8 --inject E2_V8=-DOXSDK_MERGE_KEY_UNDO
one red-v8-as-carrier --carrier E2_V15 --carrier E2_V19 --carrier E2_V8
echo "$(ts) done" >> $E/run.log
