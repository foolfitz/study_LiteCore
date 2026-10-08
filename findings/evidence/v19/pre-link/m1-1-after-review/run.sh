#!/bin/bash
# M1-1 with the per-object carrier rule (review 2026-10-08, codex B7 / opus S3): green, then the three red cases.  Run from wasm_sdk_probe/.
E=../findings/evidence/v19/pre-link/m1-1-after-review
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
