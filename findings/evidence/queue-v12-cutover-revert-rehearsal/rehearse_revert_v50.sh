#!/usr/bin/env bash
# Revert rehearsal on the final page 31787584... / v49 -> v50, revert condition 3 named instance.
# Adapted from findings/evidence/queue-v12-cutover-revert-rehearsal/rehearse_revert_v49.sh
# with only the identity constants changed (BASE_SHA, CAND_SHA, NEWGEN, old/new
# manifest version).  Everything that mutates the tree is undone by the EXIT
# trap, whether this script finishes, fails, or is killed.
set -u
SP=/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/5553bcc0-16b3-4240-9ee3-0570a4c16e23/scratchpad
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 1

BASE_SHA=1ec7baf9fb53c808cf127476346d69d56cf93a802f6c72680fa84416f7599ecc
CAND_SHA=31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a
NEWGEN=e2/editor-shell-v2-bundle-v50.json

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
python3 tools/build_cutover_page.py --profile e2-editor-v13 --write \
        --expect-sha256 "$CAND_SHA" || { echo "STEP 1 FAILED"; exit 1; }
sha256sum web/e2-editor-app.js

echo
echo "=== STEP 2: stage it where the product is served from ==="
cp web/e2-editor-app.js dist/e2-editor-app.js
sha256sum dist/e2-editor-app.js

echo
echo "=== STEP 3: freeze the new generation, then point MANIFEST at it ==="
python3 tools/build_e2_c_shell_bundle.py --manifest "$NEWGEN" \
        --frozen-date 2026-09-09 --write > "$SP/freeze-v50.json" 2>&1
echo "freeze exit=$?  (what matters is the next line)"
python3 "$SP/check_written.py" "$SP/freeze-v50.json" || { echo "STEP 3 DID NOT WRITE"; exit 1; }
python3 "$SP/repoint_manifest.py" v49 v50 || { echo "STEP 3 REPOINT FAILED"; exit 1; }
grep -n '^MANIFEST = ' tools/build_e2_c_shell_bundle.py

echo
echo "=== RUN THE NET ON THE CUTOVER PAGE (no --candidate-profile) ==="
python3 tools/run_e2_c_product_path.py --out "$SP/rerun50-after-cutover.json" \
    > "$SP/rerun50-after-cutover.log" 2>&1
echo "runner exit=$?"
python3 tools/check_usable_editor.py --report "$SP/rerun50-after-cutover.json" \
    > "$SP/rerun50-reconcile-after-cutover.json" 2>&1
echo "reconciler exit=$?"

echo
echo "=== THE REVERT ==="
restore

echo
echo "=== RUN THE NET ON THE REVERTED PAGE ==="
python3 tools/run_e2_c_product_path.py --out "$SP/rerun50-after-revert.json" \
    > "$SP/rerun50-after-revert.log" 2>&1
echo "runner exit=$?"
python3 tools/check_usable_editor.py --report "$SP/rerun50-after-revert.json" \
    > "$SP/rerun50-reconcile-after-revert.json" 2>&1
echo "reconciler exit=$?"

echo
echo "=== FINAL VERIFY ==="
sha256sum web/e2-editor-app.js dist/e2-editor-app.js
echo "expected both: $BASE_SHA"
git status --short; echo "(clean above if empty)"
echo "REHEARSAL SCRIPT DONE"
