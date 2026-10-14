#!/bin/bash
# usage: pp.sh <object> <out.i>   (run from wasm_sdk_probe/)
CMD=$(make -n -B EXTRA_DEFINES= "$1" 2>/dev/null | sed -e ':a' -e '/\\$/{N;s/\\\n//;ba}' | grep -E 'em\+\+' | head -1)
A=$(echo "$CMD" | sed -E "s# -c # -E -P #; s# -o [^ ]+# -o $2#")
eval "$A"
