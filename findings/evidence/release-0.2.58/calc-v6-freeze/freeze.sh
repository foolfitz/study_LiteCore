#!/usr/bin/env bash
# Freeze the Calc development profile ods-editor-v6 (wasm 47e3792c, worker cbf3c1ef; linked 2026-11-05 01:34 by the agent on
# the owner's word, findings/evidence/calc-structure/link/) into dist/profiles/ods-editor-v6 for the 0.2.58 hand-test slot.
# The archive already exists, read-only: build/archive/ods-editor-v6-dev-47e3792c (written at the link, with its SHA256SUMS).
# Three copies must be equal file for file: build/ods/editor-v6/profile, dist/profiles/ods-editor-v6, the archive; and the
# link's four-file receipt must agree.  dist/profiles/ods-editor-v6 must not exist before.  Writes only dist/ and this folder.
set -eu
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
E=../findings/evidence/release-0.2.58/calc-v6-freeze
SRC=build/ods/editor-v6/profile; DST=dist/profiles/ods-editor-v6; ARC=build/archive/ods-editor-v6-dev-47e3792c
test ! -e "$DST"
sums() { (cd "$1" && find . -type f ! -name SHA256SUMS -printf '%P\n' | sort | xargs sha256sum); }
sums "$SRC" > $E/source.sha256
cp -r "$SRC" "$DST"
sums "$DST" > $E/dist.sha256
sums "$ARC" > $E/archive.sha256
cmp $E/source.sha256 $E/dist.sha256
cmp $E/source.sha256 $E/archive.sha256
(cd "$ARC" && sha256sum -c SHA256SUMS) > $E/archive-own-sums.txt
sort -k2 ../findings/evidence/calc-structure/link/profile-SHA256SUMS | while read -r h f; do grep -qx "$h  $f" $E/source.sha256; done
echo FROZEN_EQUAL
