# E02 on v17: is the different pagination the font set or the WASM engine? (before the run)

Written 2026-10-07 after the V5 run and before any native run below. Diagnostic, not a criterion.

## What forced it

V5 run (`../shakedown-chrome-v5.json`): E02 is the only one of the 37 cases that does not pass, and only on `afterKeyBytes`. `../e02-breaks.txt` (re-runnable, `../e02_breaks.py`, prints structure and text lengths only): the merge itself is identical to Writer's key arm; the two reduced-byte hunks are two `T4` spans that WASM's export split around a `<text:soft-page-break/>` the spec-24 reduction removes (it removes the element, it does not re-join the spans). Breaks 2, 3, 14 and 15 of 15 sit elsewhere than in Writer's key arm r1 (and Writer's r1-r3 key arms are equal to each other). In the other 10 owner cells, in the no-edit save (M2-0) and in E01, all 15 breaks sit where Writer's do. E02 is the only cell that turns a long body paragraph (209 characters) into the first heading's style (`Heading_20_1`, 18 pt). The follow documents (after a typed `Z`) also differ (8 of 15), so it is not "saved before the layout settled" on one side only.

## Arms (native only; the owner's document is read from `wasm_sdk_probe/build/` and every output stays under `wasm_sdk_probe/build/merge-native-pmpc-e02d/`)

One round each, E02 only (an E02-only copy of `test-docs/merge/r0-pmpc.cases.tsv`, header kept), `MERGE_ESHAPE=1 MERGE_FOLLOW_TEXT=Z`, as in finding 114's native reproduction, and `FC_DEBUG=1024` in the probe's own process so the rule files it really loaded are printed (fontconfig prints them to stdout, which the runner sends to `arms.jsonl`; they are split out afterwards, the JSON lines kept).

- **N-sys**: no `FONTCONFIG_FILE` (the system rules and fonts; what R0c used).
- **N-v17**: `FONTCONFIG_FILE=build/wasm-fontset-v17/fonts-abs.conf` = the fonts and rules extracted from the shipped v17 packs (`tools/extract_wasm_fontset.py --profile e2-editor-v17`: 13 fonts, 21 conf.d files, no 35) with the relative `<include>conf.d</include>` replaced by the absolute path (standing rule, new (a) of 10-07d).

## Positive controls (an arm that fails one is not evidence)

- C1: N-v17's process loaded exactly the 21 conf.d files of `build/wasm-fontset-v17/conf.d` and no rule file from outside it; N-sys's loaded `/etc/fonts` files.
- C2: both arms' key-arm documents equal Writer's R0c key arm r1 by reduced paragraph text (the merge happened), and N-sys's key arm has R0c r1's 15 breaks (the native run reproduces itself).

## Readings (compare the 15 break contexts of each key-arm document, as `../e02_breaks.py` prints them)

- **H-font** (the v17 font set makes this layout): N-v17 breaks = WASM v17 breaks (0 of 15 differ) and N-v17 differs from N-sys at breaks 2, 3, 14, 15.
- **H-wasm** (the WASM engine lays the merged paragraph out differently with the same fonts and rules): N-v17 breaks = N-sys breaks, differing from WASM at 2, 3, 14, 15.
- **Neither**: N-v17 differs from both. Reported as such, with the differing breaks; no third explanation is written before looking at the merged paragraph's line count on each side.

## What follows

- H-font: the difference is a fidelity property of the v17 font set against this machine's system fonts (the shipped subset resolves `思源黑體` to Noto Sans CJK KR, natively it resolves to TC; V3), not of the WASM engine; it joins V4's open 19-vs-20 rows as the same question (is a KR-for-TC resolution visible in layout?). Not fixed in this round.
- H-wasm: a new finding (layout of a long CJK heading paragraph differs between WASM and native with identical fonts and rules).
- Either way: the spec-24 reduction is incomplete for breaks inside spans (removing the element leaves two adjacent spans with one style). This matters only if the owner's document returns to M2-1; it is registered, not fixed here (a change to the reduction is a criterion change and needs its own appended section).
