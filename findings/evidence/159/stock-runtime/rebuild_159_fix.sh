#!/usr/bin/env bash
# Finding 159: incremental rebuild of build-186-R with the bridge change, for the run-time check of the fix.
# This compiles (make), so the owner runs it (global rule), unless the owner has said to let the agent build.
#
# Source: wasm-lite/upstream-master/src-186-R on branch finding159-test-on-R = 4847e69dd326 (finding 186's R) + one
# commit to bridges/CustomTarget_gcc3_wasm.mk. Build dir: build-186-R, the stock build the probe ran on.
# The products of build-186-R before this were copied to archive-186-R-products-before-159/ (SHA256SUMS there).
#
# The change adds a prerequisite (workdir/UnoApiTarget/scaddins.rdb) that is older than the generated files, so make
# would not regenerate them by itself: the three generated files are deleted first. A fresh build does not need that.
# usage: rebuild_159_fix.sh            (no arguments; writes rebuild-159-fix.receipt.txt next to itself)
set -u
U=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/upstream-master
SRC=$U/src-186-R
B=build-186-R
HERE=$(cd "$(dirname "$0")" && pwd)
RECEIPT=$HERE/rebuild-159-fix.receipt.txt
LOG=$U/$B-159fix.log
GEN=$U/$B/workdir/CustomTarget/bridges/gcc3_wasm
EMS=$U/$B/workdir/installation/LibreOffice/emscripten
ARCH=$U/archive-186-R-products-before-159
fatal() { echo "FATAL: $*"; exit 2; }
[ "$(git -C "$SRC" rev-parse --abbrev-ref HEAD)" = finding159-test-on-R ] || fatal "$SRC is not on finding159-test-on-R"
[ "$(git -C "$SRC" status --short --untracked-files=no | wc -l)" = 0 ] || fatal "$SRC has uncommitted changes"
grep -q 'gb_bridges_gcc3_wasm_internal_apis' "$SRC/bridges/CustomTarget_gcc3_wasm.mk" || fatal "the change is not in $SRC"
[ -f "$ARCH/SHA256SUMS" ] || fatal "no archive of the products before the change at $ARCH"
pgrep -x make >/dev/null && fatal "another make is running: $(pgrep -a make | head -3)"
{
  echo "what=incremental rebuild of $B with the finding 159 bridge change"
  echo "src=$SRC"
  echo "src_commit=$(git -C "$SRC" log -1 --format='%H %s')"
  echo "src_parent=$(git -C "$SRC" log -1 --format='%H %s' HEAD~1)"
  echo "start=$(date -Is)"
  echo "load_at_start=$(cut -d' ' -f1-3 /proc/loadavg)"
  echo "deleted=$(cd "$GEN" && ls generated-cxx.cxx generated-asm.s exports 2>/dev/null | tr '\n' ' ')"
} > "$RECEIPT"
rm -f "$GEN/generated-cxx.cxx" "$GEN/generated-asm.s" "$GEN/exports"
SECONDS=0
"$U/build.sh" "$B" "$SRC" > "$LOG" 2>&1; rc=$?
{
  echo "make_exit=$rc seconds=$SECONDS"
  echo "end=$(date -Is)"
  echo "log=$LOG"
  echo "generated_signatures=$(grep -cE '^extern "C" void callVirtualFunction_' "$GEN/generated-cxx.cxx" 2>/dev/null)"
  (cd "$GEN" && sha256sum generated-cxx.cxx generated-asm.s exports 2>&1 | sed 's/^/generated_sha256 /')
  (cd "$EMS" && sha256sum soffice.wasm soffice.js soffice.data 2>&1 | sed 's/^/product_sha256 /')
  echo "products changed against the archive (sha256sum -c, FAILED = changed):"
  (cd "$ARCH" && sed -n 's#  \./emscripten/#  '"$EMS"'/#p' SHA256SUMS | sha256sum -c 2>&1 | sed 's/^/  /')
} >> "$RECEIPT"
cat "$RECEIPT"
exit $rc
