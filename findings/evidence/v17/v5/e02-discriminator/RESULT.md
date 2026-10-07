# E02 on v17: font set or WASM engine? (result)

Per `PREDICTION.md` (committed `c7b8c5c0` before any run here). Native arms run 2026-10-07 23:07:40 and 23:08:01 (+08:00); one WASM repeat 23:09:54. Every document of the owner's stays under `wasm_sdk_probe/build/` (`merge-native-pmpc-e02d/`, `merge-wasm-private/wasm-e02-repeat.docs/`); nothing below prints its text.

## Inputs

- Native build `native-lok-26-8/build/instdir` (the one R0c used), probe source sha in `n-*.inputs.sha256`; fixture sha256 `7b336879…` (= R0c's `fixture.odt` = the owner's file in `build/scratch-m3-production-ui/`).
- N-v17's fonts and rules: `tools/extract_wasm_fontset.py --profile e2-editor-v17 --out build/wasm-fontset-v17` (base pack sha `65e8acbb…` = V1's `base-r5-no35`, CJK pack `cjk-sub-e5` `ce59153d…`; 13 fonts, 21 conf.d, no 35), then `fonts-abs.conf` = its `fonts.conf` with `<include>conf.d</include>` replaced by the absolute path (one line differs).
- WASM repeat: `wasm-e02-repeat.json` (`--cases E02 --owner-document`, same runner `c3f723b3…`, page `4c0088c7…`).

## Controls

- **C1, as written: MISSED on one file.** N-v17's process (`FC_DEBUG=1024`, lines split out of its `arms.jsonl`) loaded `fonts-abs.conf`, the 21 conf.d files of `build/wasm-fontset-v17/conf.d`, **and** `native-lok-26-8/build/instdir/share/fonts/truetype/fc_local.conf` (`n-v17.rule-files.txt`, 23 lines). That file is LibreOffice's own: at start-up LO adds its bundled font directory, whose `fc_local.conf` maps `Symbol` to `OpenSymbol` and turns off embedded bitmaps for Calibri, Cambria and Monaco; the directory also holds `opens___.ttf` (OpenSymbol). The WASM packs hold neither (base `/instdir/share/fonts/truetype/` = the 12 Liberation files; CJK pack = the subset TTC). So N-v17 is "v17's fonts and rules plus LO's app-font directory", not v17's exactly. N-sys loaded 66 files: `/etc/fonts`, `~/.config/fontconfig/fonts.conf` and the same `fc_local.conf` (`n-sys.rule-files.txt`). No rule file from `/etc/fonts` in N-v17; no `35-lang-normalize.conf` in either.
- **C2: HIT.** Both arms' key-arm documents equal R0c's key arm r1 under the spec-24 reduction (0 hunks; the merge happened), and N-sys's key arm has R0c r1's 15 breaks exactly (the native run reproduces itself).

## Readings (break contexts compared in order; `../e02_breaks.py`'s definition)

| comparison | breaks differing (of 15) |
|---|---|
| N-v17 key arm vs N-sys key arm | none |
| N-v17 key arm vs WASM v17 after-key (V5 run) | 2, 3, 14, 15 |
| N-v17 key-follow vs WASM v17 follow | 2, 3, 5, 7, 10, 13, 14, 15 |
| N-sys key-follow vs R0c r1 key-follow | none |
| WASM repeat after-key / follow vs V5 run's | none / none (reduced bytes: 0 hunks) |
| no-edit save, N-sys and N-v17, vs R0c original and vs WASM M2-0 | none |

**H-wasm, with the C1 caveat.** With v17's font files and rules natively, Writer paginates E02's merge exactly as with the system fonts; WASM v17 paginates it differently at the same four breaks, deterministically (two runs equal). What N-v17 did not remove: LO's `fc_local.conf` and OpenSymbol are present in every native run and absent in WASM. They are not excluded by this measurement; against them: the no-edit document and the other 10 merges paginate identically natively and on WASM, so they would have to matter only after this one merge. (The document's `styles.xml` has 36 bullet levels naming `OpenSymbol1` and the body has 10 lists using `WW8Num*` styles; whether any rendered bullet actually uses OpenSymbol was not checked.)

## What this establishes

- The residual difference in E02 is on the WASM side (engine or the app-font directory it lacks), not in the v17 font set, and it is not 114's mechanism (no 35 on either side, and the caret heights agree).
- Not established: what in the merged 213-character `Heading_20_1` paragraph lays out differently (line count, line heights, keep-with-next, widow/orphan); whether WASM's layout at save time is complete (the WASM follow document, saved later, differs too, so a stale layout would have to be stale in the same way twice). Registered as finding 115.
- Unchanged from `../RESULT.md`: spec 24's reduction removes a break element but does not re-join the spans it split; this only bites when breaks differ, as here.
