#!/usr/bin/env bash
# new_document in counted mode after the commit split.  From a file: that runner waits while another runner's name is on any command line, a heredoc in the launching shell included.
set -u
cd /home/jiajun/LibreOffice/study_LiteCore || exit 9
export PATH="$PWD/wasm_sdk_probe/host-stack/bin:$PATH"
D=findings/evidence/k-0.2.45/counted-dry-run
python3 wasm_sdk_probe/tools/check_m3_new_document.py --label counted > $D/new_document.stdout.txt 2> $D/new_document.stderr.txt
echo "exit=$?" > $D/new_document.exit.txt
