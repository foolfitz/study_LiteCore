#!/bin/bash
# The revert rehearsal for e2-editor-v12, INCLUDING step 3 -- the freeze and
# repoint, which the 2026-08-28 rehearsal discovered and did not itself rehearse.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
SP="$1"
OUT="$SP/rehearsal"
export OUT
EV=../findings/evidence/queue-v12-cutover-soak
SHA=3dfdcfef4abfe6b723b573f35e8ec8f885dcc42a8ed4d8338ad2381eb386f50f
V44=e2/editor-shell-v2-bundle-v44.json

# --- backups. dist/ is NOT tracked by git, so git alone cannot restore it. ---
cp web/e2-editor-app.js            "$OUT/backup-web-page.js"
cp dist/e2-editor-app.js           "$OUT/backup-dist-page.js"
cp tools/build_e2_c_shell_bundle.py "$OUT/backup-builder.py"

restore() {
  echo "== RESTORE (trap or explicit) =="
  cp "$OUT/backup-web-page.js"  web/e2-editor-app.js
  cp "$OUT/backup-dist-page.js" dist/e2-editor-app.js
  cp "$OUT/backup-builder.py"   tools/build_e2_c_shell_bundle.py
  rm -f "$V44"
}
trap restore EXIT

hash_of() { python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:16])" "$1"; }

echo "== BASELINE =="
echo "web  $(hash_of web/e2-editor-app.js)"
echo "dist $(hash_of dist/e2-editor-app.js)"
grep -n '^MANIFEST' tools/build_e2_c_shell_bundle.py
ls e2/editor-shell-v2-bundle-v44.json 2>/dev/null && echo "!! v44 ALREADY EXISTS -- abort" && exit 1

echo
echo "== STEP 1: write the cutover page =="
python3 tools/build_cutover_page.py --profile e2-editor-v12 --write --expect-sha256 "$SHA" || exit 1

echo
echo "== STEP 2: stage into dist =="
cp web/e2-editor-app.js dist/e2-editor-app.js
echo "dist now $(hash_of dist/e2-editor-app.js)"

echo
echo "== 2b: PROVE step 3 is needed -- freeze NOTHING, run the net =="
python3 tools/run_e2_c_product_path.py --browser chrome \
    --out "$OUT/after-cutover-without-step-3.json" > "$OUT/run-no-step3.log" 2>&1
python3 tools/check_usable_editor.py --report "$OUT/after-cutover-without-step-3.json" \
    --output "$OUT/check-no-step3.json" > /dev/null 2>&1
python3 - <<'PY'
import json
r=json.load(open(__import__('os').environ['OUT']+"/after-cutover-without-step-3.json"))
c=json.load(open(__import__('os').environ['OUT']+"/check-no-step3.json"))
print("  run ok:", r.get("ok"), "| checklist ok:", c.get("ok"))
for p in (c.get("problems") or [])[:3]: print("   problem:", p[:170])
PY

echo
echo "== STEP 3: freeze generation v44, then repoint MANIFEST =="
python3 tools/build_e2_c_shell_bundle.py --manifest "$V44" \
    --frozen-date 2026-09-03 --write 2>&1 | tail -20
python3 - <<'PY'
import pathlib
p=pathlib.Path("tools/build_e2_c_shell_bundle.py")
s=p.read_text(encoding="utf-8")
old='MANIFEST = Path("e2/editor-shell-v2-bundle-v43.json")'
new='MANIFEST = Path("e2/editor-shell-v2-bundle-v44.json")'
assert s.count(old)==1, f"MANIFEST anchor count {s.count(old)}"
p.write_text(s.replace(old,new,1),encoding="utf-8")
print("  MANIFEST repointed to v44")
PY
grep -n '^MANIFEST' tools/build_e2_c_shell_bundle.py

echo
echo "== RUN THE NET on the cut-over page, WITH the generation frozen =="
python3 tools/run_e2_c_product_path.py --browser chrome \
    --out "$OUT/after-cutover-with-step-3.json" > "$OUT/run-step3.log" 2>&1
python3 tools/check_usable_editor.py --report "$OUT/after-cutover-with-step-3.json" \
    --output "$OUT/check-step3.json" > /dev/null 2>&1
python3 - <<'PY'
import json, os
o=os.environ['OUT']
r=json.load(open(o+"/after-cutover-with-step-3.json"))
c=json.load(open(o+"/check-step3.json"))
from collections import Counter
print("  run ok:", r.get("ok"), "| checklist ok:", c.get("ok"))
print("  composition:", dict(Counter(x['outcome'] for x in r['checks'])))
print("  servedShell:", json.dumps(r.get('servedShell'))[:200])
for p in (c.get("problems") or [])[:3]: print("   problem:", p[:170])
PY

echo
echo "== REVERT all three =="
restore
trap - EXIT
echo "web  $(hash_of web/e2-editor-app.js)"
echo "dist $(hash_of dist/e2-editor-app.js)"
grep -n '^MANIFEST' tools/build_e2_c_shell_bundle.py
ls e2/editor-shell-v2-bundle-v44.json 2>/dev/null && echo "!! v44 STILL PRESENT" || echo "v44 removed"

echo
echo "== RUN THE NET after the revert =="
python3 tools/run_e2_c_product_path.py --browser chrome \
    --out "$OUT/after-revert.json" > "$OUT/run-revert.log" 2>&1
python3 tools/check_usable_editor.py --report "$OUT/after-revert.json" \
    --output "$OUT/check-revert.json" > /dev/null 2>&1
python3 - <<'PY'
import json, os
from collections import Counter
o=os.environ['OUT']
r=json.load(open(o+"/after-revert.json"))
c=json.load(open(o+"/check-revert.json"))
print("  run ok:", r.get("ok"), "| checklist ok:", c.get("ok"))
print("  composition:", dict(Counter(x['outcome'] for x in r['checks'])))
for p in (c.get("problems") or [])[:3]: print("   problem:", p[:170])
PY

echo
echo "== TREE AFTER =="
cd /home/jiajun/LibreOffice/study_LiteCore && git status --short && echo "(clean)"
