#!/usr/bin/env bash
# Finding 129, criterion 129-B on the bytes that ship (SPEC-M3-autosave §9.4): tools/probe_129_m4_wasm.py --final
# (page under test = dist/ = 0.2.13's page, red control = 0.2.12's page from the archived engine package), one
# round in Chrome, then in Firefox, one after the other (never in parallel: the probe times key-to-move).  Usage:
#   tools/run_probe_129_final.sh DOCS_DIR [ROUND_LABEL] [ROUNDS]
# DOCS_DIR holds the three converted .odt files (as tools/run_probe_129_m4.sh; M4's rounds keep a copy in docs/).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docs="$(cd "${1:?DOCS_DIR}" && pwd)"
label="${2:-1}"
rounds="${3:-1}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
round_dir="$here/../findings/evidence/129/final/round-$stamp"
mkdir -p "$round_dir/docs"
cp "$docs"/arrow-selection.odt "$docs"/arrow-selection-shapes.odt "$docs"/arrow-selection-wrap.odt "$round_dir/docs/"
{
  sha256sum "$here/tools/probe_129_m4_wasm.py" "$here/tools/run_probe_129_final.sh" "$here/dist/e2-editor-app.js" \
    "$here/build/archive/host-0.2.12-engine-45cdcedfc0fe7e61/files/e2-editor-app.js.gz" \
    "$here/test-docs/f129/arrow-selection.fodt" "$here/test-docs/f129/arrow-selection-shapes.fodt" \
    "$here/test-docs/f129/arrow-selection-wrap.fodt" "$round_dir"/docs/*.odt
} > "$round_dir/inputs.sha256"
cp "$here/tools/probe_129_m4_wasm.py" "$round_dir/probe_129_m4_wasm.as-run.py"
{ date -u +%Y-%m-%dT%H:%M:%SZ; cat /proc/loadavg; grep -E 'MemTotal|MemAvailable|SwapFree' /proc/meminfo; } > "$round_dir/machine-at-start.txt"
status=0
for browser in chrome firefox; do
  python3 "$here/tools/probe_129_m4_wasm.py" --final --browser "$browser" --out "$round_dir" --docs "$round_dir/docs" \
    --round-label "$label" --rounds "$rounds" > "$round_dir/stdout-$browser.txt" 2>&1 || status=1
  date -u +%Y-%m-%dT%H:%M:%SZ > "$round_dir/ended-$browser-utc.txt"
done
{ date -u +%Y-%m-%dT%H:%M:%SZ; cat /proc/loadavg; grep -E 'MemTotal|MemAvailable|SwapFree' /proc/meminfo; } > "$round_dir/machine-at-end.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$round_dir/ended-utc.txt"
echo "round: $round_dir"
exit "$status"
