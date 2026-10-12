# Finding 132 / L-128-rapid — baseline: a held Backspace at the desk's own repeat rate, before any fix

The first step SPEC-M3-autosave §9.17 (supplementary registration 4) asks for: a real-rate baseline on page `d761f1ce…`, before any new mechanism and before the criteria are written (`specs/SPEC-M3-held-key.md` §2.2).

## Conditions

- Host `litecore` 0.2.14 (`237f2cb`), engine package buildId `eb3f94084995d3f0`, served page `d761f1cee9d26c50…` = `dist/` page, shell v63 `318b3bf2…` (the report's `static` block).
- Probe `wasm_sdk_probe/tools/probe_hand_test_0212.py` at `e18b47bf` (arms `hold-high`, `hold-low`, `--hold-rounds 2`); not a counted runner, no product byte touched. Chrome 151.0.7922.169 (15:16–15:24 UTC), Firefox 157.0.1 (15:24–15:33 UTC), 2026-10-12.
- The owner's document (the production-UI runner's gitignored copy) uploaded as `probe-hand-0212.odt`; desk 1850 × 980 CSS px, devicePixelRatio 1, canvas window 4,092 rows = 4 bands of 1,023.
- **The hold**: the desk's own settings, read into the report (`deskRepeat`: GNOME `delay` 500 ms, `repeat-interval` 30 ms). One press at 0 ms, a repeat every 30 ms from 500 ms to 2000 ms (52 keydowns, no keyup between them), one keyup at 2015 ms. Chrome: CDP `Input.dispatchKeyEvent` `rawKeyDown`, `autoRepeat: true` on the repeats, scheduled on absolute times. Firefox: one WebDriver action chain with pauses (a keyDown of a key already down is a repeat by the spec). The `repeat` flag each keydown arrived with is read back on the page.
- **Arms**: `hold-high` = caret in band 0, the first band under the view (row 229); `hold-low` = caret in band 1 with band 0 also under the view (row 1338). Each round types 56 letters one at a time, deletes 4 with single presses (each allowed to settle), then holds Backspace once; whatever the hold did not delete is deleted one key at a time, and the view's pixels are compared with before typing (`persistent`).

## What is read

On the page (`HOLD_HOOK` in the probe): every Backspace keydown (with `repeat`), keyup and `beforeinput`; every write of the latency line (one per finished action, so the k-th 「⌫ 刪除」 is the k-th delete done); every `fillRect` on `#canvas` in the selection's wash colour `#b7d3f2` or the caret's `#1a1a1a`; `requestAnimationFrame` frames while recording. From the instrument's existing log: the caret's band and its label (the change counter when that band was asked for). `hold_summary` in the probe turns these into the numbers below; `../read_hold.py` prints them (`read_hold-output.txt`).

## Results (8 holds: 2 browsers × 2 arms × 2 rounds)

| | Chrome high | Chrome low | Firefox high | Firefox low |
|---|---|---|---|---|
| keydowns / flagged repeat / deleted | 52 / 51 / 52 ×2 | 52 / 51 / 52 ×2 | 52 / 51 / 52 ×2 | 52 / 51 / 52 ×2 |
| other latency lines (refusals, failures) | none | none | none | none |
| one delete alone (single presses, keydown → done) | 44.2–48.7 ms | 44.3–46.0 ms | 45.7–50.4 ms | 46.0–47.4 ms |
| one delete in the queue (median gap between deletes done) | 65.6 ms | 65.6–65.8 ms | 66.5–66.6 ms | 66.5 ms |
| deletes done by the engine at release | 23, 23 | 23, 24 | 25, 25 | 25, 25 |
| deletes shown on screen at release | 22, 22 | **1, 1** | 24, 24 | **1, 1** |
| deletes after release | 29, 29 | 29, 28 | 27, 27 | 27, 27 |
| last delete, after release | 1843, 1844 ms | 1855, 1830 ms | 1800, 1791 ms | 1794, 1788 ms |
| caret band repainted before release | 24, 24 | **1, 1** | 26, 26 | **1, 1** |
| caret band fresh, after release | 1858, 1864 ms | 1870, 1846 ms | 1815, 1806 ms | 1814, 1808 ms |
| selection washes drawn during the hold | 52, 52 | 52, 52 | 52, 52 | 52, 52 |
| …of which on screen for ≥ 1 frame | 32, 32 | 26, 28 | 29, 29 | 33, 9 |
| wash on a single press (ms until the caret is drawn) | 8.3–10.6 | 9.2–9.5 | 7.5–9.5 | 7.3–9.2 |
| `persistent.differing` | 0, 0 | 0, 0 | 0, 0 | 0, 0 |

## Reading

1. **The tail (132's queue half) is the same in both arms.** A held key sends a repeat every 30 ms; a delete in the queue takes about 66 ms (about 46 ms alone, the rest is the repaint `run()` waits for between deletes, finding 132). So at release the engine has done 23–25 of 52 deletes, and it goes on deleting 27–29 more for **1.8 s after the key came up**. Nothing is lost and nothing is left: every key is deleted, `persistent` 0.
2. **The frozen screen (L-128-rapid's half) is the low arm only.** With the caret in the second band under the view, its band was repainted once, for the first press, and then not until the queue had drained: at release the screen shows 1 deletion while the engine has done 23–25, and the remaining ~50 appear at once about 1.8 s after release. In the high arm the caret band is repainted after every delete, so the screen follows the engine, one character per ~66 ms, but the engine itself is behind the key.
3. **The owner's 「上半下半，我感受不出區別」** is consistent with (1): in both arms deletion goes on for ~1.8 s after release. What differs is whether the screen moves during the hold (high) or jumps at the end (low); 「再一口氣出現」 describes the low arm exactly. Both halves are present at the real rate.
4. **The blue flash is the barrier's selection, drawn.** Every delete, single or held, draws one wash the size of one character (e.g. `[562, 254, 13, 29]`) and then the caret 7–11 ms later; about half of them land on a presented frame. That is §9.18 item 2's code-reading hypothesis, now measured.

## Positive controls

- The repeat flag is real: 51 of 52 keydowns arrive with `repeat: true` in both browsers, the press with `false`.
- The band reading moves when the band moves: the high arm reads 24–26 caret-band repaints before release where the low arm reads 1, on the same counter.
- The wash reading is not vacuous: it reads 52 washes per hold and one per single press; a page that drew no selection would read 0.
