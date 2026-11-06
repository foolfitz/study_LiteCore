#!/usr/bin/env bash
# Freeze the Calc development profile ods-editor-v7 (wasm 36d0e1b8, worker 8b49b46e; linked 2026-11-06 11:57 by the owner,
# findings/evidence/calc-copy/link/) into dist/profiles/ods-editor-v7 for the 0.2.59 hand-test slot.
# The archive already exists, read-only: build/archive/ods-editor-v7-dev-36d0e1b8 (written after the link, with its SHA256SUMS).
# Three copies must be equal file for file: build/ods/editor-v7/profile, dist/profiles/ods-editor-v7, the archive; and the
# link's four-file receipt must agree.  dist/profiles/ods-editor-v7 must not exist before.  Writes only dist/ and this folder.
set -eu
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
E=../findings/evidence/release-0.2.59/calc-v7-freeze
SRC=build/ods/editor-v7/profile; DST=dist/profiles/ods-editor-v7; ARC=build/archive/ods-editor-v7-dev-36d0e1b8
test ! -e "$DST"
sums() { (cd "$1" && find . -type f ! -name SHA256SUMS -printf '%P\n' | sort | xargs sha256sum); }
sums "$SRC" > $E/source.sha256
cp -r "$SRC" "$DST"
sums "$DST" > $E/dist.sha256
sums "$ARC" > $E/archive.sha256
cmp $E/source.sha256 $E/dist.sha256
cmp $E/source.sha256 $E/archive.sha256
(cd "$ARC" && sha256sum -c SHA256SUMS) > $E/archive-own-sums.txt
sort -k2 ../findings/evidence/calc-copy/link/profile-SHA256SUMS | while read -r h f; do grep -qx "$h  $f" $E/source.sha256; done
echo FROZEN_EQUAL
