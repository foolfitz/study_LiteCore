#!/usr/bin/env bash
# Finding 186: compare the configure output of each arm against the pre-regression build.
# usage: compare.sh <arms-dir> <out-dir>
# <arms-dir> holds the directories conf_arm.sh created. Build and source paths are replaced
# by @BUILDDIR@ / @SRCDIR@ before diffing, so only real differences remain.
set -u
ARMS=${1:?arms dir}; OUT=${2:?out dir}
U=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/upstream-master
PRE=$U/build-nosym            # stock LibreOfficeWASM32 build of 2a2335cf, 8 commits before d98a796946ff
mkdir -p "$OUT"

# norm <file> <builddir as written into the file>
norm() { sed -e "s#$2#@BUILDDIR@#g" -e "s#$U/submit#@SRCDIR@#g" -e "s#$U/src#@SRCDIR@#g" "$1"; }

# The build dir a config_host.mk was generated for (arm dirs were renamed after the run).
builddir_of() { sed -n 's/^export BUILDDIR=//p' "$1/config_host.mk"; }

mk_diff() {   # <label> <dirA> <dirB>
  diff <(norm "$2/config_host.mk" "$(builddir_of "$2")") <(norm "$3/config_host.mk" "$(builddir_of "$3")") \
    > "$OUT/$1.config_host.mk.diff"
  echo "$1: config_host.mk diff lines: $(grep -c '^[<>]' "$OUT/$1.config_host.mk.diff")"
}

hdr_diff() {  # <label> <dirA> <dirB>
  : > "$OUT/$1.headers.diff"
  local n=0 d=0
  for h in "$2"/config_host/*.h; do
    b=$(basename "$h"); n=$((n+1))
    if [ ! -f "$3/config_host/$b" ]; then echo "MISSING $b" >> "$OUT/$1.headers.diff"; d=$((d+1)); continue; fi
    if ! diff <(norm "$h" "$(builddir_of "$2")") <(norm "$3/config_host/$b" "$(builddir_of "$3")") > /tmp/186.$$.d; then
      { echo "--- $b"; cat /tmp/186.$$.d; } >> "$OUT/$1.headers.diff"; d=$((d+1))
    fi
  done
  rm -f /tmp/186.$$.d
  echo "$1: headers compared: $n (other side has $(ls "$3"/config_host/*.h | wc -l)), differing: $d"
}

# Non-vacuity: the inputs must exist and be non-empty.
for d in "$PRE" "$ARMS"/R2-fixR-gui "$ARMS"/R4-fixR-nogui "$ARMS"/M2-fixM-gui "$ARMS"/C4a-unpatched-nogui; do
  [ -s "$d/config_host.mk" ] || { echo "FATAL: no config_host.mk in $d"; exit 2; }
done

mk_diff  pre-vs-fixR-gui  "$PRE" "$ARMS"/R2-fixR-gui
hdr_diff pre-vs-fixR-gui  "$PRE" "$ARMS"/R2-fixR-gui
mk_diff  pre-vs-fixM-gui  "$PRE" "$ARMS"/M2-fixM-gui
hdr_diff pre-vs-fixM-gui  "$PRE" "$ARMS"/M2-fixM-gui
mk_diff  nogui-unpatched-vs-fixR "$ARMS"/C4a-unpatched-nogui "$ARMS"/R4-fixR-nogui
hdr_diff nogui-unpatched-vs-fixR "$ARMS"/C4a-unpatched-nogui "$ARMS"/R4-fixR-nogui
