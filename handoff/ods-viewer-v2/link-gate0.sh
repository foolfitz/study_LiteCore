#!/usr/bin/env bash
# Fallback F's link of ods-viewer-v2 on build-a11y-gate0 (handoff/RUNBOOK-link-ods-viewer-v2.md F1,
# specs/SPEC-M4-viewer-v2.md 7.2).  Run by the owner:
#
#   bash handoff/ods-viewer-v2/link-gate0.sh
#
# Writes only build/ods/viewer-v2/, dist/profiles/ods-viewer-v2/ and the log.  The last line make prints
# is the wasm's gzip size against the cap.
set -uo pipefail
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 2
make ALLOW_FROZEN_RELINK=1 ODS_VIEWER_V2_CORE=../wasm-lite/build-a11y-gate0 \
  dist/profiles/ods-viewer-v2/sdk-manifest.json 2>&1 | tee build/link-ods-viewer-v2-gate0.log
status=${PIPESTATUS[0]}
echo "make exit $status (log: wasm_sdk_probe/build/link-ods-viewer-v2-gate0.log). Tell Claude."
exit "$status"
