#!/usr/bin/env bash
# Finding 186: compare the products of the two full builds (arm M and arm R).
# usage: compare_builds.sh <out-dir>
# The two source worktrees (src-186-M / src-186-R) and build directories (build-186-M / build-186-R) have names of
# equal length, so path strings compiled into the binaries do not change sizes.
set -u
U=/home/jiajun/LibreOffice/study_LiteCore/wasm-lite/upstream-master
OUT=${1:?out dir}; mkdir -p "$OUT"
M=$U/build-186-M; R=$U/build-186-R
for d in "$M" "$R"; do [ -d "$d/instdir" ] || { echo "FATAL: no instdir in $d"; exit 2; }; done

sec() { echo; echo "==================== $1"; }

sec "receipts"
for a in M R; do echo "--- $a"; cat "$U/build-186-$a.receipt.txt"; done

sec "main products (bytes, sha256 prefix)"
for f in workdir/installation/LibreOffice/emscripten/soffice.wasm workdir/installation/LibreOffice/emscripten/soffice.js \
         workdir/installation/LibreOffice/emscripten/soffice.data workdir/installation/LibreOffice/emscripten/soffice.data.js.metadata; do
  for a in M R; do
    p=$U/build-186-$a/$f
    if [ -f "$p" ]; then printf '%s  %12d  %s  %s\n' "$a" "$(stat -c %s "$p")" "$(sha256sum "$p" | cut -c1-16)" "$f"
    else printf '%s  MISSING  %s\n' "$a" "$f"; fi
  done
done
wm=$(stat -c %s "$M/workdir/installation/LibreOffice/emscripten/soffice.wasm" 2>/dev/null || echo 0)
wr=$(stat -c %s "$R/workdir/installation/LibreOffice/emscripten/soffice.wasm" 2>/dev/null || echo 0)
echo "soffice.wasm: M - R = $((wm - wr)) bytes"

sec "instdir file lists"
( cd "$M/instdir" && find . -type f | LC_ALL=C sort ) > "$OUT/instdir-files-M.txt"
( cd "$R/instdir" && find . -type f | LC_ALL=C sort ) > "$OUT/instdir-files-R.txt"
echo "files: M $(wc -l < "$OUT/instdir-files-M.txt")  R $(wc -l < "$OUT/instdir-files-R.txt")"
LC_ALL=C comm -23 "$OUT/instdir-files-M.txt" "$OUT/instdir-files-R.txt" > "$OUT/instdir-only-in-M.txt"
LC_ALL=C comm -13 "$OUT/instdir-files-M.txt" "$OUT/instdir-files-R.txt" > "$OUT/instdir-only-in-R.txt"
echo "only in M: $(wc -l < "$OUT/instdir-only-in-M.txt")   only in R: $(wc -l < "$OUT/instdir-only-in-R.txt")"
echo "--- only in M (first 60)"; head -60 "$OUT/instdir-only-in-M.txt"
echo "--- only in R (first 60)"; head -60 "$OUT/instdir-only-in-R.txt"

sec "registry (instdir/share/registry/*.xcd)"
for x in "$M"/instdir/share/registry/*.xcd "$M"/instdir/share/registry/res/*.xcd; do
  rel=${x#"$M"/}
  if [ -f "$R/$rel" ]; then
    if cmp -s "$x" "$R/$rel"; then s=same; else s=DIFFERENT; fi
    printf '%-9s  M %9d  R %9d  %s\n' "$s" "$(stat -c %s "$x")" "$(stat -c %s "$R/$rel")" "$rel"
  else printf 'ONLY-IN-M  %s\n' "$rel"; fi
done
echo "--- main.xcd: occurrences of names that only the Unix-desktop .xcu files set"
for k in UseSystemFileDialog UseSystemPrintDialog 'oor:name="ooName"' ; do
  printf '%-28s M %s  R %s\n' "$k" "$(grep -o "$k" "$M/instdir/share/registry/main.xcd" | wc -l)" "$(grep -o "$k" "$R/instdir/share/registry/main.xcd" | wc -l)"
done
if command -v xmllint >/dev/null; then
  diff <(xmllint --format "$M/instdir/share/registry/main.xcd") <(xmllint --format "$R/instdir/share/registry/main.xcd") > "$OUT/main.xcd.M-vs-R.diff"
  echo "main.xcd formatted diff: $(grep -c '^<' "$OUT/main.xcd.M-vs-R.diff") lines only in M, $(grep -c '^>' "$OUT/main.xcd.M-vs-R.diff") lines only in R"
  gzip -f "$OUT/main.xcd.M-vs-R.diff"
fi

sec "file system image (soffice.data.js.metadata)"
python3 - "$M/workdir/installation/LibreOffice/emscripten/soffice.data.js.metadata" \
           "$R/workdir/installation/LibreOffice/emscripten/soffice.data.js.metadata" <<'EOF'
import json, sys
def load(p):
    d = json.load(open(p))
    return {f["filename"]: f["end"] - f["start"] for f in d["files"]}
m, r = load(sys.argv[1]), load(sys.argv[2])
print(f"files in image: M {len(m)}  R {len(r)}")
om, orr = sorted(set(m) - set(r)), sorted(set(r) - set(m))
print(f"only in M: {len(om)}   only in R: {len(orr)}")
for n in om[:40]: print("  M-only", n, m[n])
for n in orr[:40]: print("  R-only", n, r[n])
ds = sorted(n for n in set(m) & set(r) if m[n] != r[n])
print(f"same name, different size: {len(ds)}")
for n in ds[:40]: print(f"  {n}  M {m[n]}  R {r[n]}  (M-R {m[n]-r[n]})")
EOF

sec "objects that exist only with USING_UNIX_DESKTOP=TRUE"
for a in M R; do
  n=$(find "$U/build-186-$a/workdir/CxxObject/vcl/unx/generic/desktopdetect" -name '*.o' 2>/dev/null | wc -l)
  echo "$a  desktopdetect objects: $n"
done
for a in M R; do
  echo "$a  config: $(grep -E '^export (USING_UNIX_DESKTOP|USING_X11|ENABLE_OPENGL_TRANSITIONS|ENABLE_OPENGL_CANVAS|ENABLE_GTK3|ENABLE_QT5)=' "$U/build-186-$a/config_host.mk" | tr '\n' ' ')"
done
