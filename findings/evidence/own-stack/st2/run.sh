#!/usr/bin/env bash
# ST2 and ST3 of SPEC-M3-own-stack: the runners' shakedowns against the own stack, bound tools unedited, `ddev` = host-stack/bin/ddev.
# Not a count.  Every step runs even if an earlier one is red.  T1 needs a clean desk and nothing else running, so between steps, if the
# desk has come clean and T1 has not run, T1 runs first, alone.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
export PATH="$PWD/wasm_sdk_probe/host-stack/bin:$PATH"
T=wasm_sdk_probe/tools
F=findings/evidence/own-stack/st2
LOG=$F/log.txt
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
maybe_t1() {
  [ -e findings/evidence/v29-177/t1/log.txt ] && return
  if python3 -I findings/evidence/link-batch-v22/shakedown/desk_gate.py > /dev/null 2>&1; then
    say "desk clean: T1 first"; bash findings/evidence/v29-177/t1/chain.sh > /dev/null 2>&1; say "T1 chain exit $?"
  fi
}
step() { local name=$1; shift; maybe_t1; say "BEGIN $name"; "$@" > "$F/$name.stdout.txt" 2> "$F/$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$F/$name.exit.txt"
  say "END   $name exit $rc :: $(grep -E '^VERDICT|lands|LANDS|DELIVERED|CORRECT|NEW-DOCUMENT|NOT_ESTABLISHED|refusing|HONEST|WORKS' "$F/$name.stdout.txt" "$F/$name.stderr.txt" | tail -1 | cut -c1-200)"; }
say "START tree $(git rev-parse --short HEAD) host $(git -C ~/Projects/Nextcloud_Apps/litecore rev-parse --short HEAD) ddev $(command -v ddev)"
for r in assets host_entry page_honesty locks versions same_second; do step $r python3 $T/check_m3_$r.py --label shakedown --repeats 1; done
step new_document python3 $T/check_m3_new_document.py --label shakedown
step production_ui python3 $T/check_m3_production_ui.py --rounds 1 --arms Kdel,Kbs,Rbs,Rdel,Bctl,S,P --out "$PWD/$F/production-ui.json"
step files_workflow python3 $T/run_calc_editor_host.py --out "$PWD/$F/files-workflow"
step autosave python3 $T/check_m3_autosave.py --label shakedown --repeats 1
maybe_t1
say DONE
