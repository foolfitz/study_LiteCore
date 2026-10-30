#!/usr/bin/env bash
# SPEC-M3-v27-finding-176 §6 (fable ruling 2 §3.4): who reads the status strip, the review toast words, or the two
# check ids finding 176 moves.  A one-time measurement (CLAUDE.md §1, form 3): the member list lives elsewhere.
# Run from the repo root: bash findings/evidence/v27-176/census/census.sh > findings/evidence/v27-176/census/census.txt
set -u
cd wasm_sdk_probe
echo "# git $(git rev-parse --short HEAD)"
for pattern in 's-latency' '無法單獨核對' '取不到任何內容' '不是你要的就按' '檢查的極限' \
               'bulleting-a-blank-line-does-not-demand-a-rollback' 'notice-action-recovers-the-session' \
               'recoveryPairing' 'multi-block-readback'; do
  echo "== $pattern"
  grep -rln --include='*.py' --include='*.js' --include='*.mjs' --include='*.sh' -- "$pattern" tools web editor-shell-v2 sdk 2>/dev/null | sort
done
echo "== '失敗' with latency on the same line (tools/)"
grep -rn --include='*.py' -- 'latency' tools | grep -- '失敗' | cut -c1-200
echo "== findings/ readers of the two check ids"
grep -rln --include='*.py' --include='DISPOSITIONS.md' -- 'bulleting-a-blank-line-does-not-demand-a-rollback\|recoveryPairing' ../findings/evidence 2>/dev/null | sort
