#!/usr/bin/env bash
# Link batch, native step: callbacks after Shift+<key> and after plain keys on a range.
# Brief: handoff/tasks/TASK-2026-10-13h-link-native-extend-signatures.md
# Usage: tools/run_link_native_extend_signatures.sh [OUT_DIR] [ROUNDS] [SETTLE_QUIET_MS]
#
# Each round is its own process with its own profile and its own copy of the
# fixture (LibreOffice writes a lock file next to whatever it loads).  Rounds run
# ONE AFTER THE OTHER (not in parallel: this machine is shared with browser
# measurements that are sensitive to CPU load), under nice -n 10.  Arms inside a
# process run one after the other and every arm is a fresh document load.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="$(cd "$here/.." && pwd)"
src="$root/libreoffice-26-8"
install_dir="$root/native-lok-26-8/build/instdir/program"
if [ ! -d "$install_dir" ]; then echo "native build missing: $install_dir" >&2; exit 1; fi
install_dir="$(cd "$install_dir" && pwd)"

out="${1:-$root/findings/evidence/link-batch/extend-signatures}"
rounds="${2:-3}"
quiet="${3:-800}"
mkdir -p "$out"; out="$(cd "$out" && pwd)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="$out/run-$stamp"; mkdir -p "$run_dir"

fx="$here/test-docs/link-batch/extend-signatures.fodt"
gen="$here/test-docs/link-batch/gen_extend_signatures.py"
tool_src="$here/tools/link_native_extend_signatures.cpp"
probe="$run_dir/link-native-extend-signatures"

echo "g++ -std=c++17 -O2 -I<libreoffice-26-8>/include tools/link_native_extend_signatures.cpp -ldl -lpthread -o link-native-extend-signatures" > "$run_dir/build-command.txt"
g++ -std=c++17 -O2 -I"$src/include" "$tool_src" -ldl -lpthread -o "$probe"

# The tool carries its own copy of the fixture's paragraph texts; refuse to run if they drifted.
"$probe" --paragraphs > "$run_dir/tool-paragraphs.txt"
python3 -I - "$fx" "$run_dir/tool-paragraphs.txt" <<'PY'
import sys
import xml.etree.ElementTree as ET
ns = {"t": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
root = ET.parse(sys.argv[1]).getroot()
paras = []
for el in root.iter():
    if el.tag in ("{%s}p" % ns["t"], "{%s}h" % ns["t"]):
        paras.append("".join(el.itertext()))
tool = open(sys.argv[2], encoding="utf-8").read().split("\n")
if tool and tool[-1] == "":
    tool.pop()
if paras != tool:
    sys.exit("fixture paragraphs differ from the tool's kParas:\n fixture=%r\n tool=%r" % (paras, tool))
print("fixture paragraphs match the tool:", len(paras))
PY

{
  echo "date-utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "uname: $(uname -a)"
  echo "nproc: $(nproc)"
  echo "loadavg-at-start: $(cat /proc/loadavg)"
  echo "settle-quiet-ms: $quiet"
  echo "native install: $install_dir"
  ls -l --time-style=full-iso "$install_dir/libmergedlo.so" "$install_dir/libsdlo.so" 2>/dev/null | sed 's/^/  /' || true
  for d in "$root/native-lok-26-8/src" "$src"; do
    echo "source tree: $d"
    echo "  HEAD: $(git -C "$d" rev-parse HEAD)"
    echo "  HEAD subject: $(git -C "$d" log -1 --format='%ci %s')"
    echo "  status --short (tracked changes only):"
    git -C "$d" status --short --untracked-files=no | sed 's/^/    /'
    echo "  diff HEAD sha256: $(git -C "$d" diff HEAD | sha256sum | cut -d' ' -f1)"
  done
} > "$run_dir/source-commits.txt"

sha256sum "$fx" "$gen" "$tool_src" "$here/tools/run_link_native_extend_signatures.sh" > "$run_dir/inputs.sha256"
cp "$tool_src" "$run_dir/tool-source-as-run.cpp"
cp "$fx" "$run_dir/fixture-as-run.fodt"

status=0
for r in $(seq 1 "$rounds"); do
  work="$run_dir/work-$r"; mkdir -p "$work/profile"
  cp "$fx" "$work/fx.fodt"
  (
    cd "$work"
    SAL_USE_VCLPLUGIN=svp nice -n 10 "$probe" "$install_dir" "file://$work/profile" "file://$work/fx.fodt" "$r" "$quiet" \
      >"$run_dir/arms-r$r.jsonl" 2>"$run_dir/arms-r$r.stderr"
    echo "exit $?" > "$run_dir/arms-r$r.exit"
  ) || status=1
  cat "$run_dir/arms-r$r.exit"
  rm -rf "$work"
done
rm -f "$probe"
echo "loadavg-at-end: $(cat /proc/loadavg)" >> "$run_dir/source-commits.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$run_dir/ended-utc.txt"
echo "run: $run_dir"
exit "$status"
