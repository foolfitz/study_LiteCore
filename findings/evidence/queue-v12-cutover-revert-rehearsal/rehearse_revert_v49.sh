#!/usr/bin/env bash
# Revert rehearsal on the final page 9b29e39b... / v48, T2 item 5.
# Adapted from findings/evidence/queue-v12-cutover-revert-rehearsal/rehearse_revert_v45.sh
# with only the identity constants changed (BASE_SHA, CAND_SHA, NEWGEN, old/new
# manifest version).  Everything that mutates the tree is undone by the EXIT
# trap, whether this script finishes, fails, or is killed.
set -u
SP=/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/5553bcc0-16b3-4240-9ee3-0570a4c16e23/scratchpad
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 1

BASE_SHA=df5f3b6c7dde0b2eb463733975763ba70a5000f8f1345442d59109b153f85143
CAND_SHA=9b29e39bb09e5b948937a7552bfad6045bdb4e25bb993ee1270ebe70dddf361c
NEWGEN=e2/editor-shell-v2-bundle-v49.json

restore() {
  echo "=== RESTORE: undoing all three ==="
  git checkout -- web/e2-editor-app.js tools/build_e2_c_shell_bundle.py 2>&1
  cp web/e2-editor-app.js dist/e2-editor-app.js
  rm -f "$NEWGEN"
  sha256sum web/e2-editor-app.js dist/e2-editor-app.js
  grep -n '^MANIFEST = ' tools/build_e2_c_shell_bundle.py
  echo "git status (empty = clean):"; git status --short
}
trap restore EXIT

echo "=== BASELINE ==="
sha256sum web/e2-editor-app.js dist/e2-editor-app.js
grep -n '^MANIFEST = ' tools/build_e2_c_shell_bundle.py
git status --short; echo "(clean above if empty)"

echo
echo "=== STEP 1: write the page ==="
python3 tools/build_cutover_page.py --profile e2-editor-v12 --write \
        --expect-sha256 "$CAND_SHA" || { echo "STEP 1 FAILED"; exit 1; }
sha256sum web/e2-editor-app.js

echo
echo "=== STEP 2: stage it where the product is served from ==="
cp web/e2-editor-app.js dist/e2-editor-app.js
sha256sum dist/e2-editor-app.js

echo
echo "=== STEP 3: freeze the new generation, then point MANIFEST at it ==="
python3 tools/build_e2_c_shell_bundle.py --manifest "$NEWGEN" \
        --frozen-date 2026-09-07 --write > "$SP/freeze-v49.json" 2>&1
echo "freeze exit=$?  (what matters is the next line)"
python3 "$SP/check_written.py" "$SP/freeze-v49.json" || { echo "STEP 3 DID NOT WRITE"; exit 1; }
python3 "$SP/repoint_manifest.py" v48 v49 || { echo "STEP 3 REPOINT FAILED"; exit 1; }
grep -n '^MANIFEST = ' tools/build_e2_c_shell_bundle.py

echo
echo "=== RUN THE NET ON THE CUTOVER PAGE (no --candidate-profile) ==="
python3 tools/run_e2_c_product_path.py --out "$SP/rerun49-after-cutover.json" \
    > "$SP/rerun49-after-cutover.log" 2>&1
echo "runner exit=$?"
python3 tools/check_usable_editor.py --report "$SP/rerun49-after-cutover.json" \
    > "$SP/rerun49-reconcile-after-cutover.json" 2>&1
echo "reconciler exit=$?"

echo
echo "=== THE REVERT ==="
restore

echo
echo "=== RUN THE NET ON THE REVERTED PAGE ==="
python3 tools/run_e2_c_product_path.py --out "$SP/rerun49-after-revert.json" \
    > "$SP/rerun49-after-revert.log" 2>&1
echo "runner exit=$?"
python3 tools/check_usable_editor.py --report "$SP/rerun49-after-revert.json" \
    > "$SP/rerun49-reconcile-after-revert.json" 2>&1
echo "reconciler exit=$?"

echo
echo "=== FINAL VERIFY ==="
sha256sum web/e2-editor-app.js dist/e2-editor-app.js
echo "expected both: $BASE_SHA"
git status --short; echo "(clean above if empty)"
echo "REHEARSAL SCRIPT DONE"
