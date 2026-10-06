#!/usr/bin/env bash
# m3-locks README rule 5 / SPEC-M3-production-ui §12: the one repeat of the
# counted locks run allowed by finding 112's ruling.  Nothing else runs.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
LOG=wasm_sdk_probe/build/m3-count-2026-10-06b
say() { echo "$(date -u +%FT%TZ) $*" | tee -a $LOG/chain.txt; }
say "START host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) runner $(sha256sum wasm_sdk_probe/tools/check_m3_locks.py | cut -c1-16) page $(sha256sum wasm_sdk_probe/dist/e2-editor-app.js | cut -c1-12)"
say "counted locks (repeat) begin"
python3 wasm_sdk_probe/tools/check_m3_locks.py --label counted > $LOG/counted-locks.log 2>&1
say "counted locks (repeat) exit $? :: $(tail -n 1 $LOG/counted-locks.log | cut -c1-300)"
say "DONE"
