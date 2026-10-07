# Option C for finding 116: result

Predictions: `PREDICTION.md`, committed `2417c6ca` before any run. Amendment 1 was appended and committed `ee295ac2` after M2's first run and before its second.

## M1: bytes (`measure_mono_cost.py`, `mono-cost.json`; exit 0, stderr empty)

- **Positive control HIT.** The five-face collection rebuilt with the pack tool's own `subset` + `collection` is byte-identical to the shipped `cjk-sub-e5` (sha256 `ce59153d…` both).
- **Mono subset.** Source: face 8 of the full TTC (`Noto Sans Mono CJK TC`). Same tier-E code points and same subsetter options. Result: 25,767 code points, 25,814 glyphs. It passes the subset tool's own `verify` against the source face (cmap, hmtx/vmtx, every outline).

| | raw | gzip -9 | zstd -19 |
|---|---|---|---|
| shipped `cjk-sub-e5` (5 faces) | 7,210,328 | 6,227,279 | 5,604,052 |
| E5+K (+ Mono KR) | 14,374,856 (**+7,164,528**) | 12,443,888 (**+6,216,609**) | 5,748,392 (**+144,340**) |
| E5+M5 (+ Mono JP KR SC TC HK) | 14,384,856 (+7,174,528) | 12,445,609 (+6,218,330) | 5,748,782 (+144,730) |

- The pack is served as zstd level 19, without long mode, with an 8 MiB window. That is the host's own setting (`specs/SPEC-M3-zstd.md` §3.1; `package_m3_engine.py` makes the same call as this measurement). The Mono data sits about 7.2 MB after the Sans data, inside that window. zstd therefore finds the outlines the two halves share, and **the download for zstd clients grows by about 0.14 MB**. gzip's 32 KB window cannot see this, so **a gzip-only client downloads 6.2 MB more**. The **raw size doubles**, and raw size is what the worker's file system holds once the pack is loaded. Memory and boot time on a profile were not measured.
- Four more Mono names after the first cost 10,000 bytes raw and 390 bytes zstd.
- **Limit (stated, not hidden).** E5+K and E5+M5 here are measurement artifacts, not pack candidates. The check script reported every face's `head` table as different from its source. Field by field, the differences are `checkSumAdjustment` (recomputed by any collection save) on all faces, and `modified` on the five Sans faces. The second is because this script re-loaded them from the rebuilt collection without `recalcTimestamp=False`. Neither field changes a length. A real pack would be built the way the pack tool builds it, deterministically, and verified table by table.

## M2: does 116 reach fixed-pitch 細明體 / MingLiU? (`run_fixed.py`; two runs)

**Formal status: Q2 is NOT drawn.** PC-M2a missed as written in run 1: band counts were 7/8/8, not 6, because I forgot the page's own two bands. Amendment 1 replaced it with PC-M2a′. PC-M2a′ also missed as written in run 2: no request whose first family is Courier New reached fontconfig in any session of either run, so the N2 line's font is resolved before fontconfig is asked. Both misses are wrong expectations of mine about the instrument, not readings of the probe. The pre-written fallback ("stop") is taken. **No further amendment was made to make a run pass.** Everything below is observation, identical in both runs, offered as data with that status.

What did hold, in both runs:

- every session `ready` and settled;
- 21/21/22 conf.d files;
- fixture-phase blocks present;
- requests present for 細明體, MingLiU, 新細明體, Liberation Serif and K1's shape;
- **PC-M2b**: K1's shape is answered Liberation Mono on v17 and Noto Sans Mono CJK KR on the control, i.e. the probe sees 116 itself.

Run 1 is `run1-*`, run 2 is `fixed-probe.json` and `summary-fixed.txt`. Their census sections are line-for-line identical. Bands are identical too. The only difference is the control's fixture-phase block count, 29 then 30.

Observed (v17 against the control; answer family):

| request (first family, language) | v17 | control | v8 (language as rewritten by 35) |
|---|---|---|---|
| 細明體, `en` first (Western) | Liberation Mono | Noto Sans Mono CJK KR | Noto Sans Mono CJK KR (`en`,`tw`) |
| 細明體, `zh-tw` (Asian) | **Liberation Mono** | Noto Sans Mono CJK KR | Liberation Mono (`tw`) |
| 細明體, `zh-tw`, with charset (glyph fallback) | Noto Sans CJK HK | not asked | Noto Sans Mono CJK KR |
| MingLiU, Western / Asian | Liberation Mono / **Liberation Mono** | Noto Sans Mono CJK KR / Noto Sans Mono CJK KR | Noto Sans Mono CJK KR / Liberation Mono |
| 新細明體 (variable), Western / Asian | Liberation Sans / Noto Sans CJK HK | the same | Liberation Sans / Liberation Sans (+ fallback Noto Sans CJK HK) |
| Liberation Serif | Liberation Serif | Liberation Serif | Liberation Serif |

- **The negative control that could be read (新細明體) is the same in both arms.** The packs do not differ for a variable-pitch CJK name.
- **My expectation for the Asian slot missed.** I expected a Noto Sans CJK face on v17, on the reasoning that language ranks before the weak family list. The answer is Liberation Mono. The score vectors show why. The winner on v17 scores 0 on `GENERIC_FAMILY` (index 10) and 2000 on `LANG` (index 12), i.e. Liberation Mono does not cover zh-TW and still wins. The glyph-fallback block's winner, a Sans CJK face, scores 1000 on `GENERIC_FAMILY`. In fontconfig 2.18 the generic-family criterion ranks **before** language. A fixed-pitch request carries `monospace` (from `addtopattern`), so a monospace-classified face beats every CJK Sans face whatever the language. In the subset, the only monospace-classified face is Liberation Mono. This is read from the winners' vectors; the losers' full ranking was not dumped.
- **v8 is not the control either, for 細明體.** Its Asian slot is Liberation Mono for 114's reason: 35 rewrites `zh-tw` to `tw`, which is Twi, a Latin-script language.
- **Bands (secondary; `[top, bottom]` in px).**
  - Control: F1 `[81, 99]`, which includes the caret drawn on the first line; F2 `[104, 117]`; F3 starts at 123.
  - **v17: F1 and F2 read as one band, `[80, 108]`, and F3 starts at 112.** From F1's top to F3's top is 32 px on v17 against 42 px on the control, so each of the two lines is about 5 px shorter. The lines after F3 keep the control's pitch (19-20 px).
  - Reading, by inference consistent with 114 (engine caret heights were not measured): F1 and F2 take Liberation Mono's line height while their CJK glyphs come from a fallback face. That is 114's symptom, CJK text laid out with Latin line metrics, here reached through the fixed-pitch path.
  - v8 minus control, per band: `[0, 0, 0, -2, -5, -7, -7, 0]`.

## What this gives the owner (facts only; the choice is the owner's)

- **A** (add Mono faces, e.g. E5+M5) puts back, on v17, what the full TTC gives. For 116's fixture: Noto Sans Mono CJK KR for generic `monospace`. On the observed data, also fixed-pitch 細明體/MingLiU in both slots. Cost: zstd +0.14 MB, gzip +6.2 MB, raw (file system) +7.2 MB. Plus a new pack identity and profile, no link needed.
- **B** keeps v17 as it is. Generic `monospace` gets Liberation Mono (fine for Latin text). On the observed data, fixed-pitch 細明體/MingLiU paragraphs get Liberation Mono in both slots, with CJK text in fallback glyphs and Latin line height. v8 has its own, different defect on that path (114).
- Not established: whether real documents declare 細明體/MingLiU with a fixed pitch. The owner's document does not, and neither does any corpus document (read from their XML).
