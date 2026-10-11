#!/usr/bin/env bash
# After the 0.2.12 chain: red cases on the counted reports (as RESULT-0.2.9 did).
set -u
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe || exit 9
LOG=build/m3-count-2026-10-11
E=../findings/evidence/m3-production-ui/runs-0.2.12
T=tools
# 1. production UI: the three counted reports pooled under the first
python3 - "$E" <<'PY'
import json, sys
from pathlib import Path
E = Path(sys.argv[1])
names = ["counted-KR-x3.json", "counted-ctl-S-P.json", "counted-B3x-x2.json"]
reports = [json.loads((E / n).read_text()) for n in names]
pooled = dict(reports[0]); pooled["runs"] = [run for r in reports for run in r["runs"]]
Path("/home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/m3-count-2026-10-11/pooled-0.2.12.json").write_text(json.dumps(pooled))
print("static identical:", all(r["static"] == reports[0]["static"] for r in reports), "counted:", [r["counted"] for r in reports], "runner:", {r["runnerSha256"][:16] for r in reports})
PY
{ echo "pooled: counted-KR-x3.json + counted-ctl-S-P.json + counted-B3x-x2.json (runs concatenated under the first report)";
  python3 $T/check_m3_production_ui.py --red-cases /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe/build/m3-count-2026-10-11/pooled-0.2.12.json; echo "exit $?"; } > $E/red-cases-on-counted-pooled.txt 2>&1
# 2. the six runners, each on its counted report (the newest report in its runs/ dir written during this chain)
: > $E/red-cases-six.txt
for r in page_honesty locks versions assets host_entry same_second; do
  d=../findings/evidence/m3-$(echo $r | tr _ -)/runs
  rep=$(ls -t $d/*.json 2>/dev/null | head -1)
  echo "== $r $rep" >> $E/red-cases-six.txt
  python3 $T/check_m3_$r.py --red-cases $rep  2>&1 | tail -5 >> $E/red-cases-six.txt
  echo "exit ${PIPESTATUS[0]}" >> $E/red-cases-six.txt
done
cat $E/red-cases-on-counted-pooled.txt | tail -3; cat $E/red-cases-six.txt
