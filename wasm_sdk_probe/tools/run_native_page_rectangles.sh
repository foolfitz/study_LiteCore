#!/usr/bin/env bash
# Link batch item 2, Part N1: getPartPageRectangles on native LibreOffice.
# Brief: handoff/tasks/TASK-2026-10-12c-native-page-rectangles-and-129-shapes.md
# Usage: tools/run_native_page_rectangles.sh [OUT_DIR] [ROUNDS]
#
# Two documents, ROUNDS (default 3) fresh processes each:
#   owner   build/scratch-m3-production-ui/PMPC指南.odt (copied to a scratch dir
#           outside the tree; never into the repository; its payloads are
#           redacted by the probe's --redact)
#   long60  tools/create_long_document.py --pages 60 (generated into the same
#           scratch dir; not committed)
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
install_dir="$here/../native-lok-26-8/build/instdir/program"
if [ ! -d "$install_dir" ]; then echo "native build missing: $install_dir" >&2; exit 1; fi
install_dir="$(cd "$install_dir" && pwd)"

out="${1:-$here/../findings/evidence/link-batch/page-rectangles}"
rounds="${2:-3}"
scratch="${SCRATCH_DIR:?set SCRATCH_DIR to a directory outside the repository}"
mkdir -p "$out" "$scratch"; out="$(cd "$out" && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
round_dir="$out/round-$stamp"; mkdir -p "$round_dir"

owner_src="$here/build/scratch-m3-production-ui/PMPC指南.odt"
[ -f "$owner_src" ] || { echo "owner document missing: $owner_src" >&2; exit 1; }

probe="$round_dir/native-page-rectangles"
build_cmd="g++ -std=c++17 -O2 -I<libreoffice-26-8>/include tools/native_page_rectangles.cpp -ldl -lpthread -o native-page-rectangles"
echo "$build_cmd" > "$round_dir/build-command.txt"
g++ -std=c++17 -O2 -I"$src/include" "$here/tools/native_page_rectangles.cpp" -ldl -lpthread -o "$probe"

long_src="$scratch/long60.odt"
gen_cmd="python3 tools/create_long_document.py --pages 60 --out <scratch>/long60.odt"
echo "$gen_cmd" > "$round_dir/create-long-document-command.txt"
python3 "$here/tools/create_long_document.py" --pages 60 --out "$long_src" \
  | tee -a "$round_dir/create-long-document-command.txt"

{
  sha256sum "$here/tools/native_page_rectangles.cpp" "$here/tools/run_native_page_rectangles.sh" \
    "$here/tools/create_long_document.py"
  # Names only for the owner's document: record the hash, not the contents.
  echo "$(sha256sum "$owner_src" | cut -d' ' -f1)  <owner document PMPC.odt, not in the tree>"
  echo "$(sha256sum "$long_src" | cut -d' ' -f1)  <generated long60.odt, not in the tree>"
} > "$round_dir/inputs.sha256"

status=0
for doc in owner long60; do
  for r in $(seq 1 "$rounds"); do
    work="$scratch/work-$doc-$r"; rm -rf "$work"; mkdir -p "$work/profile"
    if [ "$doc" = owner ]; then
      cp "$owner_src" "$work/doc.odt"; redact="--redact"
    else
      cp "$long_src" "$work/doc.odt"; redact=""
    fi
    # the copy must be byte-identical to the hashed input
    cmp "$work/doc.odt" "$([ "$doc" = owner ] && echo "$owner_src" || echo "$long_src")"
    echo "== $doc round $r =="
    set +e
    SAL_USE_VCLPLUGIN=svp "$probe" "$install_dir" "file://$work/profile" "file://$work/doc.odt" \
      "$doc" "$r" $redact >"$round_dir/$doc-r$r.jsonl" 2>"$round_dir/$doc-r$r.stderr"
    s=$?
    set -e
    echo "exit $s" | tee "$round_dir/$doc-r$r.exit"
    [ "$s" -eq 0 ] || status=1
    rm -rf "$work"
  done
done
rm -f "$probe"
date -u +%Y-%m-%dT%H:%M:%SZ > "$round_dir/ended-utc.txt"
echo "round: $round_dir"
exit "$status"
