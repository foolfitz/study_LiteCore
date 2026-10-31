#!/usr/bin/env bash
# The count chain for host 0.2.44 / engine v28 / shell generation 82: the batched count of 0.2.27-0.2.44 (v22-v28).
# Spec specs/SPEC-M3-K-0.2.44.md (K ruling, findings/evidence/host-0.2.39/k-protocol-ruling/RULING.md, on 0.2.44's values).
# Derived from ../runs-0.2.26/chain-0.2.26.sh 2026-10-31.  Closed list of differences (spec section 4): the identity
# (PAGE, ARCHIVE), the evidence directories (runs-0.2.44, release-0.2.44), the candidate e2-editor-v28; the product-path
# net is the plain arm only, through tools/run_v82_f3_clipboard.py into $PP/<browser>-r<n>/ (K ruling item 5); the merge
# steps go through tools/run_k_0244_merge.py and there is no red step (K ruling item 1: the read script copies the 0.2.26
# reds); P0 also reads $PP; P6's static target is `make -i` with the red set exactly findings/evidence/k-0.2.44/p6-named-reds.txt
# (spec 4.1); OURS widened by run_v8|run_k_|read_k_ (chain-local); these lines.  The steps, the preflight's other items,
# the desk lines and the STOP rule are 0.2.26's.
# (0.2.24's header follows.)  The count chain for host 0.2.24 / engine v20: the batched count of 0.2.13-0.2.24 (0.2.24 = 0.2.23 + finding 145's page
# fix).  Copied from ../runs-0.2.23/chain-0.2.23.sh 2026-10-15; changed: the identity (PAGE, ARCHIVE), the evidence
# directories (runs-0.2.24, release-0.2.24) and these lines; the steps, the preflight and the STOP rule are 0.2.23's.
# 0.2.23's chain ran to DONE (20261015T025837Z) and its count did not hold: merge FAIL = finding 145.
# (0.2.23's header follows.)  The overnight count chain for host 0.2.23 / engine v20: the batched count of 0.2.13-0.2.23
# (SPEC-M3-autosave 9.4 「計數」 as deferred by 9.21; SPEC-M3-link-batch 7; ruling handoff/RULING-2026-10-15-pre-binding.md
# J-a (preflight, never abort a started chain, desk recorded never gated) and J-b (C2 three runs r1-r3)).
# Shape: findings/evidence/m3-production-ui/runs-0.2.13/chain-2026-10-12.sh, plus: the preflight block (J-a.1 P1-P5,
# P6 added here: the two judge test files no Makefile target runs), the desk line before each step, the new-document
# runner (SPEC-M3-new-document 4 「計數語意」, bound to 0.2.23 in part P3), the merge count (the modes v19's X7 ran,
# findings/evidence/v19/chain.sh, on e2-editor-v20) and the C2 chain three times (findings/evidence/136/guard-r2/c2/chain-c2.sh's
# shape).  One runner at a time: every M3 runner clears the whole oc_files_lock table.
#
# Start (P5 is an argument, see README.md):
#   cd /home/jiajun/LibreOffice/study_LiteCore
#   setsid nohup bash findings/evidence/m3-production-ui/runs-0.2.44/chain-0.2.44.sh \
#        --owner-window "<window>, agreed by the owner at <time>" > /dev/null 2>&1 &
# Preflight only (runs P1-P6, prints every reading, writes nothing but temp files, exits with the number of refusals):
#   bash findings/evidence/m3-production-ui/runs-0.2.44/chain-0.2.44.sh --preflight-only [--owner-window "..."]
#
# ESTIMATED DURATION, from the committed chain logs (runs-0.2.12/chain-2026-10-11b.out, runs-0.2.13/chain-2026-10-12.out,
# v19/x7-counted-m2 report timestamps, 136/guard-r2/c2/chain.txt, m3-autosave/shakedown, new-document/runs):
#   preflight (P6 is the slow part, ~1-2 min)                                     ~2 min
#   shakedowns: six M3 runners (page_honesty 22, locks 36-40, versions 1, assets 2,
#               host_entry 2, same_second 4)                                       ~66 min
#               autosave gate (as2-key, as4a, as5; 1 repeat, both browsers)        ~10 min
#               new-document (TW, EN; both browsers)                               ~3-14 min
#   counted production UI (KR x3, ctl/S/P x1; B3x withdrawn from this count, SPEC-M3-link-batch 17.3):
#               15 min in 0.2.12, PLUS the Rbs/Rdel arms' 60 s reopen wait x 12 (under C nothing reopens;
#               the wait ends by its timeout, scoring is keyed on the served engine)             ~27 min
#   counted six (page_honesty 64, locks 49, versions 4, assets 5, host_entry 6, same_second 12)  ~140 min
#   counted autosave (first counted run ever; 12 arms, 3 repeats but as2c x1, both browsers;
#               the 1-repeat shakedown took 34 min)                                ~100 min
#   counted new-document (0.2.19's took 3-7 min)                                   ~5 min
#   product-path net (12 runs x ~6.5 min)                                          ~78 min
#   merge count (10 reports; v19's X7 took 50 min)                                 ~50 min
#   C2 x3 (~4 min each)                                                            ~13 min
#   desk lines (a 1-5 s headless-Chrome reading before each of ~45 steps)          ~3 min
#   TOTAL about 8.2 h (7.5-9.5 h).  Started at 23:00 it ends around 07:15.
set -u
REPO=/home/jiajun/LibreOffice/study_LiteCore
HOST=$HOME/Projects/Nextcloud_Apps/litecore
cd "$REPO" || exit 9
T=wasm_sdk_probe/tools
SIX="page_honesty locks versions assets host_entry same_second"
# Identity this count is about (specs/SPEC-M3-K-0.2.44.md section 1).
PAGE=3b0a2ebb92c3db282f9c832ab194249f963592698cf5c73d771998dc10203a6a
ARCHIVE=wasm_sdk_probe/build/archive/host-0.2.44-engine-dacdfa20fd4ff1ea
HOST_URL=https://litecore.ddev.site:8443/login
OURS='probe_|judge_|check_m3|run_e2_c|run_merge|run_v20|run_v21_|diag_v21_|run_v8|run_k_|read_k_'
# Where this chain writes.
E=findings/evidence/m3-production-ui/runs-0.2.44      # production UI counted reports, as 0.2.13
R=findings/evidence/release-0.2.44
PP=$R/product-path                                      # product-path reports, one directory per run (read_k_0244_product_path.py)
MM=$R/merge-m2                                          # the merge count (judge_counted_m2.py --dir $MM --profile e2-editor-v28 --uncounted; read_k_0244_merge.py)
NAMED=findings/evidence/k-0.2.44/p6-named-reds.txt      # the static target's red set, exactly (spec 4.1)
C2=$R/c2                                                # C2 runs r1, r2, r3 (judge_c2.py --dir $C2/rK; judge_p2.py --dir $C2/rK/ratio-1)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG=wasm_sdk_probe/build/m3-count-$STAMP                # named with the start timestamp, under build/

PREFLIGHT_ONLY=0
OWNER_WINDOW="${OWNER_WINDOW:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --preflight-only) PREFLIGHT_ONLY=1 ;;
    --owner-window) shift; OWNER_WINDOW="${1:-}" ;;
    --owner-window=*) OWNER_WINDOW="${1#--owner-window=}" ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

# `say` goes to the chain log once START is possible; before that (preflight) to stdout only.
LOGGING=0
say() { if [ $LOGGING -eq 1 ]; then echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG/chain.txt"; else echo "$(date -u +%FT%TZ) $*"; fi; }
ts() { date '+%F %T %z'; }
h() { sha256sum "$1" | cut -c1-16; }
ident() { echo "host $(git -C "$HOST" rev-parse --short HEAD) dirty[$(git -C "$HOST" status --porcelain | tr '\n' ' ')] version $(grep -o '<version>[^<]*' "$HOST/appinfo/info.xml" | cut -c10-) buildId $(python3 -c 'import json,pathlib;print(json.loads((pathlib.Path.home()/"Projects/Nextcloud_Apps/litecore/engine/MANIFEST.json").read_text())["buildId"])') dist-page $(h wasm_sdk_probe/dist/e2-editor-app.js) web-page $(h wasm_sdk_probe/web/e2-editor-app.js) archive-page $(archive_page) host-served-page $(host_page)"; }
# The packaged page, decoded (the host serves gzip/zstd copies; findings/evidence/release-0.2.13/check_engine_decoded.py's read).
archive_page() { python3 -c 'import gzip,hashlib,sys;print(hashlib.sha256(gzip.decompress(open(sys.argv[1],"rb").read())).hexdigest()[:16])' "$ARCHIVE/files/e2-editor-app.js.gz" 2>/dev/null || echo unreadable; }
host_page() { python3 -c 'import gzip,hashlib,sys;print(hashlib.sha256(gzip.decompress(open(sys.argv[1],"rb").read())).hexdigest()[:16])' "$HOST/engine/files/e2-editor-app.js.gz" 2>/dev/null || echo unreadable; }

# ---------------------------------------------------------------- readings (J-a.1: recorded, never gated, at START,
# before each step, at END: loadavg, chrome / browser / firefox process counts, swap used, and P1-P3's readings)
read_p1() { busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked 2>&1 | tr '\n' ' ' | sed 's/ *$//'; }
read_p2() {  # prints "rc=<rc> bytes=<n> grep=<n>"; the positive control the 10-14p queue wrapper used (host-0.2.21/k3)
  local d; d=$(mktemp -d /tmp/chain-p2-XXXXXX)
  timeout 30 google-chrome --headless=new --user-data-dir="$d" --dump-dom "$HOST_URL" > "$d/dom.txt" 2> "$d/err.txt"
  local rc=$?
  echo "rc=$rc bytes=$(wc -c < "$d/dom.txt") grep=$(grep -c Nextcloud "$d/dom.txt")"
  rm -rf "$d"
}
# Our runners/probes/judges.  Excluded: this script and the shells it was launched from (their command lines can quote
# a runner's name without running one -- the second --preflight-only run of 2026-10-15 refused on exactly that, its
# harness's `bash -c` line naming check_m3_production_ui.py from a py_compile in the same command; README).
read_p3() {
  local pid=$$ anc=""
  while [ "$pid" -gt 1 ]; do anc="$anc $pid"; pid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' '); [ -n "$pid" ] || break; done
  pgrep -af "$OURS" | awk -v anc=" $anc " 'index(anc, " " $1 " ") == 0' || true
}
desk() {  # $1 label
  local load chrome browsers firefox swap p1 p3n p2
  load=$(cut -d' ' -f1-3 /proc/loadavg)
  chrome=$(pgrep -c chrome || true); browsers=$(pgrep -fc '/opt/google/chrome/chrome( |$)' || true); firefox=$(pgrep -c firefox || true)
  swap=$(free -m | awk '/Swap/{print $3"/"$2}')
  p1=$(read_p1); p3n=$(read_p3 | grep -c . || true); p2=$(read_p2)
  say "DESK $1 load $load chrome $chrome chrome-browsers $browsers firefox $firefox swap-used-MB $swap kwallet-locked [$p1] ours $p3n host-login [$p2]"
}

# ---------------------------------------------------------------- preflight (J-a.1 P1-P5 exactly; P6 added here)
REFUSED=0
refuse() { say "REFUSED $*"; REFUSED=$((REFUSED + 1)); }
P6DIR=$(mktemp -d /tmp/chain-p6-XXXXXX)

preflight() {
  local r n
  # P0 (chain-local, NOT a J-a item): this chain's own output directories must not already hold a run.  The merge
  # runner makes `<report>.docs/` with exist_ok=False and would die; a re-run is a new file (J-a.1), so the earlier
  # run's evidence is moved aside first (README).
  n=$(ls "$MM"/*.json "$PP"/*/report.json "$C2"/r[1-3]/*.json 2>/dev/null | wc -l)
  if [ "$n" -ne 0 ]; then refuse "P0 output collision: $n report(s) already under $MM, $PP or $C2/r1-r3; move them aside (a re-run is a new file)"; else say "P0 output directories empty: ok ($MM, $PP, $C2/r1-r3)"; fi
  # P1 KWallet unlocked
  r=$(read_p1)
  if [ "$r" = "b false" ]; then say "P1 kdewallet Locked = [$r]: ok"; else refuse "P1 kdewallet Locked = [$r] (want 'b false'); the owner unlocks the wallet on the VNC desktop"; fi
  # P2 a default-flag headless Chrome reaches the host login page
  r=$(read_p2)
  if [[ "$r" == rc=0* ]] && [[ "$r" != *grep=0 ]]; then say "P2 headless Chrome --dump-dom $HOST_URL: $r: ok"; else refuse "P2 headless Chrome --dump-dom $HOST_URL: $r (want rc=0 and grep>0)"; fi
  # P3 nothing of ours is running
  r=$(read_p3)
  n=$(printf '%s' "$r" | grep -c . || true)
  if [ "$n" -eq 0 ]; then say "P3 pgrep -af '$OURS': 0 lines: ok"; else refuse "P3 pgrep -af '$OURS': $n line(s):"$'\n'"$r"; fi
  # P4 identity: dist, web and the archived host package's page decode to the same sha256; the host tree is clean
  local d w a hp dirty
  d=$(h wasm_sdk_probe/dist/e2-editor-app.js); w=$(h wasm_sdk_probe/web/e2-editor-app.js); a=$(archive_page); hp=$(host_page)
  dirty=$(git -C "$HOST" status --porcelain)
  say "P4 pages: dist $d web $w archive $a (installed host serves $hp, recorded); want ${PAGE:0:16}; host HEAD $(git -C "$HOST" rev-parse --short HEAD) version $(grep -o '<version>[^<]*' "$HOST/appinfo/info.xml" | cut -c10-) dirty[$(printf '%s' "$dirty" | tr '\n' ' ')]"
  if [ "$d" = "${PAGE:0:16}" ] && [ "$w" = "$d" ] && [ "$a" = "$d" ] && [ -z "$dirty" ]; then say "P4 identity: ok"; else refuse "P4 identity: dist=$d web=$w archive=$a want=${PAGE:0:16}; host dirty=[$(printf '%s' "$dirty" | tr '\n' ' ')]"; fi
  # P5 the owner's agreement (an explicit argument naming the window) and an empty oc_files_lock
  if [ -n "$OWNER_WINDOW" ]; then say "P5 owner agreement: [$OWNER_WINDOW] (the owner does not open litecore.ddev.site during it)"; else refuse "P5 owner agreement not given: pass --owner-window \"<window>, agreed by the owner at <time>\" (or OWNER_WINDOW=...)"; fi
  r=$(cd "$HOST" && timeout 60 ddev mysql -e "SELECT COUNT(*) FROM oc_files_lock;" 2>&1 | tail -1)
  if [ "$r" = "0" ]; then say "P5 oc_files_lock rows: 0: ok"; else refuse "P5 oc_files_lock rows: [$r] (want 0; read-only SELECT, the runners clear the table themselves -- an owner session would be clobbered)"; fi
  # P6 (not in J-a; findings/evidence/link-batch/binding-v20/README.md: these two test files are in no Makefile target,
  # so `make test-e2-c-static` exited 0 while V19Witness was red) -- both must exit 0.
  ( cd wasm_sdk_probe && python3 -m unittest tests.test_merge_wasm_clauses tests.test_judge_counted_m2 ) > "$P6DIR/unittest.txt" 2>&1
  n=$?
  say "P6 unittest tests.test_merge_wasm_clauses tests.test_judge_counted_m2: exit $n :: $(grep -E '^Ran |^OK|^FAILED' "$P6DIR/unittest.txt" | tr '\n' ' ')"
  if [ "$n" -ne 0 ]; then refuse "P6 unittest exit $n ($P6DIR/unittest.txt)"; fi
  ( cd wasm_sdk_probe && make -i test-e2-c-static ) > "$P6DIR/static.txt" 2>&1
  n=$?
  reds=$(python3 findings/evidence/k-0.2.44/p6_reds.py "$P6DIR/static.txt")
  say "P6 make -i test-e2-c-static: exit $n :: reds [$(printf '%s' "$reds" | tr '\n' '|' | cut -c1-300)]"
  if [ "$n" -ne 0 ] || [ "$reds" != "$(cat "$NAMED")" ]; then refuse "P6 static target's red set differs from $NAMED ($P6DIR/static.txt)"; fi
}

say "PREFLIGHT tree $(git rev-parse --short HEAD) stamp $STAMP preflight-only=$PREFLIGHT_ONLY"
preflight
if [ $PREFLIGHT_ONLY -eq 1 ]; then
  say "PREFLIGHT-ONLY done: $REFUSED refusal(s); P6 outputs in $P6DIR (not kept by this script)"
  exit $REFUSED
fi
if [ $REFUSED -ne 0 ]; then
  say "PREFLIGHT REFUSED ($REFUSED item(s)); no START written, nothing ran"
  exit 3
fi

# ---------------------------------------------------------------- START (from here on nothing stops the chain but the
# shakedown STOP rule, exactly as chain-2026-10-12.sh; counted steps write their exit code and go on)
mkdir -p "$LOG" "$E" "$PP" "$MM" "$C2"
cp "$P6DIR/unittest.txt" "$LOG/preflight-p6-unittest.txt"; cp "$P6DIR/static.txt" "$LOG/preflight-p6-static.txt"; rm -rf "$P6DIR"
LOGGING=1
date -u +%FT%TZ > "$LOG/started"      # the reader picks the runners' reports newer than this file
say "PREFLIGHT ok (P0-P6); owner window [$OWNER_WINDOW]"
say "IDENTITY-START $(ident)"
say "START host $(git -C "$HOST" rev-parse --short HEAD) page $(cut -c1-12 <<< "$PAGE") tree $(git rev-parse --short HEAD) runner $(h $T/check_m3_production_ui.py) autosave $(h $T/check_m3_autosave.py) new-document $(h $T/check_m3_new_document.py) product-path $(h $T/run_e2_c_product_path.py) merge $(h $T/run_merge_wasm_shakedown.py) view $(h $T/probe_typing_latency_view.py) probe $(h $T/probe_typing_latency.py)"
desk START

# ---- shakedowns, the one STOP rule
for r in $SIX; do
  desk "before shakedown $r"
  say "shakedown $r begin"
  python3 $T/check_m3_$r.py --label shakedown --repeats 1 > "$LOG/shakedown-$r.log" 2>&1
  code=$?
  say "shakedown $r exit $code :: $(grep -E '^VERDICT|lands|LANDS' "$LOG/shakedown-$r.log" | tail -1 | cut -c1-200)"
  if [ $code -ne 0 ]; then say "STOP: shakedown $r not clean; no counted run started"; exit 1; fi
done
desk "before shakedown autosave"
say "shakedown autosave begin"
python3 $T/check_m3_autosave.py --label shakedown --arms as2-key,as4a,as5 --repeats 1 > "$LOG/shakedown-autosave.log" 2>&1
code=$?
say "shakedown autosave exit $code :: $(grep -E '^VERDICT' "$LOG/shakedown-autosave.log" | tail -1 | cut -c1-200)"
if [ $code -ne 0 ]; then say "STOP: shakedown autosave not clean; no counted run started"; exit 1; fi
desk "before shakedown new_document"
say "shakedown new_document begin"
python3 $T/check_m3_new_document.py --label shakedown > "$LOG/shakedown-new_document.log" 2>&1
code=$?
say "shakedown new_document exit $code :: $(grep -E 'NEW-DOCUMENT|NOT_ESTABLISHED|refusing' "$LOG/shakedown-new_document.log" | tail -1 | cut -c1-200)"
if [ $code -ne 0 ]; then say "STOP: shakedown new_document not clean; no counted run started"; exit 1; fi

# ---- counted production UI (SPEC-M3-production-ui 13: Kdel, Kbs, Rbs, Rdel, Bctl, S, P -- the runner's list; no arm
# was added since 0.2.13).  Same split as 0.2.13 WITHOUT the B3x step: B3x (A1-5, three boundary refusals to the Worker
# generation ceiling) is WITHDRAWN from the 0.2.23 count -- its premise, that this document's only refusals are at its
# ends (spec 13.2), is false under engine v20's C (the two ends are no-ops), so nothing can induce it; the main session
# decided this 2026-10-15 on the witness findings/evidence/m3-production-ui/witness-c-0.2.23/ (SPEC-M3-link-batch 17.3;
# the owner confirms in the morning).  Rbs/Rdel run as before; the runner now scores them under C, keyed on the bytes
# of the wasm the host serves (static.boundaryNoop in the report).
desk "before counted production_ui KR"
say "counted production_ui Kdel,Kbs,Rbs,Rdel x3 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 3 --arms Kdel,Kbs,Rbs,Rdel --out $E/counted-KR-x3.json > $E/counted-KR-x3.stdout.txt 2>&1; say "counted production_ui KR x3 exit $?"
desk "before counted production_ui ctl/S/P"
say "counted production_ui Bctl,S,P x1 begin"
python3 $T/check_m3_production_ui.py --counted --rounds 1 --arms Bctl,S,P --out $E/counted-ctl-S-P.json > $E/counted-ctl-S-P.stdout.txt 2>&1; say "counted production_ui ctl/S/P exit $?"
say "counted production_ui B3x: NOT RUN (withdrawn since the 0.2.23 count, SPEC-M3-link-batch 17.3; engine v28 also carries C)"

# ---- the six counted
for r in $SIX; do
  desk "before counted $r"
  say "counted $r begin"
  python3 $T/check_m3_$r.py --label counted > "$LOG/counted-$r.log" 2>&1
  say "counted $r exit $? :: $(grep -E '^VERDICT|lands|LANDS|refusing' "$LOG/counted-$r.log" | tail -1 | cut -c1-200)"
done

# ---- autosave counted (AS-*'s first counted run; SPEC-M3-autosave 9.4)
desk "before counted autosave"
say "counted autosave begin"
python3 $T/check_m3_autosave.py --label counted > "$LOG/counted-autosave.log" 2>&1
say "counted autosave exit $? :: $(grep -E '^VERDICT|refusing' "$LOG/counted-autosave.log" | tail -1 | cut -c1-200)"

# ---- new-document counted (SPEC-M3-new-document 4 「計數語意」, 7.5: from 0.2.20 on the count binds the candidate
# engine; part P3 wrote ENGINE_BUILD_ID c3c22d92 / PAGE_SHA256 ccb67a52.  The report goes to findings/evidence/new-document/runs/.)
desk "before counted new_document"
say "counted new_document begin"
python3 $T/check_m3_new_document.py --label counted > "$LOG/counted-new_document.log" 2>&1
say "counted new_document exit $? :: $(grep -E 'NEW-DOCUMENT|NOT_ESTABLISHED|refusing' "$LOG/counted-new_document.log" | tail -1 | cut -c1-200)"

# ---- the product-path net (specs/SPEC-M3-K-0.2.44.md section 3): the plain v28 arm, 3 rounds x 2 browsers, one at a time.
echo "$(ts) PRODUCT-PATH START tools: $(h $T/run_e2_c_product_path.py) clipboard wrapper $(h $T/run_v82_f3_clipboard.py)" >> $PP/chain.log
for B in chrome firefox; do
  for N in 1 2 3; do
    OUT=$PP/$B-r$N
    CMD="python3 $T/run_v82_f3_clipboard.py --browser $B --out $OUT"
    desk "before product-path v28 $B r$N"
    echo "$(ts) START v28 $B r$N :: $CMD" >> $PP/chain.log
    $CMD > $OUT.stdout.json 2> $OUT.stderr.txt
    RC=$?
    echo "$(ts) END   v28 $B r$N exit=$RC report_exists=$([ -s $OUT/report.json ] && echo yes || echo no)" >> $PP/chain.log
    say "product-path v28 $B r$N exit $RC"
  done
done
echo "$(ts) PRODUCT-PATH DONE" >> $PP/chain.log

# ---- the merge count (SPEC-M3-paragraph-merge 30.2 modes counted / control / m2-1b / m2-4 / m2-1-red; the file names
# are judge_counted_m2.py's FILES; the shape is findings/evidence/v19/chain.sh's X7 with e2-editor-v21 as the candidate.
# The runner's --candidate-profile defaults to e2-editor-v16, so it is passed on every non-red mode; the red case is v8.)
snap() { ps -eo pid,ppid,etime,pcpu,comm --sort=-pcpu | head -15 > "$1"
  ps -eo pid,etime,args | grep -E -- '[-]-remote-debugging-port=|[g]eckodriver|[-]marionette' > "$1.test-browsers"; }
mstep() {  # name, command...
  local name=$1; shift
  desk "before merge $name"
  snap "$MM/$name.ps-before.txt"
  say "merge $name begin :: $*"
  "$@" > "$MM/$name.stdout.txt" 2> "$MM/$name.stderr.txt"
  local rc=$?
  snap "$MM/$name.ps-after.txt"
  say "merge $name exit $rc :: $(tail -1 "$MM/$name.stderr.txt" | cut -c1-200)"
}
for B in chrome firefox; do
  mstep counted-$B          python3 $T/run_k_0244_merge.py --browser $B --mode counted --candidate-profile e2-editor-v28 --out $MM/counted-$B.json
  mstep counted-control-$B  python3 $T/run_k_0244_merge.py --browser $B --mode counted --control --candidate-profile e2-editor-v28 --out $MM/counted-control-$B.json
  mstep pair-$B             python3 $T/run_k_0244_merge.py --pair $MM/counted-$B.json $MM/counted-control-$B.json
  mstep m2-1b-$B            python3 $T/run_k_0244_merge.py --browser $B --mode m2-1b --candidate-profile e2-editor-v28 --out $MM/m2-1b-$B.json
  mstep m2-4-$B             python3 $T/run_k_0244_merge.py --browser $B --mode m2-4 --candidate-profile e2-editor-v28 --out $MM/m2-4-$B.json
done
say "merge DONE (no red step: K ruling item 1; read-0.2.44.sh copies the 0.2.26 reds, then judge_counted_m2.py --uncounted and read_k_0244_merge.py)"

# ---- C2 three times (ruling J-b.2): findings/evidence/136/guard-r2/c2/chain-c2.sh's shape per run, one directory per
# run; judges afterwards, unchanged: judge_c2.py --dir $C2/rK, judge_p2.py --dir $C2/rK/ratio-1 (both pinned to 3b0a2ebb, k-0.2.44/repin_0244.py).
c2_one() {  # dir out-stem, command...
  local d=$1 out=$2; shift 2
  timeout 600 "$@" --out "$out.json" > "$out.stdout.txt" 2>&1
  echo "$(date -u +%FT%TZ) $(basename "$out") exit $? :: $(tail -1 "$out.stdout.txt" | cut -c1-200)" >> "$d/chain.txt"
}
c2_run() {  # K
  local K=$1 D=$C2/r$1 B dist
  mkdir -p "$D/ratio-1.5" "$D/ratio-1"
  desk "before c2 r$K"
  dist=$(h wasm_sdk_probe/dist/e2-editor-app.js)
  if [ "$dist" != "${PAGE:0:16}" ]; then
    say "c2 r$K REFUSED dist $dist (want ${PAGE:0:16}); not run"; echo "$(date -u +%FT%TZ) REFUSED dist $dist (want ${PAGE:0:16})" >> "$D/chain.txt"; return
  fi
  { echo "$(date -u +%FT%TZ) pgrep -c chrome: $(pgrep -c chrome || true)"; echo "Chrome browsers (pgrep -fc '/opt/google/chrome/chrome( |$)'): $(pgrep -fc '/opt/google/chrome/chrome( |$)' || true)"
    echo "/proc/loadavg: $(cat /proc/loadavg)"; echo "pgrep -af '$OURS' (ours): $(read_p3 | tr '\n' ' ')"; echo "firefox processes at start: $(pgrep -c firefox || true)"; } > "$D/desk-at-start.txt"
  echo "$(date -u +%FT%TZ) START tree $(git rev-parse --short HEAD) dist $dist view $(h $T/probe_typing_latency_view.py) probe $(h $T/probe_typing_latency.py) chrome-procs $(pgrep -fc '/chrome/chrome( |$)' || true) load $(cut -d' ' -f1-3 /proc/loadavg)" >> "$D/chain.txt"
  say "c2 r$K begin"
  for B in chrome firefox; do
    c2_one "$D" "$D/c2-candidate-$B-owner-gap80"            python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
    c2_one "$D" "$D/c2-candidate-$B-owner-gap200"           python3 $T/probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser $B --document owner --gap 200 --chars 10
    c2_one "$D" "$D/ratio-1.5/c2-ratio1.5-$B-owner-gap80"   python3 $T/probe_typing_latency_view.py --dpr 1.5 --window 1400x1000 --browser $B --document owner --gap 80 --chars 20
    c2_one "$D" "$D/ratio-1/p-candidate-$B-owner-gap80"     python3 $T/probe_typing_latency.py --browser $B --document owner --gap 80 --chars 20
    c2_one "$D" "$D/ratio-1/p-candidate-$B-owner-gap200"    python3 $T/probe_typing_latency.py --browser $B --document owner --gap 200 --chars 10
    c2_one "$D" "$D/ratio-1/p-candidate-$B-boundaries-gap200" python3 $T/probe_typing_latency.py --browser $B --document boundaries --gap 200 --chars 10
  done
  echo "$(date -u +%FT%TZ) DONE" >> "$D/chain.txt"
  say "c2 r$K done :: $(grep -c ' exit 0 ' "$D/chain.txt") of 12 cells exit 0"
}
for K in 1 2 3; do c2_run $K; done

# ---- end
say "IDENTITY-END $(ident)"
desk END
# The runners leave one Firefox profile (~79 MB) per Firefox session in the snap-visible scratch directory and never
# remove it (as 0.2.13's chain: 167 had piled up by 2026-10-12, 8.1 GB).  Every browser of this chain has exited by now.
SCR=wasm_sdk_probe/build/scratch-m3-production-ui
say "cleanup: $(find $SCR -maxdepth 1 -name 'ff-*' -type d | wc -l) Firefox profiles in $SCR removed"
find $SCR -maxdepth 1 -name 'ff-*' -type d -exec rm -rf {} +
say "DONE (read with: bash $E/read-0.2.44.sh $LOG)"
exit 0
