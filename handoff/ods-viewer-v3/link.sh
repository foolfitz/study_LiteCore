#!/usr/bin/env bash
# Owner-run first SDK link of ods-viewer-v3 (SPEC-M4-viewer-v3 sections 4, 9).
# From the repo root: bash handoff/ods-viewer-v3/link.sh
# The core is already built; this does not invoke its make or touch ddev.
set -uo pipefail
if [ "$#" -ne 0 ]; then
    echo "Usage: bash handoff/ods-viewer-v3/link.sh"
    exit 2
fi
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 2
case "$(../wasm-lite/tools/emsdk/upstream/emscripten/emcc --version 2>/dev/null | head -1)" in
    *' 4.0.10 '*) ;;
    *) echo "STOP: emcc is not 4.0.10"; exit 2 ;;
esac
mkdir -p build || exit 2
log=$(mktemp "build/link-ods-viewer-v3-$(date +%Y%m%dT%H%M%S)-XXXXXX.log") || exit 2
echo "== ods-viewer-v3 link; log: wasm_sdk_probe/$log"
make ALLOW_FROZEN_RELINK=1 \
    ODS_VIEWER_V3_CORE=../wasm-lite/build-ods-viewer-v2 \
    dist/profiles/ods-viewer-v3/sdk-manifest.json 2>&1 | tee "$log"
statuses=("${PIPESTATUS[@]}")
ln -sf "${log##*/}" build/link-ods-viewer-v3.log
echo "make exit ${statuses[0]}, tee exit ${statuses[1]} (log: wasm_sdk_probe/$log). Tell Codex."
if [ "${statuses[0]}" -ne 0 ]; then
    exit "${statuses[0]}"
fi
exit "${statuses[1]}"
