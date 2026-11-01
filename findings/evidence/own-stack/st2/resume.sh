#!/usr/bin/env bash
# The rest of ST2 and ST3.  run.sh stopped at new_document: that runner waits while another runner is up, and the shell that had started
# run.sh carried the word in its own command line, so it waited for itself.  Start this from a command line that does not.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
export PATH="$PWD/wasm_sdk_probe/host-stack/bin:$PATH"
T=wasm_sdk_probe/tools
F=findings/evidence/own-stack/st2
LOG=$F/log.txt
say() { echo "$(date +%FT%T%z) $*" | tee -a "$LOG"; }
step() { local name=$1; shift; say "BEGIN $name"; "$@" > "$F/$name.stdout.txt" 2> "$F/$name.stderr.txt"; local rc=$?; echo "exit=$rc" > "$F/$name.exit.txt"
  say "END   $name exit $rc :: $(grep -E '^VERDICT|lands|LANDS|DELIVERED|CORRECT|WORKS|refusing' "$F/$name.stdout.txt" "$F/$name.stderr.txt" | tail -1 | cut -c1-200)"; }
say "RESUME tree $(git rev-parse --short HEAD)"
step new_document python3 $T/check_m3_new_document.py --label shakedown
step production_ui python3 $T/check_m3_production_ui.py --rounds 1 --arms Kdel,Kbs,Rbs,Rdel,Bctl,S,P --out "$PWD/$F/production-ui.json"
step files_workflow python3 $T/run_calc_editor_host.py --out "$PWD/$F/files-workflow"
step autosave python3 $T/check_m3_autosave.py --label shakedown --repeats 1
say DONE
