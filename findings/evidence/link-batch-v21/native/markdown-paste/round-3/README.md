# Markdown paste natively, round 3: the two native pre-runs of the v21 shakedown (DM-5, DM-17 C)

Arms: `findings/evidence/link-batch-v21/shakedown/ARMS-item2.md` §9 (rulings DM-5 A and DM-17 A + C: both run and are committed before any WASM run of the arms they serve). Rounds 1 and 2: `../README.md`, `../round-2/README.md` (same install, same paste call). Run 2026-10-16, native LibreOffice 26.8 only. No browser, no WASM, no `make`. Rounds 1 and 2 are unchanged.

Labels: **[OBS]** observed in this round (native); **[SRC]** read in source, file:line; **[INF]** inference. **Nothing about WASM is observed here.**

## Bottom line

- **DM-5, the five M0-PASS items that had no native reference** [OBS, 3/3 identical per arm, the signature by round 2's reader equal across the three runs]: all five convert at P1 with one `Paste clipboard` undo action that one Undo restores. C1 as Markdown gives `Heading_20_1/2/3` and a `Text_20_body` paragraph with bold, italic and monospace runs, then an empty `Text_20_body` (5 paragraphs); X09 `` `List<T>` `` gives `Use List<T> here.` with a monospace run; X10 gives one `Preformatted_20_Text` paragraph `List<T> items;`; X11 (`- [ ] todo`, `- [x] done`) gives two bullet items whose text starts with `☐` and `☒`; X12 gives `ATT tag  ` — every entity dropped (finding 149's shape, now 3/3 on other bytes: `AT&amp;T &lt;tag&gt; &#169; &#x4E2D;`). These are M1's references for the five items (`out/R3-P1-<item>/run{1,2,3}/after.fodt.gz`).
- **DM-17 C, selecting an image or a frame** [OBS, 3/3 per arm]: one engine click on the 2 cm image, on the text frame's border, in its padding, or even on its text, **selects the object**: Writer sends `GRAPHIC_SELECTION` with the object's rectangle (`1418, 1418, 1133, 1133` for the image; `1985, 5953, 3401, 1700` for the frame) and `CURSOR_VISIBLE`, and **no `TEXT_SELECTION` at all** while the click is placed. `getSelectionTypeAndText()` — the call the WASM engine's `readSelection()` makes [SRC `wasm_sdk_probe/src/probe_engine.cpp:3344-3364`] — answers **type 3 (`LOK_SELTYPE_COMPLEX`)** with no text, as does `getSelectionType()`. Then `paste(doc, "text/markdown;charset=utf-8", …)` **returns false** ("Document doesn't support this mime type"), `.uno:Paste` is `disabled`, the undo payload is unchanged and the document is unchanged by both detectors. The control (a caret placed by keys in body text) reads type 0 and pastes normally.
- **What this means for M10b/c on WASM** [INF]: the stated red risk (`ARMS.md` §5; `ARMS-item2.md` M10 prediction) was that the engine's "collapsed" rule would accept a selected image, because its cache reads only `TEXT_SELECTION` and §10.2 assumed `readSelection()` reads a selected image as `NONE`. Natively the second half of that premise is false: the read is type 3, not `NONE`, so `collapsedForPaste()` returns false on its first operand [SRC `wasm_sdk_probe/src/markdown_paste.hpp:340-345`] and the engine is predicted to answer `MARKDOWN_NEEDS_CARET` before dispatching. The cache would not have refused (no `TEXT_SELECTION` arrives). The WASM run of the same clicks decides it; the click points below are where the native run found the objects.

## What was run

| item | value |
|---|---|
| install | `native-lok-26-8/build/instdir/program`, buildid `671c848b…`, `libsofficeapp.so` `9ad35464…`, `libswlo.so` `885566e3…` [OBS sha256, equal to round 1's README] |
| probe for DM-5 | round 2's `md_paste_probe2.cpp`, rebuilt from `../round-2/tool/` exactly as round 2's README says: binary sha256 `425a8b0113366c3466bc816f8b256bd8d19611922ba1f4d98d78e780ab89c5f8`, **byte-identical** to round 2's counted binary [OBS]. So the five new references come from the same instrument as round 2's T3-P1 references |
| probe for DM-17 C | `tool/md_paste_probe3.cpp`: round 2's probe plus two records — every callback during PLACE (`place-callbacks`), and `getSelectionTypeAndText()` plus the last `TEXT_SELECTION`/`GRAPHIC_SELECTION` payloads in the position line. Built in `tool/` with `g++ -std=c++17 -O2 -Wall -I <repo>/libreoffice-26-8/include md_paste_probe3.cpp -ldl -lpthread -o <scratch>/md-paste-probe3`, no warnings; sha256 `f73114bc4e1585080af031a4d713ec434938155f7572a290e891955df42362bb`. g++ 15.2.0 |
| runner | `tool/run_arms3.py`: it declares the arms and imports round 2's `run_arms2.run_one` for everything else (fresh profile and document copy per process, `env -i` with `LANG=zh_TW.UTF-8` and `SAL_USE_VCLPLUGIN=svp`, nice, timeout, the probe's 20 s watchdog, waiting for other LOK probes, the 18765 listener and 18768 closer); it adds the probe-3 records to `summary.json` under `round3`. It refuses to start unless the corpus copies equal `markdown_paste_expected.json` and the M10 fixture equals the generator's pin |
| corpus | `tool/corpus/`: byte copies of `wasm_sdk_probe/tests/markdown_paste_corpus/{round-1/C1.md, m0/X09…, X10…, X11…, X12…}` (sha256 equal to the fixture's, checked by the runner); M2 from round 1's corpus |
| inputs | round 1's `empty-template.odt` (`a3354bae…`) for DM-5; `tool/inputs/m10-selectables.odt` (`c0628cc94189228fa36e5a24ca017930cd6a4d081ca7437c95153b46e395ea2e`), written by `wasm_sdk_probe/tools/v21_item2_fixtures.py` (`m10_selectables()`, deterministic, pinned there) for DM-17 C |
| N | 3 processes per arm, 30 in all; every process exited 0; no watchdog fired; no wait for another probe |

### The M10 fixture and the click points

`m10-selectables.odt`: A4, 2 cm margins; a page-anchored text frame `m10-frame` at (3 cm, 10 cm), 6 × 3 cm, border 0.06 cm, padding 0.5 cm, holding `M10-FRAME text`; paragraph 1 holds only a 2 × 2 cm PNG anchored as a character; then `M10-BODY plain paragraph after the image` and `M10-TAIL last paragraph`. Clicks are absolute engine clicks (`a<x>:<y>`, twips, DOWN+UP, count 1), computed from the declared geometry with page 1 at (284, 284):

| arm | click | what the click selected [OBS, 3/3] |
|---|---|---|
| `R3-SEL-image-M2` | (1985, 1985), the image's centre | the image: `GRAPHIC_SELECTION` `1418, 1418, 1133, 1133` |
| `R3-SEL-frameborder-M2` | (2002, 6803), the left border's middle line | the frame: `GRAPHIC_SELECTION` `1985, 5953, 3401, 1700` |
| `R3-SEL-framepadding-M2` | (2161, 6803), in the padding | the frame, same rectangle |
| `R3-SEL-frametext-M2` | (2600, 6408), on the frame's text | the frame, same rectangle (a first click on a text frame selects the frame) |
| `R3-SEL-keys-M2` (control) | keys: Ctrl+Home, Down, End | a caret `5689, 2552, 0, 276` at the end of `M10-BODY…`; type 0; the paste goes in |

The WASM arm (M10b/c) clicks the centre of the rectangle Writer reported here, not the declared one; the rectangles equal the declared geometry to within one twip [OBS].

## Results

Generated per run: `out/<arm>/run<k>/{cmd.txt, stdout.jsonl, stderr.txt, before.fodt.gz, after.fodt.gz, summary.json}`; `out/runner.log`.

| arm | `paste()` | undo count | document changed | after (round 2 reader, signature equal 3/3) |
|---|---|---|---|---|
| `R3-P1-C1` | true | 0 → 1, one Undo restores | yes | h1 `Heading one`, h2, h3, `Text_20_body` `Plain bold and italic and inline code end.` (bold, italic, mono runs), empty `Text_20_body` |
| `R3-P1-X09-angle-generic-inline-code` | true | 0 → 1, restores | yes | `Standard` `Use List<T> here.` (mono `List<T>`), empty `Standard` |
| `R3-P1-X10-angle-generic-fenced` | true | 0 → 1, restores | yes | `Preformatted_20_Text` `List<T> items;`, empty `Text_20_body` |
| `R3-P1-X11-task-list` | true | 0 → 1, restores | yes | two bullet items `☐ todo`, `☒ done`, empty `Standard` |
| `R3-P1-X12-entities` | true | 0 → 1, restores | yes | `Standard` `ATT tag  ` (the four entities dropped), empty `Standard` |
| `R3-SEL-image-M2`, `-frameborder-`, `-framepadding-`, `-frametext-` | **false** ("Document doesn't support this mime type") | 0 → 0, payload identical | no (both detectors) | unchanged |
| `R3-SEL-keys-M2` | true | 0 → 1, restores | yes | M2 joined to the end of `M10-BODY…` |

All runs: thread encoding 76 (UTF-8) [OBS].

## Fixed because of execution (declared)

1. **The fixture's frame position in the body.** In a one-process dry run (`--runs=1`, scratch output, not kept) the page-anchored frame stood after the paragraphs; native Writer dropped it on import (the saved `before.fodt` had no `m10-frame`) and the frame clicks landed at the end of the text. The generator now writes the frame before the first paragraph, as round 2's `frame-protected.fodt` does; its pin moved from `490b4bdb…` to `c0628cc9…` before the counted runs. The image arm's dry-run result was the same as the counted one.

Fixed because of review: 0.

## What this does NOT show

- Anything about WASM: whether the WASM engine's `readSelection()` also reads type 3, what the page's click (`placeCaret`) does on an image, and whether a second click on a text frame enters its text there.
- Ranges over a frame, a frame anchored to a paragraph or a character, images anchored other than as a character, shapes that are not frames.
- What the user sees.

## Reproduce

```
R=findings/evidence/link-batch-v21/native/markdown-paste; E=$R/round-3; S=<scratch>
(cd $R/round-2/tool && g++ -std=c++17 -O2 -Wall -I <repo>/libreoffice-26-8/include md_paste_probe2.cpp -ldl -lpthread -o $S/md-paste-probe2)
(cd $E/tool && g++ -std=c++17 -O2 -Wall -I <repo>/libreoffice-26-8/include md_paste_probe3.cpp -ldl -lpthread -o $S/md-paste-probe3)
python3 -B wasm_sdk_probe/tools/v21_item2_fixtures.py --check
python3 -B $E/tool/run_arms3.py $S/md-paste-probe2 $S/md-paste-probe3 $S/runs $E/out [--runs=N] [ARM_ID_PREFIX ...]
```

`run_arms3.py` skips a run whose `summary.json` exists. Run Python with `-B` so nothing is written into rounds 1 and 2's `tool/`.

## Files

- `tool/md_paste_probe3.cpp`, `tool/run_arms3.py`, `tool/corpus/` (5 items), `tool/inputs/m10-selectables.odt`.
- `out/<arm>/run<k>/` as round 2; `out/runner.log`.
- `SHA256SUMS`: every file in this folder except itself.
