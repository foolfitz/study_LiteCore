#!/usr/bin/env bash
# Derived from ../runs-0.2.44/read-0.2.44.sh 2026-11-02 (specs/SPEC-M3-K-0.2.45.md).  Closed list of differences: paths, the K 0.2.45 tool
# names, e2-editor-v29, the pre-chain evidence under k-0.2.45.  (0.2.44's header follows.)  Derived from ../runs-0.2.26/read-0.2.26.sh 2026-10-31 (specs/SPEC-M3-K-0.2.44.md).  Closed list of differences: paths and
# pooled-0.2.44; section 4 copies the 0.2.26 red reports into the K directory (K ruling item 1), then judge_counted_m2.py
# --uncounted --profile e2-editor-v29 (expected exit 4, red PASS, oneRunner true, K ruling item 2) and read_k_0245_merge.py;
# section 6 is read_k_0245_product_path.py; section 7 lists the two pre-chain negatives.  The production-UI expectation, the
# red-case modes and the C2 judges are 0.2.26's.  (0.2.24's header follows.)  0.2.24's copy of ../runs-0.2.23/read-0.2.23.sh (paths moved; the production-UI expectation now 28/28, the A3-1 page-number
# mutation added in 74489aa0).  After the 0.2.23 chain's DONE (ruling J-a.2: the reader is the main session, never while the chain runs): the readings,
# printed and saved.  Shape: runs-0.2.13/red-cases-2026-10-12.sh, plus the merge judge, the C2 judges and the product-path
# reader.  This script only runs existing judges/red-case modes and saves their output; it applies no reading table:
#   - C2's three (or six) verdict lines are read by the main session against J-b.2's table (no W-b2 reader exists);
#   - the product-path verdict is the reader's SUMMARY line (spec 34.7), read after the reader is made red once on
#     scratch copies by hand (precedent findings/evidence/release-0.2.12/product-path/judge-red-offline.txt);
#   - the descriptive v21-vs-0.2.24-v20 comparison (PREDICTION.md) is read by hand (precedent old-vs-new-v19.txt).
#   bash findings/evidence/m3-production-ui/runs-0.2.26/read-0.2.26.sh [LOGDIR]   (default: the newest build/m3-count-*)
set -u
REPO=/home/jiajun/LibreOffice/study_LiteCore
cd "$REPO" || exit 9
T=wasm_sdk_probe/tools
E=findings/evidence/m3-production-ui/runs-0.2.45
R=findings/evidence/release-0.2.45
PP=$R/product-path; MM=$R/merge-m2; C2=$R/c2
LOG=${1:-$(ls -d wasm_sdk_probe/build/m3-count-* 2>/dev/null | sort | tail -1)}
[ -n "$LOG" ] && [ -s "$LOG/chain.txt" ] || { echo "no chain log at ${LOG:-<none>}"; exit 2; }
STARTED=$LOG/started
[ -e "$STARTED" ] || { echo "$STARTED missing: this log directory has no START marker (preflight refused?)"; exit 2; }
STAMP=$(basename "$LOG" | sed 's/^m3-count-//')
h() { sha256sum "$1" | cut -c1-16; }
newest_after() {  # dir -> the newest *.json in it written after START, or nothing
  find "$1" -maxdepth 1 -name '*.json' -newer "$STARTED" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-
}

echo "== chain $LOG (tree $(git rev-parse --short HEAD))"
grep -E 'REFUSED|STOP|IDENTITY|^[^ ]* START |DONE| exit |RERUN' "$LOG/chain.txt" | grep -v ' DESK '
cp "$LOG/chain.txt" "$E/chain-$STAMP.out"
echo "(chain log copied to $E/chain-$STAMP.out; desk lines: $(grep -c ' DESK ' "$LOG/chain.txt"))"
if ! grep -q ' DONE' "$LOG/chain.txt"; then echo "NO DONE LINE: not a count (J-a.2); readings below are partial"; fi

# 1. production UI: the three counted reports pooled under the first, then --red-cases (as 0.2.12 / 0.2.13)
echo; echo "== 1. production UI red cases on the pooled counted reports"
python3 - "$E" "$LOG" <<'PY'
import json, sys
from pathlib import Path
E, LOG = Path(sys.argv[1]), Path(sys.argv[2])
# No counted-B3x-x2.json: B3x is withdrawn from the 0.2.23 count (SPEC-M3-link-batch 17.3), so the 13 A1-5 mutations
# find no B3x run and the runner's --red-cases exits 1 by its own rule; the reading is "red cases: N/N" with exactly
# those 13 "no passing B3x run" notes.
names = ["counted-KR-x3.json", "counted-ctl-S-P.json"]
missing = [n for n in names if not (E / n).is_file()]
if missing:
    print("MISSING counted production UI report(s):", missing); sys.exit(1)
reports = [json.loads((E / n).read_text()) for n in names]
pooled = dict(reports[0]); pooled["runs"] = [run for r in reports for run in r["runs"]]
(LOG / "pooled-0.2.45.json").write_text(json.dumps(pooled))
print("static identical:", all(r["static"] == reports[0]["static"] for r in reports), "counted:", [r["counted"] for r in reports],
      "runner:", {r["runnerSha256"][:16] for r in reports}, "cells:", [r.get("score", {}).get("cells") for r in reports])
PY
if [ -s "$LOG/pooled-0.2.45.json" ]; then
  { echo "pooled: counted-KR-x3.json + counted-ctl-S-P.json (runs concatenated under the first report; B3x withdrawn, 17.3)";
    echo "expected: 'red cases: 28/28' (the C keying recorded in the report: declared True), 13 'no passing B3x run' notes, exit 1 by the runner's every-mutation rule";
    python3 $T/check_m3_production_ui.py --red-cases "$LOG/pooled-0.2.45.json"; echo "exit $?"; } > "$E/red-cases-on-counted-pooled.txt" 2>&1
  grep -E '^red cases|^exit|STAYED GREEN|C keying' "$E/red-cases-on-counted-pooled.txt"; echo "no-passing-run notes: $(grep -v '^expected:' "$E/red-cases-on-counted-pooled.txt" | grep -c 'no passing') (13 expected, all B3x)"
fi

# 2. the six runners, each on its counted report written during this chain
echo; echo "== 2. the six runners' red cases"
: > "$E/red-cases-six.txt"
for r in page_honesty locks versions assets host_entry same_second; do
  d=findings/evidence/m3-$(echo $r | tr _ -)/runs
  rep=$(newest_after "$d")
  echo "== $r ${rep:-NO REPORT FROM THIS CHAIN in $d}" >> "$E/red-cases-six.txt"
  if [ -n "$rep" ]; then
    python3 $T/check_m3_$r.py --red-cases "$rep" 2>&1 | tail -5 >> "$E/red-cases-six.txt"
    echo "exit ${PIPESTATUS[0]}" >> "$E/red-cases-six.txt"
  fi
done
cat "$E/red-cases-six.txt"

# 3. autosave and new-document, each on its counted report written during this chain
echo; echo "== 3. autosave and new-document red cases"
rep=$(newest_after findings/evidence/m3-autosave/runs)
{ echo "== autosave ${rep:-NO REPORT FROM THIS CHAIN}"; [ -n "$rep" ] && { python3 $T/check_m3_autosave.py --red-cases "$rep" 2>&1; echo "exit ${PIPESTATUS[0]}"; }; } > "$E/red-cases-autosave.txt"
tail -3 "$E/red-cases-autosave.txt"
rep=$(newest_after findings/evidence/new-document/runs)
{ echo "== new-document ${rep:-NO REPORT FROM THIS CHAIN}"; [ -n "$rep" ] && { python3 $T/check_m3_new_document.py --red-cases "$rep" 2>&1; echo "exit ${PIPESTATUS[0]}"; }; } > "$E/red-cases-new-document.txt"
tail -3 "$E/red-cases-new-document.txt"

# 4. the merge count: the historical reds copied in, then the frozen judge --uncounted (K ruling items 1, 2) and the counted-ness reader (item 3)
echo; echo "== 4. merge count: judge_k_0245_merge.py --dir $MM --profile e2-editor-v29 --uncounted (expected exit 4, keying abiVersion 6; spec append 2)"
for B in chrome firefox; do
  [ -e "$MM/red-$B.json" ] || { cp findings/evidence/release-0.2.26/merge-m2/red-$B.json findings/evidence/release-0.2.26/merge-m2/red-$B.stderr.txt "$MM/"; cp -r findings/evidence/release-0.2.26/merge-m2/red-$B.docs "$MM/"; }
done
python3 $T/judge_k_0245_merge.py --dir "$MM" --profile e2-editor-v29 --uncounted > "$MM/judge-output.txt" 2>&1
code=$?
{ echo "exit=$code"; echo "reader $(sha256sum $T/judge_counted_m2.py | cut -d' ' -f1)"; echo "runner $(sha256sum $T/run_merge_wasm_shakedown.py | cut -d' ' -f1)";
  echo "wasm $(sha256sum wasm_sdk_probe/dist/profiles/e2-editor-v29/probe.wasm | cut -d' ' -f1)"; echo "judged $(date -u +%FT%TZ) from chain $STAMP"; } > "$MM/judge-exit.txt"
cat "$MM/judge-exit.txt"; grep -E '^VERDICT|^identity|keyed on|^red|red ' "$MM/judge-output.txt" | head -12
python3 $T/read_k_0245_merge.py --dir "$MM" > "$MM/read-k-merge.json" 2>&1; echo "read_k_0245_merge exit $?"; grep -E 'verdict' "$MM/read-k-merge.json"
python3 $T/read_k_0245_merge.py --dir "$MM" --self-test > "$MM/read-k-merge-self-test.json" 2>&1; echo "self-test exit $?"; grep -E 'selfTest' "$MM/read-k-merge-self-test.json"

# 5. C2: the judges, unchanged, per run (r4-r6 too when the extension ran); the reading table is J-b.2's, applied by the reader
echo; echo "== 5. C2 judges per run (judge_c2.py; judge_p2.py on ratio-1)"
for K in 1 2 3 4 5 6; do
  D=$C2/r$K
  [ -s "$D/chain.txt" ] || { [ $K -le 3 ] && echo "r$K: no chain.txt -> this run is missing (J-b.2: fewer than three complete runs = NOT_ESTABLISHED)"; continue; }
  python3 -I findings/evidence/c-prime/c2/judge_c2.py --dir "$D" > "$D/judge-output.txt" 2>&1; c=$?
  echo "exit $c" >> "$D/judge-output.txt"
  python3 -I findings/evidence/typing-latency/judge_p2.py --dir "$D/ratio-1" > "$D/p2-output.txt" 2>&1; p=$?
  echo "exit $p" >> "$D/p2-output.txt"
  echo "-- r$K judge_c2 exit $c :: $(grep -E '^VERDICT|^PASS|^FAIL|^REFUSED' "$D/judge-output.txt" | tail -1 | cut -c1-200)"
  grep -E 'owner-gap80' "$D/judge-output.txt" | grep -iE 'chrome' | grep -iE 'max' | head -3
  grep -E 'FAIL|REFUSED' "$D/judge-output.txt" | grep -v '^VERDICT\|^REFUSED:' | head -5
  echo "   judge_p2 exit $p :: $(grep -E '^VERDICT|^PASS|^FAIL|^REFUSED' "$D/p2-output.txt" | tail -1 | cut -c1-200)"
done
echo "(reading: a FAIL run is attributable to 135 only when its ONLY FAIL line is 'chrome owner-gap80 on-screen max' and the max is < 200 ms; table in RULING J-b.2)"

# 6. the product-path net: read_k_0245_product_path.py against the 0.2.26 v21 records
echo; echo "== 6. product-path reader (read_k_0245_product_path.py)"
EN=findings/evidence/k-0.2.45/enter-replay/report.json
python3 $T/read_k_0245_product_path.py --dir "$PP" --enter-report "$EN" > "$PP/read-k-path.json" 2>&1; echo "read_k_0245_product_path exit $?"
python3 - "$PP/read-k-path.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); print(d.get("verdict"), d.get("why", ""), *d.get("problems", []), sep="\n  "); print(d.get("specialCells"))
PY
python3 $T/read_k_0245_product_path.py --dir "$PP" --enter-report "$EN" --self-test > "$PP/read-k-path-self-test.json" 2>&1; echo "self-test exit $?"; grep -E 'selfTest' "$PP/read-k-path-self-test.json"

# 7. the two pre-chain negatives (spec section 5)
echo; echo "== 7. page-gate negative and Enter replay"
python3 - <<'PY'
import json
g = json.load(open("findings/evidence/k-0.2.45/legacy-v8-gate/report.json"))
print("page gate:", g.get("verdict"), "page", g.get("sourceSha256", "")[:16], "v8 wasm", g.get("v8WasmSha256", "")[:16], [r["inspection"].get("verdict") for r in g["runs"]],
      "insertRequests", [r["inspection"].get("insertRequests") for r in g["runs"]])
print("enter replay:", json.load(open("findings/evidence/k-0.2.45/enter-replay/report.json")).get("verdict"))
PY
echo "(the reader was made red before the chain: findings/evidence/k-0.2.45/readers/)"
echo; echo "read DONE; outputs: $E/red-cases-*.txt $E/chain-$STAMP.out $MM/judge-output.txt $MM/read-k-merge.json $C2/r*/judge-output.txt $C2/r*/p2-output.txt $PP/read-k-path.json"
