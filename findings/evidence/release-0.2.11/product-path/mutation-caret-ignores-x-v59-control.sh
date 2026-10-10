#!/bin/bash
# Attribution control: `--mutate caret-ignores-x` on the SHIPPED v59 page (18c8afbe...), same runner, Chrome.
# dist/e2-editor-app.js is swapped to the v59 bytes for this one run and restored (sha checked) afterwards.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
PP=../findings/evidence/release-0.2.11/product-path
cp dist/e2-editor-app.js $PP/.p-page.bak
git show d30a1b4c:wasm_sdk_probe/web/e2-editor-app.js > dist/e2-editor-app.js
echo "== $(date -u +%FT%TZ) dist $(sha256sum dist/e2-editor-app.js | cut -c1-16) (v59)"
timeout 1800 python3 tools/run_e2_c_product_path.py --browser chrome --mutate caret-ignores-x --out $PWD/$PP/mutation-caret-ignores-x-chrome-v59-control.json > $PP/mutation-caret-ignores-x-chrome-v59-control.stdout.txt 2> $PP/mutation-caret-ignores-x-chrome-v59-control.stderr.txt
echo "== $(date -u +%FT%TZ) exit $?"
cp $PP/.p-page.bak dist/e2-editor-app.js && rm $PP/.p-page.bak
echo "== restored dist $(sha256sum dist/e2-editor-app.js | cut -c1-16) (expect 36c2b18baa8340c5)"
