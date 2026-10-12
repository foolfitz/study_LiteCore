# Finding 129, M4 — the page fix ("click at the point, then the key") on WASM, both browsers

Brief: `handoff/tasks/TASK-2026-10-12d-m4-129-on-wasm.md` (including its "Update before dispatch" section). Native reference: `findings/evidence/129/README.md` ("Native: does 'click at the point, then the key' reproduce Writer?") and `findings/evidence/129/native/point-click-round-20261012T031459Z/`, `point-click-extras-drag-round-20261012T034525Z/`. The page under test is a mirror (see "What was run"); no product byte was written.

## Prediction (main session, before any run; copied verbatim from the brief)

- P-M4a: on the patched page, for the 12 old arms, where `#` lands equals the native `ref` arm (Writer's own behaviour), in both browsers: 12/12 each.
- P-M4b: for S1–S5, the WASM result equals the native `ref` arm (native `emu` = `ref` in all of them). For `s1d` and `m1d`: Left, Right, Up, Home, End follow the native rule; Down follows the native `emu` (not `ref`) by rule — the named limit shows up on WASM too.
- P-M4c: no arm on the patched page shows a toast; the key-to-move time is under 200 ms in every arm (the click on a selection is answered, so the 400 ms grace is never paid).
- P-M4d: `shift-collapsed` and `shift-range` change nothing and show no toast.
- P-M4e: the red control's three arms are refused with the developer sentence (0.2.12's behaviour).

(Written into this file before the first counted run; everything below the line "## Results

### What was run

| item | value |
|---|---|
| tool, runner, analysis | `wasm_sdk_probe/tools/probe_129_m4_wasm.py`, `wasm_sdk_probe/tools/run_probe_129_m4.sh`, `wasm_sdk_probe/tools/analyze_129_m4.py` (reads the raw `arms-*.jsonl`, compares strings and numbers; command in each folder's `analysis-command.txt`) |
| page under test | `wasm_sdk_probe/build/m4-mirror/e2-editor-app.js` (sha256 `2ad5b6e5…`) served from a symlink mirror of `dist/` (`pp.build_mirror`, standalone `e2-editor.html`, `web/serve.py`, no host) with ONE line appended at the end: `globalThis.__m4 = { get session() { return session; } };` (served sha256 `5e6a5cf6…`). The red control is `dist/e2-editor-app.js` (`8909564e…`) plus the same line (served sha256 `d0454dbb…`) |
| mirror check | **Per the correction of 2026-10-12 (the main session edited `web/` for 0.2.13): the mirror is verified as `dist/e2-editor-app.js` (sha256 `8909564e…`, the shipped page) + `findings/evidence/129/m4/page-129.patch`, and `web/` is not read.** Round 2 and the control rounds' tool do this at the start of every browser run (`report-<browser>.json` -> `preflight.mirrorEqualsDistPlusPatch: true`). Round 1 ran BEFORE the correction and checked against `web/` + patch instead (true at 04:22:39Z for Chrome and at 04:35:20Z for Firefox; `web/` was equal to `dist/` then, `inputs.sha256` has its hash, and `web/` was edited at 04:35:43Z); I then ran the dist-based check on the same files at 04:38:04Z (`round-20261012T042238Z/mirror-check-dist-plus-patch.txt`: dist + patch = mirror = `2ad5b6e5…`) |
| documents | the three native fixtures converted once to .odt with `native-lok-26-8/build/instdir/program/soffice --headless --convert-to odt` (`-env:UserInstallation` throwaway); copies in `round-*/docs/`; sha256 in `round-*/inputs.sha256`: arrow-selection `2ce55eff…`, shapes `883c48c0…`, wrap `59ec325d…`. `report-<browser>.json` -> `preflight.documents`: `paragraphsEqualFodt: true` for all three (`odt_paragraphs.paragraph_texts_from_xml` on the .odt equals the same function on the .fodt: 3, 10 and 2 paragraphs). The same fixtures as the native rounds; `arrow-selection-wrap.fodt` is the token paragraph of the native extras |
| browsers | Chrome 151.0.7922.169 (headless new, CDP `Input.dispatchKeyEvent`), Firefox 157.0.1 (headless, geckodriver WebDriver actions); real keys in both; pointer events through `pp.DRAG` / `pp.POINT_AT` (the page's own `#paper` handlers) |
| counted rounds | `round-20261012T042238Z` (Chrome 04:22:39Z-04:35:19Z, Firefox 04:35:20Z-04:49:23Z) and `round-20261012T045307Z` (Chrome 04:53:07Z-05:05:32Z, Firefox 05:05:32Z-05:19:02Z); the browsers run one after the other. Per browser and round: 1 calibration, 54 arms (9 shapes x 6 keys), 2 shift arms, 8 reach arms (extra), 3 red-control arms |
| extra (not a counted round) | `round-20261012T042238Z-control`: collapsed-caret key timing, see "Timing" |
| last browser run ended | **2026-10-12T05:19:13Z** (`round-20261012T045307Z/ended-utc.txt`) |

The arms, as in the brief: every arm is a FRESH `OPEN_FILE` of the document (`fresh: true` in all 216 counted arms: `revision` 0, not dirty, caret at the document start, selection collapsed). Making the selection: click inside the paragraph (at a calibrated first line, +250 twips), Home, the plain real Right key k times -> read `editorState.caret` (the anchor), n more Rights -> the far end; then DRAG (pointer events through the page's handler, x/y fractions = twips / document twips, y = caret.y + caret.height / 2) anchor -> far end (forward) or far end -> anchor (backward). `s1d` / `m1d`: the anchor is the caret after W-10 / B-10 Rights, the far end is 400 twips to the right of the end of line 1 (End key position), the drag as the owner would do it. The selection is read before the key with `session.document.getSelection()` (the engine read that `copySelection()` writes to the clipboard; `copySelection()` itself returns only the code point count) and must equal what the native arm selected (S5: recorded); then ONE real unshifted key, quiet, ONE real `#`, quiet, `session.save()` bytes -> `content.xml` -> paragraph texts, `#` located. Timeline: a MutationObserver on the latency line, the pill, the toast and a capture-phase keydown listener, all with `performance.now()`.

### Wrap offsets on WASM (found with Right, one press at a time, until the caret's y changes)

| | WASM (Chrome = Firefox, both rounds) | native |
|---|---|---|
| S1 line starts | 101, 195, 292 (5 lines, as native) | 101, 201, … |
| token line starts | 87, 175, 261 | 89, 180, 270 |

The glyph advances differ slightly from native (line 1 of S1 breaks at the same place, line 2 earlier), so absolute offsets differ for S1 from line 2 on and for the token; the vertical metrics are the same (line y = 1418, 1694, 1970, … twips as native; the table and all short lines have the same x extents as native). Hence the by-rule comparison below.

### Where `#` landed

Identical in Chrome and Firefox (54/54 cells) and identical in the two rounds (54/54 cells in each browser); `¶` in the excerpt is a paragraph / line / cell boundary. Native `ref` / `emu` are the flat indices from `native/point-click-round-20261012T031459Z` and `native/point-click-extras-drag-round-20261012T034525Z` (stable over their 3 rounds). "By rule": the native result described in terms of this browser's wrap offsets (W = 101, W2 = 195; B = 87, B2 = 175, B3 = 261), see the header of `analyze_129_m4.py`.

| shape | key | WASM: `#` at index, excerpt (both browsers, both rounds) | native `ref` | native `emu` | = native `ref` | by rule (`ref` / `emu`) | rule value |
|---|---|---|---|---|---|---|---|
| p2-forward | Left | 43, `LPHA BETA GAMM<#>A DELTA¶P3 thi` | 43 | 43 | exact | True / True | exact native |
| p2-forward | Right | 45, `HA BETA GAMMA <#>DELTA¶P3 third` | 45 | 45 | exact | True / True | exact native |
| p2-forward | Up | 24, `aragraph above<#>¶P2 ALPHA BETA` | 24 | 24 | exact | True / True | exact native |
| p2-forward | Down | 75, `aragraph below<#>` | 75 | 75 | exact | True / True | exact native |
| p2-forward | Home | 25, `ragraph above¶<#>P2 ALPHA BETA ` | 25 | 25 | exact | True / True | exact native |
| p2-forward | End | 50, `TA GAMMA DELTA<#>¶P3 third para` | 50 | 50 | exact | True / True | exact native |
| p2-backward | Left | 33, `above¶P2 ALPHA<#> BETA GAMMA DE` | 33 | 33 | exact | True / True | exact native |
| p2-backward | Right | 35, `ove¶P2 ALPHA B<#>ETA GAMMA DELT` | 35 | 35 | exact | True / True | exact native |
| p2-backward | Up | 13, `P1 first para<#>graph above¶P2` | 13 | 13 | exact | True / True | exact native |
| p2-backward | Down | 63, `A¶P3 third par<#>agraph below` | 63 | 63 | exact | True / True | exact native |
| p2-backward | Home | 25, `ragraph above¶<#>P2 ALPHA BETA ` | 25 | 25 | exact | True / True | exact native |
| p2-backward | End | 50, `TA GAMMA DELTA<#>¶P3 third para` | 50 | 50 | exact | True / True | exact native |
| s1 | Left | 100, `ber oscar papa<#> quebec romeo ` | 100 | 100 | exact | True / True | ref 100, emu 100 |
| s1 | Right | 102, `r oscar papa q<#>uebec romeo si` | 102 | 102 | exact | True / True | ref 102, emu 102 |
| s1 | Up | 0, `<#>S1 alpha bravo` | 0 | 0 | exact | True / True | ref 0, emu 0 |
| s1 | Down | 195, `four five six <#>seven eight ni` | 201 | 201 | no | True / True | ref 195, emu 195 |
| s1 | Home | 101, `er oscar papa <#>quebec romeo s` | 101 | 101 | exact | True / True | ref 101, emu 101 |
| s1 | End | 194, ` four five six<#> seven eight n` | 200 | 200 | no | True / True | ref 194, emu 194 |
| s2 | Left | 483, `rst visual lin<#>e S2 second vi` | 483 | 483 | exact | True / True | exact native |
| s2 | Right | 485, `t visual line <#>S2 second visu` | 485 | 485 | exact | True / True | exact native |
| s2 | Up | 406, `ynine thirty t<#>hirtyone thirt` | 406 | 406 | exact | True / True | exact native |
| s2 | Down | 503, `econd visual l<#>ine¶S3 text be` | 503 | 503 | exact | True / True | exact native |
| s2 | Home | 464, `irtyfive end1¶<#>S2 first visua` | 464 | 464 | exact | True / True | exact native |
| s2 | End | 484, `st visual line<#> S2 second vis` | 484 | 484 | exact | True / True | exact native |
| s3 | Left | 541, `mpty paragraph<#>¶¶S3 text afte` | 541 | 541 | exact | True / True | exact native |
| s3 | Right | 543, `ty paragraph¶¶<#>S3 text after ` | 543 | 543 | exact | True / True | exact native |
| s3 | Up | 507, `d visual line¶<#>S3 text before` | 507 | 507 | exact | True / True | exact native |
| s3 | Down | 543, `ty paragraph¶¶<#>S3 text after ` | 543 | 543 | exact | True / True | exact native |
| s3 | Home | 542, `pty paragraph¶<#>¶S3 text after` | 542 | 542 | exact | True / True | exact native |
| s3 | End | 542, `pty paragraph¶<#>¶S3 text after` | 542 | 542 | exact | True / True | exact native |
| s4 | Left | 586, `raph¶S4 cell A<#>1 text¶S4 cell` | 586 | 586 | exact | True / True | exact native |
| s4 | Right | 588, `ph¶S4 cell A1 <#>text¶S4 cell B` | 588 | 588 | exact | True / True | exact native |
| s4 | Up | 554, `h¶¶S3 text aft<#>er the empty p` | 554 | 554 | exact | True / True | exact native |
| s4 | Down | 619, `ext¶S4 cell A2<#> text¶S4 cell ` | 619 | 619 | exact | True / True | exact native |
| s4 | Home | 577, `pty paragraph¶<#>S4 cell A1 tex` | 577 | 577 | exact | True / True | exact native |
| s4 | End | 592, `4 cell A1 text<#>¶S4 cell B1 te` | 592 | 592 | exact | True / True | exact native |
| s5 | Left | 592, `4 cell A1 text<#>¶S4 cell B1 te` | 592 | 592 | exact | True / True | exact native |
| s5 | Right | 594, `cell A1 text¶S<#>4 cell B1 text` | 594 | 594 | exact | True / True | exact native |
| s5 | Up | 543, `ty paragraph¶¶<#>S3 text after ` | 543 | 543 | exact | True / True | exact native |
| s5 | Down | 625, ` cell A2 text¶<#>S4 cell B2 tex` | 625 | 625 | exact | True / True | exact native |
| s5 | Home | 593, ` cell A1 text¶<#>S4 cell B1 tex` | 593 | 593 | exact | True / True | exact native |
| s5 | End | 608, `4 cell B1 text<#>¶S4 cell A2 te` | 608 | 608 | exact | True / True | exact native |
| s1d | Left | 100, `ber oscar papa<#> quebec romeo ` | 100 | 100 | exact | True / True | ref 100, emu 100 |
| s1d | Right | 102, `r oscar papa q<#>uebec romeo si` | 102 | 102 | exact | True / True | ref 102, emu 102 |
| s1d | Up | 0, `<#>S1 alpha bravo` | 0 | 0 | exact | True / True | ref 0, emu 0 |
| s1d | Down | 195, `four five six <#>seven eight ni` | 201 | 199 | no | True / False | ref 195, emu 194 |
| s1d | Home | 101, `er oscar papa <#>quebec romeo s` | 101 | 101 | exact | True / True | ref 101, emu 101 |
| s1d | End | 194, ` four five six<#> seven eight n` | 200 | 200 | no | True / True | ref 194, emu 194 |
| m1d | Left | 86, `ydinsxdinsxchm<#>rwbglqvafkpuze` | 88 | 88 | no | True / True | ref 86, emu 86 |
| m1d | Right | 88, `insxdinsxchmrw<#>bglqvafkpuzejo` | 90 | 90 | no | True / True | ref 88, emu 88 |
| m1d | Up | 0, `<#>afkpuzejotydin` | 0 | 0 | exact | True / True | ref 0, emu 0 |
| m1d | Down | 175, `fkpuzejotydins<#>xchmrwbhmrwbgl` | 180 | 270 | no | True / False | ref 175, emu 261 |
| m1d | Home | 87, `dinsxdinsxchmr<#>wbglqvafkpuzej` | 89 | 89 | no | True / True | ref 87, emu 87 |
| m1d | End | 175, `fkpuzejotydins<#>xchmrwbhmrwbgl` | 180 | 180 | no | True / True | ref 175, emu 175 |

Bottom lines (per browser and round, `summary.md` of each round): old 12 arms = native `ref` **12/12**; S1-S5 exact = native `ref` **28/30**, by rule **30/30** (the two exceptions are S1 Down and S1 End, both determined by the second wrap: Down = start of line 3 = W2 = 195 (native 201), End = W2 - 1 = 194 (native 200)); `s1d` / `m1d` Left, Right, Up, Home, End by rule **10/10**; `s1d` / `m1d` Down: **follows the native `ref` rule** (195 = W2 for `s1d`, 175 = B2 for `m1d`), **not** the native `emu` (199 near the end of line 2 / 270 = B3).

Why the drag shapes do not reproduce the native limit: `beforeKey.caret` (what the page's `editorState.caret` holds and the planned fix clicks at) after the page's own drag is `1418, 1694` = the START of line 2, equal to the selection end rectangle (`selection.end` `1418, 1694`) in all 48 `s1d` / `m1d` key arms (2 shapes x 6 keys x 2 browsers x 2 rounds; `beforeKey.caret` = `beforeKey.selection.end` = `1418, 1694`); the native tool's raw mouse events left the visible cursor at the END of line 1 (`11021, 1418` / `11322, 1418`) with the selection end at the start of line 2. The click at the visible cursor on WASM is therefore the native `emuend` arm (click at the selection end), which was `same` as `ref` in 18/18 native cells. The extra `reach` arms (no key; `reach-<shape>-<delta>`, the drag's far end `delta` twips right of the end of line 1, deltas 0, 100, 400, 900; `round-*/arms-<browser>.jsonl`, `kind: reach`) show it is not the 400 twips I chose: S1 delta 0 (far end exactly at the End position, before the trailing space) gives selection `scar papa` with the caret at the line-1 end `10961, 1418` and `selection.end` equal to it (the point is offset 100, no ambiguity); deltas 100, 400, 900 give `scar papa ` (with the space) with caret and `selection.end` both at `1418, 1694`; the token gives `xdinsxchmr` with caret and selection end at `1418, 1694` for all four deltas. So in all 32 reach arms (8 per browser and round) the visible caret equals the selection end (checked mechanically over the raw files), and in the 48 key arms it is the start of line 2: **the Down deviation was not reachable with the page's own drag on WASM**. It may still be reachable by other ways of making a selection that the page cannot make today (Shift+End needs the link batch); this was not measured.

### Timing (keydown -> the move's latency record), toasts, pill

| | Chrome r1 | Chrome r2 | Firefox r1 | Firefox r2 |
|---|---|---|---|---|
| keys that moved the caret (47 arms): key -> move done, min / median / max ms | 80.8 / 81.8 / 95.1 | 81.3 / 81.9 / 94.0 | 83.5 / 84.7 / 120.8 | 84.0 / 84.6 / 87.7 |
| of which key -> click done (`定位游標 N ms` record) | 25.6 / 27.1 / 41.7 | 26.1 / 27.4 / 39.3 | 28.0 / 29.4 / 33.0 | 27.9 / 28.9 / 31.6 |
| keys that did NOT move the caret (7 arms): key -> move done | 280.8 / 282.5 / 283.3 | 281.5 / 282.9 / 284.5 | 285.2 / 286.9 / 299.4 | 285.3 / 286.4 / 289.4 |
| toasts in the 54 arms (whole arm after the open) | 0 | 0 | 0 | 0 |
| pill ever `stopped` | no | no | no | no |

- The 400 ms `caretAckGraceMs` is never paid: the click is done 25.6-41.7 ms after the keydown in all 216 counted arms, every `定位游標` record is from the answered click.
- The 7 slow arms per browser and round are the same 7 in all four runs: `s1-Home`, `s2-End`, `s3-Home`, `s3-End`, `s5-Home`, `s1d-Home`, `m1d-Home` - exactly the arms where the key does not move the caret (the point is already at the line start / end). A move that moves nothing waits ~255 ms for the engine whatever page it is on: the control `round-20261012T042238Z-control` (collapsed caret on the patched page, so the page's ordinary `editorAction` path, no click) gives, 3 repeats each, Chrome 251.8-252.4 ms for `Home` at line start / `End` at line end / `Up` at the top of the document (caret does not move) against 34.2-41.5 ms for a move that moves (`Home`, `End`, `Right`), Firefox 251.9-262.2 against 37.7-40.2. The fix therefore adds the click (~27-29 ms) to a move; the extra ~200 ms of the 7 arms is the engine's wait for a move that produces no callback and is the same without the fix (inferred as a mechanism; the 252 ms is measured, the mechanism is not read from source). A click-then-move that moves finishes 53-90 ms after the click (medians 54-56 ms; the 90 is one Firefox arm of round 1) against 34-42 ms for the same move collapsed.
- Machine condition: another process on this machine (the owner's `.venv/bin/python app.py`, ~16-25 GB resident) kept memory nearly full and the swap busy during round 1 (MemAvailable 1.2-2.5 GB; pages swapped per arm in the hundreds of thousands); round 2 ran with MemAvailable 4-6 GB and ~1-170k pages per arm. The timings are the same in both rounds (medians 81.8-82.0 ms Chrome, 84.6-84.7 Firefox), so memory pressure is not what the numbers show. `swapDuringArm`, `loadavgStart/End` per arm and `machine-at-*.txt` are in the raw files.

### Shift arms and the red control (both browsers, both rounds identical)

- `shift-collapsed`: caret at P2 offset 9 (`2565, 1694`), real Shift+Right x3 (Chrome: modifiers 8; Firefox: Shift key down + ArrowRight, so the keydown log also holds `Shift`): the caret is unchanged (`2565, 1694`), revision 0 -> 0, selection still collapsed, no latency record, no toast; the `#` typed afterwards lands at paragraph 1 offset 9 (flat index 34).
- `shift-range`: forward `BETA GAMMA`, real Shift+Right x1: `getSelection` text `BETA GAMMA` before and after, same caret (`4152, 1694`), same selection rectangles, revision 0 -> 0, toolbar shape `range-single` before and after, no latency record, no toast.
- Red control (`dist` page + the one line): forward Left, forward End, backward Down on P2 are each refused: the toast is `◀：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged` (`移到行尾：…`, `下移一行：…` for the other two), the latency line `◀ 失敗` / `移到行尾 失敗` / `下移一行 失敗`, the toolbar shape stays `range-single`, the caret unchanged. 3/3 in each browser and round, the sentence as in `findings/evidence/129/README.md`.

### Predictions

| prediction | verdict | what the raw output shows |
|---|---|---|
| P-M4a (12 old arms = native `ref`, 12/12 each browser) | **held** | 12/12 in Chrome and Firefox, in both rounds |
| P-M4b, first clause (S1-S5 = native `ref`) | **held, 2 of 30 cells by rule** | 28/30 exact; S1 Down (195, native 201) and S1 End (194, native 200) follow from the second wrap (W2 = 195 on WASM, 201 native): Down = start of line 3, End = W2 - 1; 30/30 by rule, both browsers, both rounds |
| P-M4b, second clause (`s1d`, `m1d`: Left, Right, Up, Home, End follow the native rule) | **held** | 10/10 by rule |
| P-M4b, third clause (`s1d`, `m1d` Down follows the native `emu`, "the named limit shows up on WASM too") | **missed** | Down follows the native `ref` rule (195 = W2, 175 = B2) in 2/2 shapes x 2 browsers x 2 rounds; the page's drag leaves the visible caret at the start of line 2, not at the end of line 1 (above) |
| P-M4c, no toast on the patched page | **held** | 0 toasts, pill never `stopped`, in 216 counted arms |
| P-M4c, key-to-move < 200 ms in every arm | **missed for the 7 arms per browser and round in which the key does not move the caret (281-299 ms)**; held for the 47 that do (80.8-120.8 ms) | the 252 ms is the engine's cost of a move that moves nothing, measured without the fix in the control; the 400 ms grace is never paid (click done 26-42 ms) |
| P-M4d (`shift-collapsed`, `shift-range` change nothing, no toast) | **held** | above |
| P-M4e (red control refused with the developer sentence) | **held** | 3/3 in each browser and round |

### Instrument notes

- Counted arms: 216 of 216 `counted` (54 per browser and round); no `selection-mismatch`, no `runner-error`, no arm not fresh. The selection read-back equalled the expected text in every arm except S5, whose expectation is the native read-back and equalled it too: `S4 cell A1 text<TAB>S4 cell B1 text<LF>` (a cell selection A1:B1, as native).
- Development before the counted rounds (scratch, outputs not kept): four Chrome runs fixed (a) the calibration walk - the first version pressed Home straight after End, and on a line that breaks mid-word End puts the caret at the end of line n whose layout position is the start of line n+1, so Home went to line n+1 and the recorded line starts of the wrap fixture were wrong (the same effect the native extras are about); the walk now returns to the line start by a click inside the line then Home; (b) `session.save()` returns `{bytes, revision, contentStamp}`, not the bytes; (c) `copySelection()` returns only code point counts and writes the clipboard, so the selection text is read with `session.document.getSelection()`.
- `str.splitlines()` splits JSON lines at U+2028 (the line-break character in the S2 paragraph), which the first version of the probe wrote raw into `arms-*.jsonl` (`ensure_ascii=False`): the data were never affected, but a reader using `splitlines()` sees broken lines. `analyze_129_m4.py` splits on `"\n"`; the probe was changed to escape U+2028 for later runs (round 2 and the control round have it; round 1's files hold it raw).
- `round-20261012T042238Z`: `tools/run_probe_129_m4.sh` was edited while that round's runner was still running, so it has no `ended-utc.txt` / `machine-at-end.txt` (note in the folder); the probe processes had loaded `probe_129_m4_wasm.py` (copy: `probe_129_m4_wasm.as-run.py`, sha256 `02c7b7c0…` = `inputs.sha256`) and ran to completion. Round 2 and the control round copy the tool they ran.
- The first Chrome arm after the calibration walk of a round is a little slower (95.1 ms Chrome, 120.8 ms Firefox in round 1; not repeated in round 2).
- `keydown` times and latency records are `performance.now()` of the page; "key -> move done" is the time from the capture-phase keydown to the first latency-line change that is not the click's `定位游標`. It is not a key-to-ink time.
- Not covered: Shift-extended selections (not possible on this page), a selection made across pages, RTL / CJK text (the token imitates a break between any two characters; the owner's documents are Chinese), the owner's own fixtures, and WASM builds other than the shipped one under `dist/`.
