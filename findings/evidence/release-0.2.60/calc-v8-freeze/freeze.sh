#!/usr/bin/env bash
# Freeze the Calc development profile ods-editor-v8 (wasm 61e2a069, worker 91d514f1; linked 2026-11-07 03:4x on the owner's
# request, findings/evidence/calc-v8/link/) into dist/profiles/ods-editor-v8 for the 0.2.60 hand-test slot (named 2026-11-07).
# The archive already exists, read-only: build/archive/ods-editor-v8-dev-61e2a069 (written after the link, with its SHA256SUMS).
# Three copies must be equal file for file: build/ods/editor-v8/profile, dist/profiles/ods-editor-v8, the archive; and the
# link's four-file receipt must agree.  dist/profiles/ods-editor-v8 must not exist before.  Writes only dist/ and this folder.
# Same steps as release-0.2.59/calc-v7-freeze/freeze.sh with v7 -> v8.
set -eu
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
E=../findings/evidence/release-0.2.60/calc-v8-freeze
SRC=build/ods/editor-v8/profile; DST=dist/profiles/ods-editor-v8; ARC=build/archive/ods-editor-v8-dev-61e2a069
test ! -e "$DST"
sums() { (cd "$1" && find . -type f ! -name SHA256SUMS -printf '%P\n' | sort | xargs sha256sum); }
sums "$SRC" > $E/source.sha256
cp -r "$SRC" "$DST"
sums "$DST" > $E/dist.sha256
sums "$ARC" > $E/archive.sha256
cmp $E/source.sha256 $E/dist.sha256
cmp $E/source.sha256 $E/archive.sha256
(cd "$ARC" && sha256sum -c SHA256SUMS) > $E/archive-own-sums.txt
sort -k2 ../findings/evidence/calc-v8/link/profile-SHA256SUMS | while read -r h f; do grep -qx "$h  $f" $E/source.sha256; done
echo FROZEN_EQUAL
