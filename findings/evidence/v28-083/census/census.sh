#!/bin/sh
# One-time census (CLAUDE.md section 1, form three) for SPEC-M3-v28: who reads the 083 path's names.
# Run from the study root.  Searched: wasm_sdk_probe/{tools,web,editor-shell-v2,sdk,tests,src} and every .py / .md
# under findings/evidence/ (excluding the native-q52 tree, which defines the candidate, and archived dist copies).
set -u
PAT='select-text-returned-none|EMPTY_SELECTION_SHAPES|取不到任何內容|L-083-stays-a-toast|selectionResultSeen|did not provide readable text|stage-deadline:awaiting-selection'
echo "# pattern: $PAT"
echo "# product and tool sources"
grep -rnE "$PAT" wasm_sdk_probe/tools wasm_sdk_probe/web wasm_sdk_probe/editor-shell-v2 wasm_sdk_probe/sdk \
  wasm_sdk_probe/tests wasm_sdk_probe/src --include=*.py --include=*.js --include=*.mjs --include=*.cpp \
  --include=*.inc --include=*.hpp --include=*.h --include=*.sh 2>/dev/null | cut -c1-220
echo "# evidence readers (.py) and disposition tables (.md) under findings/evidence"
grep -rlE "$PAT" findings/evidence --include=*.py --include=*.md 2>/dev/null | grep -v '/native-q52/' | sort
echo "# count of matching lines per evidence file"
grep -rcE "$PAT" findings/evidence --include=*.py --include=*.md 2>/dev/null | grep -v ':0$' | grep -v '/native-q52/' | sort
