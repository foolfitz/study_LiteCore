# Finding 142, D1 native reference: where a typed marker lands after the arm's last Ctrl+Home / Ctrl+End

Criterion: `specs/SPEC-M3-link-batch-v21.md` §5 **D1**, with its population replaced by §9.5. D1 compares two positions per arm. One is where a marker lands on v21, typed after the product page sends the arm's keys and then saved. The other is where the same marker lands natively, after the same arm, also saved. This folder is the native side. §5 D1 requires it to run and be committed before v21 is implemented.

Parent run: `../README.md` (the 142 native arms). This folder reuses that run's arm table (`../out/arms.json`), its fixtures (`../fixtures/`) and its probe source, plus one added step. **Nothing in the parent folder was modified.**

Labels: **[observed]** means read off the raw files in `out/`, recomputable with `tool/read_marker.py`. **[source]** means read in a source tree at the cited line. **[inferred]** means my reasoning. Nothing here is observed on WASM.

## Summary

1. **Population: 38 arms IN, 43 OUT, out of 81.** `tool/d1_population.py` generates it mechanically from `../out/arms.json`. It reports no unknown step and exits 0. The full listing is in `out/population.txt`. [observed]
2. **All 38 IN arms ran 3 times each, plus 2 controls, for 120 processes, each its own process. Every process exited 0, and every arm and control agreed 3/3** on (part, paragraph index, paragraph text, marker offset). [observed]
3. **Every saved document has exactly one marker, and no fixture contains one.** For all 38 arms, the marker sits exactly where the **142 run's own locator** put the caret after the same last press, in every round of both runs. That is two independent processes and two different readers: Shift+End/Shift+Home in core, and the saved XML. [observed]
4. **The positive controls tell positions apart** (3/3 each):
   - `a1-home-mid` without its Ctrl+Home lands in a different paragraph (body 1, offset 5, not body 0, offset 0).
   - `t-home-B2-n1` without its Ctrl+Home lands in the same paragraph at a different offset (body 5, offset 2, not offset 0).
5. **The reader goes red** (exit 1) on broken copies of one saved file. With the marker moved one character, it reports three independent reasons. With the XML truncated, it reports a parse error. On the unbroken copy it exits 0 (`out/reader-red-demo.txt`). The population script goes red on an unknown step and on zero IN arms. A fictional new arm is classified without editing anything (`out/population-red-demo.txt`).
6. **The spec and its own rule disagree about one arm.** §9.5 says `hf-home-hdr-click` is **in** the population. Applied mechanically, its rule puts it **OUT**, because the arm's script contains `u.uno:JumpToHeader`. The arm uses that step to find the header point before the two clicks. So **no header or footer arm is in D1 as generated.** The rule was applied as written. See "The `hf-home-hdr-click` discrepancy" for options.

## The D1 population (spec §9.5, by script grammar)

The step grammar is the parser in `../tool/f142_native_ctrl_home_end.cpp`, plus `Q` from `../tool/f142_native_queued_pair.cpp`. Every step kind in it is classified explicitly, and any other kind makes `d1_population.py` exit 1.

| step | meaning | D1 class |
|---|---|---|
| `k<code>[x<n>]` | key, KEYINPUT+KEYUP | product step if code ∈ {1024 Down, 1025 Up, 1027 Right, 1028 Home, 1029 End}; any other code → OUT (`k-code`) |
| `r<name>` | record the current caret rectangle as a point | product step: it only feeds `s`/`c` |
| `s<a>:<b>` | range via the text-handles path (select-range) | product step |
| `c<name>` | click at a point (place-caret) | product step |
| `M<label>=<code>` | measured press | code ∈ {9220, 9221} → the Ctrl press; label `bksp` or code 1283 → OUT (`bksp`); label `del` or code 1286 → OUT (`del`); any other code → OUT (`M-code`) |
| `B…`, `Q…` | back-to-back pair, pair queued inside a callback | OUT (`B`, `Q`; also `bksp`/`del` when a pair contains one) |
| `K…`, `J…` | K1 barrier presses | OUT (`K`, `J`) |
| `u.…` | `postUnoCommand` | OUT (`u.`) |
| `L` | locator (instrument) | allowed after the last press; D1 moves it after the save |
| `S` | saveAs fodt (instrument) | allowed after the last press; D1 replaces it with its own save |

Two refinements are mine, and both are needed to apply "after the arm's last Ctrl+Home/End press":

- **`no-ctrl`**: an arm with no `M…=9220|9221` press is OUT, because it has nothing to land. §9.5 itself names `place-*` as not in, and they have no press. A Ctrl code inside a `B`/`Q` pair does not count.
- **Refusal (exit 1)** if an IN arm had a product step after its last Ctrl press, or an instrument step before it. None does.

**D1 script of an IN arm** = its 142 steps up to and including the last Ctrl press, then `T` (type the marker), `S` (save), `L` (locator). Example: `a1-home-mid` `k1024,k1027x5,Mch=9220,L` becomes `k1024,k1027x5,Mch=9220,T,S,L`.

**IN (38)**:

- `a1-home-mid`, `a2-end-mid`
- `a3-home-at-start`, `a3-home-after-load`, `a3-end-at-end`, `a3-home-twice`, `a3-end-twice`
- `t-{home,end}-{A1,B2}-n{1,2,3}` (12)
- `tf-home-n{1,2,3}`, `tl-end-n{1,2,3}`
- `r-one-{home,end}`, `r-cross-{home,end}`, `r-bwd-{home,end}`
- `sec-{home,end}-n{1,2,3}` (6)
- `x-indent-home`

**OUT (43)**, each with every rule that excludes it (verbatim in `out/population.txt`):

| rule(s) | arms |
|---|---|
| `u.` | `hf-home-hdr-n{1,2,3}`, `hf-end-ftr-n{1,2,3}`, `hf-home-hdr-click` |
| `bksp` + `M-code` | `red-home-bksp`, `x-bullet-home-bksp`, `x-numbered-home-bksp`, `x-indent-home-bksp` |
| `del` + `M-code` | `red-end-del` |
| `K` / `J` | `red-home-k1` / `red-end-k1r` |
| `B` + `bksp`/`del` + `no-ctrl` | `b2b-home-bksp`, `b2b-end-del`, `b2b-home-bksp-at-num` |
| `Q` + `bksp`/`del` + `no-ctrl` | `q-home-bksp`, `q-end-del`, `q-ctl-home-bksp`, `q-home-bksp-at-num` |
| `M-code` + `no-ctrl` | `ctl-home` (Mhome=1028), `ctl-down` (Mdown=1024) |
| `bksp` + `M-code` + `no-ctrl` | `ctl-bksp`, `ctl-bksp-at-num` |
| `K` / `J` + `no-ctrl` | `ctl-k1` / `ctl-k1r` |
| `no-ctrl` | `place-plain3-{mid,start,end}`, `place-table-{A1,B2}`, `place-tf-body`, `place-tl-body`, `place-sec-{one,two}`, `place-bullet`, `place-numbered`, `place-indent`, `place-numsecond` |
| `u.` + `no-ctrl` | `place-hdr`, `place-ftr`, `place-hdr-click` |

The result matches §9.5's prose in every respect but one. `sec-*` are in. `ctl-*`, `red-*-k1*`, `b2b-*`, `q-*` and `place-*` are out. `red-home-bksp` and `red-end-del` are out too, by the `bksp`/`del` rule. `x-indent-home`, which the prose does not mention, is in.

### The `hf-home-hdr-click` discrepancy

The arm's script is `k1024,k1027x5,rbody,u.uno:JumpToHeader,k1027x6,rhdr,cbody,chdr,Mch=9220,L`. Its caret reaches the header by the two clicks `cbody`, `chdr`, which are product steps. But the header point `rhdr` is found by `u.uno:JumpToHeader`, and the rule is per step. The spec sentence ("所以 `sec-*` 與 `hf-home-hdr-click` 在母數裡") does not follow from the rule it summarises. Options for whoever owns the spec:

- **A.** Keep the rule. D1 then has no header or footer arm, and the spec sentence gets an appended correction. The header case is registered as not covered by D1.
- **B.** Append a new arm to the 142 table that reaches the same header point by product steps only. The grammar has no literal-coordinate click, so this needs either a new step kind, which the population script must then classify, or a product-reachable way to record the point. The generator would put such an arm IN with no edit (shown by case 3 of `out/population-red-demo.txt`). Its native marker variant would then have to run before v21, like the rest.

## The marker, and how it is typed

- **The marker is a plain ASCII `Z`.** No fixture contains a `Z` anywhere: not in the text, not in the markup (`grep -c Z ../fixtures/*.fodt` is 0 for all ten). The reader re-checks this on every run. It is a single code point, so the offset is the same in code points and in UTF-16, and nothing invisible has to survive the save. U+2063+`Z` was not used. Its survival through the fodt export would be a second question, and it would shift every offset by one.
- **How it is typed.** `T` calls `paste(doc, "text/plain;charset=utf-8", "Z", 1)`. That is the first call of the engine's insert-text handler, `handleInsertText` (`wasm_sdk_probe/src/probe_engine.cpp:3234-3243`), which the SDK's `insertText` reaches through `sdk_api.cpp:120` → `probe_engine.cpp:6859-6867` [source].
  - The handler falls back to `postKeyEvent` only when `paste()` returns false. Here `paste()` returned true in all 120 processes [observed], so the fallback was never needed and is not imitated.
  - Before pasting, `T` waits for 1.5 s with no callbacks, as before a measured press. Each measured press also already ends with 2 s of quiet. Afterwards `T` waits for 600 ms of quiet.
  - The selection was empty right before the paste in every run [observed]. So each Ctrl press, including those on the `r-*` ranges, left a collapsed caret, and the paste replaced nothing.
  - Undo after the paste is `Paste clipboard` in every run [observed].
- **Not checked here:** that the product page's keyboard typing goes through the SDK's `insertText` for an ordinary character. The engine also has a raw key path (`probe::key`, `probe_engine.cpp:6869`).

## The reader and the paragraph order

`tool/read_marker.py` is the only reader, and it is meant for the v21 side too. It reads the saved flat ODT. **Order:**

- It takes every `text:p` and `text:h` element in XML document order (pre-order), in two parts, each indexed from 0.
- **`master`** is everything under `office:master-styles`: page headers and footers, in the order the file writes them.
- **`body`** is everything under `office:body`:
  - table cells row by row as the XML nests them (in `table-mid`: 0 `Before the table`, 1 `A1 text`, 2 `B1 text`, 3 `C1 text`, 4 `A2 text`, 5 `B2 text`, …, 9 `C3 text`, 10 `After the table`);
  - section and list contents in place.

**Paragraph text:**

- `text:s` becomes spaces (count `text:c`), `text:tab` becomes `\t`, and `text:line-break` becomes `\n`.
- Every other child element's text is included in place.

**Offset:** the code-point index of `Z` in that text.

The reader exits 1 (red) when any of the following holds:

- the population recomputed from `../out/arms.json` differs from `out/population.json`, or `out/runs.json` ran another script;
- a run is missing, has a fatal record, or lacks done/typed/saved;
- `paste()` returned false;
- a saved file is missing or does not parse;
- a fixture already contains a `Z`, or a saved document does not hold exactly one;
- the run's own locator, read after the save, does not split the marker paragraph right after the marker;
- the rounds disagree;
- the landing differs from the 142 run's locator for the same arm;
- a control lands where its paired arm lands.

## Results (verbatim from `out/reader-output.txt`)

`[Z]` shows the marker. "same as the 142 locator" compares the text before and after the marker with the 142 run's Shift+Home/Shift+End reading after the same last press, in all three of its rounds. "rest of the document" compares the saved paragraphs, with the marker removed, against the fixture.

| run | role | rounds agree | fixture | part | paragraph index | offset | paragraph text with the marker | same as the 142 locator | rest of the document vs the fixture | Undo top after the paste |
|---|---|---|---|---|---|---|---|---|---|---|
| a1-home-mid | D1 | 3/3 | plain3 | body | 0 | 0 | «[Z]Alpha first paragraph» | agrees | same | Paste clipboard |
| a2-end-mid | D1 | 3/3 | plain3 | body | 2 | 23 | «Charlie third paragraph[Z]» | agrees | same | Paste clipboard |
| a3-home-at-start | D1 | 3/3 | plain3 | body | 0 | 0 | «[Z]Alpha first paragraph» | agrees | same | Paste clipboard |
| a3-home-after-load | D1 | 3/3 | plain3 | body | 0 | 0 | «[Z]Alpha first paragraph» | agrees | same | Paste clipboard |
| a3-end-at-end | D1 | 3/3 | plain3 | body | 2 | 23 | «Charlie third paragraph[Z]» | agrees | same | Paste clipboard |
| a3-home-twice | D1 | 3/3 | plain3 | body | 0 | 0 | «[Z]Alpha first paragraph» | agrees | same | Paste clipboard |
| a3-end-twice | D1 | 3/3 | plain3 | body | 2 | 23 | «Charlie third paragraph[Z]» | agrees | same | Paste clipboard |
| t-home-A1-n1 | D1 | 3/3 | table-mid | body | 1 | 0 | «[Z]A1 text» | agrees | same | Paste clipboard |
| t-home-B2-n1 | D1 | 3/3 | table-mid | body | 5 | 0 | «[Z]B2 text» | agrees | same | Paste clipboard |
| t-end-A1-n1 | D1 | 3/3 | table-mid | body | 1 | 7 | «A1 text[Z]» | agrees | same | Paste clipboard |
| t-end-B2-n1 | D1 | 3/3 | table-mid | body | 5 | 7 | «B2 text[Z]» | agrees | same | Paste clipboard |
| t-home-A1-n2 | D1 | 3/3 | table-mid | body | 0 | 0 | «[Z]Before the table» | agrees | same | Paste clipboard |
| t-home-B2-n2 | D1 | 3/3 | table-mid | body | 1 | 0 | «[Z]A1 text» | agrees | same | Paste clipboard |
| t-end-A1-n2 | D1 | 3/3 | table-mid | body | 9 | 7 | «C3 text[Z]» | agrees | same | Paste clipboard |
| t-end-B2-n2 | D1 | 3/3 | table-mid | body | 9 | 7 | «C3 text[Z]» | agrees | same | Paste clipboard |
| t-home-A1-n3 | D1 | 3/3 | table-mid | body | 0 | 0 | «[Z]Before the table» | agrees | same | Paste clipboard |
| t-home-B2-n3 | D1 | 3/3 | table-mid | body | 0 | 0 | «[Z]Before the table» | agrees | same | Paste clipboard |
| t-end-A1-n3 | D1 | 3/3 | table-mid | body | 10 | 15 | «After the table[Z]» | agrees | same | Paste clipboard |
| t-end-B2-n3 | D1 | 3/3 | table-mid | body | 10 | 15 | «After the table[Z]» | agrees | same | Paste clipboard |
| tf-home-n1 | D1 | 3/3 | table-first | body | 0 | 0 | «[Z]A1 first» | agrees | same | Paste clipboard |
| tl-end-n1 | D1 | 3/3 | table-last | body | 6 | 0 | «[Z]» | agrees | paragraph '' added after 'B2 last' (6 -> 7 paragraphs) | Paste clipboard |
| tf-home-n2 | D1 | 3/3 | table-first | body | 0 | 0 | «[Z]A1 first» | agrees | same | Paste clipboard |
| tl-end-n2 | D1 | 3/3 | table-last | body | 6 | 0 | «[Z]» | agrees | paragraph '' added after 'B2 last' (6 -> 7 paragraphs) | Paste clipboard |
| tf-home-n3 | D1 | 3/3 | table-first | body | 0 | 0 | «[Z]A1 first» | agrees | same | Paste clipboard |
| tl-end-n3 | D1 | 3/3 | table-last | body | 6 | 0 | «[Z]» | agrees | paragraph '' added after 'B2 last' (6 -> 7 paragraphs) | Paste clipboard |
| r-one-home | D1 | 3/3 | plain3 | body | 0 | 0 | «[Z]Alpha first paragraph» | agrees | same | Paste clipboard |
| r-one-end | D1 | 3/3 | plain3 | body | 2 | 23 | «Charlie third paragraph[Z]» | agrees | same | Paste clipboard |
| r-cross-home | D1 | 3/3 | plain3 | body | 0 | 0 | «[Z]Alpha first paragraph» | agrees | same | Paste clipboard |
| r-cross-end | D1 | 3/3 | plain3 | body | 2 | 23 | «Charlie third paragraph[Z]» | agrees | same | Paste clipboard |
| r-bwd-home | D1 | 3/3 | plain3 | body | 0 | 0 | «[Z]Alpha first paragraph» | agrees | same | Paste clipboard |
| r-bwd-end | D1 | 3/3 | plain3 | body | 2 | 23 | «Charlie third paragraph[Z]» | agrees | same | Paste clipboard |
| sec-home-n1 | D1 | 3/3 | section-mid | body | 1 | 0 | «[Z]Inside section one» | agrees | same | Paste clipboard |
| sec-end-n1 | D1 | 3/3 | section-mid | body | 2 | 18 | «Inside section two[Z]» | agrees | same | Paste clipboard |
| sec-home-n2 | D1 | 3/3 | section-mid | body | 0 | 0 | «[Z]Before the section» | agrees | same | Paste clipboard |
| sec-end-n2 | D1 | 3/3 | section-mid | body | 3 | 17 | «After the section[Z]» | agrees | same | Paste clipboard |
| sec-home-n3 | D1 | 3/3 | section-mid | body | 0 | 0 | «[Z]Before the section» | agrees | same | Paste clipboard |
| sec-end-n3 | D1 | 3/3 | section-mid | body | 3 | 17 | «After the section[Z]» | agrees | same | Paste clipboard |
| x-indent-home | D1 | 3/3 | indent | body | 0 | 0 | «[Z]Indented first» | agrees | same | Paste clipboard |
| ctl-noctrl-a1-home-mid | control for a1-home-mid | 3/3 | plain3 | body | 1 | 5 | «Bravo[Z] second paragraph» | - | same | Paste clipboard |
| ctl-noctrl-t-home-B2-n1 | control for t-home-B2-n1 | 3/3 | table-mid | body | 5 | 2 | «B2[Z] text» | - | same | Paste clipboard |

Reading notes:

- **The `tl-end-*` rows.** The empty paragraph after the table, which Writer adds on import (`../README.md` summary item 5), now holds the marker. "Rest of the document" therefore shows that paragraph as added. This is the import artefact, not something the marker did. [observed + inferred, as in the parent]
- **`x-indent-home`.** The marker goes to offset 0 of the indented first paragraph. The indent is a paragraph property, not text, so D1 does not see it. [observed]
- **The `-n2`/`-n3` rows give the stepping.** They walk table and section boundaries one press at a time, and the marker positions follow the 142 table (`../README.md` items 3 and 7) press for press. [observed]

## Positive controls

Each control is the paired arm's script with every Ctrl press removed (`noCtrlScript` in `out/population.json`), then `T,S,L`. The reader requires each control's (part, index, offset) to differ from its paired arm's in every pair of rounds.

- `ctl-noctrl-a1-home-mid` lands at body 1, offset 5 («Bravo[Z] second paragraph»). `a1-home-mid` lands at body 0, offset 0. They differ by **paragraph**. 3/3. [observed]
- `ctl-noctrl-t-home-B2-n1` lands at body 5, offset 2 («B2[Z] text»). `t-home-B2-n1` lands at body 5, offset 0. They differ by **offset within the same cell paragraph**. 3/3. [observed]

So the reader distinguishes both coordinates, and the Ctrl press is what moves the marker in these arms.

## Red demos

### `tool/break_one_for_red_demo.py`, transcript `out/reader-red-demo.txt`

The script works on scratch copies of `out/` and leaves `out/` itself untouched.

- **Case 0, unbroken copy:** exit 0.
- **Case 1:** in `a1-home-mid/r2.fodt.gz`, `ZAlpha` becomes `AZlpha`. The XML is still valid, only the marker moved one character. Exit 1, with three independent reasons:
  - the in-process locator does not split the paragraph after the marker;
  - the rounds disagree (2/3);
  - the landing differs from the 142 locator.
- **Case 2:** `t-home-B2-n1/r3.fodt.gz` cut 200 bytes short. Exit 1, with two reasons:
  - `ParseError: unclosed token: line 351, column 6`;
  - only 2 of 3 rounds are complete.

### `tool/population_red_demo.py`, transcript `out/population-red-demo.txt`

1. An unknown step `X9` in one arm: exit 1.
2. Only the OUT arms kept: exit 1 (`zero arms IN`).
3. A fictional arm with only product steps appended: exit 0. It is listed IN with its D1 script, and the count goes 38 → 39, with no edit to the script.
4. A fictional arm with a `u.` step appended: exit 0, listed OUT with rule `u.`.

## What was run

### Engine and binary

- Install: `native-lok-26-8/build/instdir/program`, the same one as the parent run.
- `buildid` `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`.
- `libmergedlo.so`: 159,097,704 bytes, sha256 `2d49c9ff845d3e2cd3fb5d109ea95e9ce01bf45f2925e9a1ed2176eaedd3f924`. This equals the parent's record (`../README.md`, Engine).
- Headers: `libreoffice-26-8/include`, same HEAD. Full record: `out/environment.txt`.
- Probe: `tool/f142_d1_marker.cpp` (sha256 `c7d9d591…b3fbc5`). It is `../tool/f142_native_ctrl_home_end.cpp` plus a header comment, the `kMarker` constant and the `T` step (`diff` the two). Compiled as one file:

  ```
  g++ -std=c++17 -O2 -Wall -I libreoffice-26-8/include tool/f142_d1_marker.cpp -ldl -lpthread -o <scratchpad>/native-142m/f142-d1-marker
  ```

  The binary has sha256 `3a815e44…806849` and lives only in the session scratchpad. No `make` was run.

### Environment, per process

- `nice -n 10`, a fresh empty user profile, and its own copy of the fixture.
- `SAL_USE_VCLPLUGIN=svp`, set by the runner. `SAL_LOK_OPTIONS` removed, so LOK runs threaded, as in the parent and, per the parent's correction, as in the product.
- `LANG=zh_TW.UTF-8`, inherited, as in the parent.
- Rounds are run-major. Each JSONL's first line records the environment again.

### Waiting for other LOK processes

Before each process, `run_d1.py` waits while any other LOK probe runs. Total wait: **466 s** (`out/run-log.jsonl`, `waitedForOtherLokSeconds`).

- **sec-home-n1 r1: 394 s**, on the owner's desktop Writer (`/opt/libreoffice26.8/program/soffice.bin`). The first version of the detector matched every `soffice.bin`.
- **sec-end-n3 r1: 52 s**, and **a3-end-twice r2: 20 s**, both on the Markdown agent's `md-paste-probe2`.

**The runner was stopped once.** At 08:02 UTC it had waited about 17 min, again on the owner's desktop Writer, which had been reopened, before starting `a3-end-twice` r2. Nothing of ours was running and no file for that run existed.

The detector was then changed so that `soffice`/`soffice.bin` count only when run from an `instdir/program` study build. A desktop LibreOffice under `/opt` or `/usr` is not a probe and can stay open for hours. The runner was restarted with `--resume`, which skips (run, round) pairs that have a `done` record and a saved file. That wait never started a process, so it is not in `run-log.jsonl`. The 120 log lines have no duplicate (run, round).

What the detector checks:

- **Who counts as a probe:** any process that maps an `instdir/program/libmergedlo.so`, or has an `instdir/program` argument (the Markdown runner's own rule, so each runner waits for the other), or whose executable is named `md-paste-probe*`, `f142-*` or `native-md*`.
- **Positive check:** with one of our probes running, it reported that probe. Later it reported the Markdown agent's `md-paste-probe2` and its `timeout` wrapper.
- **Not verified from the other side:** whether a Markdown process started while one of ours was running. Their `runner.log` has no per-process start times. No D1 output depends on timing.

Process durations were 13.5–26.8 s. The 1-min load average was at most 1.93 at any start. All 120 processes exited 0. Their stderr has no crash and no error line [observed]. The warnings, as in the parent, are:

- `Flavor text/plain;charset=utf-16 is not supported` x606;
- `no explicit viewshell set` x480;
- once per process: two `MsLangId … not configured yet`, `error removing directory …/extensions`, `OpenCL driver check failed`, `SvxTabStopItem expected`.

### Commands

Run from this folder. `<S>` is the session scratchpad's `native-142m/`, and `<I>` is the absolute path of `native-lok-26-8/build/instdir/program`.

```
python3 -I tool/d1_population.py ../out/arms.json --json out/population.json > out/population.txt
python3 -I tool/population_red_demo.py ../out/arms.json <S>/pop-demo > out/population-red-demo.txt
python3 -I tool/run_d1.py --binary <S>/f142-d1-marker --install <I> --fixtures ../fixtures \
    --population out/population.json --out out --work <S>/work --runs 3
# stopped once while waiting (see above); detector changed; then:
python3 -I tool/run_d1.py ... (same arguments) --resume
python3 -I tool/read_marker.py out ../fixtures ../out/arms.json ../out > out/reader-output.txt
python3 -I tool/break_one_for_red_demo.py out ../fixtures ../out/arms.json ../out <S>/red-demo > out/reader-red-demo.txt
```

## What this does NOT show

- **Nothing about WASM or v21.** This is D1's native half. The v21 half has to type the same `Z` and save, then read the result with the same `tool/read_marker.py`. It compares (part, paragraph index, offset) and the paragraph text.
- **The engine's completion logic is not exercised.** Presses are posted with the parent probe's waits: 1.5 s of quiet before, 2 s after, and 1.5 s before the paste. The product's first-callback completion, its 250 ms readback and its revision guard are not here. D1 compares only the final landing.
  - If the product types before Ctrl+Home's `AsyncAccelExec` dispatch has run, the marker can land before the move. That is the reorder from the parent's correction, and these waits rule it out on the native side.
- **Typing path.** This covers only `paste()`, which is the engine's insert-text path while paste succeeds:
  - the `postKeyEvent` fallback is not covered, and neither is anything autocorrect or AutoComplete would do to key-typed input;
  - the product page's keyboard path was not traced to `insertText` (see above).
- **Header and footer: not covered**, because no header or footer arm is in the generated population (discrepancy above).
- **Shapes:** only the parent's fixtures and arms. The parent's "Shapes not tried" list applies unchanged: frames, notes, nested tables, empty cells, multi-page documents, hidden text, RTL/CJK and more.
- **Paragraph order edge cases.** The reader's order counts a paragraph nested inside another, such as a note or frame, right after its container begins, and the container's text includes the nested text. A marker in such a paragraph would count twice, and the reader would go red rather than mislocate it. No fixture here has one.
- **Single-line paragraphs.** The in-process locator check (Shift+End/Shift+Home) assumes the marker's paragraph is one line. All paragraphs here are short.
- **Formatting is not compared.** The reader reads text only, so the marker's attributes and the paragraph's style are not read. `x-indent-home`'s indent is the example.
- **Timing:** not used by any check here. Durations are in `out/run-log.jsonl` only.

## Files

- `tool/f142_d1_marker.cpp`: the probe (the parent probe plus `T`).
- `tool/d1_population.py`: the population generator.
- `tool/run_d1.py`: the runner and the control list.
- `tool/read_marker.py`: the reader.
- `tool/break_one_for_red_demo.py`, `tool/population_red_demo.py`: the red demos.
- `out/population.txt`, `out/population.json`: the IN/OUT listing; the JSON also holds each IN arm's `d1Script` and `noCtrlScript`.
- `out/runs.json`: what was run (38 D1 arms and 2 controls).
- `out/<run>/r<N>.jsonl`: raw records `env`, `load`, `setup`, `point`, `press`, `typed`, `saved`, `locate`, `done`. The `typed` record lists callback types without payloads.
- `out/<run>/r<N>.stderr`, `out/<run>/r<N>.fodt.gz`: SAL warnings and the saved document.
- `out/run-log.jsonl`: one line per process, with start time, seconds, exit code, wait, what was waited on, load average and command.
- `out/environment.txt`.
- `out/reader-output.txt`, `out/reader-red-demo.txt`, `out/population-red-demo.txt`.
- `SHA256SUMS`: every file here except itself.
