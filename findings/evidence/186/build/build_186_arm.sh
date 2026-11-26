#!/usr/bin/env bash
# Finding 186: full WASM build of one arm, in a fresh build directory, with the environment of
# wasm-lite/upstream-master/build.sh (emsdk 4.0.10, Qt 5.15.2, the upstream-master ccache).
# usage: build_186_arm.sh <arm: M|R> <source worktree>
# Flags: the five of build-nosym, plus --with-external-tar so the tarballs already downloaded are reused
# (missing ones are fetched into that directory). That flag only sets TARFILE_LOCATION.
# A first make in a fresh directory can hit finding 003 ("Directory nonexistent" for an UnpackedTarball .version);
# in that case, and only then, make is run once more. The receipt says whether that happened.
set -u
U=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/upstream-master
ARM=${1:?arm}; SRC=${2:?source worktree}
B=build-186-$ARM
LOG=$U/$B.log
RECEIPT=$U/$B.receipt.txt
[ -e "$U/$B" ] && { echo "FATAL: $U/$B exists; A/B arms need a fresh directory"; exit 2; }
mkdir "$U/$B"
printf '%s\n' --with-distro=LibreOfficeWASM32 --disable-symbols --enable-ccache \
  --with-build-platform-configure-options=--enable-ccache --with-parallelism=10 \
  "--with-external-tar=$U/src/external/tarballs" > "$U/$B/autogen.input"
{
  echo "arm=$ARM"
  echo "src=$SRC"
  echo "src_commit=$(git -C "$SRC" log -1 --format='%H %s')"
  echo "src_dirty=$(git -C "$SRC" status --short --untracked-files=no | wc -l)"
  echo "configure_ac_sha256=$(sha256sum "$SRC/configure.ac" | cut -d' ' -f1)"
  echo "start=$(date -Is)"
  echo "load_at_start=$(cut -d' ' -f1-3 /proc/loadavg)"
} > "$RECEIPT"
SECONDS=0
"$U/build.sh" "$B" "$SRC" > "$LOG" 2>&1; rc=$?
echo "first_make_exit=$rc seconds=$SECONDS" >> "$RECEIPT"
retried=no
if [ $rc -ne 0 ] && grep -q 'UnpackedTarball/.*\.version: Directory nonexistent' "$LOG"; then
  retried=yes
  echo "=== finding 003 hit, running make once more $(date -Is)" >> "$LOG"
  "$U/build.sh" "$B" "$SRC" >> "$LOG" 2>&1; rc=$?
fi
{
  echo "retried_for_finding_003=$retried"
  echo "final_exit=$rc"
  echo "total_seconds=$SECONDS"
  echo "end=$(date -Is)"
} >> "$RECEIPT"
cat "$RECEIPT"
exit $rc
