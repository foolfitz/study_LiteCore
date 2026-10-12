#!/usr/bin/env bash
# Finding 129 M4: one counted round of tools/probe_129_m4_wasm.py in Chrome, then in Firefox, one after the other
# (never in parallel: the brief times the key-to-move interval).  Usage:
#   tools/run_probe_129_m4.sh DOCS_DIR [ROUND_LABEL] [ROUNDS]
# DOCS_DIR holds arrow-selection.odt, arrow-selection-shapes.odt, arrow-selection-wrap.odt, converted once with
#   soffice --headless --convert-to odt -env:UserInstallation=file://<throwaway> from test-docs/f129/*.fodt.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docs="$(cd "${1:?DOCS_DIR}" && pwd)"
label="${2:-1}"
rounds="${3:-1}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
round_dir="$here/../findings/evidence/129/m4/round-$stamp"
mkdir -p "$round_dir/docs"
cp "$docs"/arrow-selection.odt "$docs"/arrow-selection-shapes.odt "$docs"/arrow-selection-wrap.odt "$round_dir/docs/"
{
  sha256sum "$here/tools/probe_129_m4_wasm.py" "$here/tools/run_probe_129_m4.sh" \
    "$here/build/m4-mirror/e2-editor-app.js" "$here/dist/e2-editor-app.js" \
    "$here/../findings/evidence/129/m4/page-129.patch" \
    "$here/test-docs/f129/arrow-selection.fodt" "$here/test-docs/f129/arrow-selection-shapes.fodt" \
    "$here/test-docs/f129/arrow-selection-wrap.fodt" "$round_dir"/docs/*.odt
} > "$round_dir/inputs.sha256"
cp "$here/tools/probe_129_m4_wasm.py" "$round_dir/probe_129_m4_wasm.as-run.py"
{ date -u +%Y-%m-%dT%H:%M:%SZ; cat /proc/loadavg; grep -E 'MemTotal|MemAvailable|SwapFree' /proc/meminfo; } > "$round_dir/machine-at-start.txt"
status=0
for browser in chrome firefox; do
  python3 "$here/tools/probe_129_m4_wasm.py" --browser "$browser" --out "$round_dir" --docs "$round_dir/docs" \
    --round-label "$label" --rounds "$rounds" > "$round_dir/stdout-$browser.txt" 2>&1 || status=1
  date -u +%Y-%m-%dT%H:%M:%SZ > "$round_dir/ended-$browser-utc.txt"
done
{ date -u +%Y-%m-%dT%H:%M:%SZ; cat /proc/loadavg; grep -E 'MemTotal|MemAvailable|SwapFree' /proc/meminfo; } > "$round_dir/machine-at-end.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$round_dir/ended-utc.txt"
echo "round: $round_dir"
exit "$status"
