#!/usr/bin/env bash
# M1-1 extended (ruling 6 condition 50.4'/50.5'): the two green runs, the five red cases, and the default
# invocation after the change.  Run from wasm_sdk_probe/.  OUT=DIR writes somewhere else (the default is the
# directory that holds this script; the pre-56 outputs there are kept as the record of green-2's red).  No make target builds anything: the tool preprocesses
# src/ from `git archive BASE` and from the working tree, and reads the compile commands from `make -n -B`.
#
#   bash ../findings/evidence/link-batch/v20-part3/m1-1/run.sh
set -u
OUT=${OUT:-../findings/evidence/link-batch/v20-part3/m1-1}
V20=E2_V20=probe_engine,sdk_api,editor_api

# Condition 57 (ruling 6 amendment 2): red-5 is a red case only when its stdout has exactly one FAIL line and it is
# this one.  Before the engine edit of 543a5566 it was red on E2_V15's undeclared difference instead, so it was not.
RED5_LINE='FAIL E2_V19: its probe_engine object does not differ from 82af92ca^ (B is not in it)'
red5_clean() {  # stdout file of the red-5 run
  [ "$(grep -c '^FAIL ' "$1")" = 1 ] && grep -qxF "$RED5_LINE" "$1"
}
if [ "${1:-}" = "--check-red5" ]; then  # bash run.sh --check-red5 FILE : judge an existing red-5 stdout, run nothing
  if red5_clean "$2"; then echo "red-5 CLEAN: $2"; else echo "red-5 NOT A RED CASE (condition 57): $2"; exit 1; fi
  exit 0
fi

{
  echo "HEAD (parent of the commit that carries this evidence): $(git rev-parse HEAD)"
  echo "tools/check_merge_key_undo_scope.py sha256: $(sha256sum tools/check_merge_key_undo_scope.py | cut -d' ' -f1)"
  echo "Makefile sha256: $(sha256sum Makefile | cut -d' ' -f1)"
  echo "82af92ca^: $(git rev-parse '82af92ca^')"
  echo "5d77dc84: $(git rev-parse 5d77dc84)"
  echo "git status --short (this directory's tree, before the commit):"
  git status --short | sed 's/^/  /'
} > "$OUT/head.txt"

run() {  # name, args...
  local name=$1; shift
  echo "python3 tools/check_merge_key_undo_scope.py $* --json $OUT/$name.json" > "$OUT/$name.cmd.txt"
  python3 tools/check_merge_key_undo_scope.py "$@" --json "$OUT/$name.json" \
    > "$OUT/$name.stdout.txt" 2> "$OUT/$name.stderr.txt"
  echo "exit $?" > "$OUT/$name.exit.txt"
  echo "$name: $(cat "$OUT/$name.exit.txt")"
}

run default-after-change      --base 5d77dc84
run green-1-base-5d77dc84     --base 5d77dc84 --carrier E2_V15 --carrier E2_V19 --carrier $V20
run green-2-base-82af92ca-up  --base '82af92ca^' --carrier $V20
run red-1-v20-engine-only     --base 5d77dc84 --carrier E2_V15 --carrier E2_V19 --carrier E2_V20=probe_engine
run red-2-v20-engine-sdk-api  --base 5d77dc84 --carrier E2_V15 --carrier E2_V19 --carrier E2_V20=probe_engine,sdk_api
run red-3-v20-declared-unmoved --base 5d77dc84 --carrier E2_V15 --carrier E2_V19 --carrier E2_V20=probe_engine,sdk_api,editor_api,unoembind_stub
run red-4-inject-v19-define   --base 5d77dc84 --carrier E2_V15 --carrier E2_V19 --carrier $V20 --inject E2_V19=-DOXSDK_E2_V20_LINK_BATCH
run red-5-base-82af92ca-up-with-v19 --base '82af92ca^' --carrier $V20 --carrier E2_V19
if red5_clean "$OUT/red-5-base-82af92ca-up-with-v19.stdout.txt"; then
  echo "red-5: clean red case"
else
  echo "red-5: NOT A RED CASE (condition 57): its stdout is not exactly the one FAIL line"
fi
