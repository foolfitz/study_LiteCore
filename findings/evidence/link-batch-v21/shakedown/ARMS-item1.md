# v21 WASM shakedown, item 1 (Ctrl+Home/End): the arms, written before any run

Task: `handoff/tasks/TASK-2026-10-16c-v21-shakedown-arms.md`, Agent D (item 1). Criteria: `specs/SPEC-M3-link-batch-v21.md` §11.0 and §11.1 (pinned at `523871fa`); §12.1 does not touch item 1. Context: `handoff/HANDOFF-2026-10-16b-v21-linked-shakedown-next.md`, Next 1. Shape imitated: `findings/evidence/link-batch/v20-shakedown/ARMS.md`.

This file is committed before the first browser run of any arm below. It is never edited afterwards: corrections are appended to the results README beside it. Phase B (runner and judge) is written after the main session has reviewed and committed this file. Nothing here was run in a browser. The only commands run while writing it were read-only: `sha256sum`, `tools/build_cutover_page.py --profile e2-editor-v21` without `--write`, `shell_lagging_source(dist)`, the native D1 population and reader (re-run, output byte-identical to the committed one), and a scratch prototype of the fixture conversion (§2.5), which is not a deliverable.

**Labels.** **[source] file:line** = read in code; **[observed] path** = read from an existing evidence file or a command output named in §0; **[inferred]** = my reasoning.

**Path shorthands.** `wsp/` = `wasm_sdk_probe/`. `N142/` = `findings/evidence/link-batch-v21/native/142-ctrl-home-end/`. `D1M/` = `N142/d1-marker/`. `PAGE` = `wsp/web/e2-editor-app.js` (the tree version). `SESSION` = `wsp/editor-shell-v2/narrow-editor-v2-session.js`. `CLIENT` = `wsp/editor-shell-v2/narrow-editor-v2-client.js`. `ENGINE` = `wsp/src/probe_engine.cpp`. `WORKER` = `wsp/sdk/sdk-worker.js`. `V20R` = `wsp/tools/run_v20_shakedown.py`. `MWS` = `wsp/tools/run_merge_wasm_shakedown.py`. `PP` = `wsp/tools/run_e2_c_product_path.py`. `P14N` = `findings/evidence/host-0.2.20-hand-test/probe_10_14n.py`. `HT` = `findings/evidence/host-0.2.20-hand-test/README.md`. `V20S` = `findings/evidence/link-batch/v20-shakedown/README.md`.

## 0. Identities measured 2026-10-16, before this file

| item | value | label |
|---|---|---|
| tree | HEAD `477f2a86` | [observed] `git rev-parse` |
| profile `e2-editor-v21` (read-only) | wasm `db3408f55316bf67345258ce9f7cb58a1cb3777c9aabb9f7790bee69e1599f30`, loader `0b6cf02a51aba353d880824ab32254e551a389c58d3c219439c7641f7ce76587`, worker `0d55bcfa2ee0e4ddc6239e25282001c13410b152a5a08ebac9903cc65c3fd350`, manifest `72067d5a14a3a271137a17aea24317fc6f42380327ec4962ebff475589268f13` | [observed] `sha256sum wsp/dist/profiles/e2-editor-v21/*` |
| manifest content used below | `abiVersion` 5; 23 actions; `move-document-start` id 22 and `move-document-end` id 23, both `gestures ["collapsed"]`, `limits ["no-extend-selection"]`; `select-all` `gestures []`; `gestureBits` collapsed 1, range-single 2, range-cross 4 | [observed] the v21 manifest, read with `json` |
| tree worker | `wsp/sdk/sdk-worker.js` = `0d55bcfa…`, the same bytes as the profile's worker, so `sdk/tests/sdk-worker-v21.test.mjs` tests the shipped worker | [observed] `sha256sum` |
| page source | `PAGE` `bd15e7efbc66d4cc3a3010195c38c38b01e92aedb24dcf9e69581ee924bc1496` | [observed] |
| page served | `3d5112161b23b060b2057a25bbbeb7cbc96628cde67e3e5c3c0dab92b435b5c5`, pin `313b08d5cb085897 -> db3408f55316bf67`, `written no` | [observed] output of `python3 tools/build_cutover_page.py --profile e2-editor-v21` |
| HTML source | `wsp/web/e2-editor.html` `1d15814949c633ce43cb1240c30dd48cf982aca008f4ca25d401f4088c67764e` | [observed] |
| lagging shell files | `shell_lagging_source(dist)` = `editor-shell-v2/narrow-editor-v2-client.js` (`c5ab9d17c7ad0e3de5e982ad6e0f4744bd16deb5bfd3d8b7cfcc8367609467ad`), `editor-shell-v2/narrow-editor-v2-session.js` (`443e0f1e7c85f359cc9ef2db071cf449ba7be8ff11b15770d2189bd42bab8e5f`), `editor-shell-v2/paragraph-editor-client.js` (`4616ae1715a57927fdf11aaf45004dfd4656bf3c816ee7cebeedd203c180a9c6`), `sdk/document-sdk.js` (`9dcb83120c144cad5cf04cabcc14452255d0a640200b8e08f5eed4d4c2d63539`), `web/e2-editor.html` (as above); hashes are the tree source bytes | [observed] evaluated `PP shell_lagging_source` |
| v20 manifest (D5) | `wsp/dist/profiles/e2-editor-v20/sdk-manifest.json` `50aade86f7996ba66c7ca9a3784d9b1074c8d98c05cbe9788902e89cc5a522a0` | [observed] |
| native reference, D1 | `N142/out/arms.json` `b2863782997e91b7eb1bc11ba1cdbce3a2f8503b5b34e540c5ca6b6aac0ed52e`; `D1M/out/population.json` `58bc92f6730c2b8bea97b7bf18a93778b597f3e006ccc92aa357098daff0cb76`; `D1M/SHA256SUMS` `4cc0f2106b4e81fe1554cd7204abdce1a0f1690762e7babccd13da69c620ff90` (every entry verifies); `D1M/tool/read_marker.py` `375b9cccf7febd2566ec15954558202b49c36e675abca4a654cd11b2ee842471`; `D1M/tool/d1_population.py` `c21fda7ae916b01b46084593f3bfd528ad53438939b27e14b6a8ea1466e804e3` | [observed] `sha256sum`, `sha256sum -c` |
| native reference, 142 parent | `N142/SHA256SUMS` `89695e9c273aa1b3ef0f24a9ddaae804fea377e443de949d691fd91c15e6c47e`; every data entry verifies; the `README.md` entry fails because the 2026-10-16 correction was appended after the sums were written; `N142/tool/read_results.py` `e7270d16bec877c9936e997d9cce81ca995a288e1dfcb70b3dec83b70227bf7b` | [observed] `sha256sum -c`; the correction is at the end of `N142/README.md` |
| native reader re-run | `d1_population.py` prints `GREEN: 38 IN, 43 OUT, 81 total`; `read_marker.py out ../fixtures ../out/arms.json ../out` exits 0 and its output equals `D1M/out/reader-output.txt` byte for byte | [observed] re-run 2026-10-16 |
| fixtures (`.fodt`) | bullet `1475af1d71a2c83914aa302b3644c97201fec508a9608b316dfc38357e5f0dd3`; header-footer `32d90335308f42a4b0c1f4e5f39c08ecc32a2b3cf93cd28cd50f218937af2be4`; indent `55ca3db2b798e37fcc43d8f0e62977352fbf66b9510d82ce5bd6ad57218ff282`; numbered-first `0960ed908dd54577adc2af0b1cd20d39c6d725ad096b73a078b1ea96ef964db5`; numbered-second `1d863b4194a96713788061bc9b8996d7e59f1dc037814a8de2529b1d71606614`; plain3 `c6a8aab8ba6bb279accc83d00080895e6e4f623b87982413a3c8d62a5beb09c8`; section-mid `2f1a80ca2f9f86b33654cfad2ef4f9d935215a6c848b60cec808e5dce7ae4c4a`; table-first `ed1ffbef16035d573320955d7d7ee67f3ecc52f5a0bbfa54678e66bf056e98c1`; table-last `bc015ba1d6ab678803eb73a4c5a392eb6f7fe1d5d7005d2dc09caa084ab9e0e7`; table-mid `92989645f4bce1d60f51684d6b887b21e87927a3e1a7ee0847996ca572a8df0c` | [observed] `sha256sum N142/fixtures/*.fodt`, equal to `N142/SHA256SUMS` |
| committed unit tests cited | `page-document-keys.test.mjs` `35fe287c…`; `page-held-after-move.test.mjs` `594029b9…`; `closed-lists.test.mjs` `3bc05b9a…`; `declaration-drift.test.mjs` `43a5f91f…` (all `wsp/editor-shell-v2/tests/`); `wsp/sdk/tests/sdk-worker-v21.test.mjs` `5a433ce5…`; `findings/evidence/link-batch-v21/part-s-red/mutations.json` `dfb4ded2…` | [observed] `sha256sum` |
| D2 probe | `P14N` `4e92e92088a382e69baf44ef22cf2ef3e555449592b96877d3aa71445c094159` | [observed] |

## 1. What every item-1 report records (§11.0 「證據的身分」)

- The served page's sha256, which must equal `3d511216…` or the judge refuses the report (the v20 judge's mandatory `--expect-page` [observed] `V20S` §8 item 7). Also the page source's sha256 and the HTML source's sha256 before the observer goes in ([source] `MWS:1176-1192` binds `htmlSha256` that way).
- The profile's four hashes read from `dist/`, and the worker as served. They must equal §0 except on a declared diagnostic arm; item 1 has none.
- The sha256 of each of the five lagging shell files as served (tree bytes), and the shell digest computed over the mirror with `MWS shell_digest` ([source] `MWS:1154-1159`: every bundle module except the entrypoint). It must later equal the frozen v74's, or the report is void (§11.0).
- Every input's sha256 (each converted `.odt`, the generated long document, the M6 corpus for D6) and every reference's sha256 (§0 rows "native reference", plus each native file a judge reads).
- Browser and version, `startedAt`/`completedAt`, the runner's and the judge's sha256.
- Pre-run checks (§2.9).

## 2. Shared machinery (each arm below refers to these)

### 2.1 The served tree

- `wsp/dist/` is mirrored with `PP build_mirror` ([source] `PP:2501-2531`: symlinks, with the overridden files written). Nothing is written to `dist/`.
- Overrides:
  - `e2-editor-app.js` = `PP repointed_page(PAGE, "e2-editor-v21", manifest)` ([source] `PP:445-470`; `build_cutover_page.py` calls the same function);
  - the five lagging files = the tree's source bytes. This replaces the v20 runner's refusal on lagging files ([source] `V20R:1136-1138`), as the brief fixes;
  - `e2-editor.html` = the tree source with the observer inserted before the module script (the v20 anchor, [source] `V20R:1141-1146`).
- Fixtures are written into the mirror root as `./v21-<name>.odt` and opened through the product's `#file` input with `PP OPEN_FILE` ([source] `PP:774-790`). It fetches the bytes, builds a `File` with the given name and fires `change`; the page's handler then opens it ([source] `PAGE:3713-3727`). The input accepts `.odt` ([source] `wsp/web/e2-editor.html:284`).
- Served by `wsp/web/serve.py` on a free port, as in `V20R:1188-1189` [source].

### 2.2 The observer

v20's observer is reused as is ([source] `V20R:79-276`):
- a `Worker` wrapper;
- a DOM trace node, because Firefox evaluates in a Marionette sandbox;
- the ask channel, which copies the page's `protocolVersion` ([source] `V20R:132-143`);
- chunked drains ([source] `V20R:345-363`). The chunking exists because the CDP client closes on a frame over 1 MiB ([observed] `V20S` §6, run 2).

New in phase B:

- **(a) Keys.** Window capture-phase listeners for `keydown`/`keyup` record key, `ctrlKey`, `metaKey`, `shiftKey`, `repeat`, the focused element and the page time (the shape of `P14N:90-94` [source]). A window bubble-phase `keydown` listener records `defaultPrevented`. It runs after the page's sink listener, which is where the page calls `preventDefault` for Ctrl+Home/End ([source] `PAGE:3340-3346`). A capture listener on `#sink` records `beforeinput` `inputType`.
- **(b) State.** A `MutationObserver` on `#state-pill`, `#s-pending`, `#s-latency`, `#s-checkpoint`, `#s-generation` and `#page-status` (text, `hidden`) logs each change with the page time (the `tick` shape, [source] `P14N:83-89`).
- **(c) D7's read.** When a response to `editorActionV2` arrives for `move-document-start` or `move-document-end` with `ok: true`, a page-side `setTimeout(500)` posts one `editorGetStateV2` ask (`requestId` ≥ `0x7F000000`, [source] `V20R:70`). It logs the reply's page time, `askPostedAt`, and the ask's answer: `caret`, `selection.{collapsed, rectangles.length, observed}`, `selectionType`, `selectionText`, `revision`.
  - The engine reads the selection fresh for this request ([source] `ENGINE:6120-6141`). The worker passes `selectionType`/`selectionText` through ([source] `WORKER:1026-1028`).
  - Scheduled in the page, not by the runner: the runner sees the trace only when it drains, every 100 ms ([source] `V20R:494-504`), which is too coarse for a ±50 ms window. See DECISION D-15.
- **(d) D10's first read.** When `#s-latency` changes to text that starts with the move's label (`移到文件結尾`, [source] `PAGE:2204-2212`), one `requestAnimationFrame` later the observer takes v20's `GEOMETRY` read ([source] `V20R:285-295`) and `#page-status`. The label is written once the operation has resolved ([source] `PAGE:2103`).
- **(e) D11a only.** The harness host shim (§3, D11).
- Editor-state pushes already carry `sel.observed` ([source] `V20R:147-149`, `:164-171`).

### 2.3 Real input

- **Keys.** CDP `Input.dispatchKeyEvent` in Chrome, geckodriver key actions in Firefox. A synthetic `KeyboardEvent` is never dispatched.
  - Plain keys: `V20R press` ([source] `V20R:366-386`; arrows, Home, End, Backspace, Delete).
  - The letter `Z`: `MWS press` (uppercase sends Shift, [source] `MWS:397-417`).
  - Ctrl chords: `P14N ctrl_key` ([source] `P14N:228-241`: CDP `modifiers: 2`, WebDriver `\ue009`).
  - New: a Cmd chord (CDP `modifiers: 4`, WebDriver `\ue03d`) for D5-w.
- **Held keys.**
  - Flagged repeats: `V20R hold_key` ([source] `V20R:388-419`), new variant with Ctrl held.
  - Unflagged release/press pairs: `P14N burst_key` ([source] `P14N:189-225`), new variant with Ctrl held.
  - CDP and WebDriver flag repeats: 84 of 85 in 10-14n, 251 of 255 in 10-14l ([observed] `HT:68`, `HT:89`).
- **Pointer.**
  - Real click: `P14N real_click` ([source] `P14N:175-186`).
  - New real drag: CDP `mousePressed` at A, at least 3 `mouseMoved`, `mouseReleased` at B; WebDriver `pointerMove`/`pointerDown`/`pointerMove`/`pointerUp`.
  - A twips point (x, y, h) becomes `#paper` fractions `x/docW`, `(y + h/2)/docH`, the formula `MWS place` uses ([source] `MWS:686-687`), then a viewport point from `#paper`'s bounding box. The document size comes from the open and paint replies the observer keeps ([source] `V20R:193-204`).

### 2.4 The start state of every arm (unless the arm says otherwise)

1. Open the fixture as in §2.1. Wait until `doc == name` and `state == ready` ([source] `MWS:661-664`), then quiet: `ready` with `pending 0` for 0.5 s ([source] `MWS:449-461`).
2. Wait for an editor-state push of the current generation with `selection.observed === true`, for at most 10 s, and record the delay since `ready`.
   - Until core has reported a selection, every non-paragraph action, moves included, is refused with `EDITOR_FORMAT_GESTURE_UNSUPPORTED` ([source] `ENGINE:5546-5558`; the flag is set on the first `TEXT_SELECTION`, `ENGINE:2626-2630`).
   - Such refusals were seen for about 0.85–0.99 s after a reopen ([observed] `findings/evidence/132/held-into-refusal/ruling/ruling-1.md:39`).
   - No observation within 10 s makes the round `not-observed`, which counts as not done. DECISION D-6.
3. Give the sink focus without moving the caret: evaluate `#sink.focus({preventScroll: true})`. The page makes the same call on a toolbar `mousedown` ([source] `PAGE:2508-2512`). Record `document.activeElement === #sink`. DECISION D-5.
   - Reason: after an open, keys land on `body` until the user clicks the document ([observed] `HT:17`). A click would send `placeCaret` and change the arm.
4. Before every Ctrl press and before the marker: no editor-state push for 1.5 s, the native probe's pre-press quiet ([observed] `N142/README.md`, "What a measured press records").

### 2.5 Fixtures: how the `.fodt` sources reach the page as `.odt`

- **Sources.** The ten `N142/fixtures/*.fodt` (§0) [observed].
- **Conversion** (DECISION D-4, recommended B): a new deterministic repackager. It copies byte-for-byte slices of the flat file:
  - `office:body` into `content.xml`;
  - `office:master-styles` into `styles.xml`;
  - each child of `office:automatic-styles`: `style:page-layout` into `styles.xml` only, every other child into both files.
  - `mimetype` is stored first, then a manifest. Timestamps and member order are fixed, so each fixture has one sha256, committed with the converter and recorded before the first run.
  - Precedent that a minimal ODT of this kind opens on WASM in both browsers: `V20R build_indent_fixture` ([source] `V20R:526-559`; [observed] `V20S` §3, the "C1 recorded" row, and §5 item 3).
- **What proves that the conversion kept the structure the comparison reads:**
  - (i) For all ten fixtures, `adapter(odt) == read_marker.paragraphs(fodt)` over (part, index, text). This is D1's cross-container red case (§2.7) used as the conversion check.
  - (ii) The three copied slices are byte-identical between the `.fodt` and the part each went into. This covers what `paragraphs()` does not see: the table, section, list and indent markup.
  - (iii) Per run, the WASM saved document with the marker removed is compared with the native saved document with the marker removed, in `compare_rest`'s shape ([source] `D1M/tool/read_marker.py:90-107`). Recorded, not judged.
- **Prototype.** A scratch prototype of B (ElementTree-based, not the deliverable) gave deterministic bytes for all ten fixtures, and (i) held for all ten. A mutated adapter that drops the master part still passed (i) on nine of the ten; only `header-footer` caught it [observed] (scratch run 2026-10-16, not committed).
  - No D1 fixture has a master-styles paragraph, so the red case must include `header-footer.fodt` even though no D1 arm uses it [inferred].

### 2.6 D1's step grammar on the page

The grammar is `D1M/README.md:24-35` [observed]. Every IN arm's D1 script is its 142 steps up to the last Ctrl press, then `T,S,L` ([source] `D1M/tool/d1_population.py:154-162`). The runner refuses an unknown step kind, as the population tool does ([source] `D1M/tool/d1_population.py:54-107`).

| step | native meaning | product-path action on the page | wait / verify |
|---|---|---|---|
| `k1024`, `k1025`, `k1027`, `k1028`, `k1029` (`xN` = N presses) | Down, Up, Right, Home, End posted as raw keys | Real ArrowDown, ArrowUp, ArrowRight, Home, End. The page maps them to `move-line-down`/`-up`, `move-character-right`, `move-line-home`/`-end` ([source] `PAGE:3041-3048`), and the engine posts `Key::DOWN` etc. on the same key path ([source] `ENGINE:5692-5711`) | One press at a time: wait for its `editorActionV2` response, then the next; quiet after the step |
| `r<name>` | record the caret rectangle as a point | Instrument only. One `editorGetStateV2` ask after quiet records `caret {x, y, width, height}` in twips. This is the WASM caret, not the native one (fonts differ, finding 113) | — |
| `s<a>:<b>` | text-handles range from point a to point b (`setTextSelection` RESET/START at a, END at b, the path `oxsdk_editor_select_range` uses [observed] `N142/README.md`, "Placement") | Real pointer drag on `#paper` from a's point to b's. The page's drag sends `session.selectRange(start, end)` ([source] `PAGE:2559-2565`, `:2635-2646`, `:2652-2660`), which reaches the same engine path | An ask after quiet: `selectionType` `text` and `selectionText` equal to the native press record's `before.selText` (`'second'`, or `'second paragraph\nCharlie'` [observed] `N142/README.md`, results table). Otherwise `placement-mismatch` (DECISION D-17) |
| `c<name>` | engine click at the point | Real click (`P14N real_click`). The page sends `placeCaret` ([source] `PAGE:2652-2660`). No IN arm has one ([observed] `D1M/out/population.txt`); listed so the grammar is closed | Its `editorPlaceCaretV2` response |
| `M…=9220` / `M…=9221` | Ctrl+Home / Ctrl+End | Real Ctrl+Home / Ctrl+End. The page takes them before `if (accel) return;` ([source] `PAGE:3168-3169`); on a range it goes through `moveFromPoint` ([source] `PAGE:3322-3337`, `:3276-3294`) | Its response, then D7's +500 ms ask (§2.2 (c)) answered, then quiet |
| `T` (D1 only) | `paste(text/plain, "Z")`, the engine's insert-text handler ([observed] `D1M/README.md:82`) | Real key `Z` into the sink. The textarea's `beforeinput` goes through the input adapter to `insertText` (`_request("insertText")`, [source] `wsp/sdk/document-sdk.js:537`). The observer records the request's op name, which settles the question `D1M/README.md:87` left open | Its response, then quiet |
| `S` | saveAs fodt | The product's save: the `save` toolbar action, bytes caught by `PP INSTALL`'s `createObjectURL` hook (`MWS save`, [source] `MWS:644-658`; `PP:190-243`). The saved `.odt` is kept as evidence | Save count +1 |
| `L` | locator (instrument) | None. It is a native instrument; the saved ODT is the reader's input | — |

### 2.7 The ODT marker reader (D1's adapter) and its four red cases

- **The adapter.** A new module that loads `D1M/tool/read_marker.py` unchanged, by path, the way `read_marker.py` itself loads `d1_population.py` ([source] `D1M/tool/read_marker.py:110-115`). It returns `[p for p in paragraphs(styles.xml) if p[0] == "master"] + [p for p in paragraphs(content.xml) if p[0] == "body"]`.
  - In both files the part is a direct child of the root, and `paragraphs()` does `root.find(master-styles | body)` ([source] `D1M/tool/read_marker.py:74-87`). So the paragraph-order definition stays the one function, whose own docstring says it is for every file, native or WASM ([source] `D1M/tool/read_marker.py:11-20`). Its sha256 is bound in every report.
  - `read_marker.py` is not edited: it is committed evidence.
- **Marker rules** reused from `read_marker.py:193-197` [source]: exactly one `Z` in the saved document, all parts counted. The fixtures contain no `Z` (re-checked per run).
- **Red cases, all red before the first D1 run:**
  1. **Cross-container equality.** For every fixture (including `header-footer`) and every native saved document `D1M/out/*/r*.fodt.gz`, `adapter(repack(x)) == paragraphs(x)`. Made red with the adapter mutated three ways: master part dropped (red on header-footer only, §2.5); index continued across parts; only `content.xml` read.
  2. **Marker shift.** A saved ODT whose `Z` is moved one character (`ZAlpha` becomes `AZlpha` in `content.xml`). The arm's landing must read FAIL (the same mutation as `D1M`'s own red demo, [observed] `D1M/README.md:186-190`).
  3. **Duplicate marker.** A second `Z` in another paragraph must read FAIL ("2 markers").
  4. **Missing XML.** No `content.xml`, then no `styles.xml`, then a `content.xml` cut short. Each must read FAIL, with the parser's own message in the payload, not "0 markers" and not NOT_ESTABLISHED. No captured bytes at all (the save never came) is a different case: NOT_ESTABLISHED, because nothing was measured.

### 2.8 Engine reads

- The engine's state is asked with `editorGetStateV2` through the ask channel ([source] `V20R:474-491`).
- `selectionType` and `selectionText` are the fresh read. `selection.*` is the callback cache ([observed] `V20S` §8 item 2). A clause that needs "no selection now" reads `selectionType == "none"`.
- The saved document is the product's own save (§2.6 `S`), read with the adapter (§2.7) and, for list and indent shape, `N142/tool/read_results.py para_shapes` ([source] `:59-83`). That function reads the automatic styles and the body from the same root, so it works on `content.xml` directly [inferred].

### 2.9 Pre-run protocol, per browser run

- `V20R pre_run_checks` ([source] `V20R:328-342`): KWallet must not be `b true`; record `pgrep -c chrome`; nothing of ours running.
- Also record `/proc/loadavg` and the five processes using the most CPU. A process that is not ours was using a full core when the handoff was written ([observed] handoff 10-16b, "For the owner" 2).
- The timing-bound arms (D7, D9, D10's freshness clause) start only if the 1-minute load is under 1.5 and no process that is not ours uses more than 50 % CPU. Otherwise those arms are NOT_ESTABLISHED for that run. DECISION D-18.
- Chrome first, then Firefox, never in parallel with another runner of ours (fixed by the brief).

## 3. The arms

### D1: the marker lands where Writer's does (38 arms)

- **Criterion (§11.1, verbatim):** 「`d1-marker/tool/d1_population.py` 產生的 38 臂：產品頁送同一串步驟，用產品的打字路徑打 `Z`，存成 ODT。`read_marker.py`（加上 ODT 轉接，先做跨容器相等、標記位移、重複標記、缺 XML 四個紅案）讀到的落點等於原生」. Form: 「工具封閉」. Default if not done or red: 「第 1 項不出貨」.
- **Where:** (a), WASM, Chrome and Firefox, N=3 each, pass = 3/3 per arm per browser.
- **Population (generated, not listed here):** `d1_population.classify(arms.json)` at run time. Today it gives 38 IN, 43 OUT ([observed] re-run, §0).
  - The judge recomputes it and refuses a report whose arm list or `d1Script`s differ (as `read_marker.py:129-145` does natively [source]).
  - `hf-home-hdr-click` stays OUT (§9.14; DECISION D-3).
- **Fixtures:** the six the population uses, plain3, table-mid, table-first, table-last, section-mid and indent [observed] `D1M/out/population.txt`, converted per §2.5. The source `.fodt` hashes are in §0; the `.odt` hashes are fixed with the converter.
- **Reference:** `D1M/out/<arm>/r{1,2,3}.fodt.gz` (sums in `D1M/SHA256SUMS`). The field compared is the unique `Z`'s (part, index, paragraph text with the marker, offset), recomputed by the judge with `read_marker.paragraphs`. The judge requires the three native rounds to agree, as they do ([observed] `D1M/out/reader-output.txt`).
- **Steps:** the start state (§2.4), then the arm's D1 script, mapped per §2.6. One fresh open per arm. A page reload only after a reopen, which no D1 arm should cause (the v20 precedent, [observed] `V20S` §5 item 2). Rounds are run-major, as natively ([observed] `D1M/README.md:223`).
  - **Positive controls**, run in the same way: `ctl-noctrl-a1-home-mid` and `ctl-noctrl-t-home-B2-n1`, the arm's script without its Ctrl presses (`noCtrlScript` in `population.json`). They show that typing lands where the caret is, and that the reader tells paragraphs and offsets apart. Without them `a3-home-after-load` would pass even if the key did nothing, because the caret already sits at the document start [inferred].
- **Read:**
  - The saved ODT through the adapter (§2.7).
  - Per arm, round and browser: (part, index, text, offset) equal to the native value.
  - Controls: their landing differs from their paired arm's in every round, and equals the native control's (`body 1, 5` and `body 5, 2`, [observed] `D1M/README.md:162-163`).
  - Recorded, not judged: the requests in order (op and action); the insert's op name; the rest of the document against the native saved document (§2.5 (iii)).
- **Judge red cases and non-vacuity:**
  - the four of §2.7;
  - one arm's landing one paragraph off: FAIL;
  - offset off by one: FAIL;
  - text differs at the same index: FAIL;
  - a control landing where its paired arm lands: the control fails, and D1 is NOT_ESTABLISHED (the instrument cannot tell positions apart);
  - a report with 37 arms, or a script different from the population's: refused, NOT_ESTABLISHED;
  - a `placement-mismatch` or `not-observed` round: that cell is NOT_ESTABLISHED;
  - zero arms judged: NOT_ESTABLISHED, never PASS;
  - a served page hash other than `3d511216…`: refused.
- **Prediction:** 38/38 equal in every round on both browsers. The values are those of `D1M/README.md:124-161` [observed], for example `a1-home-mid` at body 0, offset 0, «[Z]Alpha first paragraph»; `t-end-B2-n3` at body 10, offset 15; `tl-end-n*` at body 6, offset 0, in the empty paragraph Writer adds after the final table on import.
  - The WASM core is built from the same commit `671c848b` as the native install ([observed] spec §3.2 and `D1M/README.md:207`). The `r-*` arms reach the same landing through `moveFromPoint`, because Writer collapses to the same boundary either way ([observed] `N142/README.md` summary 8) [inferred].
- **Identity:** §1, plus the six `.odt` hashes, `arms.json`, `population.json`, `D1M/SHA256SUMS`, `read_marker.py`, `d1_population.py` and the adapter module.

### D2: `press-after-ctrl-home` on the host

- **Criterion (§11.1, verbatim):** 「`press-after-ctrl-home`（宿主）：Backspace 以 `verified-boundary-noop` 完成，revision 不變，存檔文字不變。0.2.24 上照舊是紅的」. Form: 「逐實例」. Default if not done or red: 「同上」 (= 「第 1 項不出貨」).
- **Where:** (b), host 0.2.25, after the v74 freeze, Chrome and Firefox, N=3. The red case runs on host 0.2.24, which is installed today ([observed] handoff 10-16b "State"); it has to run **before** 0.2.25 is installed.
  - **Why the no-host page cannot carry the criterion as written:** the criterion names the host. The host adds the embedding route, the host's `liteCoreHost` load/save/`watchUnsaved` ([source] `PAGE:59`, `:143-149`, `:3733-3746`), the save through Nextcloud, and the owner's scroll container. The no-host page has the same page bytes and engine, but none of those.
  - **Pre-freeze predictor (DECISION D-1, recommended):** the same probe in `--mode nohost --nohost-root <the v21 mirror of §2.1>` ([source] `P14N:478-497`, `:554-555`, `:585-591`). If it is red, the §11 default can be applied before the freeze instead of after it.
- **Fixture:** `--doc long60` = `create_long_document.build(60)`, which is not deterministic, so its sha256 is recorded per run (as v20 did, [observed] `V20S` §1).
  - The original red measurement used a copy of the owner's file (`e1d5658e…`, [observed] `findings/evidence/host-0.2.20-hand-test/firefox-owner16630-b/report-host-firefox-owner16630.json`). The local copy the probe reads (`OWNER_COPIES`, [source] `P14N:566`) no longer exists ([observed] `ls` 2026-10-16). DECISION D-16.
  - The 0.2.24 red run and the v21 run use the same document kind.
- **Steps:**
  - The probe's arm, unchanged ([source] `P14N:339-375`, `:395-424`): real click on the first line; six wheel scrolls of 1,500 down; real Ctrl+Home; settle 1.5 s; one real Backspace; settle 3 s.
  - New, in a wrapper that imports the probe and does not edit it: then save (host: real Ctrl+S, then WebDAV `GET` of the file; no-host: the save action with the bytes caught) and compare the saved paragraph texts with the uploaded document's.
  - Positive control in the same run: after that read, type `Z` and save again. The comparison must then say "differs", which shows the save-and-compare can see a change.
- **Read and pass:**
  - The Backspace's `editorActionV2` response ([source] `P14N:426-460` `summarize.editorResponses`): `ok`, `completion == "verified-boundary-noop"`, `changed == false`, `rev == beforeRev` with both present (the v20 review fix, [source] `V20R:796-797`).
  - The saved paragraph texts equal the uploaded document's.
  - **Mechanism ran:** a `move-document-start` request and its move-class response precede the Backspace (observer `rq`/`rs`), and the keydown reached the sink with `ctrlKey` true.
  - **0.2.24 red:** the same arm gives `verified-selection-delete`, `changed true`, revision 0→1, and no `move-document-*` request (the key is not bound on that page).
- **Judge red cases:**
  - the Backspace answered `verified-selection-delete` on v21: FAIL;
  - revision advanced: FAIL;
  - saved text differs: FAIL;
  - no Backspace response: NOT_ESTABLISHED;
  - no `move-document-start` request on v21: FAIL (the key did not reach the action);
  - the positive control's second save not different: NOT_ESTABLISHED (the comparison is blind);
  - the 0.2.24 run not red: the red case is missing, so D2 is NOT_ESTABLISHED;
  - zero rounds: NOT_ESTABLISHED.
- **Prediction:**
  - v21: noop, with `boundaryNoop.waitedMs` 2,252–2,255 (C's window as measured on v20, [observed] `V20S` §3, C1 row); revision 0→0; text unchanged.
  - 0.2.24: `verified-selection-delete`, revision 0→1, about 60 ms after the key (59.8 ms on the owner's copy, [observed] `HT:66`).
- **Identity:** §1 for the no-host predictor. On the host: the host version, the engine package hash, and the page and shell as the host serves them (`P14N ui.static_facts`, [source] `P14N:578`); the `long60` sha256; `P14N`'s sha256.

### D2′: Ctrl+Home and Backspace back-to-back, numbered second paragraph

- **Criterion (§11.1, verbatim):** 「真鍵連送 Ctrl+Home、Backspace，不等待，起點是 `b2b-home-bksp-at-num` 的 fixture：第二段的編號與文字都不變。只在名目時序下成立，照 `CLAUDE.md`「有行為而沒有東西守著」登錄」. Form: 「逐實例」. Default if not done or red: 「同上」 (= 「第 1 項不出貨」).
- **Where:** (a), WASM, Chrome and Firefox, N=3.
- **Fixture:** `numbered-second` (`1d863b41…`), converted.
  - Reference for the claim: the fixture's own shape, P1 `none`, P2 `list-item`, P3 `none`, with texts «Plain first», «Numbered second», «Plain third» ([observed] `N142/fixtures/numbered-second.fodt`; `para_shapes`).
  - Native comparison (not the expectation): `b2b-home-bksp-at-num` turned P2 into a `list-header` in threaded native LOK ([observed] `N142/README.md` results table; summary item 12).
- **Steps:**
  1. Start state (§2.4). `k1024`, a real ArrowDown, takes the caret to P2's text start (native `place-numsecond`: «|Numbered second», [observed] `N142/README.md`, placement checks). Wait for its response, then quiet.
  2. Without waiting, real Ctrl+Home then real Backspace. Chrome: consecutive `Input.dispatchKeyEvent` calls. Firefox: one action chain (Ctrl down, Home down, Home up, Ctrl up, Backspace down, Backspace up) with no pauses.
  3. Wait for both responses and quiet; save.
  - **Placement witness, once per round and per browser:** the same open and `k1024`, then `Z` and save. The marker must be at body 1, offset 0, which shows the placement is P2's start on WASM.
  - **Positive control, once per round and per browser:** the same open and `k1024`, then one real Backspace alone. The WASM counterpart of native `ctl-bksp-at-num`; it shows that a Backspace before the move is visible.
- **Read and pass:**
  - The saved document's `para_shapes` equal the fixture's and its texts equal the fixture's.
  - **Non-vacuity:**
    - the Backspace's keydown (observer page time) precedes the move's response; otherwise the round did not test back-to-back keys and is NOT_ESTABLISHED;
    - the placement witness reads body 1, offset 0;
    - the positive control changes P2's shape. If it does not, the reading cannot tell the cases apart, and D2′ is NOT_ESTABLISHED.
  - **Recorded, not a clause:** the move's completion kind and time; the Backspace's completion (§9.1 expected `verified-boundary-noop`; §11 dropped that clause; DECISION D-19); the gap between the two keydowns.
- **Judge red cases:**
  - P2 `list-header`: FAIL;
  - P1 and P2 merged (2 paragraphs): FAIL;
  - text differs: FAIL;
  - the Backspace keydown after the move's response: NOT_ESTABLISHED;
  - the control unchanged: NOT_ESTABLISHED;
  - zero rounds: NOT_ESTABLISHED.
- **Prediction:**
  - PASS 3/3 per browser. The page queues the delete behind the move in the session's serial queue, and the move completes only on a callback that comes after `GoToStartOfDoc` ran, or on the 250 ms readback ([source] `ENGINE:506`, `:5791-5794`) [inferred].
  - The move should complete with `documented-callback-*`: natively the first callback came 1.1–1.2 ms after the post ([observed] `N142/README.md`, `b2b-home-bksp-at-num` row). A readback completion in any round is the stall case (L-142-readback-overtaken) and is reported.
  - Control: P2 `list-item` → `list-header` (natively `Number On/Off`, [observed] `N142/README.md`, `ctl-bksp-at-num` row). On WASM it should come through the merge-key path as `verified-key-undo` [inferred].
- **Identity:** §1, plus the `numbered-second.odt` hash and `read_results.py`'s.

### D3: superseded by D7

- **Criterion (§11.1, verbatim):** 「由 D7 取代，保留為說明」. Form: 「—」. Default: 「—」.
- **Where:** no arm. The two positions D3 named (already at the start, already at the end) are among D7's silent presses (`a3-home-at-start`, `a3-end-at-end`, …; §3, D7) [observed] (the population computed for D7).

### D4: ranges go through `moveFromPoint`

- **Criterion (§11.1, verbatim):** 「`r-*` 臂（含反向）：頁面走 `moveFromPoint` 再移動，標記落點等於原生」. Form: 「工具封閉（`r-*`）」. Default if not done or red: 「頁面在範圍上攔下按鍵、提示「範圍上尚不支援」，**不讓它落到輸入框**」.
- **Where:** (a), from D1's runs; no separate run.
- **Population (generated):** the IN arms whose script has an `s<a>:<b>` step. Today that is `r-one-{home,end}`, `r-cross-{home,end}` and `r-bwd-{home,end}`, 6 arms ([observed] `D1M/out/population.txt`). An arm appended with a range step joins without an edit.
- **Fixture and reference:** D1's (plain3; `D1M/out/r-*/r*.fodt.gz`).
- **Steps:** D1's. The `s` step is the real drag (§2.6), verified by `selectionText`.
- **Read and pass, per arm, round and browser:**
  - D1's landing equals the native one;
  - after the Ctrl keydown, the request log shows one `editorPlaceCaretV2` (the click at the point, [source] `PAGE:3286-3288`; op name from `wsp/editor-shell-v2/paragraph-editor-client.js:195`), and then the `move-document-*` request;
  - no `EDITOR_FORMAT_GESTURE_UNSUPPORTED` in between;
  - before the key, the selection was a range (`selectionType` `text`), so the path was really exercised.
- **Judge red cases:**
  - a move sent with no `editorPlaceCaretV2` before it: FAIL;
  - a gesture refusal: FAIL;
  - landing differs: FAIL;
  - the pre-key selection not a range: NOT_ESTABLISHED for that cell;
  - zero `r-*` cells: NOT_ESTABLISHED.
- **Prediction:** 6/6 per browser. Landings: body 0, offset 0 for the `-home` arms; body 2, offset 23 for the `-end` arms ([observed] `D1M/README.md:149-154`). One place-caret per arm.
- **Identity:** D1's.

### D5: a profile without the action does not take the key

- **Criterion (§11.1, verbatim):** 「按鍵綁定表 ×（宣告缺席、扣住、只扣一個、宣告）的矩陣，用真的 v20 manifest：只有提供的動作才攔鍵；Shift 與 `isComposing` 一律不攔」. Form: 「工具封閉」. Default if not done or red: 「最終殼層不得與 v20 搭配」.
- **Where:** (c), partly.
  - `wsp/editor-shell-v2/tests/page-document-keys.test.mjs`:
    - `:121` (the "absent" state is the real v20 manifest, `50aade86…`);
    - `:127-139` (5 states × 4 bindings: taken and `preventDefault` exactly when offered);
    - `:141-151` (Shift, Alt and `isComposing` never taken);
    - `:153-159` (other keys);
    - `:248-254` (wiring: taken before `if (accel) return;`).
  - Red on part-S mutations K1, K2 and K5 ([observed] `findings/evidence/link-batch-v21/part-s-red/mutations.json`).
  - **What it does not cover, exactly:**
    - (i) The binding axis is listed by hand (`BINDINGS`, `:114-119`, [source]). It is not generated from the page's own `DOCUMENT_KEY_ACTIONS` ([source] `PAGE:3059`). A key appended to the table would enter no matrix, so the axis is a hand enumeration, not the 「工具封閉」 the criterion names.
    - (ii) The test runs sliced functions (`documentKeyAction`, `takeDocumentKey`, …, [source] `:85-94`), not the whole keydown handler with its other listeners. Only their order is checked, by string index (`:248-254`).
  - **Residual arm D5-gen (new node test, small):** build the matrix rows from the sliced `DOCUMENT_KEY_ACTIONS` × {`ctrlKey`, `metaKey`} × the five states. The test file already takes `PAGE_SOURCE` ([source] `:27`).
    - Red first: a scratch page whose `documentKeyAction` takes a fictional third key regardless of `offered`. The generated matrix must go red; today's hand list stays green.
  - **Residual arm D5-w (a), recommended in DECISION D-11:**
    - The final page repointed to the real `e2-editor-v20` profile with the same `repointed_page` ([source] `PP:445-470`), with real Ctrl+Home, Ctrl+End, Cmd+Home and Cmd+End, and Shift+Ctrl+Home on v21, N=3 per browser.
    - Nothing in the shell checks `abiVersion`, so the v74 shell can open a v20 profile ([source] `grep abiVersion` finds no hit in `CLIENT`, `SESSION` or `wsp/sdk/document-sdk.js`).
- **Fixture:** plain3 `.odt` (D5-w).
- **Steps (D5-w):** start state; caret mid-text (`k1024,k1027x5`); each chord once; wait 1 s.
- **Read and pass (D5-w):**
  - on v20: the bubble-phase `defaultPrevented` is false for every chord, and no `editorActionV2` for `move-document-*` is posted;
  - on v21, as the positive control in the same browser session: Ctrl+Home, Ctrl+End, Cmd+Home and Cmd+End are prevented and each posts its move; Shift+Ctrl+Home is not prevented and posts nothing.
- **Judge red cases (D5-w):**
  - a prevented chord on v20: FAIL;
  - a move request on v20: FAIL;
  - Shift+Ctrl+Home taken on v21: FAIL;
  - the v21 positive control not taken: NOT_ESTABLISHED;
  - zero chords observed (keys not reaching the sink): NOT_ESTABLISHED.
- **Prediction:** the unit tests stay green on the final bytes. D5-w: not prevented on v20, prevented on v21. On v20 the textarea moves its own caret, which is today's behaviour, by design ([source] `PAGE:3050-3058`).
- **Identity:** the test file hashes (§0); for D5-w, §1 with the page repointed to v20, whose served hash is recorded (not `3d511216…`).

### D6 (record): paste 64 KiB, then Ctrl+End, then a marker

- **Criterion (§11.1, verbatim):** 「**記錄**：貼 64 KiB → Ctrl+End → 打標記，不等待；記完成種類與落點」. Form: 「記錄」. Default if not done: 「未量，不做任何排序宣稱」.
- **Where:** (a), WASM, Chrome and Firefox, N=3. No pass condition.
  - It depends on item 2's entry: if item 2 does not ship, the dialog does not exist and D6 is not done.
- **Fixture:**
  - The document: plain3 `.odt` with the caret at the document start (DECISION D-14 (ii)). In the M-series empty template the caret after the paste already sits at the document end, so Ctrl+End could not show an order [inferred from "段首貼上→變成前面的新段落，原段落不動", spec §3.2].
  - The text: item 2's M6 64 KiB corpus, as `ARMS-item2.md` fixes it (generator and sha256 there). D6 uses the same bytes and records their sha256.
- **Steps:**
  1. Start state.
  2. The dialog as item 2's M6 arm enters it: a real click on 「貼上為 Markdown…」, the corpus into the dialog's textarea by item 2's instrument, a real click on 「插入」.
  3. The dialog is modal and closes only after the paste resolves ([source] `PAGE:2327-2333`, `:2358-2361`). The sink gets the focus back when it closes ([source] `PAGE:2343`). So real Ctrl+End is sent at the first moment a key can reach the document: when the observer sees the dialog close (DECISION D-14 (i)).
  4. Real `Z` immediately after, with no wait; then wait for quiet, and save.
- **Read (recorded):**
  - the paste's completion and time;
  - whether a checkpoint `save` request precedes the move (the document is dirty after the paste; [source] `SESSION:862-875`, `:1001-1006`);
  - the move's completion kind and time;
  - the marker's landing through the adapter, classified as "document end" (P3 «Charlie third paragraph» end), "paste end" (the start of «Alpha first paragraph», the original first paragraph after the pasted blocks), or other.
- **Judge:** no verdict. A missing or unreadable record is "未量". Red case for the classifier: a synthetic document with the marker at the paste end must be classified "paste end".
- **Prediction (not a claim):** "document end" in every round [inferred]: the session drains in order, the checkpoint save runs before the move, and the engine thread has finished the paste's callbacks by then. A readback completion with the marker at "paste end" would be the first observed instance of L-142-readback-overtaken.
  - Natively a 16.6 KB paste took 81–111 ms and a 262 KB paste 3.0–3.1 s with 40,268 `CORE_LOG` callbacks ([observed] spec §3.2, citing `findings/evidence/link-batch-v21/native/markdown-paste/`).
- **Identity:** §1, the plain3 `.odt` hash, and the corpus hash.

### D7: every Ctrl press completes as Writer's callbacks predict, and its reply is fresh

- **Criterion (§11.1, verbatim):** 「D1 母數的每一下：原生有游標回呼 → `documented-callback-*`；原生無聲 → `verified-move-readback`，< 500 ms；回覆裡的游標等於回覆後 **500±50 ms** 的單次 `editor-get-state`」. Form: 「工具封閉」. Default if not done or red: 「第 1 項不出貨」.
- **Where:** (a), from D1's runs (the same presses), Chrome and Firefox, N=3.
- **Population and classes, generated:**
  - Each Ctrl press of each IN arm, classified from the native raw press records `N142/out/<arm>/r{1,2,3}.jsonl`: "cursor" if its `callbacks` include `INVALIDATE_VISIBLE_CURSOR`, "silent" if `nCallbacks == 0`. The three rounds must agree.
  - Computed today: **64 presses per round, 50 cursor and 14 silent.** The silent ones are `a3-home-at-start`, `a3-home-after-load`, `a3-end-at-end`, `a3-home-twice` ch2, `a3-end-twice` ce2, `t-home-A1-n3` ch3, `tf-home-n2` ch2, `tf-home-n3` ch2 and ch3, `tl-end-n2` ce2, `tl-end-n3` ce2 and ce3, `sec-home-n3` ch3, `sec-end-n3` ce3. All three rounds agree [observed] (computed 2026-10-16 from those files).
  - A press in neither class (callbacks but none of them a cursor) makes the population tool red; there is none today.
- **Fixture and reference:** D1's; the native press records above.
- **Steps:** D1's. The +500 ms ask is the observer's (§2.2 (c)).
- **Read and pass, per press:**
  - "cursor" presses: `completion` starts with `documented-callback-`.
  - "silent" presses: `completion == "verified-move-readback"`, and request-to-response time on the page clock under 500 ms.
  - Every press: the `askPostedAt` minus the reply's time is in [450, 550] ms, and the reply's `state.caret` equals the ask's `caret` in all four fields.
  - A press whose ask fell outside the window, or was not answered, is NOT_ESTABLISHED (not FAIL).
- **Judge red cases:**
  - a cursor press answered `verified-move-readback`: FAIL;
  - a silent press answered `documented-callback-visible-cursor`: FAIL;
  - a silent press at 520 ms: FAIL;
  - reply caret ≠ ask caret in one field: FAIL;
  - an ask at +600 ms: NOT_ESTABLISHED;
  - a missing press: NOT_ESTABLISHED;
  - zero presses: NOT_ESTABLISHED;
  - a population tool fed a press with only `STATE_CHANGED`: exits red.
- **Prediction:**
  - 50 `documented-callback-*` and 14 `verified-move-readback` per round per browser.
  - Readbacks at about 255–320 ms page-side: the engine's deadline is 250 ms ([source] `ENGINE:506`); v20's C1 completions were answered 100 ms past their engine-side wait in the runner's clock ([observed] `V20S` §3, C1 row) [inferred].
  - Caret equal in all 64.
  - The risk is not the engine but the ±50 ms window on a busy page (timer jitter while painting); a miss reads NOT_ESTABLISHED and is re-run.
- **Identity:** D1's, plus the hashes of the native press records' folders (`N142/SHA256SUMS`).

### D8: the held deletes after a move (sequences a–e)

- **Criterion (§11.1, verbatim):** 「序列 a–e：(a) 開頭 Backspace → Ctrl+End → Backspace，結尾刪一字；(b) 開頭 Backspace → Ctrl+Home → 1 秒內 18 個無旗標的 Backspace，引擎收到的刪除 ≤ 2；(c) 開頭 Backspace → Ctrl+End → 兩下 Backspace，結尾刪兩字；(d) 開頭 Backspace → 點文件中間 → Backspace，刪在點擊處；(e) 文字中 Backspace、Backspace → Ctrl+End → Delete，前兩下刪在原處、Delete 在結尾是 no-op。(c)(d)(e) 先在 0.2.24 上做紅。141／144／145 的頁面測試全部重跑」. Form: 「逐實例」. Default if not done or red: 「頁面保留今天的扣住規則，具名 **L-142-held-after-move**」.
- **Where:** (a) for the five sequences: WASM, Chrome and Firefox, N=3. Plus (c) for two parts:
  - **What the committed tests cover:** `page-held-after-move.test.mjs:220-261` runs the page's own delete listener and helpers, sliced from the page, against the real `NarrowEditorV2Session`, but over a **fake engine** with modelled timings (66 ms delete, 2,250 ms window, 250 ms readback, [source] `:51-57`, `:65-133`). It is red on part-S mutations H1–H3 ([observed] `mutations.json`).
    - It does not cover real keys through the sink and the E1-C input adapter, the real engine's answers (`boundaryNoopStands` compares real caret rectangles, [source] `PAGE:2854-2864`), or real timing.
  - **「先在 0.2.24 上做紅」:** the committed node witness `findings/evidence/link-batch-v21/part-s-red/d8-on-head-page.txt` (0.2.24's page logic: (a), (c), (d) and (e) red, (b) green [observed]).
    - On WASM, 0.2.24's page does not bind Ctrl+End, so (c) and (e) would be red there for a reason other than the hold rule [inferred from `HT:90`]. DECISION D-9 recommends adding (d) on the `dist/` page and profile as the one WASM red.
  - **「141／144／145 的頁面測試全部重跑」:** the node page tests `page-held-deletes.test.mjs`, `page-held-depth.test.mjs` and `page-delete-and-sink.test.mjs` (they name 141, 144 and 145, [observed] `grep`). Re-run on the final shell bytes at freeze. They passed in the 561/561 run at `bc6534e0` ([observed] `findings/evidence/link-batch-v21/part-s-red/README.md`). DECISION D-10.
- **Fixture:** plain3 `.odt`. The document start is the load position, and «Bravo| second paragraph» is `k1024,k1027x5` (native `place-plain3-mid`, [observed] `N142/README.md`).
- **Steps:** start state; then real input at the node test's offsets on the runner's monotonic clock ([source] `page-held-after-move.test.mjs:220-251`), with no waiting in between:
  - (a) Backspace @0, Ctrl+End @100, Backspace @200.
  - (b) Backspace @0, Ctrl+Home @100, then 18 unflagged Backspaces @150 + 55·i. Each is a real keydown/keyup pair, `repeat` false, as `P14N burst_key` sends them.
  - (c) Backspace @0, Ctrl+End @100, Backspace @200, Backspace @300.
  - (d) Backspace @0, a real click @100 at the WASM caret point of «Bravo|», Backspace @200. The point is measured in the same run by a separate open with `k1024,k1027x5` and an ask, then a fresh open for the sequence.
  - (e) From «Bravo|»: Backspace @0, Backspace @20, Ctrl+End @40, Delete @60.
  - Then wait for quiet (at most 15 s) and save.
- **Read and pass:** the saved body paragraphs equal the expectation; the order and number of `editorActionV2` requests (observer) equal the expectation:
  - (a) P3 «Charlie third paragrap»; requests `delete-backward`, `move-document-end`, `delete-backward`.
  - (b) at most 2 `delete-*` requests; the text equals the fixture.
  - (c) P3 «Charlie third paragra».
  - (d) P2 «Brav second paragraph», and the click's `editorPlaceCaretV2` response caret equals the measured point. Otherwise `placement-mismatch`, NOT_ESTABLISHED.
  - (e) P2 «Bra second paragraph», P3 unchanged; requests `delete-backward`, `delete-backward`, `move-document-end`, `delete-forward`.
  - **Non-vacuity, per round:**
    - in (a)–(d) the first Backspace was answered `verified-boundary-noop` (the round started inside C's window);
    - every later key's keydown came before that first answer (otherwise the hold was not exercised);
    - in (b), 18 `beforeinput`s were seen.
    - Any of these missing: NOT_ESTABLISHED.
- **Judge red cases:**
  - (a) with the text unchanged: FAIL;
  - (b) with 3 deletes: FAIL;
  - (d) deleting at the start: FAIL;
  - (e) with the Delete answered as a real delete: FAIL;
  - a round whose first Backspace was not a noop: NOT_ESTABLISHED;
  - keys sent after the first answer: NOT_ESTABLISHED;
  - zero rounds: NOT_ESTABLISHED.
- **Prediction:** all five pass 3/3 per browser.
  - (b) reaches exactly 2 deletes: the Backspace after Ctrl+Home is not held, because the move changed the session's `enqueueCount` ([source] `PAGE:2875-2878`, `SESSION:1144`). The next 17 are held behind it and dropped by its noop ([source] `PAGE:2920-2933`).
  - Time to ready: about 2.3 s for (a) and (c), about 4.6 s for (b) (two windows) [inferred].
- **Identity:** §1, the plain3 `.odt` hash, and the node test files' hashes (§0).

### D9: holding Ctrl+Home / Ctrl+End

- **Criterion (§11.1, verbatim):** 「按住 Ctrl+Home、Ctrl+End 各 1 秒，帶旗標的重複與 30 ms 一下的無旗標按壓各一組：放開後 ≤ 500 ms 回到就緒（同鍵的移動尚未回答時，按下去就丟掉）」. Form: 「逐實例」. Default if not done or red: 「具名「按住時每個尚未回答的窗會排一個 250 ms 的移動」」.
- **Where:** (a), WASM, Chrome and Firefox, N=3.
  - The node tests `page-document-keys.test.mjs:171-224` cover the page logic against a fake 250 ms answer (part-S mutation K3 red, [observed] `mutations.json`). They do not cover real engine latency or real key delivery.
- **Fixture:** plain3 `.odt`. Ctrl+Home from «Bravo|» (`k1024,k1027x5`); Ctrl+End from the same place.
- **Steps:** 4 sub-arms, each a fresh open with the start state:
  - Home flagged, End flagged: one press, then a repeat every 30 ms from 500 ms, keyup at about 1,015 ms, Ctrl held throughout;
  - Home unflagged, End unflagged: release/press pairs every 30 ms for 1 s, every keydown `repeat` false.
  - Then wait 2 s.
- **Read and pass, from the observer's page-time logs:**
  - (1) The time from the last keyup to the first state that is `ready` with `pending 0` and no unanswered `move-document-*` is ≤ 500 ms. Already ready at the keyup counts as 0.
  - (2) No `move-document-*` request of a key is posted while another of the same key is unanswered.
  - Recorded: the number of moves per hold (§9.8's "exactly 1" for the flagged hold, superseded by §11's wording; DECISION D-19).
  - **Non-vacuity:**
    - flagged: at least one keydown with `repeat: true` and `ctrlKey: true` reached the sink;
    - unflagged: every keydown `repeat: false`;
    - in both: at least one move request was sent and answered.
- **Judge red cases:**
  - ready 600 ms after the keyup: FAIL;
  - two overlapping same-key moves: FAIL;
  - a flagged hold with zero `repeat: true` keydowns: NOT_ESTABLISHED;
  - no move request: NOT_ESTABLISHED;
  - zero sub-arms: NOT_ESTABLISHED.
- **Prediction:**
  - Flagged: 1 move per hold; the first reply comes within tens of ms, so ready is 0 ms after the keyup.
  - Unflagged: 1 real move, then boundary moves of about 250–300 ms each, so 4–5 moves per hold; ready ≤ 300 ms after the last keyup [inferred from the 250 ms readback, `ENGINE:506`].
- **Identity:** §1 and the plain3 `.odt` hash.

### D10: Ctrl+End in a 60-page document

- **Criterion (§11.1, verbatim):** 「60 頁 fixture 按 Ctrl+End：在回覆時讀一次、靜止 1 秒後再讀一次，兩次引擎游標都在可視區內、`#page-status` 都是最後一頁；外加 D7 的新鮮度條款」. Form: 「逐實例」. Default if not done or red: 「第 1 項不出貨」.
- **Where:** (a), WASM, Chrome and Firefox, N=3, at the v20 window of 1400×1000 ([observed] `V20S` §1, §3).
- **Fixture:** `create_long_document.build(60)`, sha256 per run (not deterministic, [observed] `V20S` §1).
  - Reference: the engine's own `pageRectangles` reply in the same run gives M = `parts` (= 60). Settled as v20's P1 did ([source] `V20R:562-569`), because at open the layout is lazy (1 part, then 60, [observed] `V20S` §4).
- **Steps:** start state; wait for the settled 60 rectangles; record `parts` at the press; real Ctrl+End; read 1; quiet 1 s (no state change and no editor-state push); read 2.
- **Read and pass:**
  - **Read 1** (DECISION D-8 (i)): the observer's frame read after the page shows the move done (§2.2 (d)). Engine caret = the reply's `state.caret`.
  - **Read 2:** an ask. Engine caret = its `caret`.
  - **At both reads:**
    - the caret's [y, y + height) lies inside the visible region in twips (`V20R region_of`, [source] `V20R:454-463`, from that read's geometry);
    - `#page-status` is not hidden;
    - its last page equals M = 60 (DECISION D-8 (ii));
    - the caret's y is inside page 60's rectangle (`V20R parse_rects`, [source] `V20R:422-432`).
  - Plus D7's freshness: the reply caret equals the +500 ms ask's.
- **Judge red cases:**
  - caret below the region at read 1: FAIL;
  - status reads 59 at read 2: FAIL;
  - status hidden: FAIL;
  - freshness mismatch: FAIL;
  - no rectangles reply or M ≠ `parts`: NOT_ESTABLISHED;
  - zero rounds: NOT_ESTABLISHED.
- **Prediction:** PASS, with `第 60 頁，共 60 頁` at both reads.
  - `followCaret` centres a caret that is out of view ([source] `PAGE:1080-1095`).
  - The last line is about 5,000–6,500 twips into page 60. The view is 9,744 (Chrome) or 8,524 (Firefox) twips tall ([observed] `V20S` §3, P1-60 row), so a centred view starts below page 60's top (y 1,010,482 = 284 + 59 × 17,122; page rectangle and pitch from [source] `P14N:129-133`) [inferred].
  - The move should complete with `documented-callback-*`.
- **Identity:** §1 and the `long60` sha256.

### D11: bookkeeping (view-only, clean and dirty, stale revision)

- **Criterion (§11.1, verbatim):** 「記帳：唯讀文件按 Ctrl+End，游標動、`dirty` 不變；乾淨與髒文件依 096／098 斷言；經 SDK 送過時的 `expectedRevision`，照移動處理」. Form: 「逐實例」. Default if not done or red: 「第 1 項不出貨」.
- **Where:** (a), WASM, Chrome and Firefox, N=3, in three sub-arms.
  - **D11a, view-only.** The no-host page opens a document view-only only through a host: `openDocument(…, {readOnly})` is reached with `readOnly: true` only from `HOST.load()` ([source] `PAGE:3733-3746`), while `#file` calls `openDocument(bytes, file.name)` ([source] `PAGE:3723-3725`).
    - Recommended (DECISION D-2): a harness `liteCoreHost` shim, written by the observer before the module is imported. The page reads `globalThis.liteCoreHost` once at import ([source] `PAGE:59`). The shim offers:
      - `load()`, which returns the fixture with `readOnly: true`;
      - `save()`, which counts calls;
      - `watchUnsaved(fn)`, which keeps the page's own `hasUnsavedWork` ([source] `PAGE:127-128`, `:143`).
    - The page bytes are unchanged; the served HTML's hash is recorded.
  - **D11b, clean and dirty:** the no-host page. `dirty` is read through the page's own `beforeunload` guard: a dispatched cancelable `beforeunload` event; `defaultPrevented` = `hasUnsavedWork()` ([source] `PAGE:127-134`, `:149`). DECISION D-12.
  - **D11c, stale revision through the SDK:** the SDK harness page of D12 (DECISION D-7).
- **Fixture:** plain3 `.odt`.
- **Steps and pass:**
  - **D11a:** the shim opens plain3 view-only. Start state. Real Ctrl+End.
    - Pass: the move completes with a move completion; the engine caret (ask) moves and equals the caret a D11b clean open reaches with Ctrl+End in the same browser session; `hasUnsavedWork()` is false before and after; no `save` request; the shim's `save()` is never called.
    - Positive control: the page really is view-only. `#s-doc` ends with 「（唯讀：只能檢視）」 ([source] `PAGE:3685`), and a real `Z` posts no `insertText` (the sink is read-only, [source] `PAGE:3687`).
  - **D11b clean:** open; real Ctrl+End, then Ctrl+Home.
    - Pass: `dirty` is false after each; no `save` request; `#s-checkpoint` stays 「無」 ([source] `PAGE:977-979`). This is finding 098's assertion: moves are not mutations ([source] `SESSION:1061`).
  - **D11b dirty:** open; real `Z` at the start (revision 1, `dirty` true); real Ctrl+End; then Ctrl+Home.
    - Pass: exactly one `save` request before the first move's request, and `#s-checkpoint` becomes 「有（r1）」. This is finding 096 half C ([source] `SESSION:862-875`, `:1001-1006`).
    - No `save` before the second move: the content stamp is unchanged, so it is skipped ([source] `SESSION:868-871`).
    - `dirty` stays true. It is also the positive control that the `dirty` read can say true.
  - **D11c:** in the harness:
    1. open plain3; wait until observed;
    2. `insertText("Z")` (revision 1);
    3. `editor.action("move-document-end", {expectedRevision: 0})`;
    4. the control `editor.action("move-line-home", {expectedRevision: 0})`;
    5. the mutating control `editor.action("insert-paragraph-break", {expectedRevision: 0})`.
    - Pass (DECISION D-13): the two moves come out the same at both layers.
      - Engine (raw worker log): `ok`, a move completion, `revision == 1`, and an ask afterwards shows the caret moved.
      - SDK: the same outcome for both. By source it is `EDITOR_RESULT_INVALID`, because the client requires `beforeRevision === expectedRevision` ([source] `CLIENT:344-347`) and the engine reports its own revision as `beforeRevision` ([source] `ENGINE:5756-5760`, serialised at `:2253`).
    - The mutating control gets `STALE_REVISION` ([source] `ENGINE:2432-2443`, `:2519-2524`), which shows the revision was stale and the guard was live.
    - What this guards: before v21, `editorActionMutates` would have put ids 24 and 25 behind the guard ([source] `ENGINE:4499-4509`).
- **Judge red cases:**
  - D11a: a `save` request, or `hasUnsavedWork` true: FAIL.
  - D11a: the caret did not move: FAIL.
  - D11a: the page not view-only: NOT_ESTABLISHED.
  - D11b clean: a `save` request: FAIL.
  - D11b dirty: no checkpoint `save`, or a second one: FAIL.
  - D11b dirty: `dirty` read false after typing: NOT_ESTABLISHED (the read is blind).
  - D11c: `STALE_REVISION` for `move-document-end`: FAIL.
  - D11c: the two moves' outcomes differ: FAIL.
  - D11c: the mutating control not `STALE_REVISION`: NOT_ESTABLISHED.
  - Zero rounds of any sub-arm: NOT_ESTABLISHED.
- **Prediction:** all pass. D11c gives `EDITOR_RESULT_INVALID` at the SDK for both moves, `STALE_REVISION` for the break, and the caret at the document end after the first move [inferred].
- **Identity:** §1; for D11a also the shim's and the served HTML's hashes; for D11c the harness page's and module hashes (§3, D12).

### D12: the SDK on a range, and the worker's mask check

- **Criterion (§11.1, verbatim):** 「SDK 在範圍上送 22／23 → `EDITOR_FORMAT_GESTURE_UNSUPPORTED`、文件不變。worker 在遮罩回傳非 OK 時初始化失敗（單元測試，注入非 OK）」. Form: 「逐實例」. Default if not done or red: 「第 1 項不出貨」.
- **Where:**
  - **Second half: (c), fully covered.** `wsp/sdk/tests/sdk-worker-v21.test.mjs:151-164` (a mask refused for id 22 fails init with `INCOMPATIBLE_ABI` and `oxsdk_engine_start` is never called) and `:166-177` (statuses 7 and 3 also fail). Both use the real worker source, whose bytes equal the profile's worker (§0). Red on part-S mutation W1 ([observed] `mutations.json`). The control `:140-149` (23 masks pushed, the engine started) is green.
    - Every v21 boot in the D runs is the live positive: init succeeded, so all 23 masks answered OK ([source] `WORKER:1295-1305`).
  - **First half: (a)**, WASM, Chrome and Firefox, N=3, through the SDK harness (DECISION D-7). "The page's SDK object" is module-scoped: the page imports `createDocumentEngine` and keeps the session in a module variable ([source] `PAGE:29`, `:3574-3579`, `:3610-3627`), and it deliberately publishes no handle ([source] `PP:789-792`, a comment stating the convention). It cannot be reached without changing the page's bytes, which would void the identity.
    - The harness: an HTML and a module written into the mirror only (not `web/`). The module imports the served `sdk/document-sdk.js` and `editor-shell-v2/narrow-editor-v2-client.js`, creates the engine exactly as the page's `engineFactory` does (`workerUrl` the v21 profile's worker, `timeoutMs` 30000), opens the fixture, and wraps `Worker` with the same observer.
- **Fixture:** plain3 `.odt`.
- **Steps:**
  1. Open; wait until observed. Record caret points by moves, as the `r` step does (`p2a` after `k1024,k1027x6`, `p2b` after 6 more Right, `p3b` after `k1024,k1028,k1027x7`).
  2. `editor.selectRange(p2a, p2b)`; ask.
  3. `editor.action("move-document-start")`; ask; `editor.action("move-document-end")`; ask.
  4. The same on `selectRange(p2a, p3b)`.
  5. Control on the range: `move-line-end`, also collapsed-only. Then `placeCaret` at p2a and `move-document-start` on the caret, which must complete.
  6. Save.
- **Read and pass:**
  - Each call on a range rejects with `EDITOR_FORMAT_GESTURE_UNSUPPORTED` ([source] `ENGINE:5562-5578`).
  - The ask after it shows the same `selectionType` `text`, the same `selectionText` and the same revision as before the call.
  - The saved body paragraphs equal the fixture's.
  - **Non-vacuity:** the pre-call ask shows a range (`selectionText` `'second'` or `'second paragraph\nCharlie'`), and the collapsed control completes (the call path reaches the engine).
- **Judge red cases:**
  - a 22 or 23 call on a range that completes: FAIL;
  - a selection changed by the refused call: FAIL;
  - text changed: FAIL;
  - the pre-call selection collapsed: NOT_ESTABLISHED;
  - the collapsed control refused: NOT_ESTABLISHED;
  - zero calls: NOT_ESTABLISHED.
- **Prediction:** all four range calls are refused; the collapsed control completes with `documented-callback-*`.
- **Identity:** §1, plus the harness HTML's and module's hashes, and the plain3 `.odt` hash.

### D13: the closed lists

- **Criterion (§11.1, verbatim):** 「封閉清單：每個 ABI 5 追加的動作恰好屬於一個後置條件類別；`BOUNDARY_CAPABLE_MOVES` 等於移動完成類別；未知動作被拒絕」. Form: 「形式二」. Default if not done or red: 「第 1 項不出貨」.
- **Where:** (c), fully covered. `wsp/editor-shell-v2/tests/closed-lists.test.mjs`:
  - `:59-71` and `:73-75`: every action in `EDITOR_V4_ACTIONS` has a class, and the two ABI 5 actions are "move". The membership is read from the runtime's own lists.
  - `:77-81`: `BOUNDARY_CAPABLE_MOVES`, parsed from the session's source literal, equals the "move" class over the client's list.
  - `:83-90`: `actionMutates` agrees, action by action.
  - `:92-114`: an action in no class is refused, by `_validateInherited` and before any request or enqueue.
  - Red on part-S mutations C1, C2 and C3 ([observed] `mutations.json`).
  - The client's list is tied to the worker's wire ids and the header's by `declaration-drift.test.mjs:160-205` [source]. So an engine append that the client did not learn turns that test red.
  - Nothing is left.
- **Fixture, steps:** none (unit test).
- **Read and pass:** the test file passes on the final shell bytes, run at freeze time, with its sha256 recorded.
- **Judge red cases:** already shown by C1–C3. Non-vacuity: `EDITOR_V4_ACTIONS.length >= 22` is asserted in the test ([source] `:60`).
- **Prediction:** green (it was in the 561/561 run, [observed] `findings/evidence/link-batch-v21/part-s-red/README.md`).
- **Identity:** the test file's hash and the shell files' hashes at freeze.

### R-xlc (record): Backspace after Ctrl+Home on a numbered, bulleted or indented first paragraph

- **Criterion (§11.1, verbatim):** 「**記錄**：x-lc（Ctrl+Home 之後在有編號、項目符號、縮排的第一段按 Backspace）；表格裡 Ctrl+Home 再 Backspace（136 的儲存格邊界）」. Form: 「記錄」. Default if not done: 「列進發佈說明」.
- **Where:** (a), WASM, Chrome and Firefox, N=3, with no pass condition.
  - Population, generated: the arms of group `x-lc` in `N142/out/arms.json`: `x-bullet-home-bksp`, `x-numbered-home-bksp`, `x-indent-home-bksp` [observed].
- **Fixtures:** bullet (`1475af1d…`), numbered-first (`0960ed90…`), indent (`55ca3db2…`), converted.
  - Native reference: `N142/out/<arm>/r*.fodt.gz`, `para_shapes` and Undo top. Natively P1 goes `list-item → list-header` (`Number On/Off`) for bullet and numbered, and the indent goes 1 cm → 0 in (`Apply attributes`) ([observed] `N142/README.md` results table).
- **Steps:** start state; the arm's placement steps (`k1024,k1028,k1027x2` or `…x3`); real Ctrl+Home (wait for the response and quiet); real Backspace; wait for its response and quiet; save.
- **Recorded:** the Ctrl+Home's completion; the Backspace's completion, `waitedMs`, revision before and after, and generation; the saved `para_shapes` and texts against the fixture's and against native's; toasts.
- **Prediction (not a claim):** `verified-boundary-noop` with `waitedMs` about 2,253, the document unchanged. Writer itself would have changed the list or the indent. This matches the v20 indent record ([observed] `V20S` §3, "C1 recorded, not judged"). It is L-C-number-or-indent, now one key away.
- **Identity:** §1 and the three `.odt` hashes.

### R-table (record): Ctrl+Home to a cell start, then Backspace

- **Criterion:** the second half of the record row quoted under R-xlc (form 「記錄」, default 「列進發佈說明」).
- **Where:** (a), WASM, Chrome and Firefox, N=3, with no pass condition.
- **Fixture:** table-mid (`92989645…`), converted. Native reference for the first step: `t-home-B2-n1`, where Ctrl+Home lands at «|B2 text», body 5 offset 0 ([observed] `D1M/README.md:132`). There is no native Backspace arm here.
- **Steps:** start state; `k1024x2,k1029,k1027x3` (to «B2| text», the native placement); real Ctrl+Home; wait; real Backspace; wait for the response and for any reopen (`MWS toast_window`, [source] `MWS:743-760`); quiet 3 s; save.
- **Recorded:** the Backspace's outcome (completion, or refusal code and `mergeKey.stage`); generation before and after; the reopen toasts; the caret after the reopen against the caret before the key (finding 136's fix); the saved text against the fixture.
- **Prediction (not a claim):** refused with `EDITOR_BOUNDARY_UNSUPPORTED` at the cell boundary and reopened (generation 2), with the caret put back at B2's start and the document unchanged [inferred from finding 136's mechanism, `findings/136-after-a-refused-delete-at-a-cell-end-the-caret-comes-back-in-the-next-cell.md`].
- **Identity:** §1 and the `table-mid.odt` hash.

## 4. Summary table

| criterion | where | N | default if not done or red (verbatim) |
|---|---|---|---|
| D1 | (a) WASM | 38 arms × 3 × 2 browsers, plus 2 controls × 3 × 2 | 第 1 項不出貨 |
| D2 | (b) host 0.2.25 after the freeze; red case on host 0.2.24 before 0.2.25 is installed; (a) no-host predictor (D-1) | 3 × 2 (each) | 同上 |
| D2′ | (a) WASM | 3 × 2, plus the witness and the control 3 × 2 each | 同上 |
| D3 | none (superseded by D7) | — | — |
| D4 | (a), from D1's runs | 6 arms × 3 × 2 | 頁面在範圍上攔下按鍵、提示「範圍上尚不支援」，**不讓它落到輸入框** |
| D5 | (c) `page-document-keys.test.mjs` (partial); residual D5-gen (new node test), D5-w (a) (D-11) | unit; D5-w 3 × 2 | 最終殼層不得與 v20 搭配 |
| D6 | (a) WASM, record | 3 × 2 | 未量，不做任何排序宣稱 |
| D7 | (a), from D1's runs | 64 presses × 3 × 2 | 第 1 項不出貨 |
| D8 | (a) WASM; (c) node witness for 0.2.24 and the 141/144/145 page tests | 5 sequences × 3 × 2 | 頁面保留今天的扣住規則，具名 **L-142-held-after-move** |
| D9 | (a) WASM | 4 sub-arms × 3 × 2 | 具名「按住時每個尚未回答的窗會排一個 250 ms 的移動」 |
| D10 | (a) WASM | 3 × 2 | 第 1 項不出貨 |
| D11 | (a) WASM: a view-only (shim), b clean/dirty, c SDK harness | 3 sub-arms × 3 × 2 | 第 1 項不出貨 |
| D12 | (a) SDK harness for the first half; (c) `sdk-worker-v21.test.mjs:151`, `:166` for the second | 4 range calls × 3 × 2; unit | 第 1 項不出貨 |
| D13 | (c) `closed-lists.test.mjs`, fully | unit | 第 1 項不出貨 |
| R-xlc | (a) WASM, record | 3 arms × 3 × 2 | 列進發佈說明 |
| R-table | (a) WASM, record | 3 × 2 | 列進發佈說明 |

## 5. DECISIONS

Each needs the main session's choice before phase B. My recommendation is marked.

- **D-1. D2 is marked 「宿主」.**
  - A: host only, after the v74 freeze and the 0.2.25 install. If D2 is red, the §11 default (no binding) means another shell generation and another host version [inferred].
  - **B (recommended):** the same probe on the no-host v21 mirror before the freeze as a predictor, and the host run after the freeze as the pinned criterion. `P14N` already has `--mode nohost --nohost-root` ([source] `P14N:478-497`, `:554-555`, `:585-591`).
  - C: no-host only, which needs a §12 append because §11 names the host.
  - Order constraint either way: the 0.2.24 red case on the host must run before 0.2.25 is installed (handoff Next 4).
- **D-2. D11's view-only document on the no-host page.**
  - **A (recommended):** a harness `liteCoreHost` shim, set before the module is imported. It returns `readOnly: true`, which is the only way the page reaches `openDocument(…, {readOnly: true})` ([source] `PAGE:59`, `:3733-3746`). The page bytes are unchanged.
  - B: host 0.2.25 with a real read-only share, after the freeze.
  - C: both.
- **D-3. `hf-home-hdr-click` and D1.** Already settled by spec §9.14 (option A of `D1M/README.md:76`: it stays OUT), and §11 D1 says 38 arms. Recorded for completeness. B, a new product-reachable header arm, needs a new step kind and a native run first ([observed] `D1M/README.md:77`).
- **D-4. How the `.fodt` fixtures reach the page.**
  - A: `soffice --headless --convert-to odt`, the f129 precedent ([source] `wsp/tools/run_probe_129_m4.sh:5-6`). Writer rewrites the document on import: `table-last` gains the explicit empty paragraph after the table (native: 6 → 7 paragraphs, [observed] `D1M/README.md:144`), so the conversion check "paragraphs equal" would be red by construction for that fixture [inferred]. The bytes would also carry the conversion's timestamps, so they are not reproducible from the source alone [inferred].
  - **B (recommended):** the deterministic repackager of §2.5, with proofs (i)–(iii).
  - C: give the `.fodt` bytes to `#file` unchanged. Not the product's format: the page offers `.odt` ([source] `wsp/web/e2-editor.html:284`) and the flat format goes through another import filter.
- **D-5. Keyboard focus before the first key.**
  - **A (recommended):** evaluate `#sink.focus({preventScroll: true})`, the page's own call ([source] `PAGE:2508-2512`). No engine call, and the caret stays at the load position, as natively [inferred].
  - B: a real click at the document start. It sends `placeCaret`, so `a3-home-after-load` stops being "after load".
  - C: a real `mousedown` on a toolbar button released elsewhere. Contrived.
- **D-6. Waiting for `selection.observed` before the first step.**
  - **A (recommended):** wait for it (at most 10 s, delay recorded). The native probe waited 1.5 s of quiet after load ([observed] `N142/README.md`).
  - B: press as soon as the page is ready, and let the gesture gate's refusal ([source] `ENGINE:5552-5558`) read as a D1 or D7 failure. That gate is pre-existing and applies to every move, not only to item 1.
- **D-7. How a runner reaches "the SDK" (D11c, D12).** The page's SDK and session are module-scoped ([source] `PAGE:29`, `:3574-3579`).
  - **A (recommended):** a harness page and module in the mirror only, importing the served SDK and client bytes, with its own engine on the same profile.
  - B: the observer's raw worker channel on the product page ([source] `V20R:132-143`). That is direct-to-worker, not the SDK, and it skips the client's validation, which D11c needs.
  - C: patch the page to expose its session. That changes the page's sha256 and voids every identity.
- **D-8. D10's readings.**
  - (i) "在回覆時讀一次":
    - A: at the worker reply. The observer sees it before the page has applied it [inferred: its listener is added inside the `Worker` wrapper, before the SDK's own], and `followCaret` runs on the state update ([source] `PAGE:1034`, `:1080-1095`), so this reading is red by construction [inferred].
    - **B (recommended):** one animation frame after `#s-latency` shows the move done ([source] `PAGE:2103`). The page status is updated from the scroll event ([source] `PAGE:1317-1318`), and scroll events are dispatched before animation-frame callbacks in the same frame, so it has run by then [inferred].
    - C: a fixed +100 ms.
  - (ii) "都是最後一頁":
    - A: the text exactly `第 60 頁，共 60 頁`.
    - **B (recommended):** the status's last page equals M = 60, so a span ending at 60 passes. "Shows the last page" is literally true of a span. The exact text is recorded.
- **D-9. D8's 「(c)(d)(e) 先在 0.2.24 上做紅」 on WASM.**
  - A: the committed node witness only (`part-s-red/d8-on-head-page.txt`).
  - **B (recommended):** the node witness plus (d) on the `dist/` page and v20 profile (0.2.24), the one sequence whose red there comes from the hold rule: (d) uses no Ctrl key [inferred].
  - C: (c), (d) and (e) on WASM 0.2.24. (c) and (e) would be red there because Ctrl+End is not bound ([observed] `HT:90`), not because of the hold.
- **D-10. 「141／144／145 的頁面測試」.**
  - **A (recommended):** the node page tests (`page-held-deletes`, `page-held-depth`, `page-delete-and-sink`), re-run on the final shell bytes.
  - B: also the no-host WASM N1 runs of findings 144 and 145 ([observed] `findings/144-*.md:34`, `findings/145-*.md:38`).
- **D-11. D5's residual.**
  - A: the generated-axis node test (D5-gen) only.
  - **B (recommended):** D5-gen plus D5-w, real keys on the final page repointed to the real v20 profile. Cheap, and it runs the whole keydown handler that the unit test slices [inferred].
- **D-12. Reading `dirty` in D11b.**
  - **A (recommended):** the no-host page; a dispatched cancelable `beforeunload` read through the page's own `guardLeave` ([source] `PAGE:130-134`, `:149`).
  - B: the D-2 shim's `watchUnsaved` for D11b too. It puts the page into host mode (autosave armed, [source] `PAGE:3374-3375`; the guard handed to the host, `:143`), a configuration the other D arms do not use.
- **D-13. D11's 「照移動處理」.**
  - **A (recommended):** the same outcome as a `move-line-*` control at both layers (raw engine reply, SDK result), plus a mutating control that gets `STALE_REVISION`. Through the SDK, every move with a stale revision is rejected by the client after the engine moved ([source] `CLIENT:344-347`), so "as a move" can only be read as "the same as the other moves".
  - B: the engine level only (not `STALE_REVISION`, dispatched).
- **D-14. D6.**
  - (i) 「不等待」: the Markdown dialog is modal and closes only after the paste resolves ([source] `PAGE:2358-2361`).
    - A: send Ctrl+End right after 「插入」. It lands in the modal dialog's textarea and the document never sees it [inferred from `showModal`, `PAGE:2332`].
    - **B (recommended):** send it the moment the dialog closes, the first moment a key can reach the document.
    - C: the SDK harness, which is not the product path.
  - (ii) The document:
    - A: item 2's pinned empty template, where the post-paste caret already is the document end, so the order cannot show [inferred].
    - **B (recommended):** plain3 with the caret at the start.
- **D-15. D7's +500±50 ms read.**
  - **A (recommended):** a page-side timer in the observer.
  - B: the runner schedules it. It drains every 100 ms ([source] `V20R:494-504`) and would miss the ±50 ms window.
- **D-16. D2's document.** The owner's copy that the probe reads is gone ([observed] `ls` of `P14N`'s `OWNER_COPIES` path).
  - **A (recommended):** `long60` for both the v21 and the 0.2.24 runs (sha256 per run).
  - B: fetch the owner's file 16630 again from the host, read-only. The owner's private document, again.
- **D-17. A drag that does not reproduce the native range (the `s` steps).**
  - **A (recommended):** `placement-mismatch`, the cell NOT_ESTABLISHED and re-run (v20's C1 rule, [source] `V20R:824-828`, `:890`).
  - B: FAIL for D1 and D4.
- **D-18. A busy desk.**
  - **A (recommended):** the timing-bound arms (D7, D9, D10's freshness) start only below a 1-minute load of 1.5 and with no foreign process above 50 % CPU, and are NOT_ESTABLISHED otherwise.
  - B: record the load only.
- **D-19. Clauses in §9 that §11 dropped.** §9.1 asks D2′'s Backspace to complete `verified-boundary-noop` ([observed] spec line 175), and §9.8 asks D9 for "exactly 1 move" ([observed] spec line 228). §11's wording has neither ([observed] spec lines 354, 361).
  - **A (recommended):** judge §11's wording only (§11 governs, spec line 338) and record the §9 expectations.
  - B: add them as clauses, which needs a §12 append.

## 6. New instruments and fixtures for phase B (rough sizes)

- **Fixture converter** `fodt_to_odt.py` (§2.5, D-4 B), its proofs (i) and (ii), and the ten committed `.odt` files with a sums file: about 120 lines.
- **ODT adapter** for `read_marker.paragraphs`, with the four red cases of §2.7 as a self-test and a unit test: about 150 lines.
- **Item-1 runner** `run_v21_shakedown_item1.py`, with arms `d1` (which yields D4 and D7), `d2p`, `d6`, `d8`, `d9`, `d10`, `d11a`, `d11b`, `d5w`, `xlc` and `table`. It builds on `V20R`, `MWS`, `PP` and `P14N` and serves the lagging shell files from the tree: about 1,400–1,800 lines.
- **Observer additions** (§2.2 (a)–(d)): about 150 lines of JavaScript.
- **Real-input helpers:** Ctrl and Cmd chords, a Ctrl-held flagged hold, a Ctrl-held unflagged burst, a real drag: about 120 lines.
- **SDK harness** (HTML and module in the mirror only) and its driver arms `d12` and `d11c`: about 200 lines of JavaScript and 200 of Python.
- **`liteCoreHost` shim** for D11a: about 60 lines of JavaScript.
- **D2 wrapper** importing `P14N` (unchanged), adding the save, the compare and the positive control, for host, no-host and 0.2.24: about 150 lines.
- **D7 population tool** (the native press classes from `N142/out/*/r*.jsonl`) with its red case: about 60 lines.
- **Judge** `judge_v21_shakedown_item1.py` with `--self-test` (every red and non-vacuity case named above), plus a unittest file: about 900 lines. Lessons carried over: one report per (browser, arm), `--expect-page` mandatory, both revisions present before comparing them, `selectionType` rather than the cache ([observed] `V20S` §8).
- **D5-gen node test:** about 30 lines.
- **D6 classifier** (marker at the document end, at the paste end, or other): about 30 lines.
- **Inputs from elsewhere:** item 2's M6 corpus and dialog-entry instrument (`ARMS-item2.md`); `create_long_document.build(60)` (existing).

## 7. Found while reading (for the main session)

- §11 D6 says 「不等待」, but the dialog cannot pass a key to the document until the paste has completed ([source] `PAGE:2358-2361`). As written, the record cannot measure an order during the paste (D-14).
- §11 D10's 「在回覆時」 is earlier than the page's own update (D-8).
- Through the SDK, a move with a stale `expectedRevision` is always rejected by the client after the engine has moved the caret ([source] `CLIENT:344-347`). D11's 「照移動處理」 is only meaningful as "the same as the other moves" (D-13).
- §11.0 asks for N=3 in two browsers for every arm, while D12's second half says 「單元測試」 and D13 is a closed-list property: unit tests by nature. I treated those as (c).
- D2 names the host, and its default can only be applied after the freeze unless a no-host predictor runs first (D-1).
- `findings/evidence/link-batch-v21/part-s-red/README.md` says 31 mutations. `mutations.json` holds 29: the two `.d.ts` mutations T2 and T3 are defined in `run_mutations.py` but missing from the output [observed].
- `N142/SHA256SUMS` no longer verifies `README.md`, because of the appended correction [observed]. A reference digest should cover the data files, not the README.
- No D1 fixture has a header or footer paragraph, so the cross-container red case has to use `header-footer.fodt` from outside the population (§2.5).
- The order of the steps after the shakedown matters for D2's red case: host 0.2.24 must still be installed when it runs.

## 8. Rulings on §5 (main session, 2026-10-16, before any run)

The draft above is Agent D's, kept as written. These rulings decide its DECISIONS; where a ruling differs from the recommendation it says why. Phase B implements the rulings, not the recommendations.

| # | ruling | note |
|---|---|---|
| D-1 | **B** | No-host predictor before the freeze; the host run after the freeze is the criterion. The 0.2.24 host red case runs before 0.2.25 is installed (it needs ddev; the owner is asked first, handoff Next 4). |
| D-2 | **A** | The shim reaches the page's own `readOnly` code path. Registered: the host's read-only route (a real read-only share) is not what D11a measures; it is the user path and stays unmeasured in this round. |
| D-3 | **A** | Settled by §9.14. |
| D-4 | **B** | Addition: the converter must place **every** top-level child of `office:document` (meta, settings, scripts, font-face-decls, styles, automatic-styles, master-styles, body) and **refuse** a child it has no rule for, so a fixture with an unhandled part fails loudly instead of losing it. Proof (ii) covers every slice it copies, not only the three named. |
| D-5 | **A** | A harness step (the user clicks); recorded in each report as `focus: "sink.focus()"`. |
| D-6 | **A** | The delay from `ready` to the first observed selection is recorded per round. |
| D-7 | **Superseded (differs)** | Item 2's draft found that the page's own SDK object **can** be reached without changing the page's bytes: a module script placed before the page's module imports the same URLs, gets the same module instances, and captures the page's session through a pass-through prototype wrapper (`ARMS-item2.md` I-3, DM-1). Both items use that one instrument (`ARMS.md`, shared instrument S-3). D11c and D12 drive the page's own `DocumentHandle` and client through it; no separate harness page is built. This is closer to the criterion's wording ("the page's SDK"), and it removes a second engine from the page. |
| D-8 | **(i) B, (ii) B** | The exact status text is recorded at both reads. |
| D-9 | **B** | |
| D-10 | **A** | |
| D-11 | **B** | D5-gen satisfies the pinned 「工具封閉」 form that the hand-listed axis does not; it is not a new guard in §34's sense. |
| D-12 | **A** | |
| D-13 | **A** | Recorded as an observation for the owner, not a v21 finding: through the SDK a stale-revision move is reported as an error although the engine moved the caret; this is true of every move, not only 22/23. |
| D-14 | **(i) B, (ii) B** | |
| D-15 | **A** | |
| D-16 | **A** | The owner's private document is not fetched again. |
| D-17 | **A** | |
| D-18 | **A′ (differs)** | The 1-minute load is **recorded**, not gated on: D7 comes out of D1's own runs, and our own browser raises the load, so a load gate would void D7 by the runner's own activity. Gate instead on foreign load only: before each timing-bound arm (D7's presses are inside D1, so before each D1 arm; D9; D10), sample CPU over 2 s; if any process outside the runner's own process tree (the runner, its server, the browser and their children) uses more than 50 % of one core, that arm is NOT_ESTABLISHED for that run and the sample is kept in the report. |
| D-19 | **A** | §11 governs (spec line 338). |

§7's two evidence oddities are the main session's to handle, outside this file: the 29-versus-31 mutation count in `part-s-red/`, and `N142/SHA256SUMS` not verifying the appended README (the reference digest in phase B covers data files only).

## 9. Correction after ruling 3 (2026-10-17; append-only)

- **D2 "Where"** (`:189` stays as written): D2 runs on **host 0.2.26** (fable ruling 3, `review/ruling-fable-3.md`; spec §12.5). Host 0.2.25 displayed the closed Markdown dialog over the editor (finding 154), and D2 read NE 6/6 there. The 0.2.25 reports (`evidence/d2/d2-host-v21-*`) are finding 154's witness and are void as D2 evidence (§11.0).
- **`:607`** is D-1 option A's text; the ruling was B (`:713`). Its "another shell generation" does not apply: the fix is a host CSS rule, no JS changes, and v74 stays frozen.
- **The tool:** `HOST_EXPECT["v21"]["hostVersion"]` 0.2.25 → 0.2.26 and nothing else, with the before/after `--identity-only` outputs as witnesses. The criterion's text, `judge_d2` and the default are unchanged. D2 gets one re-run, under the stop rule in spec §12.5 (e).
