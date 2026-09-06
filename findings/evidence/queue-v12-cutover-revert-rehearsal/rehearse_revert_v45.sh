#!/usr/bin/env bash
# Revert rehearsal INCLUDING step 3 (work item W-5).  2026-09-06.
#
# Everything that mutates the tree is undone by the EXIT trap, whether this
# script finishes, fails, or is killed.  A rehearsal that can strand the tree is
# the thing it exists to prove cannot happen.
set -u
SP=/tmp/claude-1000/-home-jiajun-LibreOffice-study-LiteCore/d1e9dbdf-25ab-4bf2-842e-67215fb9cfe8/scratchpad
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 1

BASE_SHA=5aeae0e1dbfe492d7de478962ac15bffd22aa6cfcdeea89737f529b6aa8d2de7
CAND_SHA=20f09cc9da19f07d65b8c844a753aa880782e404fb6ea75e1f121c1f2d090d95
NEWGEN=e2/editor-shell-v2-bundle-v45.json

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
# The tool exits 1 if ANY problem remains after the write, and this bundle
# carries three inherited "in scope but neither included nor excluded" entries.
# So judge on whether the file was WRITTEN, not on the exit code.
python3 tools/build_e2_c_shell_bundle.py --manifest "$NEWGEN" \
        --frozen-date 2026-09-06 --write > "$SP/freeze-v45.json" 2>&1
echo "freeze exit=$?  (what matters is the next line)"
python3 "$SP/check_written.py" "$SP/freeze-v45.json" || { echo "STEP 3 DID NOT WRITE"; exit 1; }
python3 "$SP/repoint_manifest.py" v44 v45 || { echo "STEP 3 REPOINT FAILED"; exit 1; }
grep -n '^MANIFEST = ' tools/build_e2_c_shell_bundle.py

echo
echo "=== RUN THE NET ON THE CUTOVER PAGE (no --candidate-profile) ==="
python3 tools/run_e2_c_product_path.py --out "$SP/rerun-after-cutover.json" \
    > "$SP/rerun-after-cutover.log" 2>&1
echo "runner exit=$?"
python3 tools/check_usable_editor.py --report "$SP/rerun-after-cutover.json" \
    > "$SP/rerun-reconcile-after-cutover.json" 2>&1
echo "reconciler exit=$?"

echo
echo "=== THE REVERT ==="
restore

echo
echo "=== RUN THE NET ON THE REVERTED PAGE ==="
python3 tools/run_e2_c_product_path.py --out "$SP/rerun-after-revert.json" \
    > "$SP/rerun-after-revert.log" 2>&1
echo "runner exit=$?"
python3 tools/check_usable_editor.py --report "$SP/rerun-after-revert.json" \
    > "$SP/rerun-reconcile-after-revert.json" 2>&1
echo "reconciler exit=$?"

echo
echo "=== FINAL VERIFY ==="
sha256sum web/e2-editor-app.js dist/e2-editor-app.js
echo "expected both: $BASE_SHA"
git status --short; echo "(clean above if empty)"
echo "REHEARSAL SCRIPT DONE"
