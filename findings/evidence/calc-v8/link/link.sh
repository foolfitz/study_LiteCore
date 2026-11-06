#!/bin/bash
# SPEC-P-calc-copy 9 + SPEC-P-calc-zoom: the ods-editor-v8 link (owner-run).  From anywhere:
#   bash ~/LibreOffice/study_LiteCore/findings/evidence/calc-v8/link/link.sh
# Writes link-01.{stdout,stderr,exit,uptime}.txt and profile-SHA256SUMS beside this script.
here=$(cd "$(dirname "$0")" && pwd)
cd "$here/../../../../wasm_sdk_probe" || exit 1
uptime > "$here/link-01.uptime.txt"; pgrep -a make >> "$here/link-01.uptime.txt"
{ time make ods-editor-v8-dev ; } > "$here/link-01.stdout.txt" 2> "$here/link-01.stderr.txt"
code=$?
echo "$code" > "$here/link-01.exit.txt"
[ "$code" = 0 ] && (cd build/ods/editor-v8/profile && sha256sum probe.js probe.wasm sdk-worker.js sdk-manifest.json) > "$here/profile-SHA256SUMS"
echo "exit $code"; tail -3 "$here/link-01.stderr.txt"
