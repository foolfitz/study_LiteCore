# Result: native R0c on the owner's document with the WASM profile's fonts

Run 2026-10-07 11:16 UTC, `round-20261007T111635Z` (saved documents under `wasm_sdk_probe/build/merge-native-pmpc/r0c-wasmfonts/`, not in the repository; `arms.jsonl`, `inputs.sha256`, `follow-text.txt` copied to `pmpc-round-20261007T111635Z/`). Command as in `PREDICTION.md`; the font set is `fontset-MANIFEST.json`.

| prediction | result |
|---|---|
| W1 (merge does not depend on fonts) | **HIT.** `check_merge_eshape.py`: 11 cases, all `merge`, 0 KILL, the one vacuous STOP (`{'merge': 33}`). |
| W2 (the 0.79 is the fonts) | **MISS.** All 11 native placed carets are identical, to the twip, to the system-font round `r0c/pmpc-round-20261006T150756Z` (heights 348, 521, 463 as before), while WASM reports 276/414/230 for the same cases (merge shakedown run 3). |
| W3 (placement on WASM) | Not run: W2's miss means the coordinates cannot map (the prediction's own rule). |

**Positive control for W2's "nothing changed".** The same probe, one round, case E01 only, under `strace -f -e trace=openat`, once with `FONTCONFIG_FILE` set to the extracted config and once without. With it the process opened exactly 7 font files, all from the extracted set (`trace-opened-fonts-with-wasm-config.txt`: Liberation Mono/Sans/Serif faces, `NotoSansCJK-Regular-subset-E.ttc`, and LibreOffice's own `opens___.ttf`); without it, 363 system font files (`trace-opened-fonts-system-config.txt`). So the configuration was in effect, and native LibreOffice with WASM's font files and WASM's fontconfig lays the owner's document out exactly as with the machine's fonts.

**What it means.** The line-height difference on the owner's document is not the font set; it is on the WASM side of the same core. The pairs are consistent with WASM using Liberation Sans line metrics for these lines (12 pt x 1.149 = 276 twips, 18 pt x 1.149 = 414) where native uses Noto Sans CJK's (12 pt x 1.448 = 348, 18 pt x 1.448 = 521) -- an inference from the arithmetic, not a reading of either engine. Registered as finding 114. Per `PREDICTION.md`, spec 25 falls back to A.

## Correction, 2026-10-07 (after `../../114/fc-debug/`)

"WASM's fontconfig" above was only half true. The extracted `fonts.conf` includes its rules with a relative `<include>conf.d</include>`, which fontconfig resolves against its default config directory: this run loaded the machine's `/etc/fonts/conf.d` (61 files), not the profile's 22 (`../../114/fc-debug/native-repro/relative-include.rule-files.txt`). The `strace` control above shows the font files were restricted; it could not show where the rule files came from. With the profile's conf.d included by absolute path, native fontconfig rewrites LibreOffice's string `FC_LANG` `zh-tw` to `tw` through `35-lang-normalize.conf` and picks a Liberation face, which is what WASM does. So "on the WASM side of the same core" is withdrawn; the cause is the profile's rule file meeting LibreOffice's string language (finding 114, "成因"). W1 and the measured carets stand; they were made with the system rules.
